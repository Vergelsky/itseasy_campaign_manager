FROM python:3.11-slim

# Отключение буферизации Python и создание .pyc файлов
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /code

# Копирование и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Копирование и настройка entrypoint скрипта
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Создание директорий для статики и медиа
RUN mkdir -p app/static app/media

# Порт приложения
EXPOSE 8000

# Установка entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Команда запуска будет в docker-compose.yml

