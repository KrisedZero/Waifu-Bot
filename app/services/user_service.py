from app.database.connection import get_pool
from app.services.cache_service import (
    is_known_user,
    mark_known_user,
    get_cached_user_language,
    set_cached_user_language,
)


async def create_user_if_not_exists(user_id: int, language: str, username: str | None = None):
    if is_known_user(user_id):
        return

    pool = get_pool()

    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, username, language)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO NOTHING
        """, user_id, username, language)

    mark_known_user(user_id)


async def get_user_language(user_id: int):
    cached = get_cached_user_language(user_id)
    if cached:
        return cached

    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT language
            FROM users
            WHERE user_id = $1
        """, user_id)

    if row and row["language"]:
        set_cached_user_language(user_id, row["language"])
        mark_known_user(user_id)
        return row["language"]

    return "ru"


async def set_user_language(user_id: int, language: str):
    pool = get_pool()

    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE users
            SET language = $2
            WHERE user_id = $1
        """, user_id, language)

    set_cached_user_language(user_id, language)
    mark_known_user(user_id)


async def add_waifu_to_user(user_id: int, waifu_id: int, chat_id: int | None = None):
    pool = get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("""
                INSERT INTO user_waifus (user_id, waifu_id, amount)
                VALUES ($1, $2, 1)
                ON CONFLICT (user_id, waifu_id)
                DO UPDATE SET amount = user_waifus.amount + 1
            """, user_id, waifu_id)

            if chat_id is not None:
                await conn.execute("""
                    INSERT INTO user_claims (user_id, waifu_id, chat_id)
                    VALUES ($1, $2, $3)
                """, user_id, waifu_id, chat_id)


async def get_user_waifus(user_id: int):
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                w.id AS id,
                w.name_en,
                w.name_ru,
                w.rarity,
                w.category_id,
                w.gender,
                w.is_active,
                w.age,
                w.alias,
                w.alias_ru,
                w.alias_en,
                COALESCE(w.alias_ru, w.alias_en, w.alias) AS alias,
                uw.amount
            FROM user_waifus uw
            JOIN waifus w ON w.id = uw.waifu_id
            WHERE uw.user_id = $1
            ORDER BY w.rarity, w.id
        """, user_id)

    return rows


async def get_user_favorite_waifu(user_id: int):
    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                w.id,
                w.name_en,
                w.name_ru,
                w.rarity,
                w.category_id,
                w.gender,
                w.is_active,
                w.age,
                w.alias,
                w.alias_ru,
                w.alias_en,
                COALESCE(w.alias_ru, w.alias_en, w.alias) AS alias
            FROM users u
            LEFT JOIN waifus w ON w.id = u.favorite_waifu_id
            WHERE u.user_id = $1
        """, user_id)

    if row and row["id"]:
        return row

    return None


async def set_user_favorite_waifu(user_id: int, waifu_id: int):
    pool = get_pool()

    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE users
            SET favorite_waifu_id = $2
            WHERE user_id = $1
        """, user_id, waifu_id)


async def get_user_favorite_category(user_id: int):
    pool = get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT favorite_category_id
            FROM users
            WHERE user_id = $1
        """, user_id)

    if row and row['favorite_category_id'] is not None:
        return row['favorite_category_id']

    return None


async def set_user_favorite_category(user_id: int, category_id: int):
    pool = get_pool()

    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE users
            SET favorite_category_id = $2
            WHERE user_id = $1
        """, user_id, category_id)
