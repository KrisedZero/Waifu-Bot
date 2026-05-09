from __future__ import annotations
from collections import Counter
from datetime import datetime, timedelta, timezone
import html
from typing import Any
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.database.connection import get_pool
from app.services.user_service import get_user_favorite_waifu
from app.services.waifu_ui import get_waifu_name
UI = {
    "ru": {
        "profile_title": "ПРОФИЛЬ ВАЙФУ",
        "stats_title": "СТАТИСТИКА ВАЙФУ",
        "collection_title": "КОЛЛЕКЦИЯ ВАЙФУ",
        "guide_title": "ГАЙД ВАЙФУ",
        "main_tab": "Профиль",
        "stats_tab": "Статистика",
        "collection_tab": "Коллекция",
        "guide_button": "Гайд",
        "change_favorite": "Сменить любимую вайфу",
        "change_favorite_category": "Выбрать любимую коллекцию",
        "choose_collection": "Выберите любимую коллекцию:",
        "choose_collection_in": "Выберите раздел внутри коллекции:",
        "select_this_category": "Выбрать эту категорию",
        "open_subcategories": "Открыть подкатегории",
        "back": "Назад",
        "home": "В корень",
        "player": "Игрок",
        "joined": "Дата регистрации",
        "level": "Уровень",
        "xp": "XP",
        "perks": "Плюшки уровня",
        "favorite_waifu": "Любимая вайфу",
        "favorite_collection": "Любимая коллекция",
        "collection": "Коллекция",
        "activity": "Активность за неделю",
        "streak": "Серия активности",
        "first_catch": "Первый захват",
        "days": "дн.",
        "no_data": "—",
        "collection_total": "Всего вайфу",
        "collection_owned": "В коллекции",
        "collection_completion": "Заполнение",
        "weekly_spans": {
            "calm": "Спокойный",
            "steady": "Ровный",
            "active": "Активный",
            "high": "На максимуме",
            "overdrive": "Overdrive",
        },
        "rarities": {
            "common": "Common",
            "rare": "Rare",
            "epic": "Epic",
            "legendary": "Legendary",
            "unique": "Unique",
        },
        "guide_level": "Уровень растёт от собранных вайфу и меняет титул и оформление профиля.",
        "guide_xp": "XP показывает прогресс до следующего уровня.",
        "guide_activity": "Активность за неделю считается по пойманным вайфу за последние 7 дней.",
        "guide_streak": "Серия активности держится, пока не пропущен день без захвата.",
        "guide_favorite": "Любимая вайфу и любимая коллекция выбираются вручную.",
        "guide_tabs": "Вкладки разделяют профиль, статистику и коллекцию.",
        "guide_perks": "Чем выше уровень, тем богаче профиль и заметнее титул.",
        "back_to_profile": "Назад к профилю",
        "collection_saved": "Теперь твоя любимая коллекция:",
        "not_found": "Не удалось найти выбранную категорию.",
        "no_collection_data": "У тебя пока нет подходящих коллекций.",
        "select_root_hint": "Выбирай раздел или сразу подкатегорию. Любую категорию можно открыть и затем выбрать.",
    },
    "en": {
        "profile_title": "WAIFU PROFILE",
        "stats_title": "WAIFU STATS",
        "collection_title": "WAIFU COLLECTION",
        "guide_title": "WAIFU GUIDE",
        "main_tab": "Profile",
        "stats_tab": "Stats",
        "collection_tab": "Collection",
        "guide_button": "Guide",
        "change_favorite": "Change favorite waifu",
        "change_favorite_category": "Choose favorite collection",
        "choose_collection": "Choose your favorite collection:",
        "choose_collection_in": "Choose a section inside the collection:",
        "select_this_category": "Select this category",
        "open_subcategories": "Open subcategories",
        "back": "Back",
        "home": "Root",
        "player": "Player",
        "joined": "Joined",
        "level": "Level",
        "xp": "XP",
        "perks": "Level perks",
        "favorite_waifu": "Favorite waifu",
        "favorite_collection": "Favorite collection",
        "collection": "Collection",
        "activity": "Weekly activity",
        "streak": "Current streak",
        "first_catch": "First catch",
        "days": "days",
        "no_data": "—",
        "collection_total": "Total waifus",
        "collection_owned": "Owned in collection",
        "collection_completion": "Completion",
        "weekly_spans": {
            "calm": "Calm",
            "steady": "Steady",
            "active": "Active",
            "high": "High Gear",
            "overdrive": "Overdrive",
        },
        "rarities": {
            "common": "Common",
            "rare": "Rare",
            "epic": "Epic",
            "legendary": "Legendary",
            "unique": "Unique",
        },
        "guide_level": "Level grows from collected waifus and changes the title and profile frame.",
        "guide_xp": "XP shows progress to the next level.",
        "guide_activity": "Weekly activity is based on waifus caught in the last 7 days.",
        "guide_streak": "The streak continues while you do not miss a day without catching.",
        "guide_favorite": "Favorite waifu and favorite collection are chosen manually.",
        "guide_tabs": "Tabs keep profile, stats, and collection separated.",
        "guide_perks": "Higher levels make the profile richer and the title more noticeable.",
        "back_to_profile": "Back to profile",
        "collection_saved": "Your favorite collection is now:",
        "not_found": "Could not find the selected category.",
        "no_collection_data": "You do not have any suitable collections yet.",
        "select_root_hint": "Pick a section or go deeper into a subcategory. Any category can be opened and selected.",
    },
}
PROFILE_VIEW_META = {
    "main": {"title": {"ru": "ПРОФИЛЬ ВАЙФУ", "en": "WAIFU PROFILE"}, "icon": "⭐"},
    "stats": {"title": {"ru": "СТАТИСТИКА ВАЙФУ", "en": "WAIFU STATS"}, "icon": "📊"},
    "collection": {"title": {"ru": "КОЛЛЕКЦИЯ ВАЙФУ", "en": "WAIFU COLLECTION"}, "icon": "🏰"},
    "guide": {"title": {"ru": "ГАЙД ВАЙФУ", "en": "WAIFU GUIDE"}, "icon": "📖"},
}
LEVEL_GROUPS = [
    (1, 10, 100, "⚪️", {"ru": "Новичок", "en": "Novice"}, {"ru": "Базовая карточка", "en": "Basic card"}),
    (11, 20, 150, "🔵", {"ru": "Коллекционер", "en": "Collector"}, {"ru": "Показывается титул", "en": "Title appears"}),
    (21, 30, 200, "🟣", {"ru": "Охотник", "en": "Hunter"}, {"ru": "Расширенный профиль", "en": "Expanded profile"}),
    (31, 40, 250, "🟠", {"ru": "Элитный охотник", "en": "Elite Hunter"}, {"ru": "Более заметная рамка", "en": "Brighter frame"}),
    (41, 50, 350, "🟡", {"ru": "Мастер", "en": "Master"}, {"ru": "Больше визуальных плюшек", "en": "More visual perks"}),
    (51, 60, 450, "🔴", {"ru": "Командир", "en": "Commander"}, {"ru": "Премиальный вид", "en": "Premium look"}),
    (61, 70, 600, "✨", {"ru": "Легенда", "en": "Legend"}, {"ru": "Яркий статус", "en": "Bright status"}),
    (71, 80, 750, "🌟", {"ru": "Мифический", "en": "Mythic"}, {"ru": "Мифическое оформление", "en": "Mythic styling"}),
    (81, 90, 900, "🔥", {"ru": "Авангард", "en": "Apex"}, {"ru": "Почти топовый вид", "en": "Near-top visual"}),
    (91, 95, 1000, "⚜️", {"ru": "Вознесённый", "en": "Ascended"}, {"ru": "Королевская рамка", "en": "Royal frame"}),
    (96, 99, 1500, "🏅", {"ru": "Коронованный", "en": "Crowned"}, {"ru": "Почти чемпион", "en": "Almost champion"}),
    (100, 100, 1500, "🏆", {"ru": "Чемпион", "en": "Champion"}, {"ru": "Трофейный профиль", "en": "Trophy profile"}),
]
ACTIVITY_THRESHOLDS = [
    (0, 9, "calm"),
    (10, 39, "steady"),
    (40, 89, "active"),
    (90, 149, "high"),
    (150, 10**9, "overdrive"),
]
RARITY_ORDER = ["unique", "legendary", "epic", "rare", "common"]
RARITY_ICONS = {
    "unique": "💎",
    "legendary": "🟡",
    "epic": "🟣",
    "rare": "🔵",
    "common": "⚪️",
}
def _lang(value: str) -> str:
    return value if value in ("ru", "en") else "en"
