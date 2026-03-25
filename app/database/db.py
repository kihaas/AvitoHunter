# app/database/db.py
import aiosqlite
from datetime import datetime
from typing import Any

from app.core.logger import logger
from app.core.config import settings


async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS seen_listings (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL DEFAULT '',
                price       INTEGER NOT NULL DEFAULT 0,
                url         TEXT DEFAULT '',
                brand       TEXT,
                model       TEXT,
                notified    INTEGER NOT NULL DEFAULT 0,
                fake_risk   INTEGER,
                damage      TEXT,
                seen_at     TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        await db.commit()
    logger.info(f"✅ База данных инициализирована: {db_path}")


async def is_seen(db_path: str, listing_id: str) -> bool:
    """Встречали ли это объявление раньше (по любому результату AI)."""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT 1 FROM seen_listings WHERE id = ?", (listing_id,)
        ) as cur:
            return await cur.fetchone() is not None


async def is_notified(db_path: str, listing_id: str) -> bool:
    """Отправляли ли уже это объявление в Telegram."""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
                "SELECT 1 FROM seen_listings WHERE id = ? AND notified = 1", (listing_id,)
        ) as cur:
            return await cur.fetchone() is not None


async def mark_seen(db_path: str, listing: dict, ai: dict | None) -> None:
    """Сохраняем объявление сразу при встрече (до отправки в Telegram)."""
    brand = ai.get("brand") if ai else None
    model = ai.get("model") if ai else None
    fake_risk = ai.get("is_fake_risk") if ai else None
    damage = ai.get("damage") if ai else None

    fake_risk_int = None if fake_risk is None else int(fake_risk)

    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT OR IGNORE INTO seen_listings
               (id, title, price, url, brand, model, notified, fake_risk, damage)
               VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)""",
            (
                listing["id"],
                listing.get("title", ""),
                listing.get("price", 0),
                listing.get("url", ""),
                brand,
                model,
                fake_risk_int,
                damage,
            ),
        )
        await db.commit()


async def mark_notified(db_path: str, listing_id: str) -> None:
    """Помечаем объявление как отправленное — вызывать ПОСЛЕ успешной отправки в TG."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE seen_listings SET notified = 1 WHERE id = ?", (listing_id,)
        )
        await db.commit()