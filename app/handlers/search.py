from __future__ import annotations

import html
from collections import OrderedDict

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.user_service import get_user_language
from app.services.pagination import paginate
from app.services.search_state import (
    set_search_state,
    get_search_state,
    update_search_pages,
)
from app.services.waifu_service import search_waifus, get_all_waifus
from app.services.category_service import (
    search_categories,
    get_category_path,
    get_category_descendant_ids,
)
from app.services.chat_category_service import (
    filter_allowed_waifus_for_chat,
    is_category_allowed_for_chat,
)
from app.services.waifu_ui import get_waifu_name, format_category_path
from app.services.texts import format_rarity

router = Router()

CATEGORY_PAGE_SIZE = 8
WAIFU_PAGE_SIZE = 8
CATEGORY_OPEN_PAGE_SIZE = 10


def _lang_text(lang: str, ru: str, en: str) -> str:
    return ru if lang == "ru" else en


def _category_display_name(category: dict, user_lang: str) -> str:
    if user_lang == "ru":
        return category.get("name_ru") or category.get("name_en") or "—"
    return category.get("name_en") or category.get("name_ru") or "—"


async def _build_category_path_map(items: list[dict], user_lang: str) -> dict[int, str]:
    path_map: dict[int, str] = {}
    for item in items:
        category_id = item.get("id")
        if category_id is None:
            continue
        rows = await get_category_path(int(category_id))
        path_map[int(category_id)] = format_category_path(rows, user_lang)
    return path_map


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

    def group_key(item: tuple[str, list[dict]]) -> tuple[str, str]:
        category_path, group_items = item
        first_name = get_waifu_name(group_items[0], user_lang) if group_items else ""
        return (category_path.casefold(), first_name.casefold())

    return sorted(grouped.items(), key=group_key)


def _build_category_keyboard(
    page_items: list[dict],
    user_lang: str,
    current_page: int,
    total_pages: int,
) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for category in page_items:
        builder.button(
            text=f"🏰{_category_display_name(category, user_lang)}",
            callback_data=f"searchcat:{category['id']}",
        )
    if page_items:
        builder.adjust(2)

    pager = InlineKeyboardBuilder()
    if current_page > 1:
        pager.button(text="⬅️", callback_data=f"searchcats:{current_page - 1}")
    if current_page < total_pages:
        pager.button(text="➡️", callback_data=f"searchcats:{current_page + 1}")
    if current_page > 1 or current_page < total_pages:
        pager.adjust(2)
        builder.attach(pager)
    return builder


def _build_waifu_keyboard(
    page_items: list[dict],
    user_lang: str,
    current_page: int,
    total_pages: int,
    page_prefix: str,
) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for waifu in page_items:
        name = get_waifu_name(waifu, user_lang)
        builder.button(
            text=f"🎴 {name}",
            callback_data=f"wc:open:search:{waifu['id']}",
        )
    if page_items:
        builder.adjust(2)

    pager = InlineKeyboardBuilder()
    if current_page > 1:
        pager.button(text="⬅️", callback_data=f"{page_prefix}:{current_page - 1}")
    if current_page < total_pages:
        pager.button(text="➡️", callback_data=f"{page_prefix}:{current_page + 1}")
    if current_page > 1 or current_page < total_pages:
        pager.adjust(2)
        builder.attach(pager)
    return builder


def _build_category_open_keyboard(
    page_items: list[dict],
    user_lang: str,
    current_page: int,
    total_pages: int,
    category_id: int,
) -> InlineKeyboardBuilder:
    return _build_waifu_keyboard(
        page_items,
        user_lang,
        current_page,
        total_pages,
        f"searchcatpage:{category_id}",
    )


def _format_category_lines(categories: list[dict], category_paths: dict[int, str], user_lang: str) -> list[str]:
    lines: list[str] = []
    for category in categories:
        category_id = int(category["id"])
        path = category_paths.get(category_id, _category_display_name(category, user_lang))
        lines.append(f"🏰<b>{html.escape(path)}</b>")
    return lines


def _format_waifu_group_lines(
    waifus: list[dict],
    category_paths: dict[int, str],
    user_lang: str,
) -> list[str]:
    grouped = _group_waifus_by_category(waifus, category_paths, user_lang)
    lines: list[str] = []
    for category_path, group_items in grouped:
        lines.append(f"🏰<b>{html.escape(category_path)}</b>")
        for waifu in group_items:
            name = html.escape(get_waifu_name(waifu, user_lang))
            rarity_markup = format_rarity(waifu.get("rarity") or "common")
            lines.append(f"  • <i>{name}</i> — {rarity_markup}")
    return lines


