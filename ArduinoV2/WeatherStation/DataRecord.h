#ifndef DATA_RECORD_H
#define DATA_RECORD_H

#include <Arduino.h>

struct DataRecord
{
    unsigned long number;

    uint16_t year;
    uint8_t month;
    uint8_t day;

    uint8_t hour;
    uint8_t minute;

    uint8_t second;
    float sensor1;
    float sensor2;
    float sensor3;
    float sensor4;
    float sensor5;
};
#endif