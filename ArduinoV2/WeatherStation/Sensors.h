#ifndef SENSORS_H
#define SENSORS_H

#include <Arduino.h>

void sensorsBegin();

void sensorsRequest();

bool sensorsReady();

void sensorsRead(float &t1,float &t2,float &t3,float &t4,float &t5);

#endif