from __future__ import annotations

import html
from collections import OrderedDict

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.services.user_service import get_user_waifus, get_user_language
from app.services.pagination import paginate
from app.services.waifu_ui import get_waifu_name, format_category_path
from app.services.chat_category_service import filter_allowed_waifus_for_chat
from app.services.category_service import get_category_path
from app.services.texts import format_rarity

router = Router()

PAGE_SIZE = 10


def _lang_text(lang: str, ru: str, en: str) -> str:
    return ru if lang == "ru" else en


def _sort_text_key(text: str) -> tuple[int, str]:
    normalized = (text or "—").strip().casefold()
    first = next((ch for ch in normalized if not ch.isspace()), "")
    if not first:
        bucket = 2
    elif first.isdigit() or not first.isalpha():
        bucket = 0
    else:
        bucket = 1
    return bucket, normalized


class MyWaifusSearch(StatesGroup):
    waiting_query = State()


def _normalize_query(text: str | None) -> str:
    return (text or "").strip().casefold()


def _waifu_search_blob(waifu: dict) -> str:
    parts = (
        waifu.get("name_ru"),
        waifu.get("name_en"),
        waifu.get("alias_ru"),
        waifu.get("alias_en"),
        waifu.get("alias"),
    )
    return " ".join(str(part).casefold() for part in parts if part)


def _waifu_matches_owned_query(waifu: dict, query: str) -> bool:
    normalized_query = _normalize_query(query)
    if not normalized_query:
        return False
    return normalized_query in _waifu_search_blob(waifu)


