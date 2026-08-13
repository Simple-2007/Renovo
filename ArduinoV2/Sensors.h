#ifndef SENSORS_H
#define SENSORS_H

#include <Arduino.h>

// Инициализация датчиков
void sensorsBegin();

// Запуск измерения
void sensorsRequest();

// Проверка готовности
bool sensorsReady();

// Чтение температур
void sensorsRead(float &t1,float &t2,float &t3,float &t4,float &t5);

#endif