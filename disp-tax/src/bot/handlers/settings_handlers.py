"""Handlers for settings."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.database.models import Dispatcher, Group, Region
from src.services.order_service import OrderService
from src.utils.error_format import format_error_for_user
from src.bot.fsm_states import GroupAdd
from src.bot.keyboards import get_main_keyboard
import logging
import asyncio
import os

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text.in_(["/settings", "⚙️ Настройки"]))
async def cmd_settings(message: Message, session: AsyncSession):
    """Обработчик команды /settings."""
    # Создаем фиктивный callback для использования существующего handler
    from aiogram.types import CallbackQuery
    from unittest.mock import MagicMock
    
    # Используем существующий handler
    result = await session.execute(
        select(Dispatcher).where(Dispatcher.telegram_id == message.from_user.id)
    )
    dispatcher = result.scalar_one_or_none()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="settings:profile")],
        [InlineKeyboardButton(text="📁 Группы", callback_data="settings:groups")],
        [InlineKeyboardButton(text="🌍 Регионы", callback_data="settings:regions")],
        [InlineKeyboardButton(text="📋 Сценарии", callback_data="settings:scenarios")],
        [InlineKeyboardButton(text="🔐 Авторизация", callback_data="settings:auth")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
    
    status = "✅ Авторизован" if dispatcher and dispatcher.session_active else "❌ Не авторизован"
    
    groups_count = 0
    regions_count = 0
    if dispatcher:
        try:
            from src.database.models import Group, Region
            groups_result = await session.execute(
                select(func.count(Group.id)).where(Group.dispatcher_id == dispatcher.id)
            )
            groups_count = groups_result.scalar() or 0
            regions_result = await session.execute(
                select(func.count(Region.id)).where(Region.dispatcher_id == dispatcher.id)
            )
            regions_count = regions_result.scalar() or 0
        except:
            pass
    
    await message.answer(
        f"⚙️ Настройки\n\n"
        f"Статус: {status}\n"
        f"Групп: {groups_count}\n"
        f"Регионов: {regions_count}\n\n"
        f"Выберите раздел:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "settings")
async def settings_menu(callback: CallbackQuery, session: AsyncSession):
    """Главное меню настроек."""
    try:
        # Проверка, зарегистрирован ли диспетчер
        result = await session.execute(
            select(Dispatcher).where(Dispatcher.telegram_id == callback.from_user.id)
        )
        dispatcher = result.scalar_one_or_none()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Профиль", callback_data="settings:profile")],
            [InlineKeyboardButton(text="📁 Группы", callback_data="settings:groups")],
            [InlineKeyboardButton(text="🌍 Регионы", callback_data="settings:regions")],
            [InlineKeyboardButton(text="📋 Сценарии", callback_data="settings:scenarios")],
            [InlineKeyboardButton(text="🔐 Авторизация", callback_data="settings:auth")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
        
        status = "✅ Авторизован" if dispatcher and dispatcher.session_active else "❌ Не авторизован"
        
        # Безопасный подсчет групп и регионов
        groups_count = 0
        regions_count = 0
        if dispatcher:
            try:
                from src.database.models import Group, Region
                groups_result = await session.execute(
                    select(func.count(Group.id)).where(Group.dispatcher_id == dispatcher.id)
                )
                groups_count = groups_result.scalar() or 0
                regions_result = await session.execute(
                    select(func.count(Region.id)).where(Region.dispatcher_id == dispatcher.id)
                )
                regions_count = regions_result.scalar() or 0
            except:
                pass
        
        await callback.message.edit_text(
            f"⚙️ Настройки\n\n"
            f"Статус: {status}\n"
            f"Групп: {groups_count}\n"
            f"Регионов: {regions_count}\n\n"
            f"Выберите раздел:",
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in settings menu: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data == "settings:profile")
async def settings_profile(callback: CallbackQuery, session: AsyncSession):
    """Настройки профиля."""
    try:
        result = await session.execute(
            select(Dispatcher).where(Dispatcher.telegram_id == callback.from_user.id)
        )
        dispatcher = result.scalar_one_or_none()
        
        if not dispatcher:
            text = "👤 Профиль\n\nВы еще не зарегистрированы в системе."
        else:
            # Безопасный доступ к relationships
            orders_count = 0
            try:
                from src.database.models import Order
                result = await session.execute(
                    select(func.count(Order.id)).where(Order.dispatcher_id == dispatcher.id)
                )
                orders_count = result.scalar() or 0
            except:
                pass
            
            text = f"👤 Профиль\n\n"
            text += f"ID: {dispatcher.telegram_id}\n"
            text += f"Имя: {dispatcher.first_name} {dispatcher.last_name or ''}\n"
            text += f"Username: @{dispatcher.username or 'не указан'}\n"
            text += f"Сессия: {'✅ Активна' if dispatcher.session_active else '❌ Неактивна'}\n"
            text += f"Заказов: {orders_count}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="settings")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in profile: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data == "settings:groups")
async def settings_groups(callback: CallbackQuery, session: AsyncSession):
    """Управление группами."""
    try:
        result = await session.execute(
            select(Dispatcher).where(Dispatcher.telegram_id == callback.from_user.id)
        )
        dispatcher = result.scalar_one_or_none()
        
        if not dispatcher:
            text = "📁 Группы\n\nСначала нужно авторизоваться."
        else:
            # Безопасный доступ к группам
            from src.database.models import Group
            result = await session.execute(
                select(Group).where(Group.dispatcher_id == dispatcher.id)
            )
            groups = list(result.scalars().all())
            
            text = f"📁 Группы (всего: {len(groups)})\n\n"
            
            if groups:
                for i, group in enumerate(groups[:8], 1):  # Ограничиваем до 8
                    status = "✅" if group.is_active else "❌"
                    text += f"{status} {group.title[:30]}\n"
                    if len(text) > 3500:  # Проверка длины
                        text += f"\n... и еще {len(groups) - i} групп"
                        break
            else:
                text += "Группы не добавлены.\n"
                text += "Добавьте группы через авторизацию."
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить группу", callback_data="settings:add_group")],
            [InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="settings")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in groups: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data == "settings:add_group")
async def add_group_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начало добавления группы - показываем список групп пользователя."""
    try:
        from src.telethon_client.client_manager import client_manager
        
        result = await session.execute(
            select(Dispatcher).where(Dispatcher.telegram_id == callback.from_user.id)
        )
        dispatcher = result.scalar_one_or_none()
        
        if not dispatcher:
            await callback.answer("Сначала нужно авторизоваться", show_alert=True)
            return
        
        # Проверяем авторизацию Telethon
        is_authorized, error = await client_manager.check_qr_login_status(callback.from_user.id)
        if not is_authorized:
            await callback.answer(
                "Сначала авторизуйтесь через QR-код в настройках",
                show_alert=True
            )
            return
        
        await callback.message.edit_text("⏳ Загрузка списка групп...")
        await callback.answer()
        
        # Получаем список всех групп пользователя
        user_groups = await client_manager.get_user_groups(callback.from_user.id)
        
        if not user_groups:
            await callback.message.edit_text(
                "❌ Группы не найдены\n\n"
                "Убедитесь, что:\n"
                "• Вы авторизованы через QR-код\n"
                "• У вас есть группы в Telegram"
            )
            return
        
        # Получаем уже добавленные группы
        existing_groups_result = await session.execute(
            select(Group).where(Group.dispatcher_id == dispatcher.id)
        )
        existing_groups = {g.telegram_group_id: g for g in existing_groups_result.scalars().all()}
        
        # Сохраняем список групп в state
        await state.set_state(GroupAdd.input_group)
        await state.update_data(
            dispatcher_id=dispatcher.id,
            groups=user_groups,
            selected_groups={},  # {group_id: True/False}
            page=0
        )
        
        # Показываем список групп с чекбоксами
        await show_groups_selection(callback.message, state, session, user_groups, existing_groups, page=0)
        
    except Exception as e:
        logger.error(f"Error starting add group: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


async def show_groups_selection(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user_groups: list,
    existing_groups: dict,
    page: int = 0
):
    """Показ списка групп с чекбоксами."""
    from src.database.models import Group
    
    state_data = await state.get_data()
    selected_groups = state_data.get("selected_groups", {})
    
    # Пагинация: по 10 групп на страницу
    groups_per_page = 10
    start_idx = page * groups_per_page
    end_idx = start_idx + groups_per_page
    page_groups = user_groups[start_idx:end_idx]
    total_pages = (len(user_groups) + groups_per_page - 1) // groups_per_page
    
    text = f"📁 Выберите группы ({len(user_groups)} доступно)\n\n"
    
    buttons = []
    for group in page_groups:
        group_id = group['id']
        is_existing = group_id in existing_groups
        is_selected = selected_groups.get(str(group_id), False)
        
        # Определяем статус
        if is_existing:
            existing_group = existing_groups[group_id]
            status = "✅" if existing_group.is_active else "⚪"
            label = f"{status} {group['title'][:30]}"
        else:
            status = "☑️" if is_selected else "☐"
            label = f"{status} {group['title'][:30]}"
        
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"group:toggle:{group_id}"
        )])
    
    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"group:page:{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"group:page:{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Кнопки действий
    selected_count = sum(1 for v in selected_groups.values() if v)
    buttons.append([
        InlineKeyboardButton(
            text=f"💾 Сохранить ({selected_count})",
            callback_data="group:save"
        )
    ])
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="group:cancel")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    text += f"Страница {page + 1} из {total_pages}\n"
    text += f"Выбрано: {selected_count}"
    
    await message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("group:toggle:"))