def _ui(lang: str) -> dict:
    return UI[_lang(lang)]
def _escape(value: str | None) -> str:
    return html.escape(value or "—")
def _username_display(snapshot: dict) -> str:
    username = snapshot.get("username")
    if username:
        return f"@{username}"
    return f"ID: {snapshot.get('user_id')}"
def _format_date(dt: datetime | None, lang: str) -> str:
    if not dt:
        return _ui(lang)["no_data"]
    local = dt.astimezone(timezone.utc)
    return local.strftime("%d.%m.%Y") if _lang(lang) == "ru" else local.strftime("%Y-%m-%d")
def _level_requirement(level: int) -> int:
    for start, end, requirement, _, _, _ in LEVEL_GROUPS:
        if start <= level <= end:
            return requirement
    return 1500
def calculate_level(total_xp: int) -> dict[str, int | bool]:
    xp = max(0, int(total_xp or 0))
    level = 1
    while level < 100:
        requirement = _level_requirement(level)
        if xp < requirement:
            break
        xp -= requirement
        level += 1
    return {
        "level": level,
        "current_xp": xp,
        "next_xp": _level_requirement(level),
        "is_max": level >= 100,
    }
def get_level_badge(level: int) -> str:
    for start, end, _, badge, _, _ in LEVEL_GROUPS:
        if start <= level <= end:
            return badge
    return "🏆"
