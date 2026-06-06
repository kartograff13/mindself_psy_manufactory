# Mindself Psy Manufactory

Платформа для психологического самообучения. Предоставляет возможность авторизации, управления разделами и учебными материалами, прохождения тестирования, записи на консультации, а также личный кабинет пользователя.

## Технологический стек

- **Python 3.14**
- **Django 6.0** + **Django Rest Framework 3.17**
- **PostgreSQL 18**
- **JWT** (djangorestframework-simplejwt)
- **Swagger/OpenAPI** (drf-spectacular)
- **CORS** (django-cors-headers)
- **django-phonenumber-field** (валидация телефонов)
- **Pillow** (работа с изображениями)
- **Bootstrap 5** (статическая загрузка CSS/JS)
- **Vanilla JavaScript** (Fetch API, работа с JWT)
- **pytest** + **pytest-cov** - для тестирования
- **flake8, black, isort, mypy** - для качества кода

## Структура проекта

```
mindself_psy_manufactory/
├── config/ # Настройки Django (settings, urls, wsgi, asgi)
├── users/ # Приложение пользователей
│ ├── models.py # Кастомная модель User (роль, телефон, аватар, био)
│ ├── serializers.py # RegisterSerializer, UserProfileSerializer, ChangePasswordSerializer
│ ├── views.py # RegisterView, ProfileView, ChangePasswordView, JWT-вьюхи
│ └── urls.py # Маршруты auth/register, token, profile, change-password
├── courses/ # Приложение курсов
│ ├── models.py # Course, Lesson, Attachment, Test, Question, Choice,
│ │ # StudentTestAttempt, Enrollment
│ ├── serializers.py # Сериализаторы для всех моделей
│ ├── permissions.py # IsOwnerOrAdmin, IsEnrolledOrAdmin
│ ├── views.py # ViewSets для курсов, уроков, тестов, вложений, записей
│ └── urls.py # Роутеры для api/ и api/teacher/
├── consultations/ # Приложение консультаций
│ ├── models.py # ConsultationService, ConsultationRequest
│ ├── serializers.py # Сериализаторы для услуг и заявок
│ ├── views.py # ViewSets для услуг и заявок (с email-уведомлением)
│ └── urls.py # Роутеры для api/services и api/requests
├── templates/ # HTML-шаблоны
│ ├── base.html # Базовый шаблон с навигацией и Bootstrap
│ ├── index.html # Главная страница (лендинг)
│ ├── login.html # Страница входа
│ ├── register.html # Страница регистрации
│ ├── courses_list.html # Список курсов
│ ├── course_detail.html # Детали курса + запись
│ ├── lesson_detail.html # Урок + вложения + прохождение теста
│ ├── consultations_list.html # Услуги консультаций + форма заявки
│ └── profile.html # Личный кабинет + смена пароля
├── static/ # Статические файлы
│ ├── css/
│ │ ├── bootstrap.min.css
│ │ └── custom.css
│ └── js/
│ ├── bootstrap.bundle.min.js
│ └── api.js # Общие функции (пока пустой)
├── tests/ # Тесты pytest
│ ├── conftest.py # Фикстуры (пользователи, курс, урок, тест)
│ ├── test_api.py # Тесты API (курсы, уроки, тесты, записи, права)
│ ├── test_consultations.py # Тесты заявок на консультации
│ └── test_profile.py # Тесты профиля и смены пароля
├── media/ # Загружаемые файлы (аватары, видео, вложения)
├── ban_words.txt.sample # Пример списка запрещённых имён пользователей
├── .env.sample # Пример переменных окружения
├── pytest.ini # Конфигурация pytest
├── pyproject.toml # Настройки black, isort, mypy
├── .flake8 # Настройки flake8
├── .gitignore
├── requirements.txt # Зависимости
└── README.md
```

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
python manage.py runserver
```

Сервер будет доступен по адресу http://127.0.0.1:8000/.

## Документация API

Swagger UI доступен по адресу:
http://127.0.0.1:8000/api/docs/

Здесь представлены все эндпоинты с описанием и возможностью выполнения запросов.

## Тестирование

Для запуска тестов с оценкой покрытия:

```
pytest --cov=. --cov-report=term-missing
```

Покрытие кода составляет >85%.

## Роли пользователей

- **Клиент (client)** — роль по умолчанию. Может просматривать опубликованные курсы, записываться на курс (покупка) и проходить тесты после записи, оставлять заявки на консультации, редактировать свой профиль.
- **Преподаватель (teacher)** — может создавать и управлять своими курсами, уроками, тестами, просматривать записи студентов на свои курсы, а также управлять заявками на консультации.
- **Администратор (admin)** — полный доступ ко всем функциям платформы.

## Основные эндпоинты API

### Аутентификация

- **POST /api/auth/register/** — регистрация
- **POST /api/auth/token/** — получение JWT
- **POST /api/auth/token/refresh/** — обновление access-токена
- **GET /api/auth/profile/** — получить профиль
- **PATCH /api/auth/profile/** — обновить профиль
- **POST /api/auth/profile/change-password/** — смена пароля

### Курсы

- **GET /api/courses/** — список курсов (фильтруется по роли)
- **POST /api/courses/** — создание курса (только преподаватель)
- **GET /api/courses/{id}/** — детали курса
- **PATCH /api/courses/{id}/** — обновление курса
- **DELETE /api/courses/{id}/** — удаление курса

### Уроки и вложения (чтение – только студенты, записанные на курс)

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

### Консультации (заявки)

- **GET /api/services/** — список услуг консультаций (доступно всем)
- **GET /api/services/{id}/** — детали услуги
- **POST /api/requests/** — оставить заявку на консультацию (можно анонимно; авторизованным данные подставляются из профиля)
- **GET /api/requests/** — список заявок (психолог видит все, клиент – только свои)
- **GET /api/requests/{id}/** — детали заявки (психолог/админ)
- **PATCH /api/requests/{id}/** — обновить статус заявки (психолог/админ)

#### Управление услугами (только администратор):

- POST /api/services/ — создать услугу
- PUT /api/services/{id}/ — обновить услугу
- DELETE /api/services/{id}/ — удалить услугу

### ***Фронтенд (для демонстрации)***

***Реализован клиентский интерфейс на базе Bootstrap 5 (статическая загрузка CSS/JS) и чистого JavaScript (Fetch API).
JWT-токены сохраняются в localStorage и передаются в заголовке Authorization при каждом запросе.***

Страницы:

- **/** — лендинг с описанием платформы.
- **/login/** — вход в систему.
- **/register/** — регистрация.
- **/courses/** — список опубликованных курсов.
- **/courses/{id}/** — детали курса, список уроков, кнопка записи.
- **/lessons/{id}/** — урок с контентом, видео, вложениями и формой теста (если есть).
- **/consultations/** — список услуг и форма заявки на консультацию.
- **/profile/** — личный кабинет: редактирование профиля и смена пароля.
- **/admin/** — панель администратора Django (для управления контентом).

***Навигация адаптируется под авторизацию: гость видит «Войти», авторизованный пользователь — «Профиль» и «Выйти».***

### Разработка
#### Для поддержания качества кода используется:

- **flake8** и **black** (настройки в ***.flake8*** и ***pyproject.toml***)
- **isort** для сортировки импортов
- **mypy** + **django-stubs** для проверки типов
- Тесты с **pytest** и обязательным покрытием >85%
- Все статические файлы фронтенда включены в репозиторий

###### © 2026 Mindself Psy Manufactory
