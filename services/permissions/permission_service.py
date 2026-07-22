# services/permissions/permission_service.py

from typing import Optional, Dict, List, Set
from functools import lru_cache

from models.permissions import ProjectRole, SystemRole, CombinedRole
from services.permissions.app_permissions import AppRole
from services.permissions.system_permissions import SystemPermissionManager
from services.projects_service.project_role_service import ProjectRoleService


class PermissionService:
    """
    Единый сервис для управления всеми типами прав
    Использует CombinedRole для комбинирования ролей
    """

    def __init__(self, user_id: int, app_service=None, project_service=None,
                 employee_service=None, session=None):
        self.user_id = user_id
        self.app_service = app_service
        self.project_service = project_service
        self.employee_service = employee_service
        self.session = session
        self._read_only_mode = False

        # Кэш для ролей
        self._project_role_cache = {}
        self._system_role_cache = None
        self._combined_role_cache = None

        # Инициализируем менеджеры прав (для обратной совместимости)
        app_role = self._get_app_role()
        self.app_role = app_role

        # Для совместимости со старым кодом создаём полноценный прокси
        self.app_manager = _AppManagerProxy(app_role, self)

        # Сервис для определения ролей в проектах
        if session and hasattr(project_service, 'session'):
            self.role_service = ProjectRoleService(project_service.session)
        else:
            self.role_service = None

    # services/permissions/permission_service.py

    def _get_app_role(self) -> AppRole:
        """Получает роль на уровне приложения"""
        # ПРОВЕРЯЕМ СНАЧАЛА В БД
        try:
            from sqlalchemy import text
            if self.session:
                stmt = text("SELECT role FROM public.employees_data WHERE employee_id = :user_id")
                result = self.session.execute(stmt, {'user_id': self.user_id}).first()
                if result:
                    role_str = str(result[0]).strip().lower()
                    if role_str in ('super_admin', 'superadmin'):
                        return AppRole.SUPER_ADMIN
                    elif role_str == 'admin':
                        return AppRole.ADMIN
                    elif role_str == 'user':
                        return AppRole.USER
        except Exception as e:
            print(f"⚠️ Ошибка получения роли из БД: {e}")

        # Если не нашли в БД, пробуем через сервис
        if self.app_service:
            if hasattr(self.app_service, 'get_app_role'):
                try:
                    result = self.app_service.get_app_role(self.user_id)
                    if isinstance(result, AppRole):
                        return result
                except TypeError:
                    try:
                        result = self.app_service.get_app_role()
                        if isinstance(result, AppRole):
                            return result
                    except:
                        pass

        return AppRole.USER

    def _get_project_role(self, project_id: int) -> Optional[ProjectRole]:
        """Определяет роль пользователя в проекте с кэшированием"""
        if project_id not in self._project_role_cache:
            if self.role_service:
                role = self.role_service.get_project_role(self.user_id, project_id)
                if role:
                    self._project_role_cache[project_id] = role
                else:
                    self._project_role_cache[project_id] = None
            else:
                self._project_role_cache[project_id] = None
        return self._project_role_cache[project_id]

    # services/permissions/permission_service.py

    def can_edit_employee(self, target_employee_id: int) -> bool:
        """Проверяет, может ли пользователь редактировать указанного сотрудника"""
        combined = self.get_combined_role()

        # Суперадмин может редактировать всех
        if combined.is_super_admin:
            return True

        # Администратор может редактировать всех, кроме суперадминов
        if combined.is_admin:
            try:
                from sqlalchemy import text
                if self.session:
                    stmt = text("SELECT role FROM public.employees_data WHERE employee_id = :user_id")
                    result = self.session.execute(stmt, {'user_id': target_employee_id}).first()
                    if result and str(result[0]).strip().lower() == 'superadmin':
                        return False
            except:
                pass
            return True

        # Пользователь может редактировать только себя
        if combined.is_user:
            return target_employee_id == self.user_id

        return False

    def can_delete_employee(self, target_employee_id: int) -> bool:
        """Проверяет, может ли пользователь удалять указанного сотрудника"""
        combined = self.get_combined_role()

        # Суперадмин может удалять всех
        if combined.is_super_admin:
            return True

        # Администратор может удалять всех, кроме суперадминов и админов
        if combined.is_admin:
            try:
                from sqlalchemy import text
                if self.session:
                    stmt = text("SELECT role FROM public.employees_data WHERE employee_id = :user_id")
                    result = self.session.execute(stmt, {'user_id': target_employee_id}).first()
                    if result:
                        role = str(result[0]).strip().lower()
                        if role in ('superadmin', 'admin'):
                            return False
            except:
                pass
            return True

        # Пользователь не может удалять никого
        return False

    def _get_system_role(self) -> SystemRole:
        """Определяет системную роль пользователя"""
        if self.employee_service and hasattr(self.employee_service, 'get_system_role'):
            try:
                return self.employee_service.get_system_role(self.user_id)
            except Exception:
                pass
        return SystemRole.EMPLOYEE

    def get_combined_role(self, project_id: Optional[int] = None) -> CombinedRole:
        """Возвращает комбинированную роль для пользователя"""
        # Всегда получаем свежую роль из БД
        app_role = self._get_app_role()
        project_role = self._get_project_role(project_id) if project_id else None
        system_role = self._get_system_role()

        return CombinedRole(app_role, project_role, system_role)

    def has_permission(self, permission: str) -> bool:
        """Проверяет наличие права (для обратной совместимости)"""
        combined = self.get_combined_role()
        if permission == 'can_edit_any_project':
            return combined.is_super_admin or combined.is_admin
        if permission == 'can_archive_any_project':
            return combined.is_super_admin
        if permission == 'can_import_overtime':
            return combined.can_import_overtime()
        if permission == 'can_add_overtime_for_any':
            return combined.can_add_overtime()
        return False

    def can_show_create_project_button(self) -> bool:
        combined = self.get_combined_role()
        print(f"🔍 combined.app_role = {combined.app_role}")
        print(f"🔍 combined.app_role type = {type(combined.app_role)}")
        print(f"🔍 AppRole.SUPER_ADMIN = {AppRole.SUPER_ADMIN}")
        print(f"🔍 AppRole.SUPER_ADMIN type = {type(AppRole.SUPER_ADMIN)}")
        print(f"🔍 combined.is_super_admin = {combined.is_super_admin}")
        return combined.is_super_admin or combined.is_admin

    def can_create_project(self) -> bool:
        combined = self.get_combined_role()
        return combined.is_super_admin or combined.is_admin

    def can_edit_project(self, project_id: int) -> bool:
        combined = self.get_combined_role(project_id)
        return combined.can_edit_project()

    def can_archive_project(self, project_id: int) -> bool:
        combined = self.get_combined_role(project_id)
        return combined.can_archive_project()

    def can_import_overtime(self) -> bool:
        combined = self.get_combined_role()
        return combined.can_import_overtime()

    def can_add_overtime(self) -> bool:
        combined = self.get_combined_role()
        return combined.can_add_overtime()

    def can_show_overtime_tab_all(self) -> bool:
        combined = self.get_combined_role()
        return combined.can_view_all_overtime()

    def can_view_settings(self) -> bool:
        combined = self.get_combined_role()
        return combined.can_view_settings()

    def can_edit_settings(self) -> bool:
        combined = self.get_combined_role()
        return combined.can_edit_settings()

    def can_show_add_buttons_in_settings(self) -> bool:
        if self._read_only_mode:
            return False
        combined = self.get_combined_role()
        return combined.can_manage_employees()

    def can_show_delete_buttons_in_settings(self) -> bool:
        return self.can_show_add_buttons_in_settings()

    def get_settings_button_text(self) -> str:
        if self.can_show_add_buttons_in_settings():
            return "Редактировать"
        return "Подробнее"

    def is_employee_tab_read_only(self) -> bool:
        combined = self.get_combined_role()
        return combined.is_user and combined.is_employee

    def is_departments_tab_read_only(self) -> bool:
        combined = self.get_combined_role()
        return combined.is_user and combined.is_employee

    def is_divisions_tab_read_only(self) -> bool:
        combined = self.get_combined_role()
        return combined.is_user and combined.is_employee

    def is_columns_tab_read_only(self) -> bool:
        combined = self.get_combined_role()
        return combined.is_user or combined.is_admin

    def is_tags_tab_read_only(self) -> bool:
        combined = self.get_combined_role()
        return combined.is_user and combined.is_employee

    def can_view_contacts(self, target_employee_id: int) -> bool:
        combined = self.get_combined_role()
        return combined.can_view_contacts(target_employee_id, self.user_id)

    def get_project_button_text(self, project_id: int, is_edit_mode: bool = False) -> str:
        combined = self.get_combined_role(project_id)
        return combined.get_button_text(is_edit_mode)

    def get_task_visibility_filter(self, project_id: int) -> str:
        combined = self.get_combined_role(project_id)
        return combined.get_task_visibility_filter()

    def get_app_role(self) -> AppRole:
        return self._get_app_role()

    def clear_cache(self):
        self._project_role_cache.clear()
        self._system_role_cache = None
        self._combined_role_cache = None

    # services/permissions/permission_service.py

    def get_filtered_employees(self, employees: List[Dict]) -> List[Dict]:
        """
        Фильтрует список сотрудников в зависимости от прав пользователя.
        Для суперадмина и админа - все сотрудники.
        Для начальников - только подчинённые.
        """
        # Суперадмин и админ видят всех
        combined = self.get_combined_role()
        if combined.is_super_admin or combined.is_admin:
            return employees  # ← ВОЗВРАЩАЕМ ВСЕХ, БЕЗ ФИЛЬТРАЦИИ

        # Для начальников - фильтруем по иерархии
        system_manager = SystemPermissionManager(
            user_id=self.user_id,
            role=self._get_system_role(),
            session=self.session
        )
        visible_ids = system_manager.get_visible_employee_ids()

        return [emp for emp in employees if emp.get('id') in visible_ids]

    def get_filtered_departments(self, departments: List[Dict]) -> List[Dict]:
        """
        Фильтрует список отделов в зависимости от прав пользователя.
        """
        combined = self.get_combined_role()
        if combined.is_super_admin or combined.is_admin:
            return departments

        system_manager = SystemPermissionManager(
            user_id=self.user_id,
            role=self._get_system_role(),
            session=self.session
        )
        return system_manager.get_filtered_departments(departments)

    def get_filtered_divisions(self, divisions: List[Dict]) -> List[Dict]:
        """
        Фильтрует список подразделений в зависимости от прав пользователя.
        """
        combined = self.get_combined_role()
        if combined.is_super_admin or combined.is_admin:
            return divisions

        system_manager = SystemPermissionManager(
            user_id=self.user_id,
            role=self._get_system_role(),
            session=self.session
        )
        return system_manager.get_filtered_divisions(divisions)


