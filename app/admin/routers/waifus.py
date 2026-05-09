from __future__ import annotations

import asyncio

from collections import defaultdict
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.admin.keyboards.common import kb_confirm_cancel
from app.admin.keyboards.waifus import (
    waifus_menu_kb,
    waifus_list_kb,
    waifu_card_kb,
    waifu_edit_fields_kb,
    waifu_bool_kb,
    waifu_media_type_kb,
    waifu_rarity_kb,
    waifu_gender_kb,
    waifu_search_results_kb,
    waifu_category_picker_kb,
)
from app.admin.services.admin_audit_service import write_audit_log
from app.admin.utils.telegram import safe_replace_text
from app.admin.services.admin_cache_service import invalidate_waifu_catalog
from app.admin.services.admin_category_service import get_category, get_root_categories, get_child_categories, search_categories
from app.admin.services.admin_waifu_service import count_waifus, create_waifu, delete_waifu, get_waifu, list_waifus, search_waifus, set_waifu_media, update_waifu
from app.admin.services.admin_media_service import store_telegram_media
from app.services.waifu_media import send_waifu_media

router = Router()

_CREATE_WAIFU_LOCKS: defaultdict[int, asyncio.Lock] = defaultdict(lambda: asyncio.Lock())


class WaifuFlow(StatesGroup):
    waiting_category = State()
    waiting_category_search = State()
    waiting_search_query = State()
    waiting_name_ru = State()
    waiting_name_en = State()
    waiting_rarity = State()
    waiting_gender = State()
    waiting_age = State()
    waiting_alias_ru = State()
    waiting_alias_en = State()
    waiting_media = State()
    waiting_confirm_create = State()
    waiting_edit_value = State()
    waiting_edit_media = State()
    waiting_edit_confirm = State()
    waiting_delete_confirm = State()


def _lang(user) -> str:
    return "ru"


async def _safe_edit(message: Message, text: str, *, reply_markup=None, parse_mode: str | None = "HTML") -> None:
    await safe_replace_text(message, text, reply_markup=reply_markup, parse_mode=parse_mode)


def _waifu_text(row, lang: str) -> str:
    name_ru = escape(row["name_ru"] or "—")
    name_en = escape(row["name_en"] or "—")
    alias_ru = escape(str(row.get("alias_ru") or row.get("alias") or "—"))
    alias_en = escape(str(row.get("alias_en") or row.get("alias") or "—"))
    rarity = escape(row["rarity"] or "—")
    gender = escape(str(row["gender"] or "—"))
    age_value = row.get("age")
    age = escape(str(age_value if age_value not in (None, "") else "—"))
    category_name = escape((row.get("category_path_en") if lang == "en" else row.get("category_path_ru")) or (row["category_name_en"] if lang == "en" else row["category_name_ru"]) or "—")
    media_type = escape(str(row["media_type"] or "—"))
    active = "✅" if row["is_active"] else "⛔"

    if lang == "en":
        return (
            f"🧩 <b>{name_en}</b>\n"
            f"🇷🇺 RU alias: <b>{alias_ru}</b>\n"
            f"🇬🇧 EN alias: <b>{alias_en}</b>\n"
            f"🆔 ID: <code>{row['id']}</code>\n"
            f"🎂 Age: <b>{age}</b>\n"
            f"🏷 Rarity: <b>{rarity}</b>\n"
            f"⚧ Gender: <b>{gender}</b>\n"
            f"📂 Category: <b>{category_name}</b>\n"
            f"🖼 Media: <b>{media_type}</b>\n"
            f"Status: {active}"
        )

    return (
        f"🧩 <b>{name_ru}</b>\n"
        f"🇷🇺 Псевдоним: <b>{alias_ru}</b>\n"
        f"🇬🇧 Псевдоним EN: <b>{alias_en}</b>\n"
        f"🆔 ID: <code>{row['id']}</code>\n"
        f"🎂 Возраст: <b>{age}</b>\n"
        f"🏷 Редкость: <b>{rarity}</b>\n"
        f"⚧ Пол: <b>{gender}</b>\n"
        f"📂 Категория: <b>{category_name}</b>\n"
        f"🖼 Медиа: <b>{media_type}</b>\n"
        f"Статус: {active}"
    )


def _normalize_bool(text: str) -> bool | None:
    value = text.strip().lower()
    if value in {"1", "true", "yes", "да", "on", "active"}:
        return True
    if value in {"0", "false", "no", "нет", "off", "inactive"}:
        return False
    return None


def _normalize_optional_text(text: str | None) -> str | None:
    if text is None:
        return None
    value = text.strip()
    if not value or value in {"-", "—"}:
        return None
    return value


def _normalize_optional_age(text: str | None) -> str | None:
    value = _normalize_optional_text(text)
    if value is None:
        return None
    return value


def _normalize_media_type(media_type: str | None) -> str | None:
    if not media_type:
        return None
    return "animation" if media_type == "gif" else media_type


def _extract_media_file_id(message: Message, media_type: str | None) -> str | None:
    media_type = _normalize_media_type(media_type)
    if media_type == "photo" and message.photo:
        return message.photo[-1].file_id
    if media_type == "video" and message.video:
        return message.video.file_id
    if media_type == "animation" and message.animation:
        return message.animation.file_id
    if media_type == "document" and message.document:
        return message.document.file_id
    return None


async def _store_media_reference(message: Message, media_type: str | None, waifu_id: int | None = None) -> str | None:
    file_id = _extract_media_file_id(message, media_type)
    if not file_id or not message.bot:
        return None

    try:
        return await store_telegram_media(message.bot, file_id, media_type=media_type, waifu_id=waifu_id)
    except Exception:
        return None


