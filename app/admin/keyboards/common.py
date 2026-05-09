from __future__ import annotations

from aiogram.utils.keyboard import InlineKeyboardBuilder


def kb_confirm_cancel(confirm_cb: str, cancel_cb: str, lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    if lang == "en":
        kb.button(text="✅ Confirm", callback_data=confirm_cb)
        kb.button(text="❌ Cancel", callback_data=cancel_cb)
    else:
        kb.button(text="✅ Подтвердить", callback_data=confirm_cb)
        kb.button(text="❌ Отмена", callback_data=cancel_cb)
    kb.adjust(2)
    return kb.as_markup()


def kb_back(back_cb: str, lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back" if lang == "en" else "⬅️ Назад", callback_data=back_cb)
    return kb.as_markup()