def get_level_title(level: int, lang: str) -> str:
    lang = _lang(lang)
    for start, end, _, _, titles, _ in LEVEL_GROUPS:
        if start <= level <= end:
            return titles[lang]
    return "Champion" if lang == "en" else "Чемпион"
def get_level_perks(level: int, lang: str) -> str:
    lang = _lang(lang)
    for start, end, _, _, _, perks in LEVEL_GROUPS:
        if start <= level <= end:
            return perks[lang]
    return "Trophy profile" if lang == "en" else "Трофейный профиль"
def _activity_key(weekly_claims: int) -> str:
    weekly_claims = max(0, int(weekly_claims or 0))
    for lower, upper, label in ACTIVITY_THRESHOLDS:
        if lower <= weekly_claims <= upper:
            return label
    return "overdrive"
def get_activity_label(weekly_claims: int, lang: str) -> str:
    return _ui(lang)["weekly_spans"][_activity_key(weekly_claims)]
def _format_rarity_summary(rarity_counts: Counter, lang: str) -> str:
    labels = _ui(lang)["rarities"]
    return " | ".join(f"{RARITY_ICONS[rarity]} {labels[rarity]} {rarity_counts.get(rarity, 0)}" for rarity in RARITY_ORDER)
def _profile_view(view: str) -> str:
    return view if view in PROFILE_VIEW_META else "main"
def _profile_title(lang: str, view: str) -> str:
    meta = PROFILE_VIEW_META[_profile_view(view)]
    return meta["title"][_lang(lang)]
def _profile_icon(view: str) -> str:
    return PROFILE_VIEW_META[_profile_view(view)]["icon"]

