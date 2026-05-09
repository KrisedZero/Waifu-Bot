from __future__ import annotations

import asyncpg


def _sort_expr(lang: str) -> str:
    field = "name_en" if lang == "en" else "name_ru"
    return f"""
        CASE
            WHEN COALESCE({field}, name_ru) ~ '^[0-9]' THEN 0
            WHEN COALESCE({field}, name_ru) ~ '^[A-Za-z]' THEN 1
            WHEN COALESCE({field}, name_ru) ~ '^[А-Яа-яЁё]' THEN 2
            ELSE 3
        END,
        lower(COALESCE({field}, name_ru)),
        sort_order,
        id
    """


async def count_categories(pool: asyncpg.Pool) -> int:
    row = await pool.fetchrow("SELECT COUNT(*) AS c FROM categories")
    return int(row["c"]) if row else 0


async def get_category(pool: asyncpg.Pool, category_id: int):
    return await pool.fetchrow(
        """
        SELECT
            id,
            name_ru,
            name_en,
            parent_id,
            node_type,
            is_active,
            sort_order,
            created_at,
            updated_at
        FROM categories
        WHERE id = $1
        """,
        category_id,
    )


async def get_root_categories(pool: asyncpg.Pool, lang: str = "ru"):
    return await pool.fetch(
        f"""
        SELECT
            id,
            name_ru,
            name_en,
            parent_id,
            node_type,
            is_active,
            sort_order
        FROM categories
        WHERE parent_id IS NULL
        ORDER BY {_sort_expr(lang)}
        """,
    )


async def get_child_categories(pool: asyncpg.Pool, parent_id: int, lang: str = "ru"):
    return await pool.fetch(
        f"""
        SELECT
            id,
            name_ru,
            name_en,
            parent_id,
            node_type,
            is_active,
            sort_order
        FROM categories
        WHERE parent_id = $1
        ORDER BY {_sort_expr(lang)}
        """,
        parent_id,
    )


async def search_categories(pool: asyncpg.Pool, query: str, lang: str = "ru", limit: int = 15):
    q = f"%{query.strip()}%"
    return await pool.fetch(
        f"""
        SELECT
            id,
            name_ru,
            name_en,
            parent_id,
            node_type,
            is_active,
            sort_order
        FROM categories
        WHERE name_ru ILIKE $1 OR name_en ILIKE $1
        ORDER BY {_sort_expr(lang)}
        LIMIT $2
        """,
        q,
        limit,
    )


async def get_children_count(pool: asyncpg.Pool, category_id: int) -> int:
    row = await pool.fetchrow(
        """
        SELECT COUNT(*) AS c
        FROM categories
        WHERE parent_id = $1
        """,
        category_id,
    )
    return int(row["c"]) if row else 0


async def get_descendant_stats(pool: asyncpg.Pool, category_id: int) -> dict[str, int]:
    row = await pool.fetchrow(
        """
        WITH RECURSIVE subtree AS (
            SELECT id
            FROM categories
            WHERE id = $1
            UNION ALL
            SELECT c.id
            FROM categories c
            JOIN subtree s ON c.parent_id = s.id
        )
        SELECT
            COUNT(*) AS categories_count,
            COALESCE((
                SELECT COUNT(*)
                FROM waifus w
                WHERE w.category_id IN (SELECT id FROM subtree)
            ), 0) AS waifus_count
        FROM subtree
        """,
        category_id,
    )
    return {
        "categories_count": int(row["categories_count"]) if row else 0,
        "waifus_count": int(row["waifus_count"]) if row else 0,
    }


async def create_category(
    pool: asyncpg.Pool,
    *,
    name_ru: str,
    name_en: str,
    parent_id: int | None,
    node_type: str,
    sort_order: int = 0,
) -> int:
    row = await pool.fetchrow(
        """
        INSERT INTO categories (name_ru, name_en, parent_id, node_type, sort_order, is_active)
        VALUES ($1, $2, $3, $4, $5, TRUE)
        RETURNING id
        """,
        name_ru,
        name_en,
        parent_id,
        node_type,
        sort_order,
    )
    return int(row["id"])


async def update_category(
    pool: asyncpg.Pool,
    *,
    category_id: int,
    name_ru: str,
    name_en: str,
    parent_id: int | None,
    node_type: str,
    is_active: bool,
    sort_order: int,
) -> None:
    await pool.execute(
        """
        UPDATE categories
        SET name_ru = $2,
            name_en = $3,
            parent_id = $4,
            node_type = $5,
            is_active = $6,
            sort_order = $7,
            updated_at = NOW()
        WHERE id = $1
        """,
        category_id,
        name_ru,
        name_en,
        parent_id,
        node_type,
        is_active,
        sort_order,
    )


async def delete_category_tree(pool: asyncpg.Pool, category_id: int) -> int:
    rows = await pool.fetch(
        """
        WITH RECURSIVE subtree AS (
            SELECT id
            FROM categories
            WHERE id = $1
            UNION ALL
            SELECT c.id
            FROM categories c
            JOIN subtree s ON c.parent_id = s.id
        )
        SELECT id FROM subtree
        """,
        category_id,
    )
    ids = [int(r["id"]) for r in rows]
    if not ids:
        return 0

    await pool.execute(
        """
        DELETE FROM waifu_media
        WHERE waifu_id IN (
            SELECT id FROM waifus WHERE category_id = ANY($1::bigint[])
        )
        """,
        ids,
    )
    await pool.execute(
        "DELETE FROM waifus WHERE category_id = ANY($1::bigint[])",
        ids,
    )
    await pool.execute(
        "DELETE FROM categories WHERE id = ANY($1::bigint[])",
        ids,
    )
    return len(ids)