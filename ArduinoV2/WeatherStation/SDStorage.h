#ifndef SD_STORAGE_H
#define SD_STORAGE_H

#include <Arduino.h>

bool sdBegin();

bool sdSave(String data);

bool sdBufferExists();

void sdSendBuffer();

bool sdClearBuffer();

#endif