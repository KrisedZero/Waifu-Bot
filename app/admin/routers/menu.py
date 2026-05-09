from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.admin.config import admin_config
from app.admin.keyboards.menu import build_admin_menu_keyboard
from app.admin.services.admin_auth_service import is_admin_authorized
from app.admin.services.admin_command_service import list_active_admin_sessions
from app.admin.utils.telegram import safe_replace_text
from app.services.user_service import get_user_language

router = Router()


def _text(lang: str, key: str) -> str:
    texts = {
        "ru": {
            "menu_title": "👑 <b>Админ-панель</b>\n\nВыбери раздел:",
            "need_login": "Сначала войди в админку через /admin.",
            "categories_title": "📁 <b>Категории</b>\n\nУправление деревом категорий.",
            "waifus_title": "🧩 <b>Вайфу</b>\n\nУправление персонажами и медиа.",
            "help_title": "❓ <b>Помощь по админке</b>",
            "help_body": (
                "<b>Категории</b> — добавляй и открывай дерево категорий, включая подкатегории.\n"
                "<b>Вайфу</b> — добавляй, редактируй, ищи и удаляй вайфу.\n"
                "<b>Медиа</b> — прикрепляй фото, видео, GIF и другие файлы к вайфу.\n"
                "<b>Подсказка</b> — после любого действия можно вернуться назад через кнопки меню."
            ),
            "help_hint": "Выбери раздел ниже или вернись в главное меню.",
            "owner_only": "⛔ Эту кнопку может использовать только владелец бота.",
            "active_admins_title": "👥 <b>Активные админы</b>",
            "active_admins_empty": "Сейчас активных админов нет.",
        },
        "en": {
            "menu_title": "👑 <b>Admin panel</b>\n\nChoose a section:",
            "need_login": "Please log in with /admin first.",
            "categories_title": "📁 <b>Categories</b>\n\nManage the category tree.",
            "waifus_title": "🧩 <b>Waifus</b>\n\nManage characters and media.",
            "help_title": "❓ <b>Admin help</b>",
            "help_body": (
                "<b>Categories</b> — manage the category tree, including subcategories.\n"
                "<b>Waifus</b> — add, edit, search and delete waifus.\n"
                "<b>Media</b> — attach photos, videos, GIFs and other files to waifus.\n"
                "<b>Tip</b> — after any action, use the menu buttons to go back."
            ),
            "help_hint": "Pick a section below or return to the main menu.",
            "owner_only": "⛔ Only the bot owner can use this button.",
            "active_admins_title": "👥 <b>Active admins</b>",
            "active_admins_empty": "There are no active admins right now.",
        },
    }
    return texts.get(lang, texts["ru"])[key]


async def _show_menu(call: CallbackQuery) -> None:
    if not call.from_user or not call.message:
        return

    user_id = call.from_user.id
    lang = "ru"

    if not await is_admin_authorized(user_id):
        await call.answer(_text(lang, "need_login"), show_alert=True)
        return

    await safe_replace_text(
        call.message,
        _text(lang, "menu_title"),
        parse_mode="HTML",
        reply_markup=build_admin_menu_keyboard(lang, user_id == admin_config.ADMIN_OWNER_ID),
    )
    await call.answer()


@router.message(Command("help"))
async def admin_help_command(message: Message):
    if not message.from_user:
        return

    lang = await get_user_language(message.from_user.id)
    if not await is_admin_authorized(message.from_user.id):
        await message.answer(_text(lang, "need_login"))
        return

    text = f"{_text(lang, 'help_title')}\n\n{_text(lang, 'help_body')}\n\n{_text(lang, 'help_hint')}"
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=build_admin_menu_keyboard(lang, message.from_user.id == admin_config.ADMIN_OWNER_ID),
    )


@router.callback_query(F.data == "admin:menu")
async def admin_menu(call: CallbackQuery):
    await _show_menu(call)


@router.callback_query(F.data == "admin:categories")
async def admin_categories(call: CallbackQuery):
    if not call.from_user or not call.message:
        return
    lang = "ru"
    if not await is_admin_authorized(call.from_user.id):
        await call.answer(_text(lang, "need_login"), show_alert=True)
        return
    from app.admin.keyboards.categories import categories_menu_kb
    await safe_replace_text(call.message, _text(lang, "categories_title"), parse_mode="HTML", reply_markup=categories_menu_kb(lang))
    await call.answer()


@router.callback_query(F.data == "admin:waifus")
async def admin_waifus(call: CallbackQuery):
    if not call.from_user or not call.message:
        return
    lang = "ru"
    if not await is_admin_authorized(call.from_user.id):
        await call.answer(_text(lang, "need_login"), show_alert=True)
        return
    from app.admin.keyboards.waifus import waifus_menu_kb
    await safe_replace_text(call.message, _text(lang, "waifus_title"), parse_mode="HTML", reply_markup=waifus_menu_kb(lang))
    await call.answer()


@router.callback_query(F.data == "admin:help")
async def admin_help(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    lang = "ru"
    if not await is_admin_authorized(call.from_user.id):
        await call.answer(_text(lang, "need_login"), show_alert=True)
        return

    text = f"{_text(lang, 'help_title')}\n\n{_text(lang, 'help_body')}\n\n{_text(lang, 'help_hint')}"
    await safe_replace_text(
        call.message,
        text,
        parse_mode="HTML",
        reply_markup=build_admin_menu_keyboard(lang, call.from_user.id == admin_config.ADMIN_OWNER_ID),
    )
    await call.answer()


@router.callback_query(F.data == "admin:active_admins")
async def admin_active_admins(call: CallbackQuery):
    if not call.from_user or not call.message:
        return

    lang = "ru"
    if call.from_user.id != admin_config.ADMIN_OWNER_ID:
        await call.answer(_text(lang, "owner_only"), show_alert=True)
        return

    if not await is_admin_authorized(call.from_user.id):
        await call.answer(_text(lang, "need_login"), show_alert=True)
        return

    sessions = await list_active_admin_sessions()
    if not sessions:
        await safe_replace_text(call.message, _text(lang, "active_admins_empty"), parse_mode="HTML")
        await call.answer()
        return

    lines = [_text(lang, "active_admins_title"), f"", f"Всего: <b>{len(sessions)}</b>"]

    for i, row in enumerate(sessions, start=1):
        user_id = int(row["user_id"])
        display = f"ID <code>{user_id}</code>"
        try:
            chat = await call.bot.get_chat(user_id)
            parts = []
            if getattr(chat, "first_name", None):
                parts.append(chat.first_name)
            if getattr(chat, "last_name", None):
                parts.append(chat.last_name)
            full_name = " ".join(parts).strip()
            username = f"@{chat.username}" if getattr(chat, "username", None) else ""
            if full_name or username:
                name_line = " — ".join(p for p in [full_name or None, username or None] if p)
                display = f"<b>{name_line}</b> (<code>{user_id}</code>)"
        except Exception:
            pass

        last_auth = row["last_auth_at"]
        last_auth_text = last_auth.strftime("%Y-%m-%d %H:%M UTC") if last_auth else "—"
        role = row["role"] or "admin"
        lines.append(f"{i}. {display}\n   role: <code>{role}</code> · last auth: <code>{last_auth_text}</code>")

    text = "\n".join(lines)
    await safe_replace_text(call.message, text, parse_mode="HTML")
    await call.answer()
