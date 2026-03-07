#!/bin/sh
set -e

# Выполняем миграции
python manage.py migrate --noinput

# Собираем статику
python manage.py collectstatic --noinput --clear --settings=foodgram_backend.settings

# Создаём целевую директорию в volume, если её нет
mkdir -p /backend_static

# Копируем статические файлы в volume
cp -r /app/collected_static/. /backend_static/

exec "$@"