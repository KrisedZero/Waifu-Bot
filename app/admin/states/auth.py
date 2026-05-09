from aiogram.fsm.state import State, StatesGroup


class AdminAuthStates(StatesGroup):
    waiting_password = State()
    waiting_new_password = State()


class AdminCategoryStates(StatesGroup):
    waiting_name_ru = State()
    waiting_name_en = State()
    waiting_parent = State()
    waiting_node_type = State()
    waiting_sort_order = State()
    waiting_confirm_create = State()

    waiting_edit_id = State()
    waiting_edit_field = State()
    waiting_edit_value = State()
    waiting_edit_confirm = State()

    waiting_delete_id = State()
    waiting_delete_confirm = State()


class AdminWaifuStates(StatesGroup):
    waiting_category = State()
    waiting_name_ru = State()
    waiting_name_en = State()
    waiting_rarity = State()
    waiting_gender = State()
    waiting_media_type = State()
    waiting_media = State()
    waiting_confirm_create = State()

    waiting_edit_id = State()
    waiting_edit_field = State()
    waiting_edit_value = State()
    waiting_edit_media_type = State()
    waiting_edit_media = State()
    waiting_edit_confirm = State()

    waiting_delete_id = State()
    waiting_delete_confirm = State()
