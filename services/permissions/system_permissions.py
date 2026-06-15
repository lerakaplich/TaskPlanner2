# services/permissions/system_permissions.py
from enum import Enum
from typing import Set, Dict, Optional


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

    _permissions: Dict[SystemRole, Set[str]] = {
        SystemRole.ORGANIZATION_HEAD: {
            'can_view_all_employees_stats',  # Может видеть статистику всех сотрудников
            'can_view_all_departments_stats',  # Может видеть статистику всех отделов
            'can_view_all_divisions_stats',  # Может видеть статистику всех подразделений
            'can_approve_overtime_any',  # Может утверждать переработки любых сотрудников
            'can_manage_all_employees',  # Может управлять любыми сотрудниками
        },

        SystemRole.DIVISION_HEAD: {
            'can_view_division_stats',  # Может видеть статистику своего подразделения
            'can_view_department_stats',  # Может видеть статистику отделов подразделения
            'can_approve_overtime_in_division',  # Может утверждать переработки в подразделении
            'can_manage_division_employees',  # Может управлять сотрудниками подразделения
        },

        SystemRole.DEPARTMENT_HEAD: {
            'can_view_department_stats',  # Может видеть статистику своего отдела
            'can_approve_overtime_in_department',  # Может утверждать переработки в отделе
            'can_manage_department_employees',  # Может управлять сотрудниками отдела
        },

        SystemRole.EMPLOYEE: {
            'can_view_own_stats',  # Может видеть только свою статистику
            'can_view_own_overtime',  # Может видеть свои переработки
            # НЕ может утверждать переработки других
            # НЕ может управлять другими сотрудниками
        }
    }

    def __init__(self, user_id: int, role: SystemRole):
        self.user_id = user_id
        self.role = role

    def has_permission(self, permission: str) -> bool:
        return permission in self._permissions.get(self.role, set())

    def can_view_employee_stats(self, target_user_id: int) -> bool:
        """Проверяет, может ли пользователь видеть статистику другого сотрудника"""
        if self.role == SystemRole.ORGANIZATION_HEAD:
            return True
        if self.role == SystemRole.DIVISION_HEAD:
            # Проверить, что target_user_id в подразделении пользователя
            return True  # Должна быть дополнительная проверка
        if self.role == SystemRole.DEPARTMENT_HEAD:
            # Проверить, что target_user_id в отделе пользователя
            return True  # Должна быть дополнительная проверка
        return target_user_id == self.user_id

    def can_approve_overtime(self, target_user_id: int) -> bool:
        """Проверяет, может ли пользователь утверждать переработки"""
        if self.role == SystemRole.ORGANIZATION_HEAD:
            return True
        if self.role == SystemRole.DIVISION_HEAD:
            # Проверить, что target_user_id в подразделении пользователя
            return True
        if self.role == SystemRole.DEPARTMENT_HEAD:
            # Проверить, что target_user_id в отделе пользователя
            return True
        return False