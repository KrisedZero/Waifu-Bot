from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message


async def safe_edit_text(
    message: Message,
    text: str,
    *,
    reply_markup=None,
    parse_mode: str | None = "HTML",
):
    try:
        return await message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except TelegramBadRequest as e:
        err = str(e).lower()
        if "message is not modified" in err:
            return None
        if "there is no text in the message to edit" in err or "there is no text in the message" in err:
            try:
                return await message.edit_caption(
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
            except TelegramBadRequest as e2:
                err2 = str(e2).lower()
                if "message is not modified" in err2:
                    return None
                if "there is no caption in the message to edit" in err2 or "there is no caption" in err2:
                    try:
                        return await message.answer(
                            text,
                            reply_markup=reply_markup,
                            parse_mode=parse_mode,
                        )
                    except TelegramBadRequest:
                        return None
                raise
        raise


async def safe_replace_text(
    message: Message,
    text: str,
    *,
    reply_markup=None,
    parse_mode: str | None = "HTML",
):
    """Replace the current message with plain text.

    If the current bot message contains media, delete it first so the new
    screen does not keep the old photo/video/document attached.
    """
    has_media = bool(message.photo or message.video or message.animation or message.document)
    if has_media:
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
        try:
            return await message.answer(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        except TelegramBadRequest:
            return None

    return await safe_edit_text(
        message,
        text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
