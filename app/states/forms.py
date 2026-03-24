from aiogram.fsm.state import State, StatesGroup


class PhotoForm(StatesGroup):
    waiting_photo = State()


class BioForm(StatesGroup):
    waiting_bio = State()


class BroadcastForm(StatesGroup):
    waiting_text = State()
    waiting_photo = State()
    waiting_video = State()
    waiting_confirm = State()
