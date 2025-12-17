"""Error handling and notification to admins."""
import traceback
import json
from typing import Optional, Dict, Any
from aiogram import Bot
from src.config import settings
import structlog

logger = structlog.get_logger()


async def send_error_to_admin(
    bot: Bot,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
):
    """
    Отправка ошибки администратору.
    
    Args:
        bot: Экземпляр бота
        error: Исключение
        context: Дополнительный контекст
    """
    error_message = f"""
🚨 Ошибка в системе

Тип: {type(error).__name__}
Сообщение: {str(error)}

Контекст:
{json.dumps(context or {}, indent=2, ensure_ascii=False)}

Stacktrace:
{traceback.format_exc()}
"""
    
    # Отправка всем админам
    for admin_id in settings.admin_ids_list:
        try:
            await bot.send_message(admin_id, error_message)
            logger.info("error_sent_to_admin", admin_id=admin_id, error_type=type(error).__name__)
        except Exception as e:
            logger.error("failed_to_send_error_to_admin", admin_id=admin_id, error=str(e))


def log_error(
    component: str,
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    level: str = "ERROR"
):
    """
    Логирование ошибки.
    
    Args:
        component: Компонент системы
        error: Исключение
        context: Дополнительный контекст
        level: Уровень логирования
    """
    log_func = getattr(logger, level.lower(), logger.error)
    
    log_func(
        "error_occurred",
        component=component,
        error_type=type(error).__name__,
        error_message=str(error),
        context=context or {},
        stacktrace=traceback.format_exc()
    )

