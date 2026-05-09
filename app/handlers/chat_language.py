from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatMemberStatus
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.chat_settings_service import (
    ensure_chat_settings,
    get_chat_language,
    set_chat_language,
)

router = Router()


async def is_chat_admin(bot, chat_id: int, user_id: int) -> bool:
    member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    return member.status in (
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
    )


def build_language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Русский", callback_data="chatlang:ru")
    builder.button(text="English", callback_data="chatlang:en")
    builder.adjust(2)
    return builder.as_markup()


@router.message(Command("chatlanguage"))
async def chat_language(message: Message):
    if not message.from_user:
        return

    if message.chat.type == "private":
        await message.answer("Эта команда работает только в чате.")
        return

    if not await is_chat_admin(message.bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Эту команду могут использовать только админы чата.")
        return

    await ensure_chat_settings(message.chat.id)
    lang = await get_chat_language(message.chat.id)

    if lang == "ru":
        text = "🌍 Выбери язык чата:"
    else:
        text = "🌍 Choose chat language:"

    await message.answer(text, reply_markup=build_language_keyboard())


@router.callback_query(F.data.startswith("chatlang:"))
async def set_chat_lang(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    chat_id = call.message.chat.id

    if not await is_chat_admin(call.bot, chat_id, call.from_user.id):
        await call.answer("Only chat admins can change this setting.", show_alert=True)
        return

    lang = call.data.split(":", 1)[1]
    await set_chat_language(chat_id, lang)

    if lang == "ru":
        text = "✅ Язык чата изменён на русский."
    else:
        text = "✅ Chat language changed to English."

    await call.message.edit_text(text)
    await call.answer()