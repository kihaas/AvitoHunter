"""
core/scheduler.py — планировщик и главный цикл поиска.
"""

import asyncio
import logging
import random
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from app.core.config import settings
from app.database.db import is_seen, mark_seen
from app.parser.avito import get_listings
from app.parser.ai_filter import analyze
from app.bot.handlers.notifications import send_listing

logger = logging.getLogger("avito_hunter.scheduler")


async def run_check(bot: Bot) -> None:
    #Один полный прогон по всем поисковым запросам
    now = datetime.now().strftime("%H:%M")
    logger.info(f"[{now}] Начинаю проверку Авито...")

    seen_this_run: set[str] = set()
    notified = 0

    for query in settings.search_queries:
        listings = get_listings(query, max_price=settings.max_price)

        for listing in listings:
            lid = listing["id"]

            # Дедупликация: внутри прогона + в БД
            if lid in seen_this_run:
                continue
            seen_this_run.add(lid)

            if await is_seen(settings.db_path, lid):
                continue

            # AI-анализ
            ai = analyze(
                listing,
                api_key=settings.openrouter_api_key,
                model=settings.ai_model,
            )

            # Сохраняем в БД (даже если AI не ответил)
            await mark_seen(settings.db_path, listing, ai)

            if ai is None:
                logger.warning(f"  AI не ответил: {listing['title'][:50]}")
                continue

            # Не наш бренд — тихо пропускаем
            if not ai.get("is_relevant", True):
                logger.info(f"  Не релевантно: {listing['title'][:50]}")
                continue

            # Уведомляем обо всём релевантном (notify задаётся промптом)
            if ai.get("notify", False):
                await send_listing(bot, settings.admin_id, listing, ai)
                notified += 1

            await asyncio.sleep(2)  # пауза между AI-запросами

        # Пауза между поисковыми запросами к Авито
        delay = random.uniform(settings.avito_delay_min, settings.avito_delay_max)
        logger.info(f"  Пауза {delay:.1f}с...")
        await asyncio.sleep(delay)

    logger.info(f"[{now}] Готово. Отправлено уведомлений: {notified}")


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