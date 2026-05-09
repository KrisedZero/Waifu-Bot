from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_pagination_keyboard(prefix: str, page: int, total_pages: int):
    builder = InlineKeyboardBuilder()

    if page > 1:
        builder.button(text="⬅️", callback_data=f"{prefix}:{page - 1}")

    if page < total_pages:
        builder.button(text="➡️", callback_data=f"{prefix}:{page + 1}")

    if page > 1 or page < total_pages:
        builder.adjust(2)

    return builder.as_markup() if page > 1 or page < total_pages else None