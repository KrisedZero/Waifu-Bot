from __future__ import annotations

import asyncio

import asyncpg

ALLOWED_MEDIA_TYPES = {"photo", "video", "animation", "document"}
_SCHEMA_READY = False
_SCHEMA_LOCK = asyncio.Lock()


async def ensure_waifu_schema_ready(pool: asyncpg.Pool) -> None:
    global _SCHEMA_READY

    if _SCHEMA_READY:
        return

    async with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return

        async with pool.acquire() as conn:
            await conn.execute(
                """
                ALTER TABLE waifus
                ADD COLUMN IF NOT EXISTS alias TEXT
                """
            )
            await conn.execute(
                """
                ALTER TABLE waifus
                ADD COLUMN IF NOT EXISTS alias_ru TEXT
                """
            )
            await conn.execute(
                """
                ALTER TABLE waifus
                ADD COLUMN IF NOT EXISTS alias_en TEXT
                """
            )
            await conn.execute(
                """
                ALTER TABLE waifus
                ADD COLUMN IF NOT EXISTS age TEXT
                """
            )
            await conn.execute(
                """
                ALTER TABLE waifus
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ
                """
            )
            await conn.execute(
                """
                ALTER TABLE waifus
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ
                """
            )
            await conn.execute(
                """
                UPDATE waifus
                SET created_at = COALESCE(created_at, NOW()),
                    updated_at = COALESCE(updated_at, created_at, NOW())
                """
            )
            await conn.execute(
                """
                ALTER TABLE waifus
                ALTER COLUMN created_at SET DEFAULT NOW()
                """
            )
            await conn.execute(
                """
                ALTER TABLE waifus
                ALTER COLUMN updated_at SET DEFAULT NOW()
                """
            )

        _SCHEMA_READY = True


def _name_expr(lang: str) -> str:
    return "COALESCE(w.name_en, w.name_ru)" if lang == "en" else "COALESCE(w.name_ru, w.name_en)"


def _waifu_select_columns() -> str:
    return """
            w.id,
            w.category_id,
            w.name_ru,
            w.name_en,
            w.rarity,
            w.gender,
            w.age,
            w.alias,
            w.alias_ru,
            w.alias_en,
            COALESCE(w.alias_ru, w.alias_en, w.alias) AS alias,
            w.is_active,
            w.created_at,
            w.updated_at,
            c.name_ru AS category_name_ru,
            c.name_en AS category_name_en,
            ct.path_key AS category_path_key,
            ct.path_name_ru AS category_path_ru,
            ct.path_name_en AS category_path_en,
            (
                SELECT wm.media_type
                FROM waifu_media wm
                WHERE wm.waifu_id = w.id AND wm.is_primary = TRUE
                ORDER BY wm.sort_order, wm.id
                LIMIT 1
            ) AS media_type,
            (
                SELECT wm.file_id
                FROM waifu_media wm
                WHERE wm.waifu_id = w.id AND wm.is_primary = TRUE
                ORDER BY wm.sort_order, wm.id
                LIMIT 1
            ) AS file_id
    """


def _sort_sql(lang: str) -> str:
    name_expr = _name_expr(lang)
    return f"""
        COALESCE(ct.path_key, 'zzzzzz'),
        CASE
            WHEN {name_expr} ~ '^[0-9]' THEN 0
            WHEN {name_expr} ~ '^[A-Za-z]' THEN 1
            WHEN {name_expr} ~ '^[А-Яа-яЁё]' THEN 2
            ELSE 3
        END,
        lower({name_expr}),
        w.rarity,
        w.id
    """


async def count_waifus(pool: asyncpg.Pool) -> int:
    await ensure_waifu_schema_ready(pool)
    row = await pool.fetchrow("SELECT COUNT(*) AS c FROM waifus")
    return int(row["c"]) if row else 0


