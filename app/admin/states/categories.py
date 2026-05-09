from aiogram.fsm.state import State, StatesGroup


class CategorySearch(StatesGroup):
    waiting_query = State()