def _banner_style(level: int, view: str) -> tuple[str, str, str]:
    level = max(1, int(level or 1))
    if level >= 91:
        deco = "✪"
        frame = "╭━━━━━━━━━━━━━━━━━━━━╮"
        footer = "╰━━━━━━✪━━━━━━━━✪━━━━━╯"
    elif level >= 71:
        deco = "✦"
        frame = "╭━━━━━━━━━━━━━━━━━━━━╮"
        footer = "╰━━━━━━✦━━━━━━━━✦━━━━━╯"
    elif level >= 51:
        deco = "✨"
        frame = "╭━━━━━━━━━━━━━━━━━━━━╮"
        footer = "╰━━━━━━✨━━━━━━━━✨━━━━━╯"
    elif level >= 31:
        deco = "⭐"
        frame = "╭━━━━━━━━━━━━━━━━━━━━╮"
        footer = "╰━━━━━━⭐━━━━━━━━⭐━━━━━╯"
    elif level >= 11:
        deco = "🌟"
        frame = "╭━━━━━━━━━━━━━━━━━━━━╮"
        footer = "╰━━━━━━🌟━━━━━━━━🌟━━━━━╯"
    else:
        deco = "⭐"
        frame = "╭━━━━━━━━━━━━━━━━━━━━╮"
        footer = "╰━━━━━━━━━━━━━━━━━━━━╯"
    if _profile_view(view) == "guide":
        deco = "📘"
    return frame, deco, footer

def _format_banner(lang: str, view: str, level: int | None = None) -> str:
    title = _profile_title(lang, view)
    frame, deco, footer = _banner_style(level or 1, view)
    return "\n".join([
        frame,
        f"{deco} <b>{title}</b> {deco}",
        footer,
    ])

