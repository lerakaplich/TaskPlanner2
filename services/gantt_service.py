# services/gantt_service.py

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from PyQt6.QtGui import QPainter
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func

from database import get_employees_session
from models.tasks import Task, TaskDependency
from models.projects import Project
from models.employees import Employee


class GanttService:
    """Сервис для работы с диаграммой Ганта"""

    def __init__(self, session: Session, current_user_id: int = None):
        self.session = session
        self.employees_session = get_employees_session()
        self.current_user_id = current_user_id

    def __del__(self):
        try:
            if self.employees_session:
                self.employees_session.close()
        except:
            pass

    def set_current_user_id(self, user_id: int):
        self.current_user_id = user_id

    def get_projects_for_gantt(self) -> List[Dict]:
        """Получает список проектов для выбора"""
        stmt = select(Project).where(Project.is_archived == False).order_by(Project.name)
        projects = self.session.scalars(stmt).all()
        return [{"id": p.id, "name": p.name} for p in projects]

    def auto_plan_tasks(self, project_id: int, start_date: datetime.date = None) -> Dict:
        """
        Автоматическое планирование задач проекта на основе зависимостей.
        Возвращает обновленные задачи.
        """
        try:
            # Получаем все задачи проекта
            stmt = select(Task).where(
                Task.project_id == project_id,
                Task.is_archived == False
            ).options(
                joinedload(Task.column),
                joinedload(Task.dependencies_as_predecessor),
                joinedload(Task.dependencies_as_successor)
            )

            tasks = list(self.session.scalars(stmt).unique())

            if not tasks:
                return {"tasks": [], "message": "Нет задач для планирования"}

            # Если не указана дата начала, берем минимальную из существующих
            if start_date is None:
                start_date = min(
                    (t.created_at.date() if t.created_at else datetime.now().date() for t in tasks),
                    default=datetime.now().date()
                )

            # Создаем словарь для быстрого доступа к задачам
            task_dict = {t.id: t for t in tasks}

            # Словарь для хранения вычисленных дат
            planned_dates = {}

            # Строим граф зависимостей
            dependencies = {}
            for task in tasks:
                dependencies[task.id] = []
                for dep in task.dependencies_as_predecessor:
                    dependencies[task.id].append({
                        "pred_id": dep.predecessor_id,
                        "lag": dep.lag,
                        "type": dep.type
                    })

            # Выполняем топологическую сортировку
            sorted_task_ids = self._topological_sort(dependencies, [t.id for t in tasks])

            if not sorted_task_ids:
                # Если есть циклы, используем простой порядок
                sorted_task_ids = [t.id for t in tasks]

            # Вычисляем даты
            for task_id in sorted_task_ids:
                task = task_dict.get(task_id)
                if not task:
                    continue

                # Начальная дата - текущая или дедлайн предшественника
                earliest_start = start_date

                # Проверяем зависимости
                for dep in dependencies.get(task_id, []):
                    pred_task = task_dict.get(dep["pred_id"])
                    if pred_task and pred_task.id in planned_dates:
                        pred_end = planned_dates[pred_task.id]["end_date"]

                        if dep["type"] == "FS":  # Финиш-Старт
                            earliest_start = max(earliest_start, pred_end + timedelta(days=dep["lag"]))
                        elif dep["type"] == "SS":  # Старт-Старт
                            pred_start = planned_dates[pred_task.id]["start_date"]
                            earliest_start = max(earliest_start, pred_start + timedelta(days=dep["lag"]))
                        elif dep["type"] == "FF":  # Финиш-Финиш
                            pred_end = planned_dates[pred_task.id]["end_date"]
                            # Для FF нужно, чтобы дата окончания была не раньше pred_end + lag
                            pass  # Обработаем при вычислении end_date

                # Вычисляем дату окончания
                duration = task.duration_days if hasattr(task, 'duration_days') else 7
                end_date = earliest_start + timedelta(days=duration - 1)

                # Корректировка для FF зависимостей
                for dep in dependencies.get(task_id, []):
                    if dep["type"] == "FF":
                        pred_task = task_dict.get(dep["pred_id"])
                        if pred_task and pred_task.id in planned_dates:
                            pred_end = planned_dates[pred_task.id]["end_date"]
                            required_end = pred_end + timedelta(days=dep["lag"])
                            if end_date < required_end:
                                end_date = required_end
                                earliest_start = end_date - timedelta(days=duration - 1)

                planned_dates[task_id] = {
                    "start_date": earliest_start,
                    "end_date": end_date,
                    "duration": duration
                }

            # Применяем вычисленные даты к задачам
            updated_tasks = []
            for task_id, dates in planned_dates.items():
                task = task_dict.get(task_id)
                if task:
                    old_start = task.created_at.date() if task.created_at else None
                    old_end = task.deadline.date() if task.deadline else None

                    if old_start != dates["start_date"] or old_end != dates["end_date"]:
                        task.created_at = datetime.combine(dates["start_date"], datetime.min.time())
                        task.deadline = datetime.combine(dates["end_date"], datetime.min.time())
                        updated_tasks.append({
                            "id": task.id,
                            "title": task.title,
                            "old_start": old_start,
                            "old_end": old_end,
                            "new_start": dates["start_date"],
                            "new_end": dates["end_date"]
                        })

            if updated_tasks:
                self.session.commit()
                print(f"✅ Автопланирование выполнено: обновлено {len(updated_tasks)} задач")

            return {
                "tasks": updated_tasks,
                "message": f"Обновлено {len(updated_tasks)} задач" if updated_tasks else "Все задачи уже оптимально спланированы"
            }

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка автопланирования: {e}")
            import traceback
            traceback.print_exc()
            return {"tasks": [], "message": f"Ошибка: {str(e)}"}

    def _topological_sort(self, dependencies: Dict, task_ids: List[int]) -> List[int]:
        """Топологическая сортировка задач по зависимостям"""
        from collections import deque

        # Строим граф
        graph = {tid: [] for tid in task_ids}
        in_degree = {tid: 0 for tid in task_ids}

        for task_id in task_ids:
            for dep in dependencies.get(task_id, []):
                pred_id = dep["pred_id"]
                if pred_id in graph:
                    graph[pred_id].append(task_id)
                    in_degree[task_id] = in_degree.get(task_id, 0) + 1

        # Алгоритм Кана
        queue = deque([tid for tid in task_ids if in_degree.get(tid, 0) == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Если не все задачи отсортированы, значит есть цикл
        if len(result) != len(task_ids):
            print("⚠️ Обнаружен цикл в зависимостях, используется простой порядок")
            return task_ids

        return result

    def calculate_critical_path(self, project_id: int) -> List[Dict]:
        """
        Расчет критического пути проекта.
        Возвращает список задач на критическом пути.
        """
        try:
            # Получаем все задачи проекта
            stmt = select(Task).where(
                Task.project_id == project_id,
                Task.is_archived == False
            ).options(
                joinedload(Task.dependencies_as_predecessor)
            )

            tasks = list(self.session.scalars(stmt).unique())

            if not tasks:
                return []

            # Строим граф зависимостей
            task_dict = {t.id: t for t in tasks}
            dependencies = {}
            for task in tasks:
                dependencies[task.id] = []
                for dep in task.dependencies_as_predecessor:
                    dependencies[task.id].append({
                        "pred_id": dep.predecessor_id,
                        "lag": dep.lag,
                        "type": dep.type
                    })

            # Вычисляем ранние сроки
            early_start = {}
            early_finish = {}

            for task in tasks:
                duration = (task.deadline - task.created_at).days + 1 if task.deadline and task.created_at else 7
                early_start[task.id] = task.created_at.date() if task.created_at else datetime.now().date()

                # Учитываем зависимости
                for dep in dependencies.get(task.id, []):
                    if dep["type"] == "FS":
                        pred_finish = early_finish.get(dep["pred_id"])
                        if pred_finish:
                            new_start = pred_finish + timedelta(days=dep["lag"])
                            if new_start > early_start[task.id]:
                                early_start[task.id] = new_start

                early_finish[task.id] = early_start[task.id] + timedelta(days=duration - 1)

            # Находим максимальную дату окончания
            project_end = max(early_finish.values()) if early_finish else datetime.now().date()

            # Вычисляем поздние сроки (итеративно)
            late_finish = {tid: project_end for tid in task_ids}
            late_start = {}

            # Проходим в обратном порядке
            for task in reversed(tasks):
                duration = (task.deadline - task.created_at).days + 1 if task.deadline and task.created_at else 7
                late_start[task.id] = late_finish[task.id] - timedelta(days=duration - 1)

                # Обновляем поздние сроки для предшественников
                for dep in dependencies.get(task.id, []):
                    if dep["type"] == "FS":
                        pred_id = dep["pred_id"]
                        if pred_id in late_finish:
                            new_pred_finish = late_start[task.id] - timedelta(days=dep["lag"])
                            if new_pred_finish < late_finish[pred_id]:
                                late_finish[pred_id] = new_pred_finish

            # Определяем задачи на критическом пути (где резерв = 0)
            critical_path = []
            for task in tasks:
                slack = (late_start[task.id] - early_start[task.id]).days
                if slack == 0:
                    critical_path.append({
                        "id": task.id,
                        "title": task.title,
                        "start_date": early_start[task.id],
                        "end_date": early_finish[task.id],
                        "slack": slack
                    })

            return critical_path

        except Exception as e:
            print(f"❌ Ошибка расчета критического пути: {e}")
            return []

    def get_project_tasks_for_gantt(self, project_id: int, filters: Dict = None) -> Dict:
        """
        Получает задачи проекта с учетом фильтров.
        filters: {'my_tasks': bool, 'overdue': bool, 'in_progress': bool, 'completed': bool, 'search': str}
        """
        project = self.session.get(Project, project_id)
        if not project:
            return self._get_empty_result()

        # ✅ ИСПРАВЛЕНИЕ: добавляем joinedload для колонки
        stmt = select(Task).where(
            Task.project_id == project_id,
            Task.is_archived == False
        ).options(
            joinedload(Task.column),
            joinedload(Task.dependencies_as_predecessor)  # 👈 ДОБАВИТЬ
        )

        tasks = self.session.scalars(stmt).unique().all()  # unique() для устранения дублей

        if not tasks:
            return self._get_empty_result()

        today = datetime.now().date()
        gantt_tasks = []

        for task in tasks:
            # Применяем фильтры
            if filters:
                if filters.get('my_tasks') and task.assigned_to != self.current_user_id:
                    continue
                if filters.get('overdue') and not self._is_overdue(task, today):
                    continue
                if filters.get('completed') and not self._is_completed(task):
                    continue
                if filters.get('in_progress') and (self._is_completed(task) or self._is_overdue(task, today)):
                    continue
                if filters.get('search'):
                    search = filters['search'].lower()
                    if search not in task.title.lower():
                        continue

            assignee_name = self._get_employee_name(task.assigned_to) if task.assigned_to else ""
            is_completed = self._is_completed(task)
            is_overdue = self._is_overdue(task, today)
            priority_value = task.priority.value if hasattr(task.priority, 'value') else str(task.priority)
            is_critical = priority_value in ["high", "critical"]

            start_date = task.created_at.date() if task.created_at else today
            end_date = task.deadline.date() if task.deadline else start_date + timedelta(days=7)

            # ✅ Исправляем отрицательную длительность
            if start_date > end_date:
                start_date, end_date = end_date, start_date  # Меняем местами
                # Или можно задать end_date = start_date + timedelta(days=7)

            # ✅ ДОБАВЛЯЕМ проверку на наличие колонки
            column_name = task.column.name if task.column else "unknown"

            dependencies = []
            for dep in task.dependencies_as_predecessor:
                dependencies.append({
                    "successor_id": dep.successor_id,
                    "lag": dep.lag,
                    "type": dep.type
                })

            gantt_tasks.append({
                "id": task.id,
                "title": task.title,
                "description": task.description or "",
                "start_date": start_date,
                "end_date": end_date,
                "assignee": assignee_name,
                "assignee_id": task.assigned_to,
                "is_critical": is_critical,
                "dependencies": dependencies,
                "children": [],
                "project_id": task.project_id,
                "status": column_name,  # <-- ИСПРАВЛЕНО
                "is_completed": is_completed,
                "is_overdue": is_overdue,
                "duration_days": (end_date - start_date).days + 1,
                "priority": priority_value
            })

        if not gantt_tasks:
            return self._get_empty_result()

        start = min(t["start_date"] for t in gantt_tasks)
        end = max(t["end_date"] for t in gantt_tasks)
        total = len(gantt_tasks)
        completed = sum(1 for t in gantt_tasks if t["is_completed"])
        overdue = sum(1 for t in gantt_tasks if t["is_overdue"])

        return {
            "tasks": gantt_tasks,
            "project_start": start,
            "project_end": end,
            "total_tasks": total,
            "completed_tasks": completed,
            "overdue_tasks": overdue,
            "in_progress_tasks": total - completed,
            "project_name": project.name
        }

    def _is_completed(self, task: Task) -> bool:
        return task.column and task.column.is_done_column

    def _is_overdue(self, task: Task, today: datetime.date) -> bool:
        if task.deadline and not self._is_completed(task):
            return task.deadline.date() < today
        return False

    def _get_empty_result(self) -> Dict:
        today = datetime.now().date()
        return {
            "tasks": [],
            "project_start": today,
            "project_end": today + timedelta(days=30),
            "total_tasks": 0,
            "completed_tasks": 0,
            "overdue_tasks": 0,
            "in_progress_tasks": 0,
            "project_name": ""
        }

    def _get_employee_name(self, employee_id: int) -> str:
        try:
            employee = self.employees_session.get(Employee, employee_id)
            if employee:
                name = f"{employee.last_name} {employee.first_name[0] if employee.first_name else ''}."
                if employee.middle_name:
                    name += f" {employee.middle_name[0]}."
                return name
        except Exception as e:
            print(f"⚠️ Ошибка получения имени сотрудника: {e}")
        return ""

    def export_to_image(self, scene, filepath: str) -> bool:
        """Экспорт диаграммы в изображение"""
        try:
            from PyQt6.QtGui import QPixmap
            rect = scene.sceneRect()
            pixmap = QPixmap(int(rect.width()), int(rect.height()))
            pixmap.fill()
            painter = QPainter(pixmap)
            scene.render(painter)
            painter.end()
            return pixmap.save(filepath)
        except Exception as e:
            print(f"Ошибка экспорта: {e}")
            return False

    def add_task(self, project_id: int, title: str, start_date: datetime, end_date: datetime,
                 assigned_to: int = None) -> Optional[int]:
        """Создает новую задачу"""
        try:
            new_task = Task(
                project_id=project_id,
                title=title,
                description="",
                deadline=end_date,
                created_at=start_date,
                created_by=self.current_user_id,
                assigned_to=assigned_to,
                priority="medium",
                position=0
            )
            self.session.add(new_task)
            self.session.commit()
            return new_task.id
        except Exception as e:
            self.session.rollback()
            print(f"Ошибка создания задачи: {e}")
            return None

    def add_dependency(self, predecessor_id: int, successor_id: int, lag: int = 0, dep_type: str = "FS") -> bool:
        """Добавляет связь между задачами"""
        try:
            # Проверяем, существует ли уже такая связь
            existing = self.session.query(TaskDependency).filter(
                TaskDependency.predecessor_id == predecessor_id,
                TaskDependency.successor_id == successor_id
            ).first()

            if existing:
                print(f"⚠️ Связь между задачами {predecessor_id} и {successor_id} уже существует")
                return False

            dependency = TaskDependency(
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                lag=lag,
                type=dep_type
            )
            self.session.add(dependency)
            self.session.commit()
            print(f"✅ Связь создана: {predecessor_id} → {successor_id} (лаг: {lag}, тип: {dep_type})")
            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка создания связи: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_task_dependencies(self, task_id: int) -> List[Dict]:
        """Получает все связи для задачи"""
        deps = self.session.query(TaskDependency).filter(
            TaskDependency.predecessor_id == task_id
        ).all()

        return [{
            "successor_id": d.successor_id,
            "lag": d.lag,
            "type": d.type
        } for d in deps]

    def update_task_dates(self, task_id: int, start_date: datetime.date, end_date: datetime.date) -> bool:
        """Обновляет даты начала и окончания задачи"""
        try:
            print(f"🔄 update_task_dates: task_id={task_id}, start={start_date}, end={end_date}")
            task = self.session.get(Task, task_id)
            if task:
                print(f"   Задача найдена: {task.title}")
                task.created_at = datetime.combine(start_date, datetime.min.time())
                task.deadline = datetime.combine(end_date, datetime.min.time())
                self.session.commit()
                print(f"✅ Задача {task_id}: даты обновлены на {start_date} - {end_date}")
                return True
            else:
                print(f"❌ Задача {task_id} не найдена!")
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка обновления дат задачи {task_id}: {e}")
            import traceback
            traceback.print_exc()
        return False

    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        task = self.session.get(Task, task_id)
        if not task:
            return None
        return {
            "id": task.id,
            "title": task.title,
            "start_date": task.created_at.date() if task.created_at else datetime.now().date(),
            "end_date": task.deadline.date() if task.deadline else datetime.now().date() + timedelta(days=7),
            "assignee": self._get_employee_name(task.assigned_to) if task.assigned_to else "",
            "assignee_id": task.assigned_to
        }

    def get_current_user_id(self) -> Optional[int]:
        return self.current_user_id