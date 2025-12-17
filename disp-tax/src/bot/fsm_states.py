"""FSM states for aiogram."""
from aiogram.fsm.state import State, StatesGroup


class OrderInput(StatesGroup):
    """Состояния для создания заказа."""
    content = State()  # Ввод текста заказа
    preview = State()  # Просмотр preview
    confirm = State()  # Подтверждение


class OrderEdit(StatesGroup):
    """Состояния для редактирования заказа."""
    content = State()  # Новый текст
    preview = State()  # Preview изменений
    confirm = State()  # Подтверждение


class OrderSend(StatesGroup):
    """Состояния для отправки заказа."""
    select_scenario = State()  # Выбор сценария
    preview = State()  # Preview отправки
    confirm = State()  # Подтверждение


class DriverAssign(StatesGroup):
    """Состояния для назначения водителя."""
    select = State()  # Выбор водителя
    confirm = State()  # Подтверждение


class ScenarioCreate(StatesGroup):
    """Состояния для создания сценария."""
    name = State()  # Название
    groups = State()  # Выбор групп
    delays = State()  # Настройка задержек
    confirm = State()  # Подтверждение


class GroupAdd(StatesGroup):
    """Состояния для добавления группы."""
    input_group = State()  # Ввод ссылки или пересылка сообщения

