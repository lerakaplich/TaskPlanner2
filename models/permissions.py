# models/permissions.py

from enum import Enum
from typing import Set, Optional, List

from services.permissions.app_permissions import AppRole


class ProjectRole(Enum):
    """Роли внутри проекта"""
    PROJECT_MANAGER = "project_manager"
    CURATOR = "curator"
    MEMBER = "member"


class SystemRole(Enum):
    """Роли в иерархии организации"""
    ORGANIZATION_HEAD = "organization_head"
    DIVISION_HEAD = "division_head"
    DEPARTMENT_HEAD = "department_head"
    EMPLOYEE = "employee"


# models/permissions.py

# models/permissions.py

class CombinedRole:
    """Комбинированная роль, объединяющая все три уровня прав"""

    def __init__(self, app_role: AppRole, project_role: Optional[ProjectRole] = None,
                 system_role: Optional[SystemRole] = None):
        # Приводим к Enum, если передана строка
        if isinstance(app_role, str):
            try:
                app_role = AppRole(app_role)
            except ValueError:
                app_role = AppRole.USER

        if isinstance(project_role, str) and project_role:
            try:
                project_role = ProjectRole(project_role)
            except ValueError:
                project_role = None

        if isinstance(system_role, str) and system_role:
            try:
                system_role = SystemRole(system_role)
            except ValueError:
                system_role = SystemRole.EMPLOYEE

        self.app_role = app_role
        self.project_role = project_role
        self.system_role = system_role

        # Отладочный вывод для проверки типов
        print(f"🔍 CombinedRole.__init__: app_role={app_role} (type={type(app_role)}), "
              f"project_role={project_role} (type={type(project_role)}), "
              f"system_role={system_role} (type={type(system_role)})")

        # Дополнительная отладка для system_role
        if system_role:
            print(f"🔍 system_role value: {system_role.value if hasattr(system_role, 'value') else system_role}")

    def __repr__(self) -> str:
        return f"CombinedRole(app_role={self.app_role}, project_role={self.project_role}, system_role={self.system_role})"

    def can_view_analytics(self) -> bool:
        """
        Может ли пользователь видеть страницу аналитики.
        Доступна:
        - Суперадминам и админам
        - Кураторам проектов
        - Руководителям проектов
        - Начальникам отделов
        - Начальникам подразделений
        """
        # Суперадмин и админ
        if self.is_super_admin or self.is_admin:
            return True

        # Руководитель проекта или куратор
        if self.is_project_manager or self.is_curator:
            return True

        # Начальник отдела или подразделения
        if self.is_department_head or self.is_division_head:
            return True

        return False

    def can_view_all_tasks(self) -> bool:
        """Может ли пользователь видеть все задачи в проекте"""
        # Суперадмин, админ, руководитель проекта, куратор
        if self.is_super_admin or self.is_admin:
            return True
        if self.project_role in (ProjectRole.PROJECT_MANAGER, ProjectRole.CURATOR):
            return True
        return False

    def can_edit_any_task(self) -> bool:
        """Может ли пользователь редактировать любые задачи в проекте"""
        # Суперадмин, админ, руководитель проекта, куратор
        if self.is_super_admin or self.is_admin:
            return True
        if self.project_role in (ProjectRole.PROJECT_MANAGER, ProjectRole.CURATOR):
            return True
        return False

    def can_manage_project(self) -> bool:
        """Может ли пользователь управлять проектом"""
        # Суперадмин, админ, руководитель проекта, куратор
        if self.is_super_admin or self.is_admin:
            return True
        if self.project_role in (ProjectRole.PROJECT_MANAGER, ProjectRole.CURATOR):
            return True
        return False

    def can_manage_columns(self) -> bool:
        """Может ли пользователь управлять колонками проекта"""
        # Суперадмин, админ, руководитель проекта, куратор
        if self.is_super_admin or self.is_admin:
            return True
        if self.project_role in (ProjectRole.PROJECT_MANAGER, ProjectRole.CURATOR):
            return True
        return False

    def get_task_visibility_filter(self) -> str:
        """
        Возвращает фильтр для отображения задач:
        - 'all': показывать все задачи
        - 'own': показывать только свои задачи
        """
        if self.can_view_all_tasks():
            return 'all'
        return 'own'

    @property
    def is_super_admin(self) -> bool:
        return self.app_role == AppRole.SUPER_ADMIN

    @property
    def is_admin(self) -> bool:
        return self.app_role == AppRole.ADMIN

    @property
    def is_user(self) -> bool:
        return self.app_role == AppRole.USER

    @property
    def is_project_manager(self) -> bool:
        return self.project_role == ProjectRole.PROJECT_MANAGER

    @property
    def is_curator(self) -> bool:
        return self.project_role == ProjectRole.CURATOR

    @property
    def is_member(self) -> bool:
        return self.project_role == ProjectRole.MEMBER

    @property
    def is_org_head(self) -> bool:
        # Используем строковое сравнение для надёжности
        if self.system_role is None:
            return False
        # Получаем значение для сравнения
        sys_value = self.system_role.value if hasattr(self.system_role, 'value') else str(self.system_role)
        target_value = SystemRole.ORGANIZATION_HEAD.value if hasattr(SystemRole.ORGANIZATION_HEAD, 'value') else str(
            SystemRole.ORGANIZATION_HEAD)
        return sys_value == target_value

    @property
    def is_division_head(self) -> bool:
        # Используем строковое сравнение для надёжности
        if self.system_role is None:
            return False
        # Получаем значение для сравнения
        sys_value = self.system_role.value if hasattr(self.system_role, 'value') else str(self.system_role)
        target_value = SystemRole.DIVISION_HEAD.value if hasattr(SystemRole.DIVISION_HEAD, 'value') else str(
            SystemRole.DIVISION_HEAD)
        result = sys_value == target_value
        print(f"🔍 is_division_head: sys_value='{sys_value}', target_value='{target_value}', result={result}")
        return result

    @property
    def is_department_head(self) -> bool:
        if self.system_role is None:
            return False
        sys_value = self.system_role.value if hasattr(self.system_role, 'value') else str(self.system_role)
        target_value = SystemRole.DEPARTMENT_HEAD.value if hasattr(SystemRole.DEPARTMENT_HEAD, 'value') else str(
            SystemRole.DEPARTMENT_HEAD)
        return sys_value == target_value

    @property
    def is_employee(self) -> bool:
        """Является ли пользователь обычным сотрудником (не начальником)"""
        if self.system_role is None:
            return True
        sys_value = self.system_role.value if hasattr(self.system_role, 'value') else str(self.system_role)
        target_value = SystemRole.EMPLOYEE.value if hasattr(SystemRole.EMPLOYEE, 'value') else str(SystemRole.EMPLOYEE)
        return sys_value == target_value

    @property
    def is_manager(self) -> bool:
        """Является ли пользователь начальником (любого уровня)"""
        if self.system_role is None:
            return False
        sys_value = self.system_role.value if hasattr(self.system_role, 'value') else str(self.system_role)
        manager_values = [
            SystemRole.ORGANIZATION_HEAD.value if hasattr(SystemRole.ORGANIZATION_HEAD, 'value') else str(
                SystemRole.ORGANIZATION_HEAD),
            SystemRole.DIVISION_HEAD.value if hasattr(SystemRole.DIVISION_HEAD, 'value') else str(
                SystemRole.DIVISION_HEAD),
            SystemRole.DEPARTMENT_HEAD.value if hasattr(SystemRole.DEPARTMENT_HEAD, 'value') else str(
                SystemRole.DEPARTMENT_HEAD),
        ]
        return sys_value in manager_values

    # models/permissions.py

    def can_create_task_in_project(self) -> bool:
        """
        Может ли пользователь создавать задачи в проекте
        - Руководитель проекта (PROJECT_MANAGER) - может
        - Куратор (CURATOR) - может
        - Обычный участник (MEMBER) - НЕ может
        """
        if self.is_super_admin or self.is_admin:
            return True
        if self.project_role in (ProjectRole.PROJECT_MANAGER, ProjectRole.CURATOR):
            return True
        return False

    def can_edit_project(self, project_id: int = None) -> bool:
        """Может редактировать проект"""
        # Суперадмин всегда может
        if self.is_super_admin:
            return True
        # Админ может редактировать любые проекты (в системе)
        if self.is_admin:
            return True
        # Руководитель проекта может редактировать
        if self.is_project_manager:
            return True
        # Куратор может редактировать
        if self.is_curator:
            return True
        return False

    def can_archive_project(self, project_id: int = None) -> bool:
        """Может архивировать проект"""
        # Суперадмин всегда может
        if self.is_super_admin:
            return True
        # Админ может архивировать любые проекты
        if self.is_admin:
            return True
        # Руководитель проекта может архивировать
        if self.is_project_manager:
            return True
        # Куратор может архивировать
        if self.is_curator:
            return True
        return False

    def can_manage_employees(self) -> bool:
        """Может управлять сотрудниками в настройках"""
        # Суперадмин и админ могут управлять всеми
        if self.is_super_admin or self.is_admin:
            return True
        # Начальник организации может управлять всеми
        if self.is_org_head:
            return True
        # Начальник подразделения может управлять в своём подразделении
        if self.is_division_head:
            return True
        # Начальник отдела может управлять в своём отделе
        if self.is_department_head:
            return True
        return False

    def can_view_contacts(self, target_employee_id: int = None,
                          current_user_id: int = None) -> bool:
        """Может видеть контакты сотрудника"""
        # Всегда видим себя
        if target_employee_id == current_user_id:
            return True
        # Суперадмин и админ видят всех
        if self.is_super_admin or self.is_admin:
            return True
        # Начальники видят подчинённых (определяется на уровне SystemPermissionManager)
        if self.is_org_head or self.is_division_head or self.is_department_head:
            return True
        return False

    def can_create_task(self, project_id: int = None) -> bool:
        """Может создавать задачи"""
        # Все роли в проекте могут создавать задачи
        if self.project_role in (ProjectRole.PROJECT_MANAGER, ProjectRole.CURATOR, ProjectRole.MEMBER):
            return True
        # Суперадмин и админ могут создавать
        if self.is_super_admin or self.is_admin:
            return True
        return False

    def can_edit_own_task(self, task_creator_id: int = None,
                          current_user_id: int = None) -> bool:
        """Может редактировать свои задачи"""
        if task_creator_id == current_user_id:
            return True
        return self.can_edit_any_task()

    def can_delete_task(self) -> bool:
        """Может удалять задачи"""
        # Суперадмин и админ могут удалять
        if self.is_super_admin or self.is_admin:
            return True
        # Руководитель и куратор могут удалять
        if self.is_project_manager or self.is_curator:
            return True
        return False

    def can_import_overtime(self) -> bool:
        """Может импортировать переработки"""
        return self.is_super_admin or self.is_admin

    def can_add_overtime(self) -> bool:
        """Может добавлять переработки"""
        return self.is_super_admin or self.is_admin

    def can_view_all_overtime(self) -> bool:
        """Может видеть все переработки"""
        return self.is_super_admin or self.is_admin or self.is_org_head

    def can_edit_settings(self) -> bool:
        """Может редактировать настройки"""
        return self.is_super_admin or self.is_admin

    def can_view_settings(self) -> bool:
        """Может видеть настройки"""
        return True  # Все пользователи могут видеть настройки

    def get_task_visibility_filter(self) -> str:
        """
        Возвращает фильтр для отображения задач
        - 'all': показывать все задачи
        - 'own': показывать только свои задачи
        """
        if self.is_project_manager or self.is_curator:
            return 'all'
        if self.is_super_admin or self.is_admin:
            return 'all'
        return 'own'

    def get_button_text(self, is_edit_mode: bool = False) -> str:
        """Возвращает текст кнопки в зависимости от прав"""
        if is_edit_mode:
            if self.can_edit_project():
                return "Сохранить изменения"
            return "Закрыть"
        else:
            if self.can_edit_project():
                return "Редактировать"
            return "Подробнее"

    def get_role_display(self) -> str:
        """Возвращает отображаемое название роли"""
        parts = []

        # Приложение
        app_names = {
            AppRole.SUPER_ADMIN: "Суперадминистратор",
            AppRole.ADMIN: "Администратор",
            AppRole.USER: "Пользователь"
        }
        parts.append(app_names.get(self.app_role, "Пользователь"))

        # Проект
        if self.project_role:
            project_names = {
                ProjectRole.PROJECT_MANAGER: "Руководитель проекта",
                ProjectRole.CURATOR: "Куратор проекта",
                ProjectRole.MEMBER: "Участник проекта"
            }
            parts.append(project_names.get(self.project_role, ""))

        # Система
        if self.system_role and self.system_role != SystemRole.EMPLOYEE:
            system_names = {
                SystemRole.ORGANIZATION_HEAD: "Начальник организации",
                SystemRole.DIVISION_HEAD: "Начальник подразделения",
                SystemRole.DEPARTMENT_HEAD: "Начальник отдела"
            }
            parts.append(system_names.get(self.system_role, ""))

        return " | ".join(parts)

    def __str__(self) -> str:
        return self.get_role_display()