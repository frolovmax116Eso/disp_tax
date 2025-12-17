# API SPECIFICATION
# Telegram Dispatcher Platform

Этот документ описывает API для бота и внутренних компонентов системы.

---

## Stage 5.1 — API для создания/редактирования заказов

### Bot Commands (aiogram)

#### `/start`
Инициализация бота для диспетчера.

**Response:**
- Приветствие
- Кнопка "Авторизоваться" (если не авторизован)
- Главное меню (если авторизован)

#### `/new_order` или кнопка "Создать заказ"
Начало создания нового заказа.

**FSM States:**
1. `OrderInput:content` — ввод текста заказа
2. `OrderInput:normalize` — нормализация текста
3. `OrderInput:preview` — показ preview
4. `OrderInput:confirm` — подтверждение

**Handlers:**
- `process_order_content(message)` — обработка текста заказа
- `normalize_order(order_id)` — нормализация текста
- `show_order_preview(order_id)` — показ preview
- `confirm_order(order_id)` — подтверждение заказа

#### `/edit_order <order_id>`
Редактирование существующего заказа.

**Requirements:**
- Заказ в состоянии `active` или `assigned`
- Подтверждение изменений

**FSM States:**
1. `OrderEdit:content` — новый текст
2. `OrderEdit:preview` — preview изменений
3. `OrderEdit:confirm` — подтверждение

**Handlers:**
- `start_edit_order(order_id)` — начало редактирования
- `process_edit_content(message, order_id)` — обработка нового текста
- `show_edit_preview(order_id)` — preview изменений
- `confirm_edit(order_id)` — подтверждение и обновление всех сообщений

### Internal API (Services)

#### `OrderService.create_order(dispatcher_id: int, content: str) -> Order`
Создание нового заказа.

**Returns:** Order object в состоянии `draft`

#### `OrderService.normalize_content(content: str) -> str`
Нормализация текста заказа.

**Process:**
- Удаление лишних пробелов
- Форматирование
- Валидация

#### `OrderService.preview_order(order_id: int) -> dict`
Получение preview заказа.

**Returns:**
```python
{
    "order_id": int,
    "content": str,
    "normalized_content": str,
    "estimated_groups": int,  # Сколько групп будет затронуто
    "risk_level": str  # low/medium/high
}
```

#### `OrderService.confirm_order(order_id: int) -> Order`
Подтверждение заказа.

**Process:**
- Переход в состояние `confirmed`
- Создание записи в OrderHistory
- Возврат Order

#### `OrderService.edit_order(order_id: int, new_content: str) -> Order`
Редактирование заказа.

**Process:**
- Обновление content и normalized_content
- Обновление всех GroupMessage
- Создание записи в OrderHistory
- Возврат обновленного Order

---

## Stage 5.2 — API для управления сценариями отправки

### Bot Commands

#### `/scenarios` или кнопка "Сценарии"
Управление сценариями отправки.

**Menu:**
- Список сохраненных сценариев
- "Создать новый сценарий"
- "Удалить сценарий"

#### `/create_scenario`
Создание нового сценария.

**FSM States:**
1. `ScenarioCreate:name` — название сценария
2. `ScenarioCreate:groups` — выбор групп
3. `ScenarioCreate:delays` — настройка задержек
4. `ScenarioCreate:confirm` — подтверждение

**Handlers:**
- `process_scenario_name(message)` — обработка названия
- `select_scenario_groups(callback)` — выбор групп (inline keyboard)
- `set_scenario_delays(message)` — настройка задержек
- `confirm_scenario(scenario_id)` — сохранение сценария

#### `/send_order <order_id>`
Отправка заказа.

**Menu выбора сценария:**
- Сохраненные сценарии
- "По региону"
- "Все группы"
- "Выбрать вручную"

**FSM States:**
1. `OrderSend:select_scenario` — выбор сценария
2. `OrderSend:preview` — preview отправки
3. `OrderSend:confirm` — подтверждение

**Preview показывает:**
- Список групп
- Текст заказа
- Расчетное время отправки
- VIP статус (если есть)
- Индикатор риска

**Handlers:**
- `select_send_scenario(callback, order_id)` — выбор сценария
- `show_send_preview(order_id, scenario_id)` — preview отправки
- `confirm_send(order_id, scenario_id)` — подтверждение и начало отправки

### Internal API

#### `ScenarioService.create_scenario(dispatcher_id: int, name: str, group_ids: List[int], delay_min: int, delay_max: int) -> Scenario`
Создание сценария.