async def _render_search_view(
    chat_id: int,
    user_id: int,
    user_lang: str,
    query: str,
    category_page: int,
    waifu_page: int,
):
    categories = await search_categories(query, lang=user_lang)
    allowed_categories: list[dict] = []
    for category in categories:
        if await is_category_allowed_for_chat(chat_id, int(category["id"])):
            allowed_categories.append(category)

    category_paths = await _build_category_path_map(allowed_categories, user_lang)
    allowed_categories.sort(
        key=lambda cat: (
            category_paths.get(int(cat["id"]), _category_display_name(cat, user_lang)).casefold(),
            int(cat["id"]),
        )
    )
    category_page_items, category_page, category_total = paginate(allowed_categories, category_page, CATEGORY_PAGE_SIZE)

    waifus = await search_waifus(query)
    waifus = await filter_allowed_waifus_for_chat(chat_id, waifus)
    waifu_paths = await _build_waifu_category_path_map(waifus, user_lang)
    waifus.sort(
        key=lambda w: (
            waifu_paths.get(int(w["category_id"]), "—").casefold() if w.get("category_id") is not None else "—",
            get_waifu_name(w, user_lang).casefold(),
            int(w.get("id") or 0),
        )
    )
    waifu_page_items, waifu_page, waifu_total = paginate(waifus, waifu_page, WAIFU_PAGE_SIZE)

    show_categories = waifu_page == 1

    lines: list[str] = []
    title = _lang_text(user_lang, "🔎 <b>Результаты поиска</b>", "🔎 <b>Search results</b>")
    lines.append(f"{title}: <i>{html.escape(query)}</i>")
    lines.append("")

    if show_categories:
        cat_header = _lang_text(
            user_lang,
            f"🏰<b>Категории</b> — найдено <b>{len(allowed_categories)}</b>",
            f"🏰<b>Categories</b> — found <b>{len(allowed_categories)}</b>",
        )
        lines.append(cat_header)
        if category_page_items:
            lines.extend(_format_category_lines(category_page_items, category_paths, user_lang))
        else:
            lines.append(_lang_text(user_lang, "• Ничего не найдено", "• Nothing found"))
        lines.append(
            _lang_text(
                user_lang,
                f"📄 Страница <b>{category_page}</b> из <b>{category_total}</b>",
                f"📄 Page <b>{category_page}</b> of <b>{category_total}</b>",
            )
        )
        lines.append("")

    waifu_header = _lang_text(
        user_lang,
        f"🎴 <b>Вайфу</b> — найдено <b>{len(waifus)}</b>",
        f"🎴 <b>Waifus</b> — found <b>{len(waifus)}</b>",
    )
    lines.append(waifu_header)
    if waifu_page_items:
        lines.extend(_format_waifu_group_lines(waifu_page_items, waifu_paths, user_lang))
    else:
        lines.append(_lang_text(user_lang, "• Ничего не найдено", "• Nothing found"))
    lines.append(
        _lang_text(
            user_lang,
            f"📄 Страница <b>{waifu_page}</b> из <b>{waifu_total}</b>",
            f"📄 Page <b>{waifu_page}</b> of <b>{waifu_total}</b>",
        )
    )

    keyboard = InlineKeyboardBuilder()
    if show_categories and category_page_items:
        keyboard.attach(_build_category_keyboard(category_page_items, user_lang, category_page, category_total))
    if waifu_page_items:
        keyboard.attach(_build_waifu_keyboard(waifu_page_items, user_lang, waifu_page, waifu_total, "searchwaifus"))

    return "\n".join(lines), keyboard.as_markup() if (waifu_page_items or (show_categories and category_page_items)) else None, category_page, waifu_page

