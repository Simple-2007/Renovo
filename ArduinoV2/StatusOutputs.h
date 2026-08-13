#ifndef STATUS_OUTPUTS_H
#define STATUS_OUTPUTS_H

#include <Arduino.h>


#define SENSOR_ERROR_PIN 7
#define RTC_ERROR_PIN 8
#define PC_OK_PIN 9

void statusBegin();

void setSensorError(bool state);

void setRtcError(bool state);

void setPcConnection(bool state);

#endif