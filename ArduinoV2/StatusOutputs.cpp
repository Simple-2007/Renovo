#include "StatusOutputs.h"

void statusBegin()
{
    pinMode(SENSOR_ERROR_PIN, OUTPUT);
    pinMode(RTC_ERROR_PIN, OUTPUT);
    pinMode(PC_OK_PIN, OUTPUT);
    digitalWrite(SENSOR_ERROR_PIN, LOW);
    digitalWrite(RTC_ERROR_PIN, LOW);
    digitalWrite(PC_OK_PIN, LOW);
}

void setSensorError(bool state)
{
    digitalWrite(SENSOR_ERROR_PIN,state ? HIGH : LOW);
}

void setRtcError(bool state)
{
    digitalWrite(RTC_ERROR_PIN,state ? HIGH : LOW);
}

void setPcConnection(bool state)
{
    digitalWrite(PC_OK_PIN,state ? HIGH : LOW);
}