from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete

from models.projects import Project, BoardColumn, EmployeeProject


class ProjectRepo:

    def __init__(self, session: Session):
        self.session = session

    # =========================
    # Projects CRUD
    # =========================
    def get_by_id(self, project_id: int) -> Optional[Project]:
        return self.session.get(Project, project_id)

    def get_all(self) -> List[Project]:
        return list(self.session.scalars(select(Project)))

    def create(self, **kwargs) -> Project:
        project = Project(**kwargs)
        self.session.add(project)
        return project

    def delete(self, project_id: int):
        obj = self.get_by_id(project_id)
        if obj:
            self.session.delete(obj)

    def archive(self, project_id: int, value: bool = True):
        stmt = (
            update(Project)
            .where(Project.id == project_id)
            .values(is_archived=value)
        )
        self.session.execute(stmt)

    # =========================
    # Columns
    # =========================
    def add_column(self, project_id: int, name: str, position: int) -> BoardColumn:
        column = BoardColumn(
            project_id=project_id,
            name=name,
            position=position
        )
        self.session.add(column)
        return column

    def delete_column(self, column_id: int):
        obj = self.session.get(BoardColumn, column_id)
        if obj:
            self.session.delete(obj)

    def update_column_position(self, column_id: int, new_position: int):
        stmt = (
            update(BoardColumn)
            .where(BoardColumn.id == column_id)
            .values(position=new_position)
        )
        self.session.execute(stmt)

    # =========================
    # Members
    # =========================
    def add_member(self, project_id: int, employee_id: int, is_admin=False):
        rel = EmployeeProject(
            project_id=project_id,
            employee_id=employee_id,
            is_admin=is_admin
        )
        self.session.add(rel)

    def remove_member(self, project_id: int, employee_id: int):
        stmt = delete(EmployeeProject).where(
            EmployeeProject.project_id == project_id,
            EmployeeProject.employee_id == employee_id
        )
        self.session.execute(stmt)

    def update_member_role(self, project_id: int, employee_id: int, is_admin: bool):
        """Обновляет только роль участника в проекте"""
        stmt = (
            update(EmployeeProject)
            .where(EmployeeProject.project_id == project_id)
            .where(EmployeeProject.employee_id == employee_id)
            .values(is_admin=is_admin)
        )
        self.session.execute(stmt)