from __future__ import annotations

import random
from typing import Any

from app.database.connection import get_pool
from app.services.cache_service import (
    get_cached_all_waifus,
    set_cached_all_waifus,
    get_cached_waifus_by_rarity,
    set_cached_waifus_by_rarity,
    get_cached_category_root_map,
    set_cached_category_root_map,
    get_cached_blocked_roots,
    set_cached_blocked_roots,
)
from app.services.category_service import get_category_availability_map
from app.services.catalog_state_service import ensure_catalog_revision_current


def _row_to_dict(row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


async def _load_all_waifus() -> list[dict[str, Any]]:
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                w.id,
                w.name_en,
                w.name_ru,
                w.rarity,
                w.category_id,
                w.gender,
                w.is_active,
                w.age,
                w.alias
            FROM waifus w
        """
        )

    waifus = [_row_to_dict(row) for row in rows]
    set_cached_all_waifus(waifus)
    return waifus


async def _load_waifus_by_rarity(rarity: str) -> list[dict[str, Any]]:
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                w.id,
                w.name_en,
                w.name_ru,
                w.rarity,
                w.category_id,
                w.gender,
                w.is_active,
                w.age,
                w.alias
            FROM waifus w
            WHERE w.rarity = $1
            """,
            rarity,
        )

    waifus = [_row_to_dict(row) for row in rows]
    set_cached_waifus_by_rarity(rarity, waifus)
    return waifus


async def _load_category_root_map() -> dict[int, int]:
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, parent_id
            FROM categories
            """
        )

    parent_by_id = {row["id"]: row["parent_id"] for row in rows}
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

    set_cached_category_root_map(root_map)
    return root_map


async def _load_blocked_roots(chat_id: int) -> set[int]:
    pool = get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT root_category_id
            FROM chat_category_blocks
            WHERE chat_id = $1
            """,
            chat_id,
        )

    blocked = {row["root_category_id"] for row in rows}
    set_cached_blocked_roots(chat_id, blocked)
    return blocked


async def _get_category_root_map() -> dict[int, int]:
    cached = get_cached_category_root_map()
    if cached is not None:
        return cached
    return await _load_category_root_map()


async def _get_blocked_roots(chat_id: int) -> set[int]:
    cached = get_cached_blocked_roots(chat_id)
    if cached is not None:
        return cached
    return await _load_blocked_roots(chat_id)


async def _get_all_waifus_cached() -> list[dict[str, Any]]:
    cached = get_cached_all_waifus()
    if cached is not None:
        return cached
    return await _load_all_waifus()


async def _get_waifus_by_rarity_cached(rarity: str) -> list[dict[str, Any]]:
    cached = get_cached_waifus_by_rarity(rarity)
    if cached is not None:
        return cached
    return await _load_waifus_by_rarity(rarity)


async def _category_is_available(category_id: int | None) -> bool:
    if category_id is None:
        return True
    availability_map = await get_category_availability_map()
    return availability_map.get(category_id, True)


def _is_allowed(
    waifu: dict[str, Any],
    blocked_roots: set[int],
    category_root_map: dict[int, int],
    availability_map: dict[int, bool],
) -> bool:
    category_id = waifu.get("category_id")
    if not waifu.get("is_active", True):
        return False
    if category_id is None:
        return True

    if not availability_map.get(category_id, True):
        return False

    root_id = category_root_map.get(category_id)
    if root_id is None:
        return True

    return root_id not in blocked_roots and availability_map.get(root_id, True)


async def get_random_waifu():
    await ensure_catalog_revision_current()
    waifus = await _get_all_waifus_cached()
    if not waifus:
        return None
    return random.choice(waifus)


async def get_random_waifu_by_rarity(rarity: str):
    await ensure_catalog_revision_current()
    waifus = await _get_waifus_by_rarity_cached(rarity)
    if not waifus:
        return None
    return random.choice(waifus)


async def get_random_allowed_waifu_by_rarity(chat_id: int, rarity: str):
    await ensure_catalog_revision_current()
    waifus = await _get_waifus_by_rarity_cached(rarity)
    if not waifus:
        return None

    blocked_roots = await _get_blocked_roots(chat_id)
    category_root_map = await _get_category_root_map()
    availability_map = await get_category_availability_map()

    candidates = [
        waifu for waifu in waifus
        if _is_allowed(waifu, blocked_roots, category_root_map, availability_map)
    ]

    if not candidates:
        return None

    return random.choice(candidates)


async def get_random_allowed_waifu(chat_id: int):
    await ensure_catalog_revision_current()
    waifus = await _get_all_waifus_cached()
    if not waifus:
        return None

    blocked_roots = await _get_blocked_roots(chat_id)
    category_root_map = await _get_category_root_map()
    availability_map = await get_category_availability_map()

    candidates = [
        waifu for waifu in waifus
        if _is_allowed(waifu, blocked_roots, category_root_map, availability_map)
    ]

    if not candidates:
        return None

    return random.choice(candidates)
