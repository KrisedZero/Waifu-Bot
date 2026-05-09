from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.user_service import get_user_language

router = Router()

HELP_TEXTS = {
    "ru": {
        "main": (
            "🎮 <b>Как играть</b>\n\n"
            "• Пиши сообщения в группе — на 100-м сообщении может появиться вайфу.\n"
            "• Называй имя вайфу прямо в чат, без команды.\n"
            "• Если угадаешь, она попадёт в твою коллекцию.\n"
            "• У редкостей есть скрытая pity-система: шанс растёт со временем.\n\n"
            "Выбери раздел ниже, чтобы посмотреть детали."
        ),
        "play": (
            "🎯 <b>Игровой цикл</b>\n\n"
            "1. Чат живёт своей жизнью, а бот считает сообщения.\n"
            "2. После нужного количества сообщений может появиться вайфу.\n"
            "3. У неё скрыто имя, поэтому угадывать нужно по-честному.\n"
            "4. Верный ответ добавляет вайфу в коллекцию.\n\n"
            "Чем активнее чат, тем чаще происходят спавны."
        ),
        "spawn": (
            "🌸 <b>Спавн и редкости</b>\n\n"
            "• Вайфу появляются по механике сообщений, а не по таймеру.\n"
            "• Есть редкости: common, rare, epic, legendary, unique.\n"
            "• Для более редких вайфу шанс повышается скрыто через pity.\n"
            "• Порог гарантии тоже скрыт внутри механики, чтобы игра оставалась живой."
        ),
        "profile": (
            "⭐ <b>Профиль</b>\n\n"
            "• Профиль показывает твой уровень, коллекцию и личные настройки.\n"
            "• Вкладки профиля разделяют статистику, коллекцию и гайд.\n"
            "• По мере роста уровня оформление профиля становится богаче.\n"
            "• Там же можно выбрать любимую вайфу и любимую категорию."
        ),
        "collection": (
            "📚 <b>Коллекция и поиск</b>\n\n"
            "• /mywaifus — твоя коллекция.\n"
            "• /allwaifus — каталог всех доступных вайфу.\n"
            "• /searchwaifu — быстрый поиск по имени, алиасу или категории.\n"
            "• Категории могут быть вложенными: франшизы, аниме, фильмы и любые подкатегории."
        ),
        "rarity": (
            "💎 <b>Редкости и pity</b>\n\n"
            "• common, rare, epic, legendary, unique — пять уровней редкости.\n"
            "• Чем выше редкость, тем заметнее визуальная подача.\n"
            "• pity мягко подталкивает шанс редких выпадений вверх.\n"
            "• Система работает скрыто, без лишнего шума в чате."
        ),
        "commands": (
            "⌨️ <b>Команды</b>\n\n"
            "/start — приветствие\n"
            "/help — это меню\n"
            "/profile — твой профиль\n"
            "/mywaifus — твоя коллекция\n"
            "/allwaifus — каталог вайфу\n"
            "/searchwaifu — поиск вайфу\n"
            "/language — язык пользователя\n"
            "/chatlanguage — язык чата\n"
            "/chatcategories — категории чата\n\n"
            "Бот также реагирует на имя вайфу прямо в сообщениях, без команды."
        ),
    },
    "en": {
        "main": (
            "🎮 <b>How to play</b>\n\n"
            "• Send messages in the group — a waifu may spawn on the 100th message.\n"
            "• Type the waifu's name directly in chat, no command needed.\n"
            "• If you guess right, she goes into your collection.\n"
            "• Rare waifus are boosted by a hidden pity system.\n\n"
            "Pick a section below to see more details."
        ),
        "play": (
            "🎯 <b>Game loop</b>\n\n"
            "1. The chat keeps chatting while the bot counts messages.\n"
            "2. After enough messages, a waifu may appear.\n"
            "3. Her name is hidden, so the catch is fair and manual.\n"
            "4. A correct answer adds her to your collection.\n\n"
            "The more active the chat, the more often spawns happen."
        ),
        "spawn": (
            "🌸 <b>Spawn and rarity</b>\n\n"
            "• Waifus are spawned by message activity, not a timer.\n"
            "• Rarities: common, rare, epic, legendary, unique.\n"
            "• Higher rarities are softly boosted by hidden pity.\n"
            "• Guarantee thresholds are also hidden to keep the game alive."
        ),
        "profile": (
            "⭐ <b>Profile</b>\n\n"
            "• Your profile shows level, collection, and personal settings.\n"
            "• Tabs split stats, collection, and the guide.\n"
            "• As you level up, the profile becomes more visually rich.\n"
            "• You can also set a favorite waifu and favorite category there."
        ),
        "collection": (
            "📚 <b>Collection and search</b>\n\n"
            "• /mywaifus — your collection.\n"
            "• /allwaifus — the full waifu catalog.\n"
            "• /searchwaifu — fast search by name, alias, or category.\n"
            "• Categories can be nested: franchises, anime, movies, and any subcategories."
        ),
        "rarity": (
            "💎 <b>Rarity and pity</b>\n\n"
            "• common, rare, epic, legendary, unique — five rarity tiers.\n"
            "• Higher rarity gets stronger visual treatment.\n"
            "• pity gently raises the chance of rare drops.\n"
            "• The system stays hidden so the chat feels natural."
        ),
        "commands": (
            "⌨️ <b>Commands</b>\n\n"
            "/start — greeting\n"
            "/help — this menu\n"
            "/profile — your profile\n"
            "/mywaifus — your collection\n"
            "/allwaifus — waifu catalog\n"
            "/searchwaifu — waifu search\n"
            "/language — user language\n"
            "/chatlanguage — chat language\n"
            "/chatcategories — chat categories\n\n"
            "The bot also reacts to waifu names directly in messages, no command required."
        ),
    },
}

