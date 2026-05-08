# services/column_service.py

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from models.projects import BoardColumn
from database import get_tasks_session


class ColumnService:
    """Сервис для работы с шаблонными колонками"""

    def __init__(self, session: Session = None):
        self.session = session or get_tasks_session()
        self._own_session = session is None

    def close(self):
        if self._own_session and self.session:
            self.session.close()

    def get_template_columns(self) -> List[Dict[str, Any]]:
        """Возвращает все шаблонные колонки"""
        try:
            columns = self.session.query(BoardColumn).filter(
                BoardColumn.project_id == None,
                BoardColumn.is_template == True
            ).order_by(BoardColumn.template_order).all()
            return [self._column_to_dict(col) for col in columns]
        except Exception as e:
            print(f"❌ Ошибка загрузки шаблонных колонок: {e}")
            return []

    def get_column_by_id(self, column_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает колонку по ID"""
        try:
            column = self.session.get(BoardColumn, column_id)
            return self._column_to_dict(column) if column else None
        except Exception as e:
            print(f"❌ Ошибка загрузки колонки {column_id}: {e}")
            return None

    def create_template_column(self, column_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создает шаблонную колонку"""
        try:
            max_order = self.session.query(BoardColumn).filter(
                BoardColumn.project_id == None
            ).order_by(BoardColumn.template_order.desc()).first()
            next_order = (max_order.template_order + 1) if max_order and max_order.template_order else 0

            column = BoardColumn(
                name=column_data.get('name'),
                color=column_data.get('color', '#ffffff'),
                is_done_column=column_data.get('is_done_column', False),
                template_order=next_order,
                is_template=True,
                project_id=None
            )
            self.session.add(column)
            self.session.commit()
            self.session.refresh(column)

            return self._column_to_dict(column)
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании шаблонной колонки: {e}")
            return None

    def update_template_column(self, column_id: int, column_data: Dict[str, Any]) -> bool:
        """Обновляет шаблонную колонку"""
        try:
            column = self.session.get(BoardColumn, column_id)
            if not column or column.project_id is not None:
                return False

            if 'name' in column_data and column_data['name']:
                column.name = column_data['name']
            if 'color' in column_data and column_data['color']:
                column.color = column_data['color']
            if 'is_done_column' in column_data:
                column.is_done_column = column_data['is_done_column']

            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении шаблонной колонки: {e}")
            return False

    def delete_template_column(self, column_id: int) -> bool:
        """Удаляет шаблонную колонку"""
        try:
            column = self.session.get(BoardColumn, column_id)
            if column and column.project_id is None:
                self.session.delete(column)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при удалении шаблонной колонки: {e}")
            return False

    def hard_delete_template_column(self, column_id: int) -> bool:
        """Полное удаление шаблонной колонки"""
        return self.delete_template_column(column_id)

    def _column_to_dict(self, column: BoardColumn) -> Dict[str, Any]:
        """Преобразует модель колонки в словарь"""
        if column is None:
            return {}
        return {
            'id': column.id,
            'name': column.name,
            'color': column.color,
            'position': column.template_order if column.template_order is not None else column.position,
            'is_done_column': column.is_done_column,
            'project_id': column.project_id,
            'is_template': column.is_template,
            'template_order': column.template_order,
            'created_at': column.created_at.isoformat() if column.created_at else None,
        }