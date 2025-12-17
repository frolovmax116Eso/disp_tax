# Telegram Dispatcher Platform

Платформа для диспетчеров такси для управления заказами через Telegram.

## Описание

Система позволяет диспетчерам:
- Создавать и управлять заказами
- Отправлять заказы в группы водителей
- Обрабатывать ответы водителей
- Назначать водителей на заказы
- Управлять группами и регионами

## Установка

1. Клонируйте репозиторий
2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Скопируйте `.env.example` в `.env` и заполните:
```bash
cp .env.example .env
```

5. Заполните `.env`:
- `BOT_TOKEN` - токен бота от @BotFather
- `API_ID` и `API_HASH` - получите на https://my.telegram.org
- `ADMIN_IDS` - Telegram ID админов (через запятую)

6. Инициализируйте БД:
```bash
alembic upgrade head
```

7. Запустите бота:
```bash
python main.py
```

## Структура проекта

```
disp-tax/
├── src/
│   ├── bot/              # aiogram handlers
│   ├── database/         # SQLAlchemy models
│   ├── services/         # Бизнес-логика
│   ├── telethon_client/  # Telethon client manager
│   └── config.py         # Конфигурация
├── docs/                 # Документация
├── migrations/           # Alembic migrations
├── sessions/             # Telethon sessions
└── main.py              # Точка входа
```

## Документация

См. папку `docs/`:
- `FUNCTIONAL_SPEC.md` - функциональная спецификация
- `ARCHITECTURE.md` - архитектура системы
- `DATA_MODELS.md` - модели данных
- `API.md` - API спецификация
- `roadmap.md` - план разработки

## Разработка

Проект разрабатывается по этапам согласно `roadmap.md`.

## Лицензия

Proprietary

