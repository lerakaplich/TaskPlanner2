# services/permissions/system_permissions.py

from enum import Enum
from typing import Set, Dict, Optional, List
from sqlalchemy.orm import Session


class SystemRole(Enum):
    """Роли в иерархии организации"""
    ORGANIZATION_HEAD = "organization_head"  # Начальник организации
    DIVISION_HEAD = "division_head"  # Начальник подразделения
    DEPARTMENT_HEAD = "department_head"  # Начальник отдела
    EMPLOYEE = "employee"  # Сотрудник


class SystemPermissionManager:
    """
    Менеджер прав на уровне системы (организационная иерархия)
    Определяет, что может делать пользователь в зависимости от должности
    """

    def __init__(self, user_id: int, role: SystemRole, session: Session = None):
        self.user_id = user_id
        self.role = role
        self.session = session
        self._subordinates_cache = None

    def has_permission(self, permission: str) -> bool:
        """Проверяет наличие права"""
        permissions = self._get_permissions_for_role(self.role)
        return permission in permissions

    def _get_permissions_for_role(self, role: SystemRole) -> Set[str]:
        """Возвращает набор прав для роли"""
        permissions_map = {
            SystemRole.ORGANIZATION_HEAD: {
                # Управление сотрудниками (все)
                'can_manage_all_employees',
                'can_view_all_employees',
                'can_edit_all_employees',
                'can_delete_all_employees',
                'can_create_employee',

                # Управление отделами (все)
                'can_manage_all_departments',
                'can_view_all_departments',
                'can_edit_all_departments',
                'can_delete_all_departments',

                # Управление подразделениями (все)
                'can_manage_all_divisions',
                'can_view_all_divisions',
                'can_edit_all_divisions',
                'can_delete_all_divisions',

                # Статистика
                'can_view_all_stats',
                'can_view_employees_stats',
                'can_view_departments_stats',
                'can_view_divisions_stats',

                # Переработки
                'can_approve_all_overtime',
                'can_view_all_overtime',
            },

            SystemRole.DIVISION_HEAD: {
                # Управление сотрудниками (только в своём подразделении)
                'can_manage_division_employees',
                'can_view_division_employees',
                'can_edit_division_employees',
                'can_delete_division_employees',

                # Управление отделами (только в своём подразделении)
                'can_manage_division_departments',
                'can_view_division_departments',
                'can_edit_division_departments',
                'can_delete_division_departments',

                # Статистика (только по своему подразделению)
                'can_view_division_stats',
                'can_view_departments_stats_in_division',

                # Переработки (только в своём подразделении)
                'can_approve_division_overtime',
                'can_view_division_overtime',
            },

            SystemRole.DEPARTMENT_HEAD: {
                # Управление сотрудниками (только в своём отделе)
                'can_manage_department_employees',
                'can_view_department_employees',
                'can_edit_department_employees',
                'can_delete_department_employees',

                # Статистика (только по своему отделу)
                'can_view_department_stats',

                # Переработки (только в своём отделе)
                'can_approve_department_overtime',
                'can_view_department_overtime',
            },

            SystemRole.EMPLOYEE: {
                # Сотрудник может управлять только собой
                'can_view_own_profile',
                'can_edit_own_profile',

                # Статистика (только своя)
                'can_view_own_stats',

                # Переработки (только свои)
                'can_view_own_overtime',
            }
        }
        return permissions_map.get(role, set())

    # ===== МЕТОДЫ ДЛЯ ОПРЕДЕЛЕНИЯ ПОДЧИНЁННЫХ =====

    def get_subordinates(self) -> List[int]:
        """
        Возвращает список ID сотрудников, подчинённых данному начальнику
        """
        if self._subordinates_cache is not None:
            return self._subordinates_cache

        subordinates = set()

        try:
            from models.employees import Employee, Department, Division

            if self.role == SystemRole.ORGANIZATION_HEAD:
                # Начальник организации видит всех
                employees = self.session.query(Employee).all()
                subordinates = {emp.id for emp in employees}

            elif self.role == SystemRole.DIVISION_HEAD:
                # Начальник подразделения видит всех в своих отделах
                # Находим подразделения, где пользователь - начальник
                divisions = self.session.query(Division).filter(
                    Division.boss.like(f'%{self.user_id}%')
                ).all()

                division_ids = [div.id for div in divisions]

                # Все сотрудники в этих подразделениях
                employees = self.session.query(Employee).filter(
                    Employee.division_id.in_(division_ids)
                ).all()
                subordinates = {emp.id for emp in employees}

            elif self.role == SystemRole.DEPARTMENT_HEAD:
                # Начальник отдела видит всех в своём отделе
                departments = self.session.query(Department).filter(
                    Department.boss.like(f'%{self.user_id}%')
                ).all()

                department_ids = [dept.id for dept in departments]

                # Все сотрудники в этих отделах
                employees = self.session.query(Employee).filter(
                    Employee.department_id.in_(department_ids)
                ).all()
                subordinates = {emp.id for emp in employees}

            else:
                # Сотрудник не имеет подчинённых
                subordinates = set()

        except Exception as e:
            print(f"⚠️ Ошибка при получении подчинённых: {e}")
            subordinates = set()

        self._subordinates_cache = list(subordinates)
        return self._subordinates_cache

    def is_subordinate(self, employee_id: int) -> bool:
        """Проверяет, является ли сотрудник подчинённым"""
        if employee_id == self.user_id:
            return False
        subordinates = self.get_subordinates()
        return employee_id in subordinates

    def is_in_my_department(self, employee_id: int) -> bool:
        """Проверяет, находится ли сотрудник в отделе начальника"""
        if self.role != SystemRole.DEPARTMENT_HEAD:
            return False

        try:
            from models.employees import Employee, Department

            # Находим отделы, где пользователь - начальник
            departments = self.session.query(Department).filter(
                Department.boss.like(f'%{self.user_id}%')
            ).all()

            department_ids = [dept.id for dept in departments]

            # Проверяем, принадлежит ли сотрудник к этим отделам
            employee = self.session.get(Employee, employee_id)
            if employee:
                return employee.department_id in department_ids

        except Exception as e:
            print(f"⚠️ Ошибка проверки отдела: {e}")

        return False

    def is_in_my_division(self, employee_id: int) -> bool:
        """Проверяет, находится ли сотрудник в подразделении начальника"""
        if self.role != SystemRole.DIVISION_HEAD:
            return False

        try:
            from models.employees import Employee, Division

            # Находим подразделения, где пользователь - начальник
            divisions = self.session.query(Division).filter(
                Division.boss.like(f'%{self.user_id}%')
            ).all()

            division_ids = [div.id for div in divisions]

            # Проверяем, принадлежит ли сотрудник к этим подразделениям
            employee = self.session.get(Employee, employee_id)
            if employee:
                return employee.division_id in division_ids

        except Exception as e:
            print(f"⚠️ Ошибка проверки подразделения: {e}")

        return False

    # services/permissions/system_permissions.py

    def can_manage_employee(self, target_employee_id: int) -> bool:
        """
        Может ли пользователь управлять указанным сотрудником
        """
        # Нельзя управлять собой
        if target_employee_id == self.user_id:
            return False

        # Начальник организации управляет всеми
        if self.role == SystemRole.ORGANIZATION_HEAD:
            return self.has_permission('can_manage_all_employees')

        # Начальник подразделения управляет только своими подчинёнными
        if self.role == SystemRole.DIVISION_HEAD:
            if not self.has_permission('can_manage_division_employees'):
                return False
            return self.is_in_my_division(target_employee_id)

        # Начальник отдела управляет только своими подчинёнными
        if self.role == SystemRole.DEPARTMENT_HEAD:
            if not self.has_permission('can_manage_department_employees'):
                return False
            return self.is_in_my_department(target_employee_id)

        return False

    def can_edit_employee(self, target_employee_id: int) -> bool:
        """Может ли пользователь редактировать сотрудника"""
        # Начальники могут редактировать только подчинённых
        return self.can_manage_employee(target_employee_id)

    def can_delete_employee(self, target_employee_id: int) -> bool:
        """Может ли пользователь удалять сотрудника"""
        # Начальники могут удалять только подчинённых
        return self.can_manage_employee(target_employee_id)

    def can_view_employee(self, target_employee_id: int) -> bool:
        """
        Может ли пользователь просматривать сотрудника
        """
        if target_employee_id == self.user_id:
            return True

        if self.role == SystemRole.ORGANIZATION_HEAD:
            return self.has_permission('can_view_all_employees')

        if self.role == SystemRole.DIVISION_HEAD:
            if not self.has_permission('can_view_division_employees'):
                return False
            return self.is_in_my_division(target_employee_id)

        if self.role == SystemRole.DEPARTMENT_HEAD:
            if not self.has_permission('can_view_department_employees'):
                return False
            return self.is_in_my_department(target_employee_id)

        return False

    def can_manage_department(self, department_id: int) -> bool:
        """Может ли пользователь управлять отделом"""
        if self.role == SystemRole.ORGANIZATION_HEAD:
            return self.has_permission('can_manage_all_departments')

        if self.role == SystemRole.DIVISION_HEAD:
            if not self.has_permission('can_manage_division_departments'):
                return False

            try:
                from models.employees import Department
                department = self.session.get(Department, department_id)
                if department:
                    return self.is_in_my_division(
                        self.session.query(Department.boss).filter(
                            Department.id == department_id
                        ).first()
                    )
            except Exception:
                pass
            return False

        if self.role == SystemRole.DEPARTMENT_HEAD:
            # Начальник отдела может управлять только своим отделом
            try:
                from models.employees import Department
                department = self.session.get(Department, department_id)
                if department:
                    boss_ids = self._parse_boss_ids(department.boss)
                    return self.user_id in boss_ids
            except Exception:
                pass
            return False

        return False

    def can_manage_division(self, division_id: int) -> bool:
        """Может ли пользователь управлять подразделением"""
        if self.role == SystemRole.ORGANIZATION_HEAD:
            return self.has_permission('can_manage_all_divisions')

        if self.role == SystemRole.DIVISION_HEAD:
            # Начальник подразделения может управлять только своим подразделением
            try:
                from models.employees import Division
                division = self.session.get(Division, division_id)
                if division:
                    boss_ids = self._parse_boss_ids(division.boss)
                    return self.user_id in boss_ids
            except Exception:
                pass
            return False

        return False

    def _parse_boss_ids(self, boss_field) -> List[int]:
        """Парсит поле boss и возвращает список ID"""
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

    def get_filtered_employees(self, employees: List[Dict]) -> List[Dict]:
        """
        Фильтрует список сотрудников, оставляя только тех, кого может видеть пользователь
        """
        if self.role == SystemRole.ORGANIZATION_HEAD:
            return employees

        result = []
        for emp in employees:
            emp_id = emp.get('id')
            if self.can_view_employee(emp_id):
                result.append(emp)

        return result

    def get_filtered_departments(self, departments: List[Dict]) -> List[Dict]:
        """
        Фильтрует список отделов, оставляя только те, которыми может управлять пользователь
        """
        if self.role == SystemRole.ORGANIZATION_HEAD:
            return departments

        result = []
        for dept in departments:
            dept_id = dept.get('id')
            if self.can_manage_department(dept_id):
                result.append(dept)

        return result

    def can_view_contacts(self, target_employee_id: int) -> bool:
        """
        Может ли пользователь видеть контактную информацию сотрудника
        - Начальник организации: видит всех
        - Начальник подразделения: видит всех в своём подразделении
        - Начальник отдела: видит всех в своём отделе
        - Сотрудник: видит только себя
        """
        # Всегда видим себя
        if target_employee_id == self.user_id:
            return True

        # Начальник организации видит всех
        if self.role == SystemRole.ORGANIZATION_HEAD:
            return self.has_permission('can_view_all_employees')

        # Начальник подразделения видит всех в своём подразделении
        if self.role == SystemRole.DIVISION_HEAD:
            if not self.has_permission('can_view_division_employees'):
                return False
            return self.is_in_my_division(target_employee_id)

        # Начальник отдела видит всех в своём отделе
        if self.role == SystemRole.DEPARTMENT_HEAD:
            if not self.has_permission('can_view_department_employees'):
                return False
            return self.is_in_my_department(target_employee_id)

        # Сотрудник видит только себя
        return False

    def get_filtered_divisions(self, divisions: List[Dict]) -> List[Dict]:
        """
        Фильтрует список подразделений, оставляя только те, которыми может управлять пользователь
        """
        if self.role == SystemRole.ORGANIZATION_HEAD:
            return divisions

        result = []
        for div in divisions:
            div_id = div.get('id')
            if self.can_manage_division(div_id):
                result.append(div)

        return result

    def get_visible_employee_ids(self) -> Set[int]:
        """
        Возвращает множество ID сотрудников, которых видит пользователь
        """
        subordinates = set(self.get_subordinates())
        subordinates.add(self.user_id)  # Добавляем себя
        return subordinates