from __future__ import annotations
import html
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.services.texts import format_rarity
UI_TEXTS = {
    "ru": {
        "profile": "Профиль",
        "collection": "Вайфу в коллекции",
        "favorite": "Любимая вайфу",
        "rarity": "Редкость",
        "gender": "Пол",
        "alias": "Псевдоним",
        "age": "Возраст",
        "categories": "Категории",
        "close": "✖ Закрыть",
    },
    "en": {
        "profile": "Profile",
        "collection": "Waifus in collection",
        "favorite": "Favorite waifu",
        "rarity": "Rarity",
        "gender": "Gender",
        "alias": "Alias",
        "age": "Age",
        "categories": "Categories",
        "close": "✖ Close",
    },
}
GENDER_TEXTS = {
    "ru": {
        "male": "Мужской",
        "female": "Женский",
        "none": "Не указан",
        "unknown": "Не указан",
    },
    "en": {
        "male": "Male",
        "female": "Female",
        "none": "Unknown",
        "unknown": "Unknown",
    },
}
GENDER_ICONS = {
    "male": "♂️",
    "female": "♀️",
    "none": "❔",
    "unknown": "❔",
    None: "❔",
}
RARITY_ICONS = {
    "common": "✨",
    "rare": "💠",
    "epic": "🔥",
    "legendary": "🌟",
    "unique": "👑",
}
def _lang(user_lang: str) -> str:
    return user_lang if user_lang in ("ru", "en") else "en"
def _field_line(label: str, value: str, *, raw_html: bool = False) -> str:
    safe_value = value if raw_html else html.escape(value or "—")
    return f"• <b>{label}:</b> {safe_value}"
def get_waifu_name(waifu: dict, user_lang: str) -> str:
    lang = _lang(user_lang)
    if lang == "ru" and waifu.get("name_ru"):
        return waifu["name_ru"]
    return waifu.get("name_en") or waifu.get("name_ru") or "—"
def get_waifu_alias(waifu: dict, user_lang: str) -> str | None:
    """
    Returns alias in the selected language only.
    Falls back to legacy alias if the language-specific field is empty.
    """
    lang = _lang(user_lang)
    if lang == "ru":
        return waifu.get("alias_ru") or waifu.get("alias") or None
    return waifu.get("alias_en") or waifu.get("alias") or None
def get_category_name(category_row, user_lang: str) -> str:
    lang = _lang(user_lang)
    if lang == "ru" and category_row.get("name_ru"):
        return category_row["name_ru"]
    return category_row.get("name_en") or category_row.get("name_ru") or "—"
def format_category_path(category_rows, user_lang: str) -> str:
    if not category_rows:
        return "—"
    names = [get_category_name(row, user_lang) for row in category_rows]
    return " / ".join(html.escape(name) for name in names if name)
def get_gender_text(gender: str | None, user_lang: str) -> str:
    lang = _lang(user_lang)
    key = (gender or "unknown").strip().lower() if gender else "unknown"
    if key == "null":
        key = "unknown"
    return GENDER_TEXTS[lang].get(key, GENDER_TEXTS[lang]["unknown"])
def get_gender_icon(gender: str | None) -> str:
    key = (gender or "unknown").strip().lower() if gender else "unknown"
    if key == "null":
        key = "unknown"
    return GENDER_ICONS.get(key, "❔")
def get_rarity_icon(rarity: str | None) -> str:
    return RARITY_ICONS.get((rarity or "common").strip().lower(), "✨")
def build_waifu_details_lines(
    waifu: dict,
    user_lang: str,
    category_rows=None,
    *,
    show_name: bool = True,
    include_category: bool = True,
) -> list[str]:
    lang = _lang(user_lang)
    ui = UI_TEXTS[lang]
    lines: list[str] = []
    if show_name:
        name = html.escape(get_waifu_name(waifu, user_lang))
        lines.append(f"🪪 <b>{name}</b>")
    if waifu.get("id") is not None:
        lines.append(f"🆔 <b>ID:</b> <code>{waifu['id']}</code>")
    alias = get_waifu_alias(waifu, user_lang)
    if alias:
        lines.append(_field_line(f"🏷 {ui['alias']}", html.escape(str(alias)), raw_html=True))
    rarity_value = waifu.get("rarity") or "common"
    rarity_icon = get_rarity_icon(rarity_value)
    rarity_text = format_rarity(rarity_value)
    lines.append(_field_line(f"{rarity_icon} {ui['rarity']}", rarity_text, raw_html=True))
    gender = waifu.get("gender")
    gender_icon = get_gender_icon(gender)
    gender_text = get_gender_text(gender, user_lang)
    lines.append(_field_line(f"{gender_icon} {ui['gender']}", html.escape(gender_text), raw_html=True))
    age = waifu.get("age")
    if age not in (None, ""):
        lines.append(_field_line(f"🎂 {ui['age']}", html.escape(str(age)), raw_html=True))
    if include_category:
        category_path = format_category_path(category_rows, user_lang)
        lines.append(_field_line(f"📂 {ui['categories']}", category_path, raw_html=True))
    return lines
def build_card_text(waifu: dict, user_lang: str, category_rows) -> str:
    return "\n".join(build_waifu_details_lines(waifu, user_lang, category_rows, show_name=True, include_category=True))
def build_profile_text(
    user_id: int,
    waifus_count: int,
    favorite_waifu: dict | None,
    user_lang: str,
    category_rows=None,
) -> str:
    lang = _lang(user_lang)
    ui = UI_TEXTS[lang]
    lines = [
        f"👤 <b>{ui['profile']}</b>",
        "",
        f"🆔 <b>ID:</b> <code>{user_id}</code>",
        f"💖 <b>{ui['collection']}:</b> {waifus_count}",
    ]
    if favorite_waifu:
        name = html.escape(get_waifu_name(favorite_waifu, user_lang))
        lines.extend(
            [
                "",
                f"❤️ <b>{ui['favorite']}:</b> <i>{name}</i>",
            ]
        )
    else:
        lines.extend(["", "💫 <i>—</i>"])
    return "\n".join(lines)
def build_list_keyboard(
    source: str,
    page_items: list[dict],
    user_lang: str,
    current_page: int,
    total_pages: int,
    page_prefix: str,
):
    builder = InlineKeyboardBuilder()
    for waifu in page_items:
        name = get_waifu_name(waifu, user_lang)
        builder.button(
            text=f"🎴 {name}",
            callback_data=f"wc:open:{source}:{waifu['id']}",
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
    return builder.as_markup() if page_items else None
def build_close_keyboard(user_lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(
        text=UI_TEXTS[_lang(user_lang)]["close"],
        callback_data="wc:close",
    )
    return builder.as_markup()