from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from aiogram import Bot

MEDIA_ROOT = Path(__file__).resolve().parents[3] / "media" / "waifus"


def _normalize_media_type(media_type: str | None) -> str | None:
    if not media_type:
        return None
    media_type = media_type.lower().strip()
    if media_type == "gif":
        return "animation"
    return media_type


def _guess_suffix(remote_path: str | None, media_type: str | None) -> str:
    suffix = Path(remote_path or "").suffix
    if suffix:
        return suffix
    normalized = _normalize_media_type(media_type)
    return {
        "photo": ".jpg",
        "video": ".mp4",
        "animation": ".mp4",
        "document": ".bin",
    }.get(normalized, ".bin")


async def store_telegram_media(
    bot: Bot,
    file_id: str,
    *,
    media_type: str | None = None,
    waifu_id: int | None = None,
) -> str:
    """Download Telegram media to local storage and return a filesystem path."""
    file = await bot.get_file(file_id)
    suffix = _guess_suffix(file.file_path, media_type)

    parts = [MEDIA_ROOT]
    if waifu_id is not None:
        parts.append(Path(str(waifu_id)))
    else:
        parts.append(Path("pending"))
    target_dir = Path(*parts)
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / f"{uuid4().hex}{suffix}"
    await bot.download_file(file.file_path, destination=target_path)
    return str(target_path)


async def migrate_existing_waifu_media(bot: Bot, pool) -> int:
    """Convert legacy Telegram file_id references to local paths."""
    rows = await pool.fetch(
        """
        SELECT id, waifu_id, media_type, file_id
        FROM waifu_media
        WHERE file_id IS NOT NULL AND file_id <> ''
        ORDER BY id
        """
    )

    migrated = 0
    for row in rows:
        current_ref = str(row["file_id"])
        if Path(current_ref).exists():
            continue

        try:
            local_path = await store_telegram_media(
                bot,
                current_ref,
                media_type=row["media_type"],
                waifu_id=int(row["waifu_id"]),
            )
        except Exception:
            continue

        await pool.execute(
            """
            UPDATE waifu_media
            SET file_id = $2
            WHERE id = $1
            """,
            row["id"],
            local_path,
        )
        migrated += 1

    return migrated
