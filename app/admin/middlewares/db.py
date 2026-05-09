from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

import asyncpg
from aiogram import BaseMiddleware

from app.database.connection import get_pool as get_global_pool


class DbMiddleware(BaseMiddleware):
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        pool = self.pool or get_global_pool()
        if pool is None:
            raise RuntimeError("Database pool is not initialized for admin middleware")
        data["pool"] = pool
        return await handler(event, data)
