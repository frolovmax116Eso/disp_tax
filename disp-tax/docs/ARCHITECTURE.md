# ARCHITECTURE
# Telegram Dispatcher Platform

Этот документ описывает архитектуру системы.

---

## Stage 3.1 — Компоненты системы

### Основные компоненты

1. **Telethon Client Manager**
   - Управление пользовательскими сессиями диспетчеров
   - Отправка сообщений в группы от имени диспетчера
   - Мониторинг ответов в группах
   - Обработка FloodWait и rate limits

2. **Telegram Bot (aiogram)**
   - Интерфейс управления для диспетчеров
   - Админ-панель для администраторов
   - Обработка команд и callback-запросов
   - Управление FSM для создания заказов

3. **Database Layer (SQLAlchemy)**
   - Хранение всех данных системы
   - Модели: Dispatcher, Order, DriverResponse, Assignment, Group, Region, Scenario
   - Миграции через Alembic
   - Транзакции и целостность данных

4. **Order FSM Manager**
   - Управление жизненным циклом заказов
   - Валидация переходов между состояниями
   - История изменений состояний

5. **Anti-Ban Service**
   - Расчет задержек между отправками
   - Обработка FloodWait
   - Rate limiting
   - Оценка рисков блокировки

6. **Response Monitor**
   - Мониторинг групп на наличие ответов
   - Парсинг ответов водителей ("я", reply)
   - Сохранение ответов в БД

7. **Admin Panel Service**
   - Проверка прав доступа (whitelist)
   - Агрегация данных для админа
   - Отправка ошибок админу

8. **Logging Service**
   - Структурированное логирование
   - Уровни: info, warning, error, critical
   - Отправка ошибок админу

---

## Stage 3.2 — Взаимодействие между компонентами

### Архитектурная схема

```
┌─────────────────┐
│  Telegram Bot   │ (aiogram)
│   (Control UI)  │
└────────┬────────┘
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
┌─────────────────┐  ┌─────────────────┐
│  FSM Manager    │  │  Database       │
│  (Order Flow)   │──│  (SQLAlchemy)   │
└────────┬────────┘  └─────────────────┘
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
┌─────────────────┐  ┌─────────────────┐
│ Telethon Client │  │  Anti-Ban       │
│   Manager       │──│  Service        │
└────────┬────────┘  └─────────────────┘
         │
         │
         ▼
┌─────────────────┐
│ Response Monitor│
│  (Group Watch)  │
└─────────────────┘
         │
         │
         ▼
┌─────────────────┐
│  Admin Panel    │
│    Service      │
└─────────────────┘
```

### Потоки данных

#### 1. Создание заказа
```
Bot → FSM Manager → Database
     ↓
  Preview → Bot (показ диспетчеру)
     ↓
  Confirmation → FSM Manager → Database
     ↓
  Sending → Anti-Ban Service → Telethon Client → Groups
```

#### 2. Мониторинг ответов
```
Telethon Client (мониторит группы)
     ↓
Response Monitor (парсит ответы)
     ↓
Database (сохраняет ответы)
     ↓
Bot (уведомляет диспетчера)
```

#### 3. Назначение водителя
```
Bot → FSM Manager (проверка прав)
     ↓
Database (получение списка ответов)
     ↓
Bot (показ списка диспетчеру)
     ↓
Confirmation → FSM Manager → Database
     ↓
Telethon Client (отправка "✅ Отдан Вам" в группу)
```

#### 4. Логирование ошибок
```
Any Component → Logging Service
     ↓
Database (сохранение лога)
     ↓
Admin Panel Service (проверка уровня)
     ↓
Bot (отправка админу, если error/critical)
```

### Асинхронная архитектура

Все компоненты работают асинхронно:
- `async/await` для всех I/O операций
- Event loop для обработки событий
- Неблокирующие операции с БД
- Параллельная обработка нескольких диспетчеров

---

## Stage 3.3 — Технологии и стек

### Backend

- **Python 3.10+**
  - Современный синтаксис
  - Поддержка async/await
  - Type hints для надежности

- **Telethon**
  - Пользовательские сессии (диспетчеры)
  - Отправка сообщений в группы
  - Мониторинг групп
  - Обработка FloodWait

- **aiogram 3.x**
  - Telegram Bot API
  - FSM для управления состояниями
  - Inline keyboards
  - Middleware для логирования

### Database

- **SQLAlchemy 2.0+**
  - ORM для работы с БД
  - Async support
  - Миграции через Alembic

- **SQLite** (development)
  - Простота разработки
  - Файловая БД

- **PostgreSQL** (production, опционально)
  - Для production окружения
  - Лучшая производительность
  - Транзакции и целостность

### Configuration

- **python-dotenv**
  - Загрузка переменных окружения
  - Безопасное хранение токенов

- **pydantic + pydantic-settings**
  - Валидация конфигурации
  - Type-safe настройки

### Logging

- **structlog**
  - Структурированное логирование
  - JSON формат для production
  - Контекстное логирование

### Utilities

- **aiofiles**
  - Асинхронная работа с файлами
  - Сохранение сессий

- **aiohttp**
  - HTTP клиент (если понадобится)

- **python-dateutil**
  - Работа с датами и временем

### Структура проекта

```
disp-tax/
├── src/
│   ├── bot/              # aiogram bot handlers
│   │   ├── dispatcher/   # handlers для диспетчеров
│   │   ├── admin/        # handlers для админов
│   │   └── middleware/   # middleware (logging, auth)
│   ├── telethon_client/  # Telethon client manager
│   ├── database/         # SQLAlchemy models
│   ├── fsm/              # FSM для заказов
│   ├── services/         # Бизнес-логика
│   │   ├── order_service.py
│   │   ├── anti_ban.py
│   │   ├── response_monitor.py
│   │   └── admin_service.py
│   ├── utils/            # Утилиты
│   └── config.py         # Конфигурация
├── docs/                 # Документация
├── migrations/           # Alembic migrations
├── sessions/             # Telethon sessions
├── logs/                 # Логи
├── requirements.txt
├── .env
└── main.py              # Точка входа
```

### Принципы проектирования

1. **Separation of Concerns**
   - Каждый компонент отвечает за свою область
   - Четкие границы между слоями

2. **Dependency Injection**
   - Компоненты получают зависимости через конструктор
   - Легкое тестирование

3. **Async First**
   - Все I/O операции асинхронные
   - Неблокирующая архитектура

4. **Error Handling**
   - Все ошибки логируются
   - Критические ошибки отправляются админу
   - Graceful degradation

5. **Configuration over Code**
   - Все настройки в конфиге
   - Легкая смена окружений

---

## Заключение

Архитектура спроектирована с учетом:
- Масштабируемости
- Надежности
- Безопасности (Anti-Ban)
- Производительности (async)
- Поддерживаемости (чистая архитектура)

**Следующий этап:** Stage 4 — Data Models

