"""Handlers for admin panel."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.admin_service import AdminService
from src.database.models import OrderState
import json

router = Router()


def admin_required(func):
    """Декоратор для проверки прав админа."""
    async def wrapper(message_or_callback, *args, **kwargs):
        user_id = message_or_callback.from_user.id if hasattr(message_or_callback, 'from_user') else message_or_callback.message.from_user.id
        
        if not AdminService.check_admin_access(user_id):
            if isinstance(message_or_callback, CallbackQuery):
                await message_or_callback.answer("❌ Доступ запрещен", show_alert=True)
            else:
                await message_or_callback.answer("❌ Доступ запрещен")
            return
        
        return await func(message_or_callback, *args, **kwargs)
    return wrapper


@router.message(F.text.in_(["/admin", "/a"]))
@admin_required
async def cmd_admin(message: Message, session: AsyncSession = None):
    """Главное меню админ-панели."""
    await AdminService.log_admin_action(
        session=session,
        admin_id=message.from_user.id,
        action="view_admin_menu"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Диспетчеры", callback_data="admin:dispatchers")],
        [InlineKeyboardButton(text="📋 Заказы", callback_data="admin:orders")],
        [InlineKeyboardButton(text="💬 Ответы", callback_data="admin:responses")],
        [InlineKeyboardButton(text="👥 Назначения", callback_data="admin:assignments")],
        [InlineKeyboardButton(text="📊 Логи", callback_data="admin:logs")],
        [InlineKeyboardButton(text="📈 Статистика", callback_data="admin:stats")]
    ])
    
    await message.answer(
        "🔧 Админ-панель\n\nВыберите раздел:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "admin:dispatchers")
@admin_required
async def admin_dispatchers(callback: CallbackQuery, session: AsyncSession):
    """Просмотр всех диспетчеров."""
    await AdminService.log_admin_action(
        session=session,
        admin_id=callback.from_user.id,
        action="view_dispatchers"
    )
    
    dispatchers = await AdminService.get_all_dispatchers(session=session)
    
    if not dispatchers:
        await callback.message.edit_text("👤 Диспетчеры не найдены")
        await callback.answer()
        return
    
    text = f"👤 Диспетчеры (всего: {len(dispatchers)})\n\n"
    
    for i, disp in enumerate(dispatchers[:10], 1):  # Показываем первые 10
        status = "✅ Активна" if disp.session_active else "❌ Неактивна"
        text += f"{i}. @{disp.username or 'N/A'} (ID: {disp.telegram_id})\n"
        text += f"   Имя: {disp.first_name} {disp.last_name or ''}\n"
        text += f"   Сессия: {status}\n"
        text += f"   Зарегистрирован: {disp.created_at.strftime('%Y-%m-%d')}\n\n"
    
    if len(dispatchers) > 10:
        text += f"... и еще {len(dispatchers) - 10} диспетчеров"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin:menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin:orders")
@admin_required
async def admin_orders(callback: CallbackQuery, session: AsyncSession):
    """Просмотр всех заказов."""
    await AdminService.log_admin_action(
        session=session,
        admin_id=callback.from_user.id,
        action="view_orders"
    )
    
    orders = await AdminService.get_all_orders(session=session)
    
    if not orders:
        await callback.message.edit_text("📋 Заказы не найдены")
        await callback.answer()
        return
    
    text = f"📋 Заказы (всего: {len(orders)})\n\n"
    
    for i, order in enumerate(orders[:10], 1):  # Показываем первые 10
        text += f"{i}. Заказ #{order.id}\n"
        text += f"   Диспетчер ID: {order.dispatcher_id}\n"
        text += f"   Состояние: {order.state.value}\n"
        text += f"   Создан: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        text += f"   Текст: {order.content[:50]}...\n\n"
    
    if len(orders) > 10:
        text += f"... и еще {len(orders) - 10} заказов"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin:menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin:responses")
@admin_required
async def admin_responses(callback: CallbackQuery, session: AsyncSession):
    """Просмотр всех ответов."""
    await AdminService.log_admin_action(
        session=session,
        admin_id=callback.from_user.id,
        action="view_responses"
    )
    
    responses = await AdminService.get_all_responses(session=session)
    
    if not responses:
        await callback.message.edit_text("💬 Ответы не найдены")
        await callback.answer()
        return
    
    text = f"💬 Ответы водителей (всего: {len(responses)})\n\n"
    
    for i, resp in enumerate(responses[:10], 1):  # Показываем первые 10
        text += f"{i}. Ответ #{resp.id}\n"
        text += f"   Заказ: #{resp.order_id}\n"
        text += f"   Водитель: @{resp.driver_username or 'N/A'} (ID: {resp.driver_telegram_id})\n"
        text += f"   Тип: {resp.response_type.value}\n"
        text += f"   Время: {resp.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
    
    if len(responses) > 10:
        text += f"... и еще {len(responses) - 10} ответов"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin:menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin:assignments")
@admin_required
async def admin_assignments(callback: CallbackQuery, session: AsyncSession):
    """Просмотр всех назначений."""
    await AdminService.log_admin_action(
        session=session,
        admin_id=callback.from_user.id,
        action="view_assignments"
    )
    
    assignments = await AdminService.get_all_assignments(session=session)
    
    if not assignments:
        await callback.message.edit_text("👥 Назначения не найдены")
        await callback.answer()
        return
    
    text = f"👥 Назначения (всего: {len(assignments)})\n\n"
    
    for i, assign in enumerate(assignments[:10], 1):  # Показываем первые 10
        status = "✅ Активно" if assign.is_active else "❌ Неактивно"
        text += f"{i}. Назначение #{assign.id}\n"
        text += f"   Заказ: #{assign.order_id}\n"
        text += f"   Водитель: @{assign.driver_username or 'N/A'} (ID: {assign.driver_telegram_id})\n"
        text += f"   Статус: {status}\n"
        text += f"   Назначено: {assign.assigned_at.strftime('%Y-%m-%d %H:%M')}\n\n"
    
    if len(assignments) > 10:
        text += f"... и еще {len(assignments) - 10} назначений"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin:menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
@admin_required
async def admin_stats(callback: CallbackQuery, session: AsyncSession):
    """Статистика системы."""
    await AdminService.log_admin_action(
        session=session,
        admin_id=callback.from_user.id,
        action="view_stats"
    )
    
    stats = await AdminService.get_statistics(session=session, period="today")
    
    text = f"📈 Статистика (сегодня)\n\n"
    text += f"👤 Диспетчеры:\n"
    text += f"   Всего: {stats['dispatchers']['total']}\n"
    text += f"   Активных: {stats['dispatchers']['active']}\n\n"
    text += f"📋 Заказы:\n"
    text += f"   Всего: {stats['orders']['total']}\n"
    text += f"   Активных: {stats['orders']['active']}\n"
    text += f"   Назначенных: {stats['orders']['assigned']}\n"
    text += f"   Закрытых: {stats['orders']['closed']}\n"
    text += f"   Отмененных: {stats['orders']['cancelled']}\n\n"
    text += f"💬 Ответы:\n"
    text += f"   Всего: {stats['responses']['total']}\n"
    text += f"   Среднее на заказ: {stats['responses']['avg_per_order']:.1f}\n\n"
    text += f"👥 Назначения:\n"
    text += f"   Всего: {stats['assignments']['total']}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin:menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin:menu")
@admin_required
async def admin_menu(callback: CallbackQuery):
    """Возврат в главное меню."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Диспетчеры", callback_data="admin:dispatchers")],
        [InlineKeyboardButton(text="📋 Заказы", callback_data="admin:orders")],
        [InlineKeyboardButton(text="💬 Ответы", callback_data="admin:responses")],
        [InlineKeyboardButton(text="👥 Назначения", callback_data="admin:assignments")],
        [InlineKeyboardButton(text="📊 Логи", callback_data="admin:logs")],
        [InlineKeyboardButton(text="📈 Статистика", callback_data="admin:stats")]
    ])
    
    await callback.message.edit_text(
        "🔧 Админ-панель\n\nВыберите раздел:",
        reply_markup=keyboard
    )
    await callback.answer()

