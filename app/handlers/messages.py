import html
from aiogram import Router, F
from aiogram.types import Message

from app.services.user_service import (
    create_user_if_not_exists,
    get_user_language,
)
from app.services.counter_service import handle_message
from app.services.spawn_service import (
    set_active_spawn,
    get_active_spawn,
    tick_spawn,
)
from app.services.claim_service import try_claim_waifu
from app.services.waifu_service import get_waifu_media
from app.services.waifu_media import send_waifu_media
from app.services.texts import (
    get_spawn_text,
    get_claim_text,
    get_despawn_text,
)
from app.services.pity_service import (
    roll_rarity_with_pity,
    apply_pity_after_roll,
)
from app.services.gacha_service import (
    get_random_allowed_waifu,
    get_random_allowed_waifu_by_rarity,
)
from app.services.chat_settings_service import (
    ensure_chat_settings,
    get_chat_language,
    get_chat_pity,
    update_chat_pity,
)
from app.middlewares.antispam import AntiSpamMiddleware

router = Router()
router.message.middleware(AntiSpamMiddleware(cooldown=1.0))

LEVEL_UP_TEXT = {
    "ru": "🎉 <b>Новый уровень!</b> {user} получил <b>{level}</b> уровень. Поздравляем!",
    "en": "🎉 <b>Level up!</b> {user} reached <b>level {level}</b>. Congratulations!",
}

WELCOME_TEXT = {
    "ru": (
        "👋 <b>Вайфу-бот на месте!</b>\n\n"
        "✨ Теперь в этом чате может появляться вайфу.\n"
        "💖 Пиши сообщения, угадывай имя и собирай коллекцию.\n"
        "📖 Для подсказки жми /help."
    ),
    "en": (
        "👋 <b>Waifu bot is here!</b>\n\n"
        "✨ Waifus can now appear in this chat.\n"
        "💖 Send messages, guess the name, and build your collection.\n"
        "📖 Use /help for a quick guide."
    ),
}


def get_display_name(waifu: dict, lang: str) -> str:
    if lang == "ru" and waifu.get("name_ru"):
        return waifu["name_ru"]
    return waifu.get("name_en") or waifu.get("name_ru") or "—"


@router.message(F.new_chat_members)
async def welcome_on_added(message: Message):
    if not message.new_chat_members:
        return

    me = await message.bot.get_me()
    if not any(member.id == me.id for member in message.new_chat_members):
        return

    inviter_lang = "ru"
    if message.from_user:
        await create_user_if_not_exists(
            message.from_user.id,
            message.from_user.language_code or "ru",
            message.from_user.username,
        )
        inviter_lang = await get_user_language(message.from_user.id)

    await ensure_chat_settings(message.chat.id, default_language=inviter_lang)
    chat_lang = await get_chat_language(message.chat.id)
    text = WELCOME_TEXT.get(chat_lang, WELCOME_TEXT["ru"])

    await message.answer(text, parse_mode="HTML")


@router.message(F.text & ~F.text.startswith("/"))
async def all_messages_handler(message: Message):
    if not message.from_user:
        return

    # Игровая логика работает только в группах и супергруппах
    if message.chat.type not in {"group", "supergroup"}:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    telegram_lang = message.from_user.language_code or "ru"
    await create_user_if_not_exists(user_id, telegram_lang, message.from_user.username)

    user_lang = await get_user_language(user_id)

    await ensure_chat_settings(chat_id, default_language=user_lang)
    chat_lang = await get_chat_language(chat_id)

    text_input = message.text.strip()

    active_spawn = get_active_spawn(chat_id)
    if active_spawn:
        claimed, claimed_waifu, level_info = await try_claim_waifu(chat_id, user_id, text_input)

        if claimed and claimed_waifu:
            claim_name = get_display_name(claimed_waifu, user_lang)
            claim_text = get_claim_text(claim_name, claimed_waifu["rarity"], user_lang)

            await message.answer(claim_text, parse_mode="HTML")

            if level_info and int(level_info.get("new_level", 0)) > int(level_info.get("previous_level", 0)):
                user_display = html.escape(message.from_user.full_name if message.from_user else "Player")
                level_text = LEVEL_UP_TEXT.get(chat_lang, LEVEL_UP_TEXT["ru"]).format(
                    user=user_display,
                    level=int(level_info["new_level"]),
                )
                await message.answer(level_text, parse_mode="HTML")
            return

        tick_spawn(chat_id)

        if not get_active_spawn(chat_id):
            despawn_waifu = active_spawn["waifu"]
            despawn_name = get_display_name(despawn_waifu, chat_lang)
            despawn_text = get_despawn_text(
                despawn_name,
                despawn_waifu["rarity"],
                chat_lang,
            )

            await message.answer(despawn_text, parse_mode="HTML")
            return

        return

    event = handle_message(chat_id)

    if event != "spawn":
        return

    pity = await get_chat_pity(chat_id)

    rolled_rarity = roll_rarity_with_pity(
        pity["pity_epic"],
        pity["pity_legendary"],
        pity["pity_unique"],
    )

    waifu = await get_random_allowed_waifu_by_rarity(chat_id, rolled_rarity)

    if not waifu:
        waifu = await get_random_allowed_waifu(chat_id)

    if not waifu:
        if chat_lang == "ru":
            await message.answer("❌ Нет доступных вайфу для текущих категорий чата")
        else:
            await message.answer("❌ No waifus are available for the current chat categories")
        return

    actual_rarity = waifu["rarity"]

    new_pity_epic, new_pity_legendary, new_pity_unique = apply_pity_after_roll(
        pity["pity_epic"],
        pity["pity_legendary"],
        pity["pity_unique"],
        actual_rarity,
    )
    await update_chat_pity(chat_id, new_pity_epic, new_pity_legendary, new_pity_unique)

    set_active_spawn(chat_id, waifu)

    media = await get_waifu_media(waifu["id"])
    spawn_text = get_spawn_text(actual_rarity, chat_lang)

    if waifu.get("is_active", True) and media:
        sent = await send_waifu_media(message, media, spawn_text)
        if sent:
            return

    await message.answer(spawn_text)
