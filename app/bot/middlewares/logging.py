import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

logger = logging.getLogger("avito_hunter.bot")


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            user = event.from_user
            logger.info(
                f"Message from {user.id} (@{user.username}): {event.text!r}"
            )
        return await handler(event, data)