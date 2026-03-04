#!/bin/sh
set -e

# Выполняем миграции
python manage.py migrate --noinput

# Собираем статику
python manage.py collectstatic --noinput --clear --settings=foodgram_backend.settings

# Создаём целевую директорию в volume, если её нет
echo "Creating /backend_static..."
if mkdir -p /backend_static; then
  echo "Folder created successfully"
else
  echo "Error: Failed to create folder /backend_static"
  exit 1
fi

# Очищаем целевую директорию от старых файлов (чтобы избежать дублирования)
echo "Erase /backend_static..."
rm -rf /backend_static/*

# Копируем статические файлы в volume
echo "Copying /app/collected_static/ to /backend_static..."
cp -a /app/collected_static/. /backend_static/

exec "$@"