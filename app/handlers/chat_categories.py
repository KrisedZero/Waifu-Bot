import html

from aiogram import Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.category_service import get_root_categories
from app.services.chat_category_service import (
    get_blocked_root_category_ids,
    toggle_chat_root_category,
)
from app.services.chat_settings_service import get_chat_language
from app.services.user_service import get_user_language

router = Router()


async def is_chat_admin(bot, chat_id: int, user_id: int) -> bool:
    member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    return member.status in (
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
    )


def get_cat_name(cat: dict, lang: str) -> str:
    if lang == "ru" and cat.get("name_ru"):
        return cat["name_ru"]
    return cat["name_en"]


def build_chat_categories_text(
    root_categories: list[dict],
    blocked_ids: set[int],
    lang: str,
    is_admin: bool,
) -> str:
    title = "🌍 <b>Категории чата</b>" if lang == "ru" else "🌍 <b>Chat categories</b>"
    lines = [title, ""]

    if not root_categories:
        return "⚠️ Категории ещё не добавлены." if lang == "ru" else "⚠️ No categories have been added yet."

    for cat in root_categories:
        name = html.escape(get_cat_name(cat, lang))
        blocked = cat["id"] in blocked_ids
        marker = "🚫" if blocked else "✅"

        if lang == "ru":
            status = "заблокирована" if blocked else "доступна"
        else:
            status = "blocked" if blocked else "available"

        lines.append(f"{marker} <b>{name}</b> — {status}")

    allowed_count = len(root_categories) - len(blocked_ids)
    lines.append("")

    if lang == "ru":
        lines.append(f"Доступно root-категорий: <b>{allowed_count}/{len(root_categories)}</b>")
        if is_admin:
            lines.append("Нажми на кнопку, чтобы заблокировать или разблокировать категорию.")
    else:
        lines.append(f"Available root categories: <b>{allowed_count}/{len(root_categories)}</b>")
        if is_admin:
            lines.append("Tap a button to block or unblock a category.")

    return "\n".join(lines)


def build_chat_categories_keyboard(root_categories: list[dict], blocked_ids: set[int]):
    builder = InlineKeyboardBuilder()

    for cat in root_categories:
        blocked = cat["id"] in blocked_ids
        name = cat["name_en"] if cat.get("name_en") else cat["name_ru"]
        prefix = "🚫" if blocked else "✅"

        builder.button(
            text=f"{prefix} {name}",
            callback_data=f"chatcat:toggle:{cat['id']}",
        )

    if root_categories:
        builder.adjust(1)

    return builder.as_markup()


@router.message(Command("chatcategories"))
async def chat_categories(message: Message):
    if not message.from_user:
        return

    if message.chat.type == "private":
        lang = await get_user_language(message.from_user.id)
        if lang == "ru":
            await message.answer("Эта команда работает только в чате.")
        else:
            await message.answer("This command works only in a chat.")
        return

    lang = await get_chat_language(message.chat.id)
    root_categories = await get_root_categories()
    blocked_ids = set(await get_blocked_root_category_ids(message.chat.id))
    admin = await is_chat_admin(message.bot, message.chat.id, message.from_user.id)

    text = build_chat_categories_text(root_categories, blocked_ids, lang, admin)
    markup = build_chat_categories_keyboard(root_categories, blocked_ids) if admin else None

    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(lambda c: c.data and c.data.startswith("chatcat:toggle:"))
async def toggle_category(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    chat_id = call.message.chat.id
    lang = await get_chat_language(chat_id)

    if not await is_chat_admin(call.bot, chat_id, call.from_user.id):
        if lang == "ru":
            await call.answer("Только админы чата могут менять категории.", show_alert=True)
        else:
            await call.answer("Only chat admins can change categories.", show_alert=True)
        return

    root_id = int(call.data.split(":")[2])

    result = await toggle_chat_root_category(chat_id, root_id)

    if result == "last_root_locked":
        if lang == "ru":
            await call.answer("Нельзя заблокировать последнюю доступную root-категорию.", show_alert=True)
        else:
            await call.answer("You cannot block the last available root category.", show_alert=True)
        return

    root_categories = await get_root_categories()
    blocked_ids = set(await get_blocked_root_category_ids(chat_id))

    text = build_chat_categories_text(root_categories, blocked_ids, lang, True)
    markup = build_chat_categories_keyboard(root_categories, blocked_ids)

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    await call.answer()