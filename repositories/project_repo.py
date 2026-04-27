# repositories/project_repo.py

import json  # 👈 ДОБАВИТЬ
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update, delete

from models.projects import Project, BoardColumn, EmployeeProject


class ProjectRepo:

    def __init__(self, session: Session):
        self.session = session

    def get_selected_column_ids(self, project_id: int) -> List[int]:
        """Получить список ID выбранных колонок"""
        project = self.get_by_id(project_id)
        if project and project.selected_column_ids:
            try:
                # Парсим строку "1,2,3" в список [1,2,3]
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

    def get_by_id(self, project_id: int) -> Optional[Project]:
        return self.session.get(Project, project_id)

    def get_all(self, exclude_archived: bool = False) -> List[Project]:
        from sqlalchemy.orm import joinedload

        stmt = select(Project).options(
            joinedload(Project.members)
        )

        if exclude_archived:
            stmt = stmt.where(Project.is_archived == False)

        return list(self.session.scalars(stmt).unique())

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

    def get_selected_columns(self, project_id: int) -> List[Dict[str, Any]]:
        """Получить сохраненные колонки проекта из поля selected_column_ids"""
        column_ids = self.get_selected_column_ids(project_id)
        if not column_ids:
            return []

        try:
            from models.projects import BoardColumn
            from sqlalchemy import select

            stmt = select(BoardColumn).where(BoardColumn.id.in_(column_ids))
            columns = self.session.scalars(stmt).all()

            result = []
            for col in columns:
                result.append({
                    'id': col.id,
                    'name': col.name,
                    'col_key': col.name.lower().replace(' ', '_'),
                    'color': col.color,
                    'position': col.position,
                    'is_done_column': col.is_done_column
                })
            return result
        except Exception as e:
            print(f"❌ Ошибка при загрузке колонок: {e}")
            return []

    def save_selected_columns(self, project_id: int, columns_data: List[Dict[str, Any]]) -> bool:
        """Сохранить выбранные колонки - для совместимости, но лучше использовать save_selected_column_ids"""
        # Извлекаем ID колонок из данных
        column_ids = [col.get('id') for col in columns_data if col.get('id')]
        if column_ids:
            return self.save_selected_column_ids(project_id, column_ids)
        return False

    def add_column(self, project_id: int, name: str, position: int, color: str = "#ccab6e",
                   is_done_column: bool = False) -> BoardColumn:
        column = BoardColumn(
            project_id=project_id,
            name=name,
            position=position,
            color=color,
            is_done_column=is_done_column,
            created_at=datetime.now()
        )
        self.session.add(column)
        self.session.flush()
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

    def get_project_columns_count(self, project_id: int) -> int:
        """Получить количество колонок в проекте"""
        try:
            stmt = select(BoardColumn).where(BoardColumn.project_id == project_id)
            result = self.session.scalars(stmt).all()
            return len(result)
        except Exception as e:
            print(f"❌ Ошибка при подсчете колонок: {e}")
            return 0

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
        stmt = (
            update(EmployeeProject)
            .where(EmployeeProject.project_id == project_id)
            .where(EmployeeProject.employee_id == employee_id)
            .values(is_admin=is_admin)
        )
        self.session.execute(stmt)