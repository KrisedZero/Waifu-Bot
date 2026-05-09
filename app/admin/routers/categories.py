from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.admin.keyboards.categories import (
    categories_menu_kb,
    categories_tree_kb,
    category_card_kb,
    category_confirm_kb,
    category_fields_kb,
    category_node_type_kb,
    category_create_type_kb,
    category_create_place_kb,
    category_bool_kb,
    category_search_kb,
)
from app.admin.services.admin_audit_service import write_audit_log
from app.admin.utils.telegram import safe_replace_text
from app.admin.services.admin_cache_service import invalidate_category_catalog, invalidate_waifu_catalog
from app.admin.services.admin_category_service import (
    count_categories,
    create_category,
    delete_category_tree,
    get_category,
    get_children_count,
    get_descendant_stats,
    get_root_categories,
    get_child_categories,
    search_categories,
    update_category,
)

router = Router()


class CategoryFlow(StatesGroup):
    waiting_search_query = State()
    waiting_create_node_type = State()
    waiting_create_parent_choice = State()
    waiting_name_ru = State()
    waiting_name_en = State()
    waiting_sort_order = State()
    waiting_confirm_create = State()
    waiting_edit_value = State()
    waiting_edit_parent_pick = State()
    waiting_delete_confirm = State()


def _lang(user) -> str:
    return "ru"


def _cat_name(row, lang: str) -> str:
    if lang == "en":
        return (row["name_en"] or row["name_ru"] or "—").strip()
    return (row["name_ru"] or row["name_en"] or "—").strip()


def _type_label(node_type: str | None, lang: str) -> str:
    node_type = (node_type or "branch").lower()
    if lang == "en":
        return "📁 Subcategories" if node_type == "branch" else "🎯 Waifus"
    return "📁 Подкатегории" if node_type == "branch" else "🎯 Вайфу"


def _status_label(is_active: bool, lang: str) -> str:
    return ("Active" if is_active else "Inactive") if lang == "en" else ("Активна" if is_active else "Неактивна")


async def _safe_edit(message: Message, text: str, *, reply_markup=None, parse_mode: str | None = "HTML") -> None:
    await safe_replace_text(message, text, reply_markup=reply_markup, parse_mode=parse_mode)


async def _collect_category_tree(pool, lang: str, parent_id: int | None = None, depth: int = 0):
    rows = await (get_root_categories(pool, lang=lang) if parent_id is None else get_child_categories(pool, parent_id, lang=lang))
    items = []
    for row in rows:
        items.append((row, depth))
        items.extend(await _collect_category_tree(pool, lang, int(row["id"]), depth + 1))
    return items


def _tree_lines(items, lang: str) -> list[str]:
    lines: list[str] = []
    for row, depth in items:
        icon = "📁" if row["node_type"] == "branch" else "🎯"
        status = "✅" if row["is_active"] else "⛔"
        name = _cat_name(row, lang)
        indent = "  " * depth
        lines.append(f"{indent}{icon} <code>{row['id']}</code> — {escape(name)} <i>({escape(row['node_type'])}, {status}, sort={row['sort_order']})</i>")
    return lines


def _category_text(row, lang: str, children_count: int) -> str:
    name = escape(_cat_name(row, lang))
    node = _type_label(row["node_type"], lang)
    status = _status_label(bool(row["is_active"]), lang)
    parent = row["parent_id"] if row["parent_id"] is not None else ("root" if lang == "en" else "корень")
    if lang == "en":
        return (
            f"📂 <b>{name}</b>\n"
            f"ID: <code>{row['id']}</code>\n"
            f"Parent: <code>{parent}</code>\n"
            f"{node}\n"
            f"{status}\n"
            f"Sort: <code>{row['sort_order']}</code>\n"
            f"Children: <code>{children_count}</code>"
        )
    return (
        f"📂 <b>{name}</b>\n"
        f"ID: <code>{row['id']}</code>\n"
        f"Родитель: <code>{parent}</code>\n"
        f"{node}\n"
        f"{status}\n"
        f"Порядок: <code>{row['sort_order']}</code>\n"
        f"Дочерних: <code>{children_count}</code>"
    )


