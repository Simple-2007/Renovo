#include "Application.h"
#include "StatusOutputs.h"
#include "Sensors.h"
#include "RTCClock.h"
#include "SDStorage.h"
#include "SerialProtocol.h"
#include "EEPROMCounter.h"
#include "DataRecord.h"
#include "Config.h"

Application App;

void Application::begin()
{
    counterBegin();
    sensorsBegin();
    rtcBegin();
    sdBegin();
    serialProtocolBegin();
    statusBegin();
    lastMeasureTime = millis();
    state = APP_IDLE;
}

void Application::update()
{
    serialProtocolLoop();
    switch(state)
    {
        case APP_STARTUP:
            startup();
            break;
        case APP_IDLE:
            idle();
            break;
        case APP_WAIT_SENSOR:
            waitSensor();
            break;
        case APP_SEND_RECORD:
            sendRecord();
            break;
        case APP_SAVE_RECORD:
            saveRecord();
            break;
    }
}

void Application::startup()
{
    state = APP_IDLE;
}

void Application::idle()
{
    if(millis() - lastMeasureTime >= MEASURE_INTERVAL)
    {
        lastMeasureTime += MEASURE_INTERVAL;
        sensorsRequest();
        state = APP_WAIT_SENSOR;
    }
}

void Application::waitSensor()
{
    if(!sensorsReady())
        return;
    makeRecord();
    if(isPcConnected())
        state = APP_SEND_RECORD;
    else
        state = APP_SAVE_RECORD;
}

void Application::makeRecord()
{
    record.number = nextCounter();
    DateTime now = rtcGetTime();
    record.year = now.year();
    record.month = now.month();
    record.day = now.day();
    record.hour = now.hour();
    record.minute = now.minute();
    record.second = now.second();
    sensorsRead(record.sensor1,record.sensor2,record.sensor3,record.sensor4,record.sensor5);
}

//void Application::formatRecord(char* buffer,size_t size)
//{
//    snprintf(buffer,size,"DATA;%lu;%04u-%02u-%02u %02u:%02u:%02u;%.2f;%.2f;%.2f;%.2f;%.2f",
//        record.number,record.year,record.month,record.day,record.hour,
//        record.minute,record.second,record.sensor1,record.sensor2,record.sensor3,record.sensor4,record.sensor5);
//}

void Application::formatRecord(char* buffer, size_t size)
{
    char t1[16];
    char t2[16];
    char t3[16];
    char t4[16];
    char t5[16];

    dtostrf(record.sensor1, 0, 2, t1);
    dtostrf(record.sensor2, 0, 2, t2);
    dtostrf(record.sensor3, 0, 2, t3);
    dtostrf(record.sensor4, 0, 2, t4);
    dtostrf(record.sensor5, 0, 2, t5);

    snprintf(buffer, size, "DATA;%lu;%04u-%02u-%02u %02u:%02u:%02u;%s;%s;%s;%s;%s",
        record.number,record.year,record.month,record.day,record.hour,record.minute,record.second,t1,t2,t3,t4,t5);
}

void Application::sendRecord()
{
    char buffer[128];
    formatRecord(buffer,sizeof(buffer));
    Serial.println(buffer);
    state = APP_IDLE;
}

//void Application::sendRecord()
//{
//    char buffer[128];
//
//    Serial.print("DEBUG RTC: ");
//    Serial.print(record.year);
//    Serial.print("-");
//    Serial.print(record.month);
//    Serial.print("-");
//    Serial.print(record.day);
//    Serial.print(" ");
//    Serial.print(record.hour);
//    Serial.print(":");
//    Serial.print(record.minute);
//    Serial.print(":");
//    Serial.println(record.second);
//
//    Serial.print("DEBUG TEMP: ");
//    Serial.print(record.sensor1);
//    Serial.print(";");
//    Serial.print(record.sensor2);
//    Serial.print(";");
//    Serial.print(record.sensor3);
//    Serial.print(";");
//    Serial.print(record.sensor4);
//    Serial.print(";");
//    Serial.println(record.sensor5);
//
//    formatRecord(buffer, sizeof(buffer));
//
//    Serial.println(buffer);
//
//    state = APP_IDLE;
//}
//

//void sendRecord()
//{
//    Serial.print("DATA;");
//    Serial.print(record.number);
//    Serial.print(";");
//    Serial.print(record.year);
//    Serial.print("-");
//    if(record.month < 10) Serial.print("0");
//    Serial.print(record.month);
//    Serial.print("-");
//    if(record.day < 10) Serial.print("0");
//    Serial.print(record.day);
//    Serial.print(" ");
//    if(record.hour < 10) Serial.print("0");
//    Serial.print(record.hour);
//    Serial.print(":");
//    if(record.minute < 10) Serial.print("0");
//    Serial.print(record.minute);
//    Serial.print(":");
//    if(record.second < 10) Serial.print("0");
//    Serial.print(record.second);
//    Serial.print(";");
//    Serial.print(record.sensor1, 2);
//    Serial.print(";");
//    Serial.print(record.sensor2, 2);
//    Serial.print(";");
//    Serial.print(record.sensor3, 2);
//    Serial.print(";");
//    Serial.print(record.sensor4, 2);
//    Serial.print(";");
//    Serial.println(record.sensor5, 2);
//    state = APP_IDLE;
//}
//
void Application::saveRecord()
{
    char buffer[128];
    formatRecord(buffer,sizeof(buffer));
    sdSave(String(buffer));
    state = APP_IDLE;
}