# services/projects_service/project_role_service.py

from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import select, text

from models.projects import EmployeeProject, ProjectRoleEnum
from services.permissions.project_permissions import ProjectRole, ProjectPermissionManager


class ProjectRoleService:
    """Сервис для определения ролей пользователей в проектах"""

    def __init__(self, session: Session):
        self.session = session
        self._cache = {}

    def get_project_role(self, user_id: int, project_id: int) -> Optional[ProjectRole]:
        """
        Определяет роль пользователя в проекте.
        Возвращает ProjectRole или None, если пользователь не участник.
        """
        cache_key = (user_id, project_id)
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # 1. Проверяем, является ли пользователь куратором
            stmt = text("""
                SELECT manager_id FROM public.projects WHERE id = :project_id
            """)
            result = self.session.execute(stmt, {'project_id': project_id}).first()

            if result and result[0] == user_id:
                self._cache[cache_key] = ProjectRole.CURATOR
                return ProjectRole.CURATOR

            # 2. Проверяем роль из таблицы employees_projects
            stmt = text("""
                SELECT role FROM public.employees_projects 
                WHERE project_id = :project_id AND employee_id = :user_id
            """)
            result = self.session.execute(stmt, {
                'project_id': project_id,
                'user_id': user_id
            }).first()

            if result:
                role_str = result[0]
                if role_str == 'project_manager':
                    self._cache[cache_key] = ProjectRole.PROJECT_MANAGER
                    return ProjectRole.PROJECT_MANAGER
                elif role_str == 'curator':
                    self._cache[cache_key] = ProjectRole.CURATOR
                    return ProjectRole.CURATOR
                else:
                    self._cache[cache_key] = ProjectRole.MEMBER
                    return ProjectRole.MEMBER

            # 3. Проверяем, является ли пользователь владельцем проекта
            stmt = text("""
                SELECT created_by FROM public.projects WHERE id = :project_id
            """)
            result = self.session.execute(stmt, {'project_id': project_id}).first()

            if result and result[0] == user_id:
                self._cache[cache_key] = ProjectRole.PROJECT_MANAGER
                return ProjectRole.PROJECT_MANAGER

            result = self.session.execute(stmt, {
                'project_id': project_id,
                'user_id': user_id
            }).first()

            if result and result[0]:
                self._cache[cache_key] = ProjectRole.PROJECT_MANAGER
                return ProjectRole.PROJECT_MANAGER

            return None

        except Exception as e:
            print(f"⚠️ Ошибка получения роли в проекте: {e}")
            return None

    def get_project_permission_manager(self, user_id: int, project_id: int) -> Optional[ProjectPermissionManager]:
        """Возвращает менеджер прав для проекта"""
        role = self.get_project_role(user_id, project_id)
        if role is None:
            return None
        return ProjectPermissionManager(user_id, project_id, role)

    def is_project_member(self, user_id: int, project_id: int) -> bool:
        """Проверяет, является ли пользователь участником проекта"""
        return self.get_project_role(user_id, project_id) is not None

    def get_user_projects_with_roles(self, user_id: int) -> List[Dict]:
        """Возвращает список проектов пользователя с их ролями"""
        try:
            stmt = text("""
                SELECT 
                    p.id,
                    p.name,
                    p.is_archived,
                    COALESCE(ep.role, 'member') as role,
                    p.created_by,
                    p.manager_id
                FROM public.projects p
                LEFT JOIN public.employees_projects ep 
                    ON ep.project_id = p.id AND ep.employee_id = :user_id
                WHERE p.is_archived = false
                AND (
                    ep.employee_id IS NOT NULL 
                    OR p.manager_id = :user_id 
                    OR p.created_by = :user_id
                )
            """)

            result = self.session.execute(stmt, {'user_id': user_id}).all()

            projects = []
            for row in result:
                # Определяем реальную роль
                if row[1] == user_id:  # manager_id
                    role = 'curator'
                elif row[2] == 'project_manager':  # role из ep
                    role = 'project_manager'
                elif row[3] == user_id:  # created_by
                    role = 'project_manager'
                else:
                    role = 'member'

                projects.append({
                    'id': row[0],
                    'name': row[1],
                    'is_archived': row[2],
                    'role': role
                })

            return projects

        except Exception as e:
            print(f"⚠️ Ошибка получения проектов пользователя: {e}")
            return []

    def clear_cache(self):
        """Очищает кэш ролей"""
        self._cache.clear()