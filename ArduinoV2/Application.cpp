#include "Application.h"


#include "Config.h"
#include "Sensors.h"
#include "RTCClock.h"
#include "EEPROMCounter.h"
#include "SDStorage.h"
#include "SerialProtocol.h"

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
    {
        state = APP_SEND_RECORD;
    }
    else
    {
        state = APP_SAVE_RECORD;
    }
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

void Application::formatRecord(char* buffer,size_t size)
{
    snprintf(
        buffer,size,"DATA;%lu;%04u-%02u-%02u %02u:%02u:%02u;%.2f;%.2f;%.2f;%.2f;%.2f",
        record.number,record.year,record.month,record.day,record.hour,
        record.minute,record.second,record.sensor1,record.sensor2,record.sensor3,record.sensor4,record.sensor5);
}

void Application::sendRecord()
{
    char buffer[128];
    formatRecord(buffer,sizeof(buffer));
    Serial.println(buffer);
    state = APP_IDLE;
}

void Application::saveRecord()
{
    char buffer[128];
    formatRecord(buffer,sizeof(buffer));
    sdSave(String(buffer));
    state = APP_IDLE;
}