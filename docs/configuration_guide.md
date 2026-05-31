# Руководство по конфигурации Irene Voice Assistant v13

> **⚠️ Устарело (v13).** Каноническая конфигурация для v15 — полностью прокомментированный
> `configs/config-master.toml` и описание в [`configs/config-example.md`](../configs/config-example.md).
> Этот документ сохранён как историческая справка по модели «опциональных компонентов».

## 🎯 Обзор

Irene Voice Assistant v13 представляет собой модульную систему с **опциональными компонентами**, которые можно включать или отключать в зависимости от ваших потребностей. Это позволяет создавать различные конфигурации - от простого текстового процессора до полноценного голосового ассистента.

## 📋 Сценарии использования

### 1. 💬 **Режим командной строки (CLI)**
**Описание**: Текстовый интерфейс для ввода команд с клавиатуры
**Подходит для**: Тестирования, отладки, серверных установок без аудио

**Установка**:
```bash
uv add irene-voice-assistant[headless]
```

**Компоненты**:
- ✅ CLI Input (всегда доступен)
- ✅ Text Output (всегда доступен)
- ❌ Микрофон
- ❌ TTS
- ❌ Web API

**Конфигурация** (`config.toml`):
```toml
[components]
microphone = false
tts = false
audio_output = false
web_api = false

[plugins.core_commands]
enabled = true

[plugins.greetings]
enabled = true

[plugins.datetime]
enabled = true

[plugins.random]
enabled = true
```

**Запуск**:
```bash
python -m irene.runners.cli
# или
python -m irene.runners.cli --single "привет"
```

---

### 2. 🌐 **Режим веб-сервера (API)**
**Описание**: REST API и WebSocket сервер без аудио компонентов
**Подходит для**: Веб-приложений, чат-ботов, интеграции с другими сервисами

**Установка**:
```bash
uv add irene-voice-assistant[api]
```

**Компоненты**:
- ✅ CLI Input
- ✅ Web Input (HTTP/WebSocket)
- ✅ Text Output
- ✅ Web Output (JSON responses)
- ❌ Микрофон
- ❌ TTS

**Конфигурация** (`config.toml`):
```toml
[components]
microphone = false
tts = false
audio_output = false
web_api = true

[components.web_api]
host = "0.0.0.0"
port = 8000
cors_origins = ["*"]
enable_docs = true

[plugins.core_commands]
enabled = true

[plugins.greetings]
enabled = true

[plugins.datetime]
enabled = true
```

**Запуск**:
```bash
python -m irene.runners.webapi
```

**Использование**:
- Веб-интерфейс: `http://localhost:8000`
- API документация: `http://localhost:8000/docs`
- WebSocket: `ws://localhost:8000/ws`

---

### 3. 🎤 **Полный голосовой ассистент**
**Описание**: Полная функциональность с микрофоном, TTS и веб-интерфейсом
**Подходит для**: Домашних ассистентов, интерактивных систем

**Установка**:
```bash
uv add irene-voice-assistant[voice]
```

**Компоненты**:
- ✅ CLI Input
- ✅ Microphone Input (VOSK)
- ✅ Web Input
- ✅ Text Output
- ✅ TTS Output (pyttsx3, Silero)
- ✅ Audio Output
- ✅ Web Output

**Конфигурация** (`config.toml`):
```toml
[components]
microphone = true
tts = true
audio_output = true
web_api = true

[components.microphone]
model_path = "./model"  # Путь к модели VOSK
device_id = -1          # -1 для устройства по умолчанию
sample_rate = 16000

[components.tts]
default_engine = "pyttsx3"
voice_id = "russian"

[components.web_api]
host = "0.0.0.0"
port = 8000

[plugins.core_commands]
enabled = true

[plugins.greetings]
enabled = true

[plugins.datetime]
enabled = true

[plugins.async_timer]
enabled = true

[plugins.pyttsx_tts]
enabled = true

[plugins.silero_v3_tts]
enabled = true
model_path = "~/.cache/irene/models/silero"

[plugins.sounddevice_audio]
enabled = true
```

