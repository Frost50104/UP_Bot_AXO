from aiogram.fsm.state import State, StatesGroup

class RequestStates(StatesGroup):
    ChoosingDepartment = State()
    EnterAddress = State()
    EnterPhone = State()
    EnterIP = State()  # only for "Буква"
    DescribeProblem = State()
    WaitPhoto = State()
