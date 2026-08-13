#ifndef SERIAL_PROTOCOL_H
#define SERIAL_PROTOCOL_H

#include <Arduino.h>

// запуск Serial протокола
void serialProtocolBegin();

// обработка команд ПК
void serialProtocolLoop();

// состояние связи с ПК
bool isPcConnected();

// сброс состояния связи
void clearPcConnection();

#endif