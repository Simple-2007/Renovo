#include "EEPROMCounter.h"
#include "Config.h"

#include <EEPROM.h>

unsigned long counterValue = 0;

void counterBegin()
{
    EEPROM.get(EEPROM_COUNTER_ADDRESS,counterValue);
    if(counterValue == 0xFFFFFFFF)
        counterValue = 0;
}

unsigned long getCounter()
{
    return counterValue;
}

unsigned long nextCounter()
{
    counterValue++;
    EEPROM.put(EEPROM_COUNTER_ADDRESS,counterValue);
    return counterValue;
}