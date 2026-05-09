import html
from collections import OrderedDict

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.user_service import get_user_language
from app.services.waifu_service import get_all_waifus
from app.services.pagination import paginate
from app.services.chat_category_service import filter_allowed_waifus_for_chat
from app.services.category_service import get_category_path
from app.services.waifu_ui import format_category_path, get_waifu_name as ui_get_waifu_name

router = Router()

PAGE_SIZE = 10


def get_waifu_name(w: dict, user_lang: str) -> str:
    if user_lang == "ru" and w.get("name_ru"):
        return w["name_ru"]
    return w.get("name_en") or w.get("name_ru") or "—"


def _display_count(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _category_sort_key(path: str) -> tuple[int, str]:
    text = (path or "—").strip()
    if not text:
        return (0, "")

    first_significant = next((ch for ch in text if not ch.isspace()), text[0])
    bucket = 1 if first_significant.isalpha() else 0
    return (bucket, text.casefold())


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

    def group_key(item: tuple[str, list[dict]]) -> tuple[int, str, int]:
        category_path, group_items = item
        first_name = get_waifu_name(group_items[0], user_lang) if group_items else ""
        return (*_category_sort_key(category_path), first_name.casefold())

    return sorted(grouped.items(), key=group_key)


async def build_allwaifus_text(waifus: list[dict], user_lang: str, page: int, chat_id: int):
    waifus = await filter_allowed_waifus_for_chat(chat_id, waifus)

    category_paths = await _build_waifu_category_path_map(waifus, user_lang)
    waifus.sort(
        key=lambda w: (
            _category_sort_key(category_paths.get(int(w["category_id"]), "—") if w.get("category_id") is not None else "—"),
            get_waifu_name(w, user_lang).casefold(),
            int(w.get("id") or 0),
        )
    )

    page_items, current_page, total_pages = paginate(waifus, page, PAGE_SIZE)

    if not page_items:
        text = "📚 В базе пока нет вайфу" if user_lang == "ru" else "📚 There are no waifus in the database yet"
        return text, current_page, total_pages, page_items

    total_waifus = _display_count(len(waifus))
    title = "📚 Все вайфу" if user_lang == "ru" else "📚 All waifus"
    lines = [f"{title} — <b>{total_waifus}</b>", ""]

    grouped_page_items = _group_waifus_by_category(page_items, category_paths, user_lang)
    total_by_category: dict[str, int] = {}
    for waifu in waifus:
        category_id = waifu.get("category_id")
        category_path = category_paths.get(int(category_id)) if category_id is not None else "—"
        total_by_category[category_path or "—"] = total_by_category.get(category_path or "—", 0) + 1

    for category_path, items in grouped_page_items:
        safe_category = html.escape(category_path or "—")
        category_total = _display_count(total_by_category.get(category_path or "—", len(items)))
        lines.append(f"🏰 <b>{safe_category}</b> — <b>{category_total}</b>")
        for w in items:
            name = get_waifu_name(w, user_lang)
            safe_name = html.escape(name)
            rarity = html.escape(w["rarity"])
            lines.append(f"•  {safe_name} — {rarity}")
        lines.append("")

    page_text = (
        f"📄 Страница {current_page}/{total_pages}"
        if user_lang == "ru"
        else f"📄 Page {current_page}/{total_pages}"
    )
    lines.append(page_text)

    return "\n".join(lines).strip(), current_page, total_pages, page_items


async def build_allwaifus_keyboard(page_items: list[dict], user_lang: str, current_page: int, total_pages: int):
    builder = InlineKeyboardBuilder()

    for w in page_items:
        name = get_waifu_name(w, user_lang)
        builder.button(
            text=f"🎴 {name}",
            callback_data=f"wc:open:allwaifus:{w['id']}",
        )

    if page_items:
        builder.adjust(2)

    pager = InlineKeyboardBuilder()
    if current_page > 1:
        pager.button(text="⬅️", callback_data=f"allwaifus:{current_page - 1}")
    if current_page < total_pages:
        pager.button(text="➡️", callback_data=f"allwaifus:{current_page + 1}")

    if current_page > 1 or current_page < total_pages:
        pager.adjust(2)
        builder.attach(pager)

    return builder.as_markup() if page_items else None


@router.message(Command("allwaifus"))
async def all_waifus(message: Message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    user_lang = await get_user_language(user_id)
    chat_id = message.chat.id  # Получаем chat_id для фильтрации по категориям
    waifus = await get_all_waifus()

    text, page, total_pages, page_items = await build_allwaifus_text(waifus, user_lang, 1, chat_id)
    markup = await build_allwaifus_keyboard(page_items, user_lang, page, total_pages)

    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("allwaifus:"))
async def allwaifus_page(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    await call.answer()

    page = int(call.data.split(":")[1])

    user_id = call.from_user.id
    user_lang = await get_user_language(user_id)
    chat_id = call.message.chat.id  # Получаем chat_id для фильтрации по категориям
    waifus = await get_all_waifus()

    text, current_page, total_pages, page_items = await build_allwaifus_text(waifus, user_lang, page, chat_id)
    markup = await build_allwaifus_keyboard(page_items, user_lang, current_page, total_pages)

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
