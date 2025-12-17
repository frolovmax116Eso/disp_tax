"""Anti-Ban service - защита от блокировки аккаунта."""
import asyncio
import random
from typing import Optional
from collections import deque
from datetime import datetime, timedelta
from telethon.errors import FloodWaitError
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Ограничитель частоты отправки сообщений."""
    
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
    
    async def wait_if_needed(self) -> float:
        """
        Ожидание, если лимит превышен.
        
        Returns:
            Время ожидания в секундах
        """
        if await self.can_send():
            return 0.0
        
        # Вычисляем время до освобождения слота
        if self.messages:
            oldest = self.messages[0]
            wait_time = (timedelta(minutes=1) - (datetime.utcnow() - oldest)).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                return wait_time
        
        return 0.0


class AntiBanService:
    """Сервис для защиты от блокировки."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.recent_floodwaits = deque(maxlen=10)  # Последние 10 FloodWait
    
    async def random_delay(self, min_seconds: int, max_seconds: int) -> float:
        """
        Случайная задержка между отправками.
        
        Args:
            min_seconds: Минимальная задержка
            max_seconds: Максимальная задержка
            
        Returns:
            Время задержки в секундах
        """
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
        return delay
    
    async def handle_floodwait(self, seconds: int, notify_callback: Optional[callable] = None) -> None:
        """
        Обработка FloodWait.
        
        Args:
            seconds: Время ожидания
            notify_callback: Функция для уведомления (опционально)
        """
        self.recent_floodwaits.append(datetime.utcnow())
        
        if notify_callback:
            await notify_callback(f"⚠️ FloodWait: ожидание {seconds} секунд")
        
        logger.warning(f"FloodWait: waiting {seconds} seconds")
        await asyncio.sleep(seconds)
    
    async def send_with_protection(
        self,
        send_func: callable,
        min_delay: int = 5,
        max_delay: int = 10,
        notify_callback: Optional[callable] = None
    ) -> Optional[any]:
        """
        Отправка с применением Anti-Ban защиты.
        
        Args:
            send_func: Функция отправки (async)
            min_delay: Минимальная задержка
            max_delay: Максимальная задержка
            notify_callback: Функция для уведомлений
            
        Returns:
            Результат send_func или None при ошибке
        """
        # Проверка rate limit
        wait_time = await self.rate_limiter.wait_if_needed()
        if wait_time > 0 and notify_callback:
            await notify_callback(f"⏳ Ожидание освобождения лимита: {wait_time:.1f}с")
        
        # Отправка с обработкой FloodWait
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await send_func()
                await self.rate_limiter.record_send()
                
                # Случайная задержка после отправки
                delay = await self.random_delay(min_delay, max_delay)
                if notify_callback:
                    await notify_callback(f"✅ Отправлено, задержка: {delay:.1f}с")
                
                return result
                
            except FloodWaitError as e:
                await self.handle_floodwait(e.seconds, notify_callback)
                # Повторная попытка после FloodWait
                if attempt < max_retries - 1:
                    continue
                else:
                    logger.error(f"Max retries reached after FloodWait")
                    return None
                    
            except Exception as e:
                logger.error(f"Error in send_with_protection: {e}")
                return None
        
        return None
    
    def calculate_risk_level(
        self,
        group_count: int,
        delay_min: int,
        delay_max: int
    ) -> str:
        """
        Расчет уровня риска.
        
        Args:
            group_count: Количество групп
            delay_min: Минимальная задержка
            delay_max: Максимальная задержка
            
        Returns:
            "LOW", "MEDIUM" или "HIGH"
        """
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
        
        # Недавние FloodWait
        if len(self.recent_floodwaits) > 2:
            risk_score += 2
        elif len(self.recent_floodwaits) > 0:
            risk_score += 1
        
        # Определение уровня
        if risk_score >= 6:
            return "HIGH"
        elif risk_score >= 3:
            return "MEDIUM"
        else:
            return "LOW"


# Глобальный экземпляр
anti_ban_service = AntiBanService()

