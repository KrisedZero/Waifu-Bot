chat_counters = {}

SPAWN_THRESHOLD = 100


def init_chat(chat_id: int):
    if chat_id not in chat_counters:
        chat_counters[chat_id] = 0


def increment_counter(chat_id: int):
    init_chat(chat_id)
    chat_counters[chat_id] += 1
    return chat_counters[chat_id]


def reset_counter(chat_id: int):
    chat_counters[chat_id] = 0


def handle_message(chat_id: int):
    count = increment_counter(chat_id)

    if count >= SPAWN_THRESHOLD:
        reset_counter(chat_id)
        return "spawn"

    return None