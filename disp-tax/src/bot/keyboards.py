"""Keyboard layouts for the bot."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура с кнопками справа."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📝 Создать заказ"),
                KeyboardButton(text="📋 Мои заказы")
            ],
            [
                KeyboardButton(text="⚙️ Настройки"),
                KeyboardButton(text="❓ Помощь")
            ]
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выберите действие или введите команду"
    )
    return keyboard


def remove_keyboard() -> ReplyKeyboardRemove:
    """Удаление клавиатуры."""
    return ReplyKeyboardRemove()

