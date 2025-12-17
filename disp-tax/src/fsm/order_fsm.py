"""Order FSM - управление жизненным циклом заказа."""
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models import Order, OrderState, OrderHistory


class OrderFSMError(Exception):
    """Ошибка FSM перехода."""
    pass


class OrderFSM:
    """Конечный автомат для управления состояниями заказа."""
    
    # Разрешенные переходы
    ALLOWED_TRANSITIONS: Dict[OrderState, list[OrderState]] = {
        OrderState.DRAFT: [OrderState.PREVIEW],
        OrderState.PREVIEW: [OrderState.DRAFT, OrderState.CONFIRMED],
        OrderState.CONFIRMED: [OrderState.SENDING, OrderState.CANCELLED],
        OrderState.SENDING: [OrderState.ACTIVE, OrderState.CANCELLED],
        OrderState.ACTIVE: [OrderState.ASSIGNED, OrderState.CANCELLED, OrderState.ACTIVE],  # ACTIVE для редактирования
        OrderState.ASSIGNED: [OrderState.CLOSED, OrderState.CANCELLED, OrderState.ASSIGNED],  # ASSIGNED для смены водителя
        OrderState.CLOSED: [],  # Конечное состояние
        OrderState.CANCELLED: [],  # Конечное состояние
    }
    
    @staticmethod
    def can_transition(current_state: OrderState, new_state: OrderState) -> bool:
        """
        Проверка возможности перехода между состояниями.
        
        Args:
            current_state: Текущее состояние
            new_state: Новое состояние
            
        Returns:
            True если переход разрешен, False иначе
        """
        allowed = OrderFSM.ALLOWED_TRANSITIONS.get(current_state, [])
        return new_state in allowed
    
    @staticmethod
    async def transition(
        session: AsyncSession,
        order_id: int,
        new_state: OrderState,
        changed_by: int,
        change_reason: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None
    ) -> Order:
        """
        Переход заказа в новое состояние.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            new_state: Новое состояние
            changed_by: Telegram ID того, кто изменил
            change_reason: Причина изменения (опционально)
            changes: Детали изменений (опционально)
            
        Returns:
            Обновленный Order
            
        Raises:
            OrderFSMError: Если переход невозможен
        """
        # Получение заказа
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise OrderFSMError(f"Order {order_id} not found")
        
        # Проверка возможности перехода
        if not OrderFSM.can_transition(order.state, new_state):
            raise OrderFSMError(
                f"Cannot transition from {order.state.value} to {new_state.value}"
            )
        
        # Сохранение старого состояния
        old_state = order.state
        
        # Обновление состояния
        order.state = new_state
        order.updated_at = datetime.utcnow()
        
        # Обновление специальных полей в зависимости от состояния
        if new_state == OrderState.CONFIRMED:
            order.confirmed_at = datetime.utcnow()
        elif new_state == OrderState.ACTIVE:
            if not order.sent_at:
                order.sent_at = datetime.utcnow()
        elif new_state in [OrderState.CLOSED, OrderState.CANCELLED]:
            order.closed_at = datetime.utcnow()
        
        # Создание записи в истории
        history = OrderHistory(
            order_id=order_id,
            old_state=old_state,
            new_state=new_state,
            changed_by=changed_by,
            change_reason=change_reason,
            changes=changes or {}
        )
        session.add(history)
        
        await session.commit()
        await session.refresh(order)
        
        return order
    
    @staticmethod
    async def get_order_history(
        session: AsyncSession,
        order_id: int
    ) -> list[OrderHistory]:
        """
        Получение истории изменений заказа.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            
        Returns:
            Список записей истории, отсортированный по времени
        """
        result = await session.execute(
            select(OrderHistory)
            .where(OrderHistory.order_id == order_id)
            .order_by(OrderHistory.created_at)
        )
        return list(result.scalars().all())
    
    @staticmethod
    def is_final_state(state: OrderState) -> bool:
        """
        Проверка, является ли состояние конечным.
        
        Args:
            state: Состояние для проверки
            
        Returns:
            True если состояние конечное
        """
        return state in [OrderState.CLOSED, OrderState.CANCELLED]
    
    @staticmethod
    def can_edit(state: OrderState) -> bool:
        """
        Проверка, можно ли редактировать заказ в данном состоянии.
        
        Args:
            state: Состояние заказа
            
        Returns:
            True если можно редактировать
        """
        return state in [OrderState.DRAFT, OrderState.PREVIEW, OrderState.ACTIVE]
    
    @staticmethod
    def can_cancel(state: OrderState) -> bool:
        """
        Проверка, можно ли отменить заказ в данном состоянии.
        
        Args:
            state: Состояние заказа
            
        Returns:
            True если можно отменить
        """
        return state not in [OrderState.CLOSED, OrderState.CANCELLED]
    
    @staticmethod
    def can_assign_driver(state: OrderState) -> bool:
        """
        Проверка, можно ли назначить водителя в данном состоянии.
        
        Args:
            state: Состояние заказа
            
        Returns:
            True если можно назначить
        """
        return state == OrderState.ACTIVE
    
    @staticmethod
    def can_close(state: OrderState) -> bool:
        """
        Проверка, можно ли закрыть заказ в данном состоянии.
        
        Args:
            state: Состояние заказа
            
        Returns:
            True если можно закрыть
        """
        return state == OrderState.ASSIGNED

