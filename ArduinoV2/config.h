#ifndef CONFIG_H
#define CONFIG_H

// ==========================
// DS18B20 PINS
// ==========================
#define DS1_PIN 2
#define DS2_PIN 3
#define DS3_PIN 4
#define DS4_PIN 5
#define DS5_PIN 6

// ==========================
// SD CARD
// ==========================
#define SD_CS_PIN 10
#define BUFFER_FILE "buffer.csv"

// ==========================
// SERIAL
// ==========================
#define SERIAL_BAUD 9600

// ==========================
// TIMERS
// ==========================
// 30 минут
#define MEASURE_INTERVAL 1800000UL

// проверка ПК
#define PC_PING_INTERVAL 15000UL

// время ожидания DS18B20
#define DS18_WAIT_TIME 750UL

// ==========================
// TEMPERATURE
// ==========================
#define INVALID_TEMP -99.0f
#define MAX_TEMP_CHANGE 5.0f

// ==========================
// EEPROM
// ==========================
#define EEPROM_COUNTER_ADDRESS 0

#endif