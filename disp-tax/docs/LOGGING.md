# LOGGING SYSTEM
# Система логирования

Этот документ описывает систему логирования в Telegram Dispatcher Platform.

---

## Уровни логирования

### 1. INFO (информация)
**Назначение:** Обычные события работы системы.

**Примеры:**
- Создание заказа
- Отправка сообщения
- Назначение водителя
- Авторизация диспетчера

**Формат:**
```
2024-01-15 10:30:45 - INFO - Order #123 created by dispatcher #456
```

---

### 2. WARNING (предупреждение)
**Назначение:** Потенциальные проблемы, которые не критичны.

**Примеры:**
- FloodWait обнаружен
- Rate limit приближается к лимиту
- Сессия скоро истечет
- Медленная отправка

**Формат:**
```
2024-01-15 10:30:45 - WARNING - FloodWait detected: 30 seconds
```

**Действия:**
- Логируется
- Уведомляется диспетчер (опционально)
- НЕ отправляется админу

---

### 3. ERROR (ошибка)
**Назначение:** Ошибки, которые требуют внимания, но не останавливают работу.

**Примеры:**
- Ошибка отправки в одну группу
- Ошибка парсинга ответа
- Ошибка сохранения в БД (с retry)
- Ошибка подключения к Telegram API (временная)

**Формат:**
```
2024-01-15 10:30:45 - ERROR - Failed to send message to group #789: ConnectionError
```

**Действия:**
- Логируется
- Отправляется админу
- Система продолжает работу

---

### 4. CRITICAL (критическая ошибка)
**Назначение:** Критические ошибки, которые могут остановить работу системы.

**Примеры:**
- Потеря соединения с БД
- Критическая ошибка Telethon
- Ошибка авторизации бота
- Системная ошибка

**Формат:**
```
2024-01-15 10:30:45 - CRITICAL - Database connection lost: unable to reconnect
```

**Действия:**
- Логируется
- Немедленно отправляется админу
- Может остановить работу компонента

---

## Структура лога

### Базовый формат

```python
{
    "timestamp": "2024-01-15T10:30:45.123Z",
    "level": "ERROR",
    "component": "telethon_client",
    "message": "Failed to send message",
    "context": {
        "order_id": 123,
        "group_id": 789,
        "error": "ConnectionError",
        "stacktrace": "..."
    }
}
```

### Поля

- **timestamp** — время события (UTC)
- **level** — уровень логирования
- **component** — компонент системы (telethon_client, bot, database, etc.)
- **message** — краткое описание события
- **context** — дополнительный контекст (опционально)

---

## Компоненты логирования

### 1. Logger Setup

```python
import structlog
import logging

# Настройка structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
```

---

### 2. Логирование действий с заказами

```python
async def log_order_action(
    order_id: int,
    action: str,
    dispatcher_id: int,
    details: dict | None = None
):
    """Логирование действия с заказом."""
    logger.info(
        "order_action",
        order_id=order_id,
        action=action,
        dispatcher_id=dispatcher_id,
        details=details or {}
    )
    
    # Сохранение в БД
    await save_order_history(
        order_id=order_id,
        action=action,
        changed_by=dispatcher_id,
        details=details
    )
```

**Примеры действий:**
- `order_created` — заказ создан
- `order_edited` — заказ отредактирован
- `order_confirmed` — заказ подтвержден
- `order_sent` — заказ отправлен
- `order_assigned` — водитель назначен
- `order_closed` — заказ закрыт
- `order_cancelled` — заказ отменен

---

### 3. Логирование сессий и авторизаций

```python
async def log_session_event(
    dispatcher_id: int,
    event_type: str,
    details: dict | None = None
):
    """Логирование события сессии."""
    logger.info(
        "session_event",
        dispatcher_id=dispatcher_id,
        event_type=event_type,
        details=details or {}
    )
```

**Типы событий:**
- `session_started` — начало авторизации
- `session_authorized` — успешная авторизация
- `session_expired` — сессия истекла
- `session_refreshed` — сессия обновлена
- `session_failed` — ошибка авторизации

---

### 4. Логирование ошибок

```python
async def log_error(
    component: str,
    error: Exception,
    context: dict | None = None,
    level: str = "ERROR"
):
    """Логирование ошибки."""
    logger.error(
        "error_occurred",
        component=component,
        error_type=type(error).__name__,
        error_message=str(error),
        context=context or {},
        stacktrace=traceback.format_exc()
    )
    
    # Отправка админу, если ERROR или CRITICAL
    if level in ["ERROR", "CRITICAL"]:
        await send_error_to_admin(error, context)
```

