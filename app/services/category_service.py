from __future__ import annotations

import re
from typing import Any

from app.database.connection import get_pool
from app.services.cache_invalidation import invalidate_category_catalog
from app.services.cache_service import (
    get_cached_category_root_map,
    set_cached_category_root_map,
    clear_category_root_map_cache,
    get_cached_root_categories,
    set_cached_root_categories,
    clear_root_categories_cache,
    get_cached_category_availability_map,
    set_cached_category_availability_map,
    clear_category_availability_cache,
)
from app.services.catalog_state_service import ensure_catalog_revision_current


_category_meta_cache: list[dict[str, Any]] | None = None


def _row_to_dict(row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").casefold()).strip()


def _category_display_name(category: dict[str, Any], lang: str = "ru") -> str:
    if lang == "ru":
        return category.get("name_ru") or category.get("name_en") or "—"
    return category.get("name_en") or category.get("name_ru") or "—"


def _matches_query(category: dict[str, Any], query: str) -> bool:
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return False

    haystack = _normalize_text(
        " ".join(
            str(part or "")
            for part in (
                category.get("name_ru"),
                category.get("name_en"),
            )
        )
    )

    tokens = [token for token in normalized_query.split(" ") if token]
    return all(token in haystack for token in tokens)


async def _load_all_categories() -> list[dict[str, Any]]:
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name_en, name_ru, parent_id, is_active
            FROM categories
            ORDER BY LOWER(COALESCE(name_ru, name_en)), id
            """
        )

    return [_row_to_dict(row) for row in rows]


async def _get_all_categories_cached() -> list[dict[str, Any]]:
    global _category_meta_cache
    if _category_meta_cache is None:
        _category_meta_cache = await _load_all_categories()
    return [item.copy() for item in _category_meta_cache]


def _build_root_map(categories: list[dict[str, Any]]) -> dict[int, int]:
    parent_by_id = {cat["id"]: cat["parent_id"] for cat in categories}
    root_map: dict[int, int] = {}

    def find_root(category_id: int, stack: set[int] | None = None) -> int:
        if category_id in root_map:
            return root_map[category_id]

        if stack is None:
            stack = set()

        if category_id in stack:
            return category_id

        stack.add(category_id)

        parent_id = parent_by_id.get(category_id)
        if parent_id is None:
            root = category_id
        else:
            root = find_root(parent_id, stack)

        root_map[category_id] = root
        stack.discard(category_id)
        return root

    for category_id in parent_by_id:
        find_root(category_id)

    return root_map


def _build_availability_map(categories: list[dict[str, Any]]) -> dict[int, bool]:
    meta_by_id = {cat["id"]: cat for cat in categories}
    availability: dict[int, bool] = {}

    def is_available(category_id: int, stack: set[int] | None = None) -> bool:
        if category_id in availability:
            return availability[category_id]

        if stack is None:
            stack = set()

        if category_id in stack:
            availability[category_id] = False
            return False

        stack.add(category_id)
        meta = meta_by_id.get(category_id)
        if meta is None:
            availability[category_id] = True
            stack.discard(category_id)
            return True

        parent_id = meta.get("parent_id")
        current = bool(meta.get("is_active", True))
        if current and parent_id is not None:
            current = is_available(parent_id, stack)

        availability[category_id] = current
        stack.discard(category_id)
        return current

    for category_id in meta_by_id:
        is_available(category_id)

    return availability


async def get_category_path(category_id: int | None):
    """
    Возвращает путь категорий от корня к листу.
    """
    if not category_id:
        return []

    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH RECURSIVE cat_path AS (
                SELECT id, name_en, name_ru, parent_id, 1 AS depth
                FROM categories
                WHERE id = $1

                UNION ALL

                SELECT c.id, c.name_en, c.name_ru, c.parent_id, cp.depth + 1
                FROM categories c
                JOIN cat_path cp ON cp.parent_id = c.id
            )
            SELECT id, name_en, name_ru, parent_id, depth
            FROM cat_path
            ORDER BY depth DESC
            """,
            category_id,
        )

    return [_row_to_dict(row) for row in rows]


async def get_category_descendant_ids(category_id: int | None) -> list[int]:
    if not category_id:
        return []

    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH RECURSIVE cat_tree AS (
                SELECT id
                FROM categories
                WHERE id = $1

                UNION ALL

                SELECT c.id
                FROM categories c
                JOIN cat_tree ct ON c.parent_id = ct.id
            )
            SELECT id
            FROM cat_tree
            ORDER BY id
            """,
            category_id,
        )

    return [int(row["id"]) for row in rows]


async def search_categories(query: str, lang: str = "ru") -> list[dict[str, Any]]:
    query = (query or "").strip()
    if not query:
        return []

    categories = await _get_all_categories_cached()
    matched = [
        category
        for category in categories
        if category.get("is_active", True) and _matches_query(category, query)
    ]
    matched.sort(
        key=lambda cat: (
            _category_display_name(cat, lang).casefold(),
            int(cat.get("id") or 0),
        )
    )
    return [item.copy() for item in matched]


async def get_category_root_map() -> dict[int, int]:
    await ensure_catalog_revision_current()

    cached = get_cached_category_root_map()
    if cached is not None:
        return cached

    categories = await _get_all_categories_cached()
    root_map = _build_root_map(categories)
    set_cached_category_root_map(root_map)
    return root_map.copy()


async def get_category_availability_map() -> dict[int, bool]:
    await ensure_catalog_revision_current()

    cached = get_cached_category_availability_map()
    if cached is not None:
        return cached

    categories = await _get_all_categories_cached()
    availability_map = _build_availability_map(categories)
    set_cached_category_availability_map(availability_map)
    return availability_map.copy()


async def get_root_category_id(category_id: int | None):
    if not category_id:
        return None

    root_map = await get_category_root_map()
    return root_map.get(category_id)


async def get_root_categories():
    await ensure_catalog_revision_current()

    cached = get_cached_root_categories()
    if cached is not None:
        return cached

    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name_ru, name_en, parent_id
            FROM categories
            WHERE parent_id IS NULL
              AND is_active = TRUE
            ORDER BY LOWER(COALESCE(name_ru, name_en)), id
            """
        )

    root_categories = [_row_to_dict(row) for row in rows]
    set_cached_root_categories(root_categories)
    return [item.copy() for item in root_categories]


def clear_category_meta_cache() -> None:
    global _category_meta_cache
    _category_meta_cache = None


async def clear_category_caches() -> None:
    invalidate_category_catalog()
    clear_category_meta_cache()
    clear_category_root_map_cache()
    clear_root_categories_cache()
    clear_category_availability_cache()
