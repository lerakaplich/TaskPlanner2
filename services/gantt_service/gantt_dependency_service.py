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

    def delete_dependency(self, predecessor_id: int, successor_id: int) -> Tuple[bool, Optional[str]]:
        """Удаляет связь между задачами."""
        if not self._can_edit_task():
            return False, "Нет прав на удаление связей"

        try:
            # Ищем связь в БД
            dependency = self.session.query(TaskDependency).filter(
                TaskDependency.predecessor_id == predecessor_id,
                TaskDependency.successor_id == successor_id
            ).first()

            if not dependency:
                return False, "Связь не найдена"

            # Удаляем из БД
            self.session.delete(dependency)
            self.session.commit()

            # Удаляем из кэша
            for task in self._data.get_all_tasks():
                if task.id == predecessor_id:
                    task.dependencies = [
                        dep for dep in task.dependencies
                        if dep.get("successor_id") != successor_id
                    ]
                    break

            return True, "Связь успешно удалена"

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка удаления связи: {e}")
            return False, f"Ошибка удаления связи: {str(e)}"

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

            # ✅ Рассчитываем новые даты для задачи-последователя
            new_start, new_end = self._calculate_dates_for_successor(
                pred_task, succ_task, dep_type, lag
            )

            # ✅ Если даты изменились - обновляем задачу-последователя
            date_changed = False
            if new_start != succ_task.start_date or new_end != succ_task.end_date:
                date_changed = True
                succ_task.start_date = new_start
                succ_task.end_date = new_end
                print(f"🔄 Обновлены даты для задачи {succ_task.id} '{succ_task.name}'")
                print(f"   Было: {succ_task.start_date.date()} - {succ_task.end_date.date()}")
                print(f"   Стало: {new_start.date()} - {new_end.date()}")
                print(f"   Тип связи: {dep_type}")

            # Создаём связь в БД
            dependency = TaskDependency(
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                lag=lag,
                type=dep_type
            )
            self.session.add(dependency)
            self.session.flush()

            # ✅ Если даты изменились - обновляем в БД
            if date_changed:
                from models.tasks import Task
                self.session.query(Task).filter(Task.id == successor_id).update({
                    Task.created_at: new_start,
                    Task.deadline: new_end,
                    Task.updated_at: datetime.now()
                }, synchronize_session=False)

            self.session.commit()

            # Обновляем кэш
            for t in self._data.get_all_tasks():
                if t.id == predecessor_id:
                    t.dependencies.append({
                        "successor_id": successor_id,
                        "lag": lag,
                        "type": dep_type
                    })
                if t.id == successor_id:
                    t.start_date = new_start
                    t.end_date = new_end

            message = f"Связь типа {dep_type} успешно создана"
            if date_changed:
                message += f", даты задачи '{succ_task.name}' обновлены"

            return True, message

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

    # services/gantt_service/gantt_dependency_service.py

    def _calculate_dates_for_successor(
            self,
            pred_task: TaskGanttData,
            succ_task: TaskGanttData,
            dep_type: str,
            lag: int = 0
    ) -> Tuple[datetime, datetime]:
        """Рассчитывает новые даты для задачи-последователя с учётом ограничений"""
        pred_start = pred_task.start_date
        pred_end = pred_task.end_date
        succ_start = succ_task.start_date
        succ_end = succ_task.end_date

        # Длительность задачи-последователя
        duration = (succ_end - succ_start).days
        if duration <= 0:
            duration = 1

        if dep_type == "FS":  # Финиш-Старт
            # Старт последователя = финиш предшественника + lag
            new_start = pred_end + timedelta(days=lag)
            new_end = new_start + timedelta(days=duration)

        elif dep_type == "SS":  # Старт-Старт
            # ✅ Старт последователя = старт предшественника + lag
            new_start = pred_start + timedelta(days=lag)
            new_end = new_start + timedelta(days=duration)

        elif dep_type == "FF":  # Финиш-Финиш
            # Финиш последователя = финиш предшественника + lag
            new_end = pred_end + timedelta(days=lag)
            new_start = new_end - timedelta(days=duration)
            # Старт второй не может быть позже старта первой
            if new_start > pred_start:
                new_start = pred_start

        elif dep_type == "SF":  # Старт-Финиш
            # Финиш последователя = старт предшественника + lag
            new_end = pred_start + timedelta(days=lag)
            new_start = new_end - timedelta(days=duration)
            # Старт второй не может быть позже старта первой
            if new_start > pred_start:
                new_start = pred_start

        else:
            new_start = succ_start
            new_end = succ_end

        if new_start > new_end:
            new_start, new_end = new_end, new_start + timedelta(days=1)

        new_start = new_start.replace(hour=0, minute=0, second=0, microsecond=0)
        new_end = new_end.replace(hour=0, minute=0, second=0, microsecond=0)

        return new_start, new_end

    # services/gantt_service/gantt_dependency_service.py

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
            from models.tasks import Task

            # Находим задачу в кэше
            old_task = None
            for t in self._data.get_all_tasks():
                if t.id == task_id:
                    old_task = t
                    break

            if not old_task:
                return False

            # 1. Обновляем даты самой задачи в БД
            self.session.query(Task).filter(Task.id == task_id).update({
                Task.created_at: new_start,
                Task.deadline: new_end,
                Task.updated_at: datetime.now()
            }, synchronize_session=False)
            self.session.commit()

            # ✅ Обновляем в кэше для самой задачи
            for t in self._data.get_all_tasks():
                if t.id == task_id:
                    t.start_date = new_start
                    t.end_date = new_end
                    break

            # 2. Строим полную карту зависимостей (в обе стороны)
            all_tasks = self._data.get_all_tasks()
            dependency_map = {}  # predecessor_id -> [list of successor info]
            reverse_dependency_map = {}  # successor_id -> [list of predecessor info]

            for task in all_tasks:
                for dep in task.dependencies:
                    pred_id = task.id
                    succ_id = dep.get("successor_id")
                    if succ_id:
                        link_type = dep.get("type", "FS")
                        lag = dep.get("lag", 0)

                        # Прямая карта (предшественник -> последователь)
                        if pred_id not in dependency_map:
                            dependency_map[pred_id] = []
                        succ_task = None
                        for t in all_tasks:
                            if t.id == succ_id:
                                succ_task = t
                                break
                        if succ_task:
                            dependency_map[pred_id].append({
                                "task": succ_task,
                                "type": link_type,
                                "lag": lag
                            })

                        # Обратная карта (последователь -> предшественник)
                        if succ_id not in reverse_dependency_map:
                            reverse_dependency_map[succ_id] = []
                        pred_task = None
                        for t in all_tasks:
                            if t.id == pred_id:
                                pred_task = t
                                break
                        if pred_task:
                            reverse_dependency_map[succ_id].append({
                                "task": pred_task,
                                "type": link_type,
                                "lag": lag
                            })

            # 3. Обновляем зависимые задачи в обе стороны
            visited = set()

            # Сначала обновляем последователей (если двигаем предшественника)
            self._update_dependent_tasks_recursive_bidirectional(
                task_id,
                new_start,
                new_end,
                dependency_map,
                reverse_dependency_map,
                visited,
                is_forward=True
            )

            # ✅ Затем обновляем предшественников (если двигаем последователя)
            # Для SS и FF связей - двусторонняя синхронизация
            self._update_predecessors_recursive(
                task_id,
                new_start,
                new_end,
                reverse_dependency_map,
                set()
            )

            # ✅ Дополнительно обновляем кэш для всех затронутых задач
            self.session.commit()

            return True

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка обновления дат: {e}")
            import traceback
            traceback.print_exc()
            return False

    # services/gantt_service/gantt_dependency_service.py

    def _update_predecessors_recursive(
            self,
            task_id: int,
            new_start: datetime,
            new_end: datetime,
            reverse_dependency_map: Dict,
            visited: set
    ) -> None:
        """
        Рекурсивно обновляет предшественников задачи (для двусторонней синхронизации).
        """
        from models.tasks import Task

        if task_id in visited:
            return
        visited.add(task_id)

        # Находим задачу
        curr_task = None
        for t in self._data.get_all_tasks():
            if t.id == task_id:
                curr_task = t
                break

        if not curr_task:
            return

        # Находим предшественников (задачи, от которых зависит текущая)
        predecessors = reverse_dependency_map.get(task_id, [])

        for pred_info in predecessors:
            pred_task = pred_info["task"]
            link_type = pred_info["type"]
            lag = pred_info["lag"]

            # Для SS связи - синхронизируем старты в обе стороны
            if link_type == "SS":
                required_start = curr_task.start_date - timedelta(days=lag)
                old_start = pred_task.start_date
                old_end = pred_task.end_date
                duration = (pred_task.end_date - pred_task.start_date).days
                if duration <= 0:
                    duration = 1

                new_pred_start = required_start
                new_pred_end = new_pred_start + timedelta(days=duration)

                if pred_task.start_date != new_pred_start or pred_task.end_date != new_pred_end:
                    print(
                        f"🔄 Двусторонняя синхронизация (SS): обновление предшественника {pred_task.id} '{pred_task.name}'")
                    print(f"   Было: {old_start.date()} - {old_end.date()}")
                    print(f"   Стало: {new_pred_start.date()} - {new_pred_end.date()}")
                    print(f"   Текущая задача: {curr_task.id} '{curr_task.name}' старт {curr_task.start_date.date()}")

                    self.session.query(Task).filter(Task.id == pred_task.id).update({
                        Task.created_at: new_pred_start,
                        Task.deadline: new_pred_end,
                        Task.updated_at: datetime.now()
                    }, synchronize_session=False)
                    self.session.commit()

                    for t in self._data.get_all_tasks():
                        if t.id == pred_task.id:
                            t.start_date = new_pred_start
                            t.end_date = new_pred_end
                            break

                    self._update_predecessors_recursive(
                        pred_task.id,
                        new_pred_start,
                        new_pred_end,
                        reverse_dependency_map,
                        visited
                    )

            # Для FF связи - синхронизируем финиши в обе стороны
            elif link_type == "FF":
                required_end = curr_task.end_date - timedelta(days=lag)
                old_start = pred_task.start_date
                old_end = pred_task.end_date
                duration = (pred_task.end_date - pred_task.start_date).days
                if duration <= 0:
                    duration = 1

                new_pred_end = required_end
                new_pred_start = new_pred_end - timedelta(days=duration)

                if pred_task.start_date != new_pred_start or pred_task.end_date != new_pred_end:
                    print(
                        f"🔄 Двусторонняя синхронизация (FF): обновление предшественника {pred_task.id} '{pred_task.name}'")
                    print(f"   Было: {old_start.date()} - {old_end.date()}")
                    print(f"   Стало: {new_pred_start.date()} - {new_pred_end.date()}")
                    print(f"   Текущая задача: {curr_task.id} '{curr_task.name}' финиш {curr_task.end_date.date()}")

                    self.session.query(Task).filter(Task.id == pred_task.id).update({
                        Task.created_at: new_pred_start,
                        Task.deadline: new_pred_end,
                        Task.updated_at: datetime.now()
                    }, synchronize_session=False)
                    self.session.commit()

                    for t in self._data.get_all_tasks():
                        if t.id == pred_task.id:
                            t.start_date = new_pred_start
                            t.end_date = new_pred_end
                            break

                    self._update_predecessors_recursive(
                        pred_task.id,
                        new_pred_start,
                        new_pred_end,
                        reverse_dependency_map,
                        visited
                    )

            # ✅ Для FS связи - синхронизируем финиш предшественника со стартом последователя
            elif link_type == "FS":
                # Финиш предшественника = старт последователя - lag
                required_end = curr_task.start_date - timedelta(days=lag)
                old_start = pred_task.start_date
                old_end = pred_task.end_date
                duration = (pred_task.end_date - pred_task.start_date).days
                if duration <= 0:
                    duration = 1

                new_pred_end = required_end
                new_pred_start = new_pred_end - timedelta(days=duration)

                if pred_task.start_date != new_pred_start or pred_task.end_date != new_pred_end:
                    print(f"🔄 Синхронизация (FS): обновление предшественника {pred_task.id} '{pred_task.name}'")
                    print(f"   Было: {old_start.date()} - {old_end.date()}")
                    print(f"   Стало: {new_pred_start.date()} - {new_pred_end.date()}")
                    print(f"   Текущая задача: {curr_task.id} '{curr_task.name}' старт {curr_task.start_date.date()}")

                    self.session.query(Task).filter(Task.id == pred_task.id).update({
                        Task.created_at: new_pred_start,
                        Task.deadline: new_pred_end,
                        Task.updated_at: datetime.now()
                    }, synchronize_session=False)
                    self.session.commit()

                    for t in self._data.get_all_tasks():
                        if t.id == pred_task.id:
                            t.start_date = new_pred_start
                            t.end_date = new_pred_end
                            break

                    self._update_predecessors_recursive(
                        pred_task.id,
                        new_pred_start,
                        new_pred_end,
                        reverse_dependency_map,
                        visited
                    )

            # ✅ Для SF связи - синхронизируем старт предшественника с финишем последователя
            elif link_type == "SF":
                # Старт предшественника = финиш последователя - lag
                required_start = curr_task.end_date - timedelta(days=lag)
                old_start = pred_task.start_date
                old_end = pred_task.end_date
                duration = (pred_task.end_date - pred_task.start_date).days
                if duration <= 0:
                    duration = 1

                new_pred_start = required_start
                new_pred_end = new_pred_start + timedelta(days=duration)

                if pred_task.start_date != new_pred_start or pred_task.end_date != new_pred_end:
                    print(f"🔄 Синхронизация (SF): обновление предшественника {pred_task.id} '{pred_task.name}'")
                    print(f"   Было: {old_start.date()} - {old_end.date()}")
                    print(f"   Стало: {new_pred_start.date()} - {new_pred_end.date()}")
                    print(f"   Текущая задача: {curr_task.id} '{curr_task.name}' финиш {curr_task.end_date.date()}")

                    self.session.query(Task).filter(Task.id == pred_task.id).update({
                        Task.created_at: new_pred_start,
                        Task.deadline: new_pred_end,
                        Task.updated_at: datetime.now()
                    }, synchronize_session=False)
                    self.session.commit()

                    for t in self._data.get_all_tasks():
                        if t.id == pred_task.id:
                            t.start_date = new_pred_start
                            t.end_date = new_pred_end
                            break

                    self._update_predecessors_recursive(
                        pred_task.id,
                        new_pred_start,
                        new_pred_end,
                        reverse_dependency_map,
                        visited
                    )

    # services/gantt_service/gantt_dependency_service.py

    def _update_dependent_tasks_recursive_bidirectional(
            self,
            task_id: int,
            new_start: datetime,
            new_end: datetime,
            dependency_map: Dict,
            reverse_dependency_map: Dict,
            visited: set,
            is_forward: bool = True
    ) -> None:
        """
        Рекурсивно обновляет все зависимые задачи с учётом двусторонней синхронизации.
        """
        from models.tasks import Task

        if task_id in visited:
            return
        visited.add(task_id)

        # Получаем обновлённую задачу-предшественника
        pred_task = None
        for t in self._data.get_all_tasks():
            if t.id == task_id:
                pred_task = t
                break

        if not pred_task:
            return

        # Находим задачи, которые зависят от обновлённой
        dependent = dependency_map.get(task_id, [])

        for dep_info in dependent:
            succ_task = dep_info["task"]
            link_type = dep_info["type"]
            lag = dep_info["lag"]

            # Рассчитываем новые даты с учётом ограничений
            new_succ_start, new_succ_end = self._calculate_dates_for_successor(
                pred_task, succ_task, link_type, lag
            )

            # Проверяем, изменились ли даты
            if (new_succ_start != succ_task.start_date or
                    new_succ_end != succ_task.end_date):

                print(f"🔄 Обновление задачи {succ_task.id} '{succ_task.name}'")
                print(f"   Было: {succ_task.start_date.date()} - {succ_task.end_date.date()}")
                print(f"   Стало: {new_succ_start.date()} - {new_succ_end.date()}")
                print(f"   Тип связи: {link_type}")

                # Обновляем даты в БД
                self.session.query(Task).filter(Task.id == succ_task.id).update({
                    Task.created_at: new_succ_start,
                    Task.deadline: new_succ_end,
                    Task.updated_at: datetime.now()
                }, synchronize_session=False)
                self.session.commit()

                # Обновляем в кэше
                for t in self._data.get_all_tasks():
                    if t.id == succ_task.id:
                        t.start_date = new_succ_start
                        t.end_date = new_succ_end
                        break

                # Рекурсивно обновляем задачи, зависящие от этой
                self._update_dependent_tasks_recursive_bidirectional(
                    succ_task.id,
                    new_succ_start,
                    new_succ_end,
                    dependency_map,
                    reverse_dependency_map,
                    visited,
                    is_forward
                )

                # ✅ Для SS и FF - обновляем предшественников (двусторонняя синхронизация)
                if link_type in ("SS", "FF") and is_forward:
                    self._update_predecessors_recursive(
                        succ_task.id,
                        new_succ_start,
                        new_succ_end,
                        reverse_dependency_map,
                        set()
                    )

                # ✅ Для FS и SF - также обновляем предшественников
                if link_type in ("FS", "SF") and is_forward:
                    self._update_predecessors_recursive(
                        succ_task.id,
                        new_succ_start,
                        new_succ_end,
                        reverse_dependency_map,
                        set()
                    )

    def _update_dependent_tasks_recursive(
            self,
            task_id: int,
            new_start: datetime,
            new_end: datetime,
            dependency_map: Dict,
            visited: set
    ) -> None:
        """
        Рекурсивно обновляет все зависимые задачи.
        """
        from models.tasks import Task

        # Защита от циклов
        if task_id in visited:
            return
        visited.add(task_id)

        # Получаем обновлённую задачу-предшественника
        pred_task = None
        for t in self._data.get_all_tasks():
            if t.id == task_id:
                pred_task = t
                break

        if not pred_task:
            return

        # Находим задачи, которые зависят от обновлённой
        dependent = dependency_map.get(task_id, [])

        for dep_info in dependent:
            succ_task = dep_info["task"]
            link_type = dep_info["type"]
            lag = dep_info["lag"]

            # Рассчитываем новые даты с учётом ограничений
            new_succ_start, new_succ_end = self._calculate_dates_for_successor(
                pred_task, succ_task, link_type, lag
            )

            # Проверяем, изменились ли даты
            if (new_succ_start != succ_task.start_date or
                    new_succ_end != succ_task.end_date):

                print(f"🔄 Обновление задачи {succ_task.id} '{succ_task.name}'")
                print(f"   Было: {succ_task.start_date.date()} - {succ_task.end_date.date()}")
                print(f"   Стало: {new_succ_start.date()} - {new_succ_end.date()}")
                print(f"   Тип связи: {link_type}")

                # Обновляем даты в БД
                self.session.query(Task).filter(Task.id == succ_task.id).update({
                    Task.created_at: new_succ_start,
                    Task.deadline: new_succ_end,
                    Task.updated_at: datetime.now()
                }, synchronize_session=False)
                self.session.commit()

                # Обновляем в кэше
                for t in self._data.get_all_tasks():
                    if t.id == succ_task.id:
                        t.start_date = new_succ_start
                        t.end_date = new_succ_end
                        break

                # Рекурсивно обновляем задачи, зависящие от этой
                self._update_dependent_tasks_recursive(
                    succ_task.id,
                    new_succ_start,
                    new_succ_end,
                    dependency_map,
                    visited
                )

    def get_link_type_info(self, link_type: str) -> Dict:
        """Возвращает информацию о типе связи."""
        return self.LINK_TYPES.get(link_type, {"name": "Неизвестный", "symbol": "?", "description": ""})

    def get_all_link_types(self) -> Dict[str, Dict]:
        """Возвращает все доступные типы связей."""
        return self.LINK_TYPES