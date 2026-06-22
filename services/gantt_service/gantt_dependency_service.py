# services/gantt_service/gantt_dependency_service.py

from datetime import datetime, timedelta
from typing import List, Dict, Optional

from models.tasks import TaskDependency
from .gantt_base_service import TaskGanttData


class GanttDependencyService:
    """Сервис для работы со связями между задачами"""

    def __init__(self, session, data_service, permission_service=None):
        self.session = session
        self._data = data_service
        self.permission_service = permission_service

    def _can_edit_task(self) -> bool:
        """Проверяет права на редактирование"""
        if not self.permission_service:
            return True
        from services.permissions.app_permissions import AppRole
        return self.permission_service.app_manager.role == AppRole.SUPER_ADMIN

    def get_all_links(self) -> Dict[int, List[int]]:
        """Возвращает все связи между задачами"""
        links = {}
        for task in self._data.get_all_tasks():
            for dep in task.dependencies:
                links.setdefault(task.id, []).append(dep["successor_id"])
        return links

    def get_linked_tasks_for_update(self, task_id: int) -> List[int]:
        """Возвращает ID задач, зависящих от данной"""
        linked = []
        for task in self._data.get_all_tasks():
            for dep in task.dependencies:
                if dep["successor_id"] == task_id:
                    linked.append(task.id)
        return linked

    def add_dependency(self, predecessor_id: int, successor_id: int, lag: int = 0, dep_type: str = "FS") -> bool:
        """Добавляет связь между задачами"""
        if not self._can_edit_task():
            print("❌ Нет прав на создание связей")
            return False

        try:
            existing = self.session.query(TaskDependency).filter(
                TaskDependency.predecessor_id == predecessor_id,
                TaskDependency.successor_id == successor_id
            ).first()

            if existing:
                return False

            dependency = TaskDependency(
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                lag=lag,
                type=dep_type
            )
            self.session.add(dependency)
            self.session.commit()

            for t in self._data.get_all_tasks():
                if t.id == predecessor_id:
                    t.dependencies.append({
                        "successor_id": successor_id,
                        "lag": lag,
                        "type": dep_type
                    })
                    break

            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка создания связи: {e}")
            return False

    def update_task_dates_with_linked(self, task_id: int, new_start: datetime, new_end: datetime) -> bool:
        """Обновляет даты задачи и всех зависимых"""
        from .gantt_data_service import GanttDataService

        if not self._can_edit_task():
            print("❌ Нет прав на изменение дат")
            return False

        try:
            data_service = GanttDataService(self.session)
            if not data_service.update_task_dates(task_id, new_start, new_end):
                return False

            old_task = None
            for t in self._data.get_all_tasks():
                if t.id == task_id:
                    old_start = t.start_date
                    break

            if old_start:
                delta = (new_start - old_start).days
                linked_ids = self.get_linked_tasks_for_update(task_id)

                for linked_id in linked_ids:
                    for t in self._data.get_all_tasks():
                        if t.id == linked_id:
                            new_linked_start = t.start_date + timedelta(days=delta)
                            new_linked_end = t.end_date + timedelta(days=delta)
                            data_service.update_task_dates(linked_id, new_linked_start, new_linked_end)
                            break

            return True
        except Exception as e:
            print(f"❌ Ошибка обновления дат: {e}")
            return False