#ifndef SD_STORAGE_H
#define SD_STORAGE_H

#include <Arduino.h>

// запуск SD карты
bool sdBegin();

// сохранить строку
bool sdSave(String data);

// проверить наличие буфера
bool sdBufferExists();

// отправить буфер в Serial
void sdSendBuffer();

// удалить буфер
bool sdClearBuffer();

#endif