async def toggle_group_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Переключение выбора группы."""
    try:
        group_id = int(callback.data.split(":")[-1])
        
        state_data = await state.get_data()
        selected_groups = state_data.get("selected_groups", {})
        user_groups = state_data.get("groups", [])
        dispatcher_id = state_data.get("dispatcher_id")
        
        # Переключаем выбор
        group_id_str = str(group_id)
        selected_groups[group_id_str] = not selected_groups.get(group_id_str, False)
        
        await state.update_data(selected_groups=selected_groups)
        
        # Получаем уже добавленные группы
        existing_groups_result = await session.execute(
            select(Group).where(Group.dispatcher_id == dispatcher_id)
        )
        existing_groups = {g.telegram_group_id: g for g in existing_groups_result.scalars().all()}
        
        # Обновляем страницу
        page = state_data.get("page", 0)
        await show_groups_selection(callback.message, state, session, user_groups, existing_groups, page)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error toggling group: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data.startswith("group:page:"))
async def change_groups_page(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Смена страницы списка групп."""
    try:
        page = int(callback.data.split(":")[-1])
        
        state_data = await state.get_data()
        user_groups = state_data.get("groups", [])
        dispatcher_id = state_data.get("dispatcher_id")
        
        await state.update_data(page=page)
        
        # Получаем уже добавленные группы
        existing_groups_result = await session.execute(
            select(Group).where(Group.dispatcher_id == dispatcher_id)
        )
        existing_groups = {g.telegram_group_id: g for g in existing_groups_result.scalars().all()}
        
        await show_groups_selection(callback.message, state, session, user_groups, existing_groups, page)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error changing page: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data == "group:save")
