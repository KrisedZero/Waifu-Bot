from __future__ import annotations

from aiogram.utils.keyboard import InlineKeyboardBuilder


def _label(lang: str, ru: str, en: str) -> str:
    return en if lang == "en" else ru


def categories_menu_kb(lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    kb.button(text=_label(lang, "🏠 Корневые категории", "🏠 Root categories"), callback_data="admin:categories:root")
    kb.button(text=_label(lang, "🔎 Поиск", "🔎 Search"), callback_data="admin:categories:search")
    kb.button(text=_label(lang, "➕ Добавить категорию", "➕ Add category"), callback_data="admin:category:add")
    kb.button(text=_label(lang, "📃 Полный список", "📃 Full list"), callback_data="admin:categories:list")
    kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data="admin:menu")
    kb.adjust(1)
    return kb.as_markup()


def categories_tree_kb(rows, lang: str = "ru", parent_id: int | None = None, selection_mode: str | None = None):
    """
    selection_mode:
      - None         -> browse mode
      - "add_parent" -> choose parent for add flow
      - "edit_parent" -> choose parent for edit flow
    """
    kb = InlineKeyboardBuilder()

    for row in rows:
        icon = "📁" if row["node_type"] == "branch" else "🎯"
        status = "✅" if row["is_active"] else "⛔"
        name = row["name_en"] if lang == "en" and row["name_en"] else row["name_ru"]
        if selection_mode == "add_parent":
            cb = f"admin:category:addto:{row['id']}"
        elif selection_mode == "edit_parent":
            cb = f"admin:category:setparent:{row['id']}"
        else:
            cb = f"admin:category:open:{row['id']}"
        kb.button(text=f"{icon} {name} · ID:{row['id']} {status}", callback_data=cb)

    if parent_id is None:
        kb.button(text=_label(lang, "➕ Добавить в корень", "➕ Add in root"), callback_data="admin:category:addroot")
        kb.button(text=_label(lang, "🔎 Поиск", "🔎 Search"), callback_data="admin:categories:search")
        kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data="admin:menu")
    else:
        if selection_mode == "add_parent":
            kb.button(text=_label(lang, "📁 Выбрать сюда", "📁 Select this"), callback_data=f"admin:category:addto:{parent_id}")
            kb.button(text=_label(lang, "🏠 Корневые категории", "🏠 Root categories"), callback_data="admin:categories:root")
        elif selection_mode == "edit_parent":
            kb.button(text=_label(lang, "📁 Выбрать сюда", "📁 Select this"), callback_data=f"admin:category:setparent:{parent_id}")
            kb.button(text=_label(lang, "🏠 Корневые категории", "🏠 Root categories"), callback_data="admin:categories:root")
        else:
            kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data=f"admin:category:open:{parent_id}")
            kb.button(text=_label(lang, "🏠 Корневые категории", "🏠 Root categories"), callback_data="admin:categories:root")

    kb.adjust(1)
    return kb.as_markup()


def category_card_kb(category_id: int, parent_id: int | None, lang: str = "ru", children_rows=None):
    kb = InlineKeyboardBuilder()

    kb.button(text=_label(lang, "➕ Добавить сюда", "➕ Add here"), callback_data=f"admin:category:addto:{category_id}")
    kb.button(text=_label(lang, "✏️ Редактировать", "✏️ Edit"), callback_data=f"admin:category:edit:{category_id}")
    kb.button(text=_label(lang, "🗑 Удалить", "🗑 Delete"), callback_data=f"admin:category:delete:{category_id}")

    if children_rows:
        for row in children_rows:
            icon = "📁" if row["node_type"] == "branch" else "🎯"
            status = "✅" if row["is_active"] else "⛔"
            name = row["name_en"] if lang == "en" and row["name_en"] else row["name_ru"]
            kb.button(text=f"{icon} {name} · ID:{row['id']} {status}", callback_data=f"admin:category:open:{row['id']}")

    if parent_id is None:
        kb.button(text=_label(lang, "🏠 Корневые категории", "🏠 Root categories"), callback_data="admin:categories:root")
    else:
        kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data=f"admin:category:open:{parent_id}")

    kb.adjust(1)
    return kb.as_markup()


