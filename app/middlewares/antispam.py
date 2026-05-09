import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message


class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self, cooldown: float = 1.0) -> None:
        self.cooldown = cooldown
        self.last_seen: dict[tuple[int, int], float] = {}

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not event.from_user:
            return await handler(event, data)

        chat_id = event.chat.id
        user_id = event.from_user.id
        now = time.monotonic()

        key = (chat_id, user_id)
        last = self.last_seen.get(key)

        if last is not None and now - last < self.cooldown:
            return

        self.last_seen[key] = now
        return await handler(event, data)