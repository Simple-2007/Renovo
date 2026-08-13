#ifndef EEPROM_COUNTER_H
#define EEPROM_COUNTER_H

#include <Arduino.h>

void counterBegin();

unsigned long getCounter();

unsigned long nextCounter();

#endif