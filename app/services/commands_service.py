from aiogram import Bot
from aiogram.types import BotCommand
from aiogram.types import BotCommandScopeDefault
from aiogram.types import BotCommandScopeAllPrivateChats
from aiogram.types import BotCommandScopeAllGroupChats


PRIVATE_COMMANDS_RU = [
    BotCommand(command="start", description="👋 Приветствие"),
    BotCommand(command="help", description="❓ Как играть"),
    BotCommand(command="profile", description="👤 Профиль"),
    BotCommand(command="mywaifus", description="📦 Моя коллекция"),
    BotCommand(command="allwaifus", description="📚 Все вайфу"),
    BotCommand(command="searchwaifu", description="🔍 Поиск вайфу"),
    BotCommand(command="language", description="🌍 Язык пользователя"),
]

PRIVATE_COMMANDS_EN = [
    BotCommand(command="start", description="👋 Greeting"),
    BotCommand(command="help", description="❓ How to play"),
    BotCommand(command="profile", description="👤 Profile"),
    BotCommand(command="mywaifus", description="📦 My collection"),
    BotCommand(command="allwaifus", description="📚 All waifus"),
    BotCommand(command="searchwaifu", description="🔍 Search waifu"),
    BotCommand(command="language", description="🌍 User language"),
]

GROUP_COMMANDS_RU = [
    BotCommand(command="help", description="❓ Как играть"),
    BotCommand(command="profile", description="👤 Профиль"),
    BotCommand(command="mywaifus", description="📦 Моя коллекция"),
    BotCommand(command="allwaifus", description="📚 Все вайфу"),
    BotCommand(command="searchwaifu", description="🔍 Поиск вайфу"),
    BotCommand(command="chatlanguage", description="🌍 Язык чата"),
    BotCommand(command="language", description="🌍 Язык пользователя"),
    BotCommand(command="chatcategories", description="🗄 Категории чата"),
]

GROUP_COMMANDS_EN = [
    BotCommand(command="help", description="❓ How to play"),
    BotCommand(command="profile", description="👤 Profile"),
    BotCommand(command="mywaifus", description="📦 My collection"),
    BotCommand(command="allwaifus", description="📚 All waifus"),
    BotCommand(command="searchwaifu", description="🔍 Search waifu"),
    BotCommand(command="chatlanguage", description="🌍 Chat language"),
    BotCommand(command="language", description="🌍 User language"),
    BotCommand(command="chatcategories", description="🗄 Chat categories"),
]


async def setup_bot_commands(bot: Bot) -> None:
    # fallback для всех пользователей, если нет языка/специфичных команд
    await bot.set_my_commands(
        PRIVATE_COMMANDS_EN,
        scope=BotCommandScopeDefault(),
    )

    # private chats
    await bot.set_my_commands(
        PRIVATE_COMMANDS_RU,
        scope=BotCommandScopeAllPrivateChats(),
        language_code="ru",
    )
    await bot.set_my_commands(
        PRIVATE_COMMANDS_EN,
        scope=BotCommandScopeAllPrivateChats(),
        language_code="en",
    )

    # group chats
    await bot.set_my_commands(
        GROUP_COMMANDS_RU,
        scope=BotCommandScopeAllGroupChats(),
        language_code="ru",
    )
    await bot.set_my_commands(
        GROUP_COMMANDS_EN,
        scope=BotCommandScopeAllGroupChats(),
        language_code="en",
    )