"""
app/core/schedule.py

Ключевые изменения:
  1. AI-вызов через asyncio.to_thread() — Gemini SDK синхронный, не блокируем event loop
  2. mark_notified() вызывается ПОСЛЕ успешной отправки в TG, а не до
  3. is_seen() проверяет до AI-анализа — экономим API-запросы
"""

import asyncio
import logging
import random
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from app.core.config import settings
from app.database.db import is_seen, mark_seen, mark_notified
from app.parser.avito import get_listings
from app.ai.analyzer import analyze
from app.bot.handlers.notifications import send_listing

logger = logging.getLogger("avito_hunter.scheduler")


async def run_check(bot: Bot) -> None:
    """Один полный прогон по всем поисковым запросам."""
    start = datetime.now()
    logger.info(f"[{start:%H:%M}] Начинаю проверку Авито...")

    seen_this_run: set[str] = set()
    notified_count = 0

    for query in settings.search_queries:
        listings = await get_listings(query, max_price=settings.max_price)

        for listing in listings:
            lid = listing["id"]

            # Пропускаем дубли внутри одного прогона
            if lid in seen_this_run:
                continue
            seen_this_run.add(lid)

            # Пропускаем то, что уже видели раньше (есть в БД)
            if await is_seen(settings.db_path, lid):
                continue

            # AI-анализ — синхронный вызов в отдельном потоке
            ai = await asyncio.to_thread(analyze, listing)

            # Сохраняем в БД сразу — даже если AI не ответил, чтобы не обрабатывать снова
            await mark_seen(settings.db_path, listing, ai)

            if ai is None:
                logger.warning(f"  AI не ответил: {listing['title'][:50]}")
                continue

            if not ai.get("is_relevant", True):
                logger.info(f"  Не наш бренд: {listing['title'][:50]}")
                continue

            if not ai.get("notify", False):
                logger.info(f"  AI решил не уведомлять: {listing['title'][:50]}")
                continue

            # Отправляем в Telegram
            sent = await send_listing(bot, settings.admin_id, listing, ai)

            if sent:
                # Помечаем как отправленное ТОЛЬКО после успешной отправки
                await mark_notified(settings.db_path, lid)
                notified_count += 1

            await asyncio.sleep(2)

        delay = random.uniform(settings.avito_delay_min, settings.avito_delay_max)
        logger.info(f"  Пауза {delay:.1f}с...")
        await asyncio.sleep(delay)

    elapsed = (datetime.now() - start).seconds
    logger.info(f"Проверка завершена за {elapsed}с. Отправлено: {notified_count}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        run_check,
        trigger="interval",
        minutes=settings.check_interval_minutes,
        args=[bot],
        id="avito_check",
        replace_existing=True,
    )
    return scheduler