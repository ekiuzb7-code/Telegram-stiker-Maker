from aiogram.fsm.state import State, StatesGroup


class PickColor(StatesGroup):
    color = State()


class CreatePack(StatesGroup):
    title = State()
    emoji = State()