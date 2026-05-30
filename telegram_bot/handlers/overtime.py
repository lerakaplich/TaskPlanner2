# telegram_bot/handlers/overtime.py

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from sqlalchemy import text
from database import get_employees_session, get_tasks_session
from ..states import RegistrationStates
from ..keyboards import get_main_keyboard
from ..utils import get_phone_by_chat


class OvertimeStates(StatesGroup):
    waiting_for_description = State()


async def get_user_id_by_chat(chat_id: int) -> Optional[int]:
    """Получить ID сотрудника по chat_id"""
    with get_employees_session() as emp_session:
        select_stmt = text("SELECT id FROM public.employees WHERE chat_id = :chat_id")
        employee = emp_session.execute(select_stmt, {'chat_id': chat_id}).first()
        return employee[0] if employee else None


async def get_employee_name(employee_id: int) -> str:
    """Получить имя сотрудника"""
    with get_employees_session() as emp_session:
        select_stmt = text("SELECT last_name, first_name FROM public.employees WHERE id = :id")
        employee = emp_session.execute(select_stmt, {'id': employee_id}).first()
        if employee:
            return f"{employee.last_name} {employee.first_name[0]}."
        return str(employee_id)


async def get_my_overtimes(employee_id: int, start_date: date = None, end_date: date = None) -> List[Dict]:
    """Получить переработки сотрудника"""
    with get_employees_session() as emp_session:
        if start_date and end_date:
            query = text("""
                SELECT id, number, note_text, overtime_date, overtime_start, overtime_end,
                       EXTRACT(EPOCH FROM (overtime_end - overtime_start)) / 3600.0 as duration_hours
                FROM public.employee_notes
                WHERE employee_id = :employee_id AND overtime_date BETWEEN :start_date AND :end_date
                ORDER BY overtime_date DESC, overtime_start DESC
            """)
            rows = emp_session.execute(query, {
                'employee_id': employee_id,
                'start_date': start_date,
                'end_date': end_date
            }).fetchall()
        else:
            query = text("""
                SELECT id, number, note_text, overtime_date, overtime_start, overtime_end,
                       EXTRACT(EPOCH FROM (overtime_end - overtime_start)) / 3600.0 as duration_hours
                FROM public.employee_notes
                WHERE employee_id = :employee_id
                ORDER BY overtime_date DESC, overtime_start DESC
                LIMIT 50
            """)
            rows = emp_session.execute(query, {'employee_id': employee_id}).fetchall()

        result = []
        for row in rows:
            result.append({
                "id": row.id,
                "number": row.number,
                "note_text": row.note_text or "",
                "overtime_date": row.overtime_date,
                "overtime_start": row.overtime_start,
                "overtime_end": row.overtime_end,
                "duration_hours": float(row.duration_hours) if row.duration_hours else 0.0
            })
        return result


async def update_overtime_description(note_id: int, description: str) -> bool:
    """Обновить описание переработки"""
    with get_employees_session() as emp_session:
        try:
            emp_session.execute(
                text("UPDATE public.employee_notes SET note_text = :note_text WHERE id = :id"),
                {'note_text': description, 'id': note_id}
            )
            emp_session.commit()
            return True
        except Exception as e:
            print(f"[BOT] Ошибка обновления описания: {e}")
            return False


def get_current_month_period(today: date = None) -> tuple:
    """Возвращает период для текущего месяца"""
    if today is None:
        today = date.today()

    if today.day >= 25:
        display_month = today.month + 1 if today.month < 12 else 1
        display_year = today.year if today.month < 12 else today.year + 1
        start_date = date(today.year, today.month, 25)
        end_date = date(display_year, display_month, 24)
    else:
        current_month = today.month
        current_year = today.year
        if current_month == 1:
            start_month = 12
            start_year = current_year - 1
        else:
            start_month = current_month - 1
            start_year = current_year
        start_date = date(start_year, start_month, 25)
        end_date = date(current_year, current_month, 24)

    return start_date, end_date, end_date.month, end_date.year


