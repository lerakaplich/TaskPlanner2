from datetime import datetime

from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..states import RegistrationStates
from ..keyboards import get_main_keyboard, get_priority_keyboard, get_difficulty_keyboard


def register_tasks_handlers(dp, bot_instance):
    """Регистрация обработчиков задач"""

    @dp.message(Command("my_tasks"))
    async def cmd_my_tasks(message: types.Message, state: FSMContext):
        await state.clear()
        await bot_instance.show_my_tasks(message)

    @dp.message(Command("create_task"))
    async def cmd_create_task(message: types.Message, state: FSMContext):
        await state.clear()
        await bot_instance.start_create_task(message, state)

    @dp.message(lambda msg: msg.text == "✅ Мои задачи")
    async def btn_my_tasks(message: types.Message, state: FSMContext):
        await state.clear()
        await bot_instance.show_my_tasks(message)

    @dp.message(lambda msg: msg.text == "➕ Создать задачу")
    async def btn_create_task(message: types.Message, state: FSMContext):
        await state.clear()
        await bot_instance.start_create_task(message, state)

    @dp.message(RegistrationStates.waiting_for_task_deadline)
    async def process_deadline(message: types.Message, state: FSMContext):
        """Обработчик ввода дедлайна"""
        deadline_text = message.text.strip()

        if deadline_text.lower() == 'skip':
            deadline = None
        else:
            try:
                deadline = datetime.strptime(deadline_text, "%d.%m.%Y")
            except ValueError:
                await message.answer(
                    "❌ *Неверный формат даты*\n\n"
                    "Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\n"
                    "Например: 30.12.2026\n\n"
                    "Или отправьте 'skip', чтобы пропустить:",
                    parse_mode="Markdown"
                )
                return

        await state.update_data(deadline=deadline)

        # Выбор статуса
        data = await state.get_data()
        project_id = data.get('project_id')
        statuses = await bot_instance.task_service.get_statuses_for_project(project_id)

        if statuses:
            buttons = []
            for status in statuses:
                emoji = "✅" if status['is_done'] else "📌"
                buttons.append([InlineKeyboardButton(text=f"{emoji} {status['name']}",
                                                     callback_data=f"set_status|{status['id']}")])

            reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await message.answer(
                "📋 *Выберите статус задачи:*",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await bot_instance.ask_tags(message, state)

    @dp.callback_query(lambda c: c.data == "show_my_tasks")
    async def handle_show_tasks(callback: types.CallbackQuery):
        class FakeMessage:
            def __init__(self, chat, from_user):
                self.chat = chat
                self.from_user = from_user
            async def answer(self, *args, **kwargs):
                pass

        fake_msg = FakeMessage(callback.message.chat, callback.from_user)
        await bot_instance.show_my_tasks(fake_msg)

    @dp.callback_query(lambda c: c.data.startswith("tasks_page_"))
    async def handle_tasks_page(callback: types.CallbackQuery):
        page = int(callback.data.replace("tasks_page_", ""))

        # Создаем объект, имитирующий message, но с правильным from_user
        class FakeMessage:
            def __init__(self, callback_obj):
                self.chat = callback_obj.message.chat
                self.from_user = callback_obj.from_user  # Важно! Берем from_user из callback

            async def answer(self, text, **kwargs):
                # Отвечаем через callback.message
                await callback.message.answer(text, **kwargs)

        fake_msg = FakeMessage(callback)
        await bot_instance.show_my_tasks(fake_msg, page)
        await callback.answer()  # Обязательно!

    @dp.message(RegistrationStates.waiting_for_task_title)
    async def process_task_title(message: types.Message, state: FSMContext):
        """Обработчик ввода названия задачи"""
        title = message.text.strip()
        if len(title) < 3:
            await message.answer("❌ Название задачи должно содержать минимум 3 символа. Пожалуйста, введите название:")
            return

        await state.update_data(task_title=title)

        await message.answer(
            "📄 *Введите описание задачи:*\n\n"
            "Подробно опишите, что нужно сделать.",
            parse_mode="Markdown"
        )
        await state.set_state(RegistrationStates.waiting_for_task_description)



    @dp.message(RegistrationStates.waiting_for_task_description)
    async def process_task_description(message: types.Message, state: FSMContext):
        """Обработчик ввода описания задачи"""
        description = message.text.strip()
        await state.update_data(task_description=description)

        # Выбор исполнителя
        employees = await bot_instance.user_service.get_employees_list()

        if employees:
            buttons = []
            for emp in employees[:20]:
                buttons.append([InlineKeyboardButton(text=emp['name'], callback_data=f"select_executor|{emp['id']}")])
            buttons.append([InlineKeyboardButton(text="👤 Назначить себя", callback_data="select_executor|self")])
            buttons.append([InlineKeyboardButton(text="⏩ Пропустить", callback_data="select_executor|skip")])

            reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await message.answer(
                "👤 *Выберите исполнителя:*",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await state.update_data(assigned_to=None)
            await bot_instance.ask_priority(message, state)