async def _render_category_open_view(chat_id: int, user_lang: str, category_id: int, page: int):
    category_rows = await get_category_path(category_id)
    category_path = format_category_path(category_rows, user_lang)
    descendant_ids = set(await get_category_descendant_ids(category_id))

    waifus = await get_all_waifus()
    waifus = [w for w in waifus if w.get("category_id") in descendant_ids]
    waifus = await filter_allowed_waifus_for_chat(chat_id, waifus)

    waifu_paths = await _build_waifu_category_path_map(waifus, user_lang)
    waifus.sort(
        key=lambda w: (
            waifu_paths.get(int(w["category_id"]), "—").casefold() if w.get("category_id") is not None else "—",
            get_waifu_name(w, user_lang).casefold(),
            int(w.get("id") or 0),
        )
    )
    page_items, current_page, total_pages = paginate(waifus, page, CATEGORY_OPEN_PAGE_SIZE)

    lines: list[str] = []
    title = _lang_text(user_lang, "🏰<b>Категория</b>", "🏰<b>Category</b>")
    lines.append(f"{title}: <i>{html.escape(category_path)}</i>")
    lines.append("")
    lines.append(
        _lang_text(
            user_lang,
            f"🎴 <b>Вайфу</b> — найдено <b>{len(waifus)}</b>",
            f"🎴 <b>Waifus</b> — found <b>{len(waifus)}</b>",
        )
    )

    if page_items:
        lines.extend(_format_waifu_group_lines(page_items, waifu_paths, user_lang))
    else:
        lines.append(_lang_text(user_lang, "• Ничего не найдено", "• Nothing found"))

    lines.append(
        _lang_text(
            user_lang,
            f"📄 Страница <b>{current_page}</b> из <b>{total_pages}</b>",
            f"📄 Page <b>{current_page}</b> of <b>{total_pages}</b>",
        )
    )

    keyboard = _build_category_open_keyboard(page_items, user_lang, current_page, total_pages, category_id)
    return "\n".join(lines), keyboard.as_markup() if page_items else None


@router.message(Command("searchwaifu"))
async def search_waifu(message: Message):
    if not message.from_user or not message.text:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    user_lang = await get_user_language(user_id)

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        if user_lang == "ru":
            await message.answer("🔍 Использование: /searchwaifu рем")
        else:
            await message.answer("🔍 Usage: /searchwaifu rem")
        return

    query = parts[1].strip()
    set_search_state(chat_id, user_id, query, category_page=1, waifu_page=1)

    text, markup, _, _ = await _render_search_view(chat_id, user_id, user_lang, query, 1, 1)
    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("searchcats:"))
async def search_categories_page(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    await call.answer()

    page = int(call.data.split(":")[1])
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    user_lang = await get_user_language(user_id)

    state = get_search_state(chat_id, user_id)
    if not state or not state.get("query"):
        if user_lang == "ru":
            await call.message.edit_text("🔍 Поиск устарел. Введите команду заново.")
        else:
            await call.message.edit_text("🔍 Search expired. Please run the command again.")
        return

    update_search_pages(chat_id, user_id, category_page=page, waifu_page=1)
    state = get_search_state(chat_id, user_id)
    text, markup, category_page, waifu_page = await _render_search_view(
        chat_id,
        user_id,
        user_lang,
        state["query"],
        state.get("category_page", page),
        1,
    )
    update_search_pages(chat_id, user_id, category_page=category_page, waifu_page=waifu_page)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("searchwaifus:"))
async def search_waifus_page(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    await call.answer()

    page = int(call.data.split(":")[1])
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    user_lang = await get_user_language(user_id)

    state = get_search_state(chat_id, user_id)
    if not state or not state.get("query"):
        if user_lang == "ru":
            await call.message.edit_text("🔍 Поиск устарел. Введите команду заново.")
        else:
            await call.message.edit_text("🔍 Search expired. Please run the command again.")
        return

    update_search_pages(chat_id, user_id, waifu_page=page)
    state = get_search_state(chat_id, user_id)
    text, markup, category_page, waifu_page = await _render_search_view(
        chat_id,
        user_id,
        user_lang,
        state["query"],
        state.get("category_page", 1),
        state.get("waifu_page", page),
    )
    update_search_pages(chat_id, user_id, category_page=category_page, waifu_page=waifu_page)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("searchcat:"))
async def open_search_category(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    await call.answer()

    user_lang = await get_user_language(call.from_user.id)
    chat_id = call.message.chat.id
    category_id = int(call.data.split(":")[1])

    text, markup = await _render_category_open_view(chat_id, user_lang, category_id, 1)
    await call.message.answer(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("searchcatpage:"))
async def search_category_open_page(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    await call.answer()

    parts = call.data.split(":")
    if len(parts) < 3:
        return

    category_id = int(parts[1])
    page = int(parts[2])
    user_lang = await get_user_language(call.from_user.id)
    chat_id = call.message.chat.id

    text, markup = await _render_category_open_view(chat_id, user_lang, category_id, page)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
