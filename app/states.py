from aiogram.fsm.state import State, StatesGroup


class Verify(StatesGroup):
    phone = State()
    code = State()
