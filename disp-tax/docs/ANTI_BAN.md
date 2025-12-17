# ANTI-BAN LOGIC
# Защита от блокировки аккаунта Telegram

Этот документ описывает логику защиты от блокировки аккаунта при массовой отправке сообщений.

---

## Принципы

### Безопасность > Скорость
**Главное правило:** Лучше НЕ отправить заказ, чем потерять аккаунт диспетчера.

### Детерминированное поведение
- Все задержки предсказуемы
- Нет "магии" и скрытой логики
- Диспетчер всегда видит, что происходит

---

## Компоненты Anti-Ban системы

### 1. Случайные задержки (Random Delays)

**Назначение:** Имитация человеческого поведения.

**Реализация:**
```python
import random
import asyncio

async def random_delay(min_seconds: int, max_seconds: int):
    """Случайная задержка между отправками."""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)
    return delay
```

**Параметры:**
- Минимальная задержка: 3-5 секунд (по умолчанию)
- Максимальная задержка: 10-15 секунд (по умолчанию)
- Настраивается в сценарии отправки

**Использование:**
- Между отправками в разные группы
- После каждого сообщения
- Обязательно, без исключений

---

### 2. Rate Limiting (Ограничение частоты)

**Назначение:** Ограничение количества сообщений в единицу времени.

**Параметры:**
- Максимум сообщений в минуту: 10-15
- Максимум сообщений в час: 200-300
- Максимум сообщений в день: 2000-3000

**Реализация:**
```python
from collections import deque
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_per_minute: int = 12):
        self.max_per_minute = max_per_minute
        self.messages = deque()
    
    async def can_send(self) -> bool:
        """Проверка возможности отправки."""
        now = datetime.utcnow()
        # Удаляем старые записи (старше 1 минуты)
        while self.messages and (now - self.messages[0]) > timedelta(minutes=1):
            self.messages.popleft()
        
        return len(self.messages) < self.max_per_minute
    
    async def record_send(self):
        """Запись отправки."""
        self.messages.append(datetime.utcnow())
```

**Поведение:**
- Если лимит превышен — ожидание до освобождения слота
- Уведомление диспетчера о задержке
- Автоматическое продолжение после освобождения

---

### 3. FloodWait Handling

**Назначение:** Обработка ошибок FloodWait от Telegram API.

**Что такое FloodWait:**
- Telegram ограничивает слишком частые запросы
- Возвращает ошибку с временем ожидания
- Требует паузы перед следующей отправкой

**Реализация:**
```python
from telethon.errors import FloodWaitError

async def send_with_floodwait_handling(client, chat_id, message):
    """Отправка с обработкой FloodWait."""
    try:
        await client.send_message(chat_id, message)
    except FloodWaitError as e:
        wait_time = e.seconds
        # Уведомление диспетчера
        await notify_dispatcher(
            f"⚠️ FloodWait: нужно подождать {wait_time} секунд"
        )
        # Ожидание
        await asyncio.sleep(wait_time)
        # Повторная попытка
        await client.send_message(chat_id, message)
```

**Поведение:**
- Автоматическое ожидание указанного времени
- Уведомление диспетчера о задержке
- Продолжение отправки после ожидания
- Логирование всех FloodWait событий

---

### 4. Пауза и уведомление диспетчера

**Назначение:** Информирование диспетчера о проблемах.

**Сценарии уведомлений:**
1. **FloodWait обнаружен**
   - Сообщение: "⚠️ FloodWait: ожидание X секунд"
   - Показ прогресса ожидания

2. **Rate limit превышен**
   - Сообщение: "⏳ Превышен лимит отправки, ожидание..."
   - Показ времени до освобождения

3. **Высокий риск блокировки**
   - Сообщение: "🚨 Высокий риск блокировки! Рекомендуется остановить отправку."
   - Предложение отменить отправку

4. **Отправка приостановлена**
   - Сообщение: "⏸️ Отправка приостановлена из-за риска"
   - Кнопки: "Продолжить" / "Отменить"

---

### 5. Никогда не burst-send

**Правило:** Никогда не отправлять сообщения пачкой без задержек.

**Запрещено:**
```python
# ❌ НЕПРАВИЛЬНО
for group in groups:
    await client.send_message(group, message)  # Без задержки!
```

**Правильно:**
```python
# ✅ ПРАВИЛЬНО
for group in groups:
    await client.send_message(group, message)
    await random_delay(min_delay, max_delay)  # Обязательная задержка
    await rate_limiter.record_send()
```

---

## Расчет времени отправки

### Формула

```
total_time = (количество_групп × (задержка_отправки + случайная_задержка)) + 
             (количество_floodwait × время_floodwait) +
             (количество_rate_limit × время_ожидания)
```

### Пример расчета

**Параметры:**
- Групп: 50
- Минимальная задержка: 5 сек
- Максимальная задержка: 10 сек
- Средняя задержка: 7.5 сек

**Расчет:**
```
50 групп × 7.5 сек = 375 секунд = ~6.25 минут
```

**С учетом возможных FloodWait:**
- Если 2 FloodWait по 30 сек: +60 сек
- Итого: ~7.25 минут