def _waifu_list_item(row, lang: str) -> str:
    name = row["name_en"] if lang == "en" and row["name_en"] else row["name_ru"]
    cat = (row.get("category_path_en") if lang == "en" and row.get("category_path_en") else row.get("category_path_ru")) or (row["category_name_en"] if lang == "en" and row["category_name_en"] else row["category_name_ru"])
    media = row["media_type"] or "-"
    active = "✅" if row["is_active"] else "⛔"
    return f"• <code>{row['id']}</code> — {escape(name or '—')} | {escape(row['rarity'])} | {escape(str(row['gender']))} | {escape(cat or '-')} | media: {escape(media)} | {active}"


def _grouped_waifus_text(rows, lang: str) -> str:
    if not rows:
        return ""

    lines = ["<b>Вайфу по категориям</b>" if lang == "ru" else "<b>Waifus by category</b>"]
    buckets: dict[tuple[int | None, str], list] = defaultdict(list)
    order: list[tuple[int | None, str]] = []

    for row in rows:
        cat_id = row["category_id"]
        cat_name = row.get("category_path_en") if lang == "en" and row.get("category_path_en") else row.get("category_path_ru") or (row["category_name_en"] if lang == "en" and row["category_name_en"] else row["category_name_ru"])
        key = (cat_id, cat_name or "—")
        if key not in buckets:
            order.append(key)
        buckets[key].append(row)

    for cat_id, cat_name in order:
        lines.append("")
        lines.append(f"📁 <b>{escape(cat_name or '—')}</b> <code>#{cat_id or '—'}</code>")
        for row in buckets[(cat_id, cat_name)]:
            lines.append(_waifu_list_item(row, lang))

    return "\n".join(lines)



def _media_caption(waifu, lang: str) -> str:
    return _waifu_text(waifu, lang)