def category_fields_kb(category_id: int, lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    kb.button(text=_label(lang, "Название RU", "Name RU"), callback_data=f"admin:category:field:{category_id}:name_ru")
    kb.button(text=_label(lang, "Название EN", "Name EN"), callback_data=f"admin:category:field:{category_id}:name_en")
    kb.button(text=_label(lang, "Родитель", "Parent"), callback_data=f"admin:category:field:{category_id}:parent_id")
    kb.button(text=_label(lang, "Тип", "Type"), callback_data=f"admin:category:field:{category_id}:node_type")
    kb.button(text=_label(lang, "Активность", "Active"), callback_data=f"admin:category:field:{category_id}:is_active")
    kb.button(text=_label(lang, "Порядок", "Sort"), callback_data=f"admin:category:field:{category_id}:sort_order")
    kb.button(text=_label(lang, "⬅️ Отмена", "⬅️ Cancel"), callback_data=f"admin:category:open:{category_id}")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def category_node_type_kb(category_id: int, lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    kb.button(text=_label(lang, "📁 Ветвь", "📁 Branch"), callback_data=f"admin:category:node:{category_id}:branch")
    kb.button(text=_label(lang, "🎯 Лист", "🎯 Leaf"), callback_data=f"admin:category:node:{category_id}:leaf")
    kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data=f"admin:category:edit:{category_id}")
    kb.adjust(2, 1)
    return kb.as_markup()


def category_bool_kb(category_id: int, field: str, lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    kb.button(text=_label(lang, "✅ Да", "✅ Yes"), callback_data=f"admin:category:bool:{category_id}:{field}:1")
    kb.button(text=_label(lang, "❌ Нет", "❌ No"), callback_data=f"admin:category:bool:{category_id}:{field}:0")
    kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data=f"admin:category:edit:{category_id}")
    kb.adjust(2, 1)
    return kb.as_markup()


def category_confirm_kb(confirm_cb: str, cancel_cb: str, lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    kb.button(text=_label(lang, "✅ Подтвердить", "✅ Confirm"), callback_data=confirm_cb)
    kb.button(text=_label(lang, "❌ Отмена", "❌ Cancel"), callback_data=cancel_cb)
    kb.adjust(2)
    return kb.as_markup()


def category_search_kb(lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    kb.button(text=_label(lang, "🏠 Корневые категории", "🏠 Root categories"), callback_data="admin:categories:root")
    kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data="admin:menu")
    kb.adjust(1)
    return kb.as_markup()



def category_create_type_kb(lang: str = "ru", back_cb: str = "admin:categories:root"):
    kb = InlineKeyboardBuilder()
    kb.button(text=_label(lang, "📁 Ветвь", "📁 Branch"), callback_data="admin:category:create:type:branch")
    kb.button(text=_label(lang, "🎯 Лист", "🎯 Leaf"), callback_data="admin:category:create:type:leaf")
    kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data=back_cb)
    kb.adjust(2, 1)
    return kb.as_markup()


def category_create_place_kb(lang: str = "ru", back_cb: str = "admin:categories:root"):
    kb = InlineKeyboardBuilder()
    kb.button(text=_label(lang, "🏠 В корень", "🏠 To root"), callback_data="admin:category:create:place:root")
    kb.button(text=_label(lang, "🗂 Выбрать родителя", "🗂 Choose parent"), callback_data="admin:category:create:place:choose")
    kb.button(text=_label(lang, "⬅️ Назад", "⬅️ Back"), callback_data=back_cb)
    kb.adjust(1)
    return kb.as_markup()
