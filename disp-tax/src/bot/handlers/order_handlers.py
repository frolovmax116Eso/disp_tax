"""Handlers for order management."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from src.bot.fsm_states import OrderInput, OrderEdit
from src.bot.keyboards import get_main_keyboard
from src.services.order_service import OrderService
from src.fsm.order_fsm import OrderFSM, OrderFSMError
from src.utils.error_format import format_error_for_user
import logging
import io

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    """Обработчик команды /start."""
    await message.answer(
        "👋 Добро пожаловать в Telegram Dispatcher Platform!\n\n"
        "Используйте кнопки справа для быстрого доступа к функциям.",
        reply_markup=get_main_keyboard()
    )


@router.message(F.text.in_(["/new_order", "📝 Создать заказ"]))
async def cmd_new_order(message: Message, state: FSMContext):
    """Обработчик команды /new_order."""
    try:
        await state.set_state(OrderInput.content)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎤 Голосовое сообщение", callback_data="order:input:voice")],
            [InlineKeyboardButton(text="📝 Ввести текст", callback_data="order:input:text")],
            [InlineKeyboardButton(text="📋 Из шаблона", callback_data="order:input:template")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
        
        await message.answer(
            "📝 Создание нового заказа\n\n"
            "Выберите способ создания заказа:",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in cmd_new_order: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await message.answer(f"Ошибка: {error_msg}")


@router.message(F.text.in_(["/my_orders", "📋 Мои заказы"]))
async def cmd_my_orders(message: Message, session: AsyncSession):
    """Обработчик команды /my_orders."""
    # Создаем фиктивный callback для использования существующего handler
    from aiogram.types import CallbackQuery
    from unittest.mock import MagicMock
    
    # Используем существующий handler через прямой вызов
    orders = await OrderService.get_dispatcher_orders(
        session=session,
        dispatcher_id=message.from_user.id
    )
    
    if not orders:
        await message.answer("📋 У вас пока нет заказов")
        return
    
    text = f"📋 Ваши заказы (всего: {len(orders)})\n\n"
    buttons = []
    
    for i, order in enumerate(orders[:5], 1):
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
        text += f"{emoji} Заказ #{order.id} - {order.state.value}\n"
        text += f"   {order.content[:40]}...\n\n"
        buttons.append([InlineKeyboardButton(
            text=f"Заказ #{order.id}",
            callback_data=f"order:view:{order.id}"
        )])
    
    if len(orders) > 5:
        text += f"... и еще {len(orders) - 5} заказов"
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if len(text) > 4000:
        text = text[:3900] + "\n\n... (сообщение обрезано)"
    
    await message.answer(text, reply_markup=keyboard)


@router.message(F.text.in_(["/help", "❓ Помощь"]))
async def cmd_help(message: Message):
    """Обработчик команды /help."""
    help_text = (
        "❓ Помощь по использованию бота\n\n"
        "📝 <b>Создание заказа:</b>\n"
        "• Нажмите кнопку '📝 Создать заказ'\n"
        "• Выберите способ: голосовое, текст или шаблон\n"
        "• Подтвердите заказ перед отправкой\n\n"
        "📋 <b>Мои заказы:</b>\n"
        "• Нажмите кнопку '📋 Мои заказы'\n"
        "• Просмотр всех ваших заказов\n"
        "• Управление заказами (редактирование, отмена, закрытие)\n\n"
        "⚙️ <b>Настройки:</b>\n"
        "• Нажмите кнопку '⚙️ Настройки'\n"
        "• Авторизация через QR-код\n"
        "• Управление группами\n"
        "• Настройка регионов и сценариев\n\n"
        "🔐 <b>Авторизация:</b>\n"
        "• Перейдите в Настройки → Авторизация\n"
        "• Отсканируйте QR-код в приложении Telegram\n\n"
        "💡 <b>Совет:</b> Используйте кнопки справа для быстрого доступа к функциям."
    )
    await message.answer(help_text, parse_mode="HTML", reply_markup=get_main_keyboard())


@router.callback_query(F.data == "order:new")
async def start_new_order(callback: CallbackQuery, state: FSMContext):
    """Начало создания нового заказа - выбор способа ввода."""
    try:
        await state.set_state(OrderInput.content)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎤 Голосовое сообщение", callback_data="order:input:voice")],
            [InlineKeyboardButton(text="📝 Ввести текст", callback_data="order:input:text")],
            [InlineKeyboardButton(text="📋 Из шаблона", callback_data="order:input:template")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
        
        await callback.message.edit_text(
            "📝 Создание нового заказа\n\n"
            "Выберите способ создания заказа:",
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in start_new_order: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data == "order:input:text")
async def order_input_text(callback: CallbackQuery, state: FSMContext):
    """Выбор текстового ввода."""
    try:
        await state.set_state(OrderInput.content)
        await state.update_data(input_type="text")
        await callback.message.edit_text(
            "📝 Ввод текста заказа\n\n"
            "Введите текст заказа:"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in order_input_text: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data == "order:input:voice")
async def order_input_voice(callback: CallbackQuery, state: FSMContext):
    """Выбор голосового ввода."""
    try:
        await state.set_state(OrderInput.content)
        await state.update_data(input_type="voice")
        await callback.message.edit_text(
            "🎤 Голосовое сообщение\n\n"
            "Отправьте голосовое сообщение с текстом заказа.\n\n"
            "Или отправьте текст, если хотите ввести вручную:"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in order_input_voice: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data == "order:input:template")
async def order_input_template(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Выбор шаблона."""
    try:
        # Пока просто переключаем на текстовый ввод
        # В будущем здесь можно добавить список шаблонов
        await state.set_state(OrderInput.content)
        await state.update_data(input_type="template")
        await callback.message.edit_text(
            "📋 Шаблоны\n\n"
            "Шаблоны будут доступны в следующей версии.\n\n"
            "Пока введите текст заказа:"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in order_input_template: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.message(OrderInput.content)
async def process_order_content(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка текста или голосового сообщения заказа."""
    state_data = await state.get_data()
    input_type = state_data.get("input_type", "text")
    
    content = None
    
    # Обработка голосового сообщения
    if input_type == "voice" and message.voice:
        # Сначала проверяем транскрипцию от Telegram (если доступна)
        if hasattr(message, 'voice') and hasattr(message.voice, 'transcription') and message.voice.transcription:
            content = message.voice.transcription.text
            await message.answer(
                f"🎤 Голосовое сообщение распознано (Telegram):\n\n{content}\n\n"
                "Продолжаем создание заказа..."
            )
        else:
            # Если транскрипции нет, используем внешний API
            await message.answer("🎤 Обрабатываю голосовое сообщение...")
            
            try:
                from src.services.speech_recognition import SpeechRecognitionService
                
                # Получаем Bot из сообщения
                bot = message.bot
                
                # Скачиваем файл голосового сообщения
                file = await bot.get_file(message.voice.file_id)
                
                # Скачиваем файл в память
                # download_file может вернуть BytesIO или bytes
                voice_stream = await bot.download_file(file.file_path)
                
                # Преобразуем в bytes
                if isinstance(voice_stream, io.BytesIO):
                    voice_data = voice_stream.getvalue()
                elif hasattr(voice_stream, 'read'):
                    # Если это файловый объект, читаем его
                    voice_data = voice_stream.read()
                    if hasattr(voice_stream, 'seek'):
                        voice_stream.seek(0)
                else:
                    voice_data = voice_stream
                
                # Убеждаемся, что это bytes
                if not isinstance(voice_data, bytes):
                    voice_data = bytes(voice_data)
                
                logger.info(f"Downloaded voice file, size: {len(voice_data)} bytes")
                
                # Распознаем речь
                content = await SpeechRecognitionService.recognize_voice(voice_data, language="ru")
                
                if content:
                    await message.answer(
                        f"🎤 Голосовое сообщение распознано:\n\n{content}\n\n"
                        "Продолжаем создание заказа..."
                    )
                else:
                    await message.answer(
                        "❌ Не удалось распознать голосовое сообщение.\n\n"
                        "Возможные причины:\n"
                        "• API ключ не настроен (добавьте OPENAI_API_KEY или YANDEX_API_KEY в .env)\n"
                        "• Проблема с подключением к API\n"
                        "• Неподдерживаемый формат аудио\n\n"
                        "Пожалуйста, введите текст заказа вручную:"
                    )
                    return
                    
            except Exception as e:
                logger.error(f"Error recognizing voice: {e}", exc_info=True)
                await message.answer(
                    f"❌ Ошибка при распознавании речи: {str(e)[:100]}\n\n"
                    "Пожалуйста, введите текст заказа вручную:"
                )
                return
    
    # Обработка текста
    if message.text:
        content = message.text
    else:
        await message.answer(
            "❌ Пожалуйста, отправьте текст заказа."
        )
        return
    
    if not content or len(content.strip()) < 10:
        await message.answer(
            "❌ Текст заказа слишком короткий. Минимум 10 символов.\n"
            "Попробуйте еще раз:"
        )
        return
    
    try:
        # Сохранение контента в state
        await state.update_data(content=content)
        
        # Создание заказа в DRAFT
        order = await OrderService.create_order(
            session=session,
            dispatcher_id=message.from_user.id,
            content=content
        )
        
        await state.update_data(order_id=order.id)
        await state.set_state(OrderInput.preview)
        
        # Получение preview
        preview = await OrderService.preview_order(session=session, order_id=order.id)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"order:confirm:{order.id}")],
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"order:edit:{order.id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="order:cancel")]
        ])
        
        await message.answer(
            f"📋 Preview заказа\n\n"
            f"Текст:\n{preview['normalized_content']}\n\n"
            f"Состояние: {preview['state']}\n"
            f"Риск: {preview['risk_level']}",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error creating order: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await message.answer(f"Ошибка создания заказа: {error_msg}")


@router.callback_query(F.data.startswith("order:confirm:"))
async def confirm_order_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтверждение заказа."""
    try:
        order_id = int(callback.data.split(":")[-1])
        
        order = await OrderService.confirm_order(
            session=session,
            order_id=order_id,
            dispatcher_id=callback.from_user.id
        )
        
        await state.clear()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Отправить заказ", callback_data=f"order:send:{order.id}")],
            [InlineKeyboardButton(text="📋 Мои заказы", callback_data="order:list")]
        ])
        
        await callback.message.edit_text(
            f"✅ Заказ #{order.id} подтвержден!\n\n"
            f"Теперь вы можете отправить его в группы.",
            reply_markup=keyboard
        )
        await callback.answer("Заказ подтвержден")
        
    except OrderFSMError as e:
        logger.error(f"FSM error: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)
    except Exception as e:
        logger.error(f"Error confirming order: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data.startswith("order:edit:"))
async def edit_order_callback(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования заказа."""
    try:
        order_id = int(callback.data.split(":")[-1])
        
        await state.update_data(order_id=order_id)
        await state.set_state(OrderEdit.content)
        
        await callback.message.edit_text(
            "✏️ Редактирование заказа\n\n"
            "Введите новый текст заказа:"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in edit_order_callback: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.message(OrderEdit.content)
async def process_edit_content(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка нового текста при редактировании."""
    data = await state.get_data()
    order_id = data.get("order_id")
    new_content = message.text
    
    if not new_content or len(new_content.strip()) < 10:
        await message.answer(
            "❌ Текст заказа слишком короткий. Минимум 10 символов.\n"
            "Попробуйте еще раз:"
        )
        return
    
    try:
        # Получение текущего заказа
        order = await OrderService.get_order(session=session, order_id=order_id)
        if not order:
            await message.answer("❌ Заказ не найден")
            return
        
        # Preview изменений
        await state.update_data(new_content=new_content)
        await state.set_state(OrderEdit.preview)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить изменения", callback_data=f"order:edit_confirm:{order_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"order:view:{order_id}")]
        ])
        
        await message.answer(
            f"📋 Preview изменений\n\n"
            f"Старый текст:\n{order.content[:200]}...\n\n"
            f"Новый текст:\n{new_content[:200]}...\n\n"
            f"Подтвердите изменения:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error processing edit: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await message.answer(f"Ошибка: {error_msg}")


@router.callback_query(F.data.startswith("order:edit_confirm:"))
async def confirm_edit_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтверждение редактирования заказа."""
    try:
        order_id = int(callback.data.split(":")[-1])
        data = await state.get_data()
        new_content = data.get("new_content")
        
        if not new_content:
            await callback.answer("❌ Текст не найден", show_alert=True)
            return
        
        order = await OrderService.edit_order(
            session=session,
            order_id=order_id,
            new_content=new_content,
            dispatcher_id=callback.from_user.id
        )
        
        await state.clear()
        
        # Обновление всех сообщений в группах
        from src.services.send_service import SendService
        await SendService.update_all_messages(
            session=session,
            order_id=order_id,
            dispatcher_id=callback.from_user.id,
            new_text=order.normalized_content
        )
        
        await callback.message.edit_text(
            f"✅ Заказ #{order.id} отредактирован!\n\n"
            f"Новый текст:\n{order.normalized_content[:300]}..."
        )
        await callback.answer("Заказ отредактирован")
        
    except OrderFSMError as e:
        logger.error(f"FSM error: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)
    except Exception as e:
        logger.error(f"Error editing order: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data == "order:cancel")
async def cancel_order_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания заказа."""
    try:
        await state.clear()
        await callback.message.edit_text("❌ Создание заказа отменено")
        await callback.answer()
    except Exception as e:
        logger.error(f"Error cancelling order: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data == "order:list")
async def list_orders(callback: CallbackQuery, session: AsyncSession):
    """Список заказов диспетчера."""
    try:
        orders = await OrderService.get_dispatcher_orders(
            session=session,
            dispatcher_id=callback.from_user.id
        )
        
        if not orders:
            await callback.message.edit_text("📋 У вас пока нет заказов")
            await callback.answer()
            return
        
        # Разбиваем на части, если слишком длинно (Telegram лимит 4096 символов)
        text = f"📋 Ваши заказы (всего: {len(orders)})\n\n"
        buttons = []
        
        # Показываем только последние 5 заказов для краткости
        for i, order in enumerate(orders[:5], 1):
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
            text += f"{emoji} Заказ #{order.id} - {order.state.value}\n"
            text += f"   {order.content[:40]}...\n\n"
            buttons.append([InlineKeyboardButton(
                text=f"Заказ #{order.id}",
                callback_data=f"order:view:{order.id}"
            )])
        
        if len(orders) > 5:
            text += f"... и еще {len(orders) - 5} заказов"
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Проверка длины сообщения
        if len(text) > 4000:
            text = text[:3900] + "\n\n... (сообщение обрезано)"
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error listing orders: {e}", exc_info=True)
        error_msg = str(e)[:100] if len(str(e)) > 100 else str(e)
        # Убираем технические детали для пользователя
        if "no such table" in error_msg.lower():
            error_msg = "База данных не инициализирована. Обратитесь к администратору."
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать заказ", callback_data="order:new")],
        [InlineKeyboardButton(text="📋 Мои заказы", callback_data="order:list")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
    ])
    
    await callback.message.edit_text(
        "👋 Добро пожаловать в Telegram Dispatcher Platform!\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order:send:"))
