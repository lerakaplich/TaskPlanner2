# services/other_tasks_service.py

# services/other_tasks_service.py

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

# Импортируем репозиторий
from repositories.other_task_repo import OtherTaskRepo
from models.projects import BoardColumn
from models.tasks import Task
from models.schemas.tasks_dto import TaskPriority


class OtherTasksService:
    """
    Сервис для работы с задачами других сотрудников.
    Вся бизнес-логика здесь, UI только вызывает методы.
    """

    def __init__(self, db_session: Session, project_id: int = 1):
        self.db_session = db_session
        self.repo = OtherTaskRepo(db_session)
        self.current_project_id = project_id

    # =====================================================
    # Работа с задачами
    # =====================================================

    def load_tasks(self) -> List[Dict]:
        """Загружает задачи из БД."""
        tasks_orm = self.repo.get_tasks_for_kanban(self.current_project_id)
        return [self._task_to_dict(t) for t in tasks_orm]

    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        """Получает задачу по ID."""
        task_orm = self.repo.get_task_by_id(task_id)
        return self._task_to_dict(task_orm) if task_orm else None

    def create_task(self, data: Dict) -> Dict:
        """Создает новую задачу."""
        print("\n=== ОТЛАДКА: create_task в сервисе ===")
        print(f"Входные данные: {data}")

        column = self._get_column_by_name(data.get("status"))
        print(f"Найдена колонка: {column.name if column else None} (ID: {column.id if column else None})")

        if not column:
            column = self._get_first_column()
            print(f"Использую первую колонку: {column.name if column else None}")

        # Маппинг русских приоритетов в английские
        priority_map = {
            "Низкий": "low",
            "Средний": "medium",
            "Высокий": "high",
            "Критический": "critical"
        }

        priority_value = data.get("priority", "Средний")
        print(f"Приоритет из формы: {priority_value}")

        # Если приоритет пришел русским текстом, конвертируем
        if priority_value in priority_map:
            priority_enum = TaskPriority(priority_map[priority_value])
            print(f"Сконвертирован в: {priority_enum}")
        else:
            # Если уже английское значение
            priority_enum = TaskPriority(priority_value)
            print(f"Использую как есть: {priority_enum}")

        task_data = {
            "project_id": self.current_project_id,
            "column_id": column.id if column else None,
            "title": data["title"],
            "description": data.get("description"),
            "priority": priority_enum,
            "deadline": self._parse_date(data.get("deadline")),
            "created_by": data.get("created_by"),
            "assigned_to": data.get("assigned_to"),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        print(f"Подготовленные данные для репозитория: {task_data}")
        print(f"Тип priority: {type(priority_enum)}")
        print(f"Значение priority: {priority_enum}")

        try:
            new_task = self.repo.create_task(**task_data)
            print(f"Задача создана в БД, ID: {new_task.id}")

            self.db_session.commit()
            print("Транзакция закоммичена")

            result = self._task_to_dict(new_task)
            print(f"Результат для UI: {result}")

            return result
        except Exception as e:
            print(f"❌ ОШИБКА при создании задачи: {e}")
            import traceback
            traceback.print_exc()
            self.db_session.rollback()
            raise

    def update_task(self, task_id: int, updated_data: Dict) -> Optional[Dict]:
        """Обновляет задачу."""
        task = self.repo.get_task_by_id(task_id)
        if not task:
            return None

        if "title" in updated_data:
            task.title = updated_data["title"]
        if "description" in updated_data:
            task.description = updated_data.get("description")
        if "priority" in updated_data:
            task.priority = TaskPriority(updated_data["priority"])
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
        self.repo.delete_task(task_id)
        self.db_session.commit()

    def move_task(self, task_id: int, new_column_name: str) -> Optional[tuple]:
        """Перемещает задачу в другую колонку."""
        task = self.repo.get_task_by_id(task_id)
        if not task:
            return None

        old_column_name = task.column.name if task.column else None
        new_column = self._get_column_by_name(new_column_name)

        if not new_column or task.column_id == new_column.id:
            return None

        task.column_id = new_column.id
        task.updated_at = datetime.now()
        self.db_session.commit()

        return old_column_name, self._task_to_dict(task)

    # =====================================================
    # Работа с колонками
    # =====================================================

    def get_board_columns(self) -> List[BoardColumn]:
        """Получить все колонки проекта."""
        return self.repo.get_board_columns(self.current_project_id)

    def get_column_names(self) -> List[str]:
        """Получить названия всех колонок."""
        columns = self.get_board_columns()
        return [col.name for col in columns]

    def get_column_color(self, column_name: str) -> str:
        """Получить цвет колонки по названию."""
        columns = self.get_board_columns()
        for col in columns:
            if col.name == column_name:
                return col.color if col.color else "#2196F3"
        return "#2196F3"

    def is_done_column(self, column_name: str) -> bool:
        """Проверяет, является ли колонка 'выполненной'."""
        columns = self.get_board_columns()
        for col in columns:
            if col.name == column_name:
                return col.is_done_column
        return False

    # =====================================================
    # Статистика
    # =====================================================

    def get_statistics(self) -> Dict[str, int]:
        """Возвращает статистику по задачам."""
        column_counts = self.repo.get_task_count_by_column(self.current_project_id)
        overdue = self.repo.get_overdue_count(self.current_project_id)
        column_counts['overdue'] = overdue
        return column_counts

    def get_task_count_for_column(self, column_name: str) -> int:
        """Получить количество задач в конкретной колонке."""
        stats = self.get_statistics()
        return stats.get(column_name, 0)

    # =====================================================
    # Работа с исполнителями
    # =====================================================

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

    # =====================================================
    # Проверки и валидация
    # =====================================================

    def is_deadline_overdue(self, deadline_str: str, completed: bool) -> bool:
        """Проверяет, просрочен ли дедлайн."""
        if not deadline_str or completed:
            return False
        try:
            deadline_date = datetime.strptime(deadline_str, "%d.%m.%Y").date()
            return deadline_date < datetime.now().date()
        except (ValueError, TypeError):
            return False

    def validate_task(self, form_data: Dict) -> Optional[str]:
        """Валидация данных из формы."""
        if not form_data.get("title"):
            return "Введите название задачи"
        if not form_data.get("project_id"):
            return "Выберите проект"
        return None

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

    # =====================================================
    # Drag & Drop
    # =====================================================

    def serialize_task_for_drag(self, task_data: Dict) -> str:
        """Сериализует задачу для Drag-n-Drop."""
        serializable_data = task_data.copy()
        return json.dumps(serializable_data, ensure_ascii=False, default=str)

    def deserialize_task_from_drag(self, raw: bytes) -> Optional[Dict]:
        """Десериализует задачу из Drag-n-Drop."""
        try:
            return json.loads(raw.decode())
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            return None

    # =====================================================
    # Вспомогательные методы
    # =====================================================

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Преобразует ORM-объект в словарь."""
        assignee_name = None
        if task.assigned_to:
            assignee_name = self.repo.get_employee_name_by_id(task.assigned_to)

        return {
            "id": task.id,
            "project_id": task.project_id,
            "title": task.title,
            "description": task.description or "",
            "position": task.position,
            "priority": task.priority.value,
            "deadline": task.deadline.strftime("%d.%m.%Y") if task.deadline else "",
            "created_by": task.created_by,
            "assigned_to": task.assigned_to,
            "assignee_name": assignee_name,
            "created_at": task.created_at.strftime("%d.%m.%Y %H:%M") if task.created_at else "",
            "updated_at": task.updated_at.strftime("%d.%m.%Y %H:%M") if task.updated_at else "",
            "status": task.column.name if task.column else None,
            "completed": task.completed,
            "column_id": task.column_id,
            "column_name": task.column.name if task.column else None,
        }

    def _get_column_by_name(self, column_name: str) -> Optional[BoardColumn]:
        """Получает колонку по названию."""
        from sqlalchemy import select
        stmt = select(BoardColumn).where(
            BoardColumn.project_id == self.current_project_id,
            BoardColumn.name == column_name
        )
        return self.db_session.scalar(stmt)

    def _get_first_column(self) -> Optional[BoardColumn]:
        """Получает первую колонку проекта."""
        from sqlalchemy import select
        stmt = select(BoardColumn).where(
            BoardColumn.project_id == self.current_project_id
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

    # =====================================================
    # Методы для работы с UI (новые)
    # =====================================================

    def get_column_data(self) -> List[Dict]:
        """Возвращает данные всех колонок для UI."""
        columns = self.get_board_columns()
        return [
            {
                "id": col.id,
                "name": col.name,
                "color": col.color if col.color else "#2196F3",
                "position": col.position,
                "is_done": col.is_done_column
            }
            for col in columns
        ]

    def get_task_card_data(self, task_id: int) -> Optional[Dict]:
        """Возвращает данные для карточки задачи."""
        return self.get_task_by_id(task_id)

    def update_task_status(self, task_id: int, new_status: str) -> Optional[Dict]:
        """Обновляет только статус задачи (для drag-n-drop)."""
        return self.move_task(task_id, new_status)

    def get_initial_sizes(self, column_count: int, total_width: int) -> List[int]:
        """Рассчитывает начальные размеры колонок."""
        if column_count == 0:
            return []
        column_width = total_width // column_count
        return [column_width] * column_count

    def filter_tasks_by_priority(self, tasks: List[Dict], priority: str) -> List[Dict]:
        """Фильтрует задачи по приоритету."""
        if priority == "Все приоритеты":
            return tasks
        return [t for t in tasks if t.get("priority") == priority.lower()]

    def get_statistics_for_display(self) -> Dict:
        """Возвращает статистику в формате для отображения."""
        stats = self.get_statistics()
        total = sum(v for k, v in stats.items() if k != 'overdue' and isinstance(v, int))
        return {
            "total": total,
            "in_progress": stats.get('В работе', 0),
            "overdue": stats.get('overdue', 0),
            "done": stats.get('Выполнен', 0) or stats.get('Выполнено', 0),
            "column_counts": stats
        }

    def get_progress_percent(self) -> int:
        """Возвращает процент выполнения задач."""
        stats = self.get_statistics_for_display()
        if stats["total"] == 0:
            return 0
        return int((stats["done"] / stats["total"] * 100))

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

    def get_employee_list_for_combo(self) -> List[Dict]:
        """Возвращает список сотрудников для комбобокса."""
        employees = self.get_all_employees()
        return [
            {
                "id": emp["id"],
                "display_name": self.safe_person_name(emp)
            }
            for emp in employees
        ]

    # =====================================================
    # Методы для работы с диалогом задач (новые)
    # =====================================================

    def get_projects_for_dialog(self) -> List[Dict]:
        """Возвращает список проектов для диалога."""
        # TODO: заменить на реальный запрос из БД
        return [{"id": 2, "name": "Проект 2"}]

    def get_statuses_for_dialog(self) -> List[Dict]:
        """Возвращает список статусов (колонок) для диалога."""
        columns = self.get_board_columns()
        return [
            {
                "id": col.id,
                "name": col.name
            }
            for col in columns
        ]

    def get_priority_map(self) -> Dict[str, str]:
        """Возвращает маппинг приоритетов для отображения."""
        return {
            "low": "Низкий",
            "medium": "Средний",
            "high": "Высокий",
            "critical": "Критический"
        }

    def get_reverse_priority_map(self) -> Dict[str, str]:
        """Возвращает обратный маппинг приоритетов."""
        return {
            "Низкий": "low",
            "Средний": "medium",
            "Высокий": "high",
            "Критический": "critical"
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