# DATA MODELS
# Telegram Dispatcher Platform

Этот документ описывает модели данных системы.

---

## Stage 4.1 — Модель Dispatcher

### Описание
Диспетчер — основной пользователь системы, который создает и управляет заказами.

### Поля

```python
class Dispatcher:
    id: int                    # Primary key
    telegram_id: int           # Telegram user ID (уникальный)
    username: str | None       # @username (опционально)
    first_name: str            # Имя
    last_name: str | None      # Фамилия (опционально)
    session_file: str          # Путь к файлу сессии Telethon
    session_active: bool        # Активна ли сессия
    session_expires_at: datetime | None  # Когда истекает сессия
    created_at: datetime       # Когда зарегистрирован
    updated_at: datetime        # Последнее обновление
    
    # Relationships
    orders: List[Order]         # Все заказы диспетчера
    groups: List[Group]        # Группы диспетчера
    regions: List[Region]      # Регионы диспетчера
    scenarios: List[Scenario]  # Сценарии отправки
```

### Индексы
- `telegram_id` — уникальный индекс
- `session_active` — индекс для быстрого поиска активных сессий

---

## Stage 4.2 — Модель Order

### Описание
Заказ — основная сущность системы, проходит через FSM состояния.

### Поля

```python
class Order:
    id: int                    # Primary key
    dispatcher_id: int         # Foreign key → Dispatcher
    state: OrderState          # Текущее состояние FSM
    content: str               # Текст заказа
    normalized_content: str    # Нормализованный текст
    is_vip: bool              # VIP приоритет
    created_at: datetime       # Создан
    updated_at: datetime       # Обновлен
    confirmed_at: datetime | None  # Подтвержден
    sent_at: datetime | None   # Отправлен
    closed_at: datetime | None # Закрыт/отменен
    
    # Relationships
    dispatcher: Dispatcher
    responses: List[DriverResponse]  # Ответы водителей
    assignments: List[Assignment]      # Назначения
    group_messages: List[GroupMessage]  # Сообщения в группах
    history: List[OrderHistory]       # История изменений
```

### Enum: OrderState

```python
class OrderState(Enum):
    DRAFT = "draft"
    PREVIEW = "preview"
    CONFIRMED = "confirmed"
    SENDING = "sending"
    ACTIVE = "active"
    ASSIGNED = "assigned"
    CLOSED = "closed"
    CANCELLED = "cancelled"
```

### Индексы
- `dispatcher_id` — индекс для поиска заказов диспетчера
- `state` — индекс для фильтрации по состоянию
- `created_at` — индекс для сортировки

---

## Stage 4.3 — Модель Driver Response

### Описание
Ответ водителя на заказ в группе.

### Поля

```python
class DriverResponse:
    id: int                    # Primary key
    order_id: int              # Foreign key → Order
    group_id: int              # Foreign key → Group
    driver_telegram_id: int    # Telegram ID водителя
    driver_username: str | None  # @username водителя
    driver_name: str           # Отображаемое имя
    driver_phone: str | None   # Номер телефона (если доступен)
    response_text: str         # Текст ответа
    response_type: ResponseType  # Тип ответа ("я" или reply)
    message_id: int            # ID сообщения в Telegram
    replied_to_message_id: int | None  # ID сообщения заказа (если reply)
    created_at: datetime       # Время ответа
    
    # Relationships
    order: Order
    group: Group
```

### Enum: ResponseType

```python
class ResponseType(Enum):
    YA = "ya"           # Ответ "я"
    REPLY = "reply"     # Reply на сообщение заказа
```

### Индексы
- `order_id` — индекс для поиска ответов по заказу
- `driver_telegram_id` — индекс для поиска ответов водителя
- `created_at` — индекс для сортировки

---

## Stage 4.4 — Модель Assignment

### Описание
Назначение водителя на заказ. История всех назначений сохраняется.

### Поля

```python
class Assignment:
    id: int                    # Primary key
    order_id: int              # Foreign key → Order
    driver_telegram_id: int    # Telegram ID водителя
    driver_username: str | None  # @username водителя
    driver_name: str           # Имя водителя
    assigned_by: int           # Telegram ID диспетчера
    reason: str | None         # Причина назначения/смены
    is_active: bool            # Активно ли назначение
    assigned_at: datetime      # Время назначения
    unassigned_at: datetime | None  # Время снятия (если сменили)
    
    # Relationships
    order: Order
```

### Индексы
- `order_id` — индекс для поиска назначений по заказу
- `driver_telegram_id` — индекс для поиска назначений водителя
- `is_active` — индекс для поиска активных назначений