**Запуск**:
```bash
# VOSK-режим (голосовой ввод)
python -m irene.runners.vosk

# Веб-режим (все интерфейсы)
python -m irene.runners.webapi
```

---

### 4. 🎧 **Только TTS (без микрофона)**
**Описание**: Система с текстовым вводом и голосовым выводом
**Подходит для**: Чтения текста, уведомлений, систем без микрофона

**Установка**:
```bash
uv add irene-voice-assistant[tts,web-api]
```

**Компоненты**:
- ✅ CLI Input
- ✅ Web Input
- ✅ Text Output
- ✅ TTS Output
- ✅ Web Output
- ❌ Микрофон

**Конфигурация** (`config.toml`):
```toml
[components]
microphone = false
tts = true
audio_output = true
web_api = true

[plugins.pyttsx_tts]
enabled = true
voice_rate = 200
voice_volume = 0.9

[plugins.silero_v3_tts]
enabled = true
speaker_id = "xenia"
```

---

### 5. 🐳 **Docker/Контейнерный режим**
**Описание**: Конфигурация для развертывания в контейнерах
**Подходит для**: Облачных развертываний, микросервисов

**Установка**:
```bash
uv add irene-voice-assistant[api]
```

**Конфигурация** (`config.toml`):
```toml
[components]
microphone = false
tts = false
audio_output = false
web_api = true

[components.web_api]
host = "0.0.0.0"
port = 8000

# Используем переменные окружения для настройки
[plugins]
# Конфигурация через IRENE_PLUGINS__*
```

**Переменные окружения**:
```bash
IRENE_COMPONENTS__WEB_API__PORT=8000
IRENE_COMPONENTS__WEB_API__HOST=0.0.0.0
IRENE_PLUGINS__GREETINGS__ENABLED=true
```

---

### 6. 🌊 **Веб-сервер с аудиопотоком и ИИ-обработкой**
**Описание**: Веб-сервер, принимающий аудиопоток от внешнего микрофона, выполняющий распознавание речи, улучшение результата с помощью LLM и текстовый вывод
**Подходит для**: Облачных сервисов распознавания речи, ИИ-ассистентов, интеграции с внешними устройствами

**Установка**:
```bash
uv add irene-voice-assistant[api,audio-input,ai-processing]
```

**Компоненты**:
- ✅ Web Input (аудиопотоки + HTTP/WebSocket)
- ✅ ASR Processing (VOSK/Whisper)
- ✅ LLM Integration (GPT/Claude/локальные модели)
- ✅ Text Output
- ✅ Web Output (JSON responses)
- ❌ Локальный микрофон
- ❌ TTS вывод

**Конфигурация** (`config.toml`):
```toml
[components]
microphone = false              # Аудио поступает через веб
tts = false                    # Только текстовый вывод
audio_output = false
web_api = true
asr_processing = true          # Включить ASR обработку
llm_processing = true          # Включить LLM улучшение

[components.web_api]
host = "0.0.0.0"
port = 8000
cors_origins = ["*"]
enable_docs = true
max_audio_size = "10MB"        # Максимальный размер аудиофайла
audio_formats = ["wav", "mp3", "webm", "ogg"]

[components.asr]
engine = "vosk"                # vosk, whisper, или custom
model_path = "./models/vosk-ru"
confidence_threshold = 0.7      # Минимальная уверенность
language = "ru"
enable_streaming = true        # Поддержка потокового ASR

[components.llm]
provider = "openai"            # openai, anthropic, local, custom
model = "gpt-4"               # Модель для улучшения результатов
api_key_env = "OPENAI_API_KEY" # Переменная окружения с ключом
system_prompt = "Ты помощник, который улучшает результаты распознавания речи. Исправь ошибки и сделай текст более читаемым, сохраняя смысл."
max_tokens = 150
temperature = 0.3

[plugins.core_commands]
enabled = true

[plugins.asr_processor]
enabled = true

[plugins.llm_enhancer]
enabled = true

[plugins.web_audio_receiver]
enabled = true
```

