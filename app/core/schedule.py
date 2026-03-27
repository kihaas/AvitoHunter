"""
app/core/scheduler.py  (был schedule.py — переименован, т.к. schedule — стандартная библиотека Python)

Порядок работы для каждого объявления:
  1. Парсинг страницы → список объявлений
  2. Дедупликация внутри прогона (seen_this_run)
  3. Проверка в БД (is_seen) — пропускаем если уже обрабатывали
  4. AI-анализ в отдельном потоке (asyncio.to_thread)
  5. mark_seen — сохраняем в БД сразу (чтобы не прогонять через AI повторно)
  6. Отправка в TG если notify=True
  7. mark_notified — только после успешной отправки
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
    start = datetime.now()
    logger.info(f"[{start:%H:%M}] Начинаю проверку Авито...")

    seen_this_run: set[str] = set()
    notified_count = 0

    for query in settings.search_queries:
        listings = await get_listings(query, max_price=settings.max_price)

        for listing in listings:
            lid = listing["id"]

            if lid in seen_this_run:
                continue
            seen_this_run.add(lid)

            if await is_seen(settings.db_path, lid):
                continue

            ai = await asyncio.to_thread(analyze, listing)
            await mark_seen(settings.db_path, listing, ai)

            if ai is None:
                logger.warning(f"  AI не ответил: {listing['title'][:50]}")
                continue

            if not ai.get("is_relevant", True):
                logger.info(f"  Не наш бренд: {listing['title'][:50]}")
                continue

            if not ai.get("notify", False):
                logger.info(f"  Пропущено AI: {listing['title'][:50]}")
                continue

            sent = await send_listing(bot, settings.admin_id, listing, ai)
            if sent:
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