#include "SDStorage.h"
#include "Config.h"
#include <SPI.h>
#include <SD.h>

File bufferFile;

bool sdBegin()
{
    if(!SD.begin(SD_CS_PIN))
        return false;
    return true;
}

bool sdSave(String data)
{
    bufferFile = SD.open(BUFFER_FILE,FILE_WRITE);
    if(!bufferFile)
        return false;
    bufferFile.println(data);
    bufferFile.close();
    return true;
}

bool sdBufferExists()
{
    return SD.exists(BUFFER_FILE);
}

void sdSendBuffer()
{
    if(!sdBufferExists())
    {
        Serial.println("BUFFER_EMPTY");
        return;
    }
    File file = SD.open(BUFFER_FILE);
    if(!file)
    {
        Serial.println("BUFFER_ERROR");
        return;
    }
    while(file.available())
    {
        String line = file.readStringUntil('\n');
        line.trim();
        if(line.length() > 0)
        {
            Serial.print("DATA;");
            Serial.println(line);
            unsigned long start = millis();
            bool ack = false;
            while(millis()-start < 5000)
            {
                if(Serial.available())
                {
                    String answer = Serial.readStringUntil('\n');
                    answer.trim();
                    if(answer == "ACK")
                    {
                        ack = true;
                        break;
                    }
                }
            }
            if(!ack)
            {
                file.close();
                return;
            }
        }
    }
    file.close();
    Serial.println("BUFFER_FINISHED");
}

bool sdClearBuffer()
{
    if(SD.exists(BUFFER_FILE))
        return SD.remove(BUFFER_FILE);
    return true;

}