async def save_selected_groups(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Сохранение выбранных групп."""
    try:
        from src.database.models import Group
        from datetime import datetime
        
        state_data = await state.get_data()
        selected_groups = state_data.get("selected_groups", {})
        user_groups = state_data.get("groups", [])
        dispatcher_id = state_data.get("dispatcher_id")
        
        if not selected_groups:
            await callback.answer("Выберите хотя бы одну группу", show_alert=True)
            return
        
        # Получаем уже добавленные группы
        existing_groups_result = await session.execute(
            select(Group).where(Group.dispatcher_id == dispatcher_id)
        )
        existing_groups = {g.telegram_group_id: g for g in existing_groups_result.scalars().all()}
        
        saved_count = 0
        updated_count = 0
        
        # Сохраняем выбранные группы
        for group in user_groups:
            group_id = group['id']
            if selected_groups.get(str(group_id), False):
                if group_id in existing_groups:
                    # Обновляем существующую группу
                    existing_group = existing_groups[group_id]
                    existing_group.is_active = True
                    existing_group.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    # Создаем новую группу
                    new_group = Group(
                        dispatcher_id=dispatcher_id,
                        telegram_group_id=group_id,
                        title=group['title'],
                        is_active=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(new_group)
                    saved_count += 1
        
        await session.commit()
        await state.clear()
        
        await callback.message.edit_text(
            f"✅ Группы сохранены!\n\n"
            f"Добавлено: {saved_count}\n"
            f"Обновлено: {updated_count}"
        )
        await callback.answer("Группы сохранены!")
        
    except Exception as e:
        logger.error(f"Error saving groups: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data == "group:cancel")
async def cancel_group_selection(callback: CallbackQuery, state: FSMContext):
    """Отмена выбора групп."""
    try:
        await state.clear()
        await callback.message.edit_text("❌ Добавление групп отменено")
        await callback.answer()
    except Exception as e:
        logger.error(f"Error cancelling group selection: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.message(GroupAdd.input_group)
async def process_group_input_old(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка текстовых сообщений во время выбора групп (запасной вариант)."""
    # Если пользователь отправил текст, просто показываем подсказку
    await message.answer(
        "💡 Используйте кнопки выше для выбора групп.\n\n"
        "Или нажмите /cancel для отмены."
    )


@router.message(F.text == "/cancel")
async def cancel_group_add(message: Message, state: FSMContext):
    """Отмена добавления группы."""
    current_state = await state.get_state()
    if current_state and current_state.startswith("GroupAdd"):
        await state.clear()
        await message.answer("❌ Добавление группы отменено")
    else:
        await message.answer("Нет активного процесса для отмены")


@router.callback_query(F.data == "settings:regions")
async def settings_regions(callback: CallbackQuery, session: AsyncSession):
    """Управление регионами."""
    try:
        result = await session.execute(
            select(Dispatcher).where(Dispatcher.telegram_id == callback.from_user.id)
        )
        dispatcher = result.scalar_one_or_none()
        
        if not dispatcher:
            text = "🌍 Регионы\n\nСначала нужно авторизоваться."
        else:
            # Безопасный доступ к регионам
            from src.database.models import Region, Group
            result = await session.execute(
                select(Region).where(Region.dispatcher_id == dispatcher.id)
            )
            regions = list(result.scalars().all())
            
            text = f"🌍 Регионы (всего: {len(regions)})\n\n"
            
            if regions:
                for i, region in enumerate(regions[:8], 1):  # Ограничиваем
                    text += f"{i}. {region.name}\n"
                    if region.description:
                        text += f"   {region.description[:40]}...\n"
                    # Подсчет групп
                    group_result = await session.execute(
                        select(func.count(Group.id)).where(Group.region_id == region.id)
                    )
                    group_count = group_result.scalar() or 0
                    text += f"   Групп: {group_count}\n\n"
                    if len(text) > 3500:
                        text += f"\n... и еще {len(regions) - i} регионов"
                        break
            else:
                text += "Регионы не созданы.\n"
                text += "Создайте регион для группировки групп."
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать регион", callback_data="settings:add_region")],
            [InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="settings")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in regions: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data == "settings:scenarios")
