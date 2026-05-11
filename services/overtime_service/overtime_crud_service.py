# services/overtime_service/overtime_crud_service.py

from datetime import date, time
from typing import List, Dict, Optional, Tuple
from PyQt6.QtCore import QDate, QTime
from sqlalchemy.orm import Session

from repositories.overtime_repo import OvertimeRepo
from repositories.project_repo import ProjectRepo
from repositories.task_repo import TaskRepo
from repositories.employee_repo import EmployeeRepo
from .overtime_base_service import OvertimeBaseService


class OvertimeCrudService:
    """CRUD операции с переработками"""

    def __init__(self, session: Session, employees_session: Session):
        self.session = session
        self.employees_session = employees_session
        self.overtime_repo = OvertimeRepo(session)
        self.project_repo = ProjectRepo(session)
        self.task_repo = TaskRepo(session)
        self.employee_repo = EmployeeRepo(employees_session)
        self.base = OvertimeBaseService()

    def get_all_employees(self) -> List[Dict]:
        """Получает список всех сотрудников для выпадающего списка"""
        try:
            employees = self.employee_repo.get_all()
            result = []
            for emp in employees:
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

    def get_projects(self) -> List[Dict]:
        """Получает список всех проектов"""
        projects = self.project_repo.get_all()
        return sorted([{'id': p.id, 'name': p.name} for p in projects], key=lambda x: x['name'])

    def get_overtime_by_id(self, overtime_id: int) -> Optional[Dict]:
        """Получает переработку по ID"""
        try:
            note = self.overtime_repo.get_by_id(overtime_id)
            if not note:
                return None
            return self._note_to_dict(note, is_mine=False, user_id=note.employee_id)
        except Exception as e:
            print(f"❌ Ошибка при получении переработки: {e}")
            return None

    def update_overtime(self, overtime_id: int, date: QDate, start_time: QTime, end_time: QTime,
                        description: str, current_user_id: int,
                        employee_id: Optional[int] = None,
                        project_id: Optional[int] = None,
                        task_id: Optional[int] = None) -> Optional[Dict]:
        """Обновляет переработку"""
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

            # Обновляем запись
            note = self.overtime_repo.update(
                overtime_id=overtime_id,
                employee_id=employee_id,
                overtime_date=py_date,
                note_text=full_description,
                overtime_start=py_start,
                overtime_end=py_end
            )

            if note:
                self.session.commit()
                is_mine = (employee_id == current_user_id) if employee_id else (note.employee_id == current_user_id)
                return self._note_to_dict(note, is_mine=is_mine, user_id=current_user_id)
            return None

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении переработки: {e}")
            return None

    def delete_overtime(self, overtime_id: int) -> bool:
        """Удаляет переработку"""
        try:
            result = self.overtime_repo.delete(overtime_id)
            if result:
                self.session.commit()
            return result
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при удалении переработки: {e}")
            return False

    def get_tasks_for_project(self, project_id: int) -> List[Dict]:
        """Получает список задач для проекта"""
        tasks = self.task_repo.get_by_project(project_id)
        return sorted([{'id': t.id, 'title': t.title} for t in tasks], key=lambda x: x['title'])

    def load_overtimes(self, current_user_id: int) -> Tuple[List[Dict], List[Dict]]:
        """Загружает переработки из БД"""
        my_notes = self.overtime_repo.get_by_employee(current_user_id)
        my_overtimes = [self._note_to_dict(note, is_mine=True, user_id=current_user_id) for note in my_notes]

        all_notes = self.overtime_repo.get_all()
        all_overtimes = []
        for note in all_notes:
            is_mine = (note.employee_id == current_user_id)
            all_overtimes.append(self._note_to_dict(note, is_mine=is_mine, user_id=current_user_id))

        return my_overtimes, all_overtimes

    def _note_to_dict(self, note, is_mine: bool, user_id: int) -> Dict:
        """Преобразует ORM-объект в словарь для карточки"""
        employee_name = "Неизвестен"
        employee = self.employee_repo.get_by_id(note.employee_id)
        if employee:
            employee_name = f"{employee.last_name} {employee.first_name[0]}."
            if employee.middle_name:
                employee_name += f"{employee.middle_name[0]}."

        date_str = note.overtime_date.strftime("%d.%m.%Y") if note.overtime_date else ""
        duration = self.base.calculate_duration(note.overtime_start, note.overtime_end)
        time_period = self.base.format_time_period(note.overtime_start, note.overtime_end)

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
            description = re.sub(r'\[Проект: .*?\]\s*', '', description)
            description = re.sub(r'\[Задача: .*?\]\s*', '', description)
            description = description.strip()

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

    def add_overtime(self, date: QDate, start_time: QTime, end_time: QTime,
                     description: str, current_user_id: int,
                     employee_id: Optional[int] = None,
                     project_id: Optional[int] = None,
                     task_id: Optional[int] = None) -> Optional[Dict]:
        """Добавляет новую переработку в БД"""
        if not employee_id:
            employee_id = current_user_id

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
            is_mine = (employee_id == current_user_id)
            return self._note_to_dict(note, is_mine=is_mine, user_id=current_user_id)

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при добавлении переработки: {e}")
            return None

    def get_filtered_overtimes_for_export(self, overtimes: List[Dict],
                                          start_date: QDate, end_date: QDate,
                                          division: Optional[str] = None,
                                          department: Optional[str] = None,
                                          employee_service=None) -> List[Dict]:
        """Фильтрует переработки для экспорта по периоду, подразделению и отделу"""
        filtered = [ot for ot in overtimes if self._is_in_period(ot, start_date, end_date)]

        if division or department:
            filtered = self._filter_by_division_department(filtered, division, department, employee_service)

        return filtered

    def _is_in_period(self, overtime: Dict, start_date: QDate, end_date: QDate) -> bool:
        date_str = overtime.get('date', '')
        if not date_str:
            return False
        ot_date = QDate.fromString(date_str, "dd.MM.yyyy")
        return ot_date.isValid() and start_date <= ot_date <= end_date

    def _filter_by_division_department(self, overtimes: List[Dict], division: Optional[str],
                                       department: Optional[str], employee_service) -> List[Dict]:
        if not employee_service:
            return overtimes

        result = []
        for ot in overtimes:
            employee_id = ot.get('employee_id')
            if employee_id:
                emp_data = employee_service.get_employee_by_id(employee_id)
                if emp_data:
                    emp_division = emp_data.get('division_name')
                    emp_department = emp_data.get('department_name')

                    if division and emp_division != division:
                        continue
                    if department and emp_department != department:
                        continue
                    result.append(ot)
        return result

    def get_total_hours(self, overtimes: List[Dict]) -> float:
        """Вычисляет общее количество часов из списка переработок"""
        total = 0.0
        for ot in overtimes:
            duration_value = ot.get('duration', 0.0)
            try:
                if isinstance(duration_value, (int, float)):
                    total += float(duration_value)
                elif isinstance(duration_value, str):
                    total += float(duration_value.replace(',', '.'))
                else:
                    total += 0.0
            except (ValueError, AttributeError):
                pass
        return round(total, 1)

    def get_employee_name_by_id(self, employee_id: int) -> str:
        """Возвращает имя сотрудника по ID"""
        employee = self.employee_repo.get_by_id(employee_id)
        if employee:
            short_name = f"{employee.last_name} {employee.first_name[0]}."
            if employee.middle_name:
                short_name += f"{employee.middle_name[0]}."
            return short_name
        return "Неизвестный"

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