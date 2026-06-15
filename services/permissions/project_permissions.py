# services/permissions/project_permissions.py
from enum import Enum
from typing import Set, Dict, Any, Optional


class ProjectRole(Enum):
    """Роли внутри проекта"""
    PROJECT_MANAGER = "project_manager"  # Руководитель проекта
    CURATOR = "curator"  # Куратор проекта
    MEMBER = "member"  # Участник проекта


class ProjectPermissionManager:
    """
    Менеджер прав на уровне проекта
    Определяет, что может делать пользователь внутри конкретного проекта
    """

    # Права для каждой роли внутри проекта
    _permissions: Dict[ProjectRole, Set[str]] = {
        ProjectRole.PROJECT_MANAGER: {
            # Управление проектом
            'can_edit_project',  # Может редактировать проект
            'can_delete_project',  # Может удалять проект
            'can_archive_project',  # Может архивировать проект
            'can_manage_members',  # Может управлять участниками
            'can_manage_admins',  # Может управлять администраторами

            # Управление задачами
            'can_create_task',  # Может создавать задачи
            'can_edit_any_task',  # Может редактировать любые задачи проекта
            'can_delete_any_task',  # Может удалять любые задачи проекта
            'can_move_any_task',  # Может перемещать любые задачи
            'can_assign_task',  # Может назначать исполнителей

            # Управление колонками проекта
            'can_manage_project_columns',  # Может управлять колонками проекта
        },

        ProjectRole.CURATOR: {
            # Управление проектом (ограничено)
            'can_edit_project',  # Может редактировать проект
            'can_archive_project',  # Может архивировать проект
            'can_manage_members',  # Может управлять участниками

            # Управление задачами
            'can_create_task',  # Может создавать задачи
            'can_edit_any_task',  # Может редактировать любые задачи
            'can_delete_any_task',  # Может удалять любые задачи
            'can_move_any_task',  # Может перемещать любые задачи
            'can_assign_task',  # Может назначать исполнителей

            # Колонки
            'can_manage_project_columns',  # Может управлять колонками

            # НЕ может удалять проект
        },

        ProjectRole.MEMBER: {
            # Управление проектом (только просмотр)
            'can_view_project',  # Может просматривать проект

            # Управление задачами (ограничено)
            'can_create_task',  # Может создавать задачи
            'can_edit_own_task',  # Может редактировать только свои задачи
            'can_move_own_task',  # Может перемещать только свои задачи

            # НЕ может:
            # - удалять задачи
            # - редактировать проект
            # - управлять участниками
            # - управлять колонками
        }
    }

    def __init__(self, user_id: int, project_id: int, role: ProjectRole):
        self.user_id = user_id
        self.project_id = project_id
        self.role = role

    def has_permission(self, permission: str) -> bool:
        """Проверяет, есть ли у пользователя право внутри проекта"""
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