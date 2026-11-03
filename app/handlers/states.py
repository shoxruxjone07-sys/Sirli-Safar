from aiogram.fsm.state import State, StatesGroup


class AdminSt(StatesGroup):
    password = State()


class TaskAdd(StatesGroup):
    stage = State()
    kind = State()
    question = State()
    options = State()
    correct = State()
    time = State()


class TaskEdit(StatesGroup):
    value = State()


class TrapAdd(StatesGroup):
    stage = State()
    prompt = State()
    time = State()


class TrapEdit(StatesGroup):
    value = State()


class TrapOwn(StatesGroup):
    text = State()
    time = State()


class StoryEdit(StatesGroup):
    value = State()
    media = State()


class SettingEdit(StatesGroup):
    value = State()
    gif = State()
