from aiogram.fsm.state import State, StatesGroup


class WaifuSearch(StatesGroup):
    waiting_query = State()


class WaifuCategoryPick(StatesGroup):
    waiting_query = State()


class AdminWaifuStates(StatesGroup):
    waiting_category = State()
    waiting_name_ru = State()
    waiting_name_en = State()
    waiting_rarity = State()
    waiting_gender = State()
    waiting_media_type = State()
    waiting_media = State()
    waiting_confirm_create = State()

    waiting_edit_field = State()
    waiting_edit_value = State()
    waiting_edit_media_type = State()
    waiting_edit_media = State()
    waiting_edit_confirm = State()
