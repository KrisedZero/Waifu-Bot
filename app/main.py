import asyncio
import logging

from app.bot import bot, dp
from app.database.connection import create_pool
from app.handlers.chat_categories import router as chat_categories_router
from app.handlers.chat_language import router as chat_language_router
from app.handlers.help import router as help_router
from app.handlers.language import router as language_router
from app.handlers.messages import router as messages_router
from app.handlers.mywaifus import router as mywaifus_router
from app.handlers.profile import router as profile_router
from app.handlers.search import router as search_router
from app.handlers.start import router as start_router
from app.handlers.waifu_card import router as waifu_card_router
from app.handlers.waifus import router as waifus_router
from app.middlewares.error_handler import ErrorMiddleware
from app.services.commands_service import setup_bot_commands
from app.services.runtime_lock import acquire_runtime_lock
from app.services.logging_service import setup_logging


async def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Bot is starting...")

    if not acquire_runtime_lock():
        logger.error("Startup aborted because another instance holds the runtime lock.")
        return

    # Глобальный перехват ошибок
    dp.update.middleware(ErrorMiddleware())

    try:
        await create_pool()
        await setup_bot_commands(bot)

        dp.include_router(start_router)
        dp.include_router(language_router)
        dp.include_router(help_router)
        dp.include_router(waifus_router)
        dp.include_router(search_router)
        dp.include_router(waifu_card_router)
        dp.include_router(chat_language_router)
        dp.include_router(chat_categories_router)
        dp.include_router(profile_router)
        dp.include_router(mywaifus_router)
        dp.include_router(messages_router)

        await dp.start_polling(bot)

    except Exception:
        logger.exception("Fatal error in bot main loop")
        raise


if __name__ == "__main__":
    asyncio.run(main())