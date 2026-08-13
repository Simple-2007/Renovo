#include "RTCClock.h"
#include "StatusOutputs.h"

RTC_DS3231 rtc;

bool rtcOk = false;

void rtcBegin()
{
    if(!rtc.begin())
    {
        Serial.println("RTC_ERROR");
        rtcOk = false;
        setRtcError(true);
        return;
    }
    if(rtc.lostPower())
    {
        Serial.println("RTC_LOST");
        rtcOk = false;
        setRtcError(true);
    }
    else
    {
        rtcOk = true;
        setRtcError(false);
    }
}

DateTime rtcGetTime()
{
    return rtc.now();
}

void rtcSetTime(DateTime dt)
{
    rtc.adjust(dt);
    Serial.println("TIME_OK");
}

bool rtcLostPower()
{
    return rtc.lostPower();
}

bool rtcIsRunning()
{
    return rtcOk;
}
