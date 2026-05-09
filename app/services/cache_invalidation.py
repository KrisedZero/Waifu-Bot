from app.services.cache_service import (
    clear_all_waifus_cache,
    clear_waifus_by_rarity_cache,
    clear_category_root_map_cache,
    clear_root_categories_cache,
    clear_category_availability_cache,
    clear_blocked_roots_cache,
    clear_chat_cache,
)


def invalidate_category_catalog() -> None:
    """
    Сбрасывать после:
    - добавления категории
    - удаления категории
    - смены parent_id
    - переименования категории
    """
    clear_category_root_map_cache()
    clear_root_categories_cache()
    clear_category_availability_cache()
    try:
        from app.services.category_service import clear_category_meta_cache
        clear_category_meta_cache()
    except Exception:
        pass


def invalidate_waifu_catalog() -> None:
    """
    Сбрасывать после:
    - добавления вайфу
    - удаления вайфу
    - изменения rarity
    - изменения category_id
    - массового импорта вайфу
    """
    clear_all_waifus_cache()
    clear_waifus_by_rarity_cache()


def invalidate_chat_category_cache(chat_id: int) -> None:
    """
    Сбрасывать после:
    - блокировки/разблокировки root-категорий в чате
    """
    clear_blocked_roots_cache(chat_id)


def invalidate_chat_state(chat_id: int) -> None:
    """
    Сбрасывать после:
    - смены языка чата
    - ручной очистки данных чата
    - массовых изменений chat_settings
    """
    clear_chat_cache(chat_id)