from __future__ import annotations

from pathlib import Path

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, Message


LOCAL_MEDIA_PREFIX = "local:"


def normalize_media_type(media_type: str | None) -> str | None:
    if not media_type:
        return None
    media_type = media_type.lower().strip()
    if media_type == "gif":
        return "animation"
    return media_type


def _resolve_media_source(file_ref: str | None):
    if not file_ref:
        return None

    resolved = Path(file_ref)
    if resolved.exists() and resolved.is_file():
        return FSInputFile(str(resolved))

    if file_ref.startswith(LOCAL_MEDIA_PREFIX):
        local_path = Path(file_ref[len(LOCAL_MEDIA_PREFIX):])
        if local_path.exists() and local_path.is_file():
            return FSInputFile(str(local_path))

    return file_ref


async def send_waifu_media(
    message: Message,
    media: dict | None,
    caption: str,
    *,
    reply_markup=None,
    parse_mode: str = "HTML",
) -> bool:
    """Sends waifu media if possible.
    Returns True when media was sent, False when fallback text should be used.
    """
    if not media:
        return False

    media_type = normalize_media_type(media.get("media_type"))
    file_ref = media.get("file_id")

    if not file_ref or media_type not in {"photo", "video", "animation", "document"}:
        return False

    source = _resolve_media_source(str(file_ref))
    if source is None:
        return False

    try:
        if media_type == "photo":
            await message.answer_photo(source, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
            return True
        if media_type == "video":
            await message.answer_video(source, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
            return True
        if media_type == "animation":
            await message.answer_animation(source, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
            return True
        await message.answer_document(source, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except TelegramBadRequest:
        return False