async def list_waifus(pool: asyncpg.Pool, *, lang: str = "ru", limit: int = 20, offset: int = 0):
    await ensure_waifu_schema_ready(pool)
    return await pool.fetch(
        f"""
        WITH RECURSIVE cat_tree AS (
            SELECT
                c.id,
                c.parent_id,
                c.name_ru,
                c.name_en,
                c.sort_order,
                LPAD(COALESCE(c.sort_order, 0)::text, 6, '0') || ':' || LPAD(c.id::text, 12, '0') AS path_key,
                COALESCE(c.name_ru, c.name_en, '—') AS path_name_ru,
                COALESCE(c.name_en, c.name_ru, '—') AS path_name_en
            FROM categories c
            WHERE c.parent_id IS NULL
            UNION ALL
            SELECT
                c.id,
                c.parent_id,
                c.name_ru,
                c.name_en,
                c.sort_order,
                ct.path_key || '/' || LPAD(COALESCE(c.sort_order, 0)::text, 6, '0') || ':' || LPAD(c.id::text, 12, '0'),
                ct.path_name_ru || ' / ' || COALESCE(c.name_ru, c.name_en, '—'),
                ct.path_name_en || ' / ' || COALESCE(c.name_en, c.name_ru, '—')
            FROM categories c
            JOIN cat_tree ct ON c.parent_id = ct.id
        )
        SELECT
            {_waifu_select_columns()}
        FROM waifus w
        LEFT JOIN categories c ON c.id = w.category_id
        LEFT JOIN cat_tree ct ON ct.id = w.category_id
        ORDER BY {_sort_sql(lang)}
        LIMIT $1 OFFSET $2
        """,
        limit,
        offset,
    )


async def search_waifus(pool: asyncpg.Pool, query: str, *, lang: str = "ru", limit: int = 20):
    await ensure_waifu_schema_ready(pool)
    q = f"%{query.strip()}%"
    return await pool.fetch(
        f"""
        WITH RECURSIVE cat_tree AS (
            SELECT
                c.id,
                c.parent_id,
                c.name_ru,
                c.name_en,
                c.sort_order,
                LPAD(COALESCE(c.sort_order, 0)::text, 6, '0') || ':' || LPAD(c.id::text, 12, '0') AS path_key,
                COALESCE(c.name_ru, c.name_en, '—') AS path_name_ru,
                COALESCE(c.name_en, c.name_ru, '—') AS path_name_en
            FROM categories c
            WHERE c.parent_id IS NULL
            UNION ALL
            SELECT
                c.id,
                c.parent_id,
                c.name_ru,
                c.name_en,
                c.sort_order,
                ct.path_key || '/' || LPAD(COALESCE(c.sort_order, 0)::text, 6, '0') || ':' || LPAD(c.id::text, 12, '0'),
                ct.path_name_ru || ' / ' || COALESCE(c.name_ru, c.name_en, '—'),
                ct.path_name_en || ' / ' || COALESCE(c.name_en, c.name_ru, '—')
            FROM categories c
            JOIN cat_tree ct ON c.parent_id = ct.id
        )
        SELECT
            {_waifu_select_columns()}
        FROM waifus w
        LEFT JOIN categories c ON c.id = w.category_id
        LEFT JOIN cat_tree ct ON ct.id = w.category_id
        WHERE w.name_ru ILIKE $1
           OR w.name_en ILIKE $1
           OR COALESCE(w.alias_ru, '') ILIKE $1
           OR COALESCE(w.alias_en, '') ILIKE $1
           OR COALESCE(w.alias, '') ILIKE $1
           OR c.name_ru ILIKE $1
           OR c.name_en ILIKE $1
        ORDER BY {_sort_sql(lang)}
        LIMIT $2
        """,
        q,
        limit,
    )


