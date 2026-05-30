from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_for_reset_phone = State()
    waiting_for_new_password = State()
    waiting_for_help_message = State()
    waiting_for_task_project = State()
    waiting_for_task_title = State()
    waiting_for_task_description = State()
    waiting_for_task_executor = State()
    waiting_for_task_priority = State()
    waiting_for_task_difficulty = State()
    waiting_for_task_deadline = State()
    waiting_for_task_tags = State()
    waiting_for_task_status = State()