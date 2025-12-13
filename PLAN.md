# План разработки Campaign Manager для Keitaro

## Архитектура проекта

Используем **стандартную Django структуру** с разделением на Django приложения:

```
itseasy_campaign_manager/
├── app/
│   ├── manage.py
│   ├── config/              # Основная папка проекта (settings, urls, wsgi)
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── users/               # Django app для пользователей
│   │   ├── models.py        # User модель
│   │   ├── views.py         # LoginView
│   │   ├── middleware.py    # AuthMiddleware
│   │   ├── urls.py
│   │   └── admin.py
│   ├── campaigns/           # Django app для кампаний
│   │   ├── models.py        # Campaign, Flow, Offer, FlowOffer
│   │   ├── views.py         # List, Detail views
│   │   ├── services.py      # ShareCalculator, KeitaroClient, SyncService
│   │   ├── forms.py
│   │   ├── urls.py
│   │   └── admin.py
│   ├── templates/           # Общие шаблоны
│   │   ├── base.html
│   │   ├── users/           # Шаблоны авторизации
│   │   └── campaigns/       # Шаблоны кампаний
│   └── static/              # Статика (CSS, JS)
│       ├── css/
│       └── js/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## Этап 1: Базовая инфраструктура

### 1.1 Docker и окружение
- Создать `docker-compose.yml` с двумя сервисами: web (Django) и db (PostgreSQL)
- Создать `Dockerfile` для Django приложения
- Настроить `.env.example` с переменными: `POSTGRES_*`, `KEITARO_URL`, `SECRET_KEY`, `DEBUG`
- Обновить `requirements.txt` (Django 5, psycopg2-binary, requests, python-dotenv)

### 1.2 Django проект
- Создать Django проект с основной папкой `config`
- Настроить `config/settings.py` для работы с PostgreSQL и переменными окружения
- Настроить базовый `config/urls.py`

## Этап 2: Django приложения

### 2.1 Users app (`app/users/`)

Создать Django app `users` для управления пользователями.

**Модель User** (`users/models.py`) - кастомная модель:
- Наследуется от `AbstractBaseUser`
- `api_key` (CharField, unique) - API ключ Keitaro (используется как username)
- `last_page` (CharField, nullable) - последняя посещённая страница
- `is_active`, `is_staff`, `is_superuser` - стандартные флаги
- Без пароля, только API-key аутентификация

**Views** (`users/views.py`):
- `LoginView` - форма ввода API ключа, валидация через Keitaro, создание/получение User
- `LogoutView` - очистка session

**Middleware** (`users/middleware.py`):
- `AuthMiddleware` - проверка user_id в session, редирект на login

### 2.2 Campaigns app (`app/campaigns/`)

Создать Django app `campaigns` для работы с кампаниями, потоками и офферами.

**Модели** (`campaigns/models.py`)

**Campaign**:
- `keitaro_id` (IntegerField, unique) - ID в Keitaro
- `name`, `alias`, `state`, `type`
- `user` (ForeignKey to User)
- `synced_at` (DateTimeField) - время последней синхронизации

**Flow** (поток):
- `keitaro_id` (IntegerField)
- `campaign` (ForeignKey to Campaign)
- `name`, `position`, `state`
- `synced_at` (DateTimeField)
- Уникальный constraint на (campaign, keitaro_id)

**Offer** (кэшированные офферы):
- `keitaro_id` (IntegerField, unique)
- `name`, `state`
- `user` (ForeignKey to User)
- `cached_at` (DateTimeField)

**FlowOffer** (связь потока и оффера):
- `flow` (ForeignKey to Flow)
- `offer` (ForeignKey to Offer)
- `share` (IntegerField) - процент распределения (0-100)
- `is_pinned` (BooleanField) - зафиксирован ли share
- `state` (CharField) - active/disabled
- `keitaro_offer_stream_id` (IntegerField, nullable) - ID связи в Keitaro

**Сервисы** (`campaigns/services.py`):

Все вспомогательные классы в одном файле:

**Класс `ShareCalculator`**:
- `recalculate_shares(flow, pinned_offers)` - пересчёт share по правилам
- `validate_shares(flow_offers)` - валидация (сумма = 100%, минимум 1%)

**Класс `KeitaroClient`**:
- `__init__(base_url, api_key)` - инициализация
- `get_campaigns()` - GET /admin_api/v1/campaigns
- `get_campaign(campaign_id)` - GET /admin_api/v1/campaigns/{id}
- `get_streams(campaign_id)` - GET /admin_api/v1/campaigns/{id}/streams
- `update_stream(stream_id, data)` - PUT /admin_api/v1/streams/{id}
- `get_offers()` - GET /admin_api/v1/offers
- `get_report(params)` - POST /admin_api/v1/report/build
- Обработка ошибок (401, 404, 500)

**Класс `KeitaroSyncService`**:
- `sync_campaigns(user)` - синхронизация кампаний
- `sync_streams(campaign)` - синхронизация потоков
- `sync_offers(user)` - синхронизация офферов (кэш)
- `push_stream_offers(flow)` - отправка изменений в Keitaro
- `compare_with_keitaro(flow)` - сравнение данных

**Views** (`campaigns/views.py`):

**Класс `CampaignListView`** (ListView):
- Получение списка кампаний пользователя из БД
- Асинхронный запрос статистики через AJAX endpoint
- Таблица со столбцами: ID, Название (ссылка), Источник, Потоки, Клики, Конверсия, CR, Доход, Расход, Прибыль, ROI

**Класс `CampaignStatsAPIView`** (View):
- AJAX endpoint для статистики из Keitaro
- Возвращает JSON с метриками

**Класс `CampaignDetailView`** (DetailView):
- Отображение потоков кампании с офферами
- Кнопки: "Fetch streams from Keitaro", "View in Keitaro"
- При загрузке: показать БД данные + асинхронно проверить расхождения с Keitaro

**Класс `FetchStreamsView`** (View):
- AJAX endpoint для синхронизации потоков
- Вызывает `KeitaroSyncService.sync_streams()`

**Класс `CheckSyncView`** (View):
- AJAX endpoint для проверки расхождений
- Возвращает JSON о несоответствиях

**Класс `AddOfferView`** (View):
- AJAX endpoint для добавления оффера в поток
- Пересчёт share через `ShareCalculator`
- Возвращает обновлённый HTML фрагмент таблицы

**Класс `RemoveOfferView`** (View):
- AJAX endpoint для удаления оффера
- Пересчёт share

**Класс `UpdateShareView`** (View):
- AJAX endpoint для изменения share
- Валидация через `ShareCalculator`

**Класс `PushToKeitaroView`** (View):
- AJAX endpoint для отправки в Keitaro
- Вызывает `KeitaroSyncService.push_stream_offers()`

**Класс `OfferAutocompleteView`** (View):
- AJAX endpoint для автодополнения
- Поиск по кэшу офферов

## Этап 3: Фронтенд

### 3.1 Templates (`app/templates/`)
- `base.html` - базовый шаблон (Tailwind CSS CDN + jQuery CDN)
- `users/login.html` - страница авторизации
- `campaigns/campaign_list.html` - список кампаний
- `campaigns/campaign_detail.html` - детали кампании с потоками
- `campaigns/_flow_table.html` - partial для таблицы потока

### 3.2 JavaScript (`app/static/js/`)

**`campaign_detail.js`**:
- Управление состоянием редактирования потока (бежевый фон при изменениях)
- AJAX запросы для добавления/удаления офферов
- Автодополнение офферов (jQuery autocomplete)
- Обработка кнопок "Push to Keitaro" и "Cancel"
- Визуальные индикаторы (зелёный/красный текст, bold)
- Валидация share в реальном времени

**`campaign_list.js`**:
- Асинхронная загрузка статистики кампаний
- Обновление таблицы после получения данных

### 3.3 Стили (Tailwind CSS)
- Используем CDN Tailwind для быстрой разработки
- Кастомные utility-классы в `app/static/css/custom.css`:
  - Бежевый фон редактируемых потоков
  - Зелёный/красный текст для изменений
  - Состояния валидации

## Этап 4: Admin панель

Настроить Django Admin в `users/admin.py` и `campaigns/admin.py`:
- Class-based `ModelAdmin` для всех моделей
- Readonly поля: `keitaro_id`, `synced_at`, `cached_at`
- Фильтры по `user`, `state`, `campaign`
- Поиск по `name`, `alias`

## Этап 5: Технические детали

**База данных:**
- PostgreSQL 15
- Индексы на keitaro_id, user_id, synced_at
- Constraint на сумму share в FlowOffer (проверка на уровне приложения)

**API аутентификация:**
- Без JWT/Token, простая session на основе cookie
- Middleware проверяет user_id в session

**Синхронизация:**
- При просмотре страницы: показываем БД + асинхронно проверяем Keitaro
- При клике "Fetch": принудительная синхронизация
- При "Push to Keitaro": отправка только изменённых потоков

**Кэширование офферов:**
- Обновление при фокусе на поле автодополнения (фоновый запрос)
- Поиск по кэшу выполняется мгновенно

**Обработка ошибок:**
- Keitaro недоступен: показываем toast с сообщением
- Неверный API ключ: очищаем session, редирект на login
- Валидация share: блокируем кнопку "Push" до исправления

## Приоритет реализации

1. **Базовая инфраструктура** - Docker, Django, PostgreSQL
2. **Модели и миграции** - создать все модели
3. **Keitaro клиент** - базовые методы API
4. **Аутентификация** - страница входа по API ключу
5. **Список кампаний** - главная страница (пока без статистики)
6. **Детали кампании** - отображение потоков
7. **Синхронизация** - Fetch streams from Keitaro
8. **Редактирование офферов** - добавление, удаление, share
9. **Push to Keitaro** - отправка изменений
10. **Статистика** - интеграция с report/build
11. **Полировка UI** - все визуальные индикаторы и валидации

## Keitaro API Reference

**Base URL:** `{KEITARO_URL}/admin_api/v1`
**Authentication:** Header `Api-Key: {api_key}`

**Основные endpoints:**
- `GET /campaigns` - список кампаний
- `GET /campaigns/{id}` - детали кампании
- `GET /campaigns/{id}/streams` - потоки кампании
- `GET /streams/{id}` - детали потока
- `PUT /streams/{id}` - обновление потока (включая offers)
- `GET /offers` - список офферов
- `POST /report/build` - построение отчёта со статистикой

**Структура Stream.offers (OfferStream):**
```json
{
  "id": 123,
  "stream_id": 456,
  "offer_id": 789,
  "share": 50,
  "state": "active"
}
```

