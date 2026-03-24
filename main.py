# main.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import settings
from app.core.logger import setup_logging
from app.core.schedule import setup_scheduler
from app.database.db import init_db
from app.bot.handlers.admin import router as admin_router


async def main() -> None:
    setup_logging()
    logger = logging.getLogger("avito_hunter")

    # Инициализация базы
    await init_db(settings.db_path)

    # Новый способ задания parse_mode в aiogram 3.7+
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем роутеры
    dp.include_router(admin_router)

    # Настраиваем планировщик
    scheduler = setup_scheduler(bot)

    logger.info("🚀 AvitoHunter успешно запущен")
    scheduler.start()

    try:
        await dp.start_polling(
            bot,
            drop_pending_updates=True,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("👋 AvitoHunter остановлен")


if __name__ == "__main__":
    asyncio.run(main())