---

### 5. Отправка ошибок админу

```python
async def send_error_to_admin(
    error: Exception,
    context: dict | None = None
):
    """Отправка ошибки администратору."""
    from src.config import settings
    from src.bot import bot
    
    error_message = f"""
🚨 Ошибка в системе

Компонент: {context.get('component', 'unknown')}
Тип: {type(error).__name__}
Сообщение: {str(error)}

Контекст:
{json.dumps(context, indent=2, ensure_ascii=False)}
"""
    
    # Отправка всем админам
    for admin_id in settings.admin_ids_list:
        try:
            await bot.send_message(admin_id, error_message)
        except Exception as e:
            # Логируем ошибку отправки, но не падаем
            logger.error("failed_to_send_error_to_admin", admin_id=admin_id, error=str(e))
```

---

## Файлы логов

### Структура

```
logs/
├── dispatcher.log          # Основной лог (все уровни)
├── dispatcher.error.log    # Только ошибки (ERROR, CRITICAL)
├── dispatcher.info.log     # Информационные сообщения (INFO)
└── dispatcher.audit.log    # Аудит (все действия с заказами)
```

### Ротация логов

- По размеру: 10 MB на файл
- По времени: ежедневная ротация
- Хранение: последние 30 дней
- Сжатие: старые логи сжимаются

---

## Логирование в компонентах

### Telethon Client

```python
logger = structlog.get_logger("telethon_client")

async def send_message(group_id, message):
    logger.info("sending_message", group_id=group_id)
    try:
        result = await client.send_message(group_id, message)
        logger.info("message_sent", group_id=group_id, message_id=result.id)
        return result
    except FloodWaitError as e:
        logger.warning("floodwait", group_id=group_id, wait_seconds=e.seconds)
        raise
    except Exception as e:
        logger.error("send_failed", group_id=group_id, error=str(e))
        raise
```

### Bot Handlers

```python
logger = structlog.get_logger("bot")

@dp.message_handler(commands=['new_order'])
async def new_order_handler(message: Message):
    logger.info("command_received", command="new_order", user_id=message.from_user.id)
    # ...
```

### Database

```python
logger = structlog.get_logger("database")

async def save_order(order):
    logger.info("saving_order", order_id=order.id)
    try:
        await session.commit()
        logger.info("order_saved", order_id=order.id)
    except Exception as e:
        logger.error("save_failed", order_id=order.id, error=str(e))
        raise
```

---

## Фильтрация и поиск

### По уровню

```python
# Только ошибки
logs = await get_logs(level="ERROR")

# Критические ошибки
logs = await get_logs(level="CRITICAL")
```

### По компоненту

```python
# Логи Telethon Client
logs = await get_logs(component="telethon_client")
```

### По времени

```python
# За последний час
logs = await get_logs(start_time=datetime.utcnow() - timedelta(hours=1))

# За период
logs = await get_logs(
    start_time=datetime(2024, 1, 15),
    end_time=datetime(2024, 1, 16)
)
```

### По контексту

```python
# Логи конкретного заказа
logs = await get_logs(context_filter={"order_id": 123})
```

---

## Аудит

### Что логируется в аудит

1. **Все действия с заказами:**
   - Создание, редактирование, удаление
   - Изменение состояний
   - Назначение водителей

2. **Действия диспетчеров:**
   - Авторизация
   - Изменение настроек
   - Управление группами

3. **Действия админов:**
   - Просмотр данных
   - Изменение конфигурации

### Формат аудита

```json
{
    "timestamp": "2024-01-15T10:30:45.123Z",
    "user_id": 123456789,
    "user_type": "dispatcher",
    "action": "order_created",
    "resource": "order",
    "resource_id": 123,
    "details": {
        "content": "...",
        "state": "draft"
    }
}
```

---

## Заключение

Система логирования обеспечивает:
- Полную прозрачность работы системы
- Отслеживание всех ошибок
- Аудит действий пользователей
- Диагностику проблем
- Мониторинг производительности

**Принципы:**
- Все важные события логируются
- Ошибки отправляются админу
- Логи структурированы и поисковы
- История сохраняется для анализа

