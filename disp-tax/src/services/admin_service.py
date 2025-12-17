"""Admin service - бизнес-логика админ-панели."""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.database.models import (
    Admin, Dispatcher, Order, DriverResponse, Assignment,
    OrderState, AdminAccessLog
)
from src.config import settings
import logging

logger = logging.getLogger(__name__)


class AdminService:
    """Сервис для работы админ-панели."""
    
    @staticmethod
    def check_admin_access(telegram_id: int) -> bool:
        """
        Проверка прав доступа админа.
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            True если админ, False иначе
        """
        return telegram_id in settings.admin_ids_list
    
    @staticmethod
    async def log_admin_action(
        session: AsyncSession,
        admin_id: int,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Логирование действия админа.
        
        Args:
            session: Сессия БД
            admin_id: Telegram ID админа
            action: Тип действия
            details: Детали действия (опционально)
        """
        # Получение или создание записи админа
        result = await session.execute(
            select(Admin).where(Admin.telegram_id == admin_id)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            # Создание записи админа (если еще нет в БД)
            admin = Admin(
                telegram_id=admin_id,
                first_name="Admin",
                is_active=True,
                last_access_at=datetime.utcnow()
            )
            session.add(admin)
            await session.flush()
        else:
            admin.last_access_at = datetime.utcnow()
        
        # Создание записи в логе
        log = AdminAccessLog(
            admin_id=admin.id,
            action=action,
            details=details or {},
            created_at=datetime.utcnow()
        )
        session.add(log)
        await session.commit()
    
    @staticmethod
    async def get_all_dispatchers(session: AsyncSession) -> List[Dispatcher]:
        """
        Получение всех диспетчеров.
        
        Args:
            session: Сессия БД
            
        Returns:
            Список диспетчеров
        """
        result = await session.execute(
            select(Dispatcher).order_by(Dispatcher.created_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_all_orders(
        session: AsyncSession,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Order]:
        """
        Получение всех заказов с фильтрацией.
        
        Args:
            session: Сессия БД
            filters: Словарь фильтров (dispatcher_id, state, date_from, date_to, vip)
            
        Returns:
            Список заказов
        """
        query = select(Order)
        
        if filters:
            if "dispatcher_id" in filters:
                query = query.where(Order.dispatcher_id == filters["dispatcher_id"])
            if "state" in filters:
                query = query.where(Order.state == filters["state"])
            if "vip" in filters:
                query = query.where(Order.is_vip == filters["vip"])
            if "date_from" in filters:
                query = query.where(Order.created_at >= filters["date_from"])
            if "date_to" in filters:
                query = query.where(Order.created_at <= filters["date_to"])
        
        query = query.order_by(Order.created_at.desc())
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_all_responses(
        session: AsyncSession,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[DriverResponse]:
        """
        Получение всех ответов с фильтрацией.
        
        Args:
            session: Сессия БД
            filters: Словарь фильтров (order_id, driver_id, date_from, date_to)
            
        Returns:
            Список ответов
        """
        query = select(DriverResponse)
        
        if filters:
            if "order_id" in filters:
                query = query.where(DriverResponse.order_id == filters["order_id"])
            if "driver_id" in filters:
                query = query.where(DriverResponse.driver_telegram_id == filters["driver_id"])
            if "date_from" in filters:
                query = query.where(DriverResponse.created_at >= filters["date_from"])
            if "date_to" in filters:
                query = query.where(DriverResponse.created_at <= filters["date_to"])
        
        query = query.order_by(DriverResponse.created_at.desc())
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_all_assignments(
        session: AsyncSession,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Assignment]:
        """
        Получение всех назначений с фильтрацией.
        
        Args:
            session: Сессия БД
            filters: Словарь фильтров (order_id, driver_id, active)
            
        Returns:
            Список назначений
        """
        query = select(Assignment)
        
        if filters:
            if "order_id" in filters:
                query = query.where(Assignment.order_id == filters["order_id"])
            if "driver_id" in filters:
                query = query.where(Assignment.driver_telegram_id == filters["driver_id"])
            if "active" in filters:
                query = query.where(Assignment.is_active == filters["active"])
        
        query = query.order_by(Assignment.assigned_at.desc())
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_statistics(
        session: AsyncSession,
        period: str = "today"
    ) -> Dict[str, Any]:
        """
        Получение статистики системы.
        
        Args:
            session: Сессия БД
            period: Период ("today", "week", "month", "all")
            
        Returns:
            Словарь со статистикой
        """
        now = datetime.utcnow()
        
        # Определение временных границ
        if period == "today":
            date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            date_from = now - timedelta(days=7)
        elif period == "month":
            date_from = now - timedelta(days=30)
        else:  # all
            date_from = None
        
        # Диспетчеры
        dispatchers_query = select(func.count(Dispatcher.id))
        if date_from:
            dispatchers_query = dispatchers_query.where(Dispatcher.created_at >= date_from)
        total_dispatchers = (await session.execute(dispatchers_query)).scalar()
        
        active_dispatchers_query = select(func.count(Dispatcher.id)).where(
            Dispatcher.session_active == True
        )
        active_dispatchers = (await session.execute(active_dispatchers_query)).scalar()
        
        # Заказы
        orders_query = select(func.count(Order.id))
        if date_from:
            orders_query = orders_query.where(Order.created_at >= date_from)
        total_orders = (await session.execute(orders_query)).scalar()
        
        # Заказы по состояниям
        active_orders = (await session.execute(
            select(func.count(Order.id)).where(Order.state == OrderState.ACTIVE)
        )).scalar()
        
        assigned_orders = (await session.execute(
            select(func.count(Order.id)).where(Order.state == OrderState.ASSIGNED)
        )).scalar()
        
        closed_orders = (await session.execute(
            select(func.count(Order.id)).where(Order.state == OrderState.CLOSED)
        )).scalar()
        
        cancelled_orders = (await session.execute(
            select(func.count(Order.id)).where(Order.state == OrderState.CANCELLED)
        )).scalar()
        
        # Ответы
        responses_query = select(func.count(DriverResponse.id))
        if date_from:
            responses_query = responses_query.where(DriverResponse.created_at >= date_from)
        total_responses = (await session.execute(responses_query)).scalar()
        
        # Назначения
        assignments_query = select(func.count(Assignment.id))
        if date_from:
            assignments_query = assignments_query.where(Assignment.assigned_at >= date_from)
        total_assignments = (await session.execute(assignments_query)).scalar()
        
        return {
            "period": period,
            "dispatchers": {
                "total": total_dispatchers,
                "active": active_dispatchers
            },
            "orders": {
                "total": total_orders,
                "active": active_orders,
                "assigned": assigned_orders,
                "closed": closed_orders,
                "cancelled": cancelled_orders
            },
            "responses": {
                "total": total_responses,
                "avg_per_order": total_responses / total_orders if total_orders > 0 else 0
            },
            "assignments": {
                "total": total_assignments
            }
        }