async def get_waifu(pool: asyncpg.Pool, waifu_id: int) -> asyncpg.Record | None:
    await ensure_waifu_schema_ready(pool)
    return await pool.fetchrow(
        f"""
        WITH RECURSIVE cat_tree AS (
            SELECT
                c.id,
                c.parent_id,
                c.name_ru,
                c.name_en,
                c.sort_order,
                LPAD(COALESCE(c.sort_order, 0)::text, 6, '0') || ':' || LPAD(c.id::text, 12, '0') AS path_key,
                COALESCE(c.name_ru, c.name_en, '—') AS path_name_ru,
                COALESCE(c.name_en, c.name_ru, '—') AS path_name_en
            FROM categories c
            WHERE c.parent_id IS NULL
            UNION ALL
            SELECT
                c.id,
                c.parent_id,
                c.name_ru,
                c.name_en,
                c.sort_order,
                ct.path_key || '/' || LPAD(COALESCE(c.sort_order, 0)::text, 6, '0') || ':' || LPAD(c.id::text, 12, '0'),
                ct.path_name_ru || ' / ' || COALESCE(c.name_ru, c.name_en, '—'),
                ct.path_name_en || ' / ' || COALESCE(c.name_en, c.name_ru, '—')
            FROM categories c
            JOIN cat_tree ct ON c.parent_id = ct.id
        )
        SELECT
            {_waifu_select_columns()}
        FROM waifus w
        LEFT JOIN categories c ON c.id = w.category_id
        LEFT JOIN cat_tree ct ON ct.id = w.category_id
        WHERE w.id = $1
        """,
        waifu_id,
    )


async def create_waifu(
    pool: asyncpg.Pool,
    *,
    category_id: int,
    name_ru: str,
    name_en: str,
    rarity: str,
    gender: str | None,
    age: str | None = None,
    alias_ru: str | None = None,
    alias_en: str | None = None,
    alias: str | None = None,
) -> int:
    alias_fallback = alias_ru or alias_en or alias
    row = await pool.fetchrow(
        """
        INSERT INTO waifus (category_id, name_ru, name_en, alias, alias_ru, alias_en, age, rarity, gender, is_active)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, TRUE)
        RETURNING id
        """,
        category_id,
        name_ru,
        name_en,
        alias_fallback,
        alias_ru,
        alias_en,
        age,
        rarity,
        gender,
    )
    return int(row["id"])


async def update_waifu(
    pool: asyncpg.Pool,
    *,
    waifu_id: int,
    category_id: int,
    name_ru: str,
    name_en: str,
    rarity: str,
    gender: str | None,
    age: str | None,
    alias_ru: str | None = None,
    alias_en: str | None = None,
    alias: str | None = None,
    is_active: bool,
) -> None:
    alias_fallback = alias_ru or alias_en or alias
    await pool.execute(
        """
        UPDATE waifus
        SET category_id = $2,
            name_ru = $3,
            name_en = $4,
            alias = $5,
            alias_ru = $6,
            alias_en = $7,
            age = $8,
            rarity = $9,
            gender = $10,
            is_active = $11,
            updated_at = NOW()
        WHERE id = $1
        """,
        waifu_id,
        category_id,
        name_ru,
        name_en,
        alias_fallback,
        alias_ru,
        alias_en,
        age,
        rarity,
        gender,
        is_active,
    )


async def delete_waifu(pool: asyncpg.Pool, waifu_id: int) -> None:
    await ensure_waifu_schema_ready(pool)
    await pool.execute("DELETE FROM waifu_media WHERE waifu_id = $1", waifu_id)
    await pool.execute("DELETE FROM waifus WHERE id = $1", waifu_id)


async def set_waifu_media(
    pool: asyncpg.Pool,
    *,
    waifu_id: int,
    media_type: str,
    file_id: str,
    is_primary: bool = True,
    sort_order: int = 1,
) -> None:
    normalized_type = "animation" if media_type == "gif" else media_type
    if normalized_type not in ALLOWED_MEDIA_TYPES:
        raise ValueError(f"Unsupported media_type: {media_type}")

    if is_primary:
        await pool.execute(
            "DELETE FROM waifu_media WHERE waifu_id = $1 AND is_primary = TRUE",
            waifu_id,
        )

    await pool.execute(
        """
        INSERT INTO waifu_media (waifu_id, media_type, file_id, is_primary, sort_order)
        VALUES ($1, $2, $3, $4, $5)
        """,
        waifu_id,
        normalized_type,
        file_id,
        is_primary,
        sort_order,
    )


async def get_primary_media(pool: asyncpg.Pool, waifu_id: int) -> asyncpg.Record | None:
    await ensure_waifu_schema_ready(pool)
    return await pool.fetchrow(
        """
        SELECT media_type, file_id
        FROM waifu_media
        WHERE waifu_id = $1 AND is_primary = TRUE
        ORDER BY sort_order, id
        LIMIT 1
        """,
        waifu_id,
    )
