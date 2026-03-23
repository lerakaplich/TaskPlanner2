# services/tasks_service.py

# services/tasks_service.py

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func

# Импортируем репозиторий
from repositories.task_repo import TaskRepo
from models.projects import BoardColumn, Project
from models.tasks import Task
from models.schemas.tasks_dto import TaskPriority


class TasksService:
    """
    Сервис для работы с задачами.
    Поддерживает фильтрацию по пользователю и режимы:
    - "my" - задачи текущего пользователя из всех проектов
    - "others" - задачи других пользователей из всех проектов
    - "all" - все задачи
    """

    def __init__(self, db_session: Session, current_user: Dict = None, mode: str = "all"):
        self.db_session = db_session
        self.repo = TaskRepo(db_session)
        self.current_user = current_user
        self.mode = mode  # my | others | all

    # =====================================================
    # Загрузка задач из всех проектов
    # =====================================================

    # services/tasks_service.py - исправленная фильтрация

    def load_tasks(self) -> List[Dict]:
        """Загружает задачи из ВСЕХ проектов с учетом режима."""
        print(f"\n=== ОТЛАДКА: load_tasks (mode={self.mode}) ===")

        user_id = self.current_user.get("id") if self.current_user else None
        print(f"Текущий пользователь ID: {user_id}")

        # Получаем ВСЕ задачи из БД (без фильтра по проекту)
        stmt = select(Task).options(
            # Загружаем связанные данные для оптимизации
        )
        all_tasks = list(self.db_session.scalars(stmt))
        print(f"Всего задач в БД: {len(all_tasks)}")

        # Фильтруем по режиму
        filtered_tasks = []
        for task in all_tasks:
            if self.mode == "my":
                # Мои задачи: где я исполнитель ИЛИ я создатель
                # 👇 ИСПРАВЛЕНО: проверяем оба условия
                if task.assigned_to == user_id or task.created_by == user_id:
                    filtered_tasks.append(task)
                    print(f"  ✅ Моя задача: {task.title} (создатель={task.created_by}, исполнитель={task.assigned_to})")
                else:
                    print(f"  ❌ Не моя: {task.title} (создатель={task.created_by}, исполнитель={task.assigned_to})")

            elif self.mode == "others":
                # Чужие задачи: где я НЕ исполнитель И НЕ создатель
                # 👇 ИСПРАВЛЕНО: проверяем оба условия
                if task.assigned_to != user_id and task.created_by != user_id:
                    filtered_tasks.append(task)
                    print(
                        f"  ✅ Чужая задача: {task.title} (создатель={task.created_by}, исполнитель={task.assigned_to})")
                else:
                    print(f"  ❌ Не чужая: {task.title} (создатель={task.created_by}, исполнитель={task.assigned_to})")

            else:  # mode == "all"
                filtered_tasks.append(task)

        print(f"После фильтрации по режиму {self.mode}: {len(filtered_tasks)} задач")

        # Преобразуем в словари
        result = [self._task_to_dict(task) for task in filtered_tasks]

        # Группируем по проектам для отладки
        projects_count = {}
        for task in result:
            proj_name = task.get("project_name", "Неизвестно")
            projects_count[proj_name] = projects_count.get(proj_name, 0) + 1
        print(f"Задачи по проектам: {projects_count}")

        return result

    # =====================================================
    # Получение ВСЕХ колонок из всех проектов
    # =====================================================

    def get_all_columns(self) -> List[Dict]:
        """
        Получает ВСЕ колонки из всех проектов.
        Для канбан-доски нужно объединить колонки с одинаковыми названиями.
        """
        print(f"\n=== ОТЛАДКА: get_all_columns ===")

        # Получаем все колонки из всех проектов
        stmt = select(BoardColumn).order_by(BoardColumn.project_id, BoardColumn.position)
        all_columns = list(self.db_session.scalars(stmt))

        # Группируем по названию колонки
        columns_by_name = {}
        for col in all_columns:
            if col.name not in columns_by_name:
                columns_by_name[col.name] = {
                    "id": col.id,  # используем ID первой колонки с таким названием
                    "name": col.name,
                    "color": col.color if col.color else "#2196F3",
                    "position": col.position,
                    "is_done": col.is_done_column,
                    "project_ids": []
                }
            columns_by_name[col.name]["project_ids"].append(col.project_id)

        # Сортируем по позиции (берем позицию из первой колонки)
        result = sorted(columns_by_name.values(), key=lambda x: x["position"])

        print(f"Найдено уникальных колонок: {len(result)}")
        for col in result:
            print(f"  - {col['name']} (проекты: {col['project_ids']})")

        return result

    def get_column_data(self) -> List[Dict]:
        """Возвращает данные всех колонок для UI."""
        return self.get_all_columns()

    # =====================================================
    # Получение задач по колонкам (для отображения)
    # =====================================================

    def get_tasks_by_column(self, column_name: str) -> List[Dict]:
        """
        Получает все задачи, которые находятся в колонке с указанным именем,
        из всех проектов, с учетом режима фильтрации.
        """
        all_tasks = self.load_tasks()

        # Фильтруем задачи по названию колонки
        result = [
            task for task in all_tasks
            if task.get("status") == column_name
        ]

        # Сортируем по позиции
        result.sort(key=lambda x: x.get("position", 0))

        return result

    # =====================================================
    # Получение данных для доски (колонки + задачи)
    # =====================================================

    def get_board_data(self) -> List[Dict]:
        """
        Возвращает данные для канбан-доски:
        список колонок с задачами внутри.
        """
        columns = self.get_all_columns()

        result = []
        for col in columns:
            tasks = self.get_tasks_by_column(col["name"])
            result.append({
                **col,
                "tasks": tasks
            })

        return result

    # =====================================================
    # CRUD операции с задачами
    # =====================================================

    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        """Получает задачу по ID."""
        task_orm = self.repo.get_by_id(task_id)
        return self._task_to_dict(task_orm) if task_orm else None

    def create_task(self, data: Dict) -> Dict:
        """Создает новую задачу."""
        print("\n=== ОТЛАДКА: create_task в сервисе ===")
        print(f"Входные данные: {data}")

        # Получаем колонку по названию
        column = self._get_column_by_name(data.get("status"))

        if not column:
            # Если колонка не найдена, берем первую колонку из проекта
            column = self._get_first_column(data.get("project_id"))

        if not column:
            raise ValueError(f"Не найдена колонка '{data.get('status')}' в проекте {data.get('project_id')}")

        # Маппинг русских приоритетов в английские
        priority_map = {
            "Низкий": "low",
            "Средний": "medium",
            "Высокий": "high",
            "Критический": "critical"
        }

        priority_value = data.get("priority", "Средний")
        if priority_value in priority_map:
            priority_enum = TaskPriority(priority_map[priority_value])
        else:
            priority_enum = TaskPriority(priority_value) if isinstance(priority_value, str) else priority_value

        task_data = {
            "project_id": data.get("project_id"),
            "column_id": column.id,
            "title": data["title"],
            "description": data.get("description"),
            "priority": priority_enum,
            "deadline": self._parse_date(data.get("deadline")),
            "created_by": data.get("created_by"),
            "assigned_to": data.get("assigned_to"),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # Если позиция не указана, вычисляем
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
        """Обновляет задачу."""
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
                "low": TaskPriority.low,
                "medium": TaskPriority.medium,
                "high": TaskPriority.high,
                "critical": TaskPriority.critical,
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
        if "status" in updated_data:
            new_column = self._get_column_by_name(updated_data["status"])
            if new_column and task.column_id != new_column.id:
                task.column_id = new_column.id

        task.updated_at = datetime.now()
        self.db_session.commit()

        return self._task_to_dict(task)

    def delete_task(self, task_id: int):
        """Удаляет задачу."""
        self.repo.delete(task_id)
        self.db_session.commit()

    def move_task(self, task_id: int, new_column_name: str) -> Optional[tuple]:
        """Перемещает задачу в другую колонку."""
        task = self.repo.get_by_id(task_id)
        if not task:
            return None

        old_column_name = task.column.name if task.column else None
        new_column = self._get_column_by_name(new_column_name, task.project_id)

        if not new_column or task.column_id == new_column.id:
            return None

        task.column_id = new_column.id
        task.updated_at = datetime.now()
        self.db_session.commit()

        return old_column_name, self._task_to_dict(task)

    # =====================================================
    # Вспомогательные методы
    # =====================================================

    def _get_column_by_name(self, column_name: str, project_id: int = None) -> Optional[BoardColumn]:
        """Получает колонку по названию и опционально по проекту."""
        stmt = select(BoardColumn).where(BoardColumn.name == column_name)
        if project_id:
            stmt = stmt.where(BoardColumn.project_id == project_id)
        return self.db_session.scalar(stmt)

    def _get_first_column(self, project_id: int) -> Optional[BoardColumn]:
        """Получает первую колонку проекта."""
        stmt = select(BoardColumn).where(
            BoardColumn.project_id == project_id
        ).order_by(BoardColumn.position)
        return self.db_session.scalar(stmt)

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Парсит дату из строки."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Преобразует ORM-объект в словарь."""
        # Получаем имя исполнителя
        assignee_name = None
        if task.assigned_to:
            assignee_name = self.repo.get_employee_name_by_id(task.assigned_to)

        # Получаем имя создателя
        creator_name = None
        if task.created_by:
            creator_name = self.repo.get_employee_name_by_id(task.created_by)

        # Получаем имя проекта
        project_name = "Неизвестно"
        if task.project_id:
            project = self.db_session.get(Project, task.project_id)
            if project:
                project_name = project.name

        # Маппинг приоритетов для отображения
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

        # Форматируем даты
        created_text = ""
        if task.created_at:
            created_text = task.created_at.strftime("%d.%m.%Y %H:%M")

        updated_text = ""
        if task.updated_at:
            updated_text = task.updated_at.strftime("%d.%m.%Y %H:%M")

        # Форматируем дедлайн
        deadline_text = ""
        deadline_color = "#666"
        if task.deadline:
            deadline_text = task.deadline.strftime("%d.%m.%Y")
            # Проверка на просрочку
            if task.deadline.date() < datetime.now().date():
                deadline_color = "#D22730"

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
            "deadline": task.deadline.strftime("%d.%m.%Y") if task.deadline else "",
            "deadline_text": deadline_text,
            "deadline_color": deadline_color,
            "created_by": task.created_by,
            "created_by_name": creator_name,
            "assigned_to": task.assigned_to,
            "assignee_name": assignee_name,
            "created_at": created_text,
            "updated_at": updated_text,
            "created_text": f"Создана: {created_text}",
            "updated_text": f"Обновление: {updated_text}",
            "author_text": f"Автор: {creator_name}" if creator_name else "",
            "executor_text": f"Исполнитель: {assignee_name}" if assignee_name else "",
            "status": task.column.name if task.column else None,
            "completed": task.completed if hasattr(task, 'completed') else False,
            "column_id": task.column_id,
            "column_name": task.column.name if task.column else None,
            "tags": [tag.tag.name for tag in task.tags] if hasattr(task, 'tags') else [],
        }

    # =====================================================
    # Статистика
    # =====================================================

    def get_statistics(self) -> Dict[str, int]:
        """Возвращает статистику по задачам (из всех проектов)."""
        tasks = self.load_tasks()

        total = len(tasks)
        done = len([t for t in tasks if t.get("completed")])

        # Подсчет просроченных
        overdue = 0
        for t in tasks:
            deadline = t.get("deadline")
            if deadline and not t.get("completed"):
                try:
                    deadline_date = datetime.strptime(deadline, "%d.%m.%Y")
                    if deadline_date.date() < datetime.now().date():
                        overdue += 1
                except:
                    pass

        return {
            "total": total,
            "done": done,
            "overdue": overdue,
            "in_progress": total - done
        }

    def get_statistics_for_display(self) -> Dict:
        """Возвращает статистику в формате для отображения."""
        stats = self.get_statistics()
        return {
            "total": stats["total"],
            "done": stats["done"],
            "overdue": stats["overdue"],
            "in_progress": stats["in_progress"],
            "column_counts": {}  # Для обратной совместимости
        }

    def get_progress_percent(self) -> int:
        """Возвращает процент выполнения задач."""
        stats = self.get_statistics()
        if stats["total"] == 0:
            return 0
        return int((stats["done"] / stats["total"] * 100))

    # =====================================================
    # Фильтрация
    # =====================================================

    def filter_tasks_by_priority(self, tasks: List[Dict], priority: str) -> List[Dict]:
        """Фильтрация задач по приоритету."""
        if priority == "Все приоритеты":
            return tasks

        priority_map = {
            "Низкий": "low",
            "Средний": "medium",
            "Высокий": "high",
            "Критический": "critical"
        }

        target_priority = priority_map.get(priority, priority.lower())

        return [
            t for t in tasks
            if t.get("priority") == target_priority
        ]

    # =====================================================
    # Методы для диалога
    # =====================================================

    def get_all_projects(self) -> List[Dict]:
        """Возвращает список всех проектов для диалога."""
        stmt = select(Project).where(Project.is_archived == False)
        projects = list(self.db_session.scalars(stmt))
        return [{"id": p.id, "name": p.name} for p in projects]

    def get_all_statuses(self) -> List[Dict]:
        """Возвращает список всех уникальных статусов (колонок)."""
        columns = self.get_all_columns()
        return [{"id": i, "name": col["name"]} for i, col in enumerate(columns)]

    def get_employee_list_for_combo(self) -> List[Dict]:
        """Возвращает список сотрудников для комбобокса."""
        employees = self.repo.get_all_employees()
        return [
            {
                "id": emp["id"],
                "display_name": self.safe_person_name(emp)
            }
            for emp in employees
        ]

    def safe_person_name(self, person: Optional[Dict]) -> str:
        """Безопасное отображение имени."""
        if not person:
            return "Неизвестно"
        last = person.get("last_name", "") or ""
        first = (person.get("first_name") or "")[:1]
        middle = (person.get("middle_name") or "")[:1]
        f = first + "." if first else ""
        m = middle + "." if middle else ""
        return f"{last} {f}{m}".strip()

    def get_projects_for_dialog(self) -> List[Dict]:
        """Возвращает список проектов для диалога."""
        return self.get_all_projects()

    def get_statuses_for_dialog(self) -> List[Dict]:
        """Возвращает список статусов для диалога."""
        return self.get_all_statuses()

    def get_priority_map(self) -> Dict[str, str]:
        """Возвращает маппинг приоритетов."""
        return {
            "low": "Низкий",
            "medium": "Средний",
            "high": "Высокий",
            "critical": "Критический"
        }

    def get_reverse_priority_map(self) -> Dict[str, str]:
        """Возвращает обратный маппинг."""
        return {
            "Низкий": "low",
            "Средний": "medium",
            "Высокий": "high",
            "Критический": "critical"
        }

    def validate_form_data(self, form_data: Dict) -> Optional[str]:
        """Валидирует данные формы."""
        if not form_data.get("title"):
            return "Введите название задачи"
        if not form_data.get("project_id"):
            return "Выберите проект"
        if not form_data.get("status"):
            return "Выберите статус"
        return None

    def process_form_data(self, form_data: Dict, current_user: Dict) -> Dict:
        """Обрабатывает данные формы для создания/обновления задачи."""
        priority_map = self.get_reverse_priority_map()

        return {
            "title": form_data["title"],
            "description": form_data.get("description", ""),
            "project_id": form_data["project_id"],
            "assigned_to": form_data.get("assigned_to"),
            "priority": priority_map.get(form_data.get("priority", "Средний"), "medium"),
            "status": form_data["status"],
            "deadline": form_data.get("due_date"),
            "created_by": current_user.get("id"),
        }

    def prepare_dialog_data(self, mode: str, task_data: Optional[Dict] = None) -> Dict:
        """Подготавливает данные для диалога."""
        result = {
            "mode": mode,
            "title": "Создание задачи" if mode == "create" else "Редактирование задачи",
            "button_text": "Создать" if mode == "create" else "Сохранить",
            "projects": self.get_projects_for_dialog(),
            "statuses": self.get_statuses_for_dialog(),
            "employees": self.get_employee_list_for_combo(),
            "priorities": [
                {"text": "Низкий", "value": "low"},
                {"text": "Средний", "value": "medium"},
                {"text": "Высокий", "value": "high"},
                {"text": "Критический", "value": "critical"}
            ]
        }

        if mode == "edit" and task_data:
            result["task_data"] = self.prepare_task_for_display(task_data)

        return result

    def prepare_task_for_display(self, task_data: Dict) -> Dict:
        """Подготавливает данные задачи для отображения в диалоге."""
        priority_map = self.get_priority_map()

        return {
            "title": task_data.get("title", ""),
            "description": task_data.get("description", ""),
            "priority": priority_map.get(task_data.get("priority", "medium"), "Средний"),
            "status": task_data.get("status", ""),
            "assigned_to": task_data.get("assigned_to"),
            "deadline": task_data.get("deadline", ""),
            "project_id": task_data.get("project_id")
        }

    # =====================================================
    # Drag & Drop
    # =====================================================

    def serialize_task_for_drag(self, task_data: Dict) -> str:
        """Сериализует задачу для Drag-n-Drop."""
        return json.dumps(task_data, ensure_ascii=False, default=str)

    def deserialize_task_from_drag(self, raw: bytes) -> Optional[Dict]:
        """Десериализует задачу из Drag-n-Drop."""
        try:
            return json.loads(raw.decode())
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            return None

    # =====================================================
    # Методы для обратной совместимости
    # =====================================================

    def get_board_columns(self) -> List[BoardColumn]:
        """Для обратной совместимости."""
        columns = self.get_all_columns()
        return [BoardColumn(id=c["id"], name=c["name"], color=c["color"],
                            position=c["position"], is_done_column=c["is_done"])
                for c in columns]

    def get_column_names(self) -> List[str]:
        """Получить названия всех колонок."""
        return [col["name"] for col in self.get_all_columns()]

    def get_initial_sizes(self, column_count: int, total_width: int) -> List[int]:
        """Рассчитывает начальные размеры колонок."""
        if column_count == 0:
            return []
        column_width = total_width // column_count
        return [column_width] * column_count

    def format_assignee_name(self, assignee_id: Optional[int]) -> str:
        """Форматирует имя исполнителя по ID."""
        if not assignee_id:
            return ""
        name = self.repo.get_employee_name_by_id(assignee_id)
        return name or "Неизвестен"

    def get_all_employees(self) -> List[Dict]:
        """Получить список всех сотрудников."""
        return self.repo.get_all_employees()

    def get_employee_name_by_id(self, employee_id: int) -> Optional[str]:
        """Получить имя сотрудника по ID."""
        return self.repo.get_employee_name_by_id(employee_id)

    def is_deadline_overdue(self, deadline_str: str, completed: bool) -> bool:
        """Проверяет, просрочен ли дедлайн."""
        if not deadline_str or completed:
            return False
        try:
            deadline_date = datetime.strptime(deadline_str, "%d.%m.%Y").date()
            return deadline_date < datetime.now().date()
        except (ValueError, TypeError):
            return False

    def get_column_color(self, column_name: str) -> str:
        """Получить цвет колонки по названию."""
        columns = self.get_all_columns()
        for col in columns:
            if col["name"] == column_name:
                return col["color"]
        return "#2196F3"

    def prepare_task_card(self, task: dict) -> dict:
        """Подготавливает данные для TaskCard"""

        import datetime

        priority_map = {
            "low": ("Низкий", "#4CAF50"),
            "medium": ("Средний", "#FFA726"),
            "high": ("Высокий", "#D22730"),
            "critical": ("Критический", "#D22730")
        }

        priority = task.get("priority", "medium")

        priority_text, priority_color = priority_map.get(
            priority,
            ("Средний", "#FFA726")
        )

        created = self.format_date(task.get("created_at"))
        updated = self.format_date(task.get("updated_at"))

        author = self.format_user(task.get("author"))
        executor = self.format_user(task.get("assignee"))

        deadline_text, deadline_color = self.prepare_deadline(task.get("deadline"))

        return {
            **task,

            "priority_text": priority_text,
            "priority_color": priority_color,

            "created_text": f"Создана: {created}",
            "updated_text": f"Обновление: {updated}",

            "author_text": author,
            "executor_text": executor,

            "deadline_text": deadline_text,
            "deadline_color": deadline_color,

            "project_name": task.get("project", "Без проекта")
        }

    def format_date(self, date):

        if not date:
            return "Неизвестно"

        if isinstance(date, str):
            return date.split()[0]

        if hasattr(date, "strftime"):
            return date.strftime("%d.%m.%Y")

        return "Неизвестно"

    def format_user(self, user):

        if not user:
            return "Неизвестен"

        last = user.get("last_name", "")
        first = user.get("first_name", "")
        middle = user.get("middle_name", "")

        initials = ""

        if first:
            initials += first[0] + "."

        if middle:
            initials += middle[0] + "."

        return f"{last} {initials}".strip()

    def prepare_deadline(self, deadline):

        import datetime

        if not deadline:
            return None, "#666"

        if isinstance(deadline, str):
            try:
                deadline = datetime.datetime.strptime(deadline, "%Y-%m-%d")
            except:
                return f"До: {deadline}", "#666"

        today = datetime.datetime.now().date()

        diff = (deadline.date() - today).days

        text = deadline.strftime("%d.%m.%Y")

        if diff < 0:
            return f"До: {text} (просрочено)", "#D22730"

        if diff == 0:
            return f"До: {text} (сегодня)", "#FF9800"

        if diff <= 3:
            return f"До: {text} (через {diff} дн.)", "#FF9800"

        return f"До: {text}", "#4CAF50"

    def is_done_column(self, column_name: str) -> bool:
        """Проверяет, является ли колонка 'выполненной'."""
        columns = self.get_board_columns()
        for col in columns:
            if col.name == column_name:
                return col.is_done_column
        return False

    def get_task_count_for_column(self, column_name: str) -> int:
        """Получить количество задач в конкретной колонке."""
        stats = self.get_statistics()
        return stats.get(column_name, 0)

    def validate_task(self, form_data: Dict) -> Optional[str]:
        """Валидация данных из формы."""
        if not form_data.get("title"):
            return "Введите название задачи"
        if not form_data.get("project_id"):
            return "Выберите проект"
        return None

    def build_task_data(self, form_data: Dict, current_user: Dict, employees_list: List) -> Dict:
        """
        Формирует словарь для создания задачи.
        Используется в диалоге перед вызовом create_task.
        """
        assignee_name = None
        if form_data.get("assigned_to"):
            for emp in employees_list:
                if emp["id"] == form_data["assigned_to"]:
                    assignee_name = self.safe_person_name(emp)
                    break

        # Маппинг только для приоритетов (они остаются стандартными)
        priority_map = {
            "Низкий": "low",
            "Средний": "medium",
            "Высокий": "high",
            "Критический": "critical"
        }

        # Статус берем как есть - это название колонки
        status = form_data.get("status", "К выполнению")

        return {
            "title": form_data["title"],
            "description": form_data.get("description"),
            "project_id": form_data["project_id"],
            "assigned_to": form_data.get("assigned_to"),
            "assignee_name": assignee_name,
            "priority": priority_map.get(form_data.get("priority", "Средний"), "medium"),
            "status": status,  # Теперь это название колонки
            "deadline": form_data.get("due_date"),
            "created_by": current_user.get("id"),
        }

    # =====================================================
    # Фильтрация (TODO: нужно реализовать через запросы)
    # =====================================================

    def filter_tasks(self, tasks: List[Dict], priority: str = None, project: str = None) -> List[Dict]:
        """
        Пока оставим фильтрацию на клиенте.
        В будущем можно перенести в БД.
        """
        filtered = []
        for task in tasks:
            if priority and task.get("priority") != priority:
                continue
            # Фильтр по проекту, если нужно
            # if project and task.get("project") != project:
            #     continue
            filtered.append(task)
        return filtered

    # =====================================================
    # Вспомогательные методы
    # =====================================================

    def _get_column_by_status(self, status_name: str) -> Optional[BoardColumn]:
        """Получает объект колонки по имени статуса."""
        from sqlalchemy import select
        stmt = select(BoardColumn).where(
            BoardColumn.project_id == self.current_project_id,
            BoardColumn.name == status_name
        )
        return self.db_session.scalar(stmt)

    def get_task_card_data(self, task_id: int) -> Optional[Dict]:
        """Возвращает данные для карточки задачи."""
        return self.get_task_by_id(task_id)

    def update_task_status(self, task_id: int, new_status: str) -> Optional[Dict]:
        """Обновляет только статус задачи (для drag-n-drop)."""
        return self.move_task(task_id, new_status)

    def prepare_task_for_edit(self, task_data: Dict) -> Dict:
        """Подготавливает данные задачи для редактирования в диалоге."""
        return {
            "id": task_data.get("id"),
            "title": task_data.get("title", ""),
            "description": task_data.get("description", ""),
            "priority": task_data.get("priority", "medium"),
            "status": task_data.get("status", ""),
            "assigned_to": task_data.get("assigned_to"),
            "deadline": task_data.get("deadline", ""),
            "project_id": task_data.get("project_id")
        }

    def get_context_menu_actions(self, status: str, is_creator: bool) -> List[Dict]:
        """Возвращает список действий для контекстного меню."""
        if not is_creator:
            return []

        actions = [
            {"text": "Редактировать", "action": "edit"},
            {"text": "Удалить", "action": "delete"}
        ]

        if status == "review":
            actions.extend([
                {"text": "Одобрить выполнение", "action": "approve"},
                {"text": "Вернуть на доработку", "action": "return"}
            ])
        elif status == "done":
            actions.append({"text": "Архивировать", "action": "archive"})
        else:
            actions.append({"text": "✓ Отметить выполненной", "action": "done"})

        return actions

    def validate_and_prepare_form(self, form_data: Dict, current_user: Dict, employees: List) -> Optional[Dict]:
        """Валидирует и подготавливает данные формы."""
        error = self.validate_task(form_data)
        if error:
            return {"error": error}

        task_data = self.build_task_data(form_data, current_user, employees)
        return {"success": True, "data": task_data}

    def parse_deadline_from_string(self, deadline_str: str) -> Optional[datetime]:
        """Парсит строку дедлайна из формата DD.MM.YYYY."""
        if not deadline_str:
            return None
        try:
            return datetime.strptime(deadline_str, "%d.%m.%Y")
        except (ValueError, TypeError):
            return None

    def format_deadline_for_display(self, deadline: Optional[datetime]) -> str:
        """Форматирует дедлайн для отображения."""
        if not deadline:
            return ""
        return deadline.strftime("%d.%m.%Y")