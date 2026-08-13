/*
 * Renovo — снятие температуры с датчиков DS18B20 и выдача в Serial.
 *
 * Плата:    Arduino UNO
 * Схема:    каждый датчик на своём пине (по одному DS18B20 на линию).
 *           На КАЖДОЙ линии нужен свой подтягивающий резистор 4.7 кОм
 *           между её выводом DATA и +5V. Питание VDD/GND — общее.
 *
 * Вывод:    одна строка JSON на замер, 115200 бод:
 *           {"boot":815623,"seq":12,"age":0,"t":{"s1":23.5,"s2":24.1}}
 *
 * boot — случайный идентификатор запуска, генерируется при каждом включении.
 * Открытие COM-порта перезагружает плату и обнуляет seq, поэтому без boot
 * сервер принимал бы новые замеры за дубликаты уже записанных.
 *
 * Номер датчика соответствует его позиции в SENSOR_PINS: первый пин в списке
 * это s1, второй — s2 и так далее. Чтобы добавить датчик, достаточно вписать
 * его пин в этот массив — остальной код и сервер подстроятся сами.
 *
 * Библиотеки (Менеджер библиотек Arduino IDE):
 *   OneWire            by Paul Stoffregen
 *   DallasTemperature  by Miles Burton
 */

#include <OneWire.h>
#include <DallasTemperature.h>

/* ─── Настройка под вашу схему ──────────────────────────────────────────
   Перечислите пины, к которым подключены датчики, по порядку s1, s2, ...
   Это единственное место, которое нужно менять при другой распиновке
   или при добавлении датчиков. */
const uint8_t SENSOR_PINS[] = {2, 3, 4, 5, 6};
/* ───────────────────────────────────────────────────────────────────────*/

const uint8_t SENSOR_COUNT = sizeof(SENSOR_PINS) / sizeof(SENSOR_PINS[0]);

// Линии создаются пустыми, а привязка к пину делается в setup() из
// SENSOR_PINS — так список пинов остаётся в одном экземпляре.
OneWire buses[SENSOR_COUNT];

const uint16_t SAMPLE_MS  = 2000;   // период опроса
const uint8_t  RESOLUTION = 11;     // 11 бит: шаг 0.125 °C, преобразование ~375 мс
const uint16_t CONVERT_MS = 400;    // ожидание преобразования с запасом

/* Диапазон измерения DS18B20 по паспорту. Значения вне него — неисправность:
   -127 выдаётся при обрыве линии. */
const float TEMP_MIN = -55.0;
const float TEMP_MAX = 125.0;

// Один объект на все линии: DallasTemperature умеет переключаться между
// шинами через setOneWire(), поэтому пять копий держать в памяти не нужно.
DallasTemperature probe;

DeviceAddress addr[SENSOR_COUNT];   // адрес датчика на каждой линии
bool present[SENSOR_COUNT];         // найден ли датчик на этой линии

uint32_t bootId = 0;
uint32_t seq = 0;
uint32_t lastSample = 0;

/* Ищет датчик на одной линии и запоминает его адрес. */
bool probeLine(uint8_t i) {
  probe.setOneWire(&buses[i]);
  probe.begin();
  if (!probe.getAddress(addr[i], 0)) return false;
  probe.setResolution(addr[i], RESOLUTION);
  return true;
}

void discoverAll() {
  for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
    present[i] = probeLine(i);
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }

  // Энтропию берём с неподключённого аналогового входа: его младшие биты
  // шумят. Абсолютная уникальность не нужна — важно лишь, чтобы соседние
  // запуски получали разные значения.
  randomSeed(analogRead(A0) ^ micros());
  bootId = ((uint32_t)random(1, 0x7FFFFFFF));

  // Преобразование запускаем на всех линиях сразу и ждём один раз, иначе
  // пять последовательных ожиданий по 375 мс не уложились бы в период опроса.
  probe.setWaitForConversion(false);

  for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
    buses[i].begin(SENSOR_PINS[i]);
  }

  discoverAll();

  // Служебные строки начинаются с '#', шлюз их игнорирует при разборе JSON.
  Serial.print(F("# renovo temp node, boot="));
  Serial.println(bootId);

  uint8_t found = 0;
  for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
    Serial.print(F("#   s"));
    Serial.print(i + 1);
    Serial.print(F(" (pin D"));
    Serial.print(SENSOR_PINS[i]);
    Serial.print(F(") = "));
    if (!present[i]) {
      Serial.println(F("НЕ НАЙДЕН"));
      continue;
    }
    for (uint8_t b = 0; b < 8; b++) {
      if (addr[i][b] < 16) Serial.print('0');
      Serial.print(addr[i][b], HEX);
    }
    Serial.println();
    found++;
  }

  Serial.print(F("# sensors found: "));
  Serial.print(found);
  Serial.print(F(" of "));
  Serial.println(SENSOR_COUNT);

  if (found < SENSOR_COUNT) {
    Serial.println(F("# проверьте резистор 4.7к на каждой линии и распиновку"));
  }
}

void loop() {
  if (millis() - lastSample < SAMPLE_MS) return;
  lastSample = millis();

  // Датчик мог быть подключён после старта — периодически ищем заново
  // на тех линиях, где его не было.
  for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
    if (!present[i]) present[i] = probeLine(i);
  }

  // Шаг 1: команда на преобразование всем линиям, без ожидания.
  for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
    if (!present[i]) continue;
    probe.setOneWire(&buses[i]);
    probe.requestTemperatures();
  }

  // Шаг 2: одно общее ожидание — датчики считают параллельно.
  delay(CONVERT_MS);

  // Шаг 3: сбор результатов.
  seq++;
  bool any = false;
  String out = F("{\"boot\":");
  out += bootId;
  out += F(",\"seq\":");
  out += seq;
  out += F(",\"age\":0,\"t\":{");

  for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
    if (!present[i]) continue;

    probe.setOneWire(&buses[i]);
    float t = probe.getTempC(addr[i]);

    // Сбойный датчик просто пропускаем: остальные значения уйдут на сервер.
    if (t == DEVICE_DISCONNECTED_C || t < TEMP_MIN || t > TEMP_MAX) {
      present[i] = false;   // линия отвалилась — поищем датчик на следующем цикле
      continue;
    }

    if (any) out += ',';
    out += F("\"s");
    out += (i + 1);
    out += F("\":");
    out += String(t, 2);
    any = true;
  }

  out += F("}}");

  if (any) {
    Serial.println(out);
  } else {
    Serial.println(F("# нет исправных датчиков в этом замере"));
  }
}
