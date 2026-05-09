from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.admin.config import admin_config
from app.admin.middlewares.admin_guard import AdminGuardMiddleware
from app.admin.middlewares.db import DbMiddleware
from app.admin.routers.auth import router as auth_router
from app.admin.routers.categories import router as categories_router
from app.admin.routers.menu import router as menu_router
from app.admin.routers.waifus import router as waifus_router
from app.admin.services.admin_auth_service import ensure_admin_bootstrap
from app.admin.services.admin_media_service import migrate_existing_waifu_media
from app.database.connection import create_pool, get_pool


async def main():
    await create_pool()
    await ensure_admin_bootstrap()

    pool = get_pool()
    if pool is None:
        raise RuntimeError("Database pool is not initialized")

    bot = Bot(token=admin_config.ADMIN_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    for router in (auth_router, menu_router, categories_router, waifus_router):
        router.message.outer_middleware(DbMiddleware(pool))
        router.callback_query.outer_middleware(DbMiddleware(pool))

    menu_router.callback_query.outer_middleware(AdminGuardMiddleware())
    categories_router.message.outer_middleware(AdminGuardMiddleware())
    categories_router.callback_query.outer_middleware(AdminGuardMiddleware())
    waifus_router.message.outer_middleware(AdminGuardMiddleware())
    waifus_router.callback_query.outer_middleware(AdminGuardMiddleware())

    # Migrate legacy Telegram file_id-based media to local storage so the public bot
    # can display the same content even though it is a separate bot.
    try:
        migrated = await migrate_existing_waifu_media(bot, pool)
        if migrated:
            print(f"Migrated {migrated} legacy waifu media file(s) to local storage.")
    except Exception:
        # Migration must not block the admin bot from starting.
        import logging
        logging.getLogger(__name__).exception("Failed to migrate legacy waifu media")

    dp.include_router(auth_router)
    dp.include_router(menu_router)
    dp.include_router(categories_router)
    dp.include_router(waifus_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
