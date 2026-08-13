#ifndef RTC_CLOCK_H
#define RTC_CLOCK_H

#include <Arduino.h>
#include <RTClib.h>

void rtcBegin();
DateTime rtcGetTime();

void rtcSetTime(DateTime dt);

// проверка потери питания RTC
bool rtcLostPower();

bool rtcIsRunning();

#endif