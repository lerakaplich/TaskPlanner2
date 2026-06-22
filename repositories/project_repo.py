# repositories/project_repo.py - исправленный

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update, delete

from models.projects import Project, EmployeeProject, ProjectRoleEnum


class ProjectRepo:
    """Репозиторий для работы с проектами и участниками"""

    def __init__(self, session: Session):
        self.session = session

    # =====================================================
    # Проекты
    # =====================================================

    def get_by_id(self, project_id: int) -> Optional[Project]:
        return self.session.get(Project, project_id)

    def get_all(self, exclude_archived: bool = False) -> List[Project]:
        stmt = select(Project).options(joinedload(Project.members))
        if exclude_archived:
            stmt = stmt.where(Project.is_archived == False)
        return list(self.session.scalars(stmt).unique())

    def create(self, **kwargs) -> Project:
        project = Project(**kwargs)
        self.session.add(project)
        self.session.flush()
        return project

    def update(self, project_id: int, **kwargs) -> Optional[Project]:
        project = self.get_by_id(project_id)
        if project:
            for key, value in kwargs.items():
                if hasattr(project, key):
                    setattr(project, key, value)
            self.session.flush()
        return project

    def archive(self, project_id: int, value: bool = True):
        stmt = (
            update(Project)
            .where(Project.id == project_id)
            .values(is_archived=value, updated_at=datetime.now())
        )
        self.session.execute(stmt)
        self.session.flush()

    # =====================================================
    # Выбранные колонки
    # =====================================================

    def get_selected_column_ids(self, project_id: int) -> List[int]:
        project = self.get_by_id(project_id)
        if project and project.selected_column_ids:
            try:
                return [int(id_str.strip()) for id_str in project.selected_column_ids.split(',') if id_str.strip()]
            except:
                return []
        return []

    def save_selected_column_ids(self, project_id: int, column_ids: List[int]) -> bool:
        try:
            ids_str = ','.join(str(id) for id in column_ids)
            stmt = (
                update(Project)
                .where(Project.id == project_id)
                .values(selected_column_ids=ids_str)
            )
            self.session.execute(stmt)
            return True
        except Exception:
            return False

    # =====================================================
    # Участники проекта (исправлено на role)
    # =====================================================

    def get_members(self, project_id: int) -> List[EmployeeProject]:
        stmt = select(EmployeeProject).where(EmployeeProject.project_id == project_id)
        return list(self.session.scalars(stmt))

    def get_member(self, project_id: int, employee_id: int) -> Optional[EmployeeProject]:
        stmt = select(EmployeeProject).where(
            EmployeeProject.project_id == project_id,
            EmployeeProject.employee_id == employee_id
        )
        return self.session.scalar(stmt)

    def add_member(
        self,
        project_id: int,
        employee_id: int,
        role: ProjectRoleEnum = ProjectRoleEnum.MEMBER
    ) -> EmployeeProject:
        """Добавить участника в проект"""
        existing = self.get_member(project_id, employee_id)
        if existing:
            return existing

        rel = EmployeeProject(
            project_id=project_id,
            employee_id=employee_id,
            role=role
        )
        self.session.add(rel)
        self.session.flush()
        return rel

    def remove_member(self, project_id: int, employee_id: int):
        stmt = delete(EmployeeProject).where(
            EmployeeProject.project_id == project_id,
            EmployeeProject.employee_id == employee_id
        )
        self.session.execute(stmt)

    def update_member_role(self, project_id: int, employee_id: int, role: ProjectRoleEnum):
        stmt = (
            update(EmployeeProject)
            .where(EmployeeProject.project_id == project_id)
            .where(EmployeeProject.employee_id == employee_id)
            .values(role=role)
        )
        self.session.execute(stmt)

    def add_members_batch(self, project_id: int, employee_ids: List[int], role: ProjectRoleEnum = ProjectRoleEnum.MEMBER):
        for emp_id in employee_ids:
            self.add_member(project_id, emp_id, role)

    def remove_members_batch(self, project_id: int, employee_ids: List[int]):
        if not employee_ids:
            return
        stmt = delete(EmployeeProject).where(
            EmployeeProject.project_id == project_id,
            EmployeeProject.employee_id.in_(employee_ids)
        )
        self.session.execute(stmt)

    # =====================================================
    # Синхронизация участников (исправлено)
    # =====================================================

    def sync_members(self, project_id: int, members_with_roles: Dict[int, ProjectRoleEnum]):
        """
        Синхронизирует участников проекта.
        members_with_roles: {employee_id: role}
        """
        # Получаем текущих участников
        current_members = self.get_members(project_id)
        current_dict = {m.employee_id: m for m in current_members}

        new_dict = members_with_roles.copy()

        # Определяем, что нужно добавить/удалить
        current_ids = set(current_dict.keys())
        new_ids = set(new_dict.keys())

        to_add = new_ids - current_ids
        to_remove = current_ids - new_ids
        to_update = new_ids & current_ids

        # Удаляем
        if to_remove:
            self.remove_members_batch(project_id, list(to_remove))

        # Добавляем
        for emp_id in to_add:
            self.add_member(project_id, emp_id, new_dict[emp_id])

        # Обновляем роли
        for emp_id in to_update:
            current = current_dict[emp_id]
            new_role = new_dict[emp_id]
            if current.role != new_role:
                self.update_member_role(project_id, emp_id, new_role)