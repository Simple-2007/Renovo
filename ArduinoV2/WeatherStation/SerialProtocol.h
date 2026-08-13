#ifndef SERIAL_PROTOCOL_H
#define SERIAL_PROTOCOL_H

#include <Arduino.h>

void serialProtocolBegin();

void serialProtocolLoop();

bool isPcConnected();

void clearPcConnection();

#endif