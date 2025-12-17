"""Error handling middleware."""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery, Message
import logging

from src.utils.error_format import format_error_for_user

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseMiddleware):
    """Middleware для обработки ошибок."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Обработка с перехватом ошибок."""
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Error in handler: {e}", exc_info=True)
            
            # Попытка отправить сообщение об ошибке пользователю
            try:
                error_msg = format_error_for_user(e, max_length=80)
                if isinstance(event, CallbackQuery):
                    await event.answer(f"Ошибка: {error_msg}", show_alert=True)
                elif isinstance(event, Message):
                    await event.answer(f"Произошла ошибка. Попробуйте еще раз.")
            except:
                pass  # Если не удалось отправить сообщение, просто логируем
            
            raise

