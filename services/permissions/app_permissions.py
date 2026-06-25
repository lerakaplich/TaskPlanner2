# services/permissions/app_permissions.py
from enum import Enum
from typing import Set, Dict, Any, Optional
from functools import lru_cache


class AppRole(Enum):
    """Роли на уровне приложения"""
    SUPER_ADMIN = "superadmin"  # Суперадмин - может всё
    ADMIN = "admin"  # Админ - почти всё, кроме управления админами и суперадминами
    USER = "user"  # Пользователь - ограниченный доступ


class AppPermissionManager:
    """
    Менеджер прав на уровне приложения
    Определяет, что может делать пользователь в приложении в целом
    """

    # Права для каждой роли
    _permissions: Dict[AppRole, Set[str]] = {
        AppRole.SUPER_ADMIN: {
            # Управление пользователями
            'can_manage_users',  # Может управлять пользователями
            'can_create_admin',  # Может создавать админов
            'can_delete_admin',  # Может удалять админов
            'can_create_super_admin',  # Может создавать суперадминов
            'can_delete_super_admin',  # Может удалять суперадминов

            # Управление колонками
            'can_create_columns',  # Может создавать колонки
            'can_edit_columns',  # Может редактировать колонки
            'can_delete_columns',  # Может удалять колонки

            # Управление проектами
            'can_create_project',  # Может создавать проекты
            'can_edit_any_project',  # Может редактировать любые проекты
            'can_delete_any_project',  # Может удалять любые проекты
            'can_archive_any_project',  # Может архивировать любые проекты

            # Страницы
            'can_view_analytics',  # Может видеть страницу аналитики
            'can_view_settings',  # Может видеть страницу настроек
            'can_edit_settings',  # Может редактировать настройки

            # Задачи
            'can_create_task_in_any_project',  # Может создавать задачи в любом проекте
            'can_edit_any_task',  # Может редактировать любые задачи
            'can_delete_any_task',  # Может удалять любые задачи

            # Переработки
            'can_import_overtime',  # Может импортировать переработки
            'can_add_overtime_for_any',  # Может добавлять переработки для любого
        },

        AppRole.ADMIN: {
            # Управление пользователями (ограничено)
            'can_manage_users',
            'can_create_admin',  # Админ может создавать админов
            # НЕ может удалять админов
            # НЕ может создавать/удалять суперадминов

            # Управление колонками - НЕ МОЖЕТ
            # 'can_create_columns',
            # 'can_edit_columns',
            # 'can_delete_columns',

            # Управление проектами
            'can_create_project',
            'can_edit_any_project',
            'can_delete_any_project',
            # 'can_archive_any_project',  # УДАЛЯЕМ - админ НЕ может архивировать проекты

            # Страницы
            'can_view_analytics',
            'can_view_settings',
            'can_edit_settings',

            # Задачи
            'can_create_task_in_any_project',
            'can_edit_any_task',
            'can_delete_any_task',

            # Переработки
            'can_import_overtime',
            'can_add_overtime_for_any',
        },

        AppRole.USER: {
            # Управление проектами (только просмотр)
            'can_view_own_projects',  # Может видеть только свои проекты
            # НЕ может создавать проекты
            # НЕ может редактировать проекты
            # НЕ может архивировать проекты

            # Страницы
            'can_view_settings',  # Может видеть настройки, но только для просмотра
            # НЕ может редактировать настройки

            # Задачи (ограничено)
            'can_view_own_tasks',  # Может видеть свои задачи
            'can_create_task_in_own_projects',  # Может создавать задачи в своих проектах

            # Переработки (ограничено)
            'can_view_own_overtime',  # Может видеть свои переработки
        },
    }

    def __init__(self, user_id: int, role: AppRole):
        self.user_id = user_id
        self.role = role

    def can_archive_any_project(self) -> bool:
        return self.has_permission('can_archive_any_project')

    def has_permission(self, permission: str) -> bool:
        """Проверяет, есть ли у пользователя указанное право"""
        return permission in self._permissions.get(self.role, set())

    def can_create_project(self) -> bool:
        return self.has_permission('can_create_project')

    def can_edit_any_project(self) -> bool:
        return self.has_permission('can_edit_any_project')

    def can_view_analytics(self) -> bool:
        return self.has_permission('can_view_analytics')

    def can_view_settings(self) -> bool:
        return self.has_permission('can_view_settings')

    def can_edit_settings(self) -> bool:
        return self.has_permission('can_edit_settings')

    def can_create_columns(self) -> bool:
        return self.has_permission('can_create_columns')

    def can_import_overtime(self) -> bool:
        return self.has_permission('can_import_overtime')

    def can_add_overtime(self) -> bool:
        return self.has_permission('can_add_overtime_for_any')

    def can_create_task_in_any_project(self) -> bool:
        return self.has_permission('can_create_task_in_any_project')

    def can_create_task_in_own_projects(self) -> bool:
        return self.has_permission('can_create_task_in_own_projects')

    def get_visible_tabs(self) -> Set[str]:
        """Возвращает набор видимых для пользователя вкладок"""
        tabs = {'projects', 'my_tasks', 'other_tasks', 'gantt', 'chat', 'archive'}

        if self.has_permission('can_view_analytics'):
            tabs.add('analytics')

        if self.has_permission('can_view_settings'):
            tabs.add('settings')

        if self.has_permission('can_view_own_overtime'):
            tabs.add('overtime')

        return tabs

    @classmethod
    @lru_cache(maxsize=128)
    def get_role_by_user(cls, user_id: int, service=None) -> 'AppRole':
        """
        Определяет роль пользователя на уровне приложения
        Должен быть реализован через сервис, который читает из БД
        """
        if service:
            return service.get_app_role(user_id)
        return AppRole.USER  # По умолчанию пользователь