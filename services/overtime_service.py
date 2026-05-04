# services/overtime_service.py

from datetime import datetime, date, time, timedelta
from typing import Dict, List, Optional, Tuple
from PyQt6.QtCore import QDate, QTime

from database import get_tasks_session, get_employees_session  # ← ДОБАВИТЬ get_employees_session
from repositories.overtime_repo import OvertimeRepo
from repositories.project_repo import ProjectRepo
from repositories.task_repo import TaskRepo
from repositories.employee_repo import EmployeeRepo
from models.employees import Employee


class OvertimeService:
    """Сервис для работы с переработками"""

    def __init__(self, session=None):
        # Сессия для taskplanner БД (переработки, проекты, задачи)
        self.session = session or get_tasks_session()
        # Отдельная сессия для employees БД (сотрудники)
        self.employees_session = get_employees_session()

        self.overtime_repo = OvertimeRepo(self.session)
        self.project_repo = ProjectRepo(self.session)
        self.task_repo = TaskRepo(self.session)
        # Используем employees_session для EmployeeRepo
        self.employee_repo = EmployeeRepo(self.employees_session)  # ← ИСПРАВЛЕНО
        self.current_user_id = None

    def __del__(self):
        """Закрываем сессию employees при удалении"""
        try:
            if hasattr(self, 'employees_session') and self.employees_session:
                self.employees_session.close()
        except:
            pass

    def set_current_user_id(self, user_id: int):
        """Устанавливает ID текущего пользователя"""
        self.current_user_id = user_id

    # ======================================================
    # Работа с сотрудниками
    # ======================================================
    def get_all_employees(self) -> List[Dict]:
        """Получает список всех сотрудников для выпадающего списка"""
        try:
            employees = self.employee_repo.get_all()
            print(f"📊 Загружено сотрудников из БД: {len(employees)}")

            result = []
            for emp in employees:
                # Формируем ФИО
                full_name = f"{emp.last_name} {emp.first_name}"
                if emp.middle_name:
                    full_name += f" {emp.middle_name}"

                result.append({
                    'id': emp.id,
                    'name': full_name,
                    'short_name': f"{emp.last_name} {emp.first_name[0]}." + (
                        f"{emp.middle_name[0]}." if emp.middle_name else "")
                })
            return sorted(result, key=lambda x: x['name'])
        except Exception as e:
            print(f"❌ Ошибка при загрузке сотрудников: {e}")
            return []

    # ======================================================
    # Работа с проектами и задачами
    # ======================================================
    def get_projects(self) -> List[Dict]:
        """Получает список всех проектов для выпадающего списка"""
        projects = self.project_repo.get_all()
        result = []
        for project in projects:
            result.append({
                'id': project.id,
                'name': project.name
            })
        return sorted(result, key=lambda x: x['name'])

    def get_tasks_for_project(self, project_id: int) -> List[Dict]:
        """Получает список задач для выбранного проекта"""
        tasks = self.task_repo.get_by_project(project_id)
        result = []
        for task in tasks:
            result.append({
                'id': task.id,
                'title': task.title
            })
        return sorted(result, key=lambda x: x['title'])

    # ======================================================
    # Работа с временем
    # ======================================================
    def calculate_duration(self, start_time: Optional[time], end_time: Optional[time]) -> str:
        """Вычисляет продолжительность в часах (например, '2,5')"""
        if not start_time or not end_time:
            return "0,0"

        start = datetime.combine(date.today(), start_time)
        end = datetime.combine(date.today(), end_time)

        if end < start:
            end = end + timedelta(days=1)

        hours = (end - start).total_seconds() / 3600
        return f"{hours:.1f}".replace(".", ",")

    def format_time_period(self, start_time: Optional[time], end_time: Optional[time]) -> str:
        """Возвращает строку периода 'hh:mm - hh:mm'"""
        if not start_time or not end_time:
            return "--:-- - --:--"
        return f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"

    # ======================================================
    # Загрузка данных из БД
    # ======================================================
    def load_overtimes(self) -> Tuple[List[Dict], List[Dict]]:
        """Загружает переработки из БД"""
        if not self.current_user_id:
            return [], []

        # Мои переработки
        my_notes = self.overtime_repo.get_by_employee(self.current_user_id)
        my_overtimes = [self._note_to_dict(note, is_mine=True) for note in my_notes]

        # Все переработки
        all_notes = self.overtime_repo.get_all()
        all_overtimes = []
        for note in all_notes:
            is_mine = (note.employee_id == self.current_user_id)
            all_overtimes.append(self._note_to_dict(note, is_mine))

        return my_overtimes, all_overtimes

    def _note_to_dict(self, note, is_mine: bool) -> Dict:
        """Преобразует ORM-объект в словарь для карточки"""
        # Получаем имя сотрудника (используем employees_session)
        employee_name = "Неизвестен"
        employee = self.employee_repo.get_by_id(note.employee_id)
        if employee:
            employee_name = f"{employee.last_name} {employee.first_name[0]}."
            if employee.middle_name:
                employee_name += f"{employee.middle_name[0]}."

        # Форматируем дату
        date_str = note.overtime_date.strftime("%d.%m.%Y") if note.overtime_date else ""

        # Продолжительность и период
        duration = self.calculate_duration(note.overtime_start, note.overtime_end)
        time_period = self.format_time_period(note.overtime_start, note.overtime_end)

        # Извлекаем проект и задачу из описания
        project_name = None
        task_title = None
        description = note.note_text or "Без описания"

        if description.startswith("[Проект:"):
            import re
            project_match = re.search(r'\[Проект: (.*?)\]', description)
            if project_match:
                project_name = project_match.group(1)

            task_match = re.search(r'\[Задача: (.*?)\]', description)
            if task_match:
                task_title = task_match.group(1)

            clean_description = re.sub(r'\[Проект: .*?\]\s*', '', description)
            clean_description = re.sub(r'\[Задача: .*?\]\s*', '', clean_description)
            description = clean_description.strip()

        return {
            "id": note.id,
            "number": note.number,
            "employee_id": note.employee_id,
            "user": employee_name,
            "date": date_str,
            "start_time": note.overtime_start.strftime("%H:%M") if note.overtime_start else "",
            "end_time": note.overtime_end.strftime("%H:%M") if note.overtime_end else "",
            "time_period": time_period,
            "duration": duration,
            "description": description,
            "project": project_name,
            "task": task_title,
            "is_mine": is_mine
        }

    # ======================================================
    # Создание переработки
    # ======================================================
    def add_overtime(self, date: QDate, start_time: QTime, end_time: QTime,
                     description: str, employee_id: Optional[int] = None,
                     project_id: Optional[int] = None,
                     task_id: Optional[int] = None) -> Optional[Dict]:
        """Добавляет новую переработку в БД"""
        if not employee_id:
            employee_id = self.current_user_id

        if not employee_id:
            return None

        try:
            py_date = date.toPyDate()
            py_start = time(start_time.hour(), start_time.minute())
            py_end = time(end_time.hour(), end_time.minute())

            full_description = description
            if project_id:
                project = self.project_repo.get_by_id(project_id)
                if project:
                    full_description = f"[Проект: {project.name}] {description}"
                    if task_id:
                        task = self.task_repo.get_by_id(task_id)
                        if task:
                            full_description = f"[Проект: {project.name}] [Задача: {task.title}] {description}"

            note = self.overtime_repo.create(
                employee_id=employee_id,
                overtime_date=py_date,
                note_text=full_description,
                overtime_start=py_start,
                overtime_end=py_end
            )

            self.session.commit()
            is_mine = (employee_id == self.current_user_id)
            return self._note_to_dict(note, is_mine=is_mine)

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при добавлении переработки: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ======================================================
    # Фильтрация
    # ======================================================
    def filter_overtimes(self, overtimes: List[Dict], **filters) -> List[Dict]:
        """Фильтрует список переработок"""
        filtered = overtimes.copy()

        project_name = filters.get('project_name')
        if project_name and project_name != "Все переработки":
            filtered = [ot for ot in filtered if ot.get('project') == project_name]

        task_title = filters.get('task_title')
        if task_title and task_title != "Все задачи":
            filtered = [ot for ot in filtered if ot.get('task') == task_title]

        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        if start_date and end_date:
            filtered = [
                ot for ot in filtered
                if start_date <= QDate.fromString(ot['date'], "dd.MM.yyyy") <= end_date
            ]

        return filtered

    def get_filtered_overtimes(self, employee_id: Optional[int] = None,
                               project_name: Optional[str] = None,
                               task_title: Optional[str] = None,
                               start_date: Optional[QDate] = None,
                               end_date: Optional[QDate] = None) -> List[Dict]:
        """Получает отфильтрованные переработки напрямую из БД"""
        all_notes = self.overtime_repo.get_all()
        result = []

        for note in all_notes:
            if employee_id is not None and note.employee_id != employee_id:
                continue

            note_dict = self._note_to_dict(note, is_mine=(note.employee_id == self.current_user_id))

            if project_name and note_dict.get('project') != project_name:
                continue
            if task_title and note_dict.get('task') != task_title:
                continue
            if start_date and end_date:
                note_qdate = QDate.fromString(note_dict['date'], "dd.MM.yyyy")
                if not (start_date <= note_qdate <= end_date):
                    continue

            result.append(note_dict)

        return result