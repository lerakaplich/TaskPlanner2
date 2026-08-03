# services/gantt_service/gantt_dependency_service.py

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from models.tasks import TaskDependency
from .gantt_base_service import TaskGanttData


class GanttDependencyService:
    """Сервис для работы со связями между задачами"""

    # Типы связей и их описание
    LINK_TYPES = {
        "FS": {"name": "Финиш-Старт", "symbol": "→", "description": "Задача B начинается после завершения задачи A"},
        "SS": {"name": "Старт-Старт", "symbol": "⇉", "description": "Задача B начинается одновременно с задачей A"},
        "FF": {"name": "Финиш-Финиш", "symbol": "⇇", "description": "Задача B завершается одновременно с задачей A"},
        "SF": {"name": "Старт-Финиш", "symbol": "↩", "description": "Задача B завершается после начала задачи A"},
    }

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

    def get_all_links(self) -> Dict[int, List[Dict]]:
        """Возвращает все связи между задачами с типами"""
        links = {}
        for task in self._data.get_all_tasks():
            for dep in task.dependencies:
                links.setdefault(task.id, []).append({
                    "successor_id": dep.get("successor_id"),
                    "lag": dep.get("lag", 0),
                    "type": dep.get("type", "FS")  # <-- Убедимся, что тип передается
                })
        return links

    def get_linked_tasks_for_update(self, task_id: int) -> List[int]:
        """Возвращает ID задач, которые зависят от данной (где данная - предшественник)"""
        linked = []
        for task in self._data.get_all_tasks():
            for dep in task.dependencies:
                if dep.get("successor_id") == task_id:
                    linked.append(task.id)
        return linked

    def add_dependency(
            self,
            predecessor_id: int,
            successor_id: int,
            lag: int = 0,
            dep_type: str = "FS"
    ) -> Tuple[bool, Optional[str]]:
        """Добавляет связь между задачами"""
        if not self._can_edit_task():
            return False, "Нет прав на создание связей"

        if dep_type not in self.LINK_TYPES:
            return False, f"Неизвестный тип связи: {dep_type}"

        try:
            existing = self.session.query(TaskDependency).filter(
                TaskDependency.predecessor_id == predecessor_id,
                TaskDependency.successor_id == successor_id
            ).first()

            if existing:
                return False, "Связь между этими задачами уже существует"

            pred_task = None
            succ_task = None
            for t in self._data.get_all_tasks():
                if t.id == predecessor_id:
                    pred_task = t
                if t.id == successor_id:
                    succ_task = t

            if not pred_task or not succ_task:
                return False, "Одна из задач не найдена"

            if self._would_create_cycle(predecessor_id, successor_id):
                return False, "Создание связи создаст циклическую зависимость"

            new_start, new_end = self._calculate_dates_for_successor(
                pred_task, succ_task, dep_type, lag
            )

            dependency = TaskDependency(
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                lag=lag,
                type=dep_type
            )
            self.session.add(dependency)
            self.session.flush()

            from models.tasks import Task
            self.session.query(Task).filter(Task.id == successor_id).update({
                Task.created_at: new_start,
                Task.deadline: new_end,
                Task.updated_at: datetime.now()
            }, synchronize_session=False)
            self.session.commit()

            for t in self._data.get_all_tasks():
                if t.id == predecessor_id:
                    t.dependencies.append({
                        "successor_id": successor_id,
                        "lag": lag,
                        "type": dep_type
                    })
                    break

            for t in self._data.get_all_tasks():
                if t.id == successor_id:
                    t.start_date = new_start
                    t.end_date = new_end
                    break

            return True, f"Связь типа {dep_type} успешно создана, даты обновлены"

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка создания связи: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Ошибка создания связи: {str(e)}"

    def _would_create_cycle(self, predecessor_id: int, successor_id: int) -> bool:
        """Проверяет, не создаст ли связь циклическую зависимость"""
        visited = set()
        stack = [successor_id]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            if current == predecessor_id:
                return True

            for task in self._data.get_all_tasks():
                for dep in task.dependencies:
                    if dep.get("successor_id") == current:
                        stack.append(task.id)
                        break

        return False

    def _calculate_dates_for_successor(
            self,
            pred_task: TaskGanttData,
            succ_task: TaskGanttData,
            dep_type: str,
            lag: int = 0
    ) -> Tuple[datetime, datetime]:
        """Рассчитывает новые даты для задачи-последователя"""
        pred_start = pred_task.start_date
        pred_end = pred_task.end_date
        succ_start = succ_task.start_date
        succ_end = succ_task.end_date

        duration = (succ_end - succ_start).days
        if duration <= 0:
            duration = 1

        if dep_type == "FS":
            new_start = pred_end + timedelta(days=lag)
            new_end = new_start + timedelta(days=duration)

        elif dep_type == "SS":
            new_start = max(succ_start, pred_start + timedelta(days=lag))
            new_end = new_start + timedelta(days=duration)

        elif dep_type == "FF":
            new_end = max(succ_end, pred_end + timedelta(days=lag))
            new_start = new_end - timedelta(days=duration)

        elif dep_type == "SF":
            new_end = max(succ_end, pred_start + timedelta(days=lag))
            new_start = new_end - timedelta(days=duration)

        else:
            new_start = succ_start
            new_end = succ_end

        if new_start > new_end:
            new_start, new_end = new_end, new_start + timedelta(days=1)

        new_start = new_start.replace(hour=0, minute=0, second=0, microsecond=0)
        new_end = new_end.replace(hour=0, minute=0, second=0, microsecond=0)

        return new_start, new_end

    def update_task_dates_with_linked(
            self,
            task_id: int,
            new_start: datetime,
            new_end: datetime
    ) -> bool:
        """
        Обновляет даты задачи и всех зависимых с учётом типов связей.
        Возвращает True при успехе.
        """
        if not self._can_edit_task():
            return False

        try:
            # Находим задачу в кэше
            old_task = None
            old_start = None
            for t in self._data.get_all_tasks():
                if t.id == task_id:
                    old_start = t.start_date
                    old_task = t
                    break

            if not old_task:
                return False

            # 1. Обновляем даты самой задачи
            from models.tasks import Task
            self.session.query(Task).filter(Task.id == task_id).update({
                Task.created_at: new_start,
                Task.deadline: new_end,
                Task.updated_at: datetime.now()
            }, synchronize_session=False)
            self.session.commit()

            # Обновляем в кэше
            for t in self._data.get_all_tasks():
                if t.id == task_id:
                    t.start_date = new_start
                    t.end_date = new_end
                    break

            # 2. Обновляем все зависимые задачи (где task_id - предшественник)
            delta_days = (new_start - old_start).days if old_start else 0

            # Получаем все задачи, которые зависят от task_id
            for task in self._data.get_all_tasks():
                # Проверяем зависимости задачи
                for dep in task.dependencies:
                    if dep.get("successor_id") == task_id:
                        # Это означает, что task_id является предшественником для task
                        link_type = dep.get("type", "FS")
                        lag = dep.get("lag", 0)

                        # Рассчитываем новые даты для зависимой задачи
                        new_linked_start, new_linked_end = self._calculate_dates_for_successor(
                            old_task,  # предшественник (старый, но используем для логики)
                            task,  # зависимая задача
                            link_type,
                            lag
                        )

                        # Обновляем даты в БД
                        self.session.query(Task).filter(Task.id == task.id).update({
                            Task.created_at: new_linked_start,
                            Task.deadline: new_linked_end,
                            Task.updated_at: datetime.now()
                        }, synchronize_session=False)
                        self.session.commit()

                        # Обновляем в кэше
                        for t in self._data.get_all_tasks():
                            if t.id == task.id:
                                t.start_date = new_linked_start
                                t.end_date = new_linked_end
                                break

                        # Рекурсивно обновляем задачи, зависящие от этой
                        self.update_task_dates_with_linked(task.id, new_linked_start, new_linked_end)
                        break

            return True

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка обновления дат: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_link_type_info(self, link_type: str) -> Dict:
        """Возвращает информацию о типе связи."""
        return self.LINK_TYPES.get(link_type, {"name": "Неизвестный", "symbol": "?", "description": ""})

    def get_all_link_types(self) -> Dict[str, Dict]:
        """Возвращает все доступные типы связей."""
        return self.LINK_TYPES