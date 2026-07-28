# services/permissions/permission_service.py

from typing import Optional, Dict, List, Set, Any
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

    def can_edit_employee(self, target_employee_id: int) -> bool:
        """
        Проверяет, может ли пользователь редактировать указанного сотрудника
        Учитывает:
        - Роль в приложении (superadmin, admin, user)
        - Системную роль (начальник организации, подразделения, отдела)
        """
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

        # ===== ПРОВЕРКА СИСТЕМНОЙ РОЛИ (НАЧАЛЬНИК) =====
        system_role = self._get_system_role()

        # Если пользователь - начальник отдела
        if system_role == SystemRole.DEPARTMENT_HEAD:
            # Проверяем, находится ли сотрудник в отделе начальника
            return self._is_employee_in_my_department(target_employee_id)

        # Если пользователь - начальник подразделения
        if system_role == SystemRole.DIVISION_HEAD:
            return self._is_employee_in_my_division(target_employee_id)

        # Если пользователь - начальник организации
        if system_role == SystemRole.ORGANIZATION_HEAD:
            return True

        # Пользователь может редактировать только себя
        if combined.is_user:
            return target_employee_id == self.user_id

        return False

    def can_delete_employee(self, target_employee_id: int) -> bool:
        """
        Проверяет, может ли пользователь удалять указанного сотрудника
        Учитывает:
        - Роль в приложении (superadmin, admin, user)
        - Системную роль (начальник организации, подразделения, отдела)
        """
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

        # ===== ПРОВЕРКА СИСТЕМНОЙ РОЛИ (НАЧАЛЬНИК) =====
        system_role = self._get_system_role()

        # Начальник отдела может удалять сотрудников своего отдела
        if system_role == SystemRole.DEPARTMENT_HEAD:
            return self._is_employee_in_my_department(target_employee_id)

        # Начальник подразделения может удалять сотрудников своего подразделения
        if system_role == SystemRole.DIVISION_HEAD:
            return self._is_employee_in_my_division(target_employee_id)

        # Начальник организации может удалять всех
        if system_role == SystemRole.ORGANIZATION_HEAD:
            return True

        # Пользователь не может удалять никого
        return False

    def _is_employee_in_my_department(self, target_employee_id: int) -> bool:
        """Проверяет, находится ли сотрудник в отделе текущего пользователя (начальника отдела)"""
        try:
            from sqlalchemy import text
            if not self.session:
                return False

            # Получаем ID отдела, где пользователь - начальник
            # (поле boss содержит ID начальников через запятую)
            stmt = text("""
                SELECT id FROM departments 
                WHERE boss LIKE :boss_pattern
            """)
            result = self.session.execute(stmt, {'boss_pattern': f'%{self.user_id}%'}).first()
            if not result:
                return False

            department_id = result[0]

            # Проверяем, принадлежит ли сотрудник этому отделу
            stmt2 = text("""
                SELECT id FROM employees 
                WHERE id = :emp_id AND department_id = :dept_id
            """)
            result2 = self.session.execute(stmt2, {
                'emp_id': target_employee_id,
                'dept_id': department_id
            }).first()

            return result2 is not None
        except Exception as e:
            print(f"⚠️ Ошибка в _is_employee_in_my_department: {e}")
            return False

    def _is_employee_in_my_division(self, target_employee_id: int) -> bool:
        """Проверяет, находится ли сотрудник в подразделении текущего пользователя (начальника подразделения)"""
        try:
            from sqlalchemy import text
            if not self.session:
                return False

            # Получаем ID подразделения, где пользователь - начальник
            stmt = text("""
                SELECT id FROM divisions 
                WHERE boss LIKE :boss_pattern
            """)
            result = self.session.execute(stmt, {'boss_pattern': f'%{self.user_id}%'}).first()
            if not result:
                return False

            division_id = result[0]

            # Проверяем, принадлежит ли сотрудник этому подразделению
            stmt2 = text("""
                SELECT id FROM employees 
                WHERE id = :emp_id AND division_id = :div_id
            """)
            result2 = self.session.execute(stmt2, {
                'emp_id': target_employee_id,
                'div_id': division_id
            }).first()

            return result2 is not None
        except Exception as e:
            print(f"⚠️ Ошибка в _is_employee_in_my_division: {e}")
            return False

    def _get_system_role(self) -> SystemRole:
        """Определяет системную роль пользователя"""
        print(f"🔍 _get_system_role: self.employee_service = {self.employee_service}")

        if self.employee_service and hasattr(self.employee_service, 'get_system_role'):
            try:
                role = self.employee_service.get_system_role(self.user_id)
                print(f"🔍 _get_system_role: user_id={self.user_id}, role={role}, type={type(role)}")

                # Если role - строка, преобразуем в Enum
                if isinstance(role, str):
                    from services.permissions.system_permissions import SystemRole
                    try:
                        role = SystemRole(role)
                        print(f"🔍 _get_system_role: преобразовано в Enum: {role}")
                    except ValueError:
                        print(f"⚠️ Неизвестная роль: {role}")
                        return SystemRole.EMPLOYEE

                return role
            except Exception as e:
                print(f"⚠️ Ошибка получения системной роли: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️ _get_system_role: employee_service не доступен!")

        return SystemRole.EMPLOYEE

    def get_combined_role(self, project_id: Optional[int] = None) -> CombinedRole:
        """Возвращает комбинированную роль для пользователя"""
        # Всегда получаем свежую роль из БД
        app_role = self._get_app_role()
        project_role = self._get_project_role(project_id) if project_id else None

        # ВАЖНО: получаем системную роль через employee_service
        system_role = self._get_system_role()
        print(f"🔍 get_combined_role: system_role = {system_role}")

        return CombinedRole(app_role, project_role, system_role)

    def get_user_project_role(self, project_id: int) -> Optional[ProjectRole]:
        """
        Возвращает роль пользователя в проекте
        """
        return self._get_project_role(project_id)

    def can_manage_tasks_in_project(self, project_id: int) -> bool:
        """
        Может ли пользователь управлять задачами в проекте (создавать, редактировать, удалять)
        - Руководитель проекта (PROJECT_MANAGER) - может
        - Куратор (CURATOR) - может
        - Обычный участник (MEMBER) - НЕ может
        """
        combined = self.get_combined_role(project_id)
        return combined.can_manage_project()  # или combined.is_project_manager or combined.is_curator

    def can_view_all_tasks(self, project_id: int) -> bool:
        """
        Может ли пользователь видеть все задачи в проекте
        """
        combined = self.get_combined_role(project_id)
        return combined.can_view_all_tasks()

    def can_edit_any_task(self, project_id: int) -> bool:
        """
        Может ли пользователь редактировать любые задачи в проекте
        """
        combined = self.get_combined_role(project_id)
        return combined.can_edit_any_task()

    def can_manage_columns(self, project_id: int) -> bool:
        """
        Может ли пользователь управлять колонками проекта
        """
        combined = self.get_combined_role(project_id)
        return combined.can_manage_columns()

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
        """
        Проверяет, может ли пользователь редактировать проект
        Учитывает:
        - Роль в приложении (superadmin, admin)
        - Роль в проекте (project_manager, curator)
        """
        combined = self.get_combined_role(project_id)
        return combined.can_edit_project()

    def can_manage_project(self, project_id: int) -> bool:
        """
        Может ли пользователь управлять проектом (редактировать, архивировать, управлять участниками)
        """
        combined = self.get_combined_role(project_id)
        return combined.can_manage_project()

    def can_archive_project(self, project_id: int) -> bool:
        """
        Проверяет, может ли пользователь архивировать проект
        Учитывает:
        - Роль в приложении (superadmin)
        - Роль в проекте (project_manager, curator)
        """
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

    def is_departments_tab_read_only(self) -> bool:
        """Определяет, должна ли вкладка отделов быть только для чтения"""
        combined = self.get_combined_role()

        # Суперадмин и админ могут редактировать
        if combined.is_super_admin or combined.is_admin:
            return False

        # Начальник отдела может редактировать (свои отделы)
        if combined.is_department_head:
            return False

        # Начальник подразделения может редактировать (свои подразделения)
        if combined.is_division_head:
            return False

        # Начальник организации может редактировать
        if combined.is_org_head:
            return False

        # Обычный пользователь — только просмотр
        return True

    def is_employee_tab_read_only(self) -> bool:
        """Определяет, должна ли вкладка сотрудников быть только для чтения"""
        combined = self.get_combined_role()

        # Суперадмин и админ могут редактировать
        if combined.is_super_admin or combined.is_admin:
            return False

        # Начальник отдела может редактировать сотрудников своего отдела
        if combined.is_department_head:
            return False

        # Начальник подразделения может редактировать сотрудников своего подразделения
        if combined.is_division_head:
            return False

        # Начальник организации может редактировать
        if combined.is_org_head:
            return False

        # Обычный пользователь — только просмотр
        return True

    def is_divisions_tab_read_only(self) -> bool:
        """Определяет, должна ли вкладка подразделений быть только для чтения"""
        combined = self.get_combined_role()

        # Суперадмин и админ могут редактировать
        if combined.is_super_admin or combined.is_admin:
            return False

        # Начальник подразделения может редактировать
        if combined.is_division_head:
            return False

        # Начальник организации может редактировать
        if combined.is_org_head:
            return False

        # Обычный пользователь — только просмотр
        return True

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

    def can_add_division(self) -> bool:
        """
        Проверяет, может ли пользователь добавлять подразделения
        ТОЛЬКО суперадмин и админ могут добавлять подразделения
        """
        combined = self.get_combined_role()

        # Только суперадмин и админ могут добавлять подразделения
        if combined.is_super_admin or combined.is_admin:
            return True

        # Начальник организации НЕ может добавлять
        # Начальник подразделения НЕ может добавлять
        # Обычный пользователь НЕ может добавлять

        return False

    # services/permissions/permission_service.py

    def can_edit_department(self, department_id: int) -> bool:
        """
        Проверяет, может ли пользователь редактировать отдел
        """
        combined = self.get_combined_role()

        # Суперадмин и админ могут редактировать всё
        if combined.is_super_admin or combined.is_admin:
            return True

        # Начальник организации может редактировать всё
        if combined.is_org_head:
            return True

        # Начальник подразделения может редактировать только отделы в своём подразделении
        if combined.is_division_head:
            return self._is_department_in_my_division(department_id)

        # Начальник отдела может редактировать только свой отдел
        if combined.is_department_head:
            return self._is_department_managed_by_user(department_id)

        return False

    def can_delete_department(self, department_id: int) -> bool:
        """
        Проверяет, может ли пользователь удалять отдел
        """
        combined = self.get_combined_role()

        # Суперадмин и админ могут удалять всё
        if combined.is_super_admin or combined.is_admin:
            return True

        # Начальник организации может удалять всё
        if combined.is_org_head:
            return True

        if combined.is_division_head:
            return self._is_department_in_my_division(department_id)

        # Начальник отдела может удалять только свой отдел
        if combined.is_department_head:
            return self._is_department_managed_by_user(department_id)

        return False

    def can_add_department(self) -> bool:
        """
        Проверяет, может ли пользователь добавлять отделы
        """
        combined = self.get_combined_role()

        # Суперадмин и админ могут добавлять везде
        if combined.is_super_admin or combined.is_admin:
            return True

        # Начальник организации может добавлять везде
        if combined.is_org_head:
            return True

        # Начальник подразделения может добавлять только в своём подразделении
        if combined.is_division_head:
            return True

        # Начальник отдела НЕ может добавлять отделы
        if combined.is_department_head:
            return False

        return False

    def _is_department_in_my_division(self, department_id: int) -> bool:
        """Проверяет, находится ли отдел в подразделении пользователя (начальника подразделения)"""
        try:
            from sqlalchemy import text
            from database import get_employees_session

            with get_employees_session() as emp_session:
                # Получаем отдел
                stmt = text("SELECT division_id FROM departments WHERE id = :dept_id")
                result = emp_session.execute(stmt, {'dept_id': department_id}).first()
                if not result:
                    return False

                division_id = result[0]

                # Проверяем, является ли пользователь начальником этого подразделения
                stmt2 = text("SELECT boss FROM divisions WHERE id = :div_id")
                result2 = emp_session.execute(stmt2, {'div_id': division_id}).first()
                if not result2:
                    return False

                boss_value = result2[0]
                if boss_value is None:
                    return False

                boss_ids = [int(x.strip()) for x in str(boss_value).split(',') if x.strip().isdigit()]
                return self.user_id in boss_ids

        except Exception as e:
            print(f"⚠️ Ошибка в _is_department_in_my_division: {e}")
            return False

    def _is_department_managed_by_user(self, department_id: int) -> bool:
        """Проверяет, управляет ли пользователь отделом (начальник отдела)"""
        try:
            from sqlalchemy import text
            from database import get_employees_session

            with get_employees_session() as emp_session:
                stmt = text("SELECT boss FROM departments WHERE id = :dept_id")
                result = emp_session.execute(stmt, {'dept_id': department_id}).first()
                if not result:
                    return False

                boss_value = result[0]
                if boss_value is None:
                    return False

                boss_ids = [int(x.strip()) for x in str(boss_value).split(',') if x.strip().isdigit()]
                return self.user_id in boss_ids

        except Exception as e:
            print(f"⚠️ Ошибка в _is_department_managed_by_user: {e}")
            return False

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

    def can_edit_division(self, division_id: int) -> bool:
        """
        Проверяет, может ли пользователь редактировать подразделение
        """
        combined = self.get_combined_role()

        # Суперадмин и админ могут редактировать все
        if combined.is_super_admin or combined.is_admin:
            return True

        # Начальник организации может редактировать все
        if combined.is_org_head:
            return True

        # Начальник подразделения может редактировать только своё
        if combined.is_division_head:
            return self._is_division_managed_by_user(division_id)

        return False

    def can_delete_division(self, division_id: int) -> bool:
        """
        Проверяет, может ли пользователь удалять подразделение
        ТОЛЬКО суперадмин и админ могут удалять подразделения
        """
        combined = self.get_combined_role()

        # Только суперадмин и админ могут удалять подразделения
        if combined.is_super_admin or combined.is_admin:
            return True

        # Начальник организации НЕ может удалять
        # Начальник подразделения НЕ может удалять
        # Обычный пользователь НЕ может удалять

        return False

    def _is_division_managed_by_user(self, division_id: int) -> bool:
        """Проверяет, управляет ли пользователь указанным подразделением"""
        try:
            from sqlalchemy import text
            from database import get_employees_session

            # ✅ ИСПРАВЛЕНО: используем отдельную сессию для employees БД
            with get_employees_session() as emp_session:
                stmt = text("""
                    SELECT id, boss FROM divisions 
                    WHERE id = :div_id
                """)

                result = emp_session.execute(stmt, {'div_id': division_id}).first()
                if not result:
                    print(f"⚠️ Подразделение {division_id} не найдено")
                    return False

                boss_value = result[1]
                print(
                    f"🔍 _is_division_managed_by_user: division_id={division_id}, boss='{boss_value}', user_id={self.user_id}")

                if boss_value is None:
                    return False

                boss_str = str(boss_value)
                boss_ids = [int(x.strip()) for x in boss_str.split(',') if x.strip().isdigit()]
                print(f"🔍 boss_ids: {boss_ids}")

                return self.user_id in boss_ids

        except Exception as e:
            print(f"⚠️ Ошибка в _is_division_managed_by_user: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_editable_division_ids(self, user_id: int) -> List[int]:
        """
        Возвращает ID подразделений, которые пользователь может редактировать.
        """
        if not user_id:
            return []

        try:
            from database import get_employees_session
            from sqlalchemy import text

            with get_employees_session() as emp_session:
                stmt = text("""
                    SELECT id, boss FROM divisions 
                    WHERE boss LIKE :pattern1 
                    OR boss LIKE :pattern2
                    OR boss = :exact
                """)

                results = emp_session.execute(
                    stmt,
                    {
                        'pattern1': f'%,{user_id},%',
                        'pattern2': f'{user_id},%',
                        'exact': str(user_id)
                    }
                ).fetchall()

                return [row[0] for row in results]

        except Exception as e:
            print(f"⚠️ Ошибка в get_editable_division_ids: {e}")
            # Откатываем транзакцию основной сессии, если она была прервана
            try:
                self.session.rollback()
            except:
                pass
            return []

    def can_create_task_in_project(self, project_id: int) -> bool:
        """
        Может ли пользователь создавать задачи в проекте
        - Руководитель проекта (PROJECT_MANAGER) - может
        - Куратор (CURATOR) - может
        - Обычный участник (MEMBER) - НЕ может
        """
        combined = self.get_combined_role(project_id)
        return combined.can_create_task_in_project()

    def get_manageable_projects(self) -> List[Dict[str, Any]]:
        """
        Возвращает проекты, где пользователь может управлять задачами
        """
        if not self.project_service:
            return []

        # Используем существующий метод в GanttService
        # или реализуем свою логику через project_service
        try:
            # Получаем все проекты пользователя
            user_projects = self.project_service.get_user_projects_with_roles(self.user_id)
            manageable = []
            for project in user_projects:
                project_id = project.get('id')
                role = self.get_user_project_role(project_id)
                if role in (ProjectRole.PROJECT_MANAGER, ProjectRole.CURATOR):
                    manageable.append({
                        'id': project_id,
                        'name': project.get('name', f"Проект #{project_id}")
                    })
            return manageable
        except Exception as e:
            print(f"⚠️ Ошибка получения проектов: {e}")
            return []


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