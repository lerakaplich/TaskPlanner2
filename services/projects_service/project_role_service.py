# services/projects_service/project_role_service.py

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from models.projects import EmployeeProject, ProjectRoleEnum
from services.permissions.project_permissions import ProjectRole


class ProjectRoleService:
    """Сервис для определения ролей пользователей в проектах"""

    def __init__(self, session: Session):
        self.session = session

    def get_project_role(self, user_id: int, project_id: int) -> Optional[ProjectRole]:
        """
        Определяет роль пользователя в проекте.
        Возвращает None, если пользователь не является участником проекта.
        """
        stmt = select(EmployeeProject).where(
            EmployeeProject.employee_id == user_id,
            EmployeeProject.project_id == project_id
        )
        membership = self.session.scalar(stmt)

        if not membership:
            return None

        # Если есть роль, используем её
        if membership.role:
            # Конвертируем ProjectRoleEnum в ProjectRole
            if membership.role == ProjectRoleEnum.PROJECT_MANAGER:
                return ProjectRole.PROJECT_MANAGER
            elif membership.role == ProjectRoleEnum.CURATOR:
                return ProjectRole.CURATOR

        # Для обратной совместимости: если is_admin=True, то PROJECT_MANAGER
        if membership.is_admin:
            return ProjectRole.PROJECT_MANAGER

        return ProjectRole.MEMBER

    def is_project_member(self, user_id: int, project_id: int) -> bool:
        """Проверяет, является ли пользователь участником проекта"""
        return self.get_project_role(user_id, project_id) is not None

    def is_project_manager(self, user_id: int, project_id: int) -> bool:
        """Проверяет, является ли пользователь руководителем проекта"""
        role = self.get_project_role(user_id, project_id)
        return role == ProjectRole.PROJECT_MANAGER

    def is_curator(self, user_id: int, project_id: int) -> bool:
        """Проверяет, является ли пользователь куратором проекта"""
        role = self.get_project_role(user_id, project_id)
        return role == ProjectRole.CURATOR

    def can_manage_project(self, user_id: int, project_id: int) -> bool:
        """Проверяет, может ли пользователь управлять проектом"""
        role = self.get_project_role(user_id, project_id)
        return role in (ProjectRole.PROJECT_MANAGER, ProjectRole.CURATOR)

    def get_user_projects(self, user_id: int) -> list[int]:
        """Возвращает список ID проектов, в которых участвует пользователь"""
        stmt = select(EmployeeProject.project_id).where(
            EmployeeProject.employee_id == user_id
        )
        return list(self.session.scalars(stmt).all())

    def get_project_members(self, project_id: int) -> list[dict]:
        """Возвращает список участников проекта с их ролями"""
        stmt = select(EmployeeProject).where(
            EmployeeProject.project_id == project_id
        )
        memberships = self.session.scalars(stmt).all()

        result = []
        for membership in memberships:
            result.append({
                "employee_id": membership.employee_id,
                "role": membership.role.value if membership.role else "member",
                "is_admin": membership.is_admin,
                "joined_at": membership.joined_at
            })
        return result