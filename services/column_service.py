# services/column_service.py

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from models.projects import BoardColumn


class ColumnService:
    """Сервис для работы с колонками (шаблоны и проектные)"""

    def __init__(self, session: Session):
        self.session = session

    # ==================== ШАБЛОНЫ КОЛОНОК ====================

    def get_template_columns(self) -> List[Dict[str, Any]]:
        """Получить все шаблонные колонки"""
        print("🔍 ColumnService.get_template_columns() вызван")

        stmt = select(BoardColumn).where(
            BoardColumn.is_template == True
        ).order_by(BoardColumn.template_order, BoardColumn.position)

        columns = self.session.scalars(stmt).all()
        print(f"📊 Найдено шаблонных колонок: {len(columns)}")

        for col in columns:
            print(f"   - {col.name} (id={col.id}, is_template={col.is_template})")

        return [self._column_to_dict(col) for col in columns]

    def create_template_column(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создать шаблонную колонку"""
        try:
            # Получаем максимальный template_order
            max_order = self.session.query(BoardColumn.template_order).filter(
                BoardColumn.is_template == True
            ).order_by(BoardColumn.template_order.desc()).first()

            next_order = (max_order[0] + 1) if max_order and max_order[0] else 1

            # Получаем максимальную позицию
            max_position = self.session.query(BoardColumn.position).filter(
                BoardColumn.is_template == True
            ).order_by(BoardColumn.position.desc()).first()

            next_position = (max_position[0] + 1) if max_position and max_position[0] else 0

            new_column = BoardColumn(
                name=data.get('name'),
                color=data.get('color', '#ccab6e'),
                position=next_position,
                is_done_column=data.get('is_done_column', False),
                is_template=True,
                template_order=next_order,
                project_id=None
            )

            self.session.add(new_column)
            self.session.commit()
            self.session.refresh(new_column)

            return self._column_to_dict(new_column)

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании шаблонной колонки: {e}")
            return None

    def update_template_column(self, column_id: int, data: Dict[str, Any]) -> bool:
        """Обновить шаблонную колонку"""
        try:
            column = self.session.get(BoardColumn, column_id)
            if not column or not column.is_template:
                return False

            if 'name' in data:
                column.name = data['name']
            if 'color' in data:
                column.color = data['color']
            if 'is_done_column' in data:
                column.is_done_column = data['is_done_column']

            self.session.commit()
            return True

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении шаблонной колонки: {e}")
            return False

    def delete_template_column(self, column_id: int) -> bool:
        """Удалить шаблонную колонку"""
        try:
            column = self.session.get(BoardColumn, column_id)
            if column and column.is_template:
                print(f"🗑️ Удаляем шаблонную колонку: ID={column.id}, name={column.name}")
                self.session.delete(column)
                self.session.commit()
                print(f"✅ Шаблонная колонка {column_id} удалена")
                return True
            else:
                print(f"⚠️ Колонка {column_id} не найдена или не является шаблоном")
                return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при удалении шаблонной колонки: {e}")
            import traceback
            traceback.print_exc()
            return False

    def reorder_template_columns(self, column_ids: List[int]):
        """Изменить порядок шаблонных колонок"""
        try:
            for order, col_id in enumerate(column_ids):
                stmt = update(BoardColumn).where(
                    BoardColumn.id == col_id
                ).values(template_order=order)
                self.session.execute(stmt)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при сортировке колонок: {e}")

    def get_project_columns(self, project_id: int) -> List[Dict[str, Any]]:
        """Получить колонки для конкретного проекта"""
        stmt = select(BoardColumn).where(
            BoardColumn.project_id == project_id,
            BoardColumn.is_template == False  # Только проектные колонки, не шаблоны
        ).order_by(BoardColumn.position)

        columns = self.session.scalars(stmt).all()
        return [self._column_to_dict(col) for col in columns]

    def create_project_column(self, project_id: int, template_column_id: int = None, custom_data: Dict = None) -> \
    Optional[Dict[str, Any]]:
        """Создать колонку для проекта (на основе шаблона или с нуля)"""
        try:
            from datetime import datetime

            # Получаем максимальную позицию в проекте
            max_position = self.session.query(BoardColumn.position).filter(
                BoardColumn.project_id == project_id
            ).order_by(BoardColumn.position.desc()).first()
            next_position = (max_position[0] + 1) if max_position and max_position[0] else 0

            # Если указан template_column_id, копируем из шаблона
            if template_column_id:
                template = self.session.get(BoardColumn, template_column_id)
                if template and template.is_template:
                    new_column = BoardColumn(
                        project_id=project_id,
                        name=template.name,
                        color=template.color,
                        position=next_position,
                        is_done_column=template.is_done_column,
                        is_template=False,
                        created_at=datetime.now()  # ← ДОБАВИТЬ
                    )

                    self.session.add(new_column)
                    self.session.flush()  # ← flush чтобы получить ID
                    self.session.refresh(new_column)

                    print(
                        f"  📝 Создана колонка из шаблона: ID={new_column.id}, name={new_column.name}, position={new_column.position}")

                    return self._column_to_dict(new_column)

            # Создаём с нуля
            elif custom_data:
                new_column = BoardColumn(
                    project_id=project_id,
                    name=custom_data.get('name'),
                    color=custom_data.get('color', '#ccab6e'),
                    position=custom_data.get('position', next_position),
                    # ← используем переданную позицию или next_position
                    is_done_column=custom_data.get('is_done_column', False),
                    is_template=False,
                    created_at=datetime.now()  # ← ДОБАВИТЬ
                )

                self.session.add(new_column)
                self.session.flush()  # ← flush чтобы получить ID
                self.session.refresh(new_column)

                print(
                    f"  📝 Создана колонка с нуля: ID={new_column.id}, name={new_column.name}, position={new_column.position}")

                return self._column_to_dict(new_column)

            return None

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании проектной колонки: {e}")
            import traceback
            traceback.print_exc()
            return None

    def initialize_project_columns(self, project_id: int) -> List[Dict[str, Any]]:
        """Инициализировать проект стандартными колонками из шаблонов"""
        templates = self.get_template_columns()
        created_columns = []

        for template in templates:
            column = self.create_project_column(project_id, template_column_id=template['id'])
            if column:
                created_columns.append(column)

        return created_columns

    def update_project_column(self, column_id: int, data: Dict[str, Any]) -> bool:
        """Обновить проектную колонку"""
        try:
            column = self.session.get(BoardColumn, column_id)
            if not column or column.is_template:
                return False

            if 'name' in data:
                column.name = data['name']
            if 'color' in data:
                column.color = data['color']
            if 'is_done_column' in data:
                column.is_done_column = data['is_done_column']

            self.session.commit()
            return True

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении проектной колонки: {e}")
            return False

    def delete_project_column(self, column_id: int) -> bool:
        """Удалить проектную колонку (только если нет задач)"""
        try:
            column = self.session.get(BoardColumn, column_id)
            if column and not column.is_template:
                # Проверяем, есть ли задачи в колонке
                if column.tasks and len(column.tasks) > 0:
                    print(f"⚠️ Нельзя удалить колонку {column_id}: в ней есть задачи")
                    return False

                self.session.delete(column)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при удалении проектной колонки: {e}")
            return False

    def create_project_columns_batch(self, project_id: int, columns_data: List[Dict[str, Any]]) -> List[
        Dict[str, Any]]:
        """
        Создать несколько колонок для проекта за один раз.

        Args:
            project_id: ID проекта
            columns_data: Список словарей с данными колонок:
                [
                    {'name': 'Название проекта', 'color': '#1B232A', 'position': 0, 'is_done_column': False},
                    {'name': 'Статус', 'color': '#ccab6e', 'position': 1, 'is_done_column': False},
                    ...
                ]

        Returns:
            Список созданных колонок в виде словарей
        """
        from datetime import datetime

        created_columns = []

        try:
            for col_data in columns_data:
                new_column = BoardColumn(
                    project_id=project_id,
                    name=col_data.get('name'),
                    color=col_data.get('color', '#ccab6e'),
                    position=col_data.get('position', len(created_columns)),
                    is_done_column=col_data.get('is_done_column', False),
                    is_template=False,
                    created_at=datetime.now()
                )

                self.session.add(new_column)
                self.session.flush()  # получаем ID

                created_columns.append({
                    'id': new_column.id,
                    'name': new_column.name,
                    'color': new_column.color,
                    'position': new_column.position,
                    'is_done_column': new_column.is_done_column
                })

                print(f"  ✅ Создана колонка: {new_column.name} (ID: {new_column.id})")

            self.session.commit()
            return created_columns

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при массовом создании колонок: {e}")
            return []

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def _column_to_dict(self, column: BoardColumn) -> Dict[str, Any]:
        """Преобразует модель колонки в словарь"""
        return {
            'id': column.id,
            'project_id': column.project_id,
            'name': column.name,
            'color': column.color,
            'position': column.position,
            'is_done_column': column.is_done_column,
            'is_template': column.is_template,
            'created_at': column.created_at.isoformat() if column.created_at else None,
        }