**API Endpoints**:
```bash
# Отправка аудиофайла для обработки
POST /audio/process
Content-Type: multipart/form-data
{
  "audio": <audio_file>,
  "enhance": true,           # Включить LLM улучшение
  "language": "ru"
}

# Потоковое распознавание через WebSocket
WS /audio/stream
{
  "type": "audio_chunk",
  "data": "<base64_audio>",
  "format": "wav",
  "sample_rate": 16000
}

# Получение результата
{
  "original_text": "превет как дила",
  "enhanced_text": "Привет, как дела?",
  "confidence": 0.85,
  "processing_time": 1.2
}
```

**Запуск**:
```bash
# Запуск веб-сервера с ASR+LLM
python -m irene.runners.webapi --enable-asr --enable-llm

# С настройкой портов
python -m irene.runners.webapi --port 9000 --asr-port 9001
```

**Использование**:
- API документация: `http://localhost:8000/docs`
- Тестовый интерфейс: `http://localhost:8000/audio-test`
- WebSocket ASR: `ws://localhost:8000/audio/stream`
- REST API: `POST http://localhost:8000/audio/process`

**Переменные окружения**:
```bash
# LLM настройки
export OPENAI_API_KEY="your_api_key_here"
export ANTHROPIC_API_KEY="your_claude_key_here"

# ASR настройки
export IRENE_COMPONENTS__ASR__MODEL_PATH="/opt/vosk/models/ru"
export IRENE_COMPONENTS__ASR__CONFIDENCE_THRESHOLD=0.8

# Веб-сервер
export IRENE_COMPONENTS__WEB_API__MAX_AUDIO_SIZE=50MB
export IRENE_COMPONENTS__LLM__PROVIDER=anthropic
export IRENE_COMPONENTS__LLM__MODEL=claude-3-haiku
```

**Пример использования (Python)**:
```python
import requests
import json

# Отправка аудиофайла
with open("audio.wav", "rb") as audio_file:
    response = requests.post(
        "http://localhost:8000/audio/process",
        files={"audio": audio_file},
        data={"enhance": True, "language": "ru"}
    )
    
result = response.json()
print(f"Оригинал: {result['original_text']}")
print(f"Улучшено: {result['enhanced_text']}")
print(f"Уверенность: {result['confidence']}")
```

**Пример использования (JavaScript)**:
```javascript
// WebSocket потоковое распознавание
const ws = new WebSocket('ws://localhost:8000/audio/stream');

ws.onmessage = function(event) {
    const result = JSON.parse(event.data);
    if (result.type === 'recognition_result') {
        console.log('Распознано:', result.enhanced_text);
        console.log('Уверенность:', result.confidence);
    }
};

// Отправка аудиочанка
function sendAudioChunk(audioBlob) {
    const reader = new FileReader();
    reader.onload = function() {
        const base64 = btoa(reader.result);
        ws.send(JSON.stringify({
            type: 'audio_chunk',
            data: base64,
            format: 'wav',
            sample_rate: 16000
        }));
    };
    reader.readAsBinaryString(audioBlob);
}
```

---

## 🔧 Детальная конфигурация компонентов

### **Микрофон (Speech Recognition)**

**Зависимости**: `vosk`, `sounddevice`, `soundfile`

```toml
[components.microphone]
model_path = "./model"           # Путь к модели VOSK
device_id = -1                   # ID аудиоустройства (-1 = по умолчанию)
sample_rate = 16000              # Частота дискретизации
block_size = 8000                # Размер блока аудио
channels = 1                     # Количество каналов
```

