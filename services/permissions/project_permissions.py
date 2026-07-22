# services/permissions/project_permissions.py

from enum import Enum
from typing import Set, Dict, Optional, List
from functools import lru_cache

from models.permissions import CombinedRole, SystemRole
from services.permissions.app_permissions import AppRole


class ProjectRole(Enum):
    """Роли внутри проекта"""
    PROJECT_MANAGER = "project_manager"  # Руководитель проекта
    CURATOR = "curator"  # Куратор проекта
    MEMBER = "member"  # Участник проекта


class ProjectPermissions:
    """
    Права для каждой роли внутри проекта
    """

    # Права для руководителя проекта
    MANAGER_PERMISSIONS: Set[str] = {
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
        'can_change_task_status',

        # Управление колонками
        'can_manage_project_columns',

        # Просмотр
        'can_view_project',
        'can_view_all_tasks',
        'can_view_analytics',
    }

    # Права для куратора проекта
    CURATOR_PERMISSIONS: Set[str] = {
        # Управление проектом (ограничено)
        'can_edit_project',
        'can_archive_project',
        'can_manage_members',

        # Управление задачами
        'can_create_task',
        'can_edit_any_task',  # Может редактировать любые задачи
        'can_delete_any_task',  # Может удалять любые задачи
        'can_move_any_task',
        'can_assign_task',
        'can_change_task_status',

        # Колонки
        'can_manage_project_columns',

        # Просмотр
        'can_view_project',
        'can_view_all_tasks',
        'can_view_analytics',
    }

    # Права для участника проекта
    MEMBER_PERMISSIONS: Set[str] = {
        # Просмотр
        'can_view_project',
        'can_view_own_tasks',  # Видит только свои задачи

        # Управление задачами (только своими)
        'can_create_task',
        'can_edit_own_task',
        'can_move_own_task',
        'can_change_own_task_status',

        # НЕ может:
        # - редактировать проект
        # - управлять участниками
        # - управлять колонками
        # - удалять задачи
        # - видеть чужие задачи
    }

    @classmethod
    def get_permissions(cls, role: ProjectRole) -> Set[str]:
        """Возвращает набор прав для роли"""
        permissions_map = {
            ProjectRole.PROJECT_MANAGER: cls.MANAGER_PERMISSIONS,
            ProjectRole.CURATOR: cls.CURATOR_PERMISSIONS,
            ProjectRole.MEMBER: cls.MEMBER_PERMISSIONS,
        }
        return permissions_map.get(role, set())


class ProjectPermissionManager:
    """
    Менеджер прав для конкретного проекта
    """

    def __init__(self, user_id: int, project_id: int, role: ProjectRole):
        self.user_id = user_id
        self.project_id = project_id
        self.role = role
        self._permissions = ProjectPermissions.get_permissions(role)

    def has_permission(self, permission: str) -> bool:
        """Проверяет наличие права"""
        return permission in self._permissions

    # ===== ПРОВЕРКИ ПРАВ =====

    def can_view_project(self) -> bool:
        """Может просматривать проект"""
        return self.has_permission('can_view_project')

    def can_edit_project(self) -> bool:
        """Может редактировать проект"""
        return self.has_permission('can_edit_project')

    def can_archive_project(self) -> bool:
        """Может архивировать проект"""
        return self.has_permission('can_archive_project')

    def can_manage_members(self) -> bool:
        """Может управлять участниками"""
        return self.has_permission('can_manage_members')

    def can_manage_project_columns(self) -> bool:
        """Может управлять колонками проекта"""
        return self.has_permission('can_manage_project_columns')

    # ===== ПРАВА НА ЗАДАЧИ =====

    def can_create_task(self) -> bool:
        """Может создавать задачи"""
        return self.has_permission('can_create_task')

    def can_view_task(self, task_creator_id: Optional[int] = None) -> bool:
        """
        Может просматривать задачу
        - Руководитель/куратор: все задачи
        - Участник: только свои задачи
        """
        if self.has_permission('can_view_all_tasks'):
            return True
        if self.has_permission('can_view_own_tasks') and task_creator_id == self.user_id:
            return True
        return False

    def can_edit_task(self, task_creator_id: Optional[int] = None) -> bool:
        """
        Может редактировать задачу
        - Руководитель/куратор: любые задачи
        - Участник: только свои задачи
        """
        if self.has_permission('can_edit_any_task'):
            return True
        if self.has_permission('can_edit_own_task') and task_creator_id == self.user_id:
            return True
        return False

    def can_delete_task(self, task_creator_id: Optional[int] = None) -> bool:
        """
        Может удалять задачу
        - Руководитель/куратор: любые задачи
        - Участник: НЕ может удалять
        """
        return self.has_permission('can_delete_any_task')

    def can_move_task(self, task_creator_id: Optional[int] = None) -> bool:
        """
        Может перемещать задачу между колонками
        - Руководитель/куратор: любые задачи
        - Участник: только свои задачи
        """
        if self.has_permission('can_move_any_task'):
            return True
        if self.has_permission('can_move_own_task') and task_creator_id == self.user_id:
            return True
        return False

    def can_assign_task(self) -> bool:
        """Может назначать исполнителя"""
        return self.has_permission('can_assign_task')

    def can_change_task_status(self, task_creator_id: Optional[int] = None) -> bool:
        """
        Может менять статус задачи
        - Руководитель/куратор: любые задачи
        - Участник: только свои задачи
        """
        if self.has_permission('can_change_task_status'):
            return True
        if self.has_permission('can_change_own_task_status') and task_creator_id == self.user_id:
            return True
        return False

    def can_view_analytics(self) -> bool:
        """Может видеть страницу аналитики проекта"""
        return self.has_permission('can_view_analytics')

    def get_combined_role_for_project(self, user_id: int, project_id: int,
                                      app_role: AppRole, system_role: SystemRole) -> CombinedRole:
        """
        Получает комбинированную роль для пользователя в проекте
        """
        project_role = self._get_project_role(user_id, project_id)
        return CombinedRole(app_role, project_role, system_role)

    def get_task_visibility_filter(self) -> str:
        """
        Возвращает фильтр для отображения задач
        - 'all': показывать все задачи
        - 'own': показывать только свои задачи
        """
        if self.has_permission('can_view_all_tasks'):
            return 'all'
        return 'own'