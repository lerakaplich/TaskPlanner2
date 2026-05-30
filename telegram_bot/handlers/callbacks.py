from aiogram import types
from aiogram.fsm.context import FSMContext
from datetime import datetime
from sqlalchemy import text
from database import get_employees_session, get_tasks_session
from models.employees import Employee, EmployeeData
from shared_state import pending_registrations
from ..states import RegistrationStates
from ..keyboards import get_main_keyboard
from ..utils import get_employee_id_by_chat


def register_callback_handlers(dp, bot_instance):
    """Регистрация callback обработчиков"""

    @dp.callback_query(lambda c: c.data.startswith("select_project|"))
    async def handle_project_selection(callback: types.CallbackQuery, state: FSMContext):
        project_id = int(callback.data.replace("select_project|", ""))
        await state.update_data(project_id=project_id)

        await callback.message.edit_text(
            "📝 *Введите название задачи:*\n\n"
            "Например: Исправить баг в авторизации",
            parse_mode="Markdown"
        )
        await state.set_state(RegistrationStates.waiting_for_task_title)

    @dp.callback_query(lambda c: c.data == "cancel_task_creation")
    async def handle_cancel_creation(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.edit_text(
            "✅ *Создание задачи отменено*",
            parse_mode="Markdown"
        )
        await callback.message.answer(
            "Используйте кнопки ниже для работы с ботом:",
            reply_markup=get_main_keyboard()
        )

    @dp.callback_query(lambda c: c.data.startswith("select_executor|"))
    async def process_executor_selection(callback: types.CallbackQuery, state: FSMContext):
        data = callback.data.replace("select_executor|", "")

        if data == "self":
            user_id = callback.from_user.id
            with get_employees_session() as emp_session:
                select_stmt = text("SELECT id FROM public.employees WHERE chat_id = :chat_id")
                employee = emp_session.execute(select_stmt, {'chat_id': user_id}).first()
                assigned_to = employee[0] if employee else None
        elif data == "skip":
            assigned_to = None
        else:
            assigned_to = int(data)

        await state.update_data(assigned_to=assigned_to)
        await callback.message.edit_text("✅ Исполнитель выбран")
        await bot_instance.ask_priority(callback.message, state)

    @dp.callback_query(lambda c: c.data.startswith("set_priority|"))
    async def process_priority(callback: types.CallbackQuery, state: FSMContext):
        priority = callback.data.replace("set_priority|", "")
        await state.update_data(priority=priority)
        await callback.message.edit_text(f"✅ Приоритет: {priority}")

        from ..keyboards import get_difficulty_keyboard
        await callback.message.answer(
            "📊 *Выберите сложность задачи (1-5):*",
            parse_mode="Markdown",
            reply_markup=get_difficulty_keyboard()
        )

    @dp.callback_query(lambda c: c.data.startswith("set_difficulty|"))
    async def process_difficulty(callback: types.CallbackQuery, state: FSMContext):
        difficulty = int(callback.data.replace("set_difficulty|", ""))
        await state.update_data(difficulty=difficulty)
        await callback.message.edit_text(f"✅ Сложность: {difficulty} ⭐")

        # Переходим к вводу дедлайна
        await callback.message.answer(
            "📅 *Введите дедлайн задачи* (в формате ДД.ММ.ГГГГ)\n\n"
            "Например: 30.12.2026\n\n"
            "Или отправьте 'skip', чтобы пропустить:",
            parse_mode="Markdown"
        )
        await state.set_state(RegistrationStates.waiting_for_task_deadline)
        # Не вызываем callback.answer() здесь, так как дальше идёт ожидание ввода

    @dp.callback_query(lambda c: c.data.startswith("set_status|"))
    async def process_status(callback: types.CallbackQuery, state: FSMContext):
        status_id = int(callback.data.replace("set_status|", ""))
        await state.update_data(status_id=status_id)
        await callback.message.edit_text("✅ Статус выбран")
        await bot_instance.ask_tags(callback.message, state)

    @dp.callback_query(lambda c: c.data.startswith("add_tag|"))
    async def process_add_tag(callback: types.CallbackQuery, state: FSMContext):
        tag_name = callback.data.replace("add_tag|", "")
        data = await state.get_data()
        selected_tags = data.get('selected_tags', [])

        if tag_name not in selected_tags:
            selected_tags.append(tag_name)
            await state.update_data(selected_tags=selected_tags)
            await callback.answer(f"✅ Тег '{tag_name}' добавлен", show_alert=False)
        else:
            await callback.answer(f"ℹ️ Тег '{tag_name}' уже добавлен", show_alert=False)

    @dp.callback_query(lambda c: c.data == "tags_done")
    async def process_tags_done(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.edit_text("✅ Выбор тегов завершен")
        await bot_instance.finish_task_creation(callback, state, callback.from_user.id)

    @dp.callback_query(lambda c: c.data.startswith("approve|"))
    async def approve_registration(callback: types.CallbackQuery):
        request_id = callback.data.replace("approve|", "")
        registration_data = pending_registrations.get(request_id)

        if not registration_data:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        password = bot_instance.user_service.generate_password()
        password_hash = bot_instance.user_service.hash_password(password)

        phone_number = registration_data.get('phone_number')
        if phone_number:
            bot_instance.user_passwords[phone_number] = password

        with get_employees_session() as emp_session:
            try:
                from sqlalchemy import func
                max_number = emp_session.query(func.max(Employee.number)).scalar()
                next_number = (max_number + 1) if max_number else 1

                insert_stmt = text("""
                    INSERT INTO public.employees (
                        number, last_name, first_name, middle_name, 
                        position, phone_number, email,
                        birth_date, department_id, division_id, organization_id,
                        chat_id, work_number
                    ) VALUES (
                        :number, :last_name, :first_name, :middle_name,
                        :position, :phone_number, :email,
                        :birth_date, :department_id, :division_id, :organization_id,
                        :chat_id, :work_number
                    )
                    RETURNING id
                """)
                result = emp_session.execute(insert_stmt, {
                    'number': next_number,
                    'last_name': registration_data.get('last_name'),
                    'first_name': registration_data.get('first_name'),
                    'middle_name': registration_data.get('middle_name'),
                    'position': registration_data.get('position'),
                    'phone_number': registration_data.get('phone_number'),
                    'email': registration_data.get('email'),
                    'birth_date': registration_data.get('birth_date'),
                    'department_id': registration_data.get('department_id'),
                    'division_id': registration_data.get('division_id'),
                    'organization_id': 1,
                    'chat_id': registration_data.get('chat_id'),
                    'work_number': registration_data.get('work_number')
                })
                emp_session.commit()
                new_employee_id = result.scalar()

                with get_tasks_session() as tasks_session:
                    insert_data_stmt = text("""
                        INSERT INTO public.employees_data (employee_id, is_active, role, password_hash, created_at, updated_at)
                        VALUES (:employee_id, true, 'user', :password_hash, NOW(), NOW())
                    """)
                    tasks_session.execute(insert_data_stmt, {
                        'employee_id': new_employee_id,
                        'password_hash': password_hash
                    })
                    tasks_session.commit()

            except Exception as e:
                emp_session.rollback()
                await callback.answer(f"Ошибка: {e}", show_alert=True)
                return

        user_chat_id = registration_data.get('chat_id')
        if user_chat_id:
            try:
                await bot_instance.bot.send_message(
                    user_chat_id,
                    f"✅ *Ваша заявка на регистрацию одобрена!*\n\n"
                    f"📞 *Телефон:* {registration_data.get('phone_number')}\n"
                    f"🔐 *Пароль:* `{password}`\n\n"
                    f"⚠️ *Сохраните этот пароль!*\n\n"
                    f"📅 Я буду присылать вам напоминания о задачах каждый день в 9:00.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"❌ Ошибка отправки уведомления пользователю: {e}")

        await callback.message.edit_text(
            f"✅ *Заявка одобрена!*\n\n"
            f"Пользователь {registration_data.get('last_name')} {registration_data.get('first_name')} зарегистрирован.\n",
            parse_mode="Markdown"
        )
        pending_registrations.pop(request_id, None)
        await callback.answer("✅ Заявка одобрена")

    @dp.callback_query(lambda c: c.data.startswith("reject|"))
    async def reject_registration(callback: types.CallbackQuery):
        request_id = callback.data.replace("reject|", "")
        registration_data = pending_registrations.get(request_id)

        if registration_data:
            user_chat_id = registration_data.get('chat_id')
            phone_number = registration_data.get('phone_number')
            if phone_number and phone_number in bot_instance.user_passwords:
                del bot_instance.user_passwords[phone_number]

            if user_chat_id:
                try:
                    await bot_instance.bot.send_message(
                        user_chat_id,
                        f"❌ *Ваша заявка на регистрацию отклонена.*\n\n"
                        f"Пожалуйста, свяжитесь с администратором.",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    print(f"❌ Ошибка отправки уведомления пользователю: {e}")

            await callback.message.edit_text(
                f"❌ *Заявка отклонена*\n\n"
                f"Пользователь {registration_data.get('last_name')} {registration_data.get('first_name')} получил уведомление.",
                parse_mode="Markdown"
            )
            pending_registrations.pop(request_id, None)

        await callback.answer("❌ Заявка отклонена")