#include "SerialProtocol.h"
#include "RTCClock.h"
#include "SDStorage.h"
#include "StatusOutputs.h"

bool pcConnected = false;

char commandBuffer[64];
uint8_t commandIndex = 0;

void serialProtocolBegin()
{
    Serial.begin(9600);
}

// -------------------------------------------------
// обработка входящих символов
// -------------------------------------------------
void serialProtocolLoop()
{
    while(Serial.available())
    {
        char c = Serial.read();
        if(c == '\n')
        {
            commandBuffer[commandIndex] = 0;
            String command = commandBuffer;
            command.trim();
            if(command == "PING")
            {
                Serial.println("PONG");
                pcConnected = true;
                setPcConnection(true);
            }
            else if(command == "BUFFER")
            {
                pcConnected = true;
                sdSendBuffer();
            }
            else if(command.startsWith("TIME;"))
            {
                int y = command.substring(5,9).toInt();
                int m = command.substring(10,12).toInt();
                int d = command.substring(13,15).toInt();
                int h = command.substring(16,18).toInt();
                int min = command.substring(19,21).toInt();
                int s = command.substring(22,24).toInt();
                rtcSetTime(DateTime(y,m,d,h,min,s));
                Serial.println("TIME_OK");
            }
            else if(command == "STATUS")
            {
                Serial.print("STATUS;");
                if(rtcIsRunning())
                    Serial.print("RTC_OK;");
                else
                    Serial.print("RTC_ERROR;");

                if(sdBufferExists())
                    Serial.println("BUFFER_EXISTS");
                else
                    Serial.println("BUFFER_EMPTY");
            }
            commandIndex = 0;
        }
        else
        {
            if(commandIndex < sizeof(commandBuffer)-1)
            {
                commandBuffer[commandIndex++] = c;
            }
        }
    }
}

bool isPcConnected()
{
    return pcConnected;
}

void clearPcConnection()
{
    pcConnected=false;
    setPcConnection(false);
}
