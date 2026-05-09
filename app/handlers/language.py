from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.services.user_service import set_user_language

router = Router()


def language_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="English", callback_data="lang:en"),
            ]
        ]
    )


@router.message(Command("language"))
async def choose_language(message: Message):
    await message.answer(
        "Выбери язык / Choose language:",
        reply_markup=language_keyboard()
    )


@router.callback_query(F.data.startswith("lang:"))
async def set_language(call: CallbackQuery):
    lang = call.data.split(":")[1]

    await set_user_language(call.from_user.id, lang)

    if lang == "ru":
        text = "✅ Язык изменён на русский"
    else:
        text = "✅ Language changed to English"

    await call.message.edit_text(text)
    await call.answer()