"""Main entry point for Telegram Dispatcher Platform."""
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, MenuButtonCommands
from aiogram.fsm.storage.memory import MemoryStorage
from src.config import settings
from src.utils.logging_setup import setup_logging

# Setup logging
logger = setup_logging()


async def setup_bot_commands(bot: Bot):
    """Настройка команд меню бота (опционально, для совместимости)."""
    # Оставляем команды для совместимости, но основное меню - это кнопки справа
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="help", description="❓ Помощь"),
    ]
    
    await bot.set_my_commands(commands)
    logger.info("Bot commands menu set up successfully")


async def main():
    """Main function."""
    logger.info("Starting Telegram Dispatcher Platform...")
    
    # Initialize bot and dispatcher
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Setup bot commands menu
    await setup_bot_commands(bot)
    
    # Register middleware
    from src.bot.middleware.database import DatabaseMiddleware
    from src.bot.middleware.error_handler import ErrorHandlerMiddleware
    from src.bot.middleware.logging_middleware import LoggingMiddleware
    
    # Logging middleware (первым для логирования всех событий)
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    
    # Error handler
    dp.message.middleware(ErrorHandlerMiddleware())
    dp.callback_query.middleware(ErrorHandlerMiddleware())
    
    # Database middleware
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    
    # Register handlers
    from src.bot.handlers import order_handlers, admin_handlers, settings_handlers
    dp.include_router(order_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(settings_handlers.router)
    
    logger.info("Bot started. Press Ctrl+C to stop.")
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

