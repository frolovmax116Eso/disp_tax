"""Service for driver assignment."""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models import Assignment, Order, OrderState
from src.fsm.order_fsm import OrderFSM
from src.telethon_client.client_manager import client_manager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AssignmentService:
    """Сервис для назначения водителей."""
    
    @staticmethod
    async def assign_driver(
        session: AsyncSession,
        order_id: int,
        driver_telegram_id: int,
        driver_username: Optional[str],
        driver_name: str,
        assigned_by: int,
        reason: Optional[str] = None
    ) -> Assignment:
        """
        Назначение водителя на заказ.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            driver_telegram_id: Telegram ID водителя
            driver_username: Username водителя
            driver_name: Имя водителя
            assigned_by: Telegram ID диспетчера
            reason: Причина назначения (опционально)
            
        Returns:
            Созданное Assignment
        """
        # Получение заказа
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.dispatcher_id != assigned_by:
            raise PermissionError("Only order owner can assign driver")
        
        if not OrderFSM.can_assign_driver(order.state):
            raise ValueError(f"Cannot assign driver to order in state {order.state.value}")
        
        # Деактивация предыдущего назначения (если есть)
        result = await session.execute(
            select(Assignment).where(
                Assignment.order_id == order_id,
                Assignment.is_active == True
            )
        )
        previous_assignment = result.scalar_one_or_none()
        
        if previous_assignment:
            previous_assignment.is_active = False
            previous_assignment.unassigned_at = datetime.utcnow()
        
        # Создание нового назначения
        assignment = Assignment(
            order_id=order_id,
            driver_telegram_id=driver_telegram_id,
            driver_username=driver_username,
            driver_name=driver_name,
            assigned_by=assigned_by,
            reason=reason,
            is_active=True,
            assigned_at=datetime.utcnow()
        )
        
        session.add(assignment)
        
        # Переход заказа в ASSIGNED
        order = await OrderFSM.transition(
            session=session,
            order_id=order_id,
            new_state=OrderState.ASSIGNED,
            changed_by=assigned_by,
            change_reason=reason or "Driver assigned",
            changes={
                "driver_telegram_id": driver_telegram_id,
                "driver_name": driver_name
            }
        )
        
        await session.commit()
        await session.refresh(assignment)
        
        # Отправка "✅ Отдан Вам" в группу
        # TODO: Получить группу из ответа водителя
        # await client_manager.send_message(...)
        
        logger.info(f"Driver {driver_telegram_id} assigned to order {order_id}")
        return assignment
    
    @staticmethod
    async def change_driver(
        session: AsyncSession,
        order_id: int,
        new_driver_telegram_id: int,
        new_driver_username: Optional[str],
        new_driver_name: str,
        assigned_by: int,
        reason: str
    ) -> Assignment:
        """
        Смена назначенного водителя.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            new_driver_telegram_id: Telegram ID нового водителя
            new_driver_username: Username нового водителя
            new_driver_name: Имя нового водителя
            assigned_by: Telegram ID диспетчера
            reason: Причина смены (обязательно)
            
        Returns:
            Новое Assignment
        """
        if not reason:
            raise ValueError("Reason is required for driver change")
        
        # Деактивация текущего назначения и создание нового
        return await AssignmentService.assign_driver(
            session=session,
            order_id=order_id,
            driver_telegram_id=new_driver_telegram_id,
            driver_username=new_driver_username,
            driver_name=new_driver_name,
            assigned_by=assigned_by,
            reason=reason
        )
    
    @staticmethod
    async def get_active_assignment(
        session: AsyncSession,
        order_id: int
    ) -> Optional[Assignment]:
        """
        Получение активного назначения заказа.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            
        Returns:
            Assignment или None
        """
        result = await session.execute(
            select(Assignment).where(
                Assignment.order_id == order_id,
                Assignment.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_assignment_history(
        session: AsyncSession,
        order_id: int
    ) -> List[Assignment]:
        """
        Получение истории всех назначений заказа.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            
        Returns:
            Список назначений, отсортированный по времени
        """
        result = await session.execute(
            select(Assignment)
            .where(Assignment.order_id == order_id)
            .order_by(Assignment.assigned_at)
        )
        return list(result.scalars().all())

