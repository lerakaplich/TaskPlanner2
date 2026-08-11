# services/employee_service/column_service.py

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from repositories.column_repo import ColumnRepo
from server_app.database import get_tasks_session

from PyQt6.QtCore import QObject, pyqtSignal


class ColumnService(QObject):
    """Сервис для работы с шаблонными колонками"""

    columns_updated = pyqtSignal()

    def __init__(self, session: Session = None):
        super().__init__()
        self.session = session or get_tasks_session()
        self._own_session = session is None
        self.repo = ColumnRepo(self.session)

    def close(self):
        if self._own_session and self.session:
            self.session.close()

    def get_template_columns(self) -> List[Dict[str, Any]]:
        """Возвращает все шаблонные колонки в виде словарей"""
        try:
            columns = self.repo.get_template_columns()
            return [self._column_to_dict(col) for col in columns]
        except Exception as e:
            print(f"❌ Ошибка загрузки шаблонных колонок: {e}")
            return []

    def get_column_by_id(self, column_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает колонку по ID"""
        try:
            column = self.repo.get_by_id(column_id)
            return self._column_to_dict(column) if column else None
        except Exception as e:
            print(f"❌ Ошибка загрузки колонки {column_id}: {e}")
            return None

    def create_template_column(self, column_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создает шаблонную колонку"""
        try:
            column = self.repo.create_template_column(
                name=column_data.get('name'),
                color=column_data.get('color', '#ffffff'),
                is_done_column=column_data.get('is_done_column', False)
            )
            self.session.commit()
            print(f"✅ Колонка '{column.name}' создана, отправляем сигнал обновления")
            self.columns_updated.emit()
            return self._column_to_dict(column)
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании шаблонной колонки: {e}")
            return None

    def update_template_column(self, column_id: int, column_data: Dict[str, Any]) -> bool:
        """Обновляет шаблонную колонку"""
        try:
            success = self.repo.update_template_column(
                column_id=column_id,
                name=column_data.get('name'),
                color=column_data.get('color'),
                is_done_column=column_data.get('is_done_column')
            )
            if success:
                self.session.commit()
                print(f"✅ Колонка {column_id} обновлена, отправляем сигнал обновления")
                self.columns_updated.emit()
            return success
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении шаблонной колонки: {e}")
            return False

    def delete_template_column(self, column_id: int) -> bool:
        """Удаляет шаблонную колонку"""
        try:
            success = self.repo.delete_template_column(column_id)
            if success:
                self.session.commit()
                print(f"✅ Колонка {column_id} удалена, отправляем сигнал обновления")
                self.columns_updated.emit()
            return success
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при удалении шаблонной колонки: {e}")
            return False

    def hard_delete_template_column(self, column_id: int) -> bool:
        """Полное удаление шаблонной колонки (алиас)"""
        return self.delete_template_column(column_id)

    def _column_to_dict(self, column) -> Dict[str, Any]:
        """Преобразует модель колонки в словарь"""
        if column is None:
            return {}
        return {
            'id': column.id,
            'name': column.name,
            'color': column.color,
            'position': getattr(column, 'template_order', column.position) if hasattr(column,
                                                                                      'template_order') else column.position,
            'is_done_column': column.is_done_column,
            'project_id': column.project_id,
            'is_template': getattr(column, 'is_template', False),
            'template_order': getattr(column, 'template_order', 0)
        }