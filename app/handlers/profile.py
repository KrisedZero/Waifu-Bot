from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.user_service import (
    create_user_if_not_exists,
    get_user_language,
    get_user_waifus,
    set_user_favorite_waifu,
    set_user_favorite_category,
)
from app.services.profile_ui_service import (
    get_profile_snapshot,
    build_profile_text,
    build_profile_keyboard,
    build_profile_guide_text,
    build_favorite_collection_view,
)
from app.services.waifu_media import send_waifu_media
from app.services.waifu_service import get_waifu_media

router = Router()


UI = {
    "ru": {
        "choose_favorite": "Выберите любимую вайфу:",
        "no_waifus": "У тебя пока нет вайфу.",
        "not_found": "Не удалось найти выбранную вайфу.",
        "changed": "Теперь твоя любимая вайфу:",
        "choose_collection": "Выберите любимую коллекцию:",
        "collection_changed": "Теперь твоя любимая коллекция:",
        "collection_saved": "Теперь твоя любимая коллекция:",
        "no_collection_data": "У тебя пока нет подходящих коллекций.",
    },
    "en": {
        "choose_favorite": "Choose your favorite waifu:",
        "no_waifus": "You do not have any waifus yet.",
        "not_found": "Could not find the selected waifu.",
        "changed": "Your favorite waifu is now:",
        "choose_collection": "Choose your favorite collection:",
        "collection_changed": "Your favorite collection is now:",
        "collection_saved": "Your favorite collection is now:",
        "no_collection_data": "You do not have any suitable collections yet.",
    },
}


def t(lang: str, key: str) -> str:
    return UI.get(lang, UI["ru"]).get(key, UI["ru"].get(key, key))


def get_display_name(waifu: dict, lang: str) -> str:
    if lang == "ru" and waifu.get("name_ru"):
        return waifu["name_ru"]
    return waifu.get("name_en") or waifu.get("name_ru") or "—"


async def _ensure_user(message: Message) -> str:
    user_id = message.from_user.id if message.from_user else 0
    telegram_lang = (message.from_user.language_code or "ru") if message.from_user else "ru"
    await create_user_if_not_exists(user_id, telegram_lang, message.from_user.username if message.from_user else None)
    return await get_user_language(user_id)


async def _render_profile(message: Message, view: str = "main", *, replace: bool = False, user_id: int | None = None, username: str | None = None, language_code: str | None = None):
    if not message.from_user and user_id is None:
        return

    actor_user_id = user_id or message.from_user.id
    actor_username = username if username is not None else getattr(message.from_user, "username", None)
    actor_language = language_code if language_code is not None else getattr(message.from_user, "language_code", None)

    if message.from_user and user_id is None:
        user_lang = await _ensure_user(message)
    else:
        telegram_lang = actor_language or "ru"
        await create_user_if_not_exists(actor_user_id, telegram_lang, actor_username)
        user_lang = await get_user_language(actor_user_id)

    snapshot = await get_profile_snapshot(
        user_id=actor_user_id,
        username=actor_username,
        telegram_language=actor_language or user_lang,
    )

    text = build_profile_text(snapshot, user_lang, view=view)
    markup = build_profile_keyboard(user_lang, view=view)

    if replace:
        try:
            await message.delete()
        except TelegramBadRequest:
            pass

    if view == "main":
        favorite_waifu = snapshot.get("favorite_waifu")
        if favorite_waifu:
            media = await get_waifu_media(favorite_waifu["id"])
            if media:
                sent = await send_waifu_media(message, media, text, reply_markup=markup)
                if sent:
                    return

    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@router.message(Command("profile"))
async def profile(message: Message):
    await _render_profile(message, view="main")


