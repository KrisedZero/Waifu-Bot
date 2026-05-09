from __future__ import annotations

from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_admin_menu_keyboard(lang: str = "ru", is_owner: bool = False):
    kb = InlineKeyboardBuilder()
    if lang == "en":
        kb.button(text="📁 Categories", callback_data="admin:categories")
        kb.button(text="🧩 Waifus", callback_data="admin:waifus")
        kb.button(text="❓ Help", callback_data="admin:help")
        if is_owner:
            kb.button(text="👥 Active admins", callback_data="admin:active_admins")
            kb.button(text="🔑 Change password", callback_data="admin:change_password")
        kb.button(text="♻️ Refresh session", callback_data="admin:reload_session")
        kb.button(text="🚪 Logout", callback_data="admin:logout")
    else:
        kb.button(text="📁 Категории", callback_data="admin:categories")
        kb.button(text="🧩 Вайфу", callback_data="admin:waifus")
        kb.button(text="❓ Помощь", callback_data="admin:help")
        if is_owner:
            kb.button(text="👥 Активные админы", callback_data="admin:active_admins")
            kb.button(text="🔑 Сменить пароль", callback_data="admin:change_password")
        kb.button(text="♻️ Обновить сессию", callback_data="admin:reload_session")
        kb.button(text="🚪 Выйти", callback_data="admin:logout")

    kb.adjust(2, 2, 2)
    return kb.as_markup()
