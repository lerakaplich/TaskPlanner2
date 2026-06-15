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
        # Сначала проверяем глобальные права
        if self.app_manager.can_archive_any_project():
            return True

        # Затем проверяем права в проекте через сервис
        if self.project_service and hasattr(self.project_service, 'can_archive_project'):
            return self.project_service.can_archive_project(project_id, self.user_id)

        # Fallback - проверяем роль в проекте
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
        """Может ли пользователь видеть кнопку создания проекта"""
        return self.app_manager.can_create_project()

    def can_edit_project(self, project_id: int) -> bool:
        """Может ли пользователь редактировать проект"""
        # Проверяем глобальные права (только суперадмин и админ)
        if self.app_manager.role in (AppRole.SUPER_ADMIN, AppRole.ADMIN):
            if self.app_manager.can_edit_any_project():
                return True

        # Для обычного пользователя - НЕТ права на редактирование
        # Даже если он состоит в проекте
        return False

    def get_project_button_text(self, project_id: int, is_edit_mode: bool = False) -> str:
        """
        Определяет текст кнопки для проекта:
        - Если пользователь может редактировать -> "Редактировать"
        - Иначе -> "Подробнее"
        """
        if is_edit_mode:
            # Для окна редактирования
            if self.can_edit_project(project_id):
                return "Сохранить изменения"
            return "Закрыть"
        else:
            # Для карточки проекта
            if self.can_edit_project(project_id):
                return "Редактировать"
            return "Подробнее"

    def can_edit_project_dialog(self, project_id: int) -> bool:
        """
        Может ли пользователь редактировать поля в диалоге проекта
        (True - поля активны, False - только просмотр)
        """
        return self.can_edit_project(project_id)

    def can_show_project_columns_selector(self, project_id: int) -> bool:
        """
        Может ли пользователь видеть/изменять выбор колонок в проекте
        """
        project_perms = self.get_project_permissions(project_id)
        return project_perms.can_manage_project_columns()

    def can_show_analytics_page(self) -> bool:
        """Может ли пользователь видеть страницу аналитики"""
        return self.app_manager.can_view_analytics()

    def can_show_overtime_tab_all(self) -> bool:
        """
        Может ли пользователь видеть вкладку "Все переработки"
        (Начальники могут, обычные пользователи - нет)
        """
        system_role = self._get_system_role()
        return system_role != SystemRole.EMPLOYEE

    def can_import_overtime(self) -> bool:
        """Может ли пользователь импортировать переработки"""
        return self.app_manager.can_import_overtime()

    def can_add_overtime(self) -> bool:
        """Может ли пользователь добавлять переработки"""
        return self.app_manager.can_add_overtime()

    def can_show_create_task_button(self, project_id: Optional[int] = None) -> bool:
        """
        Может ли пользователь видеть кнопку создания задачи
        """
        if self.app_manager.can_create_task_in_any_project():
            return True

        if project_id and self.app_manager.can_create_task_in_own_projects():
            project_perms = self.get_project_permissions(project_id)
            return project_perms.can_create_task()

        return False

    def can_edit_settings(self) -> bool:
        """Может ли пользователь редактировать настройки"""
        return self.app_manager.can_edit_settings()

    def can_show_add_buttons_in_settings(self) -> bool:
        """Может ли пользователь видеть кнопки добавления в настройках"""
        return self.can_edit_settings()

    def can_show_delete_buttons_in_settings(self) -> bool:
        """Может ли пользователь видеть кнопки удаления в настройках"""
        return self.can_edit_settings()

    def get_settings_button_text(self) -> str:
        """
        Определяет текст кнопки в настройках:
        - Если может редактировать -> "Редактировать"
        - Иначе -> "Подробнее"
        """
        return "Редактировать" if self.can_edit_settings() else "Подробнее"

    def is_settings_dialog_editable(self) -> bool:
        """
        Можно ли редактировать поля в диалоге настроек
        """
        return self.can_edit_settings()