def get_current_display_month() -> tuple:
    """Возвращает отображаемый текущий месяц и год"""
    _, _, month, year = get_current_month_period()
    return month, year


def get_month_period_by_month(month: int, year: int) -> tuple:
    """Возвращает период для выбранного месяца"""
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    start_date = date(prev_year, prev_month, 25)
    end_date = date(year, month, 24)
    return start_date, end_date


async def get_month_name(month: int) -> str:
    months = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }
    return months.get(month, str(month))


def format_duration(duration_hours: float) -> str:
    hours = int(duration_hours)
    minutes = int((duration_hours - hours) * 60)
    if minutes > 0:
        return f"{hours} ч {minutes} мин"
    return f"{hours} ч"


def register_overtime_handlers(dp, bot_instance):
    """Регистрация обработчиков переработок"""

    @dp.message(Command("overtime"))
    async def cmd_overtime(message: types.Message, state: FSMContext):
        chat_id = message.chat.id

        # Проверяем авторизацию
        with get_employees_session() as emp_session:
            select_stmt = text("SELECT id FROM public.employees WHERE chat_id = :chat_id")
            employee = emp_session.execute(select_stmt, {'chat_id': chat_id}).first()

            if not employee:
                await message.answer(
                    "🔐 *Для работы с переработками необходимо авторизоваться*\n\n"
                    "Используйте /start для привязки аккаунта",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
                return

            user_id = employee[0]

        await state.update_data(employee_id=user_id)

        start_date, end_date, _, _ = get_current_month_period()
        overtimes = await get_my_overtimes(user_id, start_date, end_date)

        total_hours = sum(o['duration_hours'] for o in overtimes)
        total_days = len(overtimes)

        total_str = format_duration(total_hours)

        target_month = end_date.month
        target_year = end_date.year
        month_name = await get_month_name(target_month)

        period_text = f"{start_date.strftime('%d.%m')} — {end_date.strftime('%d.%m')}"
        employee_name = await get_employee_name(user_id)

        # ИСПРАВЛЕНО: переименовано с 'text' на 'message_text'
        message_text = (
            "📊 *Мои переработки*\n\n"
            f"👤 *Сотрудник:* `{employee_name}`\n"
            f"📅 *Период:* `{period_text}` ({month_name} {target_year})\n"
            f"📈 *Количество:* `{total_days}`\n"
            f"⏱️ *Общая сумма:* `{total_str}`\n\n"
            "Выберите действие:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Текущий месяц", callback_data="overtime_this_month")],
            [InlineKeyboardButton(text="📆 Другой месяц", callback_data="overtime_select_month")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="overtime_close")]
        ])

        await message.answer(message_text, reply_markup=keyboard, parse_mode="Markdown")

    @dp.message(lambda msg: msg.text == "⏱️ Переработки")
    async def btn_overtime(message: types.Message, state: FSMContext):
        await cmd_overtime(message, state)

    @dp.callback_query(lambda c: c.data == "overtime_close")
    async def overtime_close(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.delete()
        await callback.answer()

    @dp.callback_query(lambda c: c.data == "overtime_this_month")
    async def overtime_this_month(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        employee_id = data.get('employee_id')

        start_date, end_date, _, _ = get_current_month_period()
        overtimes = await get_my_overtimes(employee_id, start_date, end_date)

        target_month = end_date.month
        target_year = end_date.year
        month_name = await get_month_name(target_month)

        await show_overtime_group(
            callback.message, overtimes,
            f"📅 {month_name} {target_year} (с {start_date.day}.{start_date.month} по {end_date.day}.{end_date.month})",
            start_date, end_date, state
        )
        await callback.answer()

    @dp.callback_query(lambda c: c.data == "overtime_select_month")
    async def overtime_select_month(callback: types.CallbackQuery, state: FSMContext):
        current_year = datetime.now().year
        current_display_month, current_display_year = get_current_display_month()

        data = await state.get_data()
        employee_id = data.get('employee_id')

        await state.update_data(current_year=current_year)

        builder = InlineKeyboardBuilder()

        for month in range(1, 13):
            month_name = await get_month_name(month)
            start, end = get_month_period_by_month(month, current_year)
            overtimes = await get_my_overtimes(employee_id, start, end)
            count = len(overtimes)

            if month == current_display_month and current_year == current_display_year:
                button_text = f"✅ {month_name} ({count})" if count > 0 else f"✅ {month_name}"
            else:
                button_text = f"📌 {month_name} ({count})" if count > 0 else f"📅 {month_name}"

            builder.button(text=button_text, callback_data=f"ot_month_{month}_{current_year}")

        builder.adjust(4)

        builder.row(InlineKeyboardButton(text="◀️ Прошлый год", callback_data="overtime_prev_year"))
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="overtime_main"))

        await callback.message.edit_text(
            "📆 *Выберите месяц*\n\n"
            "📌 Период считается с 25-го числа выбранного месяца по 24-е число следующего\n"
            "✅ - текущий месяц (период, который сейчас активен)",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
        await callback.answer()

    @dp.callback_query(lambda c: c.data.startswith("ot_month_"))
    async def ot_month_detail(callback: types.CallbackQuery, state: FSMContext):
        parts = callback.data.split("_")
        month = int(parts[2])
        year = int(parts[3])

        data = await state.get_data()
        employee_id = data.get('employee_id')

        start_date, end_date = get_month_period_by_month(month, year)
        overtimes = await get_my_overtimes(employee_id, start_date, end_date)

        target_month = end_date.month
        target_year = end_date.year
        month_name = await get_month_name(target_month)

        await show_overtime_group(
            callback.message, overtimes,
            f"📅 {month_name} {target_year}",
            start_date, end_date, state
        )
        await callback.answer()

    @dp.callback_query(lambda c: c.data == "overtime_prev_year")
    async def overtime_prev_year(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        employee_id = data.get('employee_id')
        current_year = data.get('current_year', datetime.now().year)
        prev_year = current_year - 1

        await state.update_data(current_year=prev_year)

        current_display_month, current_display_year = get_current_display_month()

        builder = InlineKeyboardBuilder()

        for month in range(1, 13):
            month_name = await get_month_name(month)
            start, end = get_month_period_by_month(month, prev_year)
            overtimes = await get_my_overtimes(employee_id, start, end)
            count = len(overtimes)

            if month == current_display_month and prev_year == current_display_year:
                button_text = f"✅ {month_name} ({count})" if count > 0 else f"✅ {month_name}"
            else:
                button_text = f"📌 {month_name} ({count})" if count > 0 else f"📅 {month_name}"

            builder.button(text=button_text, callback_data=f"ot_month_{month}_{prev_year}")

        builder.adjust(4)

        builder.row(InlineKeyboardButton(text="📅 Текущий год", callback_data="overtime_select_month"))
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="overtime_main"))

        await callback.message.edit_text(
            f"📆 *{prev_year} год*\n\n"
            "📌 Период считается с 25-го числа выбранного месяца по 24-е число следующего",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
        await callback.answer()

    @dp.callback_query(lambda c: c.data == "overtime_main")
    async def overtime_main(callback: types.CallbackQuery, state: FSMContext):
        await cmd_overtime(callback.message, state)
        await callback.answer()

    @dp.callback_query(lambda c: c.data.startswith("ot_detail_"))
    async def overtime_detail(callback: types.CallbackQuery, state: FSMContext):
        note_id = int(callback.data.split("_")[2])

        with get_employees_session() as emp_session:
            note = emp_session.execute(
                text("""
                    SELECT id, number, note_text, overtime_date, overtime_start, overtime_end,
                           EXTRACT(EPOCH FROM (overtime_end - overtime_start)) / 3600.0 as duration_hours
                    FROM public.employee_notes WHERE id = :id
                """),
                {'id': note_id}
            ).first()

            if not note:
                await callback.answer("Переработка не найдена", show_alert=True)
                return

            date_obj = note.overtime_date
            start = note.overtime_start.strftime('%H:%M') if note.overtime_start else "00:00"
            end = note.overtime_end.strftime('%H:%M') if note.overtime_end else "00:00"
            duration = format_duration(note.duration_hours)
            description = note.note_text or ""

            # ИСПРАВЛЕНО: переименовано с 'text' на 'detail_text'
            detail_text = (
                f"📋 *Детали переработки*\n\n"
                f"📅 *Дата:* {date_obj.strftime('%d.%m.%Y')}\n"
                f"⏰ *Время:* {start} → {end}\n"
                f"⏱️ *Длительность:* {duration}\n\n"
            )

            if description and description != 'None':
                detail_text += f"📝 *Описание:*\n{description}\n\n"
            else:
                detail_text += "📝 *Описание:* ❌ *не добавлено*\n\n"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Добавить/редактировать описание", callback_data=f"ot_edit_{note_id}")],
                [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="overtime_back_to_list")],
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="overtime_main")]
            ])

            await callback.message.edit_text(detail_text, reply_markup=keyboard, parse_mode="Markdown")

        await callback.answer()

    @dp.callback_query(lambda c: c.data == "overtime_back_to_list")
    async def overtime_back_to_list(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        employee_id = data.get('employee_id')
        start_date, end_date, _, _ = get_current_month_period()
        overtimes = await get_my_overtimes(employee_id, start_date, end_date)
        target_month = end_date.month
        target_year = end_date.year
        month_name = await get_month_name(target_month)
        await show_overtime_group(
            callback.message, overtimes,
            f"📅 {month_name} {target_year} (с {start_date.day}.{start_date.month} по {end_date.day}.{end_date.month})",
            start_date, end_date, state
        )
        await callback.answer()

    @dp.callback_query(lambda c: c.data.startswith("ot_edit_"))
    async def overtime_edit_form(callback: types.CallbackQuery, state: FSMContext):
        note_id = int(callback.data.split("_")[2])

        with get_employees_session() as emp_session:
            note = emp_session.execute(
                text("""
                    SELECT id, number, note_text, overtime_date, overtime_start, overtime_end,
                           EXTRACT(EPOCH FROM (overtime_end - overtime_start)) / 3600.0 as duration_hours
                    FROM public.employee_notes WHERE id = :id
                """),
                {'id': note_id}
            ).first()

            if not note:
                await callback.answer("Переработка не найдена", show_alert=True)
                return

            overtime_data = {
                "id": note.id,
                "number": note.number,
                "note_text": note.note_text or "",
                "overtime_date": note.overtime_date,
                "overtime_start": note.overtime_start,
                "overtime_end": note.overtime_end,
                "duration_hours": float(note.duration_hours) if note.duration_hours else 0.0
            }

            await state.update_data(selected_overtime=overtime_data)

            date_obj = note.overtime_date
            start = note.overtime_start.strftime('%H:%M') if note.overtime_start else "00:00"
            end = note.overtime_end.strftime('%H:%M') if note.overtime_end else "00:00"
            duration = format_duration(note.duration_hours)
            current_desc = note.note_text or "не добавлено"

            # ИСПРАВЛЕНО: переименовано с 'text' на 'edit_text'
            edit_text = (
                f"✏️ *Редактирование описания*\n\n"
                f"📅 *Дата:* {date_obj.strftime('%d.%m.%Y')}\n"
                f"⏰ *Время:* {start} → {end}\n"
                f"⏱️ *Длительность:* {duration}\n\n"
                f"📝 *Текущее описание:*\n{current_desc}\n\n"
                f"✏️ *Введите новое описание* и отправьте сообщение\n"
                f"(или отправьте 'пусто' чтобы очистить поле)"
            )

            await state.set_state(OvertimeStates.waiting_for_description)

            await callback.message.delete()
            await callback.message.answer(edit_text, parse_mode="Markdown")

        await callback.answer()

    @dp.message(OvertimeStates.waiting_for_description)
    async def overtime_save_description(message: types.Message, state: FSMContext):
        data = await state.get_data()
        overtime = data.get('selected_overtime')

        if not overtime:
            await message.answer("❌ Ошибка: данные не найдены. Используйте /overtime")
            await state.clear()
            return

        description = message.text.strip()
        if description.lower() in ["пусто", "очистить", "удалить"]:
            description = ""

        success = await update_overtime_description(overtime['id'], description)

        if success:
            if description:
                await message.answer(
                    f"✅ *Описание сохранено!*\n\n"
                    f"📅 {overtime['overtime_date'].strftime('%d.%m.%Y')}\n"
                    f"📝 Новое описание: _{description}_",
                    parse_mode="Markdown"
                )
            else:
                await message.answer(
                    f"✅ *Описание удалено!*\n\n"
                    f"📅 {overtime['overtime_date'].strftime('%d.%m.%Y')}",
                    parse_mode="Markdown"
                )
        else:
            await message.answer("❌ *Ошибка при сохранении описания*\nПопробуйте позже", parse_mode="Markdown")

        await state.clear()
        await cmd_overtime(message, state)


async def show_overtime_group(msg: types.Message, overtimes: List[Dict], title: str,
                              start_date: date = None, end_date: date = None,
                              state: FSMContext = None):
    """Показывает переработки с группировкой по датам"""

    if not overtimes:
        period_text = ""
        if start_date and end_date:
            period_text = f"\n📅 Период: {start_date.strftime('%d.%m')} — {end_date.strftime('%d.%m')}"
        await msg.edit_text(
            f"{title}{period_text}\n\n📭 *Нет переработок за этот период*",
            parse_mode="Markdown"
        )
        return

    # Группируем по датам
    groups = {}
    for ot in overtimes:
        date_key = ot['overtime_date']
        if date_key not in groups:
            groups[date_key] = []
        groups[date_key].append(ot)

    lines = [f"{title}", ""]

    for date_key in sorted(groups.keys(), reverse=True):
        day_overtimes = groups[date_key]
        lines.append(f"📅 *{date_key.strftime('%d.%m.%Y')}*")
        lines.append("")

        for ot in day_overtimes:
            start = ot['overtime_start'].strftime('%H:%M') if ot['overtime_start'] else "00:00"
            end = ot['overtime_end'].strftime('%H:%M') if ot['overtime_end'] else "00:00"
            duration = format_duration(ot['duration_hours'])

            has_desc = ot.get('note_text') and ot['note_text'] != 'None' and ot['note_text'].strip()

            if has_desc:
                desc_preview = ot['note_text'][:50] + ("..." if len(ot['note_text']) > 50 else "")
                lines.append(f"   ⏰ {start} → {end}  |  {duration}")
                lines.append(f"   📝 *{desc_preview}*")
            else:
                lines.append(f"   ⏰ {start} → {end}  |  {duration}")
                lines.append(f"   📝 ❌ *нет описания*")

            lines.append("")

    total_hours = sum(o['duration_hours'] for o in overtimes)
    lines.append(f"📊 *Итого:* {format_duration(total_hours)}")
    lines.append("")
    lines.append("🔍 Нажмите на кнопку с нужной переработкой, чтобы увидеть детали")

    builder = InlineKeyboardBuilder()

    for ot in overtimes[:20]:  # Ограничим количество кнопок
        date_str = ot['overtime_date'].strftime('%d.%m')
        start = ot['overtime_start'].strftime('%H:%M') if ot['overtime_start'] else "00:00"
        builder.button(text=f"🔍 {date_str} {start}", callback_data=f"ot_detail_{ot['id']}")

    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔙 Назад в меню", callback_data="overtime_main"))

    await msg.edit_text("\n".join(lines), reply_markup=builder.as_markup(), parse_mode="Markdown")