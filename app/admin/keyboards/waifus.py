from __future__ import annotations

from aiogram.utils.keyboard import InlineKeyboardBuilder


def _label(lang: str, ru: str, en: str) -> str:
    return en if lang == "en" else ru


def waifus_menu_kb(lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    kb.button(text=_label(lang, "➕ Добавить вайфу", "➕ Add waifu"), callback_data="admin:waifu:add")
    kb.button(text=_label(lang, "🔎 Поиск", "🔎 Search"), callback_data="admin:waifu:search")
    kb.button(text=_label(lang, "📃 Полный список", "📃 Full list"), callback_data="admin:waifu:list:0")
    kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data="admin:menu")
    kb.adjust(1)
    return kb.as_markup()


def waifus_list_nav_kb(page: int, has_prev: bool, has_next: bool, lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    if has_prev:
        kb.button(text="⬅️", callback_data=f"admin:waifu:list:{page - 1}")
    if has_next:
        kb.button(text="➡️", callback_data=f"admin:waifu:list:{page + 1}")
    kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data="admin:waifus")
    kb.adjust(2, 1)
    return kb.as_markup()


def waifus_list_kb(rows, page: int, has_prev: bool, has_next: bool, lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    for row in rows:
        name = row["name_en"] if lang == "en" and row["name_en"] else row["name_ru"]
        cat = row["category_name_en"] if lang == "en" and row["category_name_en"] else row["category_name_ru"]
        icon = "🧩" if row["is_active"] else "⛔"
        kb.button(
            text=f"{icon} {name} · ID:{row['id']} · {cat or '-'}",
            callback_data=f"admin:waifu:open:{row['id']}",
        )
    if has_prev:
        kb.button(text="⬅️", callback_data=f"admin:waifu:list:{page - 1}")
    if has_next:
        kb.button(text="➡️", callback_data=f"admin:waifu:list:{page + 1}")
    kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data="admin:waifus")
    kb.adjust(3)
    return kb.as_markup()


