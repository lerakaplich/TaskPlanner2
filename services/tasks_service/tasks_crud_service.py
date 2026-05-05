# services/tasks_service/tasks_crud_service.py

from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models.projects import BoardColumn, Project
from models.schemas.tasks_dto import TaskPriority
from models.tasks import Task
from repositories.task_repo import TaskRepo


class TasksCrudService:
    """Базовый CRUD сервис для задач"""

    def __init__(self, db_session: Session, current_user: Dict = None, mode: str = "all"):
        self.db_session = db_session
        self.repo = TaskRepo(db_session)
        self.current_user = current_user
        self.mode = mode

    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        """Получить задачу по ID"""
        task_orm = self.repo.get_by_id(task_id)
        return self._task_to_dict(task_orm) if task_orm else None

    def get_tasks_by_ids(self, task_ids: List[int]) -> List[Dict]:
        """Получить задачи по списку ID"""
        if not task_ids:
            return []
        stmt = select(Task).where(Task.id.in_(task_ids))
        tasks = self.db_session.scalars(stmt).all()
        return [self._task_to_dict(task) for task in tasks]

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
            return self._task_to_dict(new_task)
        except Exception as e:
            self.db_session.rollback()
            raise

    def update_task(self, task_id: int, updated_data: Dict) -> Optional[Dict]:
        """Обновить задачу"""
        task = self.repo.get_by_id(task_id)
        if not task:
            return None

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

        return self._task_to_dict(task)

    def delete_task(self, task_id: int) -> bool:
        """Удалить задачу"""
        try:
            self.repo.delete(task_id)
            self.db_session.commit()
            return True
        except Exception as e:
            self.db_session.rollback()
            print(f"❌ Ошибка удаления задачи: {e}")
            return False

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

    def archive_task(self, task_id: int) -> bool:
        """Архивировать задачу"""
        task = self.repo.get_by_id(task_id)
        if not task:
            return False
        task.is_archived = True
        task.archived_at = datetime.now()
        self.db_session.commit()
        return True

    def prepare_dialog_data(self, mode: str, task_data: Optional[Dict] = None) -> Dict:
        """Подготавливает данные для диалога создания/редактирования задачи"""
        from models.projects import BoardColumn, Project
        from models.tasks import Tag
        from database import get_employees_session
        from models.employees import Employee  # из models/employees.py

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

        # Получаем сотрудников из БД employees (без фильтрации по is_active)
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

        # Получаем теги (из taskplanner)
        stmt = select(Tag).where(Tag.is_archived == False).order_by(Tag.name)
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

    def duplicate_task(self, task_id: int) -> Optional[Dict]:
        """Дублировать задачу"""
        original = self.repo.get_by_id(task_id)
        if not original:
            return None

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
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        max_pos = self.db_session.scalar(
            select(func.max(Task.position)).where(Task.column_id == original.column_id)
        )
        new_task_data["position"] = (max_pos or 0) + 1

        new_task = self.repo.create(**new_task_data)
        self.db_session.commit()
        return self._task_to_dict(new_task)

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
            finally:
                employees_session.close()

        return None

    def load_tasks(self) -> List[Dict]:
        """Загрузить задачи с фильтрацией по режиму"""
        user_id = self.current_user.get("id") if self.current_user else None

        stmt = select(Task)
        all_tasks = list(self.db_session.scalars(stmt))

        filtered_tasks = []
        for task in all_tasks:
            if self.mode == "my":
                if task.assigned_to == user_id or task.created_by == user_id:
                    filtered_tasks.append(task)
            elif self.mode == "others":
                if task.assigned_to != user_id and task.created_by != user_id:
                    filtered_tasks.append(task)
            else:
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
        stmt = select(BoardColumn).order_by(BoardColumn.project_id, BoardColumn.position)
        all_columns = list(self.db_session.scalars(stmt))

        columns_by_name = {}
        for col in all_columns:
            if col.name not in columns_by_name:
                columns_by_name[col.name] = {
                    "id": col.id,
                    "name": col.name,
                    "color": col.color if col.color else "#2196F3",
                    "position": col.position,
                    "is_done": col.is_done_column,
                    "project_ids": []
                }
            columns_by_name[col.name]["project_ids"].append(col.project_id)

        return sorted(columns_by_name.values(), key=lambda x: x["position"])

    def get_column_data(self) -> List[Dict]:
        """Получить данные колонок для UI"""
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
            "executor_text": executor_display,
            "status": task.column.name if task.column else None,
            "completed": task.completed,
            "column_id": task.column_id,
            "tags": []
        }

    def _get_column_by_name(self, column_name: str, project_id: int = None) -> Optional[BoardColumn]:
        """Получить колонку по имени"""
        stmt = select(BoardColumn).where(BoardColumn.name == column_name)
        if project_id:
            stmt = stmt.where(BoardColumn.project_id == project_id)
        return self.db_session.scalar(stmt)

    def _get_first_column(self, project_id: int) -> Optional[BoardColumn]:
        """Получить первую колонку проекта"""
        stmt = select(BoardColumn).where(
            BoardColumn.project_id == project_id
        ).order_by(BoardColumn.position)
        return self.db_session.scalar(stmt)

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Парсинг даты"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return None