# services/gantt_service/gantt_filter_service.py

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from .gantt_base_service import TaskGanttData


class GanttFilterService:
    """Сервис для фильтрации задач"""

    def __init__(self, data_service):
        self._data = data_service

    def get_filtered_tasks(self, project_filter: str, executor_filter: str) -> List[TaskGanttData]:
        """Возвращает задачи с применением фильтров"""
        all_tasks = self._data.get_all_tasks()
        print(f"🔍 get_filtered_tasks: всего задач {len(all_tasks)}")
        print(f"   Фильтр проекта: '{project_filter}'")
        print(f"   Фильтр исполнителя: '{executor_filter}'")

        # Фильтр по проекту
        if project_filter != "all":
            try:
                # Пытаемся извлечь ID проекта из строки вида "project_123"
                if isinstance(project_filter, str) and project_filter.startswith("project_"):
                    project_id = int(project_filter.split("_")[1])
                else:
                    project_id = int(project_filter)

                filtered = [t for t in all_tasks if t.project_id == project_id]
                print(f"   После фильтра по проекту {project_id}: {len(filtered)} задач")
            except (ValueError, IndexError) as e:
                print(f"   Ошибка парсинга project_filter '{project_filter}': {e}")
                filtered = all_tasks.copy()
        else:
            filtered = all_tasks.copy()
            print(f"   Все проекты: {len(filtered)} задач")

        # Фильтр по исполнителю
        if executor_filter != "all":
            filtered = [t for t in filtered if t.executor_name == executor_filter]
            print(f"   После фильтра по исполнителю '{executor_filter}': {len(filtered)} задач")

        return filtered

    def get_filtered_tasks_for_export(
        self,
        tasks: List[TaskGanttData],
        start_date: datetime,
        end_date: datetime
    ) -> List[TaskGanttData]:
        """Фильтрует задачи для экспорта по периоду"""
        return [
            task for task in tasks
            if task.start_date <= end_date and task.end_date >= start_date
        ]

    def get_date_range_for_tasks(self, tasks: List[TaskGanttData], padding_days: int = 14) -> Tuple[datetime, datetime]:
        """Возвращает диапазон дат для списка задач"""
        if not tasks:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            return today.replace(day=1), today.replace(day=28) + timedelta(days=30)

        start = min(t.start_date for t in tasks)
        end = max(t.end_date for t in tasks)

        start = start.replace(day=1)
        start = start - timedelta(days=padding_days)
        end = end + timedelta(days=padding_days)
        start = start.replace(day=1)

        if (end - start).days < 60:
            end = end + timedelta(days=30)

        return start, end

    def get_default_export_period(self, tasks: List[TaskGanttData]) -> Tuple[datetime, datetime]:
        return self.get_date_range_for_tasks(tasks, padding_days=0)

    # services/gantt_service/gantt_filter_service.py

    def get_date_range(self, period: str) -> Tuple[datetime, datetime]:
        """Возвращает диапазон дат для выбранного периода"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if period == "Месяц":
            start = today.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
            return start, end

        elif period == "Квартал":
            quarter = (today.month - 1) // 3
            start = today.replace(month=quarter * 3 + 1, day=1)
            if quarter == 3:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 3, day=1) - timedelta(days=1)
            return start, end

        elif period == "Полгода":  # ✅ ДОБАВЛЕНО
            if today.month <= 6:
                start = today.replace(month=1, day=1)
                end = today.replace(month=6, day=30)
            else:
                start = today.replace(month=7, day=1)
                end = today.replace(month=12, day=31)
            return start, end

        elif period == "Год":
            return today.replace(month=1, day=1), today.replace(month=12, day=31)

        else:  # "Неделя" или по умолчанию
            start = today - timedelta(days=today.weekday())
            return start, start + timedelta(days=6)

    def validate_project_selected(self, project_filter: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """Проверяет, выбран ли проект"""
        if project_filter == "all":
            return False, None, "Пожалуйста, сначала выберите проект из списка проектов"

        try:
            project_id = int(project_filter.split("_")[1])
            return True, project_id, None
        except (ValueError, IndexError):
            return False, None, "Неверный формат фильтра проекта"