from __future__ import annotations

from typing import Any


_known_users_cache: set[int] = set()
_user_language_cache: dict[int, str] = {}

_chat_language_cache: dict[int, str] = {}
_chat_pity_cache: dict[int, dict[str, int]] = {}

_all_waifus_cache: list[dict[str, Any]] | None = None
_waifus_by_rarity_cache: dict[str, list[dict[str, Any]]] = {}

_category_root_map_cache: dict[int, int] | None = None
_blocked_roots_cache: dict[int, set[int]] = {}

_root_categories_cache: list[dict[str, Any]] | None = None
_category_availability_cache: dict[int, bool] | None = None


# -----------------------------
# USERS
# -----------------------------
def is_known_user(user_id: int) -> bool:
    return user_id in _known_users_cache


def mark_known_user(user_id: int) -> None:
    _known_users_cache.add(user_id)


def clear_known_user(user_id: int) -> None:
    _known_users_cache.discard(user_id)


def has_cached_user_language(user_id: int) -> bool:
    return user_id in _user_language_cache


def get_cached_user_language(user_id: int) -> str | None:
    return _user_language_cache.get(user_id)


def set_cached_user_language(user_id: int, language: str) -> None:
    _user_language_cache[user_id] = language


def clear_user_language_cache(user_id: int) -> None:
    _user_language_cache.pop(user_id, None)


# -----------------------------
# CHATS
# -----------------------------
def has_cached_chat_language(chat_id: int) -> bool:
    return chat_id in _chat_language_cache


def get_cached_chat_language(chat_id: int) -> str | None:
    return _chat_language_cache.get(chat_id)


def set_cached_chat_language(chat_id: int, language: str) -> None:
    _chat_language_cache[chat_id] = language


def clear_chat_language_cache(chat_id: int) -> None:
    _chat_language_cache.pop(chat_id, None)


def has_cached_chat_pity(chat_id: int) -> bool:
    return chat_id in _chat_pity_cache


def get_cached_chat_pity(chat_id: int) -> dict[str, int] | None:
    value = _chat_pity_cache.get(chat_id)
    if value is None:
        return None
    return value.copy()


def set_cached_chat_pity(
    chat_id: int,
    pity_epic: int,
    pity_legendary: int,
    pity_unique: int,
) -> None:
    _chat_pity_cache[chat_id] = {
        "pity_epic": pity_epic,
        "pity_legendary": pity_legendary,
        "pity_unique": pity_unique,
    }


def clear_chat_pity_cache(chat_id: int) -> None:
    _chat_pity_cache.pop(chat_id, None)


def clear_chat_cache(chat_id: int) -> None:
    clear_chat_language_cache(chat_id)
    clear_chat_pity_cache(chat_id)
    _blocked_roots_cache.pop(chat_id, None)


# -----------------------------
# WAIFUS
# -----------------------------
def has_cached_all_waifus() -> bool:
    return _all_waifus_cache is not None


def get_cached_all_waifus() -> list[dict[str, Any]] | None:
    if _all_waifus_cache is None:
        return None
    return [item.copy() for item in _all_waifus_cache]


def set_cached_all_waifus(waifus: list[dict[str, Any]]) -> None:
    global _all_waifus_cache
    _all_waifus_cache = [item.copy() for item in waifus]


def clear_all_waifus_cache() -> None:
    global _all_waifus_cache
    _all_waifus_cache = None
    _waifus_by_rarity_cache.clear()


def has_cached_waifus_by_rarity(rarity: str) -> bool:
    return rarity in _waifus_by_rarity_cache


def get_cached_waifus_by_rarity(rarity: str) -> list[dict[str, Any]] | None:
    waifus = _waifus_by_rarity_cache.get(rarity)
    if waifus is None:
        return None
    return [item.copy() for item in waifus]


def set_cached_waifus_by_rarity(rarity: str, waifus: list[dict[str, Any]]) -> None:
    _waifus_by_rarity_cache[rarity] = [item.copy() for item in waifus]


def clear_waifus_by_rarity_cache(rarity: str | None = None) -> None:
    if rarity is None:
        _waifus_by_rarity_cache.clear()
        return
    _waifus_by_rarity_cache.pop(rarity, None)


# -----------------------------
# CATEGORY ROOT MAP
# -----------------------------
def has_cached_category_root_map() -> bool:
    return _category_root_map_cache is not None


def get_cached_category_root_map() -> dict[int, int] | None:
    if _category_root_map_cache is None:
        return None
    return _category_root_map_cache.copy()


def set_cached_category_root_map(category_root_map: dict[int, int]) -> None:
    global _category_root_map_cache
    _category_root_map_cache = category_root_map.copy()


def clear_category_root_map_cache() -> None:
    global _category_root_map_cache
    _category_root_map_cache = None


# -----------------------------
# BLOCKED ROOTS PER CHAT
# -----------------------------
def has_cached_blocked_roots(chat_id: int) -> bool:
    return chat_id in _blocked_roots_cache


def get_cached_blocked_roots(chat_id: int) -> set[int] | None:
    blocked = _blocked_roots_cache.get(chat_id)
    if blocked is None:
        return None
    return blocked.copy()


def set_cached_blocked_roots(chat_id: int, blocked_root_ids: set[int]) -> None:
    _blocked_roots_cache[chat_id] = blocked_root_ids.copy()


def clear_blocked_roots_cache(chat_id: int | None = None) -> None:
    if chat_id is None:
        _blocked_roots_cache.clear()
        return
    _blocked_roots_cache.pop(chat_id, None)


def get_cached_root_categories() -> list[dict[str, Any]] | None:
    if _root_categories_cache is None:
        return None
    return [item.copy() for item in _root_categories_cache]


def set_cached_root_categories(categories: list[dict[str, Any]]) -> None:
    global _root_categories_cache
    _root_categories_cache = [item.copy() for item in categories]


def clear_root_categories_cache() -> None:
    global _root_categories_cache
    _root_categories_cache = None

# -----------------------------
# CATEGORY AVAILABILITY
# -----------------------------
def get_cached_category_availability_map() -> dict[int, bool] | None:
    if _category_availability_cache is None:
        return None
    return _category_availability_cache.copy()


def set_cached_category_availability_map(category_availability_map: dict[int, bool]) -> None:
    global _category_availability_cache
    _category_availability_cache = category_availability_map.copy()


def clear_category_availability_cache() -> None:
    global _category_availability_cache
    _category_availability_cache = None
