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

        # Инициализируем менеджеры прав
        app_role = self._get_app_role(app_service)
        self.app_manager = AppPermissionManager(user_id, app_role)

        self.project_service = project_service
        self.employee_service = employee_service

        # Кэш для ролей в проектах
        self._project_role_cache = {}

    def _get_app_role(self, service) -> AppRole:
        """Получает роль на уровне приложения"""
        if service and hasattr(service, 'get_app_role'):
            return service.get_app_role(self.user_id)
        return AppRole.USER

    def _get_project_role(self, project_id: int) -> ProjectRole:
        """Определяет роль пользователя в проекте"""
        if self.project_service and hasattr(self.project_service, 'get_project_role'):
            return self.project_service.get_project_role(self.user_id, project_id)
        return ProjectRole.MEMBER

    def can_archive_project(self, project_id: int) -> bool:
        """Может ли пользователь архивировать проект"""
        if self.app_manager.can_archive_any_project():
            return True

        if self.project_service and hasattr(self.project_service, 'can_archive_project'):
            return self.project_service.can_archive_project(project_id, self.user_id)

        project_perms = self.get_project_permissions(project_id)
        return project_perms.has_permission('can_archive_project')

    def _get_system_role(self) -> SystemRole:
        """Получает роль в системе (должность)"""
        if self.employee_service:
            return self.employee_service.get_system_role(self.user_id)
        return SystemRole.EMPLOYEE

    def get_project_permissions(self, project_id: int) -> ProjectPermissionManager:
        """Возвращает менеджер прав для конкретного проекта"""
        if project_id not in self._project_role_cache:
            role = self._get_project_role(project_id)
            self._project_role_cache[project_id] = ProjectPermissionManager(
                self.user_id, project_id, role
            )
        return self._project_role_cache[project_id]

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

    def get_app_role(self) -> AppRole:
        return self.app_manager.role