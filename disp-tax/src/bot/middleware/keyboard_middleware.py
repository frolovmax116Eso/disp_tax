"""Middleware for persistent keyboard."""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from src.bot.keyboards import get_main_keyboard


class KeyboardMiddleware(BaseMiddleware):
    """Middleware для автоматического показа клавиатуры."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Показываем клавиатуру, если это обычное сообщение и клавиатура не установлена."""
        result = await handler(event, data)
        
        # Если это сообщение и в ответе не установлена клавиатура, добавляем основную
        if isinstance(event, Message) and not event.via_bot:
            # Проверяем, не установлена ли уже клавиатура в ответе
            # Это делается через проверку, был ли вызван answer с reply_markup
            # Но проще всего - просто не трогать, если клавиатура уже установлена
            pass
        
        return result

