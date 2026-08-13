#ifndef EEPROM_COUNTER_H
#define EEPROM_COUNTER_H


#include <Arduino.h>

// Инициализация счетчика
void counterBegin();

// Получить текущее значение
unsigned long getCounter();

// Увеличить счетчик и сохранить
unsigned long nextCounter();

#endif