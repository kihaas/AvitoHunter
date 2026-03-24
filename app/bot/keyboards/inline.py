from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def listing_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Открыть на Авито", url=url)
    ]])


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Статус бота", callback_data="status")],
        [InlineKeyboardButton(text="Запустить проверку", callback_data="run_now")],
        [InlineKeyboardButton(text="Помощь", callback_data="help")],
    ])