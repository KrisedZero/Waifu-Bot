from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ChatMemberStatus

router = Router()


async def is_chat_admin(bot, chat_id: int, user_id: int) -> bool:
    member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)


@router.message(Command("chatlanguage"))
async def chat_language(message: Message):
    if not message.from_user:
        return

    if not await is_chat_admin(message.bot, message.chat.id, message.from_user.id):
        await message.answer("⛔ Эту команду могут использовать только админы чата.")
        return

    await message.answer("Здесь позже будет выбор языка чата.")