@router.callback_query(F.data == "admin:categories")
async def categories_menu(call: CallbackQuery, pool):
    if not call.from_user or not call.message:
        return

    lang = _lang(call.from_user)
    rows = await get_root_categories(pool, lang=lang)
    text = "📁 <b>Категории</b>\n\nВыбери раздел:" if lang == "ru" else "📁 <b>Categories</b>\n\nChoose a section:"
    await _safe_edit(call.message, text, reply_markup=categories_tree_kb(rows, lang=lang, parent_id=None))
    await call.answer()


@router.callback_query(F.data == "admin:categories:root")
async def categories_root(call: CallbackQuery, pool):
    await categories_menu(call, pool)


@router.callback_query(F.data == "admin:categories:list")
async def categories_full_list(call: CallbackQuery, pool):
    if not call.from_user or not call.message:
        return

    lang = _lang(call.from_user)
    total = await count_categories(pool)
    items = await _collect_category_tree(pool, lang)

    if not items:
        text = "Категорий пока нет." if lang == "ru" else "No categories yet."
        await _safe_edit(call.message, text, reply_markup=categories_menu_kb(lang), parse_mode=None)
        await call.answer()
        return

    title = f"<b>{'Категории' if lang == 'ru' else 'Categories'}</b>\n\n"
    body = "\n".join(_tree_lines(items, lang))
    footer = f"\n\nTotal: <code>{total}</code>"
    root_rows = await get_root_categories(pool, lang=lang)
    await _safe_edit(call.message, title + body + footer, reply_markup=categories_tree_kb(root_rows, lang=lang, parent_id=None))
    await call.answer()


    await _safe_edit(call.message, title + body + footer, reply_markup=categories_tree_kb(root_rows, lang=lang, parent_id=None))
    await call.answer()


@router.callback_query(F.data.startswith("admin:category:open:"))
async def category_open(call: CallbackQuery, pool):
    if not call.from_user or not call.message:
        return

    lang = _lang(call.from_user)
    category_id = int(call.data.split(":")[-1])
    category = await get_category(pool, category_id)

    if not category:
        await call.answer("Категория не найдена." if lang == "ru" else "Category not found.", show_alert=True)
        return

    rows = await get_child_categories(pool, category_id, lang=lang)
    children_count = len(rows)
    text = _category_text(category, lang, children_count)
    if children_count:
        text += "\n\n" + ("Подкатегории:" if lang == "ru" else "Subcategories:")
        for row in rows:
            icon = "📁" if row["node_type"] == "branch" else "🎯"
            status = "✅" if row["is_active"] else "⛔"
            text += f"\n• {icon} <code>{row['id']}</code> — {escape(_cat_name(row, lang))} ({status})"
    else:
        text += "\n\n" + ("Здесь пока нет подкатегорий." if lang == "ru" else "There are no subcategories yet.")

    await _safe_edit(
        call.message,
        text,
        reply_markup=category_card_kb(category_id, category["parent_id"], lang, children_rows=rows),
    )
    await call.answer()


@router.callback_query(F.data == "admin:categories:search")
async def category_search_prompt(call: CallbackQuery, state: FSMContext):
    if not call.from_user or not call.message:
        return

    lang = _lang(call.from_user)
    await state.set_state(CategoryFlow.waiting_search_query)
    text = "Введите часть названия категории:" if lang == "ru" else "Enter part of the category name:"
    await _safe_edit(call.message, text, reply_markup=category_search_kb(lang), parse_mode=None)
    await call.answer()


@router.message(StateFilter(CategoryFlow.waiting_search_query), F.text)
async def category_search(message: Message, state: FSMContext, pool):
    if not message.from_user:
        return

    lang = _lang(message.from_user)
    query = (message.text or "").strip()
    if not query:
        await message.answer("Пустой запрос." if lang == "ru" else "Empty query.")
        return

    rows = await search_categories(pool, query, lang=lang, limit=15)
    if not rows:
        await message.answer("Ничего не найдено." if lang == "ru" else "Nothing found.", reply_markup=category_search_kb(lang))
        await state.clear()
        return

    await message.answer(
        "Найденные категории:" if lang == "ru" else "Found categories:",
        reply_markup=categories_tree_kb(rows, lang=lang, parent_id=None),
    )
    await state.clear()


