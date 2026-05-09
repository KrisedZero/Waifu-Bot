from __future__ import annotations

from typing import Any

SEARCH_STATE: dict[tuple[int, int], dict[str, Any]] = {}


def set_search_state(
    chat_id: int,
    user_id: int,
    query: str,
    *,
    category_page: int = 1,
    waifu_page: int = 1,
) -> None:
    SEARCH_STATE[(chat_id, user_id)] = {
        "query": query.strip(),
        "category_page": max(1, int(category_page or 1)),
        "waifu_page": max(1, int(waifu_page or 1)),
    }


def get_search_state(chat_id: int, user_id: int) -> dict[str, Any] | None:
    state = SEARCH_STATE.get((chat_id, user_id))
    return state.copy() if state else None


def update_search_pages(
    chat_id: int,
    user_id: int,
    *,
    category_page: int | None = None,
    waifu_page: int | None = None,
) -> None:
    state = SEARCH_STATE.setdefault(
        (chat_id, user_id),
        {"query": "", "category_page": 1, "waifu_page": 1},
    )

    if category_page is not None:
        state["category_page"] = max(1, int(category_page))
    if waifu_page is not None:
        state["waifu_page"] = max(1, int(waifu_page))


def clear_search_state(chat_id: int, user_id: int) -> None:
    SEARCH_STATE.pop((chat_id, user_id), None)


def set_search_query(chat_id: int, user_id: int, query: str) -> None:
    set_search_state(chat_id, user_id, query)


def get_search_query(chat_id: int, user_id: int) -> str | None:
    state = SEARCH_STATE.get((chat_id, user_id))
    if not state:
        return None
    query = state.get("query")
    return query if query else None
