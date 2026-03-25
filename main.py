import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import settings
from app.core.logger import setup_logging
from app.core.schedule import setup_scheduler, run_check
from app.database.db import init_db
from app.bot.handlers.admin import router as admin_router
from app.bot.middlewares.logging import LoggingMiddleware


async def main() -> None:
    setup_logging()
    logger = logging.getLogger("avito_hunter")

    await init_db(settings.db_path)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(LoggingMiddleware())
    dp.include_router(admin_router)

    scheduler = setup_scheduler(bot)
    scheduler.start()

    logger.info("AvitoHunter запущен")

    # Первая проверка сразу при старте
    asyncio.create_task(run_check(bot))

    try:
        await dp.start_polling(
            bot,
            drop_pending_updates=True,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("AvitoHunter остановлен")


if __name__ == "__main__":
    asyncio.run(main())