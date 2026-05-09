import random
import html


RARITY_STYLE = {
    "ru": {
        "common": {
            "badge": "✨",
            "prefix": "Обычное появление:",
            "spawn_boost": "",
            "despawn_boost": "",
            "claim_boost": "",
        },
        "rare": {
            "badge": "💠",
            "prefix": "Что-то редкое витает в воздухе:",
            "spawn_boost": "",
            "despawn_boost": "",
            "claim_boost": "",
        },
        "epic": {
            "badge": "🔥",
            "prefix": "Сцена начинает накаляться:",
            "spawn_boost": "",
            "despawn_boost": "",
            "claim_boost": "",
        },
        "legendary": {
            "badge": "🌟",
            "prefix": "Легендарное появление:",
            "spawn_boost": "",
            "despawn_boost": "",
            "claim_boost": "",
        },
        "unique": {
            "badge": "👑",
            "prefix": "Всё внимание — сюда:",
            "spawn_boost": "",
            "despawn_boost": "",
            "claim_boost": "",
        },
    },
    "en": {
        "common": {
            "badge": "✨",
            "prefix": "A normal appearance:",
            "spawn_boost": "",
            "despawn_boost": "",
            "claim_boost": "",
        },
        "rare": {
            "badge": "💠",
            "prefix": "Something rare is in the air:",
            "spawn_boost": "",
            "despawn_boost": "",
            "claim_boost": "",
        },
        "epic": {
            "badge": "🔥",
            "prefix": "The scene is heating up:",
            "spawn_boost": "",
            "despawn_boost": "",
            "claim_boost": "",
        },
        "legendary": {
            "badge": "🌟",
            "prefix": "A legendary appearance:",
            "spawn_boost": "",
            "despawn_boost": "",
            "claim_boost": "",
        },
        "unique": {
            "badge": "👑",
            "prefix": "Everyone, pay attention:",
            "spawn_boost": "",
            "despawn_boost": "",
            "claim_boost": "",
        },
    },
}


BASE_MESSAGES = {
    "ru": {
        "spawn": [
            "Кажется, кто-то появился...",
            "Ты чувствуешь это?",
            "В чате появилась загадочная фигура...",
            "Кто-то наблюдает за вами...",
            "Что-то изменилось...",
            "Тень мелькнула в чате...",
            "Кажется, это кто-то особенный...",
            "Вайфу появилась, но кто же это?",
            "Кто скрывается за этим образом?",
            "Кто-то хочет, чтобы его нашли...",
        ],
        "despawn": [
            "Она устала ждать и ушла...",
            "Никто её не позвал...",
            "Она растворилась в воздухе...",
            "Слишком долго...",
            "Она больше не ждёт...",
            "И след простыл...",
            "Вы её упустили...",
            "Она ушла в другой мир...",
            "Свобода зовёт...",
            "Она ждала... но зря...",
        ],
        "claim": [
            "Ты получил вайфу:",
            "Теперь она твоя:",
            "Отличный выбор!",
            "Поздравляем!",
            "Ты заполучил её:",
            "Удача на твоей стороне:",
            "Новая вайфу добавлена:",
            "Она выбрала тебя:",
            "Ты не упустил шанс:",
            "Судьба свела вас:",
        ],
    },
    "en": {
        "spawn": [
            "Someone seems to have appeared...",
            "Can you feel it?",
            "A mysterious figure entered the chat...",
            "Someone is watching you...",
            "Something has changed...",
            "A shadow flashed in the chat...",
            "It looks like someone special...",
            "A waifu has appeared, but who is it?",
            "Who is hiding behind this silhouette?",


"Someone wants to be found...",
        ],
        "despawn": [
            "She got tired of waiting and left...",
            "Nobody called her...",
            "She dissolved into the air...",
            "Too much time passed...",
            "She is no longer waiting...",
            "And then she was gone...",
            "You missed her...",
            "She went to another world...",
            "Freedom is calling...",
            "She waited... but in vain...",
        ],
        "claim": [
            "You got the waifu:",
            "Now she is yours:",
            "Great choice!",
            "Congratulations!",
            "You have claimed her:",
            "Luck is on your side:",
            "New waifu added:",
            "She chose you:",
            "You did not miss your chance:",
            "Fate brought you together:",
        ],
    },
}


def _decorate(lang: str, rarity: str, text: str) -> str:
    lang = lang if lang in ("ru", "en") else "ru"
    rarity = rarity if rarity in RARITY_STYLE[lang] else "common"

    style = RARITY_STYLE[lang][rarity]
    badge = style["badge"]
    prefix = style["prefix"]

    return f"{badge} {prefix} {text}".strip()


def get_spawn_text(rarity: str = "common", lang: str = "ru") -> str:
    base = random.choice(BASE_MESSAGES.get(lang, BASE_MESSAGES["ru"])["spawn"])
    return _decorate(lang, rarity, base)


def get_despawn_text(name: str, rarity: str = "common", lang: str = "ru") -> str:
    base = random.choice(BASE_MESSAGES.get(lang, BASE_MESSAGES["ru"])["despawn"])
    rarity_text = format_rarity(rarity)
    text = f"{base} <i>{html.escape(name)}</i> — {rarity_text}"
    return _decorate(lang, rarity, text)


def get_claim_text(name: str, rarity: str = "common", lang: str = "ru") -> str:
    base = random.choice(BASE_MESSAGES.get(lang, BASE_MESSAGES["ru"])["claim"])
    rarity_text = format_rarity(rarity)
    text = f"{base} <i>{html.escape(name)}</i> — {rarity_text}"
    return _decorate(lang, rarity, text)


def format_rarity(rarity: str) -> str:
    mapping = {
        "common": "<b>Common</b>",
        "rare": "<b>Rare</b>",
        "epic": "<b>Epic</b>",
        "legendary": "<b>Legendary</b>",
        "unique": "<b>Unique💎</b>",
    }
    return mapping.get(rarity, f"<b>{html.escape(rarity)}</b>")