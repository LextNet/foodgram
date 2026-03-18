
# Описание проекта

Foodgram — это веб-приложение, на котором пользователи будут публиковать свои рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. 
Зарегистрированным пользователям также будет доступен сервис «Список покупок». Он позволит создавать список продуктов, которые нужно купить для приготовления выбранных блюд..

# Технологический стек

Фронтенд — это одностраничное SPA-приложение, написанное на фреймворке React
Бэкенд - это REST API, написанное с помощью следующих компонентов, библиотек: 
Python 3.12.7
Django==5.1.1
Django REST Framework 3.15.2
SQLite
Djoser для аутентификации
Django Filter для фильтрации данных

Проект запускается в четырёх контейнерах — nginx, PostgreSQL, backend и frontend через docker-compose.
Данные сохраняются в volumes.
Образы проекта помещены в облачное хранилище образов.
Настроен автоматический деплой с использованием CI/CD через GitHub Actions.
Проект доступен по доменному имени https://foodgram-final.sytes.net

# Установка и запуск

1. Клонирование репозитория
git clone https://github.com/LextNet/foodgram.git
cd foodgram

2. Настройка переменных окружения
Создайте файл .env в корневой директории проекта:

# Файл .env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=postgres
# Добавляем переменные для Django-проекта:
DB_NAME=postgres
DB_HOST=db
DB_PORT=5432

DEBUG=True
SECRET_KEY=ваш-секретный-ключ
ALLOWED_HOSTS=ip адрес сервера,127.0.0.1,localhost,доменное имя сервера
CSRF_TRUSTED_ORIGINS=https://доменное имя,http://доменное имя

3. Находясь в папке infra (cd infra) запустите docker compose up --build
Будет выполнена сборка образов и запуск контейнеров проекта.

4. Создание суперпользователя
bash
Необходимо находясь в контейнере проекта backend создать суперпользователя:
docker exec -it foodgram-backend bash
python3 manage.py createsuperuser

# Приложение будет доступно по адресу: http://127.0.0.1

# Документация API
После запуска сервера спецификация API будет доступна по следующему адресу:
ReDoc: http://localhost/api/docs/

Админка будет доступна по адресу:
http://localhost/admin/

Адрес сервера на котором запущен foodgram: https://foodgram-final.sytes.net