async def settings_scenarios(callback: CallbackQuery, session: AsyncSession):
    """Управление сценариями."""
    try:
        result = await session.execute(
            select(Dispatcher).where(Dispatcher.telegram_id == callback.from_user.id)
        )
        dispatcher = result.scalar_one_or_none()
        
        if not dispatcher:
            text = "📋 Сценарии\n\nСначала нужно авторизоваться."
        else:
            # Безопасный доступ к сценариям
            from src.database.models import Scenario
            result = await session.execute(
                select(Scenario).where(Scenario.dispatcher_id == dispatcher.id)
            )
            scenarios = list(result.scalars().all())
            
            text = f"📋 Сценарии отправки (всего: {len(scenarios)})\n\n"
            
            if scenarios:
                for i, scenario in enumerate(scenarios[:8], 1):  # Ограничиваем
                    group_ids = scenario.group_ids if isinstance(scenario.group_ids, list) else []
                    text += f"{i}. {scenario.name[:30]}\n"
                    text += f"   Групп: {len(group_ids)}\n"
                    text += f"   Задержка: {scenario.delay_min}-{scenario.delay_max}с\n\n"
                    if len(text) > 3500:
                        text += f"\n... и еще {len(scenarios) - i} сценариев"
                        break
            else:
                text += "Сценарии не созданы.\n"
                text += "Создайте сценарий для быстрой отправки заказов."
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать сценарий", callback_data="settings:add_scenario")],
            [InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="settings")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in scenarios: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data == "settings:auth")