---

## Индикатор риска

### Уровни риска

1. **LOW (низкий)**
   - Меньше 10 групп
   - Нормальные задержки
   - Нет недавних FloodWait

2. **MEDIUM (средний)**
   - 10-30 групп
   - Нормальные задержки
   - Недавние FloodWait редки

3. **HIGH (высокий)**
   - Больше 30 групп
   - Короткие задержки
   - Частые FloodWait
   - Много отправок за последний час

### Расчет риска

```python
def calculate_risk_level(
    group_count: int,
    delay_min: int,
    delay_max: int,
    recent_floodwaits: int,
    messages_last_hour: int
) -> str:
    """Расчет уровня риска."""
    risk_score = 0
    
    # Количество групп
    if group_count > 30:
        risk_score += 3
    elif group_count > 10:
        risk_score += 1
    
    # Задержки
    avg_delay = (delay_min + delay_max) / 2
    if avg_delay < 5:
        risk_score += 2
    elif avg_delay < 7:
        risk_score += 1
    
    # FloodWait
    if recent_floodwaits > 2:
        risk_score += 2
    elif recent_floodwaits > 0:
        risk_score += 1
    
    # Активность
    if messages_last_hour > 200:
        risk_score += 2
    elif messages_last_hour > 100:
        risk_score += 1
    
    # Определение уровня
    if risk_score >= 6:
        return "HIGH"
    elif risk_score >= 3:
        return "MEDIUM"
    else:
        return "LOW"
```

---

## Процесс отправки с Anti-Ban

### Алгоритм

```python
async def send_order_with_anti_ban(order, groups, scenario):
    """Отправка заказа с применением Anti-Ban логики."""
    
    # 1. Расчет риска
    risk = calculate_risk_level(...)
    
    # 2. Показ preview с риском
    await show_send_preview(order, groups, risk)
    
    # 3. Подтверждение диспетчера
    if risk == "HIGH":
        confirmed = await confirm_high_risk_send()
        if not confirmed:
            return
    
    # 4. Начало отправки
    order.state = OrderState.SENDING
    await save_order(order)
    
    # 5. Отправка в каждую группу
    for group in groups:
        # Проверка rate limit
        while not await rate_limiter.can_send():
            await notify_dispatcher("⏳ Ожидание освобождения лимита...")
            await asyncio.sleep(1)
        
        try:
            # Отправка
            message = await client.send_message(group.id, order.normalized_content)
            
            # Сохранение сообщения
            await save_group_message(order.id, group.id, message.id)
            
            # Запись в rate limiter
            await rate_limiter.record_send()
            
            # Случайная задержка
            delay = await random_delay(scenario.delay_min, scenario.delay_max)
            await notify_progress(f"Отправлено в {group.title}, задержка: {delay:.1f}с")
            
        except FloodWaitError as e:
            # Обработка FloodWait
            await handle_floodwait(e.seconds)
            # Повторная попытка
            message = await client.send_message(group.id, order.normalized_content)
            await save_group_message(order.id, group.id, message.id)
        
        except Exception as e:
            # Обработка других ошибок
            await log_error(f"Ошибка отправки в {group.title}: {e}")
            await notify_dispatcher(f"❌ Ошибка в {group.title}: {e}")
            # Продолжаем с следующей группой
    
    # 6. Завершение
    order.state = OrderState.ACTIVE
    await save_order(order)
    await notify_dispatcher("✅ Заказ отправлен во все группы")
```

---

## Мониторинг и логирование

### Что логируется

1. **Каждая отправка:**
   - Группа
   - Время отправки
   - Задержка
   - Успех/ошибка

2. **FloodWait события:**
   - Время ожидания
   - Группа
   - Время события

3. **Rate limit события:**
   - Время блокировки
   - Количество сообщений в минуту
   - Время освобождения

4. **Риски:**
   - Уровень риска
   - Факторы риска
   - Действия диспетчера

---

## Рекомендации

### Для диспетчеров

1. **Используйте разумные задержки**
   - Минимум 5 секунд между отправками
   - Максимум 15 секунд для безопасности

2. **Не отправляйте слишком часто**
   - Максимум 10-15 заказов в час
   - Делайте перерывы

3. **Следите за индикатором риска**
   - Если HIGH — подумайте о паузе
   - Увеличьте задержки при частых FloodWait

4. **Не игнорируйте предупреждения**
   - FloodWait — это сигнал
   - Сделайте паузу при необходимости

### Для системы

1. **Всегда применяйте задержки**
   - Даже для одного сообщения
   - Никаких исключений

2. **Уведомляйте о проблемах**
   - Диспетчер должен знать о задержках
   - Показывайте прогресс

3. **Безопасность превыше всего**
   - Лучше не отправить, чем потерять аккаунт
   - Предлагайте отмену при высоком риске

---

## Заключение

Anti-Ban логика — критически важный компонент системы. Она защищает аккаунты диспетчеров от блокировки, обеспечивая безопасную массовую отправку сообщений.

**Принципы:**
- Безопасность > Скорость
- Детерминированное поведение
- Прозрачность для диспетчера
- Автоматическая обработка ошибок

