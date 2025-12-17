"""Logging middleware."""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery, Message
import logging

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования запросов."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Логирование перед обработкой."""
        if isinstance(event, CallbackQuery):
            logger.info(f"Callback received: {event.data} from user {event.from_user.id}")
        elif isinstance(event, Message):
            if event.text:
                logger.info(f"Message received: {event.text[:50]} from user {event.from_user.id}")
        
        try:
            result = await handler(event, data)
            logger.info(f"Handler completed successfully")
            return result
        except Exception as e:
            logger.error(f"Handler failed: {e}", exc_info=True)
            raise

