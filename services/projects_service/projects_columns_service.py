# services/projects_service/projects_columns_service.py

from typing import List, Dict, Any, Optional
from sqlalchemy import select
from models.projects import BoardColumn


class ProjectsColumnsService:
    """Работа с колонками проектов"""

    def __init__(self, session):
        self.session = session

    def get_template_columns_for_selector(self) -> List[Dict]:
        """Возвращает шаблонные колонки для диалога выбора с дополнительными полями"""
        try:
            stmt = select(BoardColumn).where(
                BoardColumn.is_template == True
            ).order_by(BoardColumn.template_order)
            columns = self.session.scalars(stmt).all()

            result = []
            for col in columns:
                result.append({
                    'id': col.id,
                    'name': col.name,
                    'col_key': col.name.lower().replace(' ', '_'),
                    'color': col.color,
                    'position': col.template_order or col.position,
                    'is_done_column': col.is_done_column,
                    'is_template': True,
                    'description': getattr(col, 'description', '')
                })
            return result
        except Exception as e:
            print(f"❌ Ошибка при загрузке колонок для селектора: {e}")
            return []

    def filter_columns_by_search(self, columns: List[Dict], search_text: str) -> List[Dict]:
        """Фильтрует колонки по поисковому запросу"""
        if not search_text:
            return columns.copy()

        search_lower = search_text.lower().strip()
        filtered = []
        for col in columns:
            col_name = col.get('name', '').lower()
            col_key = col.get('col_key', '').lower()
            if search_lower in col_name or search_lower in col_key:
                filtered.append(col)
        return filtered

    def get_selected_columns_by_keys(self, all_columns: List[Dict], selected_keys: List[str]) -> List[Dict]:
        """Возвращает данные выбранных колонок по ключам"""
        selected = []
        for col in all_columns:
            col_key = col.get('col_key', col.get('name', '').lower().replace(' ', '_'))
            if col_key in selected_keys:
                col_copy = col.copy()
                if 'col_key' not in col_copy:
                    col_copy['col_key'] = col_key
                selected.append(col_copy)
        return selected

    def load_template_columns(self) -> List[Dict]:
        """Загружает шаблонные колонки из БД"""
        try:
            stmt = select(BoardColumn).where(
                BoardColumn.is_template == True
            ).order_by(BoardColumn.template_order)
            columns = self.session.scalars(stmt).all()

            return [{
                'id': col.id,
                'name': col.name,
                'col_key': col.name.lower().replace(' ', '_'),
                'color': col.color,
                'position': col.template_order or col.position,
                'is_done_column': col.is_done_column,
                'is_template': True
            } for col in columns]
        except Exception as e:
            print(f"❌ Ошибка при загрузке колонок: {e}")
            return []

    def get_project_columns(self, project_id: int, project_repo) -> List[Dict]:
        """Возвращает колонки проекта по сохраненным ID"""
        from sqlalchemy import select
        from models.projects import BoardColumn

        column_ids = project_repo.get_selected_column_ids(project_id)
        result = []

        if column_ids:
            stmt = select(BoardColumn).where(BoardColumn.id.in_(column_ids))
            columns = self.session.scalars(stmt).all()

            for col in columns:
                result.append({
                    'id': col.id,
                    'name': col.name,
                    'color': col.color,
                    'position': col.template_order if col.template_order is not None else col.position,
                    'is_done': col.is_done_column
                })
            print(f"📋 Загружено колонок проекта: {len(result)}")
        else:
            # Если нет сохраненных, берем все шаблонные
            stmt = select(BoardColumn).where(BoardColumn.is_template == True)
            columns = self.session.scalars(stmt).all()
            for col in columns:
                result.append({
                    'id': col.id,
                    'name': col.name,
                    'color': col.color,
                    'position': col.template_order if col.template_order is not None else col.position,
                    'is_done': col.is_done_column
                })

        return result

    def add_column_to_project(self, project_id: int, column_service, template_column_id: int = None, custom_data: Dict = None) -> Optional[Dict[str, Any]]:
        """Добавляет колонку в проект"""
        try:
            column = column_service.create_project_column(
                project_id=project_id,
                template_column_id=template_column_id,
                custom_data=custom_data
            )

            if column:
                self.session.commit()
                print(f"✅ Колонка '{column['name']}' добавлена в проект {project_id}")

            return column
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при добавлении колонки в проект: {e}")
            return None