# main.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import Settings
from app.core.logger import setup_logging
from app.core.schedule import setup_scheduler
from app.database.db import init_db
from app.bot.handlers.admin import router as admin_router


async def main() -> None:
    setup_logging()
    logger = logging.getLogger("avito_hunter")

    await init_db(Settings.db_path)

    bot = Bot(token=Settings.bot_token, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем обработчики
    dp.include_router(admin_router)

    scheduler = setup_scheduler(bot)

    logger.info("🚀 AvitoHunter успешно запущен")
    scheduler.start()

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("👋 AvitoHunter остановлен")


if __name__ == "__main__":
    asyncio.run(main())