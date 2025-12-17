"""Service for sending orders to groups."""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models import Order, Group, GroupMessage, OrderState
from src.telethon_client.client_manager import client_manager
from src.services.anti_ban import anti_ban_service
from src.fsm.order_fsm import OrderFSM
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SendService:
    """Сервис для отправки заказов в группы."""
    
    @staticmethod
    async def send_order_to_groups(
        session: AsyncSession,
        order_id: int,
        group_ids: List[int],
        dispatcher_id: int,
        delay_min: int = 5,
        delay_max: int = 10,
        progress_callback: Optional[callable] = None
    ) -> bool:
        """
        Отправка заказа в группы с применением Anti-Ban логики.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            group_ids: Список ID групп
            dispatcher_id: ID диспетчера
            delay_min: Минимальная задержка
            delay_max: Максимальная задержка
            progress_callback: Функция для уведомления о прогрессе
            
        Returns:
            True если успешно отправлено во все группы
        """
        # Получение заказа
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            logger.error(f"Order {order_id} not found")
            return False
        
        if order.dispatcher_id != dispatcher_id:
            logger.error(f"Order {order_id} does not belong to dispatcher {dispatcher_id}")
            return False
        
        # Переход в состояние SENDING
        try:
            order = await OrderFSM.transition(
                session=session,
                order_id=order_id,
                new_state=OrderState.SENDING,
                changed_by=dispatcher_id,
                change_reason="Starting order send"
            )
        except Exception as e:
            logger.error(f"Error transitioning to SENDING: {e}")
            return False
        
        # Получение групп
        result = await session.execute(
            select(Group).where(
                Group.id.in_(group_ids),
                Group.dispatcher_id == dispatcher_id,
                Group.is_active == True
            )
        )
        groups = list(result.scalars().all())
        
        if not groups:
            logger.error(f"No active groups found for dispatcher {dispatcher_id}")
            return False
        
        success_count = 0
        failed_groups = []
        
        # Отправка в каждую группу
        for i, group in enumerate(groups, 1):
            if progress_callback:
                await progress_callback(f"Отправка {i}/{len(groups)}: {group.title}")
            
            async def send_to_group():
                """Функция отправки в группу."""
                message_id = await client_manager.send_message(
                    dispatcher_id=dispatcher_id,
                    chat_id=group.telegram_group_id,
                    message=order.normalized_content
                )
                return message_id
            
            # Отправка с Anti-Ban защитой
            message_id = await anti_ban_service.send_with_protection(
                send_func=send_to_group,
                min_delay=delay_min,
                max_delay=delay_max,
                notify_callback=progress_callback
            )
            
            if message_id:
                # Сохранение сообщения в БД
                group_message = GroupMessage(
                    order_id=order_id,
                    group_id=group.id,
                    telegram_message_id=message_id,
                    message_text=order.normalized_content,
                    sent_at=datetime.utcnow()
                )
                session.add(group_message)
                success_count += 1
            else:
                failed_groups.append(group.title)
                logger.warning(f"Failed to send to group {group.id}")
        
        await session.commit()
        
        # Переход в ACTIVE, если хотя бы одно сообщение отправлено
        if success_count > 0:
            try:
                order = await OrderFSM.transition(
                    session=session,
                    order_id=order_id,
                    new_state=OrderState.ACTIVE,
                    changed_by=dispatcher_id,
                    change_reason=f"Order sent to {success_count} groups"
                )
                
                if progress_callback:
                    await progress_callback(
                        f"✅ Заказ отправлен в {success_count}/{len(groups)} групп"
                    )
                
                if failed_groups:
                    logger.warning(f"Failed groups: {failed_groups}")
                
                return True
            except Exception as e:
                logger.error(f"Error transitioning to ACTIVE: {e}")
                return False
        else:
            # Все отправки провалились - отмена
            try:
                await OrderFSM.transition(
                    session=session,
                    order_id=order_id,
                    new_state=OrderState.CANCELLED,
                    changed_by=dispatcher_id,
                    change_reason="All sends failed"
                )
            except Exception as e:
                logger.error(f"Error cancelling order: {e}")
            
            return False
    
    @staticmethod
    async def update_all_messages(
        session: AsyncSession,
        order_id: int,
        dispatcher_id: int,
        new_text: str
    ) -> bool:
        """
        Обновление всех сообщений заказа в группах.
        
        Args:
            session: Сессия БД
            order_id: ID заказа
            dispatcher_id: ID диспетчера
            new_text: Новый текст
            
        Returns:
            True если успешно
        """
        # Получение всех сообщений заказа
        result = await session.execute(
            select(GroupMessage).where(
                GroupMessage.order_id == order_id,
                GroupMessage.is_deleted == False
            )
        )
        messages = list(result.scalars().all())
        
        if not messages:
            logger.warning(f"No messages found for order {order_id}")
            return True
        
        success_count = 0
        
        for group_message in messages:
            # Получение группы
            result = await session.execute(
                select(Group).where(Group.id == group_message.group_id)
            )
            group = result.scalar_one_or_none()
            
            if not group:
                continue
            
            # Обновление сообщения через Telethon
            success = await client_manager.edit_message(
                dispatcher_id=dispatcher_id,
                chat_id=group.telegram_group_id,
                message_id=group_message.telegram_message_id,
                new_text=new_text
            )
            
            if success:
                group_message.message_text = new_text
                group_message.updated_at = datetime.utcnow()
                success_count += 1
        
        await session.commit()
        
        logger.info(f"Updated {success_count}/{len(messages)} messages for order {order_id}")
        return success_count == len(messages)

