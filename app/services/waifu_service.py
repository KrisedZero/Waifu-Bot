from __future__ import annotations

import random
import re
from typing import Any

from app.database.connection import get_pool
from app.services.cache_service import get_cached_all_waifus, set_cached_all_waifus
from app.services.cache_invalidation import invalidate_waifu_catalog
from app.services.catalog_state_service import ensure_catalog_revision_current


RARITY_ORDER = {
    "unique": 1,
    "legendary": 2,
    "epic": 3,
    "rare": 4,
    "common": 5,
}

ALLOWED_MEDIA_TYPES = {"photo", "video", "animation", "document"}


def _normalize_media_type(media_type: str | None) -> str | None:
    if not media_type:
        return None
    media_type = media_type.lower().strip()
    if media_type == "gif":
        return "animation"
    return media_type if media_type in ALLOWED_MEDIA_TYPES else None


def _row_to_dict(row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _sort_waifus(waifus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        waifus,
        key=lambda w: (
            RARITY_ORDER.get(w.get("rarity"), 99),
            w.get("id", 0),
        ),
    )


def _normalize(text: str) -> str:
    text = (text or "").casefold()
    text = re.sub(r"[^\w\s]+", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _search_sort_key(waifu: dict[str, Any], lang: str) -> tuple[str, int]:
    if lang == "ru":
        name = waifu.get("name_ru") or waifu.get("name_en") or ""
    else:
        name = waifu.get("name_en") or waifu.get("name_ru") or ""
    return (_normalize(name), int(waifu.get("id") or 0))


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
                w.alias,
                w.alias_ru,
                w.alias_en,
                COALESCE(w.alias_ru, w.alias_en, w.alias) AS alias
            FROM waifus w
            ORDER BY w.id
            """
        )

    waifus = [_row_to_dict(row) for row in rows]
    waifus = _sort_waifus(waifus)
    set_cached_all_waifus(waifus)
    return waifus


async def get_all_waifus() -> list[dict[str, Any]]:
    await ensure_catalog_revision_current()

    cached = get_cached_all_waifus()
    if cached is not None:
        return cached

    return await _load_all_waifus()


def _matches_query(waifu: dict[str, Any], query: str) -> bool:
    normalized_query = _normalize(query)
    if not normalized_query:
        return False

    haystack = _normalize(
        " ".join(
            str(part or "")
            for part in (
                waifu.get("name_en"),
                waifu.get("name_ru"),
                waifu.get("alias_ru"),
                waifu.get("alias_en"),
                waifu.get("alias"),
            )
        )
    )

    tokens = [token for token in normalized_query.split(" ") if token]
    return all(token in haystack for token in tokens)


async def search_waifus(query: str, *, lang: str = "ru") -> list[dict[str, Any]]:
    query = (query or "").strip()
    if not query:
        return []

    waifus = await get_all_waifus()
    matched = [w for w in waifus if _matches_query(w, query)]
    return sorted(matched, key=lambda w: _search_sort_key(w, lang))


async def get_waifu_details(waifu_id: int):
    waifus = await get_all_waifus()
    return next((waifu.copy() for waifu in waifus if waifu["id"] == waifu_id), None)


async def get_waifu_media(waifu_id: int):
    pool = get_pool()

    if pool is None:
        raise Exception("Database pool not initialized")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT file_id, media_type
            FROM waifu_media
            WHERE waifu_id = $1
              AND file_id IS NOT NULL
              AND file_id <> ''
            ORDER BY is_primary DESC, sort_order ASC, id ASC
            LIMIT 1
            """,
            waifu_id,
        )

    if not row:
        return None

    result = dict(row)
    result["media_type"] = _normalize_media_type(result.get("media_type"))
    return result


def clear_waifu_catalog_cache() -> None:
    invalidate_waifu_catalog()