#### `ScenarioService.get_scenarios(dispatcher_id: int) -> List[Scenario]`
Получение всех сценариев диспетчера.

#### `ScenarioService.get_scenario_by_region(dispatcher_id: int, region_id: int) -> Scenario`
Создание временного сценария по региону.

#### `ScenarioService.get_all_groups_scenario(dispatcher_id: int) -> Scenario`
Создание временного сценария "все группы".

#### `OrderService.send_order(order_id: int, scenario_id: int) -> None`
Отправка заказа по сценарию.

**Process:**
- Переход в состояние `sending`
- Получение групп из сценария
- Применение Anti-Ban логики
- Отправка через Telethon Client
- Создание GroupMessage для каждого отправленного сообщения
- Переход в состояние `active`

---

## Stage 5.3 — API для работы с ответами водителей

### Bot Commands

#### `/order_responses <order_id>` или кнопка "Ответы"
Просмотр ответов водителей на заказ.

**Response:**
- Список всех ответов
- Для каждого ответа: имя, ник, группа, время, текст
- Кнопка "Назначить водителя"

**Handlers:**
- `show_order_responses(order_id)` — показ списка ответов
- `refresh_responses(callback, order_id)` — обновление списка

### Internal API

#### `ResponseMonitor.start_monitoring(order_id: int, group_ids: List[int]) -> None`
Начало мониторинга групп на ответы.

**Process:**
- Регистрация групп для мониторинга
- Подключение handlers к Telethon Client
- Обработка новых сообщений

#### `ResponseMonitor.parse_response(message: Message, order_id: int) -> DriverResponse | None`
Парсинг ответа водителя.

**Logic:**
- Проверка на "я" (регистронезависимо)
- Проверка на reply к сообщению заказа
- Извлечение данных водителя
- Создание DriverResponse

#### `ResponseService.get_responses(order_id: int) -> List[DriverResponse]`
Получение всех ответов на заказ.

**Returns:** Список DriverResponse, отсортированный по времени

#### `ResponseService.get_responses_by_driver(order_id: int, driver_telegram_id: int) -> List[DriverResponse]`
Получение всех ответов конкретного водителя.

#### `ResponseService.notify_new_response(dispatcher_id: int, response: DriverResponse) -> None`
Уведомление диспетчера о новом ответе.

**Process:**
- Отправка сообщения диспетчеру через бота
- Показ информации о водителе и ответе

---

## Stage 5.4 — API для назначения водителя

### Bot Commands

#### `/assign_driver <order_id>`
Назначение водителя на заказ.

**Process:**
1. Получение списка ответивших водителей
2. Показ списка с inline keyboard
3. Выбор водителя
4. Подтверждение назначения

**FSM States:**
1. `DriverAssign:select` — выбор водителя
2. `DriverAssign:confirm` — подтверждение

**Handlers:**
- `show_driver_list(order_id)` — показ списка водителей
- `select_driver(callback, order_id, driver_id)` — выбор водителя
- `confirm_assignment(order_id, driver_id, reason: str | None)` — подтверждение

**Confirmation shows:**
- Информация о водителе
- Информация о заказе
- Кнопки "Подтвердить" / "Отмена"

#### `/change_driver <order_id>`
Смена назначенного водителя.

**Requirements:**
- Заказ в состоянии `assigned`
- Новый водитель должен быть из списка ответивших

**Process:**
- Аналогично `/assign_driver`, но с обязательной причиной смены

**Handlers:**
- `start_change_driver(order_id)` — начало смены
- `select_new_driver(callback, order_id, driver_id)` — выбор нового водителя
- `set_change_reason(message, order_id, driver_id)` — ввод причины
- `confirm_change(order_id, driver_id, reason)` — подтверждение смены

### Internal API

#### `AssignmentService.assign_driver(order_id: int, driver_telegram_id: int, assigned_by: int, reason: str | None) -> Assignment`
Назначение водителя.

**Process:**
- Деактивация предыдущего назначения (если есть)
- Создание нового Assignment
- Переход заказа в состояние `assigned`
- Отправка "✅ Отдан Вам" в группу через Telethon
- Создание записи в OrderHistory

#### `AssignmentService.change_driver(order_id: int, new_driver_id: int, assigned_by: int, reason: str) -> Assignment`
Смена водителя.

**Process:**
- Деактивация текущего назначения
- Создание нового назначения с причиной
- Обновление сообщения в группе
- Создание записи в OrderHistory

