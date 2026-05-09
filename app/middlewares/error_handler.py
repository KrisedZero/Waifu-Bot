from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)


class ErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception("Unhandled error while processing %s", type(event).__name__)
            await self._notify_user(event)
            return None

    async def _notify_user(self, event: Any) -> None:
        text = "⚠️ Произошла внутренняя ошибка. Попробуйте ещё раз чуть позже."

        try:
            if isinstance(event, Message):
                await event.answer(text)

            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "⚠️ Произошла ошибка. Попробуйте ещё раз позже.",
                    show_alert=True,
                )

        except Exception:
            logger.exception("Failed to notify user about an error")