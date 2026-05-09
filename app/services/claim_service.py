import asyncio
import re

from app.database.connection import get_pool
from app.services.spawn_service import get_active_spawn, clear_spawn
from app.services.user_service import add_waifu_to_user
from app.services.profile_ui_service import calculate_level


_chat_locks: dict[int, asyncio.Lock] = {}
_chat_locks_guard = asyncio.Lock()


async def _get_chat_lock(chat_id: int) -> asyncio.Lock:
    async with _chat_locks_guard:
        lock = _chat_locks.get(chat_id)
        if lock is None:
            lock = asyncio.Lock()
            _chat_locks[chat_id] = lock
        return lock


def normalize_text(text: str) -> list[str]:
    cleaned = re.sub(r"[^\w\s]", "", text.casefold())
    return cleaned.split()


def waifu_matches_text(waifu: dict, text: str) -> bool:
    words = normalize_text(text)

    if len(words) > 3:
        return False

    words_set = set(words)

    for key in ("name_en", "name_ru"):
        value = waifu.get(key)
        if not value:
            continue

        name_parts = normalize_text(value)

        if len(name_parts) == 1:
            if name_parts[0] in words_set:
                return True
            continue

        for part in name_parts:
            if len(part) >= 2 and part in words_set:
                return True

    return False


async def try_claim_waifu(chat_id: int, user_id: int, text: str) -> tuple[bool, dict | None, dict | None]:
    lock = await _get_chat_lock(chat_id)

    async with lock:
        active_spawn = get_active_spawn(chat_id)
        if not active_spawn:
            return False, None, None

        waifu = active_spawn["waifu"]

        if not waifu_matches_text(waifu, text):
            return False, None, None

        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COUNT(*) AS total_claims
                FROM user_claims
                WHERE user_id = $1
                """,
                user_id,
            )

        previous_claims = int(row["total_claims"] or 0) if row else 0
        previous_level = int(calculate_level(previous_claims)["level"])
        new_level = int(calculate_level(previous_claims + 1)["level"])

        await add_waifu_to_user(user_id, waifu["id"], chat_id)
        clear_spawn(chat_id)
        return True, waifu, {
            "previous_level": previous_level,
            "new_level": new_level,
        }
