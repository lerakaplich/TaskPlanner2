# services/permissions/permission_service.py

from typing import Optional

from services.permissions.app_permissions import AppPermissionManager, AppRole
from services.permissions.project_permissions import ProjectPermissionManager, ProjectRole
from services.permissions.system_permissions import SystemRole


class PermissionService:
    """
    Единый сервис для управления всеми типами прав
    Объединяет AppPermissionManager, ProjectPermissionManager и SystemPermissionManager
    """

    def __init__(self, user_id: int, app_service=None, project_service=None, employee_service=None):
        self.user_id = user_id
        self._project_role_cache = {}

        # Инициализируем менеджеры прав
        app_role = self._get_app_role(app_service)
        self.app_manager = AppPermissionManager(user_id, app_role)

        self.project_service = project_service
        self.employee_service = employee_service

        # Если есть project_service, используем его для определения ролей
        if project_service and hasattr(project_service, 'get_project_role'):
            self._get_project_role = project_service.get_project_role
        else:
            self._get_project_role = self._default_get_project_role

    def _default_get_project_role(self, user_id: int, project_id: int) -> ProjectRole:
        """Заглушка для определения роли в проекте"""
        return ProjectRole.MEMBER

    def _get_project_role(self, project_id: int) -> ProjectRole:
        """Определяет роль пользователя в проекте с кэшированием"""
        if project_id not in self._project_role_cache:
            role = self._get_project_role(self.user_id, project_id)
            self._project_role_cache[project_id] = role or ProjectRole.MEMBER
        return self._project_role_cache[project_id]

    def can_archive_project(self, project_id: int) -> bool:
        """
        Проверяет, может ли пользователь архивировать проект
        """
        # 1. Проверяем права на уровне приложения (суперадмин может всё)
        if self.app_manager.can_archive_any_project():
            return True

        # 2. Проверяем права на уровне проекта
        if self.project_service and hasattr(self.project_service, 'can_archive_project'):
            return self.project_service.can_archive_project(project_id, self.user_id)

        # 3. Проверяем роль в проекте
        role = self._get_project_role(project_id)
        return role in (ProjectRole.PROJECT_MANAGER, ProjectRole.CURATOR)

    def get_project_permissions(self, project_id: int) -> ProjectPermissionManager:
        """Возвращает менеджер прав для конкретного проекта"""
        if project_id not in self._project_permission_cache:
            role = self._get_project_role(project_id)
            self._project_permission_cache[project_id] = ProjectPermissionManager(
                self.user_id, project_id, role
            )
        return self._project_permission_cache[project_id]

    def _get_app_role(self, service) -> AppRole:
        """Получает роль на уровне приложения"""
        if service and hasattr(service, 'get_app_role'):
            return service.get_app_role(self.user_id)
        return AppRole.USER

    def _get_system_role(self) -> SystemRole:
        """Получает роль в системе (должность)"""
        if self.employee_service:
            return self.employee_service.get_system_role(self.user_id)
        return SystemRole.EMPLOYEE

    def can_show_create_project_button(self) -> bool:
        return self.app_manager.can_create_project()

    def can_edit_project(self, project_id: int) -> bool:
        if self.app_manager.role in (AppRole.SUPER_ADMIN, AppRole.ADMIN):
            if self.app_manager.can_edit_any_project():
                return True
        return False

    def get_project_button_text(self, project_id: int, is_edit_mode: bool = False) -> str:
        if is_edit_mode:
            if self.can_edit_project(project_id):
                return "Сохранить изменения"
            return "Закрыть"
        else:
            if self.can_edit_project(project_id):
                return "Редактировать"
            return "Подробнее"

    def can_edit_project_dialog(self, project_id: int) -> bool:
        return self.can_edit_project(project_id)

    def can_show_project_columns_selector(self, project_id: int) -> bool:
        project_perms = self.get_project_permissions(project_id)
        return project_perms.can_manage_project_columns()

    def can_show_analytics_page(self) -> bool:
        return self.app_manager.can_view_analytics()

    def can_show_overtime_tab_all(self) -> bool:
        system_role = self._get_system_role()
        return system_role != SystemRole.EMPLOYEE

    def can_import_overtime(self) -> bool:
        return self.app_manager.can_import_overtime()

    def can_add_overtime(self) -> bool:
        return self.app_manager.can_add_overtime()

    def can_show_create_task_button(self, project_id: Optional[int] = None) -> bool:
        if self.app_manager.can_create_task_in_any_project():
            return True

        if project_id and self.app_manager.can_create_task_in_own_projects():
            project_perms = self.get_project_permissions(project_id)
            return project_perms.can_create_task()

        return False

    # ===== МЕТОДЫ ДЛЯ НАСТРОЕК =====

    def can_edit_settings(self) -> bool:
        return self.app_manager.can_edit_settings()

    def can_view_settings(self) -> bool:
        return self.app_manager.can_view_settings()

    def can_show_add_buttons_in_settings(self) -> bool:
        return self.can_edit_settings()

    def can_show_delete_buttons_in_settings(self) -> bool:
        return self.can_edit_settings()

    def get_settings_button_text(self) -> str:
        return "Редактировать" if self.can_edit_settings() else "Подробнее"

    def is_settings_dialog_editable(self) -> bool:
        return self.can_edit_settings()

    def is_employee_tab_read_only(self) -> bool:
        """Вкладка Сотрудники - только просмотр для USER"""
        return self.app_manager.role == AppRole.USER

    def is_departments_tab_read_only(self) -> bool:
        """Вкладка Отделы - только просмотр для USER"""
        return self.app_manager.role == AppRole.USER

    def is_divisions_tab_read_only(self) -> bool:
        """Вкладка Подразделения - только просмотр для USER"""
        return self.app_manager.role == AppRole.USER

    def is_columns_tab_read_only(self) -> bool:
        """Вкладка Колонки - только просмотр для USER и ADMIN"""
        return self.app_manager.role in (AppRole.USER, AppRole.ADMIN)

    def is_tags_tab_read_only(self) -> bool:
        """Вкладка Темы - только просмотр для USER"""
        return self.app_manager.role == AppRole.USER

    def get_app_role(self) -> AppRole:
        return self.app_manager.role