SECTION_BUTTONS = (
    ("help:view:play", {"ru": "🎯 Игра", "en": "🎯 Game"}),
    ("help:view:spawn", {"ru": "🌸 Спавн", "en": "🌸 Spawn"}),
    ("help:view:profile", {"ru": "⭐ Профиль", "en": "⭐ Profile"}),
    ("help:view:collection", {"ru": "📚 Коллекция", "en": "📚 Collection"}),
    ("help:view:rarity", {"ru": "💎 Редкости", "en": "💎 Rarity"}),
    ("help:view:commands", {"ru": "⌨️ Команды", "en": "⌨️ Commands"}),
)


def _lang(user_lang: str) -> str:
    return "en" if user_lang.lower().startswith("en") else "ru"


def _build_help_keyboard(lang: str, section: str = "main") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if section == "main":
        for callback_data, labels in SECTION_BUTTONS:
            builder.button(text=labels.get(lang, labels["ru"]), callback_data=callback_data)
        builder.adjust(2)
    else:
        builder.button(
            text=("⬅️ Назад" if lang == "ru" else "⬅️ Back"),
            callback_data="help:view:main",
        )
        builder.button(
            text=("🏠 Главная" if lang == "ru" else "🏠 Home"),
            callback_data="help:view:main",
        )
        builder.adjust(2)

    return builder.as_markup()


def _build_help_text(lang: str, section: str = "main") -> str:
    texts = HELP_TEXTS.get(lang, HELP_TEXTS["ru"])
    return texts.get(section, texts["main"])


async def _render_help(message: Message, user_lang: str, section: str = "main") -> None:
    lang = _lang(user_lang)
    await message.answer(
        _build_help_text(lang, section),
        parse_mode="HTML",
        reply_markup=_build_help_keyboard(lang, section),
    )


@router.message(Command("help"))
async def help_command(message: Message):
    if not message.from_user:
        return

    user_lang = await get_user_language(message.from_user.id)
    await _render_help(message, user_lang, "main")


@router.callback_query(F.data.startswith("help:view:"))
async def help_section(call: CallbackQuery):
    if not call.message or not call.from_user:
        return

    user_lang = await get_user_language(call.from_user.id)
    lang = _lang(user_lang)
    section = call.data.split(":", 2)[2]
    if section not in HELP_TEXTS[lang]:
        section = "main"

    await call.message.edit_text(
        _build_help_text(lang, section),
        parse_mode="HTML",
        reply_markup=_build_help_keyboard(lang, section),
    )
    await call.answer()
