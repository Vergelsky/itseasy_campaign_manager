#!/bin/bash
set -e

echo "Применение миграций..."
python app/manage.py migrate --noinput

echo "Запуск сервера..."
exec "$@"

