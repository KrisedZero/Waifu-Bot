active_spawns = {}


def set_active_spawn(chat_id: int, waifu: dict):
    active_spawns[chat_id] = {
        "waifu": waifu,
        "messages_left": 20
    }


def get_active_spawn(chat_id: int):
    return active_spawns.get(chat_id)


def tick_spawn(chat_id: int):
    spawn = active_spawns.get(chat_id)
    if not spawn:
        return None

    spawn["messages_left"] -= 1

    if spawn["messages_left"] <= 0:
        return clear_spawn(chat_id)

    return spawn


def clear_spawn(chat_id: int):
    return active_spawns.pop(chat_id, None)

