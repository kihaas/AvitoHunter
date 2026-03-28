FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей (для selenium, если используется)
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium-driver \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Переменные окружения по умолчанию
ENV TELEGRAM_BOT_TOKEN="" \
    TELEGRAM_CHAT_ID="" \
    CHECK_INTERVAL_SECONDS=60 \
    AVITO_SEARCH_URLS="" \
    LOG_LEVEL=INFO

CMD ["python", "main.py"]