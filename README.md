# Mindself Psy Manufactory

Платформа для психологического самообучения. Предоставляет возможность авторизации, управления разделами и учебными материалами, прохождения тестирования, а также записи на онлайн/офлайн консультации.

## Технологический стек

- **Python 3.14**
- **Django 6.0** + **Django Rest Framework 3.17**
- **PostgreSQL 18**
- **JWT** (djangorestframework-simplejwt)
- **Swagger/OpenAPI** (drf-spectacular)
- **CORS** (django-cors-headers)
- **pytest** + **pytest-cov** для тестирования и оценки покрытия
- **flake8, black, isort, mypy** для соблюдения PEP8 и типизации

## Установка и запуск

### 1. Клонирование репозитория

```
git clone https://github.com/kartograff13/mindself_psy_manufactory.git
cd mindself_psy_manufactory
```

### 2. Настройка виртуального окружения

```
python3.14 -m venv venv
source venv/bin/activate      # для Linux/MacOS
venv\Scripts\activate         # для Windows
pip install -r requirements.txt
```

### 3. Переменные окружения

Создайте файл .env в корне проекта (можно скопировать из .env.sample) и укажите свои значения:

```
SECRET_KEY=ваш_секретный_ключ
DEBUG=True

DB_NAME=mindself_db
DB_USER=mindself_user
DB_PASSWORD=ваш_пароль
DB_HOST=localhost
DB_PORT=5432

BAN_WORDS_FILE=ban_words.txt
```

### 4. База данных

Убедитесь, что PostgreSQL запущен, и создайте базу данных с пользователем из .env.
Затем выполните миграции:

```
python manage.py makemigrations
python manage.py migrate
```

### 5. Создание суперпользователя

```
python manage.py createsuperuser
```

### 6. Запуск сервера

```
python manage.py createsuperuser
```

Сервер будет доступен по адресу http://127.0.0.1:8000/.

## Документация API

После запуска сервера откройте Swagger UI:
http://127.0.0.1:8000/api/docs/

Здесь представлены все эндпоинты с описанием и возможностью выполнения запросов.

## Тестирование

Для запуска тестов с оценкой покрытия:

```
pytest --cov=. --cov-report=term-missing
```

Покрытие кода составляет >80%.

## Роли пользователей

- **Клиент (client)** — роль по умолчанию. Может просматривать опубликованные курсы, записываться на курс (покупка) и проходить тесты после записи, а также записываться на консультации (будет расширено).
- **Преподаватель (teacher)** — может создавать и управлять своими курсами, уроками, тестами, просматривать записи студентов на свои курсы.
- **Администратор (admin)** — полный доступ ко всем функциям платформы.

## Основные эндпоинты API
### Аутентификация

- **POST /api/auth/register/** — регистрация нового пользователя (роль client)
- **POST /api/auth/token/** — получение JWT (access + refresh)
- **POST /api/auth/token/refresh/** — обновление access-токена

### Курсы

- **GET /api/courses/** — список курсов (фильтруется по роли)
- **POST /api/courses/** — создание курса (только преподаватель)
- **GET /api/courses/{id}/** — детали курса
- **PATCH /api/courses/{id}/** — обновление курса
- **DELETE /api/courses/{id}/** — удаление курса

### Уроки и вложения

- **GET /api/lessons/** — список доступных уроков
- **GET /api/lessons/{id}/** — детали урока с вложениями
- **GET /api/attachments/{id}/** — получение вложения

#### Управление уроками и вложениями для преподавателей:

- **POST /api/teacher/lessons/** — создать урок
- **PUT /api/teacher/lessons/{id}/** — обновить урок
- **DELETE /api/teacher/lessons/{id}/** — удалить урок
- **POST /api/teacher/attachments/** — загрузить файл к уроку
- **PUT /api/teacher/attachments/{id}/** — обновить вложение
- **DELETE /api/teacher/attachments/{id}/** — удалить вложение

### Тесты

- **GET /api/tests/** — список доступных тестов
- **GET /api/tests/{id}/** — детали теста
- **POST /api/tests/{id}/submit/** — отправка ответов на тест (студент)

#### Управление тестами для преподавателей:

- **POST /api/teacher/tests/** — создать тест с вопросами и вариантами ответов
- **PUT /api/teacher/tests/{id}/** — обновить тест
- **DELETE /api/teacher/tests/{id}/** — удалить тест

### Записи на курс (Enrollments)

- **GET /api/enrollments/** — список записей (фильтруется по роли)
- **POST /api/enrollments/** — записаться на опубликованный курс
- **DELETE /api/enrollments/{id}/** — отчислиться / отчислить студента

### Разработка
#### Для поддержания качества кода используется:

- **flake8** и **black** (настройки в .flake8 и pyproject.toml)
- **isort** для сортировки импортов
- **mypy** + **django-stubs** для проверки типов
- Тесты с **pytest** и обязательным покрытием >80%
