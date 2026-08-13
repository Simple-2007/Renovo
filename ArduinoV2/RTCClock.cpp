#include "RTCClock.h"
RTC_DS3231 rtc;

void rtcBegin()
{
    if(!rtc.begin())
    {
        Serial.println("RTC_ERROR");
        return;
    }
    if(rtc.lostPower())
        Serial.println("RTC_LOST");
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

if(rtc.lostPower())
{
    Serial.println("RTC_LOST");
    setRtcError(true);
}
else
    setRtcError(false);

bool rtcIsRunning()
{
    return true;
}

