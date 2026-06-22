# services/permissions/project_permissions.py

from enum import Enum
from typing import Set, Dict, Optional
from models.projects import ProjectRoleEnum  # Импортируем из моделей


class ProjectRole(Enum):
    """Роли внутри проекта (для PermissionManager)"""
    PROJECT_MANAGER = "project_manager"
    CURATOR = "curator"
    MEMBER = "member"

    @classmethod
    def from_enum(cls, role_enum):
        """Конвертирует ProjectRoleEnum в ProjectRole"""
        if role_enum == ProjectRoleEnum.PROJECT_MANAGER:
            return cls.PROJECT_MANAGER
        elif role_enum == ProjectRoleEnum.CURATOR:
            return cls.CURATOR
        else:
            return cls.MEMBER


class ProjectPermissionManager:
    """
    Менеджер прав на уровне проекта
    """

    _permissions: Dict[ProjectRole, Set[str]] = {
        ProjectRole.PROJECT_MANAGER: {
            # Управление проектом
            'can_edit_project',
            'can_delete_project',
            'can_archive_project',
            'can_manage_members',
            'can_manage_admins',
            # Управление задачами
            'can_create_task',
            'can_edit_any_task',
            'can_delete_any_task',
            'can_move_any_task',
            'can_assign_task',
            # Управление колонками
            'can_manage_project_columns',
        },

        ProjectRole.CURATOR: {
            # Управление проектом (ограничено)
            'can_edit_project',
            'can_archive_project',
            'can_manage_members',
            # Управление задачами
            'can_create_task',
            'can_edit_any_task',
            'can_delete_any_task',
            'can_move_any_task',
            'can_assign_task',
            # Колонки
            'can_manage_project_columns',
        },

        ProjectRole.MEMBER: {
            'can_view_project',
            'can_create_task',
            'can_edit_own_task',
            'can_move_own_task',
            # НЕ может удалять задачи
            # НЕ может редактировать проект
            # НЕ может управлять участниками
            # НЕ может управлять колонками
        }
    }

    def __init__(self, user_id: int, project_id: int, role: ProjectRole):
        self.user_id = user_id
        self.project_id = project_id
        self.role = role

    def has_permission(self, permission: str) -> bool:
        return permission in self._permissions.get(self.role, set())

    def can_edit_project(self) -> bool:
        return self.has_permission('can_edit_project')

    def can_manage_members(self) -> bool:
        return self.has_permission('can_manage_members')

    def can_create_task(self) -> bool:
        return self.has_permission('can_create_task')

    def can_edit_task(self, task_creator_id: Optional[int] = None) -> bool:
        """Проверяет, может ли пользователь редактировать задачу"""
        if self.has_permission('can_edit_any_task'):
            return True
        if self.has_permission('can_edit_own_task') and task_creator_id == self.user_id:
            return True
        return False

    def can_delete_task(self, task_creator_id: Optional[int] = None) -> bool:
        """Проверяет, может ли пользователь удалять задачу"""
        return self.has_permission('can_delete_any_task')

    def can_move_task(self, task_creator_id: Optional[int] = None) -> bool:
        """Проверяет, может ли пользователь перемещать задачу"""
        if self.has_permission('can_move_any_task'):
            return True
        if self.has_permission('can_move_own_task') and task_creator_id == self.user_id:
            return True
        return False

    def can_manage_project_columns(self) -> bool:
        return self.has_permission('can_manage_project_columns')

    @classmethod
    def get_role_in_project(cls, user_id: int, project_id: int, service=None) -> Optional['ProjectRole']:
        """
        Определяет роль пользователя в проекте
        Должен быть реализован через сервис, который читает из БД
        """
        if service:
            return service.get_project_role(user_id, project_id)
        return ProjectRole.MEMBER  # По умолчанию участник