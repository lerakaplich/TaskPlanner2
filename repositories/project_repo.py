# repositories/project_repo.py

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update, delete

from models.projects import Project, EmployeeProject


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

    def delete(self, project_id: int):
        obj = self.get_by_id(project_id)
        if obj:
            self.session.delete(obj)

    def archive(self, project_id: int, value: bool = True):
        stmt = (
            update(Project)
            .where(Project.id == project_id)
            .values(is_archived=value, updated_at=datetime.now())
        )
        self.session.execute(stmt)

    # =====================================================
    # Выбранные колонки проекта (только ID)
    # =====================================================

    def get_selected_column_ids(self, project_id: int) -> List[int]:
        """Получить список ID выбранных колонок"""
        project = self.get_by_id(project_id)
        if project and project.selected_column_ids:
            try:
                return [int(id_str.strip()) for id_str in project.selected_column_ids.split(',') if id_str.strip()]
            except:
                return []
        return []

    def save_selected_column_ids(self, project_id: int, column_ids: List[int]) -> bool:
        """Сохранить ID колонок через запятую"""
        try:
            ids_str = ','.join(str(id) for id in column_ids)
            stmt = (
                update(Project)
                .where(Project.id == project_id)
                .values(selected_column_ids=ids_str)
            )
            self.session.execute(stmt)
            return True
        except Exception as e:
            print(f"❌ Ошибка при сохранении ID колонок: {e}")
            return False

    # =====================================================
    # Участники проекта
    # =====================================================

    def get_members(self, project_id: int) -> List[EmployeeProject]:
        """Получить всех участников проекта"""
        stmt = select(EmployeeProject).where(EmployeeProject.project_id == project_id)
        return list(self.session.scalars(stmt))

    def get_member(self, project_id: int, employee_id: int) -> Optional[EmployeeProject]:
        """Получить конкретного участника"""
        stmt = select(EmployeeProject).where(
            EmployeeProject.project_id == project_id,
            EmployeeProject.employee_id == employee_id
        )
        return self.session.scalar(stmt)

    def add_member(self, project_id: int, employee_id: int, is_admin: bool = False):
        """Добавить участника в проект"""
        # Проверяем, нет ли уже
        existing = self.get_member(project_id, employee_id)
        if existing:
            return existing

        rel = EmployeeProject(
            project_id=project_id,
            employee_id=employee_id,
            is_admin=is_admin
        )
        self.session.add(rel)
        self.session.flush()
        return rel

    def remove_member(self, project_id: int, employee_id: int):
        """Удалить участника из проекта"""
        stmt = delete(EmployeeProject).where(
            EmployeeProject.project_id == project_id,
            EmployeeProject.employee_id == employee_id
        )
        self.session.execute(stmt)

    def update_member_role(self, project_id: int, employee_id: int, is_admin: bool):
        """Обновить роль участника"""
        stmt = (
            update(EmployeeProject)
            .where(EmployeeProject.project_id == project_id)
            .where(EmployeeProject.employee_id == employee_id)
            .values(is_admin=is_admin)
        )
        self.session.execute(stmt)

    def add_members_batch(self, project_id: int, employee_ids: List[int], is_admin: bool = False):
        """Добавить нескольких участников"""
        for emp_id in employee_ids:
            self.add_member(project_id, emp_id, is_admin)

    def remove_members_batch(self, project_id: int, employee_ids: List[int]):
        """Удалить нескольких участников"""
        if not employee_ids:
            return
        stmt = delete(EmployeeProject).where(
            EmployeeProject.project_id == project_id,
            EmployeeProject.employee_id.in_(employee_ids)
        )
        self.session.execute(stmt)

    # =====================================================
    # Синхронизация участников
    # =====================================================

    def sync_members(self, project_id: int, member_ids: List[int], admin_ids: List[int] = None):
        """
        Синхронизирует участников проекта.
        member_ids - все ID участников
        admin_ids - ID администраторов (подмножество member_ids)
        """
        admin_set = set(admin_ids or [])

        # Получаем текущих участников
        current_members = self.get_members(project_id)
        current_ids = {m.employee_id for m in current_members}

        new_ids = set(member_ids)
        to_add = new_ids - current_ids
        to_remove = current_ids - new_ids

        # Удаляем
        if to_remove:
            self.remove_members_batch(project_id, list(to_remove))

        # Добавляем
        for emp_id in to_add:
            is_admin = emp_id in admin_set
            self.add_member(project_id, emp_id, is_admin)

        # Обновляем роли у существующих
        for emp_id in new_ids & current_ids:
            is_admin = emp_id in admin_set
            current = self.get_member(project_id, emp_id)
            if current and current.is_admin != is_admin:
                self.update_member_role(project_id, emp_id, is_admin)