@router.callback_query(F.data.startswith("profile:view:"))
async def profile_view(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    view = call.data.split(":", 2)[2]
    user_id = call.from_user.id
    telegram_lang = call.from_user.language_code or "ru"
    await create_user_if_not_exists(user_id, telegram_lang, call.from_user.username)
    user_lang = await get_user_language(user_id)

    snapshot = await get_profile_snapshot(
        user_id=user_id,
        username=call.from_user.username,
        telegram_language=telegram_lang,
    )

    if view == "guide":
        try:
            await call.message.delete()
        except TelegramBadRequest:
            pass
        await call.message.answer(
            build_profile_guide_text(user_lang, int(snapshot.get("level", 1))),
            parse_mode="HTML",
            reply_markup=build_profile_keyboard(user_lang, view="guide"),
        )
        await call.answer()
        return

    text = build_profile_text(snapshot, user_lang, view=view)
    markup = build_profile_keyboard(user_lang, view=view)

    try:
        await call.message.delete()
    except TelegramBadRequest:
        pass

    if view == "main":
        favorite_waifu = snapshot.get("favorite_waifu")
        if favorite_waifu:
            media = await get_waifu_media(favorite_waifu["id"])
            if media:
                sent = await send_waifu_media(call.message, media, text, reply_markup=markup)
                if sent:
                    await call.answer()
                    return

    await call.message.answer(text, parse_mode="HTML", reply_markup=markup)
    await call.answer()


@router.callback_query(F.data == "change_favorite")
async def change_favorite(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    user_id = call.from_user.id
    user_lang = await get_user_language(user_id)
    waifus = await get_user_waifus(user_id)

    if not waifus:
        await call.message.answer(t(user_lang, "no_waifus"))
        await call.answer()
        return

    builder = InlineKeyboardBuilder()
    for w in waifus:
        builder.button(
            text=f"{get_display_name(w, user_lang)} x{w['amount']}",
            callback_data=f"set_favorite:{w['id']}"
        )
    builder.adjust(2)

    try:
        await call.message.delete()
    except TelegramBadRequest:
        pass
    try:
        await call.message.delete()
    except TelegramBadRequest:
        pass
    await call.message.answer(
        t(user_lang, "choose_favorite"),
        reply_markup=builder.as_markup()
    )
    await call.answer()


@router.callback_query(F.data == "change_favorite_category")
async def change_favorite_category(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    user_id = call.from_user.id
    user_lang = await get_user_language(user_id)
    text, markup = await build_favorite_collection_view(user_lang, None)
    try:
        await call.message.delete()
    except TelegramBadRequest:
        pass
    await call.message.answer(text, parse_mode="HTML", reply_markup=markup)
    await call.answer()


@router.callback_query(F.data.startswith("set_favorite:"))
async def set_favorite(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    user_id = call.from_user.id
    user_lang = await get_user_language(user_id)
    waifu_id = int(call.data.split(":")[1])

    waifus = await get_user_waifus(user_id)
    selected_waifu = next((w for w in waifus if w["id"] == waifu_id), None)

    if not selected_waifu:
        await call.message.answer(t(user_lang, "not_found"))
        await call.answer()
        return

    await set_user_favorite_waifu(user_id, waifu_id)
    await _render_profile(call.message, view="main", replace=True, user_id=call.from_user.id, username=call.from_user.username, language_code=call.from_user.language_code)
    await call.answer()


@router.callback_query(F.data.startswith("favcat:open:"))
async def open_favorite_category(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    user_id = call.from_user.id
    user_lang = await get_user_language(user_id)
    current = call.data.split(":", 2)[2]
    category_id = None if current in {"root", "0", "none"} else int(current)

    text, markup = await build_favorite_collection_view(user_lang, category_id)
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer(text, parse_mode="HTML", reply_markup=markup)
    await call.answer()


@router.callback_query(F.data.startswith("set_favorite_category:"))
async def set_favorite_category(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    user_id = call.from_user.id
    user_lang = await get_user_language(user_id)
    category_id = int(call.data.split(":")[1])

    snapshot = await get_profile_snapshot(
        user_id=user_id,
        username=call.from_user.username,
        telegram_language=call.from_user.language_code or user_lang,
    )
    stats = snapshot.get("favorite_collection_stats") or []
    selected = next((item for item in stats if int(item["id"]) == category_id), None)

    if not selected:
        await call.message.answer(t(user_lang, "not_found"))
        await call.answer()
        return

    await set_user_favorite_category(user_id, category_id)
    await _render_profile(call.message, view="main", replace=True, user_id=call.from_user.id, username=call.from_user.username, language_code=call.from_user.language_code)
    await call.answer()
