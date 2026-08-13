#include "Sensors.h"
#include "Config.h"
#include <microDS18B20.h>

MicroDS18B20<DS1_PIN> sensor1;
MicroDS18B20<DS2_PIN> sensor2;
MicroDS18B20<DS3_PIN> sensor3;
MicroDS18B20<DS4_PIN> sensor4;
MicroDS18B20<DS5_PIN> sensor5;

float last1 = INVALID_TEMP;
float last2 = INVALID_TEMP;
float last3 = INVALID_TEMP;
float last4 = INVALID_TEMP;
float last5 = INVALID_TEMP;

unsigned long requestTime = 0;
bool waiting = false;

void sensorsBegin()
{
    last1 = INVALID_TEMP;
    last2 = INVALID_TEMP;
    last3 = INVALID_TEMP;
    last4 = INVALID_TEMP;
    last5 = INVALID_TEMP;
}

void sensorsRequest()
{
    sensor1.requestTemp();
    sensor2.requestTemp();
    sensor3.requestTemp();
    sensor4.requestTemp();
    sensor5.requestTemp();
    requestTime = millis();
    waiting = true;
}

bool sensorsReady()
{
    if(!waiting)
        return false;
    if(millis() - requestTime >= DS18_WAIT_TIME)
    {
        waiting = false;
        return true;
    }
    return false;
}

bool validTemperature(
    float value,
    float lastValue)
{
    if(value == 85.0)
        return false;
    if(value < -55 || value > 125)
        return false;
    if(lastValue != INVALID_TEMP)
    {
        if(abs(value - lastValue) > MAX_TEMP_CHANGE)
            return false;
    }
    return true;
}

float readSensorValue(
    bool result,
    float value,
    float &lastValue)
{
    if(result)
    {
        if(validTemperature(value,lastValue))
        {
            lastValue = value;
        }
    }
    return lastValue;
}

void sensorsRead(
    float &t1,
    float &t2,
    float &t3,
    float &t4,
    float &t5
)
{
    if(sensor1.readTemp())
    {
        t1 = readSensorValue(true,sensor1.getTemp(),last1);
    }
    else
    {
        t1 = last1;
    }
    if(sensor2.readTemp())
    {
        t2 = readSensorValue(true,sensor2.getTemp(),last2);
    }
    else
    {
        t2 = last2;
    }
    if(sensor3.readTemp())
    {
        t3 = readSensorValue(true,sensor3.getTemp(),last3);
    }
    else
    {
        t3 = last3;
    }
    if(sensor4.readTemp())
    {
        t4 = readSensorValue(true,sensor4.getTemp(),last4);
    }
    else
    {
        t4 = last4;
    }
    if(sensor5.readTemp())
    {
        t5 = readSensorValue(true,sensor5.getTemp(),last5);
    }
    else
    {
        t5 = last5;
    }
}