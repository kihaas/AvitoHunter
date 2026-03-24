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
                title       TEXT NOT NULL,
                price       INTEGER NOT NULL,
                url         TEXT,
                brand       TEXT,
                model       TEXT,
                notified    INTEGER DEFAULT 0,
                fake_risk   INTEGER,      -- 1=true, 0=false, NULL
                damage      TEXT,
                seen_at     TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.commit()
    logger.info(f"✅ База данных инициализирована: {db_path}")


async def is_seen(db_path: str, listing_id: str) -> bool:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT 1 FROM seen_listings WHERE id = ?", (listing_id,)) as cur:
            return await cur.fetchone() is not None


async def mark_seen(db_path: str, listing: dict, ai: dict | None = None) -> None:
    brand = ai.get("brand") if ai else None
    model = ai.get("model") if ai else None
    notified = int(ai.get("notify", False)) if ai else 0
    fake_risk = int(ai.get("is_fake_risk")) if ai and ai.get("is_fake_risk") is not None else None
    damage = ai.get("damage") if ai else None

    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT OR IGNORE INTO seen_listings 
               (id, title, price, url, brand, model, notified, fake_risk, damage)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (listing["id"], listing.get("title", ""), listing.get("price", 0),
             listing.get("url", ""), brand, model, notified, fake_risk, damage)
        )
        await db.commit()