---

## Stage 4.5 — Модели Group, Region, Scenario

### Group (Группа)

```python
class Group:
    id: int                    # Primary key
    dispatcher_id: int         # Foreign key → Dispatcher
    telegram_group_id: int     # Telegram chat ID (уникальный для диспетчера)
    title: str                 # Название группы
    region_id: int | None      # Foreign key → Region (опционально)
    is_active: bool            # Активна ли группа
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    dispatcher: Dispatcher
    region: Region | None
    responses: List[DriverResponse]
    messages: List[GroupMessage]
```

### Region (Регион)

```python
class Region:
    id: int                    # Primary key
    dispatcher_id: int         # Foreign key → Dispatcher
    name: str                  # Название региона
    description: str | None    # Описание
    created_at: datetime
    
    # Relationships
    dispatcher: Dispatcher
    groups: List[Group]
```

### Scenario (Сценарий отправки)

```python
class Scenario:
    id: int                    # Primary key
    dispatcher_id: int         # Foreign key → Dispatcher
    name: str                  # Название сценария
    description: str | None    # Описание
    group_ids: List[int]       # JSON массив ID групп
    delay_min: int             # Минимальная задержка (секунды)
    delay_max: int             # Максимальная задержка (секунды)
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    dispatcher: Dispatcher
```

### Индексы
- `dispatcher_id` — индекс для поиска по диспетчеру
- `telegram_group_id` (Group) — уникальный индекс в рамках диспетчера
- `is_active` (Group) — индекс для фильтрации активных групп

---

## Stage 4.6 — Модель Admin

### Описание
Администратор платформы с полным доступом.

### Поля

```python
class Admin:
    id: int                    # Primary key
    telegram_id: int           # Telegram user ID (уникальный)
    username: str | None       # @username
    first_name: str
    is_active: bool            # Активен ли админ
    created_at: datetime
    last_access_at: datetime | None  # Последний доступ
    
    # Relationships
    access_logs: List[AdminAccessLog]
```

### AdminAccessLog (Лог доступа админа)

```python
class AdminAccessLog:
    id: int                    # Primary key
    admin_id: int              # Foreign key → Admin
    action: str                # Действие (view_dispatchers, view_orders, etc.)
    details: str | None         # JSON с деталями
    created_at: datetime
    
    # Relationships
    admin: Admin
```

### Индексы
- `telegram_id` (Admin) — уникальный индекс
- `admin_id` (AdminAccessLog) — индекс для поиска логов админа
- `created_at` (AdminAccessLog) — индекс для сортировки

---

## Дополнительные модели

### OrderHistory (История заказа)

```python
class OrderHistory:
    id: int                    # Primary key
    order_id: int              # Foreign key → Order
    old_state: OrderState | None  # Предыдущее состояние
    new_state: OrderState         # Новое состояние
    changed_by: int            # Telegram ID того, кто изменил
    change_reason: str | None   # Причина изменения
    changes: str               # JSON с деталями изменений
    created_at: datetime
    
    # Relationships
    order: Order
```

### GroupMessage (Сообщение заказа в группе)

```python
class GroupMessage:
    id: int                    # Primary key
    order_id: int              # Foreign key → Order
    group_id: int              # Foreign key → Group
    telegram_message_id: int   # ID сообщения в Telegram
    message_text: str          # Текст сообщения
    sent_at: datetime          # Когда отправлено
    updated_at: datetime | None # Когда обновлено
    is_deleted: bool           # Удалено ли сообщение
    
    # Relationships
    order: Order
    group: Group
```

### Индексы
- `order_id` (OrderHistory, GroupMessage) — индекс для поиска по заказу
- `telegram_message_id` (GroupMessage) — индекс для поиска сообщения

---

## Связи между моделями

```
Dispatcher (1) ──→ (N) Order
Dispatcher (1) ──→ (N) Group
Dispatcher (1) ──→ (N) Region
Dispatcher (1) ──→ (N) Scenario

Order (1) ──→ (N) DriverResponse
Order (1) ──→ (N) Assignment
Order (1) ──→ (N) OrderHistory
Order (1) ──→ (N) GroupMessage

Group (N) ──→ (1) Region
Group (1) ──→ (N) DriverResponse
Group (1) ──→ (N) GroupMessage

Admin (1) ──→ (N) AdminAccessLog
```

---

## Заключение

Все модели спроектированы с учетом:
- Целостности данных (foreign keys)
- Производительности (индексы)
- Неизменяемости истории (OrderHistory)
- Гибкости (опциональные поля)

**Следующий этап:** Stage 5 — API

