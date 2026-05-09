from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramForbiddenError

from app.services.user_service import get_user_language

router = Router()


@router.message(Command("start"))
async def start(message: Message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    try:
        await message.answer_sticker("CAACAgIAAxkBAANTac33Nm9AEPgXaWOq7GgUfeeeX4wAAueJAALN9XFK5ubxS7vMhMg6BA")

        if lang == "en":
            text = (
                "👋 <b>Welcome!</b>\n\n"
                "✨ Glad to see you here!\n"
                "💖 Collect waifus and have fun!\n\n"
                "📦 Use /help to see how everything works\n"
            )
        else:
            text = (
                "👋 <b>Привет!</b>\n\n"
                "✨ Рад тебя видеть!\n"
                "💖 Собирай вайфу, получай удовольствие и играй!\n\n"
                "📦 Напиши /help чтобы узнать как играть\n"
            )

        await message.answer(text, parse_mode="HTML")

    except TelegramForbiddenError:
        return