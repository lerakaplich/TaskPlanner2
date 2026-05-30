from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard():
    """Главная клавиатура бота"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Мои задачи")],
            [KeyboardButton(text="⏱️ Переработки")],
            [KeyboardButton(text="➕ Создать задачу")],
            [KeyboardButton(text="🆘 Поддержка")],
            [KeyboardButton(text="🔄 Сбросить пароль")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_priority_keyboard():
    """Клавиатура выбора приоритета"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Низкий", callback_data="set_priority|low")],
        [InlineKeyboardButton(text="🟡 Средний", callback_data="set_priority|medium")],
        [InlineKeyboardButton(text="🟠 Высокий", callback_data="set_priority|high")],
        [InlineKeyboardButton(text="🔴 Критический", callback_data="set_priority|critical")]
    ])


def get_difficulty_keyboard():
    """Клавиатура выбора сложности"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Низкая (1)", callback_data="set_difficulty|1")],
        [InlineKeyboardButton(text="⭐⭐ Средняя (2)", callback_data="set_difficulty|2")],
        [InlineKeyboardButton(text="⭐⭐⭐ Высокая (3)", callback_data="set_difficulty|3")],
        [InlineKeyboardButton(text="⭐⭐⭐⭐ Очень высокая (4)", callback_data="set_difficulty|4")],
        [InlineKeyboardButton(text="⭐⭐⭐⭐⭐ Максимальная (5)", callback_data="set_difficulty|5")]
    ])