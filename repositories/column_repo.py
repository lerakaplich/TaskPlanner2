# repositories/column_repo.py

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, func
from datetime import datetime

from models.projects import BoardColumn


class ColumnRepo:
    """Репозиторий для работы с колонками (шаблонными и проектными)"""

    def __init__(self, session: Session):
        self.session = session

    # =========================
    # Получение колонок
    # =========================

    def get_by_id(self, column_id: int) -> Optional[BoardColumn]:
        return self.session.get(BoardColumn, column_id)

    def get_template_columns(self) -> List[BoardColumn]:
        """Получить все колонки"""
        stmt = select(BoardColumn).order_by(BoardColumn.position)
        return list(self.session.scalars(stmt))

    def get_project_columns(self, project_id: int) -> List[BoardColumn]:
        """Получить колонки конкретного проекта"""
        stmt = select(BoardColumn).where(
            BoardColumn.project_id == project_id
        ).order_by(BoardColumn.position)
        return list(self.session.scalars(stmt))

    def get_columns_by_ids(self, column_ids: List[int]) -> List[BoardColumn]:
        """Получить колонки по списку ID"""
        if not column_ids:
            return []
        stmt = select(BoardColumn).where(BoardColumn.id.in_(column_ids))
        return list(self.session.scalars(stmt))

    # =========================
    # Создание колонок
    # =========================

    def create_template_column(self, name: str, color: str = "#ffffff",
                                is_done_column: bool = False) -> BoardColumn:
        """Создать шаблонную колонку"""
        # Находим максимальный template_order
        max_order = self.session.scalar(
            select(func.max(BoardColumn.template_order))
            .where(BoardColumn.project_id == None)
        )
        next_order = (max_order + 1) if max_order else 0

        column = BoardColumn(
            name=name,
            color=color,
            is_done_column=is_done_column,
            template_order=next_order,
            is_template=True,
            project_id=None,
            position=0
        )
        self.session.add(column)
        self.session.flush()
        return column

    def create_project_column(self, project_id: int, name: str, color: str = "#ffffff",
                              position: int = 0, is_done_column: bool = False) -> BoardColumn:
        """Создать колонку проекта (project_id обязателен)"""
        column = BoardColumn(
            name=name,
            color=color,
            position=position,
            is_done_column=is_done_column,
            project_id=project_id,  # обязательный
            is_template=False,
            template_order=None
        )
        self.session.add(column)
        self.session.flush()
        return column

    def copy_from_template(self, template_column: BoardColumn, project_id: int) -> BoardColumn:
        """Создать колонку проекта на основе шаблонной"""
        column = BoardColumn(
            name=template_column.name,
            color=template_column.color,
            position=template_column.template_order or template_column.position,
            is_done_column=template_column.is_done_column,
            project_id=project_id,
            is_template=False,
            template_order=template_column.template_order,
            created_at=datetime.now()
        )
        self.session.add(column)
        self.session.flush()
        return column

    # =========================
    # Обновление колонок
    # =========================

    def update_template_column(self, column_id: int, name: str = None,
                                color: str = None, is_done_column: bool = None) -> bool:
        """Обновить шаблонную колонку"""
        column = self.get_by_id(column_id)
        if not column or column.project_id is not None:
            return False

        if name is not None:
            column.name = name
        if color is not None:
            column.color = color
        if is_done_column is not None:
            column.is_done_column = is_done_column

        return True

    def update_project_column(self, column_id: int, name: str = None,
                               color: str = None, position: int = None,
                               is_done_column: bool = None) -> bool:
        """Обновить колонку проекта"""
        column = self.get_by_id(column_id)
        if not column:
            return False

        if name is not None:
            column.name = name
        if color is not None:
            column.color = color
        if position is not None:
            column.position = position
        if is_done_column is not None:
            column.is_done_column = is_done_column

        return True

    # =========================
    # Удаление колонок
    # =========================

    def delete_template_column(self, column_id: int) -> bool:
        """Удалить шаблонную колонку"""
        column = self.get_by_id(column_id)
        if column and column.project_id is None:
            self.session.delete(column)
            return True
        return False

    def delete_project_column(self, column_id: int) -> bool:
        """Удалить колонку проекта (задачи перейдут в NULL)"""
        column = self.get_by_id(column_id)
        if column and column.project_id is not None:
            self.session.delete(column)
            return True
        return False

    # =========================
    # Сортировка колонок
    # =========================

    def reorder_project_columns(self, project_id: int, column_ids: List[int]) -> bool:
        """Переупорядочить колонки проекта"""
        try:
            for position, column_id in enumerate(column_ids):
                stmt = update(BoardColumn).where(
                    BoardColumn.id == column_id,
                    BoardColumn.project_id == project_id
                ).values(position=position)
                self.session.execute(stmt)
            return True
        except Exception as e:
            print(f"❌ Ошибка переупорядочивания колонок: {e}")
            return False

    # =========================
    # Вспомогательные
    # =========================

    def get_done_column_ids(self, project_id: int) -> List[int]:
        """Получить ID колонок, которые считаются выполненными"""
        columns = self.get_project_columns(project_id)
        return [col.id for col in columns if col.is_done_column]

    def get_template_columns_count(self) -> int:
        """Количество шаблонных колонок"""
        return len(self.get_template_columns())

    # =========================
    # Проектные колонки
    # =========================

    def add_column_to_project(self, project_id: int, name: str, position: int,
                              color: str = "#ccab6e", is_done_column: bool = False) -> BoardColumn:
        """Создать колонку в проекте"""
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

    def update_column_position(self, column_id: int, new_position: int) -> bool:
        """Обновить позицию колонки"""
        column = self.get_by_id(column_id)
        if column:
            column.position = new_position
            return True
        return False

    def get_project_columns_count(self, project_id: int) -> int:
        """Получить количество колонок в проекте"""
        return len(self.get_project_columns(project_id))