**Модели VOSK**:
- Скачайте модель с https://alphacephei.com/vosk/models
- Распакуйте в папку `./model/` или укажите путь в `model_path`

### **TTS (Text-to-Speech)**

#### **pyttsx3 (Системный TTS)**
```toml
[plugins.pyttsx_tts]
enabled = true
voice_id = "russian"             # ID голоса
voice_rate = 200                 # Скорость речи
voice_volume = 0.9               # Громкость (0.0-1.0)
```

#### **Silero TTS (Нейронный TTS)**
```toml
[plugins.silero_v3_tts]
enabled = true
model_path = "~/.cache/irene/models/silero"  # Кэш моделей
speaker_id = "xenia"             # Голос: aidar, baya, kseniya, xenia
sample_rate = 48000              # Качество аудио
torch_device = "cpu"             # "cpu" или "cuda"

[plugins.silero_v4_tts]
enabled = true
model_path = "~/.cache/irene/models/silero_v4"
speaker_id = "xenia"
```

### **Аудио вывод**

#### **SoundDevice (Рекомендуется)**
```toml
[plugins.sounddevice_audio]
enabled = true
device_id = -1                   # ID устройства воспроизведения
sample_rate = 44100              # Частота воспроизведения
channels = 2                     # Стерео
```

#### **AudioPlayer (Кроссплатформенный)**
```toml
[plugins.audioplayer_audio]
enabled = true
volume = 0.8                     # Громкость
```

#### **ALSA (Linux)**
```toml
[plugins.aplay_audio]
enabled = true
device = "default"               # ALSA устройство
```

### **Веб-сервер**

```toml
[components.web_api]
host = "0.0.0.0"                 # Адрес привязки
port = 8000                      # Порт
cors_origins = ["*"]             # CORS домены
enable_docs = true               # Swagger документация
ssl_cert = ""                    # Путь к SSL сертификату
ssl_key = ""                     # Путь к SSL ключу
```

---

## 📦 Установка зависимостей

### **Группы зависимостей**

```bash
# Только базовая функциональность
uv add irene-voice-assistant

# Текстовый режим
uv add irene-voice-assistant[headless]

# Веб API
uv add irene-voice-assistant[api]

# Голосовой ввод
uv add irene-voice-assistant[audio-input]

# TTS вывод
uv add irene-voice-assistant[tts]

# Аудио вывод
uv add irene-voice-assistant[audio-output]

# Полный голосовой ассистент
uv add irene-voice-assistant[voice]

# Все компоненты
uv add irene-voice-assistant[all]
```

### **Проверка зависимостей**

```bash
# Проверить доступность компонентов
python -m irene.runners.cli --check-deps

# Показать статус компонентов
python -c "from irene.utils.loader import get_component_status; print(get_component_status())"
```

---

## 🚀 Запуск различных режимов

### **Командная строка**
```bash
# Интерактивный режим
python -m irene.runners.cli

# Одна команда
python -m irene.runners.cli --single "привет"

# С проверкой зависимостей
python -m irene.runners.cli --check-deps
```

### **Голосовой ввод (VOSK)**
```bash
# Запуск с голосовым вводом
python -m irene.runners.vosk

# С указанием устройства
python -m irene.runners.vosk --device-id 1

# С указанием модели
python -m irene.runners.vosk --model-path /path/to/vosk/model
```

### **Веб-сервер**
```bash
# Запуск веб-сервера
python -m irene.runners.webapi

# На определенном порту
python -m irene.runners.webapi --port 9000

# С отладкой
python -m irene.runners.webapi --reload --debug
```

### **Настройки (Gradio)**
```bash
# Веб-интерфейс настроек
python -m irene.runners.settings_manager

# На определенном порту
python -m irene.runners.settings_manager --port 7860
```

---

## 📁 Структура конфигурации

### **Расположение файлов**
```
~/.config/irene/config.toml      # Пользовательская конфигурация
./config.toml                    # Конфигурация проекта
/etc/irene/config.toml           # Системная конфигурация (Linux)
```