def _build_mywaifus_keyboard(
    page_items: list[dict],
    user_lang: str,
    current_page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    rows.append([
        InlineKeyboardButton(
            text=_lang_text(user_lang, "🔎 Найти вайфу", "🔎 Find waifu"),
            callback_data="mywaifus:search",
        )
    ])

    for i in range(0, len(page_items), 2):
        row: list[InlineKeyboardButton] = []
        for waifu in page_items[i:i + 2]:
            row.append(
                InlineKeyboardButton(
                    text=f"🎴 {get_waifu_name(waifu, user_lang)}",
                    callback_data=f"wc:open:mywaifus:{waifu['id']}",
                )
            )
        rows.append(row)

    pager: list[InlineKeyboardButton] = []
    if current_page > 1:
        pager.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"mywaifus:{current_page - 1}")
        )
    if current_page < total_pages:
        pager.append(
            InlineKeyboardButton(text="➡️", callback_data=f"mywaifus:{current_page + 1}")
        )
    if pager:
        rows.append(pager)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_mywaifus_search_results_keyboard(
    waifus: list[dict],
    user_lang: str,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for i in range(0, len(waifus), 2):
        row: list[InlineKeyboardButton] = []
        for waifu in waifus[i:i + 2]:
            row.append(
                InlineKeyboardButton(
                    text=f"🎴 {get_waifu_name(waifu, user_lang)}",
                    callback_data=f"wc:open:mywaifus:{waifu['id']}",
                )
            )
        rows.append(row)

    rows.append([
        InlineKeyboardButton(
            text=_lang_text(user_lang, "⬅️ Назад в гарем", "⬅️ Back to collection"),
            callback_data="mywaifus:back",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _render_mywaifus_search_results(
    waifus: list[dict],
    user_lang: str,
    query: str,
) -> str:
    category_paths = await _build_waifu_category_path_map(waifus, user_lang)

    waifus.sort(
        key=lambda w: (
            category_paths.get(int(w["category_id"]), "—").casefold()
            if w.get("category_id") is not None
            else "—",
            get_waifu_name(w, user_lang).casefold(),
            int(w.get("id") or 0),
        )
    )

    title = _lang_text(user_lang, "🔎 Поиск по твоему гарему", "🔎 Search in your collection")
    lines = [
        f"{title}: <i>{html.escape(query)}</i>",
        "",
        _lang_text(
            user_lang,
            f"🎴 Найдено: <b>{len(waifus)}</b>",
            f"🎴 Found: <b>{len(waifus)}</b>",
        ),
        "",
    ]
    lines.extend(_format_group_lines(waifus, category_paths, user_lang))
    return "\n".join(lines)


async def _build_waifu_category_path_map(items: list[dict], user_lang: str) -> dict[int, str]:
    category_ids = sorted({int(w["category_id"]) for w in items if w.get("category_id") is not None})
    path_map: dict[int, str] = {}
    for category_id in category_ids:
        rows = await get_category_path(category_id)
        path_map[category_id] = format_category_path(rows, user_lang)
    return path_map


def _group_waifus_by_category(
    waifus: list[dict],
    category_paths: dict[int, str],
    user_lang: str,
) -> list[tuple[str, list[dict]]]:
    grouped: OrderedDict[str, list[dict]] = OrderedDict()
    for waifu in waifus:
        category_id = waifu.get("category_id")
        category_path = category_paths.get(int(category_id)) if category_id is not None else "—"
        grouped.setdefault(category_path or "—", []).append(waifu)

    def group_key(item: tuple[str, list[dict]]) -> tuple[int, str, str]:
        category_path, group_items = item
        first_name = get_waifu_name(group_items[0], user_lang) if group_items else ""
        bucket, normalized = _sort_text_key(category_path)
        return (bucket, normalized, first_name.casefold())

    return sorted(grouped.items(), key=group_key)


def _format_group_lines(
    waifus: list[dict],
    category_paths: dict[int, str],
    user_lang: str,
) -> list[str]:
    grouped = _group_waifus_by_category(waifus, category_paths, user_lang)
    lines: list[str] = []

    for category_path, group_items in grouped:
        total_amount = sum(int(item.get("amount") or 0) for item in group_items)
        lines.append(f"🏰 <b>{html.escape(category_path)}</b> — <b>{total_amount}</b>")

        for waifu in group_items:
            name = html.escape(get_waifu_name(waifu, user_lang))
            amount = int(waifu.get("amount") or 1)
            rarity_markup = format_rarity(waifu.get("rarity") or "common")
            amount_text = f" x{amount}" if amount > 1 else ""
            lines.append(f"  • <i>{name}</i>{amount_text} — {rarity_markup}")

    return lines


# Строим текст для команды "My Waifus"
async def build_mywaifus_text(waifus: list[dict], user_lang: str, page: int, chat_id: int):
    waifus = await filter_allowed_waifus_for_chat(chat_id, waifus)
    category_paths = await _build_waifu_category_path_map(waifus, user_lang)

    waifus.sort(
        key=lambda w: (
            category_paths.get(int(w["category_id"]), "—").casefold()
            if w.get("category_id") is not None
            else "—",
            get_waifu_name(w, user_lang).casefold(),
            int(w.get("id") or 0),
        )
    )

    page_items, current_page, total_pages = paginate(waifus, page, PAGE_SIZE)

    if not page_items:
        text = _lang_text(user_lang, "📦 У тебя пока нет вайфу", "📦 You don't have any waifus yet")
        return text, current_page, total_pages, page_items

    total_waifus = sum(int(w.get("amount") or 1) for w in waifus)
    title = _lang_text(user_lang, "📦 Твоя коллекция", "📦 Your collection")
    lines = [f"{title} — <b>{total_waifus}</b>", ""]
    lines.extend(_format_group_lines(page_items, category_paths, user_lang))
    lines.append(
        _lang_text(
            user_lang,
            f"📄 Страница <b>{current_page}</b> из <b>{total_pages}</b>",
            f"📄 Page <b>{current_page}</b> of <b>{total_pages}</b>",
        )
    )

    return "\n".join(lines), current_page, total_pages, page_items


@router.message(Command("mywaifus"))
async def my_waifus(message: Message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    user_lang = await get_user_language(user_id)
    chat_id = message.chat.id
    waifus = await get_user_waifus(user_id)

    text, page, total_pages, page_items = await build_mywaifus_text(waifus, user_lang, 1, chat_id)
    markup = _build_mywaifus_keyboard(page_items, user_lang, page, total_pages)

    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("mywaifus:") & ~F.data.startswith("mywaifus:search"))
async def mywaifus_page(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    await call.answer()

    page = int(call.data.split(":")[1])

    user_id = call.from_user.id
    user_lang = await get_user_language(user_id)
    chat_id = call.message.chat.id
    waifus = await get_user_waifus(user_id)

    text, current_page, total_pages, page_items = await build_mywaifus_text(waifus, user_lang, page, chat_id)
    markup = _build_mywaifus_keyboard(page_items, user_lang, current_page, total_pages)

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data == "mywaifus:search")
async def mywaifus_search_start(call: CallbackQuery, state: FSMContext):
    if not call.from_user or not call.message:
        return

    await call.answer()
    await state.set_state(MyWaifusSearch.waiting_query)

    user_lang = await get_user_language(call.from_user.id)
    prompt = _lang_text(
        user_lang,
        "🔎 Введи имя вайфу для поиска только среди твоих вайфу.",
        "🔎 Send a waifu name to search only inside your collection.",
    )
    await call.message.answer(prompt)


@router.message(MyWaifusSearch.waiting_query, F.text)
async def mywaifus_search_query(message: Message, state: FSMContext):
    if not message.from_user or not message.text:
        return

    user_id = message.from_user.id
    user_lang = await get_user_language(user_id)
    chat_id = message.chat.id
    query = message.text.strip()

    await state.clear()

    waifus = await get_user_waifus(user_id)
    waifus = await filter_allowed_waifus_for_chat(chat_id, waifus)

    matched = [w for w in waifus if _waifu_matches_owned_query(w, query)]

    if not matched:
        await message.answer(
            _lang_text(
                user_lang,
                f"❌ В твоём гареме не найдено: <i>{html.escape(query)}</i>",
                f"❌ Nothing found in your collection for: <i>{html.escape(query)}</i>",
            ),
            parse_mode="HTML",
        )
        return

    text = await _render_mywaifus_search_results(matched, user_lang, query)
    markup = _build_mywaifus_search_results_keyboard(matched, user_lang)
    await message.answer(text, parse_mode="HTML", reply_markup=markup)
    
@router.callback_query(F.data == "mywaifus:back")
async def mywaifus_back(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    await call.answer()

    user_id = call.from_user.id
    user_lang = await get_user_language(user_id)
    chat_id = call.message.chat.id
    waifus = await get_user_waifus(user_id)

    text, page, total_pages, page_items = await build_mywaifus_text(
        waifus,
        user_lang,
        1,
        chat_id,
    )
    markup = _build_mywaifus_keyboard(page_items, user_lang, page, total_pages)

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=markup)