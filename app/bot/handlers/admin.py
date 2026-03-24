"""
handlers/admin.py — команды и коллбэки для администратора бота.
"""

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from app.core.config import settings
from app.bot.keyboards.inline import admin_menu_keyboard

logger = logging.getLogger("avito_hunter.bot")
router = Router()

# Фильтр — только от администратора
def _is_admin(user_id: int) -> bool:
    return user_id == settings.admin_id


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return

    await message.answer(
        "🏓 <b>AvitoHunter запущен</b>\n\n"
        f"Слежу за {len(settings.search_queries)} запросами.\n"
        f"Проверка каждые {settings.check_interval_minutes} мин.\n"
        f"Макс. цена: {settings.max_price:,} ₽\n\n"
        "Буду присылать сюда всё найденное.",
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "status")
async def cb_status(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    text = (
        f"<b>Статус</b> — {now}\n\n"
        f"Модель: <code>{settings.ai_model}</code>\n"
        f"Запросов: {len(settings.search_queries)}\n"
        f"Интервал: {settings.check_interval_minutes} мин\n"
        f"Макс. цена: {settings.max_price:,} ₽"
    )
    await callback.message.edit_text(text, reply_markup=admin_menu_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery) -> None:
    text = (
        "<b>Как работает бот:</b>\n\n"
        "1. Каждые 30 мин парсит Авито по 8 запросам\n"
        "2. AI смотрит текст + фото каждого объявления\n"
        "3. Если это Nox или Adidas — присылает сюда\n"
        "4. Видел объявление раньше? Не дублирует\n\n"
        "<b>Иконки в уведомлениях:</b>\n"
        "✅ — всё хорошо\n"
        "🟡 — стоит посмотреть\n"
        "⚠️ — риск подделки или подозрительная цена\n"
        "❓ — не удалось определить по фото"
    )
    await callback.message.edit_text(text, reply_markup=admin_menu_keyboard(), parse_mode="HTML")
    await callback.answer()