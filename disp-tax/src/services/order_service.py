"""Order service - бизнес-логика работы с заказами."""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models import Order, OrderState, Dispatcher
from src.fsm.order_fsm import OrderFSM, OrderFSMError


class OrderService:
    """Сервис для работы с заказами."""
    
    @staticmethod
    async def create_order(
        session: AsyncSession,
        dispatcher_id: int,
        content: str
    ) -> Order:
        """
        Создание нового заказа.
        
        Args:
            session: Сессия БД
            dispatcher_id: ID диспетчера
            content: Текст заказа
            
        Returns:
            Созданный Order в состоянии DRAFT
        """
        # Нормализация текста
        normalized_content = OrderService.normalize_content(content)
        
        # Создание заказа
        order = Order(
            dispatcher_id=dispatcher_id,
            state=OrderState.DRAFT,
            content=content,
            normalized_content=normalized_content,
            is_vip=False
        )
        
        session.add(order)
        await session.commit()
        await session.refresh(order)
        
        # Создание записи в истории
        await OrderFSM.transition(
            session=session,
            order_id=order.id,
            new_state=OrderState.DRAFT,
            changed_by=dispatcher_id,
            change_reason="Order created",
            changes={"content": content}
        )
        
        return order
    
    @staticmethod
    def normalize_content(content: str) -> str:
        """
        Нормализация текста заказа.
        
        Args:
            content: Исходный текст
            
        Returns:
            Нормализованный текст
        """
        # Удаление лишних пробелов
        normalized = " ".join(content.split())
        
        # Удаление пробелов в начале и конце
        normalized = normalized.strip()
        
        # Можно добавить другую нормализацию:
        # - Форматирование дат
        # - Нормализация адресов
        # - и т.д.
        
        return normalized
    
    @staticmethod
    async def preview_order(
        session: AsyncSession,
        order_id: int
    ) -> Dict[str, Any]:
        """
        Получение preview заказа.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            
        Returns:
            Словарь с информацией для preview
        """
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        # Переход в PREVIEW, если в DRAFT
        if order.state == OrderState.DRAFT:
            order = await OrderFSM.transition(
                session=session,
                order_id=order_id,
                new_state=OrderState.PREVIEW,
                changed_by=order.dispatcher_id,
                change_reason="Preview generated"
            )
        
        # Расчет риска (упрощенный)
        risk_level = "LOW"  # TODO: реализовать расчет риска
        
        return {
            "order_id": order.id,
            "content": order.content,
            "normalized_content": order.normalized_content,
            "state": order.state.value,
            "is_vip": order.is_vip,
            "estimated_groups": 0,  # TODO: получить из сценария
            "risk_level": risk_level
        }
    
    @staticmethod
    async def confirm_order(
        session: AsyncSession,
        order_id: int,
        dispatcher_id: int
    ) -> Order:
        """
        Подтверждение заказа.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            dispatcher_id: ID диспетчера
            
        Returns:
            Подтвержденный Order
        """
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.dispatcher_id != dispatcher_id:
            raise PermissionError("Only order owner can confirm")
        
        if order.state != OrderState.PREVIEW:
            raise OrderFSMError(f"Cannot confirm order in state {order.state.value}")
        
        return await OrderFSM.transition(
            session=session,
            order_id=order_id,
            new_state=OrderState.CONFIRMED,
            changed_by=dispatcher_id,
            change_reason="Order confirmed by dispatcher"
        )
    
    @staticmethod
    async def edit_order(
        session: AsyncSession,
        order_id: int,
        new_content: str,
        dispatcher_id: int
    ) -> Order:
        """
        Редактирование заказа.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            new_content: Новый текст заказа
            dispatcher_id: ID диспетчера
            
        Returns:
            Обновленный Order
        """
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.dispatcher_id != dispatcher_id:
            raise PermissionError("Only order owner can edit")
        
        if not OrderFSM.can_edit(order.state):
            raise OrderFSMError(f"Cannot edit order in state {order.state.value}")
        
        # Сохранение старого контента
        old_content = order.content
        old_normalized = order.normalized_content
        
        # Обновление контента
        order.content = new_content
        order.normalized_content = OrderService.normalize_content(new_content)
        order.updated_at = datetime.utcnow()
        
        # Если в DRAFT или PREVIEW, можно вернуться в DRAFT
        if order.state in [OrderState.DRAFT, OrderState.PREVIEW]:
            order.state = OrderState.DRAFT
        
        # Если в ACTIVE, остается в ACTIVE, но обновляются сообщения
        # (обновление сообщений будет в другом сервисе)
        
        await session.commit()
        await session.refresh(order)
        
        # Запись в историю
        await OrderFSM.transition(
            session=session,
            order_id=order_id,
            new_state=order.state,  # Остается в том же состоянии или DRAFT
            changed_by=dispatcher_id,
            change_reason="Order edited",
            changes={
                "old_content": old_content,
                "new_content": new_content,
                "old_normalized": old_normalized,
                "new_normalized": order.normalized_content
            }
        )
        
        return order
    
    @staticmethod
    async def cancel_order(
        session: AsyncSession,
        order_id: int,
        dispatcher_id: int,
        reason: Optional[str] = None
    ) -> Order:
        """
        Отмена заказа.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            dispatcher_id: ID диспетчера
            reason: Причина отмены (опционально)
            
        Returns:
            Отмененный Order
        """
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.dispatcher_id != dispatcher_id:
            raise PermissionError("Only order owner can cancel")
        
        if not OrderFSM.can_cancel(order.state):
            raise OrderFSMError(f"Cannot cancel order in state {order.state.value}")
        
        # Обновление всех сообщений в группах (помечаем как отмененные)
        if order.state in [OrderState.SENDING, OrderState.ACTIVE, OrderState.ASSIGNED]:
            from src.services.send_service import SendService
            cancelled_text = f"{order.normalized_content}\n\n❌ ЗАКАЗ ОТМЕНЕН"
            await SendService.update_all_messages(
                session=session,
                order_id=order_id,
                dispatcher_id=dispatcher_id,
                new_text=cancelled_text
            )
        
        return await OrderFSM.transition(
            session=session,
            order_id=order_id,
            new_state=OrderState.CANCELLED,
            changed_by=dispatcher_id,
            change_reason=reason or "Order cancelled by dispatcher"
        )
    
    @staticmethod
    async def close_order(
        session: AsyncSession,
        order_id: int,
        dispatcher_id: int
    ) -> Order:
        """
        Закрытие заказа.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            dispatcher_id: ID диспетчера
            
        Returns:
            Закрытый Order
        """
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.dispatcher_id != dispatcher_id:
            raise PermissionError("Only order owner can close")
        
        if not OrderFSM.can_close(order.state):
            raise OrderFSMError(f"Cannot close order in state {order.state.value}")
        
        # Обновление всех сообщений в группах (помечаем как закрытые)
        from src.services.send_service import SendService
        closed_text = f"{order.normalized_content}\n\n✅ ЗАКАЗ ЗАКРЫТ"
        await SendService.update_all_messages(
            session=session,
            order_id=order_id,
            dispatcher_id=dispatcher_id,
            new_text=closed_text
        )
        
        return await OrderFSM.transition(
            session=session,
            order_id=order_id,
            new_state=OrderState.CLOSED,
            changed_by=dispatcher_id,
            change_reason="Order closed by dispatcher"
        )
    
    @staticmethod
    async def get_order(
        session: AsyncSession,
        order_id: int
    ) -> Optional[Order]:
        """
        Получение заказа по ID.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            
        Returns:
            Order или None
        """
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_dispatcher_orders(
        session: AsyncSession,
        dispatcher_id: int,
        state: Optional[OrderState] = None
    ) -> list[Order]:
        """
        Получение заказов диспетчера.
        
        Args:
            session: Сессия БД
            dispatcher_id: ID диспетчера
            state: Фильтр по состоянию (опционально)
            
        Returns:
            Список заказов
        """
        query = select(Order).where(Order.dispatcher_id == dispatcher_id)
        
        if state:
            query = query.where(Order.state == state)
        
        query = query.order_by(Order.created_at.desc())
        
        result = await session.execute(query)
        return list(result.scalars().all())

