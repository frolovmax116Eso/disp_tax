"""Audit logging for order actions and dispatcher activities."""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models import OrderHistory, Dispatcher
import structlog

logger = structlog.get_logger()


async def log_order_action(
    session: AsyncSession,
    order_id: int,
    action: str,
    dispatcher_id: int,
    details: Optional[Dict[str, Any]] = None
):
    """
    Логирование действия с заказом.
    
    Args:
        session: Сессия БД
        order_id: ID заказа
        action: Тип действия
        dispatcher_id: Telegram ID диспетчера
        details: Детали действия
    """
    logger.info(
        "order_action",
        order_id=order_id,
        action=action,
        dispatcher_id=dispatcher_id,
        details=details or {}
    )
    
    # История уже сохраняется в OrderFSM.transition
    # Здесь только логируем в файл


async def log_session_event(
    session: AsyncSession,
    dispatcher_id: int,
    event_type: str,
    details: Optional[Dict[str, Any]] = None
):
    """
    Логирование события сессии.
    
    Args:
        session: Сессия БД
        dispatcher_id: Telegram ID диспетчера
        event_type: Тип события
        details: Детали события
    """
    logger.info(
        "session_event",
        dispatcher_id=dispatcher_id,
        event_type=event_type,
        details=details or {}
    )
    
    # Обновление last_access в Dispatcher (если нужно)
    result = await session.execute(
        select(Dispatcher).where(Dispatcher.telegram_id == dispatcher_id)
    )
    dispatcher = result.scalar_one_or_none()
    
    if dispatcher:
        dispatcher.updated_at = datetime.utcnow()
        await session.commit()

