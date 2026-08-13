#ifndef APPLICATION_H
#define APPLICATION_H

#include <Arduino.h>
#include "DataRecord.h"

enum AppState
{
    APP_STARTUP,
    APP_IDLE,
    APP_WAIT_SENSOR,
    APP_SEND_RECORD,
    APP_SAVE_RECORD
};

class Application
{
public:
    void begin();
    void update();

private:
    AppState state;
    unsigned long lastMeasureTime;
    DataRecord record;
    void startup();
    void idle();
    void waitSensor();
    void makeRecord();
    void formatRecord(char* buffer, size_t size);
    void sendRecord();
    void saveRecord();
};

extern Application App;
#endif