### **Приоритет конфигураций**
1. Переменные окружения (`IRENE_*`)
2. `./config.toml` (текущая папка)
3. `~/.config/irene/config.toml` (пользователь)
4. `/etc/irene/config.toml` (система)
5. Настройки по умолчанию

### **Создание конфигурации**
```bash
# Создать конфигурацию по умолчанию
python -c "from irene.config.manager import ConfigManager; ConfigManager().create_default_config('./config.toml')"
```

---

## 🔧 Переменные окружения

Все настройки можно переопределить через переменные окружения:

```bash
# Компоненты
export IRENE_COMPONENTS__MICROPHONE=true
export IRENE_COMPONENTS__TTS=true
export IRENE_COMPONENTS__WEB_API__PORT=9000

# Плагины
export IRENE_PLUGINS__GREETINGS__ENABLED=true
export IRENE_PLUGINS__SILERO_V3_TTS__SPEAKER_ID=aidar

# Пути
export IRENE_COMPONENTS__MICROPHONE__MODEL_PATH=/opt/vosk/model
```

---

## 🐛 Отладка и диагностика

### **Проверка системы**
```bash
# Проверить все компоненты
python -m irene.runners.cli --check-deps

# Протестировать приветствие
python -m irene.runners.cli --single "привет"

# Проверить аудио устройства
python -c "from irene.utils.audio_helpers import list_audio_devices; list_audio_devices()"
```

### **Логирование**
```toml
[logging]
level = "INFO"                   # DEBUG, INFO, WARNING, ERROR
format = "detailed"              # simple, detailed
file = "irene.log"               # Файл логов
```

### **Типичные проблемы**

1. **Микрофон не работает**:
   - Проверьте права доступа к микрофону
   - Убедитесь, что модель VOSK установлена
   - Проверьте ID аудиоустройства

2. **TTS не работает**:
   - Установите `pyttsx3` для базового TTS
   - Для Silero проверьте наличие `torch`
   - Проверьте права на запись в кэш моделей

3. **Веб-сервер недоступен**:
   - Проверьте, что порт не занят
   - Убедитесь, что `fastapi` и `uvicorn` установлены
   - Проверьте настройки брандмауэра

---

## 📖 Примеры полных конфигураций

### **Домашний ассистент**
```toml
[components]
microphone = true
tts = true
audio_output = true
web_api = true

[components.microphone]
model_path = "/opt/vosk/model-ru"
device_id = 0

[components.web_api]
host = "0.0.0.0"
port = 8000

[plugins.core_commands]
enabled = true

[plugins.greetings]
enabled = true

[plugins.datetime]
enabled = true

[plugins.async_timer]
enabled = true

[plugins.silero_v3_tts]
enabled = true
speaker_id = "xenia"

[plugins.sounddevice_audio]
enabled = true
```

### **Сервер для разработки**
```toml
[components]
microphone = false
tts = false
audio_output = false
web_api = true

[components.web_api]
host = "127.0.0.1"
port = 8000
enable_docs = true

[plugins.core_commands]
enabled = true

[plugins.greetings]
enabled = true

[logging]
level = "DEBUG"
```

### **Облачная установка**
```toml
[components]
microphone = false
tts = false
audio_output = false
web_api = true

[components.web_api]
host = "0.0.0.0"
port = 8000
cors_origins = ["https://mydomain.com"]

[plugins.core_commands]
enabled = true
```

---

## 📞 Поддержка и помощь

- **Документация**: Проверьте `docs/` в репозитории
- **Примеры**: Смотрите `irene/examples/`
- **Проблемы**: Создайте issue в GitHub репозитории
- **Миграция с v12**: Используйте `tools/migrate_*.py`

---

*Этот документ описывает систему Irene Voice Assistant v13 с модульной архитектурой и асинхронной обработкой команд.* 