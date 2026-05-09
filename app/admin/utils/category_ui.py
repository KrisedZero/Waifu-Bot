from __future__ import annotations

from typing import Any


def category_type_label(node_type: str | None, lang: str = "ru") -> str:
    node_type = (node_type or "branch").lower()
    if lang == "en":
        return "📁 Subcategories" if node_type == "branch" else "🎯 Waifus"
    return "📁 Подкатегории" if node_type == "branch" else "🎯 Вайфу"


def category_status_label(is_active: bool, lang: str = "ru") -> str:
    if lang == "en":
        return "Active" if is_active else "Inactive"
    return "Активна" if is_active else "Неактивна"


def category_display_name(row: Any, lang: str = "ru") -> str:
    if lang == "en":
        name = row["name_en"] or row["name_ru"] or ""
    else:
        name = row["name_ru"] or row["name_en"] or ""
    return name.strip() or "—"


def category_card_title(row: Any, lang: str = "ru") -> str:
    name = category_display_name(row, lang)
    node = category_type_label(row["node_type"], lang)
    status = category_status_label(bool(row["is_active"]), lang)
    return f"{name}\n{node} · {status} · ID: {row['id']}"


def normalize_query(text: str) -> str:
    return " ".join((text or "").strip().split())