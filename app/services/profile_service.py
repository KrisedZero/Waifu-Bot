from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import html

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.connection import get_pool
from app.services.category_service import get_category_root_map
from app.services.user_service import get_user_favorite_waifu
from app.services.waifu_ui import get_waifu_name


UI = {
    "ru": {
        "profile_title": "ПРОФИЛЬ ВАЙФУ",
        "main_tab": "Профиль",
        "stats_tab": "Статистика",
        "collection_tab": "Коллекция",
        "guide_button": "Гайд",
        "change_favorite": "Сменить любимую вайфу",
        "change_favorite_category": "Выбрать любимую коллекцию",
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
        "guide_title": "КРАТКИЙ ГАЙД",
        "guide_level": "Уровень растёт от собранных вайфу и меняет титул и оформление профиля.",
        "guide_xp": "XP показывает прогресс до следующего уровня.",
        "guide_activity": "Активность за неделю считается по пойманным вайфу за последние 7 дней.",
        "guide_streak": "Серия активности держится, пока не пропущен день без захвата.",
        "guide_favorite": "Любимая вайфу и любимая коллекция выбираются вручную.",
        "guide_tabs": "Вкладки помогают смотреть профиль, статистику и коллекцию отдельно.",
        "guide_perks": "Чем выше уровень, тем богаче профиль и заметнее титул.",
        "back_to_profile": "Назад к профилю",
        "choose_collection": "Выберите любимую коллекцию:",
        "collection_saved": "Теперь твоя любимая коллекция:",
        "no_collection_data": "У тебя пока нет подходящих коллекций.",
    },
    "en": {
        "profile_title": "WAIFU PROFILE",
        "main_tab": "Profile",
        "stats_tab": "Stats",
        "collection_tab": "Collection",
        "guide_button": "Guide",
        "change_favorite": "Change favorite waifu",
        "change_favorite_category": "Choose favorite collection",
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
        "guide_title": "SHORT GUIDE",
        "guide_level": "Level grows from collected waifus and changes the title and profile frame.",
        "guide_xp": "XP shows progress to the next level.",
        "guide_activity": "Weekly activity is based on waifus caught in the last 7 days.",
        "guide_streak": "The streak continues while you do not miss a day without catching.",
        "guide_favorite": "Favorite waifu and favorite collection are chosen manually.",
        "guide_tabs": "Tabs keep profile, stats, and collection separated.",
        "guide_perks": "Higher levels make the profile richer and the title more noticeable.",
        "back_to_profile": "Back to profile",
        "choose_collection": "Choose your favorite collection:",
        "collection_saved": "Your favorite collection is now:",
        "no_collection_data": "You do not have any suitable collections yet.",
    },
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
        return UI[_lang(lang)]["no_data"]
    local = dt.astimezone(timezone.utc)
    if _lang(lang) == "ru":
        return local.strftime("%d.%m.%Y")
    return local.strftime("%Y-%m-%d")


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
    lang = _lang(lang)
    return _ui(lang)["weekly_spans"][_activity_key(weekly_claims)]


def _format_rarity_summary(rarity_counts: Counter, lang: str) -> str:
    labels = _ui(lang)["rarities"]
    parts = []
    for rarity in RARITY_ORDER:
        parts.append(f"{RARITY_ICONS[rarity]} {labels[rarity]} {rarity_counts.get(rarity, 0)}")
    return " | ".join(parts)


def _format_banner(lang: str) -> str:
    title = _ui(lang)["profile_title"]
    return (
        "╭━━━━━━━━━━━━━━━━━━━━╮\n"
        f"✨ <b>{title}</b> ✨\n"
        "╰━━━━━━━━━━━━━━━━━━━━╯"
    )


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

        waifu_rows = await conn.fetch(
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

        root_categories = await conn.fetch(
            """
            SELECT id, name_ru, name_en
            FROM categories
            WHERE parent_id IS NULL AND is_active = TRUE
            ORDER BY id
            """
        )

    username_value = username or (user_row["username"] if user_row else None)
    language_value = (user_row["language"] if user_row and user_row["language"] else telegram_language) or "en"
    root_map = await get_category_root_map()
    root_meta = {row["id"]: {"name_ru": row["name_ru"], "name_en": row["name_en"]} for row in root_categories}

    total_claims = 0
    rarity_counts: Counter[str] = Counter()
    owned_by_root: Counter[int] = Counter()

    for row in waifu_rows:
        amount = int(row["amount"] or 0)
        total_claims += amount
        rarity = str(row["rarity"] or "common").lower()
        rarity_counts[rarity] += amount
        root_id = root_map.get(row["category_id"], row["category_id"])
        if root_id is not None:
            owned_by_root[root_id] += 1

    total_by_root: Counter[int] = Counter()
    for row in all_waifus:
        root_id = root_map.get(row["category_id"], row["category_id"])
        if root_id is not None:
            total_by_root[root_id] += 1

    root_stats: list[dict] = []
    for root_id, meta in root_meta.items():
        owned = owned_by_root.get(root_id, 0)
        total = total_by_root.get(root_id, 0)
        percent = round((owned / total) * 100) if total else 0
        root_stats.append({
            "id": root_id,
            "name_ru": meta.get("name_ru"),
            "name_en": meta.get("name_en"),
            "owned": owned,
            "total": total,
            "percent": percent,
        })

    root_stats.sort(key=lambda item: (-item["owned"], -item["total"], item["name_en"] or item["name_ru"] or "", item["id"]))

    favorite_root_id = None
    favorite_root_name = None
    favorite_root_owned = 0
    favorite_root_total = 0
    favorite_root_percent = 0

    selected_category_id = user_row["favorite_category_id"] if user_row else None
    if selected_category_id:
        selected_root_id = root_map.get(selected_category_id, selected_category_id)
        if selected_root_id in root_meta:
            favorite_root_id = selected_root_id

    if favorite_root_id is None and owned_by_root:
        favorite_root_id = max(
            owned_by_root.keys(),
            key=lambda rid: (
                owned_by_root[rid],
                total_by_root.get(rid, 0),
                -rid,
            ),
        )

    if favorite_root_id is not None:
        favorite_root_owned = owned_by_root.get(favorite_root_id, 0)
        favorite_root_total = total_by_root.get(favorite_root_id, 0)
        favorite_root_percent = round((favorite_root_owned / favorite_root_total) * 100) if favorite_root_total else 0
        favorite_root_row = root_meta.get(favorite_root_id, {})
        favorite_root_name = favorite_root_row.get(f"name_{_lang(language_value)}") or favorite_root_row.get("name_en") or favorite_root_row.get("name_ru")

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
        "favorite_collection_id": favorite_root_id,
        "favorite_collection_name": favorite_root_name,
        "favorite_collection_percent": favorite_root_percent,
        "favorite_collection_owned": favorite_root_owned,
        "favorite_collection_total": favorite_root_total,
        "favorite_collection_stats": root_stats,
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
        _format_banner(lang),
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
            f"🔥 <b>{ui['activity']}:</b> {ui['weekly_spans'][_activity_key(snapshot.get('weekly_claims', 0))]} ({snapshot.get('weekly_claims', 0)})",
            f"⚡ <b>{ui['streak']}:</b> {snapshot.get('streak', 0)} {ui['days']}",
            f"🆕 <b>{ui['first_catch']}:</b> {_format_date(snapshot.get('first_catch'), lang)}",
        ])
    elif view == "collection":
        lines.extend([
            "",
            f"📚 <b>{ui['collection_total']}:</b> {collection_total}",
            _format_rarity_summary(rarity_counts, lang),
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


def build_profile_guide_text(user_lang: str) -> str:
    lang = _lang(user_lang)
    ui = _ui(lang)
    lines = [
        _format_banner(lang),
        "",
        f"📖 <b>{ui['guide_title']}</b>",
        "",
        f"• {ui['guide_level']}",
        f"• {ui['guide_xp']}",
        f"• {ui['guide_activity']}",
        f"• {ui['guide_streak']}",
        f"• {ui['guide_favorite']}",
        f"• {ui['guide_tabs']}",
        f"• {ui['guide_perks']}",
    ]
    return "\n".join(lines)


def build_profile_keyboard(user_lang: str, view: str = "main") -> InlineKeyboardMarkup:
    lang = _lang(user_lang)
    ui = _ui(lang)
    builder = InlineKeyboardBuilder()
    builder.button(text=f"⭐ {ui['main_tab']}", callback_data="profile:view:main")
    builder.button(text=f"📊 {ui['stats_tab']}", callback_data="profile:view:stats")
    builder.button(text=f"📚 {ui['collection_tab']}", callback_data="profile:view:collection")
    builder.adjust(3)

    builder.row(
        InlineKeyboardButton(text=f"❤️ {ui['change_favorite']}", callback_data="change_favorite"),
        InlineKeyboardButton(text=f"🏷 {ui['change_favorite_category']}", callback_data="change_favorite_category"),
    )
    builder.row(
        InlineKeyboardButton(text=f"📖 {ui['guide_button']}", callback_data="profile:guide"),
    )

    return builder.as_markup()


def build_favorite_collection_keyboard(user_lang: str, collection_stats: list[dict]) -> InlineKeyboardMarkup:
    lang = _lang(user_lang)
    ui = _ui(lang)
    builder = InlineKeyboardBuilder()

    for item in collection_stats:
        name = item.get(f"name_{lang}") or item.get("name_en") or item.get("name_ru") or "—"
        percent = item.get("percent", 0)
        owned = item.get("owned", 0)
        total = item.get("total", 0)
        label = f"{name} — {percent}% ({owned}/{total})"
        builder.button(text=label[:64], callback_data=f"set_favorite_category:{item['id']}")

    if collection_stats:
        builder.adjust(1)

    builder.row(
        InlineKeyboardButton(text=f"⬅️ {ui['back_to_profile']}", callback_data="profile:view:main"),
    )
    return builder.as_markup()
