from app.database.connection import get_pool
from app.services.cache_service import (
    has_cached_chat_language,
    has_cached_chat_pity,
    get_cached_chat_language,
    get_cached_chat_pity,
    set_cached_chat_language,
    set_cached_chat_pity,
)


async def ensure_chat_settings(chat_id: int, default_language: str = "ru") -> None:
    if has_cached_chat_language(chat_id) and has_cached_chat_pity(chat_id):
        return

    pool = get_pool()

    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO chat_settings (chat_id, language)
            VALUES ($1, $2)
            ON CONFLICT (chat_id) DO UPDATE
            SET language = COALESCE(chat_settings.language, EXCLUDED.language)
        """, chat_id, default_language)

        row = await conn.fetchrow("""
            SELECT language, pity_epic, pity_legendary, pity_unique
            FROM chat_settings
            WHERE chat_id = $1
        """, chat_id)

    if row:
        language = row["language"] or default_language
        set_cached_chat_language(chat_id, language)
        set_cached_chat_pity(
            chat_id,
            row["pity_epic"] or 0,
            row["pity_legendary"] or 0,
            row["pity_unique"] or 0,
        )


async def get_chat_language(chat_id: int) -> str:
    cached = get_cached_chat_language(chat_id)
    if cached:
        return cached

    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT language
            FROM chat_settings
            WHERE chat_id = $1
        """, chat_id)

    if row and row["language"]:
        set_cached_chat_language(chat_id, row["language"])
        return row["language"]

    return "ru"


async def set_chat_language(chat_id: int, language: str) -> None:
    pool = get_pool()

    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO chat_settings (chat_id, language)
            VALUES ($1, $2)
            ON CONFLICT (chat_id)
            DO UPDATE SET language = EXCLUDED.language
        """, chat_id, language)

    set_cached_chat_language(chat_id, language)


async def get_chat_pity(chat_id: int):
    cached = get_cached_chat_pity(chat_id)
    if cached:
        return cached

    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT pity_epic, pity_legendary, pity_unique
            FROM chat_settings
            WHERE chat_id = $1
        """, chat_id)

    if row:
        pity = {
            "pity_epic": row["pity_epic"],
            "pity_legendary": row["pity_legendary"],
            "pity_unique": row["pity_unique"],
        }
        set_cached_chat_pity(
            chat_id,
            pity["pity_epic"],
            pity["pity_legendary"],
            pity["pity_unique"],
        )
        return pity

    return {
        "pity_epic": 0,
        "pity_legendary": 0,
        "pity_unique": 0,
    }


async def update_chat_pity(
    chat_id: int,
    pity_epic: int,
    pity_legendary: int,
    pity_unique: int,
) -> None:
    pool = get_pool()

    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE chat_settings
            SET pity_epic = $2,
                pity_legendary = $3,
                pity_unique = $4
            WHERE chat_id = $1
        """, chat_id, pity_epic, pity_legendary, pity_unique)

    set_cached_chat_pity(chat_id, pity_epic, pity_legendary, pity_unique)