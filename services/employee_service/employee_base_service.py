# services/employee_service/employee_base_service.py

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from database import get_employees_session, get_tasks_session
from models.employees import Employee, Department, Division, EmployeeData, RoleEnum
from repositories.employee_repo import EmployeeRepo


class EmployeeBaseService:
    """Базовый сервис с общими утилитами"""

    def __init__(self, session: Session = None):
        self.session = session or get_employees_session()
        self.tasks_session = get_tasks_session()
        self.repo = EmployeeRepo(self.session)
        self._own_session = session is None

    def close(self):
        if self._own_session and self.session:
            self.session.close()
        if self.tasks_session:
            self.tasks_session.close()

    def _get_full_name(self, employee: Employee) -> str:
        """Формирует ФИО сотрудника"""
        parts = [employee.last_name, employee.first_name]
        if employee.middle_name:
            parts.append(employee.middle_name)
        return ' '.join(parts)

    def _parse_boss_ids(self, boss_field) -> List[int]:
        """Парсит поле boss и возвращает список ID сотрудников"""
        if not boss_field:
            return []
        if isinstance(boss_field, str):
            if all(c.isdigit() or c == ',' or c.isspace() for c in boss_field):
                ids = []
                for part in boss_field.split(','):
                    part = part.strip()
                    if part and part.isdigit():
                        ids.append(int(part))
                return ids
            return []
        elif isinstance(boss_field, (int, float)):
            return [int(boss_field)]
        elif isinstance(boss_field, list):
            return boss_field
        return []

    def get_employee_short_name(self, employee_id: int) -> str:
        """Возвращает краткое ФИО сотрудника: Фамилия И.О."""
        employee = self.repo.get_by_id(employee_id)
        if not employee:
            return ""

        last_name = employee.last_name or ''
        first_name = employee.first_name or ''
        middle_name = employee.middle_name or ''

        initials = ""
        if first_name:
            initials += first_name[0] + "."
        if middle_name:
            initials += middle_name[0] + "."

        result = f"{last_name} {initials}".strip() if initials else last_name
        return result if result.strip() else ""

    def get_role_display_name(self, role: str) -> str:
        role_map = {
            'superadmin': 'Суперадминистратор',
            'admin': 'Администратор',
            'user': 'Пользователь'
        }
        return role_map.get(role, 'Пользователь')

    def get_subordinates(self, employee_id: int) -> List[int]:
        """
        Возвращает список ID сотрудников, которые подчиняются данному руководителю.
        Сотрудник считается руководителем, если он указан как boss в отделе или подразделении.
        """
        subordinates = set()

        try:
            # 1. Сотрудники из отделов, где этот сотрудник - руководитель
            departments = self.session.query(Department).filter(
                Department.boss.like(f'%{employee_id}%')
            ).all()

            for dept in departments:
                dept_employees = self.session.query(Employee).filter(
                    Employee.department_id == dept.id
                ).all()
                for emp in dept_employees:
                    if emp.id != employee_id:
                        subordinates.add(emp.id)

            # 2. Сотрудники из подразделений, где этот сотрудник - руководитель
            divisions = self.session.query(Division).filter(
                Division.boss.like(f'%{employee_id}%')
            ).all()

            for div in divisions:
                div_employees = self.session.query(Employee).filter(
                    Employee.division_id == div.id
                ).all()
                for emp in div_employees:
                    if emp.id != employee_id:
                        subordinates.add(emp.id)

        except Exception as e:
            print(f"❌ Ошибка при получении подчинённых: {e}")

        return list(subordinates)

    def get_role_color(self, role: str) -> str:
        role_colors = {
            'superadmin': '#D22730',
            'admin': '#ccab6e',
            'user': '#1B232A'
        }
        return role_colors.get(role, '#1B232A')

    def format_phone_display(self, phone: str) -> str:
        if not phone:
            return '—'
        if phone.startswith('375'):
            return '+' + phone
        return phone