#### `AssignmentService.get_active_assignment(order_id: int) -> Assignment | None`
Получение активного назначения.

#### `AssignmentService.get_assignment_history(order_id: int) -> List[Assignment]`
Получение истории всех назначений.

---

## Stage 5.5 — API для админ-панели

### Bot Commands (только для админов)

#### `/admin` или `/a`
Главное меню админ-панели.

**Menu:**
- "Все диспетчеры"
- "Все заказы"
- "Все ответы"
- "Все назначения"
- "Логи и ошибки"
- "Статистика"

#### `/admin_dispatchers`
Просмотр всех диспетчеров.

**Response:**
- Список диспетчеров с информацией:
  - Telegram ID, имя, ник
  - Статус сессии
  - Количество заказов
  - Последняя активность

**Handlers:**
- `show_all_dispatchers()` — показ списка
- `show_dispatcher_details(dispatcher_id)` — детали диспетчера

#### `/admin_orders [filter]`
Просмотр всех заказов.

**Filters:**
- По диспетчеру
- По состоянию
- По дате
- По VIP статусу

**Response:**
- Список заказов с фильтрацией
- Детали заказа по клику

**Handlers:**
- `show_all_orders(filters: dict)` — показ списка
- `show_order_details(order_id)` — детали заказа

#### `/admin_responses [order_id]`
Просмотр всех ответов.

**Response:**
- Список ответов
- Группировка по заказам (если указан order_id)

#### `/admin_assignments [order_id]`
Просмотр всех назначений.

**Response:**
- Список назначений
- История смен водителей

#### `/admin_logs [level]`
Просмотр логов и ошибок.

**Filters:**
- По уровню (info/warning/error/critical)
- По дате
- По компоненту

**Response:**
- Список логов с фильтрацией
- Детали лога по клику

#### `/admin_stats`
Статистика системы.

**Shows:**
- Количество диспетчеров
- Количество заказов (по состояниям)
- Количество ответов
- Активность за период

### Internal API

#### `AdminService.check_admin_access(telegram_id: int) -> bool`
Проверка прав доступа админа.

**Process:**
- Проверка telegram_id в whitelist
- Обновление last_access_at
- Создание записи в AdminAccessLog

#### `AdminService.get_all_dispatchers() -> List[Dispatcher]`
Получение всех диспетчеров.

#### `AdminService.get_all_orders(filters: dict) -> List[Order]`
Получение всех заказов с фильтрацией.

#### `AdminService.get_all_responses(filters: dict) -> List[DriverResponse]`
Получение всех ответов с фильтрацией.

#### `AdminService.get_all_assignments(filters: dict) -> List[Assignment]`
Получение всех назначений с фильтрацией.

#### `AdminService.get_logs(level: str | None, start_date: datetime | None, end_date: datetime | None) -> List[Log]`
Получение логов с фильтрацией.

#### `AdminService.send_error_to_admin(error: Exception, context: dict) -> None`
Отправка ошибки админу.

**Process:**
- Создание лога с уровнем error/critical
- Отправка сообщения админу через бота
- Включение контекста и stacktrace

---

## Middleware

### AdminMiddleware
Проверка прав доступа для админ-команд.

**Process:**
- Перехват команд `/admin*`
- Проверка через `AdminService.check_admin_access()`
- Блокировка доступа, если не админ

### LoggingMiddleware
Логирование всех действий.

**Process:**
- Логирование всех команд
- Логирование всех callback-запросов
- Сохранение контекста (user_id, command, timestamp)

### SessionMiddleware
Проверка активной сессии диспетчера.

**Process:**
- Проверка сессии перед действиями, требующими Telethon
- Блокировка отправки, если сессия неактивна
- Уведомление диспетчера о необходимости переавторизации

---

## Callback Data Format

Все callback data в формате JSON:

```python
{
    "action": "assign_driver",
    "order_id": 123,
    "driver_id": 456789
}
```

**Actions:**
- `assign_driver` — назначение водителя
- `change_driver` — смена водителя
- `confirm_order` — подтверждение заказа
- `edit_order` — редактирование заказа
- `cancel_order` — отмена заказа
- `close_order` — закрытие заказа
- `select_scenario` — выбор сценария
- `select_group` — выбор группы
- и т.д.

---

## Заключение

API спроектировано с учетом:
- Четкого разделения Bot API и Internal API
- FSM для многошаговых процессов
- Подтверждений для критических действий
- Фильтрации и поиска для админ-панели

**Следующий этап:** Stage 6 — Core Logic (реализация)

