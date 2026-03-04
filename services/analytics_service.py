# Расчеты статистики (кол-во задач, среднее время выполнения).

from datetime import datetime
from models.schemas.employees_dto import EmployeeAnalyticsDTO
from models.schemas.projects_dto import ProjectAnalyticsDTO

class AnalyticsService:
    STATUS_MAP = {
        'to_do': 'К выполнению',
        'in_progress': 'В работе',
        'review': 'На проверке',
        'completed': 'Выполнено',
        'archived': 'Архивировано'
    }
    def __init__(self, employee_repo, project_repo, task_repo):
        self.employee_repo = employee_repo
        self.project_repo = project_repo
        self.task_repo = task_repo

    # ВКЛАДКА ТЕМЫ

    def get_themes_analytics(self):
        """Возвращает словарь {ИмяТега: [СписокОбъектовЗадач]} для генерации вкладок."""
        all_tasks = self.task_repo.get_all_tasks_with_tags()
        themes = {}
        for task in all_tasks:
            for tag in task.tags:
                themes.setdefault(tag.name, []).append(task)
        return themes

    def get_theme_stats_by_employees(self, tasks):
        """
        Принимает список моделей задач и возвращает агрегированную статистику
        по сотрудникам для конкретной темы/тега.
        """
        stats = {}

        for task in tasks:
            emp_id = task.assigned_to
            if not emp_id:
                continue

            # Получаем имя через репозиторий (внешняя БД)
            emp_name = self.employee_repo.get_name_by_id(emp_id)

            if emp_name not in stats:
                stats[emp_name] = {
                    "kpi_sum": 0.0,
                    "kpi_count": 0,
                    "completed": 0,
                    "low": 0, "medium": 0, "high": 0, "critical": 0
                }

            # Считаем приоритеты
            prio = task.priority.lower() if task.priority else "medium"
            if prio in ["low", "medium", "high", "critical"]:
                stats[emp_name][prio] += 1

            # Считаем выполненные и КПД
            if task.status in ("completed", "archived"):
                stats[emp_name]["completed"] += 1
                kpi = self._calculate_kpi_value(task)  # Используем наш приватный метод
                if kpi is not None and kpi != float('inf'):
                    stats[emp_name]["kpi_sum"] += kpi
                    stats[emp_name]["kpi_count"] += 1

        # Формируем финальный список для таблицы
        result = []
        for name, data in stats.items():
            avg_kpi = data["kpi_sum"] / data["kpi_count"] if data["kpi_count"] > 0 else 0
            result.append({
                "employee": name,
                "avg_kpi": f"{avg_kpi:.2f}",
                "completed": str(data["completed"]),
                "low": str(data["low"]),
                "medium": str(data["medium"]),
                "high": str(data["high"]),
                "critical": str(data["critical"])
            })
        return result

    def get_theme_card_data(self, theme_name, tasks):
        """Формирует полный пакет данных для ThemeCard."""
        return {
            "theme_name": theme_name,
            "task_count": len(tasks),
            "employee_stats": self.get_theme_stats_by_employees(tasks),
            # Используем метод иерархической группировки для ThemeProjectsView
            "project_stats": self.get_theme_projects_data(tasks)
        }

    def get_theme_projects_data(self, tasks):
        """
        Группирует задачи темы: Проект -> Статус -> Список DTO задач.
        Используется внутри ThemeProjectsView.
        """
        projects_tree = {}
        for task in tasks:
            p_name = task.project.name if task.project else "Без проекта"
            if p_name not in projects_tree:
                # Инициализируем структуру статусов для каждого нового проекта
                projects_tree[p_name] = {s: [] for s in ['to_do', 'in_progress', 'review', 'completed']}

            status = task.status.lower() if task.status else 'to_do'
            # Если статус в модели сложнее, приводим к базовым ключам
            target_status = status if status in projects_tree[p_name] else 'to_do'

            projects_tree[p_name][target_status].append(self._prepare_task_dto(task))
        return projects_tree

    # ВКЛАДКА ПРОЕКТЫ

    def get_projects_analytics(self):
        """Список всех активных проектов для вкладки 'Проекты'."""
        projects = self.project_repo.get_all_active_projects()
        return [self.prepare_project_card_data(p) for p in projects]

    def prepare_project_card_data(self, project):
        """Подготовка данных для ProjectCard (вкладка Проекты)."""
        tasks = self.task_repo.get_tasks_by_project_id(project.id)
        status_order = ["to_do", "in_progress", "review", "completed", "archived"]
        grouped_tasks = {s: [] for s in status_order}

        for t in tasks:
            status = t.status.lower() if t.status else "to_do"
            if status in grouped_tasks:
                grouped_tasks[status].append(self._prepare_task_dto(t))

        return {
            "id": project.id,
            "name": project.name,
            "start_date_str": project.start_date.strftime("%d.%m.%Y") if project.start_date else "не указана",
            "status_display": self.STATUS_MAP.get(project.status, project.status),
            "emp_count": len(project.employees) if hasattr(project, 'employees') else 0,
            "grouped_tasks": grouped_tasks,
            "employees": project.employees if hasattr(project, 'employees') else [],
            "is_active": project.status in ("to_do", "in_progress", "review")
        }

    # ВКЛАДКА СОТРУДНИКИ

    def get_employees_analytics(self):
        """Базовый список сотрудников для инициализации вкладок."""
        remote_employees = self.employee_repo.get_all_remote()
        return [{
            "id": emp.id,
            "name": f"{emp.last_name} {emp.first_name} {emp.middle_name}",
            "position": emp.position,
            "department": emp.department,
            "subdivision": getattr(emp, 'subdivision', '—') # Добавили поле из UI
        } for emp in remote_employees]

    def get_employee_personal_analytics(self, employee_id):
        """Глубокая аналитика для конкретной карточки EmployeeCard."""
        tasks = self.task_repo.get_tasks_by_employee_id(employee_id)
        projects_all = self.project_repo.get_projects_by_employee(employee_id)

        tag_stats = {}
        for task in tasks:
            if task.status == 'completed':
                kpi = self._calculate_kpi_value(task)
                if kpi and kpi != float('inf'):
                    for tag in task.tags:
                        s = tag_stats.setdefault(tag.name, {"sum": 0, "count": 0})
                        s["sum"] += kpi
                        s["count"] += 1

        return {
            "active_projects": [p for p in projects_all if p.status != 'completed'],
            "completed_projects": [p for p in projects_all if p.status == 'completed'],
            "tag_analytics": [
                {"tag": name, "kpd": round(val["sum"] / val["count"], 2), "count": val["count"]}
                for name, val in tag_stats.items()
            ]
        }

    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ

    def _calculate_kpi_value(self, task):
        if not all([task.created_at, task.completed_at, task.due_date]): return None
        planned = (task.due_date - task.created_at).days
        actual = (task.completed_at - task.created_at).days
        return round(planned / actual, 2) if actual > 0 else 0

    def _is_task_overdue(self, task):
        if task.status in ('completed', 'archived'): return False
        return task.due_date and task.due_date < datetime.now().date()

    def _prepare_task_dto(self, task, creator_name=None):
        return {
            "title": task.title,
            "priority": task.priority,
            "status": task.status,
            "is_overdue": self._is_task_overdue(task),
            "tags_list": [tag.name for tag in task.tags],
            "created_at_str": task.created_at.strftime("%d.%m.%Y") if task.created_at else "—",
            "due_date_str": task.due_date.strftime("%d.%m.%Y") if task.due_date else "Нет",
            "creator_name": creator_name or "Неизвестно",
            "kpi_value": self._calculate_kpi_value(task) if task.status == 'completed' else None,
            "project_name": task.project.name if task.project else "—"
        }