async def _render_waifu_card(message: Message, waifu, lang: str, reply_markup=None):
    text = _media_caption(waifu, lang)

    if waifu.get("is_active", True):
        try:
            sent = await send_waifu_media(
                message,
                waifu,
                text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        except Exception:
            sent = False
        if sent:
            try:
                await message.delete()
            except Exception:
                pass
            return sent

    return await _safe_edit(message, text, reply_markup=reply_markup, parse_mode="HTML")


async def _send_waifu_card(message: Message, waifu, lang: str, reply_markup=None):
    text = _media_caption(waifu, lang)

    if waifu.get("is_active", True):
        try:
            sent = await send_waifu_media(
                message,
                waifu,
                text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        except Exception:
            sent = False
        if sent:
            return sent

    return await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")


def _category_picker_title(lang: str, mode: str) -> str:
    return "Choose a category:" if lang == "en" else "Выбери категорию:"


async def _render_category_picker(call: CallbackQuery, pool, lang: str, mode: str, waifu_id: int = 0, parent_id: int | None = None):
    rows = await (get_root_categories(pool, lang=lang) if parent_id is None else get_child_categories(pool, parent_id, lang=lang))
    await _safe_edit(
        call.message,
        _category_picker_title(lang, mode),
        reply_markup=waifu_category_picker_kb(rows, lang=lang, mode=mode, waifu_id=waifu_id, parent_id=parent_id),
        parse_mode=None,
    )


@router.callback_query(F.data == "admin:waifus")
async def waifus_menu(call: CallbackQuery):
    if not call.message or not call.from_user:
        return

    lang = _lang(call.from_user)
    await _safe_edit(call.message, "🧩 <b>Вайфу</b>" if lang == "ru" else "🧩 <b>Waifus</b>", reply_markup=waifus_menu_kb(lang))
    await call.answer()


@router.callback_query(F.data == "admin:waifu:add")
async def waifu_add_start(call: CallbackQuery, state: FSMContext, pool):
    if not call.message or not call.from_user:
        return

    lang = _lang(call.from_user)
    await state.clear()
    await state.update_data(category_mode="add", waifu_id=0)
    await state.set_state(WaifuFlow.waiting_category_search)
    await _render_category_picker(call, pool, lang, mode="add", waifu_id=0, parent_id=None)
    await call.answer()


@router.callback_query(F.data.startswith("admin:waifu:list:"))
async def waifu_list(call: CallbackQuery, pool):
    if not call.message or not call.from_user:
        return

    lang = _lang(call.from_user)
    page = int(call.data.split(":")[-1])
    offset = page * 20
    total = await count_waifus(pool)
    rows = await list_waifus(pool, lang=lang, limit=20, offset=offset)

    if not rows:
        text = "Вайфу пока нет." if lang == "ru" else "No waifus yet."
        await _safe_edit(call.message, text, reply_markup=waifus_menu_kb(lang), parse_mode=None)
        await call.answer()
        return

    text = _grouped_waifus_text(rows, lang)
    has_prev = page > 0
    has_next = total > offset + 20
    await _safe_edit(call.message, text, reply_markup=waifus_list_kb(rows, page, has_prev, has_next, lang), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "admin:waifu:search")
async def waifu_search_start(call: CallbackQuery, state: FSMContext):
    if not call.message or not call.from_user:
        return

    lang = _lang(call.from_user)
    await state.clear()
    await state.update_data(search_mode="view")
    await state.set_state(WaifuFlow.waiting_search_query)
    text = "Введите имя вайфу или часть имени:" if lang == "ru" else "Enter waifu name or part of the name:"
    await _safe_edit(call.message, text, reply_markup=None, parse_mode=None)
    await call.answer()


@router.callback_query(F.data.startswith("admin:waifu:edit:"))
async def waifu_edit_start(call: CallbackQuery, state: FSMContext, pool):
    if not call.message or not call.from_user:
        return

    lang = _lang(call.from_user)
    waifu_id = int(call.data.split(":")[-1])
    waifu = await get_waifu(pool, waifu_id)

    if not waifu:
        await call.answer("Вайфу не найдена." if lang == "ru" else "Waifu not found.", show_alert=True)
        return

    await state.clear()
    await state.update_data(waifu_id=waifu_id)
    await _safe_edit(call.message, _waifu_text(waifu, lang) + ("\n\nВыбери поле:" if lang == "ru" else "\n\nChoose field:"), reply_markup=waifu_edit_fields_kb(waifu_id, lang), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "admin:waifu:delete")
async def waifu_delete_search_start(call: CallbackQuery, state: FSMContext):
    if not call.message or not call.from_user:
        return

    lang = _lang(call.from_user)
    await state.clear()
    await state.update_data(search_mode="delete")
    await state.set_state(WaifuFlow.waiting_search_query)
    text = "Введите имя вайфу или ID для удаления:" if lang == "ru" else "Enter waifu name or ID to delete:"
    await _safe_edit(call.message, text, parse_mode=None)
    await call.answer()


@router.message(StateFilter(WaifuFlow.waiting_search_query), F.text)
async def waifu_search_query(message: Message, state: FSMContext, pool):
    if not message.from_user:
        return

    lang = _lang(message.from_user)
    data = await state.get_data()
    mode = data.get("search_mode", "view")
    query = (message.text or "").strip()

    if not query:
        await message.answer("Пустой запрос." if lang == "ru" else "Empty query.")
        return

    rows = []
    if query.isdigit():
        waifu = await get_waifu(pool, int(query))
        if waifu:
            rows = [waifu]
    if not rows:
        rows = await search_waifus(pool, query, lang=lang, limit=15)

    if not rows:
        await message.answer("Ничего не найдено." if lang == "ru" else "Nothing found.", reply_markup=waifus_menu_kb(lang))
        await state.clear()
        return

    if mode == "delete":
        await message.answer("Найденные вайфу для удаления:" if lang == "ru" else "Found waifus for deletion:", reply_markup=waifu_search_results_kb(rows, lang))
    else:
        await message.answer("Найденные вайфу:" if lang == "ru" else "Found waifus:", reply_markup=waifu_search_results_kb(rows, lang))

    await state.clear()


@router.callback_query(F.data.startswith("admin:waifu:open:"))
async def waifu_open(call: CallbackQuery, pool):
    if not call.message or not call.from_user:
        return

    lang = _lang(call.from_user)
    waifu_id = int(call.data.split(":")[-1])
    waifu = await get_waifu(pool, waifu_id)

    if not waifu:
        await call.answer("Вайфу не найдена." if lang == "ru" else "Waifu not found.", show_alert=True)
        return

    await _render_waifu_card(call.message, waifu, lang, reply_markup=waifu_card_kb(waifu_id, waifu["category_id"], lang))
    await call.answer()


@router.callback_query(F.data.startswith("admin:waifu:field:"))
async def waifu_field_pick(call: CallbackQuery, state: FSMContext, pool):
    if not call.message or not call.from_user:
        return

    lang = _lang(call.from_user)
    _, _, _, waifu_id_str, field = call.data.split(":", 4)
    waifu_id = int(waifu_id_str)
    waifu = await get_waifu(pool, waifu_id)

    if not waifu:
        await call.answer("Вайфу не найдена." if lang == "ru" else "Waifu not found.", show_alert=True)
        return

    await state.clear()
    await state.update_data(waifu_id=waifu_id, edit_field=field)

    if field == "category_id":
        await state.update_data(search_mode="edit_category")
        await _render_category_picker(call, pool, lang, mode="edit", waifu_id=waifu_id, parent_id=None)
        await state.set_state(WaifuFlow.waiting_edit_value)
    elif field == "rarity":
        await state.set_state(WaifuFlow.waiting_edit_value)
        await _safe_edit(call.message, "Выбери новую редкость:" if lang == "ru" else "Choose new rarity:", reply_markup=waifu_rarity_kb(waifu_id, lang, mode="edit"), parse_mode=None)
    elif field == "gender":
        await state.set_state(WaifuFlow.waiting_edit_value)
        await _safe_edit(call.message, "Выбери новый пол:" if lang == "ru" else "Choose new gender:", reply_markup=waifu_gender_kb(waifu_id, lang, mode="edit"), parse_mode=None)
    elif field == "media":
        await state.set_state(WaifuFlow.waiting_edit_media)
        await _safe_edit(call.message, "Выбери тип медиа:" if lang == "ru" else "Choose media type:", reply_markup=waifu_media_type_kb(waifu_id, lang, mode="edit"), parse_mode=None)
    elif field == "is_active":
        await state.set_state(WaifuFlow.waiting_edit_value)
        await _safe_edit(call.message, "Сделать вайфу активной?" if lang == "ru" else "Make waifu active?", reply_markup=waifu_bool_kb(waifu_id, field, lang), parse_mode=None)
    else:
        await state.set_state(WaifuFlow.waiting_edit_value)
        prompts = {
            "name_ru": "Введите новое имя на русском:" if lang == "ru" else "Enter new Russian name:",
            "name_en": "Введите новое имя на английском:" if lang == "ru" else "Enter new English name:",
            "alias_ru": "Введите новое русское прозвище, либо '-' чтобы пропустить:" if lang == "ru" else "Enter a new Russian alias, or '-' to skip:",
            "alias_en": "Введите новое английское прозвище, либо '-' чтобы пропустить:" if lang == "ru" else "Enter a new English alias, or '-' to skip:",
            "age": "Введите новый возраст в любом формате, например 20-25, 20k+, ±100, либо '-' чтобы пропустить:" if lang == "ru" else "Enter a new age in any format, e.g. 20-25, 20k+, ±100, or '-' to skip:",
            "rarity": "Введите новую редкость:" if lang == "ru" else "Enter new rarity:",
            "gender": "Введите новый пол или none:" if lang == "ru" else "Enter new gender or none:",
        }
        await _safe_edit(call.message, prompts[field], parse_mode=None)

    await call.answer()


@router.callback_query(F.data.startswith("admin:waifu:catroot:"))
async def waifu_category_root(call: CallbackQuery, pool):
    if not call.message or not call.from_user:
        return

    _, _, _, mode, waifu_id_str = call.data.split(":", 4)
    lang = _lang(call.from_user)
    await _render_category_picker(call, pool, lang, mode=mode, waifu_id=int(waifu_id_str), parent_id=None)
    await call.answer()


@router.callback_query(F.data.startswith("admin:waifu:catopen:"))
async def waifu_category_open(call: CallbackQuery, pool):
    if not call.message or not call.from_user:
        return

    _, _, _, mode, waifu_id_str, cat_id_str = call.data.split(":", 5)
    lang = _lang(call.from_user)
    category_id = int(cat_id_str)
    waifu_id = int(waifu_id_str)

    category = await get_category(pool, category_id)
    if not category:
        await call.answer("Категория не найдена." if lang == "ru" else "Category not found.", show_alert=True)
        return

    rows = await get_child_categories(pool, category_id, lang=lang)
    if category["node_type"] == "leaf":
        title = f"🎯 <b>{escape(category['name_ru'])}</b>\nID: <code>{category_id}</code>" if lang == "ru" else f"🎯 <b>{escape(category['name_en'] or category['name_ru'])}</b>\nID: <code>{category_id}</code>"
        await _safe_edit(call.message, title, reply_markup=waifu_category_picker_kb([category], lang=lang, mode=mode, waifu_id=waifu_id, parent_id=category["parent_id"]), parse_mode="HTML")
        await call.answer()
        return

    title = f"📁 <b>{escape(category['name_ru'])}</b>\nВыбери подкатегорию:" if lang == "ru" else f"📁 <b>{escape(category['name_en'] or category['name_ru'])}</b>\nChoose a subcategory:"
    await _safe_edit(call.message, title, reply_markup=waifu_category_picker_kb(rows, lang=lang, mode=mode, waifu_id=waifu_id, parent_id=category["parent_id"]), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("admin:waifu:catpick:"))
async def waifu_category_pick(call: CallbackQuery, state: FSMContext, pool):
    if not call.message or not call.from_user:
        return

    _, _, _, mode, waifu_id_str, cat_id_str = call.data.split(":", 5)
    waifu_id = int(waifu_id_str)
    category_id = int(cat_id_str)
    lang = _lang(call.from_user)

    category = await get_category(pool, category_id)
    if not category:
        await call.answer("Категория не найдена." if lang == "ru" else "Category not found.", show_alert=True)
        return

    if category["node_type"] != "leaf":
        await call.answer("Нужна leaf-категория." if lang == "ru" else "A leaf category is required.", show_alert=True)
        return

    if mode == "add":
        await state.update_data(category_id=category_id)
        await state.set_state(WaifuFlow.waiting_name_ru)
        await _safe_edit(call.message, "Введите имя вайфу на русском:" if lang == "ru" else "Enter waifu name in Russian:", parse_mode=None)
    else:
        waifu = await get_waifu(pool, waifu_id)
        if not waifu:
            await call.answer("Вайфу не найдена." if lang == "ru" else "Waifu not found.", show_alert=True)
            return

        await update_waifu(pool, waifu_id=waifu_id, category_id=category_id, name_ru=waifu["name_ru"], name_en=waifu["name_en"], alias_ru=waifu.get("alias_ru"), alias_en=waifu.get("alias_en"), alias=waifu.get("alias"), age=waifu.get("age"), rarity=waifu["rarity"], gender=waifu["gender"], is_active=bool(waifu["is_active"]))
        await write_audit_log(pool, user_id=call.from_user.id, action="waifu_update", target_type="waifu", target_id=waifu_id, payload={"category_id": category_id})
        await invalidate_waifu_catalog()
        await state.clear()
        await _safe_edit(call.message, "Категория вайфу обновлена." if lang == "ru" else "Waifu category updated.", reply_markup=waifu_card_kb(waifu_id, category_id, lang), parse_mode=None)

    await call.answer()


@router.callback_query(F.data.startswith("admin:waifu:catsearch:"))
async def waifu_category_search_start(call: CallbackQuery, state: FSMContext):
    if not call.message or not call.from_user:
        return

    _, _, _, mode, waifu_id_str = call.data.split(":", 4)
    lang = _lang(call.from_user)
    await state.clear()
    await state.update_data(search_mode=f"category_{mode}", waifu_id=int(waifu_id_str), category_mode=mode)
    await state.set_state(WaifuFlow.waiting_category_search)
    await _safe_edit(call.message, "Введите часть названия категории:" if lang == "ru" else "Enter part of the category name:", parse_mode=None)
    await call.answer()


@router.message(StateFilter(WaifuFlow.waiting_category_search), F.text)
async def waifu_category_search(message: Message, state: FSMContext, pool):
    if not message.from_user:
        return

    lang = _lang(message.from_user)
    data = await state.get_data()
    mode = data.get("category_mode", "add")
    waifu_id = int(data.get("waifu_id") or 0)
    query = (message.text or "").strip()

    if not query:
        await message.answer("Пустой запрос." if lang == "ru" else "Empty query.")
        return

    rows = await search_categories(pool, query, lang=lang, limit=15)
    if not rows:
        await message.answer("Ничего не найдено." if lang == "ru" else "Nothing found.", reply_markup=waifus_menu_kb(lang))
        await state.clear()
        return

    await message.answer("Найденные категории:" if lang == "ru" else "Found categories:", reply_markup=waifu_category_picker_kb(rows, lang=lang, mode=mode, waifu_id=waifu_id, parent_id=None))
    await state.clear()


@router.message(StateFilter(WaifuFlow.waiting_name_ru), F.text)
async def waifu_name_ru(message: Message, state: FSMContext):
    lang = _lang(message.from_user)
    text = (message.text or "").strip()
    if not text:
        await message.answer("Имя не может быть пустым.")
        return
    await state.update_data(name_ru=text)
    await state.set_state(WaifuFlow.waiting_name_en)
    await message.answer("Введите имя вайфу на английском:" if lang == "ru" else "Enter waifu name in English:")


@router.message(StateFilter(WaifuFlow.waiting_name_en), F.text)
async def waifu_name_en(message: Message, state: FSMContext):
    lang = _lang(message.from_user)
    text = (message.text or "").strip()
    if not text:
        await message.answer("Имя не может быть пустым.")
        return
    await state.update_data(name_en=text)
    await state.set_state(WaifuFlow.waiting_rarity)
    await message.answer("Выбери редкость:" if lang == "ru" else "Choose rarity:", reply_markup=waifu_rarity_kb(0, lang, mode="add"))


@router.message(StateFilter(WaifuFlow.waiting_rarity), F.text)
async def waifu_rarity(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Редкость не может быть пустой.")
        return
    await state.update_data(rarity=text)
    await state.set_state(WaifuFlow.waiting_gender)
    await message.answer("Введите пол или напиши none:")




@router.callback_query(F.data.startswith("admin:waifu:rarity:"))
async def waifu_rarity_pick(call: CallbackQuery, state: FSMContext, pool):
    if not call.message or not call.from_user:
        return

    _, _, _, mode, waifu_id_str, rarity = call.data.split(":", 5)
    lang = _lang(call.from_user)
    waifu_id = int(waifu_id_str)

    if mode == "add":
        await state.update_data(rarity=rarity)
        await state.set_state(WaifuFlow.waiting_gender)
        await _safe_edit(call.message, "Выбери пол:", reply_markup=waifu_gender_kb(0, lang, mode="add"), parse_mode=None)
        await call.answer()
        return

    waifu = await get_waifu(pool, waifu_id)
    if not waifu:
        await call.answer("Вайфу не найдена." if lang == "ru" else "Waifu not found.", show_alert=True)
        return

    await update_waifu(
        pool,
        waifu_id=waifu_id,
        category_id=waifu["category_id"],
        name_ru=waifu["name_ru"],
        name_en=waifu["name_en"],
        alias=waifu.get("alias"),
        age=waifu.get("age"),
        rarity=rarity,
        gender=waifu["gender"],
        is_active=bool(waifu["is_active"]),
    )
    await write_audit_log(pool, user_id=call.from_user.id, action="waifu_update", target_type="waifu", target_id=waifu_id, payload={"rarity": rarity})
    await invalidate_waifu_catalog()
    await state.clear()
    updated = await get_waifu(pool, waifu_id)
    if updated:
        await _render_waifu_card(call.message, updated, lang, reply_markup=waifu_card_kb(waifu_id, updated["category_id"], lang))
    await call.answer()


@router.callback_query(F.data.startswith("admin:waifu:gender:"))
async def waifu_gender_pick(call: CallbackQuery, state: FSMContext, pool):
    if not call.message or not call.from_user:
        return

    _, _, _, mode, waifu_id_str, gender = call.data.split(":", 5)
    lang = _lang(call.from_user)
    waifu_id = int(waifu_id_str)
    gender_value = None if gender == "none" else gender

    if mode == "add":
        await state.update_data(gender=gender_value)
        await state.set_state(WaifuFlow.waiting_age)
        await _safe_edit(call.message, "Укажи возраст в любом формате, например 20-25, 20k+, ±100, или '-' чтобы пропустить:" if lang == "ru" else "Enter age in any format, e.g. 20-25, 20k+, ±100, or '-' to skip:", reply_markup=None, parse_mode=None)
        await call.answer()
        return

    waifu = await get_waifu(pool, waifu_id)
    if not waifu:
        await call.answer("Вайфу не найдена." if lang == "ru" else "Waifu not found.", show_alert=True)
        return

    await update_waifu(
        pool,
        waifu_id=waifu_id,
        category_id=waifu["category_id"],
        name_ru=waifu["name_ru"],
        name_en=waifu["name_en"],
        alias=waifu.get("alias"),
        age=waifu.get("age"),
        rarity=waifu["rarity"],
        gender=gender_value,
        is_active=bool(waifu["is_active"]),
    )
    await write_audit_log(pool, user_id=call.from_user.id, action="waifu_update", target_type="waifu", target_id=waifu_id, payload={"gender": gender_value})
    await invalidate_waifu_catalog()
    await state.clear()
    updated = await get_waifu(pool, waifu_id)
    if updated:
        await _render_waifu_card(call.message, updated, lang, reply_markup=waifu_card_kb(waifu_id, updated["category_id"], lang))
    await call.answer()


@router.message(StateFilter(WaifuFlow.waiting_gender), F.text)
async def waifu_gender(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    gender = None if text.lower() in {"none", "", "null"} else text
    await state.update_data(gender=gender)
    await state.set_state(WaifuFlow.waiting_age)
    await message.answer("Укажи возраст в любом формате, например 20-25, 20k+, ±100, или '-' чтобы пропустить:" if _lang(message.from_user) == "ru" else "Enter age in any format, e.g. 20-25, 20k+, ±100, or '-' to skip:")


@router.message(StateFilter(WaifuFlow.waiting_age), F.text)
async def waifu_age(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    age = _normalize_optional_age(text)
    if text not in {"", "-", "—"} and age is None:
        await message.answer("Возраст не должен быть пустым. Используй любой формат или '-' для пропуска." if _lang(message.from_user) == "ru" else "Age cannot be empty. Use any format or '-' to skip.")
        return

    await state.update_data(age=age)
    await state.set_state(WaifuFlow.waiting_alias_ru)
    await message.answer("Укажи русское прозвище, например 'бог-дракон', или '-' чтобы пропустить:" if _lang(message.from_user) == "ru" else "Enter the Russian alias, e.g. 'dragon-god', or '-' to skip:")


@router.message(StateFilter(WaifuFlow.waiting_alias_ru), F.text)
async def waifu_alias_ru(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    alias_ru = None if text in {"", "-", "—"} else text
    await state.update_data(alias_ru=alias_ru)
    await state.set_state(WaifuFlow.waiting_alias_en)
    await message.answer("Укажи английское прозвище, например 'dragon-god', или '-' чтобы пропустить:" if _lang(message.from_user) == "ru" else "Enter the English alias, e.g. 'dragon-god', or '-' to skip:")


@router.message(StateFilter(WaifuFlow.waiting_alias_en), F.text)
async def waifu_alias_en(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    alias_en = None if text in {"", "-", "—"} else text
    await state.update_data(alias_en=alias_en)
    await state.set_state(WaifuFlow.waiting_media)
    await message.answer("Выбери тип медиа:" if _lang(message.from_user) == "ru" else "Choose media type:", reply_markup=waifu_media_type_kb(0, _lang(message.from_user), mode="add"))


@router.callback_query(F.data.startswith("admin:waifu:mediatype:"))
async def waifu_media_type_pick(call: CallbackQuery, state: FSMContext):

    if not call.message or not call.from_user:
        return

    _, _, _, mode, waifu_id_str, media_type = call.data.split(":", 5)
    lang = _lang(call.from_user)
    normalized = _normalize_media_type(media_type)

    await state.update_data(media_type=normalized or media_type)

    if mode == "edit":
        await state.set_state(WaifuFlow.waiting_edit_media)
        text = "Теперь отправьте новый медиафайл." if lang == "ru" else "Now send the new media file."
    else:
        await state.set_state(WaifuFlow.waiting_media)
        text = "Теперь отправьте сам медиафайл." if lang == "ru" else "Now send the media file."

    await _safe_edit(call.message, text, reply_markup=None, parse_mode=None)
    await call.answer()


@router.message(StateFilter(WaifuFlow.waiting_media), F.photo | F.video | F.animation | F.document)
async def waifu_media(message: Message, state: FSMContext, pool):
    data = await state.get_data()
    media_type = data.get("media_type")
    current_waifu_id = int(data["waifu_id"]) if data.get("waifu_id") else None
    file_id = await _store_media_reference(message, media_type, waifu_id=current_waifu_id)

    if not file_id:
        await message.answer(
            "Не увидел нужный тип медиа. Отправь ещё раз." if _lang(message.from_user) == "ru"
            else "I did not detect the selected media type. Send it again."
        )
        return

    category_id = data.get("category_id")
    if not category_id and data.get("waifu_id"):
        current_waifu = await get_waifu(pool, int(data["waifu_id"]))
        if current_waifu:
            category_id = current_waifu.get("category_id")

    if not category_id:
        await state.clear()
        await message.answer(
            "Не удалось определить категорию вайфу. Начни добавление заново и выбери категорию ещё раз." if _lang(message.from_user) == "ru"
            else "Could not determine the waifu category. Start over and choose the category again."
        )
        return

    name_ru = data.get("name_ru")
    if not name_ru:
        await state.clear()
        await message.answer(
            "Не хватает данных для сохранения. Начни добавление заново." if _lang(message.from_user) == "ru"
            else "Required data is missing. Start the flow again."
        )
        return

    await state.update_data(category_id=category_id, file_id=file_id)
    await state.set_state(WaifuFlow.waiting_confirm_create)

    preview = (
        "<b>Проверь данные</b>\n"
        f"Категория: <code>{category_id}</code>\n"
        f"Имя RU: {escape(name_ru)}\n"
        f"Имя EN: {escape(data.get('name_en') or name_ru or '—')}\n"
        f"Псевдоним RU: {escape(str(data.get('alias_ru') or '—'))}\n"
        f"Псевдоним EN: {escape(str(data.get('alias_en') or '—'))}\n"
        f"Возраст: {escape(str(data.get('age') or '—'))}\n"
        f"Редкость: {escape(data.get('rarity') or '—')}\n"
        f"Пол: {escape(str(data.get('gender') or '—'))}\n"
        f"Медиа: {escape(str(media_type or '—'))}"
    )
    lang = _lang(message.from_user)
    await message.answer(preview, parse_mode="HTML", reply_markup=kb_confirm_cancel("admin:waifu:confirm", "admin:waifus", lang))

@router.callback_query(F.data == "admin:waifu:confirm")
async def waifu_confirm(call: CallbackQuery, state: FSMContext, pool):
    if not call.message or not call.from_user:
        return

    lang = _lang(call.from_user)
    lock = _CREATE_WAIFU_LOCKS[call.from_user.id]

    async with lock:
        data = await state.get_data()
        if not data or not data.get("category_id") or not data.get("name_ru") or not data.get("rarity") or not data.get("file_id"):
            await call.answer(
                "Создание уже обработано или данные устарели. Начни заново." if lang == "ru"
                else "The creation has already been processed or the data is stale. Start over.",
                show_alert=True,
            )
            return

        category_id = int(data["category_id"])
        category = await get_category(pool, category_id)
        if not category:
            await call.answer("Категория не найдена." if lang == "ru" else "Category not found.", show_alert=True)
            return
        if category["node_type"] != "leaf":
            await call.answer("Нужна leaf-категория." if lang == "ru" else "A leaf category is required.", show_alert=True)
            return

        waifu_id = await create_waifu(
            pool,
            category_id=category_id,
            name_ru=data["name_ru"],
            name_en=data.get("name_en") or data["name_ru"],
            rarity=data["rarity"],
            gender=data.get("gender"),
            age=data.get("age"),
            alias_ru=data.get("alias_ru"),
            alias_en=data.get("alias_en"),
        )
        await set_waifu_media(pool, waifu_id=waifu_id, media_type=data["media_type"], file_id=data["file_id"], is_primary=True)

        await write_audit_log(
            pool,
            user_id=call.from_user.id,
            action="waifu_create",
            target_type="waifu",
            target_id=waifu_id,
            payload={
                "category_id": category_id,
                "name_ru": data["name_ru"],
                "name_en": data.get("name_en") or data["name_ru"],
                "rarity": data["rarity"],
                "gender": data.get("gender"),
                "media_type": data["media_type"],
                "alias_ru": data.get("alias_ru"),
                "alias_en": data.get("alias_en"),
                "age": data.get("age"),
            },
        )
        await invalidate_waifu_catalog()
        await state.clear()
        await _safe_edit(call.message, f"Вайфу создана. ID: <code>{waifu_id}</code>" if lang == "ru" else f"Waifu created. ID: <code>{waifu_id}</code>", reply_markup=waifus_menu_kb(lang), parse_mode="HTML")
        await call.answer()


@router.callback_query(F.data.startswith("admin:waifu:media:"))
async def waifu_media_edit_start(call: CallbackQuery, state: FSMContext, pool):

    if not call.message or not call.from_user:
        return

    waifu_id = int(call.data.split(":")[-1])
    waifu = await get_waifu(pool, waifu_id)
    if not waifu:
        await call.answer("Вайфу не найдена." if _lang(call.from_user) == "ru" else "Waifu not found.", show_alert=True)
        return

    lang = _lang(call.from_user)
    await state.clear()
    await state.update_data(waifu_id=waifu_id, edit_field="media")
    await state.set_state(WaifuFlow.waiting_edit_media)
    await _safe_edit(call.message, "Выбери тип медиа:" if lang == "ru" else "Choose media type:", reply_markup=waifu_media_type_kb(waifu_id, lang, mode="edit"), parse_mode=None)
    await call.answer()


@router.message(StateFilter(WaifuFlow.waiting_edit_media), F.photo | F.video | F.animation | F.document)
async def waifu_edit_media(message: Message, state: FSMContext, pool):
    data = await state.get_data()
    waifu_id = int(data["waifu_id"])
    media_type = data.get("media_type")
    file_id = await _store_media_reference(message, media_type, waifu_id=waifu_id)

    if not file_id:
        await message.answer("Не увидел нужный тип медиа. Отправь ещё раз.")
        return

    await set_waifu_media(pool, waifu_id=waifu_id, media_type=media_type, file_id=file_id, is_primary=True)
    await write_audit_log(pool, user_id=message.from_user.id, action="waifu_media_update", target_type="waifu", target_id=waifu_id, payload={"media_type": media_type})
    await invalidate_waifu_catalog()
    await state.clear()

    updated = await get_waifu(pool, waifu_id)
    lang = _lang(message.from_user)
    if updated:
        await _send_waifu_card(message, updated, lang, reply_markup=waifu_card_kb(waifu_id, updated["category_id"], lang))
    else:
        await message.answer("Медиа обновлено." if lang == "ru" else "Media updated.", reply_markup=waifus_menu_kb(lang))


@router.callback_query(F.data.startswith("admin:waifu:bool:"))
async def waifu_bool_set(call: CallbackQuery, pool):
    if not call.message or not call.from_user:
        return

    lang = _lang(call.from_user)
    _, _, _, waifu_id_str, field, value = call.data.split(":", 5)
    waifu_id = int(waifu_id_str)
    waifu = await get_waifu(pool, waifu_id)

    if not waifu:
        await call.answer("Вайфу не найдена." if lang == "ru" else "Waifu not found.", show_alert=True)
        return

    is_active = value == "1"
    await update_waifu(pool, waifu_id=waifu_id, category_id=waifu["category_id"], name_ru=waifu["name_ru"], name_en=waifu["name_en"], alias_ru=waifu.get("alias_ru"), alias_en=waifu.get("alias_en"), alias=waifu.get("alias"), age=waifu.get("age"), rarity=waifu["rarity"], gender=waifu["gender"], is_active=is_active)
    await write_audit_log(pool, user_id=call.from_user.id, action="waifu_update", target_type="waifu", target_id=waifu_id, payload={field: is_active})
    await invalidate_waifu_catalog()
    await _safe_edit(call.message, "Состояние вайфу обновлено." if lang == "ru" else "Waifu state updated.", reply_markup=waifu_edit_fields_kb(waifu_id, lang), parse_mode=None)
    await call.answer()


@router.message(StateFilter(WaifuFlow.waiting_edit_value), F.text)
async def waifu_edit_value(message: Message, state: FSMContext, pool):
    data = await state.get_data()
    waifu_id = int(data["waifu_id"])
    field = data["edit_field"]
    waifu = await get_waifu(pool, waifu_id)

    if not waifu:
        await message.answer("Вайфу не найдена." if _lang(message.from_user) == "ru" else "Waifu not found.")
        return

    raw = (message.text or "").strip()
    updates = {"category_id": waifu["category_id"], "name_ru": waifu["name_ru"], "name_en": waifu["name_en"], "alias_ru": waifu.get("alias_ru"), "alias_en": waifu.get("alias_en"), "alias": waifu.get("alias"), "age": waifu.get("age"), "rarity": waifu["rarity"], "gender": waifu["gender"], "is_active": bool(waifu["is_active"])}

    if field in {"name_ru", "name_en", "rarity", "alias_ru", "alias_en"}:
        if raw in {"", "-", "—"}:
            if field in {"alias_ru", "alias_en"}:
                updates[field] = None
            else:
                await message.answer("Значение не может быть пустым.")
                return
        else:
            updates[field] = raw
    elif field == "age":
        if raw in {"", "-", "—"}:
            updates[field] = None
        else:
            updates[field] = raw
    elif field == "gender":
        updates[field] = None if raw.lower() in {"none", "", "null"} else raw
    elif field == "is_active":
        value = _normalize_bool(raw)
        if value is None:
            await message.answer("Нужно yes/no, true/false, 1/0.")
            return
        updates[field] = value
    else:
        await message.answer("Это поле выбирается кнопками." if _lang(message.from_user) == "ru" else "This field is controlled by buttons.")
        return

    await state.update_data(edit_value=updates)
    lang = _lang(message.from_user)
    await message.answer(
        "<b>Сохранить изменения?</b>\n" f"ID: <code>{waifu_id}</code>\n" f"field: {escape(field)}\n" f"value: {escape(str(updates[field]))}" if lang == "ru" else "<b>Save changes?</b>\n" f"ID: <code>{waifu_id}</code>\n" f"field: {escape(field)}\n" f"value: {escape(str(updates[field]))}",
        parse_mode="HTML",
        reply_markup=kb_confirm_cancel(f"admin:waifu:editconfirm:{waifu_id}", f"admin:waifu:open:{waifu_id}", lang),
    )
    await state.set_state(WaifuFlow.waiting_edit_confirm)


@router.callback_query(F.data.startswith("admin:waifu:editconfirm:"))
async def waifu_edit_confirm(call: CallbackQuery, state: FSMContext, pool):
    if not call.message or not call.from_user:
        return

    waifu_id = int(call.data.split(":")[-1])
    data = await state.get_data()
    upd = data.get("edit_value")
    lang = _lang(call.from_user)

    if not upd:
        await call.answer("Нет данных для сохранения." if lang == "ru" else "No data to save.", show_alert=True)
        return

    category = await get_category(pool, int(upd["category_id"]))
    if not category:
        await call.answer("Категория не найдена." if lang == "ru" else "Category not found.", show_alert=True)
        return
    if category["node_type"] != "leaf":
        await call.answer("Нужна leaf-категория." if lang == "ru" else "A leaf category is required.", show_alert=True)
        return

    await update_waifu(pool, waifu_id=waifu_id, category_id=int(upd["category_id"]), name_ru=upd["name_ru"], name_en=upd["name_en"], alias_ru=upd.get("alias_ru"), alias_en=upd.get("alias_en"), alias=upd.get("alias"), age=upd.get("age"), rarity=upd["rarity"], gender=upd["gender"], is_active=upd["is_active"])
    await write_audit_log(pool, user_id=call.from_user.id, action="waifu_update", target_type="waifu", target_id=waifu_id, payload=upd)
    await invalidate_waifu_catalog()
    await state.clear()

    waifu = await get_waifu(pool, waifu_id)
    if waifu:
        await _render_waifu_card(call.message, waifu, lang, reply_markup=waifu_card_kb(waifu_id, waifu["category_id"], lang))
    else:
        await _safe_edit(call.message, "Вайфу обновлена." if lang == "ru" else "Waifu updated.", reply_markup=waifus_menu_kb(lang), parse_mode=None)
    await call.answer()


@router.callback_query(F.data.startswith("admin:waifu:deleteconfirm:"))
async def waifu_delete_confirm(call: CallbackQuery, state: FSMContext, pool):
    if not call.message or not call.from_user:
        return

    waifu_id = int(call.data.split(":")[-1])
    lang = _lang(call.from_user)
    await delete_waifu(pool, waifu_id)
    await write_audit_log(pool, user_id=call.from_user.id, action="waifu_delete", target_type="waifu", target_id=waifu_id)
    await invalidate_waifu_catalog()
    await state.clear()
    await _safe_edit(call.message, "Вайфу удалена." if lang == "ru" else "Waifu deleted.", reply_markup=waifus_menu_kb(lang), parse_mode=None)
    await call.answer()


@router.callback_query(F.data.startswith("admin:waifu:delete:"))
async def waifu_delete_start(call: CallbackQuery, pool):
    if not call.message or not call.from_user:
        return

    waifu_id = int(call.data.split(":")[-1])
    waifu = await get_waifu(pool, waifu_id)
    if not waifu:
        await call.answer("Вайфу не найдена." if _lang(call.from_user) == "ru" else "Waifu not found.", show_alert=True)
        return

    lang = _lang(call.from_user)
    await _safe_edit(
        call.message,
        (
            "Удалить вайфу?\n"
            f"ID: {waifu_id}\n"
            f"RU: {waifu['name_ru']}\n"
            f"EN: {waifu['name_en']}\n"
            f"Редкость: {waifu['rarity']}\n"
            f"Медиа: {waifu['media_type'] or '-'}"
            if lang == "ru"
            else
            "Delete waifu?\n"
            f"ID: {waifu_id}\n"
            f"RU: {waifu['name_ru']}\n"
            f"EN: {waifu['name_en']}\n"
            f"Редкость: {waifu['rarity']}\n"
            f"Медиа: {waifu['media_type'] or '-'}"
        ),
        reply_markup=kb_confirm_cancel(f"admin:waifu:deleteconfirm:{waifu_id}", f"admin:waifu:open:{waifu_id}", lang),
        parse_mode=None,
    )
    await call.answer()