@router.callback_query(F.data == "admin:category:add")
async def category_add_root(call: CallbackQuery, state: FSMContext):
    if not call.from_user or not call.message:
        return

    lang = _lang(call.from_user)
    await state.clear()
    await state.update_data(parent_id=None)
    await state.set_state(CategoryFlow.waiting_create_node_type)
    await _safe_edit(
        call.message,
        "Выбери тип новой категории:" if lang == "ru" else "Choose the new category type:",
        reply_markup=category_create_type_kb(lang, back_cb="admin:categories:root"),
        parse_mode=None,
    )
    await call.answer()


@router.callback_query(F.data == "admin:category:addroot")
async def category_add_root_alias(call: CallbackQuery, state: FSMContext):
    await category_add_root(call, state)


@router.callback_query(F.data.startswith("admin:category:addto:"))
async def category_add_to(call: CallbackQuery, state: FSMContext, pool):
    if not call.from_user or not call.message:
        return

    lang = _lang(call.from_user)
    parent_id = int(call.data.split(":")[-1])
    parent = await get_category(pool, parent_id)

    if not parent:
        await call.answer("Родительская категория не найдена." if lang == "ru" else "Parent category not found.", show_alert=True)
        return

    if parent["node_type"] != "branch":
        await call.answer("Родительская категория должна быть ветвью." if lang == "ru" else "Parent category must be a branch.", show_alert=True)
        return

    data = await state.get_data()
    node_type = data.get("new_node_type")

    await state.update_data(parent_id=parent_id)

    if not node_type:
        await state.set_state(CategoryFlow.waiting_create_node_type)
        await _safe_edit(
            call.message,
            "Выбери тип новой категории:" if lang == "ru" else "Choose the new category type:",
            reply_markup=category_create_type_kb(lang, back_cb=f"admin:category:open:{parent_id}"),
            parse_mode=None,
        )
        await call.answer()
        return

    await state.set_state(CategoryFlow.waiting_name_ru)
    await _safe_edit(call.message, "Введите название категории на русском:" if lang == "ru" else "Enter category name in Russian:", parse_mode=None)
    await call.answer()


@router.callback_query(F.data == "admin:category:create:type:branch")
@router.callback_query(F.data == "admin:category:create:type:leaf")
async def category_create_type_pick(call: CallbackQuery, state: FSMContext, pool):
    if not call.from_user or not call.message:
        return

    lang = _lang(call.from_user)
    new_type = call.data.rsplit(":", 1)[-1]
    data = await state.get_data()
    parent_id = data.get("parent_id")

    await state.update_data(new_node_type=new_type)

    if parent_id is not None:
        await state.set_state(CategoryFlow.waiting_name_ru)
        await _safe_edit(call.message, "Введите название категории на русском:" if lang == "ru" else "Enter category name in Russian:", parse_mode=None)
        await call.answer()
        return

    await state.set_state(CategoryFlow.waiting_create_parent_choice)
    await _safe_edit(
        call.message,
        "Где разместить категорию?" if lang == "ru" else "Where should the category be placed?",
        reply_markup=category_create_place_kb(lang, back_cb="admin:categories:root"),
        parse_mode=None,
    )
    await call.answer()


@router.callback_query(F.data == "admin:category:create:place:root")
async def category_create_place_root(call: CallbackQuery, state: FSMContext):
    if not call.from_user or not call.message:
        return

    lang = _lang(call.from_user)
    await state.update_data(parent_id=None)
    await state.set_state(CategoryFlow.waiting_name_ru)
    await _safe_edit(call.message, "Введите название категории на русском:" if lang == "ru" else "Enter category name in Russian:", parse_mode=None)
    await call.answer()


@router.callback_query(F.data == "admin:category:create:place:choose")
async def category_create_place_choose(call: CallbackQuery, state: FSMContext, pool):
    if not call.from_user or not call.message:
        return

    lang = _lang(call.from_user)
    rows = await get_root_categories(pool, lang=lang)
    await state.set_state(CategoryFlow.waiting_create_parent_choice)
    await _safe_edit(
        call.message,
        (
            "Открой нужную категорию и нажми «Добавить сюда»." if lang == "ru" else
            "Open the target category and press Add here."
        ),
        reply_markup=categories_tree_kb(rows, lang=lang, parent_id=None),
        parse_mode=None,
    )
    await call.answer()


