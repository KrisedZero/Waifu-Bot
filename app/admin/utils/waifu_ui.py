from __future__ import annotations

from typing import Any


def _name(row: Any, lang: str = "ru") -> str:
    if lang == "en":
        return (row.get("name_en") or row.get("name_ru") or "—").strip()
    return (row.get("name_ru") or row.get("name_en") or "—").strip()


def waifu_card_text(row: Any, lang: str = "ru") -> str:
    name = _name(row, lang)
    rarity = row.get("rarity") or "—"
    gender = row.get("gender") or "—"
    category = row.get("category_name_en") if lang == "en" and row.get("category_name_en") else row.get("category_name_ru") or "—"
    status = (
        "Active" if row.get("is_active", True) and lang == "en"
        else "Inactive" if lang == "en"
        else ("Активна" if row.get("is_active", True) else "Неактивна")
    )
    media = row.get("media_type") or "—"
    lines = [
        f"<b>{name}</b>",
        f"ID: <code>{row.get('id')}</code>",
        f"{('Редкость' if lang == 'ru' else 'Rarity')}: {rarity}",
        f"{('Пол' if lang == 'ru' else 'Gender')}: {gender}",
        f"{('Категория' if lang == 'ru' else 'Category')}: {category}",
        f"{('Статус' if lang == 'ru' else 'Status')}: {status}",
        f"{('Медиа' if lang == 'ru' else 'Media')}: {media}",
    ]
    return "\n".join(lines)


def waifu_list_item_text(row: Any, lang: str = "ru") -> str:
    name = _name(row, lang)
    cat = row.get("category_name_en") if lang == "en" and row.get("category_name_en") else row.get("category_name_ru") or "—"
    return f"{name} · {cat} · {row.get('rarity') or '—'} · ID:{row.get('id')}"
