from __future__ import annotations

from app.services.cache_invalidation import (
    invalidate_category_catalog as _invalidate_category_catalog,
    invalidate_chat_state as _invalidate_chat_state,
    invalidate_chat_category_cache as _invalidate_chat_category_cache,
    invalidate_waifu_catalog as _invalidate_waifu_catalog,
)
from app.services.catalog_state_service import bump_catalog_revision


async def invalidate_category_catalog() -> None:
    _invalidate_category_catalog()
    await bump_catalog_revision()


async def invalidate_waifu_catalog() -> None:
    _invalidate_waifu_catalog()
    await bump_catalog_revision()


async def invalidate_chat_category_cache(chat_id: int) -> None:
    _invalidate_chat_category_cache(chat_id)


async def invalidate_chat_state(chat_id: int) -> None:
    _invalidate_chat_state(chat_id)


async def invalidate_all_admin_sessions() -> None:
    # На текущем этапе админ-сессии живут в БД через auth_version_seen.
    # Поэтому полноценного отдельного кэша здесь нет.
    return None
