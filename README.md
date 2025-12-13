# Campaign Manager для Keitaro

Веб-приложение для управления распределением офферов по потокам рекламных кампаний в Keitaro.

## Технологии

- Django 5.1
- PostgreSQL 15
- Docker & Docker Compose
- Tailwind CSS
- jQuery

## Быстрый старт

1. Скопируйте `.env.example` в `.env` и настройте переменные окружения:
```bash
cp .env.example .env
```

2. Отредактируйте `.env` и укажите:
   - `SECRET_KEY` - секретный ключ Django
   - `KEITARO_URL` - URL вашего Keitaro инстанса

3. Запустите проект:
```bash
docker-compose up -d
```

4. Примените миграции:
```bash
docker-compose exec web python app/manage.py migrate
```

5. Создайте суперпользователя (опционально):
```bash
docker-compose exec web python app/manage.py createsuperuser
```

6. Откройте в браузере: http://localhost:8000

## Структура проекта

```
itseasy_campaign_manager/
├── app/
│   ├── manage.py
│   ├── config/          # Настройки Django
│   ├── users/           # Приложение пользователей
│   ├── campaigns/       # Приложение кампаний
│   ├── templates/       # HTML шаблоны
│   └── static/          # CSS, JS, изображения
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── PLAN.md             # Детальный план разработки
└── README.md
```

## Разработка

Посмотреть логи:
```bash
docker-compose logs -f web
```

Остановить контейнеры:
```bash
docker-compose down
```

Пересобрать после изменения requirements.txt:
```bash
docker-compose up -d --build
```

## Подробности

См. [PLAN.md](PLAN.md) для детального плана разработки и архитектуры проекта.

