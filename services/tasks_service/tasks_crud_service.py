# services/tasks_service/tasks_crud_service.py

from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models.projects import Project, BoardColumn
from models.schemas.tasks_dto import TaskPriority
from models.tasks import Task
from repositories.task_repo import TaskRepo
from services.employee_service.column_service import ColumnService


class TasksCrudService:
    """Базовый CRUD сервис для задач"""

    def __init__(self, db_session: Session, current_user: Dict = None, mode: str = "all", column_service: ColumnService = None):
        self.db_session = db_session
        self.repo = TaskRepo(db_session)
        self.current_user = current_user
        self.mode = mode
        self._column_service = column_service

    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        """Получить задачу по ID"""
        task_orm = self.repo.get_by_id(task_id)
        return self._task_to_dict(task_orm) if task_orm else None

    def get_projects_for_filter(self, user_id: int) -> List[Dict]:
        """Загружает проекты для фильтра (только где пользователь участник/админ/куратор/создатель)"""
        from sqlalchemy import select
        from models.projects import Project, EmployeeProject

        try:
            stmt = select(Project).where(
                (Project.is_archived == False) & (
                        (Project.id.in_(
                            select(EmployeeProject.project_id).where(EmployeeProject.employee_id == user_id)
                        )) |
                        (Project.created_by == user_id)
                )
            ).order_by(Project.name)

            projects = self.db_session.scalars(stmt).all()
            return [{"id": p.id, "name": p.name} for p in projects]
        except Exception as e:
            print(f"⚠️ Ошибка загрузки проектов для фильтра: {e}")
            return []

    def get_project_columns(self, project_id: int) -> List[Dict]:
        """Получает колонки проекта по его ID"""
        from models.projects import BoardColumn
        from sqlalchemy import select

        try:
            # Получаем проект
            stmt = select(Project).where(Project.id == project_id)
            project = self.db_session.scalar(stmt)

            column_ids = []
            if project and project.selected_column_ids:
                ids_str = project.selected_column_ids
                if ids_str:
                    column_ids = [int(id_str.strip()) for id_str in ids_str.split(',') if id_str.strip()]

            if not column_ids:
                stmt = select(BoardColumn).order_by(BoardColumn.position)
                columns = self.db_session.scalars(stmt).all()
            else:
                stmt = select(BoardColumn).where(BoardColumn.id.in_(column_ids)).order_by(BoardColumn.position)
                columns = self.db_session.scalars(stmt).all()

            return [
                {
                    "id": col.id,
                    "name": col.name,
                    "color": col.color,
                    "position": col.position,
                    "is_done": col.is_done_column
                }
                for col in columns
            ]
        except Exception as e:
            print(f"⚠️ Ошибка получения колонок проекта {project_id}: {e}")
            return []

    def get_tasks_for_project_filter(self, tasks: List[Dict], project_id: int) -> List[Dict]:
        """Фильтрует задачи по проекту"""
        if not project_id:
            return tasks
        return [t for t in tasks if t.get("project_id") == project_id]

    def get_task_statistics(self, tasks: List[Dict]) -> Dict:
        """Рассчитывает статистику по задачам"""
        total = len(tasks)

        in_progress = sum(1 for t in tasks if not t.get("completed", False))

        overdue = 0
        today = datetime.now().date()
        for task in tasks:
            deadline_str = task.get("deadline")
            if deadline_str and not task.get("completed", False):
                try:
                    deadline_date = datetime.strptime(deadline_str, "%d.%m.%Y").date()
                    if deadline_date < today:
                        overdue += 1
                except (ValueError, TypeError):
                    pass

        avg_progress = int(sum(t.get("progress_percent", 0) for t in tasks) / total) if total > 0 else 0

        return {
            "total": total,
            "in_progress": in_progress,
            "overdue": overdue,
            "avg_progress": avg_progress
        }

    def get_column_tasks_count(self, column_name: str, tasks: List[Dict]) -> int:
        """Возвращает количество задач в колонке"""
        return sum(1 for t in tasks if t.get("status") == column_name)

    def get_tasks_by_ids(self, task_ids: List[int]) -> List[Dict]:
        """Получить задачи по списку ID"""
        if not task_ids:
            return []
        stmt = select(Task).where(Task.id.in_(task_ids))
        tasks = self.db_session.scalars(stmt).all()
        return [self._task_to_dict(task) for task in tasks]

    def get_projects_for_filter_others(self, user_id: int) -> List[Dict]:
        """Загружает проекты для фильтра (чужие задачи)"""
        from sqlalchemy import select
        from models.projects import Project, EmployeeProject

        try:
            # Для чужих задач показываем все проекты, где пользователь НЕ является создателем
            stmt = select(Project).where(
                Project.is_archived == False,
                Project.created_by != user_id
            ).order_by(Project.name)

            projects = self.db_session.scalars(stmt).all()
            return [{"id": p.id, "name": p.name} for p in projects]
        except Exception as e:
            print(f"⚠️ Ошибка загрузки проектов для фильтра (чужие): {e}")
            return []

    def filter_tasks_by_priority_and_project_ids(
            self,
            tasks: List[Dict],
            priority: str,
            project_id: Optional[int]
    ) -> set:
        """Возвращает множество ID отфильтрованных задач"""
        filtered = tasks
        if priority and priority != "Все приоритеты":
            priority_map = {"Низкий": "low", "Средний": "medium", "Высокий": "high", "Критический": "critical"}
            target_priority = priority_map.get(priority, priority.lower())
            filtered = [t for t in filtered if t.get("priority") == target_priority]
        if project_id:
            filtered = [t for t in filtered if t.get("project_id") == project_id]
        return {t["id"] for t in filtered}

    def get_tasks_for_project_filter_others(
            self,
            all_tasks: List[Dict],
            project_id: Optional[int],
            user_id: int
    ) -> List[Dict]:
        """Фильтрует задачи для чужих задач"""
        filtered = all_tasks

        # Исключаем задачи, где пользователь является исполнителем
        filtered = [t for t in filtered if t.get("assigned_to") != user_id]

        if project_id:
            filtered = [t for t in filtered if t.get("project_id") == project_id]

        return filtered

    def get_project_columns_by_ids(self, project_id: int) -> List[Dict]:
        """Получает колонки проекта по его ID (с fallback на все колонки)"""
        from models.projects import BoardColumn
        from sqlalchemy import select

        try:
            stmt = select(Project).where(Project.id == project_id)
            project = self.db_session.scalar(stmt)

            column_ids = []
            if project and project.selected_column_ids:
                ids_str = project.selected_column_ids
                if ids_str:
                    column_ids = [int(id_str.strip()) for id_str in ids_str.split(',') if id_str.strip()]

            if not column_ids:
                # ✅ ИСПРАВЛЕНО: берем все колонки, сортируем по position
                stmt = select(BoardColumn).order_by(BoardColumn.position)
                columns = self.db_session.scalars(stmt).all()
            else:
                stmt = select(BoardColumn).where(BoardColumn.id.in_(column_ids)).order_by(BoardColumn.position)
                columns = self.db_session.scalars(stmt).all()

            return [
                {
                    "id": col.id,
                    "name": col.name,
                    "color": col.color,
                    "position": col.position,
                    "is_done": col.is_done_column
                }
                for col in columns
            ]
        except Exception as e:
            print(f"⚠️ Ошибка получения колонок проекта {project_id}: {e}")
            return []

    def get_task_statistics_others(self, tasks: List[Dict]) -> Dict:
        """Рассчитывает статистику для чужих задач"""
        total = len(tasks)

        in_progress = 0
        done_columns = ["Готово", "Done", "Выполнено"]
        for task in tasks:
            status = task.get("status", "")
            completed = task.get("completed", False)
            if status not in done_columns and not completed:
                in_progress += 1

        overdue = 0
        today = datetime.now().date()
        for task in tasks:
            deadline_str = task.get("deadline")
            completed = task.get("completed", False)
            if deadline_str and not completed:
                try:
                    deadline_date = datetime.strptime(deadline_str, "%d.%m.%Y").date()
                    if deadline_date < today:
                        overdue += 1
                except (ValueError, TypeError):
                    pass

        avg_progress = int(sum(t.get("progress_percent", 0) for t in tasks) / total) if total > 0 else 0

        return {
            "total": total,
            "in_progress": in_progress,
            "overdue": overdue,
            "avg_progress": avg_progress
        }

    def update_task_card_data(self, task_id: int, updated_task: Dict) -> Dict:
        """Обновляет данные карточки задачи"""
        return self._task_to_dict(updated_task)

    def has_task_in_ui(self, tasks: List[Dict], task_id: int) -> bool:
        """Проверяет, есть ли задача в списке"""
        return any(t.get("id") == task_id for t in tasks)

    def create_task(self, data: Dict) -> Dict:
        """Создать новую задачу"""
        column = self._get_column_by_name(data.get("status"))
        if not column:
            column = self._get_first_column(data.get("project_id"))

        if not column:
            raise ValueError(f"Не найдена колонка '{data.get('status')}'")

        priority_map = {
            "Низкий": "low",
            "Средний": "medium",
            "Высокий": "high",
            "Критический": "critical"
        }

        priority_value = data.get("priority", "Средний")
        priority_enum = TaskPriority(priority_map.get(priority_value, "medium"))

        task_data = {
            "project_id": data.get("project_id"),
            "column_id": column.id,
            "title": data["title"],
            "description": data.get("description"),
            "priority": priority_enum,
            "deadline": self._parse_date(data.get("deadline")),
            "created_by": data.get("created_by"),
            "assigned_to": data.get("assigned_to"),
            "difficulty": float(data.get("difficulty", 0)),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        if "position" not in task_data:
            max_pos = self.db_session.scalar(
                select(func.max(Task.position)).where(Task.column_id == column.id)
            )
            task_data["position"] = (max_pos or 0) + 1

        try:
            new_task = self.repo.create(**task_data)
            self.db_session.commit()

            # === СОХРАНЯЕМ ТЕГИ ===
            tags = data.get("tags", [])
            if tags:
                print(f"🏷️ Сохраняем теги для задачи {new_task.id}: {tags}")
                from services.tasks_service.tasks_tag_service import TasksTagService
                tag_service = TasksTagService(self.db_session, self.repo)
                tag_service.set_task_tags(new_task.id, tags)
                self.db_session.commit()
                print(f"   ✅ Теги сохранены")

            return self._task_to_dict(new_task)
        except Exception as e:
            self.db_session.rollback()
            raise

    def update_task_progress(self, task_id: int, progress_percent: float) -> Optional[Dict]:
        """Обновить прогресс выполнения задачи"""
        print(f"\n🔍 [DEBUG] update_task_progress: начало")
        print(f"   - task_id: {task_id}")
        print(f"   - progress_percent: {progress_percent}")

        task = self.repo.update_progress(task_id, progress_percent)
        if task:
            self.db_session.commit()
            print(f"   - транзакция закоммичена")
            # Обновляем КПД сотрудника если задача завершена
            if progress_percent >= 100 and task.assigned_to:
                print(f"   - задача завершена, обновляем КПД сотрудника {task.assigned_to}")
                self._update_employee_kpd(task.assigned_to)

            result = self._task_to_dict(task)
            print(f"   - результат преобразован в dict")
            print(f"🔍 [DEBUG] update_task_progress: конец, возвращаем dict\n")
            return result

        print(f"🔍 [DEBUG] update_task_progress: конец, задача не найдена\n")
        return None

    def start_task(self, task_id: int) -> Optional[Dict]:
        """Начать выполнение задачи"""
        task = self.repo.start_task(task_id)
        if task:
            self.db_session.commit()
            return self._task_to_dict(task)
        return None

    def complete_task(self, task_id: int, actual_hours: float = None) -> Optional[Dict]:
        """Завершить задачу"""
        task = self.repo.complete_task(task_id, actual_hours)
        if task:
            self.db_session.commit()
            # Обновляем КПД сотрудника
            if task.assigned_to:
                self._update_employee_kpd(task.assigned_to)
            return self._task_to_dict(task)
        return None

    def _update_employee_kpd(self, employee_id: int) -> None:
        """Обновить КПД сотрудника"""
        try:
            from models.employees import EmployeeData
            employee_data = self.db_session.query(EmployeeData).filter(
                EmployeeData.employee_id == employee_id
            ).first()
            if employee_data:
                employee_data.update_kpd(self.db_session)
                self.db_session.commit()
        except Exception as e:
            print(f"⚠️ Ошибка обновления КПД сотрудника {employee_id}: {e}")

    def get_task_kpd_info(self, task_id: int) -> Optional[Dict]:
        """Получить информацию о КПД задачи"""
        task = self.repo.get_by_id(task_id)
        if not task:
            return None

        return {
            "task_id": task.id,
            "title": task.title,
            "kpd_score": task.kpd_score,
            "difficulty": task.difficulty,
            "priority": task.priority.value,
            "priority_factor": task.priority_factor,
            "efficiency_factor": task.efficiency_factor,
            "progress_percent": task.progress_percent,
            "completed": task.completed,
            "completed_at": task.completed_at.strftime("%d.%m.%Y %H:%M") if task.completed_at else None,
            "deadline": task.deadline.strftime("%d.%m.%Y") if task.deadline else None,
            "planned_hours": task.planned_hours,
            "actual_hours": task.actual_hours
        }

    def update_task(self, task_id: int, updated_data: Dict) -> Optional[Dict]:
        """Обновить задачу"""
        task = self.repo.get_by_id(task_id)
        if not task:
            return None

        # === НОВЫЙ КОД: Обработка изменения статуса ===
        if "status" in updated_data:
            new_status_name = updated_data["status"]
            # Находим колонку по имени
            column = self._get_column_by_name(new_status_name, task.project_id)
            if column and task.column_id != column.id:
                print(f"🔄 Изменение статуса в БД: {task.column.name if task.column else 'None'} -> {new_status_name}")
                task.column_id = column.id

                # Если перемещаем в Done колонку - устанавливаем прогресс 100%
                if column.is_done_column:
                    task.progress_percent = 100.0
                    task.completed_at = datetime.now()
                    task.completed = True
                elif task.column and task.column.is_done_column:
                    # Если убираем из Done колонки
                    task.completed_at = None
                    task.completed = False

        if "title" in updated_data:
            task.title = updated_data["title"]
        if "description" in updated_data:
            task.description = updated_data.get("description")
        if "priority" in updated_data:
            priority_value = updated_data["priority"]
            priority_map = {
                "Низкий": TaskPriority.low,
                "Средний": TaskPriority.medium,
                "Высокий": TaskPriority.high,
                "Критический": TaskPriority.critical
            }
            task.priority = priority_map.get(priority_value, TaskPriority.medium)
        if "deadline" in updated_data:
            task.deadline = self._parse_date(updated_data["deadline"])
        if "assigned_to" in updated_data:
            task.assigned_to = updated_data["assigned_to"]
        if "difficulty" in updated_data:
            task.difficulty = float(updated_data["difficulty"])

        task.updated_at = datetime.now()
        self.db_session.commit()

        # === ОБНОВЛЯЕМ ТЕГИ ===
        tags = updated_data.get("tags")
        if tags is not None:
            print(f"🏷️ Обновляем теги для задачи {task_id}: {tags}")
            from services.tasks_service.tasks_tag_service import TasksTagService
            tag_service = TasksTagService(self.db_session, self.repo)
            tag_service.set_task_tags(task_id, tags)
            self.db_session.commit()
            print(f"   ✅ Теги обновлены")

        return self._task_to_dict(task)

    def format_assignee_name(self, assignee_id: Optional[int]) -> str:
        """Форматирует имя исполнителя"""
        if not assignee_id:
            return ""

        from database import get_employees_session
        from models.employees import Employee

        employees_session = get_employees_session()
        if employees_session:
            try:
                employee = employees_session.get(Employee, assignee_id)
                if employee:
                    first_initial = f"{employee.first_name[0]}." if employee.first_name else ""
                    middle_initial = f"{employee.middle_name[0]}." if employee.middle_name else ""
                    return f"{employee.last_name} {first_initial}{middle_initial}".strip()
            finally:
                employees_session.close()

        return "Неизвестен"

    def prepare_dialog_data(self, mode: str, task_data: Optional[Dict] = None) -> Dict:
        """Подготавливает данные для диалога создания/редактирования задачи"""
        from models.tasks import Tag
        from database import get_employees_session
        from models.employees import Employee

        result = {
            "projects": [],
            "statuses": [],
            "employees": [],
            "tags": []
        }

        # Получаем проекты (из taskplanner)
        stmt = select(Project).where(Project.is_archived == False)
        projects = self.db_session.scalars(stmt).all()
        result["projects"] = [{"id": p.id, "name": p.name} for p in projects]

        # Получаем статусы (колонки)
        stmt = select(BoardColumn).order_by(BoardColumn.position)
        columns = self.db_session.scalars(stmt).all()
        seen_statuses = set()
        for col in columns:
            if col.name not in seen_statuses:
                seen_statuses.add(col.name)
                result["statuses"].append({"id": col.id, "name": col.name})

        # Получаем сотрудников из БД employees
        employees_session = get_employees_session()
        if employees_session:
            try:
                stmt = select(Employee).order_by(Employee.last_name)
                employees = employees_session.scalars(stmt).all()
                for emp in employees:
                    first_initial = f"{emp.first_name[0]}." if emp.first_name else ""
                    middle_initial = f"{emp.middle_name[0]}." if emp.middle_name else ""
                    display_name = f"{emp.last_name} {first_initial}{middle_initial}".strip()
                    result["employees"].append({
                        "id": emp.id,
                        "display_name": display_name,
                        "last_name": emp.last_name,
                        "first_name": emp.first_name,
                        "middle_name": emp.middle_name
                    })
            finally:
                employees_session.close()
        else:
            print("⚠️ Нет подключения к базе employees")

        # ✅ ИСПРАВЛЕНО: убираем фильтр is_archived
        stmt = select(Tag).order_by(Tag.name)  # <-- убрали .where(Tag.is_archived == False)
        tags = self.db_session.scalars(stmt).all()
        result["tags"] = [{"id": t.id, "name": t.name, "color": t.color} for t in tags]

        # Если режим редактирования, добавляем данные задачи
        if mode == "edit" and task_data:
            result["task_data"] = task_data

        return result

    def validate_form_data(self, form_data: Dict) -> Optional[str]:
        """Валидация данных формы"""
        if not form_data.get("title"):
            return "Введите название задачи"
        if not form_data.get("project_id"):
            return "Выберите проект"
        return None

    def process_form_data(self, form_data: Dict, current_user: Dict) -> Dict:
        """Обработка данных формы перед сохранением"""
        processed = {
            "title": form_data.get("title", ""),
            "description": form_data.get("description", ""),
            "project_id": form_data.get("project_id"),
            "assigned_to": form_data.get("assigned_to"),
            "priority": form_data.get("priority", "Средний"),
            "status": form_data.get("status", "К выполнению"),
            "difficulty": form_data.get("difficulty", 0),
            "tags": form_data.get("tags", [])
        }

        # Обработка дедлайна
        due_date = form_data.get("due_date")
        if due_date:
            processed["deadline"] = due_date

        # Для создания добавляем created_by
        if "created_by" not in form_data:
            processed["created_by"] = current_user.get("id")

        return processed

    def get_tasks_for_board(self) -> List[Dict]:
        """Получить задачи для доски с учётом режима"""
        return self.load_tasks()

    def _get_employee_name(self, employee_id: Optional[int]) -> Optional[str]:
        """Получить имя сотрудника из БД employees"""
        if not employee_id:
            return None

        from database import get_employees_session
        from models.employees import Employee

        employees_session = get_employees_session()
        if employees_session:
            try:
                employee = employees_session.get(Employee, employee_id)
                if employee:
                    first_initial = f"{employee.first_name[0]}." if employee.first_name else ""
                    middle_initial = f"{employee.middle_name[0]}." if employee.middle_name else ""
                    return f"{employee.last_name} {first_initial}{middle_initial}".strip()
            except Exception as e:
                print(f"⚠️ Ошибка получения имени сотрудника {employee_id}: {e}")
            finally:
                employees_session.close()

        return None

    def load_tasks(self) -> List[Dict]:
        """Загрузить задачи с фильтрацией по режиму и архиву"""
        user_id = self.current_user.get("id") if self.current_user else None

        print(f"\n🔍 [DEBUG] load_tasks: mode={self.mode}, user_id={user_id}")

        # ВАЖНО: фильтруем только НЕархивированные задачи
        stmt = select(Task).where(Task.is_archived == False)
        all_tasks = list(self.db_session.scalars(stmt))

        print(f"🔍 [DEBUG] Всего неархивированных задач в БД: {len(all_tasks)}")

        filtered_tasks = []
        for task in all_tasks:
            include = False

            # Для режима "my" - задачи, где пользователь является ИСПОЛНИТЕЛЕМ
            if self.mode == "my":
                if task.assigned_to == user_id:
                    include = True

            # Для режима "others" - задачи, где пользователь НЕ является исполнителем
            elif self.mode == "others":
                if task.assigned_to != user_id:
                    include = True

            # Для режима "all" - все задачи
            else:
                include = True

            if include:
                filtered_tasks.append(task)

        return [self._task_to_dict(task) for task in filtered_tasks]

    def is_deadline_overdue(self, deadline_str: str, completed: bool) -> bool:
        """Проверить, просрочен ли дедлайн"""
        if not deadline_str or completed:
            return False
        try:
            from datetime import datetime
            deadline_date = datetime.strptime(deadline_str, "%d.%m.%Y").date()
            return deadline_date < datetime.now().date()
        except (ValueError, TypeError):
            return False

    def get_columns_for_board(self) -> List[Dict]:
        """Получить колонки для доски"""
        return self.get_all_columns()

    def get_all_columns(self) -> List[Dict]:
        """Получить все уникальные колонки"""
        print(f"🔍 get_all_columns: mode={self.mode}, вызывается...")

        columns_by_name = {}

        stmt = select(BoardColumn).order_by(BoardColumn.position)
        all_columns = self.db_session.scalars(stmt).all()

        for col in all_columns:
            if col.name not in columns_by_name:
                columns_by_name[col.name] = {
                    "id": col.id,
                    "name": col.name,
                    "color": col.color if col.color else "#2196F3",
                    "position": col.position,
                    "is_done": col.is_done_column
                }

        result = sorted(columns_by_name.values(), key=lambda x: x["position"])

        for col in result:
            print(f"  - {col['name']} (позиция: {col['position']})")

        return result

    def get_column_data(self) -> List[Dict]:
        """Получить данные колонок для UI (адаптер)"""
        return self.get_all_columns()

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Преобразование задачи в словарь"""
        assignee_name = self._get_employee_name(task.assigned_to)
        creator_name = self._get_employee_name(task.created_by)

        project_name = "Неизвестно"
        if task.project_id:
            project = self.db_session.get(Project, task.project_id)
            if project:
                project_name = project.name

        priority_map = {
            TaskPriority.low: ("Низкий", "#4CAF50"),
            TaskPriority.medium: ("Средний", "#FFA726"),
            TaskPriority.high: ("Высокий", "#D22730"),
            TaskPriority.critical: ("Критический", "#D22730")
        }

        priority_text, priority_color = priority_map.get(
            task.priority,
            ("Средний", "#FFA726")
        )

        deadline_text = ""
        deadline_color = "#666"
        if task.deadline:
            deadline_text = task.deadline.strftime("%d.%m.%Y")
            if task.deadline.date() < datetime.now().date():
                deadline_color = "#D22730"

        created_display = ""
        if task.created_at:
            created_display = task.created_at.strftime("%d.%m.%Y %H:%M")

        updated_display = ""
        if task.updated_at:
            updated_display = task.updated_at.strftime("%d.%m.%Y %H:%M")

        author_display = ""
        if creator_name:
            author_display = creator_name

        executor_display = ""
        if assignee_name:
            executor_display = assignee_name

        # === ЗАГРУЖАЕМ ТЕГИ ===
        tag_names = []
        try:
            from models.tasks import Tag
            # Получаем теги через связь task.tags
            if task.tags:
                for task_tag in task.tags:
                    if task_tag.tag:
                        tag_names.append(task_tag.tag.name)
        except Exception as e:
            print(f"⚠️ Ошибка загрузки тегов: {e}")

        return {
            "id": task.id,
            "project_id": task.project_id,
            "project_name": project_name,
            "title": task.title,
            "description": task.description or "",
            "position": task.position,
            "priority": task.priority.value,
            "priority_text": priority_text,
            "priority_color": priority_color,
            "difficulty": float(task.difficulty) if task.difficulty else 0,
            "progress_percent": float(task.progress_percent) if task.progress_percent else 0,
            "completed_at": task.completed_at.strftime("%d.%m.%Y") if task.completed_at else None,
            "started_at": task.started_at.strftime("%d.%m.%Y") if task.started_at else None,
            "actual_hours": float(task.actual_hours) if task.actual_hours else 0,
            "deadline": task.deadline.strftime("%d.%m.%Y") if task.deadline else "",
            "deadline_text": deadline_text,
            "deadline_color": deadline_color,
            "created_by": task.created_by,
            "created_by_name": creator_name,
            "assigned_to": task.assigned_to,
            "assignee_name": assignee_name,
            "created_at": created_display,
            "updated_at": updated_display,
            "created_text": created_display,
            "updated_text": updated_display,
            "author_text": author_display,
            "is_paused": task.is_paused,
            "total_paused_seconds": task.total_paused_seconds,
            "executor_text": executor_display,
            "status": task.column.name if task.column else None,
            "completed": task.completed,
            "column_id": task.column_id,
            "tags": tag_names  # <-- ТЕПЕРЬ ТЕГИ ВОЗВРАЩАЮТСЯ
        }

    def _get_column_by_name(self, column_name: str, project_id: int = None) -> Optional[BoardColumn]:
        """Получить колонку по имени"""
        if not column_name:
            return None

        if project_id:
            stmt = select(BoardColumn).where(
                BoardColumn.name == column_name,
                BoardColumn.project_id == project_id
            )
            column = self.db_session.scalar(stmt)
            if column:
                print(f"   ✅ Найдена колонка проекта '{column_name}' с id={column.id}")
                return column

        # Если не нашли в проекте, ищем любую колонку с таким именем
        stmt = select(BoardColumn).where(BoardColumn.name == column_name)
        column = self.db_session.scalar(stmt)
        if column:
            print(f"   ✅ Найдена колонка '{column_name}' с id={column.id}")
            return column

        print(f"   ❌ Колонка '{column_name}' не найдена!")
        return None

    def _get_first_column(self, project_id: int) -> Optional[BoardColumn]:
        """Получить первую колонку проекта"""
        stmt = select(BoardColumn).where(
            BoardColumn.project_id == project_id
        ).order_by(BoardColumn.position)
        return self.db_session.scalar(stmt)

    def pause_task(self, task_id: int) -> Optional[Dict]:
        """Поставить задачу на паузу"""
        task = self.repo.pause_task(task_id)
        if task:
            self.db_session.commit()
            return self._task_to_dict(task)
        return None

    def resume_task(self, task_id: int) -> Optional[Dict]:
        """Возобновить задачу"""
        task = self.repo.resume_task(task_id)
        if task:
            self.db_session.commit()
            return self._task_to_dict(task)
        return None

    def duplicate_task(self, task_id: int) -> Optional[Dict]:
        """Дублировать задачу - создаёт точную копию в той же колонке"""
        original = self.repo.get_by_id(task_id)
        if not original:
            return None

        # Создаём копию задачи
        new_task_data = {
            "project_id": original.project_id,
            "column_id": original.column_id,
            "title": f"{original.title} (копия)",
            "description": original.description,
            "priority": original.priority,
            "deadline": original.deadline,
            "created_by": original.created_by,
            "assigned_to": original.assigned_to,
            "difficulty": original.difficulty,
            "progress_percent": 0,  # Копия начинается с 0%
            "is_archived": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # Находим максимальную позицию в той же колонке
        max_pos = self.db_session.scalar(
            select(func.max(Task.position)).where(Task.column_id == original.column_id)
        )
        new_task_data["position"] = (max_pos or 0) + 1

        new_task = self.repo.create(**new_task_data)
        self.db_session.commit()

        # Копируем теги
        from models.tasks import TaskTag
        for tag in original.tags:
            new_task_tag = TaskTag(task_id=new_task.id, tag_id=tag.tag_id)
            self.db_session.add(new_task_tag)

        self.db_session.commit()
        print(f"📋 Задача {task_id} дублирована -> новая задача {new_task.id}")

        return self._task_to_dict(new_task)

    def archive_task(self, task_id: int) -> bool:
        """Архивировать задачу"""
        task = self.repo.get_by_id(task_id)
        if not task:
            return False
        task.is_archived = True
        task.archived_at = datetime.now()
        self.db_session.commit()
        print(f"📦 Задача {task_id} архивирована")
        return True

    def delete_task(self, task_id: int) -> bool:
        """Полное удаление задачи из БД"""
        try:
            # Сначала удаляем связи с тегами
            from models.tasks import TaskTag
            self.db_session.query(TaskTag).filter(TaskTag.task_id == task_id).delete()

            # Затем удаляем саму задачу
            task = self.repo.get_by_id(task_id)
            if task:
                self.db_session.delete(task)
                self.db_session.commit()
                print(f"🗑️ Задача {task_id} полностью удалена из БД")
                return True
            return False
        except Exception as e:
            self.db_session.rollback()
            print(f"❌ Ошибка удаления задачи: {e}")
            return False

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Парсинг даты"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    def get_tasks_for_user(self, user_id: int, project_id: int, permission_service=None) -> List[Dict]:
        """
        Получает задачи для пользователя с учетом прав
        """
        # Получаем все задачи проекта
        all_tasks = self.get_by_project(project_id, load_column=True)

        if not permission_service:
            return all_tasks

        # Определяем фильтр видимости
        visibility_filter = permission_service.get_task_visibility_filter(project_id)

        if visibility_filter == 'all':
            # Руководитель/куратор - видят все задачи
            return all_tasks
        else:
            # Участник - видит только свои задачи
            return [task for task in all_tasks if task.get('created_by') == user_id]