async def settings_auth(callback: CallbackQuery, session: AsyncSession):
    """Авторизация через QR."""
    try:
        from src.telethon_client.client_manager import client_manager
        from src.database.models import Dispatcher
        from datetime import datetime
        from aiogram.types import BufferedInputFile
        
        result = await session.execute(
            select(Dispatcher).where(Dispatcher.telegram_id == callback.from_user.id)
        )
        dispatcher = result.scalar_one_or_none()
        
        # Проверяем статус авторизации
        if dispatcher:
            is_authorized, error = await client_manager.check_qr_login_status(callback.from_user.id)
            if is_authorized:
                # Обновляем статус в БД
                dispatcher.session_active = True
                dispatcher.updated_at = datetime.utcnow()
                await session.commit()
                
                text = "🔐 Авторизация\n\n"
                text += "✅ Вы уже авторизованы.\n"
                text += "Сессия активна и готова к работе."
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="settings")]
                ])
                
                await callback.message.edit_text(text, reply_markup=keyboard)
                await callback.answer()
                return
        
        # Если не авторизован - запускаем QR-авторизацию
        await callback.message.edit_text("🔐 Инициализация авторизации...")
        await callback.answer()
        
        # Создаем или получаем диспетчера
        if not dispatcher:
            from src.config import settings
            session_path = os.path.join(settings.SESSIONS_DIR, f"dispatcher_{callback.from_user.id}.session")
            
            dispatcher = Dispatcher(
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name or "Unknown",
                last_name=callback.from_user.last_name,
                session_file=session_path,
                session_active=False
            )
            session.add(dispatcher)
            await session.commit()
            await session.refresh(dispatcher)
        
        # Запускаем QR-авторизацию
        qr_result = await client_manager.start_qr_login(callback.from_user.id)
        
        if not qr_result:
            await callback.message.edit_text(
                "❌ Ошибка при инициализации авторизации.\n"
                "Возможно, вы уже авторизованы. Попробуйте проверить статус."
            )
            return
        
        qr_login, qr_image_bytes = qr_result
        
        # Отправляем QR-код
        text = "🔐 Авторизация через QR-код\n\n"
        text += "1. Откройте приложение Telegram на телефоне\n"
        text += "2. Перейдите в Настройки → Устройства → Подключить устройство\n"
        text += "3. Отсканируйте QR-код ниже\n\n"
        text += "⏳ Ожидание авторизации..."
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Проверить статус", callback_data="auth:check")],
            [InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="settings")]
        ])
        
        # Отправляем QR-код как фото
        photo = BufferedInputFile(qr_image_bytes, filename="qr_code.png")
        await callback.message.delete()  # Удаляем предыдущее сообщение
        await callback.message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=keyboard
        )
        
        # Запускаем фоновую задачу для проверки статуса
        asyncio.create_task(check_auth_status_periodically(
            callback.from_user.id,
            callback.message.chat.id,
            session,
            qr_login
        ))
        
    except Exception as e:
        logger.error(f"Error in auth: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


async def check_auth_status_periodically(dispatcher_id: int, chat_id: int, session: AsyncSession, qr_login):
    """Фоновая задача для проверки статуса авторизации."""
    from src.telethon_client.client_manager import client_manager
    from src.database.models import Dispatcher
    from datetime import datetime
    from aiogram import Bot
    from src.config import settings
    
    bot = Bot(token=settings.BOT_TOKEN)
    
    try:
        # Ждем завершения авторизации через QR-код
        try:
            await asyncio.wait_for(qr_login.wait(), timeout=300)  # 5 минут таймаут
            
            # Проверяем статус
            is_authorized, error = await client_manager.check_qr_login_status(dispatcher_id)
            
            if is_authorized:
                # Обновляем статус в БД
                result = await session.execute(
                    select(Dispatcher).where(Dispatcher.telegram_id == dispatcher_id)
                )
                dispatcher = result.scalar_one_or_none()
                
                if dispatcher:
                    dispatcher.session_active = True
                    dispatcher.updated_at = datetime.utcnow()
                    await session.commit()
                
                # Отправляем уведомление
                await bot.send_message(
                    chat_id=chat_id,
                    text="✅ Авторизация успешна!\n\n"
                         "Сессия активирована и готова к работе."
                )
            elif error and "password" in error.lower():
                await bot.send_message(
                    chat_id=chat_id,
                    text="🔐 Требуется пароль двухфакторной аутентификации.\n\n"
                         "Используйте команду /auth_password для ввода пароля."
                )
        except asyncio.TimeoutError:
            await bot.send_message(
                chat_id=chat_id,
                text="⏱️ Время ожидания авторизации истекло.\n\n"
                     "Попробуйте начать авторизацию заново."
            )
    except Exception as e:
        logger.error(f"Error in auth status check: {e}")
    finally:
        await bot.session.close()


@router.callback_query(F.data == "auth:check")
async def check_auth_status(callback: CallbackQuery, session: AsyncSession):
    """Проверка статуса авторизации."""
    try:
        from src.telethon_client.client_manager import client_manager
        from src.database.models import Dispatcher
        from datetime import datetime
        
        is_authorized, error = await client_manager.check_qr_login_status(callback.from_user.id)
        
        if is_authorized:
            # Обновляем статус в БД
            result = await session.execute(
                select(Dispatcher).where(Dispatcher.telegram_id == callback.from_user.id)
            )
            dispatcher = result.scalar_one_or_none()
            
            if dispatcher:
                dispatcher.session_active = True
                dispatcher.updated_at = datetime.utcnow()
                await session.commit()
            
            text = "✅ Авторизация успешна!\n\n"
            text += "Сессия активирована и готова к работе."
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="settings")]
            ])
            
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer("Авторизация успешна!")
        else:
            text = "⏳ Авторизация еще не завершена.\n\n"
            if error:
                text += f"Статус: {error}\n\n"
            text += "Продолжайте ожидание или отсканируйте QR-код еще раз."
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Проверить снова", callback_data="auth:check")],
                [InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="settings")]
            ])
            
            await callback.message.edit_caption(caption=text, reply_markup=keyboard)
            await callback.answer("Ожидание авторизации...")
            
    except Exception as e:
        logger.error(f"Error checking auth status: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data.startswith("order:view:"))
async def view_order_handler(callback: CallbackQuery, session: AsyncSession):
    """Просмотр деталей заказа."""
    try:
        order_id = int(callback.data.split(":")[-1])
        order = await OrderService.get_order(session=session, order_id=order_id)
        
        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        
        if order.dispatcher_id != callback.from_user.id:
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        state_emoji = {
            "draft": "📝",
            "preview": "👁️",
            "confirmed": "✅",
            "sending": "📤",
            "active": "🟢",
            "assigned": "👤",
            "closed": "🔒",
            "cancelled": "❌"
        }
        emoji = state_emoji.get(order.state.value, "📋")
        
        text = f"{emoji} Заказ #{order.id}\n\n"
        text += f"Состояние: {order.state.value}\n"
        text += f"Создан: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        text += f"Текст:\n{order.content[:500]}"
        
        if len(order.content) > 500:
            text += "..."
        
        buttons = []
        
        # Кнопки действий в зависимости от состояния
        if order.state.value in ["draft", "preview"]:
            buttons.append([InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"order:edit:{order.id}")])
        if order.state.value == "preview":
            buttons.append([InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"order:confirm:{order.id}")])
        if order.state.value == "confirmed":
            buttons.append([InlineKeyboardButton(text="📤 Отправить", callback_data=f"order:send:{order.id}")])
        if order.state.value == "active":
            buttons.append([InlineKeyboardButton(text="👥 Ответы", callback_data=f"order:responses:{order.id}")])
            buttons.append([InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"order:edit:{order.id}")])
        if order.state.value == "assigned":
            buttons.append([InlineKeyboardButton(text="✅ Закрыть", callback_data=f"order:close:{order.id}")])
        
        buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data=f"order:cancel_order:{order.id}")])
        buttons.append([InlineKeyboardButton(text="🔙 Назад к списку", callback_data="order:list")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error viewing order: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data.startswith("order:close:"))
async def close_order_callback(callback: CallbackQuery, session: AsyncSession):
    """Закрытие заказа."""
    try:
        order_id = int(callback.data.split(":")[-1])
        
        order = await OrderService.close_order(
            session=session,
            order_id=order_id,
            dispatcher_id=callback.from_user.id
        )
        
        await callback.message.edit_text(
            f"✅ Заказ #{order.id} закрыт!"
        )
        await callback.answer("Заказ закрыт")
    except Exception as e:
        logger.error(f"Error closing order: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data.startswith("order:cancel_order:"))
async def cancel_order_callback(callback: CallbackQuery, session: AsyncSession):
    """Отмена заказа."""
    try:
        order_id = int(callback.data.split(":")[-1])
        
        order = await OrderService.cancel_order(
            session=session,
            order_id=order_id,
            dispatcher_id=callback.from_user.id,
            reason="Отменено через бота"
        )
        
        await callback.message.edit_text(
            f"❌ Заказ #{order.id} отменен!"
        )
        await callback.answer("Заказ отменен")
    except Exception as e:
        logger.error(f"Error cancelling order: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data.startswith("order:responses:"))
async def view_order_responses(callback: CallbackQuery, session: AsyncSession):
    """Просмотр ответов на заказ."""
    try:
        from src.services.response_service import ResponseService
        
        order_id = int(callback.data.split(":")[-1])
        responses = await ResponseService.get_responses(session=session, order_id=order_id)
        
        if not responses:
            await callback.message.edit_text(
                f"💬 Ответы на заказ #{order_id}\n\n"
                f"Пока нет ответов от водителей."
            )
            await callback.answer()
            return
        
        text = f"💬 Ответы на заказ #{order_id}\n"
        text += f"Всего: {len(responses)}\n\n"
        
        # Группируем по водителям
        from collections import defaultdict
        drivers_responses = defaultdict(list)
        for resp in responses:
            drivers_responses[resp.driver_telegram_id].append(resp)
        
        # Ограничиваем до 4 водителей для краткости
        for driver_id, driver_resps in list(drivers_responses.items())[:4]:
            first_resp = driver_resps[0]
            text += f"👤 {first_resp.driver_name[:25]}\n"
            text += f"@{first_resp.driver_username or 'N/A'}\n"
            text += f"Ответов: {len(driver_resps)}\n\n"
            
            if len(text) > 3000:  # Проверка длины
                text += f"... и еще {len(drivers_responses) - 4} водителей"
                break
        
        if len(drivers_responses) > 4 and len(text) < 3000:
            text += f"... и еще {len(drivers_responses) - 4} водителей"
        
        buttons = []
        # Кнопки для назначения водителей
        for driver_id, driver_resps in list(drivers_responses.items())[:5]:
            first_resp = driver_resps[0]
            buttons.append([InlineKeyboardButton(
                text=f"✅ Назначить: {first_resp.driver_name}",
                callback_data=f"order:assign:{order_id}:{driver_id}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"order:view:{order_id}")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        if len(text) > 4000:
            text = text[:3900] + "\n\n... (сообщение обрезано)"
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error viewing responses: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)