async def send_order_callback(callback: CallbackQuery, session: AsyncSession):
    """Отправка заказа."""
    try:
        order_id = int(callback.data.split(":")[-1])
        order = await OrderService.get_order(session=session, order_id=order_id)
        
        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        
        if order.state.value != "confirmed":
            await callback.answer("❌ Заказ должен быть подтвержден", show_alert=True)
            return
        
        # Получаем группы диспетчера
        from sqlalchemy import select
        from src.database.models import Group
        
        result = await session.execute(
            select(Group).where(
                Group.dispatcher_id == order.dispatcher_id,
                Group.is_active == True
            )
        )
        groups = list(result.scalars().all())
        
        if not groups:
            await callback.answer("❌ Нет активных групп. Добавьте группы в настройках.", show_alert=True)
            return
        
        # Показываем выбор групп
        buttons = []
        for group in groups[:10]:
            buttons.append([InlineKeyboardButton(
                text=f"📤 {group.title}",
                callback_data=f"order:send_to_group:{order_id}:{group.id}"
            )])
        
        buttons.append([InlineKeyboardButton(
            text="📤 Отправить во все группы",
            callback_data=f"order:send_all:{order_id}"
        )])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"order:view:{order_id}")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            f"📤 Отправка заказа #{order_id}\n\n"
            f"Выберите группы для отправки:",
            reply_markup=keyboard
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in send_order: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data.startswith("order:send_all:"))
async def send_order_all_groups(callback: CallbackQuery, session: AsyncSession):
    """Отправка заказа во все группы."""
    try:
        order_id = int(callback.data.split(":")[-1])
        order = await OrderService.get_order(session=session, order_id=order_id)
        
        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        
        # Получаем все активные группы
        from sqlalchemy import select
        from src.database.models import Group
        from src.services.send_service import SendService
        
        result = await session.execute(
            select(Group).where(
                Group.dispatcher_id == order.dispatcher_id,
                Group.is_active == True
            )
        )
        groups = list(result.scalars().all())
        
        if not groups:
            await callback.answer("❌ Нет активных групп", show_alert=True)
            return
        
        group_ids = [g.id for g in groups]
        
        # Отправка с прогрессом
        await callback.message.edit_text(f"📤 Отправка заказа #{order_id} в {len(groups)} групп...\n\nПожалуйста, подождите...")
        
        async def progress_callback(msg):
            await callback.message.edit_text(f"📤 Отправка заказа #{order_id}\n\n{msg}")
        
        success = await SendService.send_order_to_groups(
            session=session,
            order_id=order_id,
            group_ids=group_ids,
            dispatcher_id=callback.from_user.id,
            delay_min=5,
            delay_max=10,
            progress_callback=progress_callback
        )
        
        if success:
            await callback.message.edit_text(
                f"✅ Заказ #{order_id} отправлен в {len(groups)} групп!"
            )
            await callback.answer("Заказ отправлен")
        else:
            await callback.message.edit_text(
                f"❌ Ошибка при отправке заказа #{order_id}"
            )
            await callback.answer("Ошибка отправки", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error sending order: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)


