"""Service for handling driver responses."""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models import DriverResponse, Order, Group, ResponseType
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ResponseService:
    """Сервис для работы с ответами водителей."""
    
    @staticmethod
    def parse_response(text: str, is_reply: bool = False) -> Optional[ResponseType]:
        """
        Парсинг ответа водителя.
        
        Args:
            text: Текст ответа
            is_reply: Является ли ответом на сообщение заказа
            
        Returns:
            ResponseType или None
        """
        text_lower = text.lower().strip()
        
        # Проверка на "я"
        if "я" in text_lower.split():
            return ResponseType.YA
        
        # Проверка на reply
        if is_reply:
            return ResponseType.REPLY
        
        return None
    
    @staticmethod
    async def save_response(
        session: AsyncSession,
        order_id: int,
        group_id: int,
        driver_telegram_id: int,
        driver_username: Optional[str],
        driver_name: str,
        driver_phone: Optional[str],
        response_text: str,
        response_type: ResponseType,
        message_id: int,
        replied_to_message_id: Optional[int] = None
    ) -> DriverResponse:
        """
        Сохранение ответа водителя.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            group_id: ID группы
            driver_telegram_id: Telegram ID водителя
            driver_username: Username водителя
            driver_name: Имя водителя
            driver_phone: Телефон водителя
            response_text: Текст ответа
            response_type: Тип ответа
            message_id: ID сообщения
            replied_to_message_id: ID сообщения заказа (если reply)
            
        Returns:
            Сохраненный DriverResponse
        """
        response = DriverResponse(
            order_id=order_id,
            group_id=group_id,
            driver_telegram_id=driver_telegram_id,
            driver_username=driver_username,
            driver_name=driver_name,
            driver_phone=driver_phone,
            response_text=response_text,
            response_type=response_type,
            message_id=message_id,
            replied_to_message_id=replied_to_message_id,
            created_at=datetime.utcnow()
        )
        
        session.add(response)
        await session.commit()
        await session.refresh(response)
        
        logger.info(f"Response saved: order_id={order_id}, driver_id={driver_telegram_id}")
        return response
    
    @staticmethod
    async def get_responses(
        session: AsyncSession,
        order_id: int
    ) -> List[DriverResponse]:
        """
        Получение всех ответов на заказ.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            
        Returns:
            Список ответов, отсортированный по времени
        """
        result = await session.execute(
            select(DriverResponse)
            .where(DriverResponse.order_id == order_id)
            .order_by(DriverResponse.created_at)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_responses_by_driver(
        session: AsyncSession,
        order_id: int,
        driver_telegram_id: int
    ) -> List[DriverResponse]:
        """
        Получение всех ответов конкретного водителя на заказ.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            driver_telegram_id: Telegram ID водителя
            
        Returns:
            Список ответов водителя
        """
        result = await session.execute(
            select(DriverResponse)
            .where(
                DriverResponse.order_id == order_id,
                DriverResponse.driver_telegram_id == driver_telegram_id
            )
            .order_by(DriverResponse.created_at)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_unique_drivers(
        session: AsyncSession,
        order_id: int
    ) -> List[int]:
        """
        Получение списка уникальных водителей, ответивших на заказ.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            
        Returns:
            Список Telegram ID водителей
        """
        result = await session.execute(
            select(DriverResponse.driver_telegram_id)
            .where(DriverResponse.order_id == order_id)
            .distinct()
        )
        return [row[0] for row in result.all()]

