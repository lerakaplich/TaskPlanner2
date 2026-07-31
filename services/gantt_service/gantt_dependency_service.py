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
                    "type": dep.get("type", "FS")
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

    # services/gantt_service/gantt_dependency_service.py

    def add_dependency(
            self,
            predecessor_id: int,
            successor_id: int,
            lag: int = 0,
            dep_type: str = "FS"
    ) -> Tuple[bool, Optional[str]]:
        """
        Добавляет связь между задачами с указанным типом.
        При создании связи автоматически пересчитывает даты задачи-последователя.
        """
        if not self._can_edit_task():
            return False, "Нет прав на создание связей"

        if dep_type not in self.LINK_TYPES:
            return False, f"Неизвестный тип связи: {dep_type}"

        try:
            # Проверяем существование связи
            existing = self.session.query(TaskDependency).filter(
                TaskDependency.predecessor_id == predecessor_id,
                TaskDependency.successor_id == successor_id
            ).first()

            if existing:
                return False, "Связь между этими задачами уже существует"

            # Находим задачи
            pred_task = None
            succ_task = None
            for t in self._data.get_all_tasks():
                if t.id == predecessor_id:
                    pred_task = t
                if t.id == successor_id:
                    succ_task = t

            if not pred_task or not succ_task:
                return False, "Одна из задач не найдена"

            # Проверяем, не создаст ли связь циклическую зависимость
            if self._would_create_cycle(predecessor_id, successor_id):
                return False, "Создание связи создаст циклическую зависимость"

            # Рассчитываем новые даты для задачи-последователя
            new_start, new_end = self._calculate_dates_for_successor(
                pred_task, succ_task, dep_type, lag
            )

            # Создаём связь в БД
            dependency = TaskDependency(
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                lag=lag,
                type=dep_type
            )
            self.session.add(dependency)

            # Обновляем даты задачи-последователя в БД
            from .gantt_data_service import GanttDataService
            data_service = GanttDataService(self.session)
            data_service.update_task_dates(successor_id, new_start, new_end)

            self.session.commit()

            # Обновляем кэш
            for t in self._data.get_all_tasks():
                if t.id == predecessor_id:
                    t.dependencies.append({
                        "successor_id": successor_id,
                        "lag": lag,
                        "type": dep_type
                    })
                    break

            # Обновляем задачу-последователя в кэше
            for t in self._data.get_all_tasks():
                if t.id == successor_id:
                    t.start_date = new_start
                    t.end_date = new_end
                    break

            return True, f"Связь типа {dep_type} успешно создана, даты обновлены"

        except Exception as e:
            self.session.rollback()
            return False, f"Ошибка создания связи: {str(e)}"

    def _would_create_cycle(self, predecessor_id: int, successor_id: int) -> bool:
        """Проверяет, не создаст ли связь циклическую зависимость"""
        # Простая проверка: если уже есть путь от successor к predecessor
        visited = set()
        stack = [successor_id]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            if current == predecessor_id:
                return True

            # Находим все задачи, которые зависят от current
            for task in self._data.get_all_tasks():
                for dep in task.dependencies:
                    if dep.get("successor_id") == current:
                        stack.append(task.id)
                        break

        return False

    # services/gantt_service/gantt_dependency_service.py

    def _calculate_dates_for_successor(
            self,
            pred_task: TaskGanttData,
            succ_task: TaskGanttData,
            dep_type: str,
            lag: int = 0
    ) -> Tuple[datetime, datetime]:
        """
        Рассчитывает новые даты для задачи-последователя в зависимости от типа связи.

        Правила (согласно логике):
        - FS (Финиш-Старт): succ.start >= pred.end + lag
        - SS (Старт-Старт): succ.start >= pred.start + lag
        - FF (Финиш-Финиш): succ.end >= pred.end + lag
        - SF (Старт-Финиш): succ.end >= pred.start + lag
        """
        pred_start = pred_task.start_date
        pred_end = pred_task.end_date
        succ_start = succ_task.start_date
        succ_end = succ_task.end_date

        # Рассчитываем длительность задачи-последователя
        duration = (succ_end - succ_start).days
        if duration <= 0:
            duration = 1  # Минимум 1 день

        if dep_type == "FS":  # Финиш-Старт
            # Задача-последователь начинается ПОСЛЕ завершения предшественника
            new_start = pred_end + timedelta(days=lag)
            new_end = new_start + timedelta(days=duration)

        elif dep_type == "SS":  # Старт-Старт
            # Задача-последователь начинается ОДНОВРЕМЕННО или ПОЗЖЕ предшественника
            new_start = max(succ_start, pred_start + timedelta(days=lag))
            new_end = new_start + timedelta(days=duration)

        elif dep_type == "FF":  # Финиш-Финиш
            # Задача-последователь завершается ОДНОВРЕМЕННО или ПОЗЖЕ предшественника
            new_end = max(succ_end, pred_end + timedelta(days=lag))
            new_start = new_end - timedelta(days=duration)

        elif dep_type == "SF":  # Старт-Финиш
            # Задача-последователь завершается ПОСЛЕ начала предшественника
            new_end = max(succ_end, pred_start + timedelta(days=lag))
            new_start = new_end - timedelta(days=duration)

        else:
            new_start = succ_start
            new_end = succ_end

        # Убеждаемся, что даты корректны
        if new_start > new_end:
            new_start, new_end = new_end, new_start + timedelta(days=1)

        # Округляем до начала дня
        new_start = new_start.replace(hour=0, minute=0, second=0, microsecond=0)
        new_end = new_end.replace(hour=0, minute=0, second=0, microsecond=0)

        return new_start, new_end

    def update_task_dates_with_linked(
        self,
        task_id: int,
        new_start: datetime,
        new_end: datetime
    ) -> Tuple[bool, Optional[str]]:
        """
        Обновляет даты задачи и всех зависимых с учётом типов связей.
        Возвращает (успех, сообщение).
        """
        from .gantt_data_service import GanttDataService

        if not self._can_edit_task():
            return False, "Нет прав на изменение дат"

        try:
            data_service = GanttDataService(self.session)

            # Получаем старые даты задачи
            old_task = None
            old_start = None
            for t in self._data.get_all_tasks():
                if t.id == task_id:
                    old_start = t.start_date
                    old_task = t
                    break

            if not old_task:
                return False, f"Задача {task_id} не найдена"

            # Обновляем даты задачи
            if not data_service.update_task_dates(task_id, new_start, new_end):
                return False, "Не удалось обновить даты задачи"

            # Рассчитываем смещение
            delta_days = (new_start - old_start).days if old_start else 0

            # Обновляем зависимые задачи с учётом типа связи
            linked_tasks = self.get_linked_tasks_for_update(task_id)

            for linked_id in linked_tasks:
                linked_task = None
                for t in self._data.get_all_tasks():
                    if t.id == linked_id:
                        linked_task = t
                        break

                if not linked_task:
                    continue

                # Находим тип связи
                link_type = "FS"  # По умолчанию
                for dep in linked_task.dependencies:
                    if dep.get("successor_id") == task_id:
                        link_type = dep.get("type", "FS")
                        break

                # Рассчитываем новые даты в зависимости от типа связи
                new_linked_start, new_linked_end = self._calculate_dates_by_link_type(
                    linked_task,
                    old_start,
                    new_start,
                    delta_days,
                    link_type
                )

                if new_linked_start and new_linked_end:
                    data_service.update_task_dates(linked_id, new_linked_start, new_linked_end)

            return True, "Даты обновлены"

        except Exception as e:
            return False, f"Ошибка обновления дат: {str(e)}"

    def _calculate_dates_by_link_type(
        self,
        task: TaskGanttData,
        old_start: datetime,
        new_start: datetime,
        delta_days: int,
        link_type: str
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Рассчитывает новые даты для задачи в зависимости от типа связи.
        """
        if link_type == "FS":  # Финиш-Старт
            # Задача начинается после завершения предшественника
            return task.start_date + timedelta(days=delta_days), task.end_date + timedelta(days=delta_days)

        elif link_type == "SS":  # Старт-Старт
            # Обе задачи начинаются одновременно
            duration = (task.end_date - task.start_date).days
            new_start_date = new_start
            new_end_date = new_start_date + timedelta(days=duration)
            return new_start_date, new_end_date

        elif link_type == "FF":  # Финиш-Финиш
            # Обе задачи завершаются одновременно
            duration = (task.end_date - task.start_date).days
            new_end_date = new_start + (task.end_date - old_start)  # Используем смещение от старого старта
            new_start_date = new_end_date - timedelta(days=duration)
            return new_start_date, new_end_date

        elif link_type == "SF":  # Старт-Финиш
            # Задача завершается после начала предшественника
            duration = (task.end_date - task.start_date).days
            new_start_date = new_start + timedelta(days=delta_days)
            new_end_date = new_start_date + timedelta(days=duration)
            return new_start_date, new_end_date

        else:
            # По умолчанию - обычный сдвиг
            return task.start_date + timedelta(days=delta_days), task.end_date + timedelta(days=delta_days)

    def get_link_type_info(self, link_type: str) -> Dict:
        """Возвращает информацию о типе связи."""
        return self.LINK_TYPES.get(link_type, {"name": "Неизвестный", "symbol": "?", "description": ""})

    def get_all_link_types(self) -> Dict[str, Dict]:
        """Возвращает все доступные типы связей."""
        return self.LINK_TYPES