class _AppManagerProxy:
    """
    Прокси для обратной совместимости с AppPermissionManager
    """

    def __init__(self, role: AppRole, service: 'PermissionService'):
        self.role = role
        self._service = service

    def get_visible_tabs(self) -> Set[str]:
        # Базовые вкладки, которые видят все
        tabs = {'projects', 'my_tasks', 'other_tasks', 'gantt', 'chat', 'archive'}

        # Переработки - ВИДЯТ ВСЕ (страница с вкладкой "Мои переработки")
        tabs.add('overtime')

        # Настройки - видят все (но с разными правами)
        tabs.add('settings')

        # Аналитика - только для админов и суперадминов
        combined = self._service.get_combined_role()
        if combined.is_super_admin or combined.is_admin:
            tabs.add('analytics')

        return tabs

    def has_permission(self, permission: str) -> bool:
        return self._service.has_permission(permission)

    def can_create_project(self) -> bool:
        return self._service.can_create_project()

    def can_edit_any_project(self) -> bool:
        combined = self._service.get_combined_role()
        return combined.is_super_admin or combined.is_admin

    def can_archive_any_project(self) -> bool:
        combined = self._service.get_combined_role()
        return combined.is_super_admin

    def can_view_analytics(self) -> bool:
        combined = self._service.get_combined_role()
        return combined.is_super_admin or combined.is_admin

    def can_view_settings(self) -> bool:
        return True

    def can_edit_settings(self) -> bool:
        combined = self._service.get_combined_role()
        return combined.is_super_admin or combined.is_admin

    def can_view_own_overtime(self) -> bool:
        return True

    def can_view_all_overtime(self) -> bool:
        combined = self._service.get_combined_role()
        return combined.can_view_all_overtime()

    def can_import_overtime(self) -> bool:
        combined = self._service.get_combined_role()
        return combined.can_import_overtime()

    def can_add_overtime(self) -> bool:
        combined = self._service.get_combined_role()
        return combined.can_add_overtime()

    def can_create_task_in_any_project(self) -> bool:
        combined = self._service.get_combined_role()
        return combined.is_super_admin or combined.is_admin

    def can_create_task_in_own_projects(self) -> bool:
        return True