@router.message(StateFilter(CategoryFlow.waiting_name_ru), F.text)
async def category_name_ru(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Название не может быть пустым.")
        return
    await state.update_data(name_ru=text)
    await state.set_state(CategoryFlow.waiting_name_en)
    await message.answer("Введите название категории на английском:" )


@router.message(StateFilter(CategoryFlow.waiting_name_en), F.text)
async def category_name_en(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Название не может быть пустым.")
        return
    await state.update_data(name_en=text)
    await state.set_state(CategoryFlow.waiting_sort_order)
    await message.answer("Введите sort_order, например 0:")


@router.message(StateFilter(CategoryFlow.waiting_sort_order), F.text)
async def category_sort_order(message: Message, state: FSMContext):
    raw = (message.text or "0").strip()
    try:
        sort_order = int(raw)
    except ValueError:
        await message.answer("Нужно целое число.")
        return

    await state.update_data(sort_order=sort_order)
    data = await state.get_data()
    preview = (
        "<b>Проверь данные</b>\n"
        f"Тип: {escape(str(data.get('new_node_type', 'branch')))}\n"
        f"RU: {escape(data['name_ru'])}\n"
        f"EN: {escape(data['name_en'])}\n"
        f"Родитель: {data.get('parent_id')}\n"
        f"Порядок: {sort_order}"
    )
    lang = _lang(message.from_user)
    await state.set_state(CategoryFlow.waiting_confirm_create)
    await message.answer(preview, parse_mode="HTML", reply_markup=category_confirm_kb("admin:category:confirm", "admin:categories:root", lang=lang))


@router.callback_query(F.data == "admin:category:confirm")
async def category_confirm(call: CallbackQuery, state: FSMContext, pool):
    if not call.from_user or not call.message:
        return

    data = await state.get_data()
    parent_id = data.get("parent_id")
    node_type = data.get("new_node_type", "branch")
    lang = _lang(call.from_user)

    if parent_id is not None:
        parent = await get_category(pool, int(parent_id))
        if not parent:
            await call.answer("Родительская категория не найдена.", show_alert=True)
            return
        if parent["node_type"] != "branch":
            await call.answer("Родительская категория должна быть ветвью.", show_alert=True)
            return

    category_id = await create_category(
        pool,
        name_ru=data["name_ru"],
        name_en=data["name_en"],
        parent_id=parent_id,
        node_type=node_type,
        sort_order=int(data.get("sort_order", 0)),
    )

    await write_audit_log(
        pool,
        user_id=call.from_user.id,
        action="category_create",
        target_type="category",
        target_id=category_id,
        payload={"name_ru": data["name_ru"], "name_en": data["name_en"], "parent_id": parent_id, "node_type": node_type, "sort_order": int(data.get("sort_order", 0))},
    )
    await invalidate_category_catalog()
    await invalidate_waifu_catalog()
    await state.clear()

    await _safe_edit(call.message, f"Категория создана. ID: <code>{category_id}</code>" if lang == "ru" else f"Category created. ID: <code>{category_id}</code>", reply_markup=categories_menu_kb(lang))
    await call.answer()


@router.callback_query(F.data.startswith("admin:category:edit:"))
async def category_edit_start(call: CallbackQuery, state: FSMContext, pool):
    if not call.from_user or not call.message:
        return

    lang = _lang(call.from_user)
    category_id = int(call.data.split(":")[-1])
    category = await get_category(pool, category_id)

    if not category:
        await call.answer("Категория не найдена." if lang == "ru" else "Category not found.", show_alert=True)
        return

    await state.clear()
    await state.update_data(category_id=category_id)
    await _safe_edit(
        call.message,
        (
            "<b>Редактирование категории</b>\n"
            f"ID: <code>{category_id}</code>\n"
            f"Название: {escape(_cat_name(category, lang))}\n\n"
            "Выбери поле:"
            if lang == "ru"
            else
            "<b>Edit category</b>\n"
            f"ID: <code>{category_id}</code>\n"
            f"Name: {escape(_cat_name(category, lang))}\n\n"
            "Choose field:"
        ),
        reply_markup=category_fields_kb(category_id, lang),
    )
    await call.answer()


@router.callback_query(F.data == "admin:category:edit")
async def category_edit_alias(call: CallbackQuery, pool):
    if not call.from_user or not call.message:
        return
    lang = _lang(call.from_user)
    await _safe_edit(call.message, "Открой категорию и нажми «Редактировать»." if lang == "ru" else "Open a category and press Edit.", reply_markup=categories_menu_kb(lang), parse_mode=None)
    await call.answer()


@router.callback_query(F.data.startswith("admin:category:field:"))
async def category_field_pick(call: CallbackQuery, state: FSMContext, pool):
    if not call.from_user or not call.message:
        return

    lang = _lang(call.from_user)
    _, _, _, category_id_str, field = call.data.split(":", 4)
    category_id = int(category_id_str)
    category = await get_category(pool, category_id)

    if not category:
        await call.answer("Категория не найдена." if lang == "ru" else "Category not found.", show_alert=True)
        return

    await state.clear()
    await state.update_data(category_id=category_id, edit_field=field)

    if field in {"name_ru", "name_en", "sort_order"}:
        await state.set_state(CategoryFlow.waiting_edit_value)
        prompt = {
            "name_ru": "Введите новое название на русском:" if lang == "ru" else "Enter new Russian name:",
            "name_en": "Введите новое название на английском:" if lang == "ru" else "Enter new English name:",
            "sort_order": "Введите новый sort_order:" if lang == "ru" else "Enter new sort_order:",
        }[field]
        await _safe_edit(call.message, prompt, parse_mode=None)

    elif field == "node_type":
        await _safe_edit(call.message, "Выбери новый тип категории:" if lang == "ru" else "Choose new category type:", reply_markup=category_node_type_kb(category_id, lang), parse_mode=None)

    elif field == "is_active":
        await _safe_edit(call.message, "Сделать категорию активной?" if lang == "ru" else "Make category active?", reply_markup=category_bool_kb(category_id, field, lang), parse_mode=None)

    elif field == "parent_id":
        await state.set_state(CategoryFlow.waiting_edit_parent_pick)
        rows = await get_root_categories(pool, lang=lang)
        await _safe_edit(call.message, "Выбери новую родительскую категорию:" if lang == "ru" else "Choose new parent category:", reply_markup=categories_tree_kb(rows, lang=lang, parent_id=None, selection_mode="edit_parent"), parse_mode=None)

    await call.answer()


@router.callback_query(F.data.startswith("admin:category:node:"))
async def category_node_type_set(call: CallbackQuery, state: FSMContext, pool):
    if not call.from_user or not call.message:
        return

    lang = _lang(call.from_user)
    _, _, _, category_id_str, new_type = call.data.split(":", 4)
    category_id = int(category_id_str)
    category = await get_category(pool, category_id)

    if not category:
        await call.answer("Категория не найдена." if lang == "ru" else "Category not found.", show_alert=True)
        return

    children_count = await get_children_count(pool, category_id)
    if new_type == "leaf" and children_count > 0:
        await call.answer("Нельзя сделать leaf-категорию родителем для подкатегорий." if lang == "ru" else "A leaf category cannot contain subcategories.", show_alert=True)
        return

    await update_category(
        pool,
        category_id=category_id,
        name_ru=category["name_ru"],
        name_en=category["name_en"],
        parent_id=category["parent_id"],
        node_type=new_type,
        is_active=bool(category["is_active"]),
        sort_order=int(category["sort_order"]),
    )

    await write_audit_log(pool, user_id=call.from_user.id, action="category_update", target_type="category", target_id=category_id, payload={"node_type": new_type})
    await invalidate_category_catalog()
    await invalidate_waifu_catalog()

    await _safe_edit(call.message, "Тип категории обновлён." if lang == "ru" else "Category type updated.", reply_markup=category_fields_kb(category_id, lang), parse_mode=None)
    await call.answer()


@router.callback_query(F.data.startswith("admin:category:bool:"))
async def category_bool_set(call: CallbackQuery, pool):
    if not call.from_user or not call.message:
        return

    lang = _lang(call.from_user)
    _, _, _, category_id_str, field, value = call.data.split(":", 5)
    category_id = int(category_id_str)
    category = await get_category(pool, category_id)

    if not category:
        await call.answer("Категория не найдена." if lang == "ru" else "Category not found.", show_alert=True)
        return

    is_active = value == "1"
    await update_category(
        pool,
        category_id=category_id,
        name_ru=category["name_ru"],
        name_en=category["name_en"],
        parent_id=category["parent_id"],
        node_type=category["node_type"],
        is_active=is_active,
        sort_order=int(category["sort_order"]),
    )

    await write_audit_log(pool, user_id=call.from_user.id, action="category_update", target_type="category", target_id=category_id, payload={field: is_active})
    await invalidate_category_catalog()
    await invalidate_waifu_catalog()

    await _safe_edit(call.message, "Состояние категории обновлено." if lang == "ru" else "Category state updated.", reply_markup=category_fields_kb(category_id, lang), parse_mode=None)
    await call.answer()


@router.message(StateFilter(CategoryFlow.waiting_edit_value), F.text)
async def category_edit_value(message: Message, state: FSMContext, pool):
    if not message.from_user:
        return

    data = await state.get_data()
    category_id = int(data["category_id"])
    field = data["edit_field"]
    lang = _lang(message.from_user)

    category = await get_category(pool, category_id)
    if not category:
        await message.answer("Категория не найдена." if lang == "ru" else "Category not found.")
        return

    value = (message.text or "").strip()
    if field in {"name_ru", "name_en"}:
        if not value:
            await message.answer("Значение не может быть пустым.")
            return
    elif field == "sort_order":
        try:
            value = int(value)
        except ValueError:
            await message.answer("Нужно целое число.")
            return
    else:
        await message.answer("Это поле настраивается кнопками." if lang == "ru" else "This field is controlled by buttons.")
        return

    updates = {
        "name_ru": category["name_ru"],
        "name_en": category["name_en"],
        "parent_id": category["parent_id"],
        "node_type": category["node_type"],
        "is_active": bool(category["is_active"]),
        "sort_order": int(category["sort_order"]),
    }
    updates[field] = value

    await state.update_data(edit_value=updates)
    preview = (
        "<b>Сохранить изменения?</b>\n"
        f"ID: <code>{category_id}</code>\n"
        f"field: {escape(field)}\n"
        f"value: {escape(str(value))}"
        if lang == "ru"
        else
        "<b>Save changes?</b>\n"
        f"ID: <code>{category_id}</code>\n"
        f"field: {escape(field)}\n"
        f"value: {escape(str(value))}"
    )
    await state.set_state(CategoryFlow.waiting_confirm_create)
    await message.answer(preview, parse_mode="HTML", reply_markup=category_confirm_kb(f"admin:category:editconfirm:{category_id}", f"admin:category:edit:{category_id}", lang))


@router.callback_query(F.data.startswith("admin:category:editconfirm:"))
async def category_edit_confirm(call: CallbackQuery, state: FSMContext, pool):
    if not call.from_user or not call.message:
        return

    category_id = int(call.data.split(":")[-1])
    data = await state.get_data()
    upd = data.get("edit_value")
    lang = _lang(call.from_user)

    if not upd:
        await call.answer("Нет данных для сохранения." if lang == "ru" else "No data to save.", show_alert=True)
        return

    current = await get_category(pool, category_id)
    if not current:
        await call.answer("Категория не найдена." if lang == "ru" else "Category not found.", show_alert=True)
        return

    if upd["parent_id"] is not None:
        parent = await get_category(pool, int(upd["parent_id"]))
        if not parent:
            await call.answer("Родительская категория не найдена.", show_alert=True)
            return
        if parent["node_type"] != "branch":
            await call.answer("Родительская категория должна быть ветвью.", show_alert=True)
            return
        if int(upd["parent_id"]) == category_id:
            await call.answer("Категория не может быть родителем самой себя.", show_alert=True)
            return

    children_count = await get_children_count(pool, category_id)
    if upd["node_type"] == "leaf" and children_count > 0:
        await call.answer("Нельзя сделать листовую категорию родителем для подкатегорий.", show_alert=True)
        return

    await update_category(
        pool,
        category_id=category_id,
        name_ru=upd["name_ru"],
        name_en=upd["name_en"],
        parent_id=upd["parent_id"],
        node_type=upd["node_type"],
        is_active=upd["is_active"],
        sort_order=upd["sort_order"],
    )

    await write_audit_log(pool, user_id=call.from_user.id, action="category_update", target_type="category", target_id=category_id, payload=upd)
    await invalidate_category_catalog()
    await invalidate_waifu_catalog()
    await state.clear()

    await _safe_edit(call.message, "Категория обновлена." if lang == "ru" else "Category updated.", reply_markup=categories_menu_kb(lang), parse_mode=None)
    await call.answer()


@router.callback_query(F.data.startswith("admin:category:setparent:"))
async def category_set_parent(call: CallbackQuery, state: FSMContext, pool):
    if not call.from_user or not call.message:
        return

    lang = _lang(call.from_user)
    new_parent_id = int(call.data.split(":")[-1])
    data = await state.get_data()
    category_id = int(data.get("category_id") or 0)

    if not category_id:
        await call.answer("Нет выбранной категории." if lang == "ru" else "No category selected.", show_alert=True)
        return

    category = await get_category(pool, category_id)
    parent = await get_category(pool, new_parent_id)

    if not category or not parent:
        await call.answer("Категория не найдена." if lang == "ru" else "Category not found.", show_alert=True)
        return

    if parent["node_type"] != "branch":
        await call.answer("Родительская категория должна быть ветвью.", show_alert=True)
        return

    if new_parent_id == category_id:
        await call.answer("Категория не может быть родителем самой себя.", show_alert=True)
        return

    current = parent
    while current and current["parent_id"] is not None:
        if int(current["parent_id"]) == category_id:
            await call.answer("Нельзя переместить категорию в её же поддерево.", show_alert=True)
            return
        current = await get_category(pool, int(current["parent_id"]))

    await update_category(
        pool,
        category_id=category_id,
        name_ru=category["name_ru"],
        name_en=category["name_en"],
        parent_id=new_parent_id,
        node_type=category["node_type"],
        is_active=bool(category["is_active"]),
        sort_order=int(category["sort_order"]),
    )

    await write_audit_log(pool, user_id=call.from_user.id, action="category_update", target_type="category", target_id=category_id, payload={"parent_id": new_parent_id})
    await invalidate_category_catalog()
    await invalidate_waifu_catalog()
    await state.clear()

    await _safe_edit(call.message, "Родительская категория обновлена." if lang == "ru" else "Parent category updated.", reply_markup=categories_menu_kb(lang), parse_mode=None)
    await call.answer()


@router.callback_query(F.data.startswith("admin:category:delete:"))
async def category_delete_start(call: CallbackQuery, state: FSMContext, pool):
    if not call.from_user or not call.message:
        return

    lang = _lang(call.from_user)
    category_id = int(call.data.split(":")[-1])
    category = await get_category(pool, category_id)

    if not category:
        await call.answer("Категория не найдена." if lang == "ru" else "Category not found.", show_alert=True)
        return

    stats = await get_descendant_stats(pool, category_id)
    await state.clear()
    await state.update_data(category_id=category_id)
    await state.set_state(CategoryFlow.waiting_delete_confirm)

    await _safe_edit(
        call.message,
        (
            f"Будет удалено категорий: {stats['categories_count']}\n"
            f"Будет удалено вайфу: {stats['waifus_count']}\n"
            f"Подтвердить?"
            if lang == "ru"
            else
            f"Categories to delete: {stats['categories_count']}\n"
            f"Waifus to delete: {stats['waifus_count']}\n"
            f"Confirm?"
        ),
        reply_markup=category_confirm_kb(f"admin:category:deleteconfirm:{category_id}", f"admin:category:open:{category_id}", lang),
        parse_mode=None,
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:category:deleteconfirm:"))
async def category_delete_confirm(call: CallbackQuery, state: FSMContext, pool):
    if not call.from_user or not call.message:
        return

    category_id = int(call.data.split(":")[-1])
    lang = _lang(call.from_user)
    deleted = await delete_category_tree(pool, category_id)

    await write_audit_log(pool, user_id=call.from_user.id, action="category_delete", target_type="category", target_id=category_id, payload={"deleted_category_nodes": deleted})
    await invalidate_category_catalog()
    await invalidate_waifu_catalog()
    await state.clear()

    await _safe_edit(call.message, "Категория и вся ветка удалены." if lang == "ru" else "Category and whole branch deleted.", reply_markup=categories_menu_kb(lang), parse_mode=None)
    await call.answer()
