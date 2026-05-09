from app.database.connection import get_pool
from app.services.category_service import (
    get_root_categories,
    get_category_root_map,
    get_category_availability_map,
)
from app.services.cache_service import (
    get_cached_blocked_roots,
    set_cached_blocked_roots,
)
from app.services.cache_invalidation import invalidate_chat_category_cache


async def _add_chat_category_block(chat_id: int, root_category_id: int) -> None:
    pool = get_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO chat_category_blocks (chat_id, root_category_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            chat_id,
            root_category_id,
        )


async def _remove_chat_category_block(chat_id: int, root_category_id: int) -> None:
    pool = get_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            DELETE FROM chat_category_blocks
            WHERE chat_id = $1 AND root_category_id = $2
            """,
            chat_id,
            root_category_id,
        )


async def ensure_chat_category_block(chat_id: int, root_category_id: int) -> None:
    """
    Совместимость со старым кодом.
    Просто гарантирует наличие блока.
    """
    await _add_chat_category_block(chat_id, root_category_id)
    invalidate_chat_category_cache(chat_id)


async def block_chat_category(chat_id: int, root_category_id: int) -> None:
    await _add_chat_category_block(chat_id, root_category_id)
    invalidate_chat_category_cache(chat_id)


async def unblock_chat_category(chat_id: int, root_category_id: int) -> None:
    await _remove_chat_category_block(chat_id, root_category_id)
    invalidate_chat_category_cache(chat_id)


async def get_blocked_root_category_ids(chat_id: int) -> list[int]:
    cached = get_cached_blocked_roots(chat_id)
    if cached is not None:
        return sorted(cached)

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
    return sorted(blocked)


async def toggle_chat_root_category(chat_id: int, root_category_id: int) -> str:
    """
    Возвращает:
        "blocked"         -> категория заблокирована
        "unblocked"       -> категория разблокирована
        "last_root_locked"-> нельзя заблокировать последнюю доступную root-категорию
    """
    roots = await get_root_categories()
    blocked_ids = set(await get_blocked_root_category_ids(chat_id))

    if root_category_id in blocked_ids:
        await _remove_chat_category_block(chat_id, root_category_id)
        invalidate_chat_category_cache(chat_id)
        return "unblocked"

    allowed_roots = len(roots) - len(blocked_ids)
    if allowed_roots <= 1:
        return "last_root_locked"

    await _add_chat_category_block(chat_id, root_category_id)
    invalidate_chat_category_cache(chat_id)
    return "blocked"


async def is_category_allowed_for_chat(chat_id: int, category_id: int | None) -> bool:
    if not category_id:
        return True

    root_map = await get_category_root_map()
    availability_map = await get_category_availability_map()
    root_id = root_map.get(category_id)

    if root_id is None:
        return True

    if not availability_map.get(category_id, True):
        return False

    blocked_ids = set(await get_blocked_root_category_ids(chat_id))
    return root_id not in blocked_ids and availability_map.get(root_id, True)


async def filter_allowed_waifus_for_chat(chat_id: int, waifus: list[dict]) -> list[dict]:
    if not waifus:
        return []

    blocked_ids = set(await get_blocked_root_category_ids(chat_id))
    root_map = await get_category_root_map()
    availability_map = await get_category_availability_map()

    return [
        w for w in waifus
        if w.get("is_active", True)
        and (w.get("category_id") is None or availability_map.get(w["category_id"], True))
        and (w.get("category_id") is None or root_map.get(w["category_id"]) not in blocked_ids)
    ]


async def get_allowed_root_categories_count(chat_id: int) -> int:
    roots = await get_root_categories()
    blocked_ids = set(await get_blocked_root_category_ids(chat_id))
    availability_map = await get_category_availability_map()
    return max(0, sum(1 for root in roots if availability_map.get(root["id"], True) and root["id"] not in blocked_ids))