@router.callback_query(F.data.startswith("order:assign:"))
async def assign_driver_callback(callback: CallbackQuery, session: AsyncSession):
    """Назначение водителя на заказ."""
    try:
        from src.services.assignment_service import AssignmentService
        from src.services.response_service import ResponseService
        
        parts = callback.data.split(":")
        order_id = int(parts[2])
        driver_id = int(parts[3])
        
        # Получаем информацию о водителе из ответов
        responses = await ResponseService.get_responses_by_driver(
            session=session,
            order_id=order_id,
            driver_telegram_id=driver_id
        )
        
        if not responses:
            await callback.answer("❌ Водитель не найден", show_alert=True)
            return
        
        first_response = responses[0]
        
        # Назначаем водителя
        assignment = await AssignmentService.assign_driver(
            session=session,
            order_id=order_id,
            driver_telegram_id=driver_id,
            driver_username=first_response.driver_username,
            driver_name=first_response.driver_name,
            assigned_by=callback.from_user.id
        )
        
        await callback.message.edit_text(
            f"✅ Водитель назначен на заказ #{order_id}!\n\n"
            f"Водитель: {first_response.driver_name}\n"
            f"@{first_response.driver_username or 'N/A'}"
        )
        await callback.answer("Водитель назначен")
        
    except Exception as e:
        logger.error(f"Error assigning driver: {e}", exc_info=True)
        error_msg = format_error_for_user(e)
        await callback.answer(f"Ошибка: {error_msg}", show_alert=True)