def _row_to_dict(row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}
async def _load_categories() -> list[dict[str, Any]]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name_ru, name_en, parent_id, is_active, sort_order
            FROM categories
            WHERE is_active = TRUE
            ORDER BY COALESCE(sort_order, 0), LOWER(COALESCE(name_ru, name_en)), id
            """
        )
    return [_row_to_dict(row) for row in rows]
def _build_category_helpers(categories: list[dict[str, Any]]):
    categories_by_id = {int(item["id"]): item for item in categories}
    children_by_parent: dict[int | None, list[int]] = {}
    for item in categories:
        parent_id = item.get("parent_id")
        key = int(parent_id) if parent_id is not None else None
        children_by_parent.setdefault(key, []).append(int(item["id"]))
    for child_ids in children_by_parent.values():
        child_ids.sort(key=lambda cid: (_category_display_name(categories_by_id[cid], "ru").casefold(), _category_display_name(categories_by_id[cid], "en").casefold(), cid))
    path_cache: dict[tuple[int, str], str] = {}
    ancestor_cache: dict[int, list[int]] = {}
    def ancestors(category_id: int) -> list[int]:
        if category_id in ancestor_cache:
            return ancestor_cache[category_id]
        chain: list[int] = []
        seen: set[int] = set()
        current = category_id
        while current in categories_by_id and current not in seen:
            seen.add(current)
            chain.append(current)
            parent_id = categories_by_id[current].get("parent_id")
            if parent_id is None:
                break
            current = int(parent_id)
        ancestor_cache[category_id] = chain
        return chain
    def path(category_id: int, lang: str) -> str:
        key = (category_id, _lang(lang))
        if key in path_cache:
            return path_cache[key]
        cat = categories_by_id.get(category_id)
        if not cat:
            path_cache[key] = "—"
            return "—"
        parent_id = cat.get("parent_id")
        name = _category_display_name(cat, lang)
        if parent_id is None or int(parent_id) not in categories_by_id:
            result = name
        else:
            parent_path = path(int(parent_id), lang)
            result = f"{parent_path} / {name}" if parent_path and parent_path != "—" else name
        path_cache[key] = result
        return result
    return categories_by_id, children_by_parent, path, ancestors
def _category_display_name(category: dict[str, Any], lang: str = "ru") -> str:
    if _lang(lang) == "ru":
        return category.get("name_ru") or category.get("name_en") or "—"
    return category.get("name_en") or category.get("name_ru") or "—"
def _build_category_stats(
    categories: list[dict[str, Any]],
    owned_rows: list[dict[str, Any]],
    all_waifus: list[dict[str, Any]],
    lang: str,
) -> list[dict[str, Any]]:
    categories_by_id, _, path, ancestors = _build_category_helpers(categories)
    if not categories_by_id:
        return []
    exact_owned: Counter[int] = Counter()
    exact_total: Counter[int] = Counter()
    for row in owned_rows:
        category_id = row.get("category_id")
        if category_id is None:
            continue
        category_id = int(category_id)
        if category_id not in categories_by_id:
            continue
        exact_owned[category_id] += 1
    for row in all_waifus:
        category_id = row.get("category_id")
        if category_id is None:
            continue
        category_id = int(category_id)
        if category_id not in categories_by_id:
            continue
        exact_total[category_id] += 1
    owned_subtree: Counter[int] = Counter()
    total_subtree: Counter[int] = Counter()
    for category_id, amount in exact_owned.items():
        for ancestor_id in ancestors(category_id):
            owned_subtree[ancestor_id] += amount
    for category_id, amount in exact_total.items():
        for ancestor_id in ancestors(category_id):
            total_subtree[ancestor_id] += amount
    stats: list[dict[str, Any]] = []
    for category_id, category in categories_by_id.items():
        owned = int(owned_subtree.get(category_id, 0))
        total = int(total_subtree.get(category_id, 0))
        percent = round((owned / total) * 100) if total else 0
        stats.append(
            {
                "id": category_id,
                "name_ru": category.get("name_ru"),
                "name_en": category.get("name_en"),
                "path_ru": path(category_id, "ru"),
                "path_en": path(category_id, "en"),
                "path": path(category_id, lang),
                "owned": owned,
                "total": total,
                "percent": percent,
                "parent_id": category.get("parent_id"),
            }
        )
    stats.sort(key=lambda item: (item["path"].casefold(), int(item["id"])))
    return stats
def _shorten_label(text: str, limit: int = 64) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"
async def get_profile_snapshot(user_id: int, username: str | None = None, telegram_language: str | None = None) -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        user_row = await conn.fetchrow(
            """
            SELECT user_id, username, language, created_at, favorite_waifu_id, favorite_category_id
            FROM users
            WHERE user_id = $1
            """,
            user_id,
        )
        claim_rows = await conn.fetch(
            """
            SELECT waifu_id, claimed_at, chat_id
            FROM user_claims
            WHERE user_id = $1
            ORDER BY claimed_at ASC
            """,
            user_id,
        )
        owned_rows = await conn.fetch(
            """
            SELECT
                uw.waifu_id,
                uw.amount,
                w.name_ru,
                w.name_en,
                w.rarity,
                w.category_id
            FROM user_waifus uw
            JOIN waifus w ON w.id = uw.waifu_id
            WHERE uw.user_id = $1
            ORDER BY w.rarity, w.id
            """,
            user_id,
        )
        all_waifus = await conn.fetch(
            """
            SELECT id, category_id
            FROM waifus
            WHERE is_active = TRUE
            """
        )
        categories = await conn.fetch(
            """
            SELECT id, name_ru, name_en, parent_id, is_active, sort_order
            FROM categories
            WHERE is_active = TRUE
            ORDER BY COALESCE(sort_order, 0), LOWER(COALESCE(name_ru, name_en)), id
            """
        )
    username_value = username or (user_row["username"] if user_row else None)
    language_value = (user_row["language"] if user_row and user_row["language"] else telegram_language) or "en"
    categories_list = [_row_to_dict(row) for row in categories]
    category_stats = _build_category_stats(categories_list, [dict(r) for r in owned_rows], [dict(r) for r in all_waifus], language_value)
    category_stats_by_id = {int(item["id"]): item for item in category_stats}
    total_claims = 0
    rarity_counts: Counter[str] = Counter()
    for row in owned_rows:
        amount = int(row["amount"] or 0)
        total_claims += amount
        rarity = str(row["rarity"] or "common").lower()
        rarity_counts[rarity] += amount
    favorite_collection_id = None
    favorite_collection_name = None
    favorite_collection_owned = 0
    favorite_collection_total = 0
    favorite_collection_percent = 0
    selected_category_id = int(user_row["favorite_category_id"]) if user_row and user_row["favorite_category_id"] is not None else None
    if selected_category_id is not None and selected_category_id in category_stats_by_id:
        favorite_collection_id = selected_category_id
    elif category_stats:
        favorite_collection_id = max(
            category_stats,
            key=lambda item: (
                int(item.get("owned") or 0),
                int(item.get("total") or 0),
                item.get("path") or "",
                -int(item.get("id") or 0),
            ),
        )["id"]
    if favorite_collection_id is not None:
        favorite_item = category_stats_by_id.get(favorite_collection_id)
        if favorite_item:
            favorite_collection_name = favorite_item.get(f"path_{_lang(language_value)}") or favorite_item.get("path")
            favorite_collection_owned = int(favorite_item.get("owned") or 0)
            favorite_collection_total = int(favorite_item.get("total") or 0)
            favorite_collection_percent = int(favorite_item.get("percent") or 0)
    weekly_claims = 0
    first_catch = None
    streak = 0
    if claim_rows:
        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=7)
        weekly_claims = sum(1 for row in claim_rows if row["claimed_at"] and row["claimed_at"] >= week_start)
        first_catch = claim_rows[0]["claimed_at"]
        unique_days = sorted({row["claimed_at"].date() for row in claim_rows if row["claimed_at"]})
        if unique_days:
            streak = 1
            for idx in range(len(unique_days) - 1, 0, -1):
                if unique_days[idx] - unique_days[idx - 1] == timedelta(days=1):
                    streak += 1
                else:
                    break
    level_info = calculate_level(total_claims)
    favorite_waifu = await get_user_favorite_waifu(user_id)
    favorite_waifu_name = None
    if favorite_waifu:
        favorite_waifu_name = get_waifu_name(favorite_waifu, language_value)
    return {
        "user_id": user_id,
        "username": username_value,
        "language": _lang(language_value),
        "created_at": user_row["created_at"] if user_row else None,
        "total_claims": total_claims,
        "rarity_counts": rarity_counts,
        "favorite_waifu": favorite_waifu,
        "favorite_waifu_name": favorite_waifu_name,
        "favorite_collection_id": favorite_collection_id,
        "favorite_collection_name": favorite_collection_name,
        "favorite_collection_percent": favorite_collection_percent,
        "favorite_collection_owned": favorite_collection_owned,
        "favorite_collection_total": favorite_collection_total,
        "favorite_collection_stats": category_stats,
        "weekly_claims": weekly_claims,
        "activity_label": get_activity_label(weekly_claims, language_value),
        "first_catch": first_catch,
        "streak": streak,
        "level": int(level_info["level"]),
        "current_xp": int(level_info["current_xp"]),
        "next_xp": int(level_info["next_xp"]),
        "is_max": bool(level_info["is_max"]),
    }
def build_profile_text(snapshot: dict, user_lang: str, view: str = "main") -> str:
    lang = _lang(user_lang)
    ui = _ui(lang)
    view = _profile_view(view)
    badge = get_level_badge(int(snapshot.get("level", 1)))
    title = get_level_title(int(snapshot.get("level", 1)), lang)
    perks = get_level_perks(int(snapshot.get("level", 1)), lang)
    username = _escape(_username_display(snapshot))
    joined = _format_date(snapshot.get("created_at"), lang)
    favorite_waifu = _escape(snapshot.get("favorite_waifu_name"))
    favorite_collection = _escape(snapshot.get("favorite_collection_name"))
    collection_total = int(snapshot.get("total_claims") or 0)
    rarity_counts: Counter = snapshot.get("rarity_counts") or Counter()
    xp_line = "MAX" if snapshot.get("is_max") else f"{snapshot.get('current_xp', 0)} / {snapshot.get('next_xp', 0)}"
    lines: list[str] = [
        _format_banner(lang, view, int(snapshot.get("level", 1))),
        "",
        f"🌟 <b>{ui['player']}:</b> {username}",
        f"📅 <b>{ui['joined']}:</b> {joined}",
        "",
        f"{badge} <b>{ui['level']}:</b> {snapshot.get('level', 1)} — {html.escape(title)}",
        f"⭐ <b>{ui['xp']}:</b> {xp_line}",
        f"🎁 <b>{ui['perks']}:</b> {html.escape(perks)}",
    ]
    if view == "main":
        lines.extend([
            "",
            f"❤️ <b>{ui['favorite_waifu']}:</b> {favorite_waifu}",
            f"🏷 <b>{ui['favorite_collection']}:</b> {favorite_collection} — {snapshot.get('favorite_collection_percent', 0)}%",
        ])
    elif view == "stats":
        lines.extend([
            "",
            f"🔥 <b>{ui['activity']}:</b> {snapshot.get('activity_label') or ui['weekly_spans'][_activity_key(snapshot.get('weekly_claims', 0))]} ({snapshot.get('weekly_claims', 0)})",
            f"⚡ <b>{ui['streak']}:</b> {snapshot.get('streak', 0)} {ui['days']}",
            f"🆕 <b>{ui['first_catch']}:</b> {_format_date(snapshot.get('first_catch'), lang)}",
        ])
    elif view == "collection":
        lines.extend([
            "",
            f"📚 <b>{ui['collection_total']}:</b> {collection_total}",
            f"🗂 <b>{ui['collection']}:</b> {_format_rarity_summary(rarity_counts, lang)}",
            "",
            f"🏷 <b>{ui['favorite_collection']}:</b> {favorite_collection} — {snapshot.get('favorite_collection_percent', 0)}%",
        ])
    else:
        lines.extend([
            "",
            f"❤️ <b>{ui['favorite_waifu']}:</b> {favorite_waifu}",
            f"🏷 <b>{ui['favorite_collection']}:</b> {favorite_collection} — {snapshot.get('favorite_collection_percent', 0)}%",
        ])
    return "\n".join(lines)
def build_profile_guide_text(user_lang: str, level: int = 1) -> str:
    lang = _lang(user_lang)
    ui = _ui(lang)
    is_ru = lang == "ru"
    lines = [
        _format_banner(lang, "guide", level),
        "",
        f"📖 <b>{ui['guide_title']}</b>",
        "",
        f"<b>{'Что делает профиль' if is_ru else 'What the profile does'}</b>",
        f"• {'Показывает уровень, XP, любимую вайфу и любимую коллекцию.' if is_ru else 'Shows level, XP, favorite waifu, and favorite collection.'}",
        f"• {'Чем выше уровень, тем богаче рамка, титул и оформление.' if is_ru else 'The higher the level, the richer the frame, title, and styling.'}",
        "",
        f"<b>{'Как растёт уровень' if is_ru else 'How levels grow'}</b>",
        f"• {'Нижние уровни — это базовая карточка.' if is_ru else 'Lower levels use the basic card frame.'}",
        f"• {'Дальше профиль становится заметнее и красочнее.' if is_ru else 'Later the profile becomes brighter and more decorated.'}",
        f"• {'XP и уровень растут от собранных вайфу.' if is_ru else 'XP and levels grow from collected waifus.'}",
        "",
        f"<b>{'Разделы' if is_ru else 'Sections'}</b>",
        f"<b>1.</b> {ui['guide_level']}",
        f"<b>2.</b> {ui['guide_xp']}",
        f"<b>3.</b> {ui['guide_activity']}",
        f"<b>4.</b> {ui['guide_streak']}",
        f"<b>5.</b> {ui['guide_favorite']}",
        f"<b>6.</b> {ui['guide_tabs']}",
        f"<b>7.</b> {ui['guide_perks']}",
        "",
        f"🧭 <b>{'Как пользоваться' if is_ru else 'How to use it'}</b>",
        f"• {'Открой профиль, статистику или коллекцию одной кнопкой.' if is_ru else 'Open profile, stats, or collection with one tap.'}",
        f"• {'Выбери любимую вайфу и любимую коллекцию.' if is_ru else 'Choose your favorite waifu and favorite collection.'}",
        f"• {'Заходи в подкатегории, чтобы выбрать точную франшизу или аниме.' if is_ru else 'Go deeper into subcategories to pick the exact franchise or anime.'}",
    ]
    return "\n".join(lines)

def _tab_label(icon: str, label: str, active: bool) -> str:
    return f"{'✨ ' if active else ''}{icon} {label}"

def build_profile_keyboard(user_lang: str, view: str = "main") -> InlineKeyboardMarkup:
    lang = _lang(user_lang)
    ui = _ui(lang)
    view = _profile_view(view)
    builder = InlineKeyboardBuilder()
    builder.button(text=_tab_label("⭐", ui['main_tab'], view == "main"), callback_data="profile:view:main")
    builder.button(text=_tab_label("📊", ui['stats_tab'], view == "stats"), callback_data="profile:view:stats")
    builder.button(text=_tab_label("🏰", ui['collection_tab'], view == "collection"), callback_data="profile:view:collection")
    builder.adjust(3)
    builder.row(
        InlineKeyboardButton(text=f"❤️ {ui['change_favorite']}", callback_data="change_favorite"),
        InlineKeyboardButton(text=f"🏷 {ui['change_favorite_category']}", callback_data="change_favorite_category"),
    )
    builder.row(
        InlineKeyboardButton(text=f"📖 {ui['guide_button']}", callback_data="profile:view:guide"),
    )
    return builder.as_markup()
async def build_favorite_collection_view(
    user_lang: str,
    current_category_id: int | None = None,
) -> tuple[str, InlineKeyboardMarkup]:
    lang = _lang(user_lang)
    ui = _ui(lang)
    categories = await _load_categories()
    if not categories:
        text = ui["no_collection_data"]
        back_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=f"⬅️ {ui['back_to_profile']}", callback_data="profile:view:main")]]
        )
        return text, back_keyboard
    categories_by_id, children_by_parent, path, _ancestors = _build_category_helpers(categories)
    if current_category_id is not None and current_category_id not in categories_by_id:
        current_category_id = None
    if current_category_id is not None:
        current_label = path(current_category_id, lang)
        parent_id = categories_by_id[current_category_id].get("parent_id")
    else:
        current_label = None
        parent_id = None
    children = children_by_parent.get(current_category_id if current_category_id is not None else None, [])
    lines = [
        _format_banner(lang, "collection", 1),
        "",
        f"📚 <b>{ui['choose_collection']}</b>",
    ]
    if current_label:
        lines.append(f"🏷 <i>{html.escape(current_label)}</i>")
    lines.append("")
    lines.append(ui["select_root_hint"])
    builder = InlineKeyboardBuilder()
    if current_category_id is not None:
        buttons = [
            InlineKeyboardButton(text=f"✅ {ui['select_this_category']}", callback_data=f"set_favorite_category:{current_category_id}"),
        ]
        if parent_id is not None:
            buttons.append(
                InlineKeyboardButton(
                    text=f"⬅️ {ui['back']}",
                    callback_data=f"favcat:open:{int(parent_id)}",
                )
            )
        builder.row(*buttons)
    else:
        builder.row(
            InlineKeyboardButton(text=f"🏰 {ui['home']}", callback_data="favcat:open:root"),
        )
    child_builder = InlineKeyboardBuilder()
    for child_id in children:
        category = categories_by_id[child_id]
        has_children = bool(children_by_parent.get(child_id))
        label = _shorten_label(f"{'📁' if has_children else '🏰'} {_category_display_name(category, lang)}")
        callback = f"favcat:open:{child_id}" if has_children else f"set_favorite_category:{child_id}"
        child_builder.button(text=label, callback_data=callback)
    if children:
        child_builder.adjust(2)
        builder.attach(child_builder)
    builder.row(
        InlineKeyboardButton(text=f"⬅️ {ui['back_to_profile']}", callback_data="profile:view:main"),
    )
    return "\n".join(lines), builder.as_markup()