def waifu_card_kb(waifu_id: int, category_id: int | None, lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    if category_id:
        kb.button(text=_label(lang, "📁 Категория", "📁 Category"), callback_data=f"admin:category:open:{category_id}")
    kb.button(text=_label(lang, "✏️ Редактировать", "✏️ Edit"), callback_data=f"admin:waifu:edit:{waifu_id}")
    kb.button(text=_label(lang, "🖼 Медиа", "🖼 Media"), callback_data=f"admin:waifu:media:{waifu_id}")
    kb.button(text=_label(lang, "🗑 Удалить", "🗑 Delete"), callback_data=f"admin:waifu:delete:{waifu_id}")
    kb.button(text=_label(lang, "⬅️ Назад к вайфу", "⬅️ Back to waifus"), callback_data="admin:waifus")
    kb.adjust(1)
    return kb.as_markup()


def waifu_edit_fields_kb(waifu_id: int, lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    kb.button(text=_label(lang, "Категория", "Category"), callback_data=f"admin:waifu:field:{waifu_id}:category_id")
    kb.button(text=_label(lang, "Имя RU", "Name RU"), callback_data=f"admin:waifu:field:{waifu_id}:name_ru")
    kb.button(text=_label(lang, "Имя EN", "Name EN"), callback_data=f"admin:waifu:field:{waifu_id}:name_en")
    kb.button(text=_label(lang, "Псевдоним RU", "Alias RU"), callback_data=f"admin:waifu:field:{waifu_id}:alias_ru")
    kb.button(text=_label(lang, "Псевдоним EN", "Alias EN"), callback_data=f"admin:waifu:field:{waifu_id}:alias_en")
    kb.button(text=_label(lang, "Возраст", "Age"), callback_data=f"admin:waifu:field:{waifu_id}:age")
    kb.button(text=_label(lang, "Редкость", "Rarity"), callback_data=f"admin:waifu:field:{waifu_id}:rarity")
    kb.button(text=_label(lang, "Пол", "Gender"), callback_data=f"admin:waifu:field:{waifu_id}:gender")
    kb.button(text=_label(lang, "Активность", "Active"), callback_data=f"admin:waifu:field:{waifu_id}:is_active")
    kb.button(text=_label(lang, "Медиа", "Media"), callback_data=f"admin:waifu:field:{waifu_id}:media")
    kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data=f"admin:waifu:open:{waifu_id}")
    kb.adjust(2, 2, 2, 2, 2, 1)
    return kb.as_markup()


def waifu_bool_kb(waifu_id: int, field: str, lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    kb.button(text=_label(lang, "✅ Да", "✅ Yes"), callback_data=f"admin:waifu:bool:{waifu_id}:{field}:1")
    kb.button(text=_label(lang, "❌ Нет", "❌ No"), callback_data=f"admin:waifu:bool:{waifu_id}:{field}:0")
    kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data=f"admin:waifu:field:{waifu_id}:{field}")
    kb.adjust(2, 1)
    return kb.as_markup()


def waifu_media_type_kb(waifu_id: int, lang: str = "ru", mode: str = "add"):
    kb = InlineKeyboardBuilder()
    prefix = "admin:waifu:mediatype"
    kb.button(text=_label(lang, "Фото", "Photo"), callback_data=f"{prefix}:{mode}:{waifu_id}:photo")
    kb.button(text=_label(lang, "Видео", "Video"), callback_data=f"{prefix}:{mode}:{waifu_id}:video")
    kb.button(text=_label(lang, "Анимация", "Animation"), callback_data=f"{prefix}:{mode}:{waifu_id}:animation")
    kb.button(text="GIF", callback_data=f"{prefix}:{mode}:{waifu_id}:gif")
    kb.button(text=_label(lang, "Файл", "Document"), callback_data=f"{prefix}:{mode}:{waifu_id}:document")
    kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data=f"admin:waifu:open:{waifu_id}" if mode == "edit" else "admin:waifus")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def waifu_search_results_kb(rows, lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    for row in rows:
        name = row["name_en"] if lang == "en" and row["name_en"] else row["name_ru"]
        cat = row["category_name_en"] if lang == "en" and row["category_name_en"] else row["category_name_ru"]
        icon = "🧩" if row["is_active"] else "⛔"
        kb.button(
            text=f"{icon} {name} · ID:{row['id']} · {cat or '-'}",
            callback_data=f"admin:waifu:open:{row['id']}",
        )
    kb.adjust(1)
    return kb.as_markup()


def waifu_category_picker_kb(rows, lang: str = "ru", mode: str = "add", waifu_id: int = 0, parent_id: int | None = None):
    kb = InlineKeyboardBuilder()

    for row in rows:
        icon = "📁" if row["node_type"] == "branch" else "🎯"
        status = "✅" if row["is_active"] else "⛔"
        name = row["name_en"] if lang == "en" and row["name_en"] else row["name_ru"]
        if row["node_type"] == "branch":
            cb = f"admin:waifu:catopen:{mode}:{waifu_id}:{row['id']}"
        else:
            cb = f"admin:waifu:catpick:{mode}:{waifu_id}:{row['id']}"
        kb.button(text=f"{icon} {name} · ID:{row['id']} {status}", callback_data=cb)

    kb.button(text=_label(lang, "🔎 Поиск", "🔎 Search"), callback_data=f"admin:waifu:catsearch:{mode}:{waifu_id}")
    if parent_id is None:
        kb.button(text=_label(lang, "🏠 Корневые категории", "🏠 Root categories"), callback_data=f"admin:waifu:catroot:{mode}:{waifu_id}")
        kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data="admin:waifus")
    else:
        kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data=f"admin:waifu:catopen:{mode}:{waifu_id}:{parent_id}")
        kb.button(text=_label(lang, "🏠 Корневые категории", "🏠 Root categories"), callback_data=f"admin:waifu:catroot:{mode}:{waifu_id}")

    kb.adjust(1)
    return kb.as_markup()


def waifu_rarity_kb(waifu_id: int, lang: str = "ru", mode: str = "add"):
    kb = InlineKeyboardBuilder()
    prefix = "admin:waifu:rarity"
    kb.button(text=_label(lang, "Обычная", "Common"), callback_data=f"{prefix}:{mode}:{waifu_id}:common")
    kb.button(text=_label(lang, "Редкая", "Rare"), callback_data=f"{prefix}:{mode}:{waifu_id}:rare")
    kb.button(text=_label(lang, "Эпическая", "Epic"), callback_data=f"{prefix}:{mode}:{waifu_id}:epic")
    kb.button(text=_label(lang, "Легендарная", "Legendary"), callback_data=f"{prefix}:{mode}:{waifu_id}:legendary")
    kb.button(text=_label(lang, "Уникальная", "Unique"), callback_data=f"{prefix}:{mode}:{waifu_id}:unique")
    kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data="admin:waifus")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def waifu_gender_kb(waifu_id: int, lang: str = "ru", mode: str = "add"):
    kb = InlineKeyboardBuilder()
    prefix = "admin:waifu:gender"
    kb.button(text=_label(lang, "Мужской", "Male"), callback_data=f"{prefix}:{mode}:{waifu_id}:male")
    kb.button(text=_label(lang, "Женский", "Female"), callback_data=f"{prefix}:{mode}:{waifu_id}:female")
    kb.button(text=_label(lang, "Не указан", "Unknown"), callback_data=f"{prefix}:{mode}:{waifu_id}:none")
    kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data="admin:waifus")
    kb.adjust(2, 1)
    return kb.as_markup()
