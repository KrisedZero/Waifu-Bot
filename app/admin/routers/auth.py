from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.types import CallbackQuery, Message

from app.admin.config import admin_config
from app.admin.keyboards.menu import build_admin_menu_keyboard
from app.admin.services.admin_auth_service import (
    AdminAuthResult,
    authenticate_admin_password,
    change_admin_password,
    is_admin_authorized,
    logout_admin,
)
from app.admin.states.auth import AdminAuthStates
from app.admin.utils.telegram import safe_replace_text
from app.services.user_service import get_user_language

router = Router()


def _text(lang: str, key: str) -> str:
    texts = {
        "ru": {
            "login_prompt": "🔐 Введи пароль для входа в админ-панель:",
            "menu_title": "👑 <b>Админ-панель</b>\n\nВыбери раздел:",
            "wrong": "❌ Неверный пароль.",
            "locked": "⏳ Доступ временно заблокирован. Попробуй позже.",
            "banned": "⛔ Доступ к админке навсегда заблокирован.",
            "owner_only": "⛔ Эту команду может использовать только владелец бота.",
            "password_change_prompt": "🔑 Введи новый пароль для админки:",
            "password_changed": "✅ Пароль изменён. Все старые сессии сброшены. Введи /admin заново.",
            "session_reset": "♻️ Сессия сброшена. Введи пароль заново.",
        },
        "en": {
            "login_prompt": "🔐 Enter the password to access the admin panel:",
            "menu_title": "👑 <b>Admin panel</b>\n\nChoose a section:",
            "wrong": "❌ Wrong password.",
            "locked": "⏳ Access is temporarily locked. Try again later.",
            "banned": "⛔ Admin access is permanently blocked.",
            "owner_only": "⛔ Only the bot owner can use this command.",
            "password_change_prompt": "🔑 Enter a new admin password:",
            "password_changed": "✅ Password changed. All old sessions were reset. Use /admin again.",
            "session_reset": "♻️ Session reset. Enter password again.",
        },
    }
    return texts.get(lang, texts["ru"])[key]


def _fmt_attempts(lang: str, result: AdminAuthResult) -> str:
    if lang == "ru":
        return f"❌ Неверный пароль. Осталось попыток до следующего лимита: {result.attempts_left}"
    return f"❌ Wrong password. Attempts left before the next limit: {result.attempts_left}"


@router.message(Command("admin"))
async def admin_entry(message: Message, state: FSMContext):
    if not message.from_user:
        return

    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    if await is_admin_authorized(user_id):
        await state.clear()
        await message.answer(
            _text(lang, "menu_title"),
            parse_mode="HTML",
            reply_markup=build_admin_menu_keyboard(lang, user_id == admin_config.ADMIN_OWNER_ID),
        )
        return

    await state.set_state(AdminAuthStates.waiting_password)
    await message.answer(_text(lang, "login_prompt"))


@router.message(AdminAuthStates.waiting_password, F.text)
async def admin_password_input(message: Message, state: FSMContext):
    if not message.from_user or not message.text:
        return

    user_id = message.from_user.id
    lang = await get_user_language(user_id)
    result = await authenticate_admin_password(user_id, message.text.strip())

    if result.ok:
        await state.clear()
        await message.answer(
            _text(lang, "menu_title"),
            parse_mode="HTML",
            reply_markup=build_admin_menu_keyboard(lang, user_id == admin_config.ADMIN_OWNER_ID),
        )
        return

    if result.reason == "permanent_ban":
        await message.answer(_text(lang, "banned"))
        return

    if result.reason == "locked":
        if result.wait_seconds > 0:
            minutes = max(1, result.wait_seconds // 60)
            if lang == "ru":
                await message.answer(f"⏳ Попробуй снова через ~{minutes} мин.")
            else:
                await message.answer(f"⏳ Try again in about {minutes} min.")
        else:
            await message.answer(_text(lang, "locked"))
        return

    await message.answer(_fmt_attempts(lang, result) if result.attempts_left else _text(lang, "wrong"))


@router.callback_query(F.data == "admin:reload_session")
async def reload_session_handler(call, state: FSMContext):
    if not call.from_user:
        return
    lang = await get_user_language(call.from_user.id)
    await logout_admin(call.from_user.id)
    await state.clear()
    await safe_replace_text(call.message, _text(lang, "session_reset"), parse_mode=None)
    await call.answer()


@router.callback_query(F.data == "admin:logout")
async def logout_handler(call, state: FSMContext):
    if not call.from_user:
        return
    lang = await get_user_language(call.from_user.id)
    await logout_admin(call.from_user.id)
    await state.clear()
    await safe_replace_text(call.message, _text(lang, "session_reset"), parse_mode=None)
    await call.answer()


@router.message(Command("changepassword"))
async def change_password_start(message: Message, state: FSMContext):
    if not message.from_user:
        return

    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    if user_id != admin_config.ADMIN_OWNER_ID or admin_config.ADMIN_OWNER_ID == 0:
        await message.answer(_text(lang, "owner_only"))
        return

    await state.set_state(AdminAuthStates.waiting_new_password)
    await message.answer(_text(lang, "password_change_prompt"))

@router.callback_query(F.data == "admin:change_password")
async def change_password_button(call: CallbackQuery, state: FSMContext):
    if not call.from_user:
        return

    user_id = call.from_user.id
    lang = await get_user_language(user_id)

    if user_id != admin_config.ADMIN_OWNER_ID or admin_config.ADMIN_OWNER_ID == 0:
        await call.answer(_text(lang, "owner_only"), show_alert=True)
        return

    await state.set_state(AdminAuthStates.waiting_new_password)
    await safe_replace_text(call.message, _text(lang, "password_change_prompt"), parse_mode=None)
    await call.answer()

@router.message(AdminAuthStates.waiting_new_password, F.text)
async def change_password_finish(message: Message, state: FSMContext):
    if not message.from_user or not message.text:
        return

    user_id = message.from_user.id
    lang = await get_user_language(user_id)

    if user_id != admin_config.ADMIN_OWNER_ID or admin_config.ADMIN_OWNER_ID == 0:
        await state.clear()
        await message.answer(_text(lang, "owner_only"))
        return

    new_password = message.text.strip()
    if len(new_password) < 8:
        await message.answer("❌ Пароль должен быть минимум 8 символов." if lang == "ru" else "❌ Password must be at least 8 characters long.")
        return

    await change_admin_password(new_password, user_id)
    await logout_admin(user_id)
    await state.clear()
    await message.answer(_text(lang, "password_changed"))
