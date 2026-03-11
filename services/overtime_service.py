# services/overtime_service.py

from datetime import datetime, date, time, timedelta
from typing import Dict, List, Optional, Tuple
from PyQt6.QtCore import QDate, QTime

from database import get_tasks_session
from repositories.overtime_repo import OvertimeRepo
from repositories.project_repo import ProjectRepo
from repositories.task_repo import TaskRepo
from repositories.external_employee_repo import ExternalEmployeeRepo


class OvertimeService:
    """Сервис для работы с переработками"""

    def __init__(self, session=None):
        self.session = session or get_tasks_session()
        self.overtime_repo = OvertimeRepo(self.session)
        self.project_repo = ProjectRepo(self.session)
        self.task_repo = TaskRepo(self.session)
        self.employee_repo = ExternalEmployeeRepo(self.session)
        self.current_user_id = None

    def set_current_user_id(self, user_id: int):
        """Устанавливает ID текущего пользователя"""
        self.current_user_id = user_id

    # ======================================================
    # Работа с сотрудниками
    # ======================================================
    def get_all_employees(self) -> List[Dict]:
        """Получает список всех сотрудников для выпадающего списка"""
        try:
            employees = self.employee_repo.get_all()  # Это ExternalEmployeeRepo
            print(f"📊 Загружено сотрудников из БД: {len(employees)}")

            result = []
            for emp in employees:
                # Формируем ФИО
                full_name = f"{emp.last_name} {emp.first_name}"
                if emp.middle_name:
                    full_name += f" {emp.middle_name}"

                # Для отладки
                print(f"  - ID: {emp.id}, Имя: {full_name}")

                result.append({
                    'id': emp.id,
                    'name': full_name,
                    'short_name': f"{emp.last_name} {emp.first_name[0]}." + (
                        f"{emp.middle_name[0]}." if emp.middle_name else "")
                })
            return sorted(result, key=lambda x: x['name'])
        except Exception as e:
            print(f"❌ Ошибка при загрузке сотрудников: {e}")
            import traceback
            traceback.print_exc()
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
        return result

    def get_tasks_for_project(self, project_id: int) -> List[Dict]:
        """Получает список задач для выбранного проекта"""
        tasks = self.task_repo.get_by_project(project_id)
        result = []
        for task in tasks:
            result.append({
                'id': task.id,
                'title': task.title
            })
        return result

    # ======================================================
    # Работа с временем
    # ======================================================
    def calculate_duration(self, start_time: Optional[time], end_time: Optional[time]) -> str:
        """Вычисляет продолжительность в часах (например, '2,5')"""
        if not start_time or not end_time:
            return "0,0"

        # Преобразуем time в datetime для вычисления разницы
        start = datetime.combine(date.today(), start_time)
        end = datetime.combine(date.today(), end_time)

        # Если время окончания меньше времени начала, значит переход на следующий день
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
        """
        Загружает переработки из БД
        Возвращает (мои переработки, все переработки)
        """
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
        # Получаем имя сотрудника
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
            "description": note.note_text or "Без описания",
            "project": None,  # В employee_notes нет привязки к проектам
            "task": None,  # В employee_notes нет привязки к задачам
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
        # Если не указан сотрудник, используем текущего пользователя
        if not employee_id:
            employee_id = self.current_user_id

        if not employee_id:
            return None

        try:
            # Преобразуем QDate и QTime в Python date/time
            py_date = date.toPyDate()
            py_start = time(start_time.hour(), start_time.minute())
            py_end = time(end_time.hour(), end_time.minute())

            # Добавляем информацию о проекте и задаче в описание
            full_description = description
            if project_id:
                project = self.project_repo.get_by_id(project_id)
                if project:
                    full_description = f"[Проект: {project.name}] {description}"
                    if task_id:
                        task = self.task_repo.get_by_id(task_id)
                        if task:
                            full_description = f"[Проект: {project.name}] [Задача: {task.title}] {description}"

            # Создаем запись в БД
            note = self.overtime_repo.create(
                employee_id=employee_id,
                overtime_date=py_date,
                note_text=full_description,
                overtime_start=py_start,
                overtime_end=py_end
            )

            self.session.commit()

            # Определяем, является ли созданная переработка "моей"
            is_mine = (employee_id == self.current_user_id)
            return self._note_to_dict(note, is_mine=is_mine)

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при добавлении переработки: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ======================================================
    # Фильтрация (пока на клиенте)
    # ======================================================
    def filter_overtimes(self, overtimes: List[Dict], **filters) -> List[Dict]:
        """
        Фильтрует список переработок
        filters может содержать: project, task, start_date, end_date
        """
        filtered = overtimes.copy()

        # Фильтр по периоду
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        if start_date and end_date:
            filtered = [
                ot for ot in filtered
                if start_date <= QDate.fromString(ot['date'], "dd.MM.yyyy") <= end_date
            ]

        # В будущем можно добавить фильтры по проекту/задаче,
        # когда они появятся в employee_notes

        return filtered