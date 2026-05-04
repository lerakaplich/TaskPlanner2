# services/analytics_service.py

from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_

from database import get_employees_session
from models.tasks import Task, TaskTag, Tag
from models.projects import Project, EmployeeProject, BoardColumn
from models.employees import Employee, Department, Division
from repositories.tag_repo import TagRepo


class AnalyticsService:
    """Сервис для аналитики по сотрудникам, темам и проектам"""

    def __init__(self, session: Session):
        # Сессия для taskplanner БД (проекты, задачи)
        self.session = session
        # Отдельная сессия для employees БД (сотрудники)
        self.employees_session = get_employees_session()

        self.tag_repo = TagRepo(session)
        self.current_user_id = None

    def __del__(self):
        """Закрываем сессию employees при удалении"""
        try:
            if hasattr(self, 'employees_session') and self.employees_session:
                self.employees_session.close()
        except:
            pass

    def set_current_user_id(self, user_id: int):
        """Устанавливает ID текущего пользователя"""
        self.current_user_id = user_id
        print(f"📊 AnalyticsService: current_user_id = {user_id}")

    # ======================================================
    # Данные для карточек задач
    # ======================================================

    def get_task_card_data(self, task_data: Dict) -> Dict:
        """
        Подготавливает данные для карточки задачи TaskCard.
        Возвращает словарь с полями:
        - title, description, priority, priority_text, priority_color
        - status, status_text, is_overdue
        - due_date_str, created_at_str, completed_at_str
        - creator_name, project_name, tags_list
        """
        priority = task_data.get("priority", "medium")
        status = task_data.get("status", "to_do")
        is_overdue = task_data.get("is_overdue", False)

        # Приоритет
        priority_map = {
            'low': ('Низкий', '#2ecc71'),
            'medium': ('Средний', '#f1c40f'),
            'high': ('Высокий', '#e67e22'),
            'critical': ('Критический', '#e74c3c')
        }
        priority_text, priority_color = priority_map.get(priority, ('Средний', '#f1c40f'))

        # Статус
        status_map = {
            'to_do': 'К выполнению',
            'in_progress': 'В работе',
            'review': 'На проверке',
            'completed': 'Выполнено',
            'archived': 'Архивировано'
        }
        status_text = status_map.get(status, status.capitalize() if status else "Неизвестно")

        # Получаем теги
        tags_list = task_data.get("tags_list", [])

        return {
            "id": task_data.get("id"),
            "title": task_data.get("title", "Без названия"),
            "description": task_data.get("description", ""),
            "priority": priority,
            "priority_text": priority_text,
            "priority_color": priority_color,
            "status": status,
            "status_text": status_text,
            "is_overdue": is_overdue,
            "due_date_str": task_data.get("due_date_str", "Нет"),
            "created_at_str": task_data.get("created_at_str", ""),
            "completed_at_str": task_data.get("completed_at_str", ""),
            "creator_name": task_data.get("creator_name", ""),
            "project_name": task_data.get("project_name", ""),
            "tags_list": tags_list[:3],  # Максимум 3 тега
            "tags_extra_count": max(0, len(tags_list) - 3)
        }

    def get_task_card_background_color(self, task_data: Dict) -> str:
        """
        Возвращает цвет фона для карточки задачи.
        Просроченные задачи - #ffeeee, остальные - white
        """
        is_overdue = task_data.get("is_overdue", False)
        return "#ffeeee" if is_overdue else "white"

    def get_task_card_border_color(self, task_data: Dict) -> str:
        """
        Возвращает цвет границы для карточки задачи.
        Цвет границы определяется приоритетом задачи.
        """
        priority = task_data.get("priority", "medium")
        priority_colors = {
            'low': '#2ecc71',
            'medium': '#f1c40f',
            'high': '#e67e22',
            'critical': '#e74c3c'
        }
        is_overdue = task_data.get("is_overdue", False)
        if is_overdue:
            return "#e74c3c"
        return priority_colors.get(priority, "#cccccc")

    # ======================================================
    # Аналитика по сотрудникам
    # ======================================================

    def get_employee_card_data(self, employee_id: int) -> Dict[str, Any]:
        """
        Получить данные сотрудника для карточки EmployeeCard
        Возвращает словарь с ключами:
        - id, name, position, department, subdivision
        - active_projects, completed_projects
        - active_tasks, completed_tasks, overdue_tasks, total_tasks
        - tag_analytics
        """
        emp = self.employees_session.get(Employee, employee_id)
        if not emp:
            return {}

        stats = self._get_employee_stats(employee_id)

        return {
            "id": emp.id,
            "name": self._format_employee_name(emp),
            "last_name": emp.last_name,
            "first_name": emp.first_name,
            "middle_name": emp.middle_name or "",
            "position": emp.position or "—",
            "department_id": emp.department_id,
            "division_id": emp.division_id,
            "department": self._get_department_name(emp.department_id),
            "subdivision": self._get_division_name(emp.division_id),
            "active_projects": stats["active_projects"],
            "completed_projects": stats["completed_projects"],
            "active_tasks": stats["active_tasks"],
            "completed_tasks": stats["completed_tasks"],
            "overdue_tasks": stats["overdue_tasks"],
            "total_tasks": stats["total_tasks"],
            "tag_analytics": stats["tag_analytics"]
        }

    def get_all_employees_for_cards(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Получить всех сотрудников с данными для карточек EmployeeCard
        """
        stmt = select(Employee).order_by(Employee.last_name)
        employees = list(self.employees_session.scalars(stmt))

        result = []
        for emp in employees:
            if active_only:
                # Проверяем активность через EmployeeData
                from models.employees import EmployeeData
                emp_data = self.session.query(EmployeeData).filter(
                    EmployeeData.employee_id == emp.id
                ).first()
                if emp_data and not emp_data.is_active:
                    continue

            card_data = self.get_employee_card_data(emp.id)
            result.append(card_data)

        return result

    def get_all_employees_with_stats(self) -> List[Dict[str, Any]]:
        """Получить всех сотрудников со статистикой"""
        stmt = select(Employee).order_by(Employee.last_name)
        employees = list(self.employees_session.scalars(stmt))
        print(f"📊 Найдено сотрудников в БД employees: {len(employees)}")

        # Выводим первых несколько сотрудников для проверки
        for emp in employees[:3]:
            print(f"   - {emp.last_name} {emp.first_name} (ID: {emp.id})")

        result = []
        for emp in employees:
            # Проверяем активность через EmployeeData (в taskplanner)
            from models.employees import EmployeeData
            emp_data = self.session.query(EmployeeData).filter(
                EmployeeData.employee_id == emp.id
            ).first()

            is_active = emp_data.is_active if emp_data else True
            print(f"   Сотрудник {emp.id}: is_active={is_active}")

            if not is_active:
                print(f"   → Пропускаем неактивного: {emp.last_name}")
                continue

            try:
                card_data = self.get_employee_card_data(emp.id)
                if card_data:
                    print(f"   → Добавляем: {card_data.get('name')}")
                    result.append(card_data)
                else:
                    print(f"   → Ошибка: card_data пуст для {emp.id}")
            except Exception as e:
                print(f"   → Ошибка при получении card_data для {emp.id}: {e}")
                import traceback
                traceback.print_exc()

        print(f"📊 Итоговое количество сотрудников для отображения: {len(result)}")
        return result

    def _get_employee_stats(self, employee_id: int) -> Dict[str, Any]:
        """Получить статистику сотрудника"""
        from datetime import datetime

        # 1. Проекты сотрудника (из taskplanner)
        projects_stmt = select(Project).join(
            EmployeeProject, Project.id == EmployeeProject.project_id
        ).where(EmployeeProject.employee_id == employee_id)

        all_projects = list(self.session.scalars(projects_stmt))

        # Активные проекты (не архивные) и выполненные проекты (архивные)
        active_projects = []
        completed_projects = []

        for p in all_projects:
            proj_dict = self._project_to_dict(p)
            if p.is_archived:
                completed_projects.append(proj_dict)
            else:
                active_projects.append(proj_dict)

        # 2. Задачи сотрудника (как исполнитель или создатель) - из taskplanner
        tasks_stmt = select(Task).where(
            or_(
                Task.assigned_to == employee_id,
                Task.created_by == employee_id
            )
        )
        all_tasks = list(self.session.scalars(tasks_stmt))

        # Подсчет статистики по задачам
        active_tasks = 0
        completed_tasks = 0
        overdue_tasks = 0

        for task in all_tasks:
            is_completed = False
            if task.column:
                is_completed = task.column.is_done_column

            if is_completed or task.is_archived:
                completed_tasks += 1
            else:
                active_tasks += 1

            # Проверка на просрочку
            if task.deadline and not is_completed and not task.is_archived:
                if task.deadline.date() < datetime.now().date():
                    overdue_tasks += 1

        # 3. Аналитика по тегам (темам)
        tag_analytics = self._get_employee_tag_analytics(employee_id, all_tasks)

        return {
            "active_projects": active_projects,
            "completed_projects": completed_projects,
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
            "total_tasks": len(all_tasks),
            "tag_analytics": tag_analytics
        }

    def _get_employee_tag_analytics(self, employee_id: int, tasks: List[Task]) -> List[Dict]:
        """Получить аналитику по тегам для сотрудника"""
        tag_stats = {}

        for task in tasks:
            # Получаем теги задачи
            task_tags = self.tag_repo.get_task_tags(task.id)

            for tag in task_tags:
                tag_name = tag.name
                if tag_name not in tag_stats:
                    tag_stats[tag_name] = {
                        "tag": tag_name,
                        "count": 0,
                        "completed": 0,
                        "kpd": 0.0
                    }

                tag_stats[tag_name]["count"] += 1

                # Проверяем, выполнена ли задача
                is_completed = False
                if task.column:
                    is_completed = task.column.is_done_column
                if is_completed or task.is_archived:
                    tag_stats[tag_name]["completed"] += 1

        # Рассчитываем КПД для каждого тега
        for tag_name, stats in tag_stats.items():
            if stats["count"] > 0:
                stats["kpd"] = round(stats["completed"] / stats["count"], 2)
            else:
                stats["kpd"] = 0.0

        # Сортируем по количеству задач
        return sorted(tag_stats.values(), key=lambda x: x["count"], reverse=True)

    # ======================================================
    # Аналитика по проектам
    # ======================================================

    def get_project_card_data(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Подготавливает данные для карточки проекта.
        Возвращает словарь с ключами:
        - id, name, description, is_archived, created_at_str, status_display
        - total_tasks, active_tasks, completed_tasks, overdue_tasks, high_priority_tasks
        - members, member_count
        - grouped_tasks (с уже преобразованными задачами)
        """
        # Группируем задачи по статусам
        grouped_tasks = self._prepare_grouped_tasks(project_data.get("grouped_tasks", {}))

        # Форматируем сотрудников
        employees = self._prepare_employees_data(project_data.get("employees", []))

        return {
            "id": project_data.get("id"),
            "name": project_data.get("name", "Без названия"),
            "description": project_data.get("description", ""),
            "is_archived": project_data.get("is_archived", False),
            "created_at": project_data.get("created_at", ""),
            "created_at_str": project_data.get("created_at_str", ""),
            "status_display": "Активный" if not project_data.get("is_archived", False) else "Архивный",
            "total_tasks": project_data.get("total_tasks", 0),
            "active_tasks": project_data.get("active_tasks", 0),
            "completed_tasks": project_data.get("completed_tasks", 0),
            "overdue_tasks": project_data.get("overdue_tasks", 0),
            "high_priority_tasks": project_data.get("high_priority_tasks", 0),
            "members": employees,
            "employees": employees,
            "member_count": len(employees),
            "emp_count": len(employees),
            "grouped_tasks": grouped_tasks
        }

    def _prepare_grouped_tasks(self, grouped_tasks: Dict) -> Dict:
        """
        Подготавливает сгруппированные задачи для отображения.
        Каждая задача преобразуется в словарь с нужными полями.
        """
        result = {
            "to_do": [],
            "in_progress": [],
            "review": [],
            "completed": []
        }

        status_map = {
            "to_do": "К выполнению",
            "in_progress": "В работе",
            "review": "На проверке",
            "completed": "Выполнено"
        }

        for status_key, tasks in grouped_tasks.items():
            if status_key not in result:
                continue
            for task in tasks:
                # Если задача уже словарь, используем как есть
                if isinstance(task, dict):
                    task_dict = task
                else:
                    # Преобразуем объект задачи в словарь
                    task_dict = self._task_to_analytics_dto(
                        task,
                        status_key,
                        status_key == "completed"
                    )

                # Добавляем название статуса для отображения
                task_dict["status_display"] = status_map.get(status_key, status_key)
                result[status_key].append(task_dict)

        return result

    def _prepare_employees_data(self, employees: List) -> List[Dict]:
        """
        Подготавливает данные сотрудников для отображения в карточке проекта.
        """
        result = []
        for emp in employees:
            # Если сотрудник уже словарь, используем как есть
            if isinstance(emp, dict):
                emp_dict = emp.copy()
            else:
                # Преобразуем объект сотрудника
                emp_dict = {
                    "id": getattr(emp, 'id', 0),
                    "name": self._format_employee_name(emp) if hasattr(emp, 'last_name') else str(emp),
                    "is_admin": getattr(emp, 'is_admin', False),
                    "active_tasks": getattr(emp, 'active_tasks', 0),
                    "completed_tasks": getattr(emp, 'completed_tasks', 0),
                    "active": getattr(emp, 'active', 0),
                    "completed": getattr(emp, 'completed', 0)
                }

            # Нормализуем ключи для совместимости с UI
            emp_dict["employee_name"] = emp_dict.get("name", "Неизвестен")
            emp_dict["active"] = emp_dict.get("active_tasks", emp_dict.get("active", 0))
            emp_dict["completed"] = emp_dict.get("completed_tasks", emp_dict.get("completed", 0))
            result.append(emp_dict)

        return result

    def get_status_name(self, status_key: str) -> str:
        """Возвращает русское название статуса"""
        status_names = {
            'to_do': 'К выполнению',
            'in_progress': 'В работе',
            'review': 'На проверке',
            'completed': 'Выполнено'
        }
        return status_names.get(status_key, status_key)

    def has_tasks_in_project(self, project_data: Dict) -> bool:
        """Проверяет, есть ли задачи в проекте"""
        grouped_tasks = project_data.get("grouped_tasks", {})
        return any(tasks for tasks in grouped_tasks.values())

    # ======================================================
    # Аналитика по темам
    # ======================================================

    def get_themes_stats(self) -> List[Dict[str, Any]]:
        """Получить статистику по всем темам (тегам)"""
        all_tags = self.tag_repo.get_all(include_archived=False)
        result = []

        for tag in all_tags:
            # Получаем все задачи с этим тегом
            task_ids = self.tag_repo.get_tasks_by_tag(tag.id)
            tasks = []
            for task_id in task_ids:
                task = self.session.get(Task, task_id)
                if task and not task.is_archived:
                    tasks.append(task)

            # Статистика по проектам
            project_stats = {}
            # Статистика по сотрудникам
            employee_stats = {}

            for task in tasks:
                # Проект
                project = self.session.get(Project, task.project_id)
                if project:
                    project_name = project.name
                    if project_name not in project_stats:
                        project_stats[project_name] = {
                            "project_name": project_name,
                            "task_count": 0,
                            "completed_count": 0
                        }
                    project_stats[project_name]["task_count"] += 1

                    # Проверка на выполнение
                    is_completed = False
                    if task.column:
                        is_completed = task.column.is_done_column
                    if is_completed:
                        project_stats[project_name]["completed_count"] += 1

                # Сотрудник (исполнитель)
                if task.assigned_to:
                    emp = self.employees_session.get(Employee, task.assigned_to)
                    if emp:
                        emp_name = self._format_employee_name(emp)
                        if emp_name not in employee_stats:
                            employee_stats[emp_name] = {
                                "employee_id": task.assigned_to,
                                "employee_name": emp_name,
                                "task_count": 0,
                                "completed_count": 0,
                                "avg_kpi": 0,
                                "low": 0,
                                "medium": 0,
                                "high": 0,
                                "critical": 0
                            }
                        employee_stats[emp_name]["task_count"] += 1

                        # Считаем приоритеты
                        priority = task.priority.value if hasattr(task.priority, 'value') else str(task.priority)
                        if priority in employee_stats[emp_name]:
                            employee_stats[emp_name][priority] += 1
                        elif priority == "low":
                            employee_stats[emp_name]["low"] += 1
                        elif priority == "medium":
                            employee_stats[emp_name]["medium"] += 1
                        elif priority == "high":
                            employee_stats[emp_name]["high"] += 1
                        elif priority == "critical":
                            employee_stats[emp_name]["critical"] += 1

                        is_completed = False
                        if task.column:
                            is_completed = task.column.is_done_column
                        if is_completed:
                            employee_stats[emp_name]["completed_count"] += 1

            # Рассчитываем средний КПД для сотрудников
            for emp_name, stats in employee_stats.items():
                if stats["task_count"] > 0:
                    stats["avg_kpi"] = round(stats["completed_count"] / stats["task_count"], 2)
                else:
                    stats["avg_kpi"] = 0

            # КПД для тега
            total_tasks = len(tasks)
            completed_tasks = sum(1 for t in tasks if t.column and t.column.is_done_column)
            kpd = round(completed_tasks / total_tasks, 2) if total_tasks > 0 else 0

            result.append({
                "theme_name": tag.name,
                "tag_id": tag.id,
                "color": tag.color,
                "task_count": total_tasks,
                "completed_count": completed_tasks,
                "kpd": kpd,
                "project_stats": list(project_stats.values()),
                "employee_stats": list(employee_stats.values())
            })

        # Сортируем по количеству задач
        return sorted(result, key=lambda x: x["task_count"], reverse=True)

    def get_theme_card_data(self, theme_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Подготавливает данные для карточки темы.
        Возвращает словарь с ключами:
        - theme_name, tag_id, color, task_count, completed_count, kpd, kpd_percent
        - employee_stats (подготовленные), project_stats (подготовленные)
        """
        employee_stats = self._prepare_theme_employee_stats(theme_data.get("employee_stats", []))
        project_stats = self._prepare_theme_project_stats(theme_data.get("project_stats", []))

        kpd = theme_data.get("kpd", 0)

        return {
            "theme_name": theme_data.get("theme_name", "Без названия"),
            "tag_id": theme_data.get("tag_id"),
            "color": theme_data.get("color", "#ccab6e"),
            "task_count": theme_data.get("task_count", 0),
            "completed_count": theme_data.get("completed_count", 0),
            "kpd": kpd,
            "kpd_percent": int(kpd * 100),
            "employee_stats": employee_stats,
            "project_stats": project_stats
        }

    def _prepare_theme_employee_stats(self, employee_stats: List[Dict]) -> List[Dict]:
        """
        Подготавливает статистику сотрудников для отображения в теме.
        """
        result = []
        for stat in employee_stats:
            if not isinstance(stat, dict):
                continue

            # Рассчитываем KPI в процентах
            task_count = stat.get("task_count", 0)
            completed_count = stat.get("completed_count", 0)
            avg_kpi = (completed_count / task_count * 100) if task_count > 0 else 0

            result.append({
                "employee_name": stat.get("employee_name", "Неизвестно"),
                "employee_id": stat.get("employee_id"),
                "avg_kpi": round(avg_kpi, 1),
                "completed_count": completed_count,
                "task_count": task_count,
                "low": stat.get("low", 0),
                "medium": stat.get("medium", 0),
                "high": stat.get("high", 0),
                "critical": stat.get("critical", 0)
            })

        # Сортируем по КПД (по убыванию)
        result.sort(key=lambda x: x.get("avg_kpi", 0), reverse=True)
        return result

    def _prepare_theme_project_stats(self, project_stats: List[Dict]) -> List[Dict]:
        """
        Подготавливает статистику проектов для отображения в теме.
        """
        result = []
        for stat in project_stats:
            if not isinstance(stat, dict):
                continue

            result.append({
                "project_name": stat.get("project_name", "Без названия"),
                "task_count": stat.get("task_count", 0),
                "completed_count": stat.get("completed_count", 0),
                "completion_percent": (
                            stat.get("completed_count", 0) / stat.get("task_count", 1) * 100) if stat.get(
                    "task_count", 0) > 0 else 0
            })

        # Сортируем по количеству задач (по убыванию)
        result.sort(key=lambda x: x.get("task_count", 0), reverse=True)
        return result

    def filter_employees_by_name(self, employees_data: List[Dict], search_text: str) -> List[Dict]:
        """Фильтрует сотрудников по имени"""
        if not search_text:
            return employees_data
        search_lower = search_text.lower()
        return [
            emp for emp in employees_data
            if search_lower in emp.get("employee_name", "").lower()
        ]

    def get_empty_employee_stats(self) -> Dict:
        """Возвращает пустые данные для статистики сотрудников"""
        return {
            "employee_name": "Нет данных",
            "avg_kpi": 0,
            "completed_count": 0,
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0
        }

    # ======================================================
    # Аналитика по проектам
    # ======================================================

    def get_projects_stats(self) -> List[Dict[str, Any]]:
        """Получить статистику по всем проектам"""
        stmt = select(Project).order_by(Project.name)
        projects = list(self.session.scalars(stmt))

        result = []
        for project in projects:
            # Задачи проекта
            tasks = self.session.scalars(
                select(Task).where(Task.project_id == project.id)
            ).all()

            # Группируем задачи по статусам для ProjectCard
            grouped_tasks = {
                "to_do": [],
                "in_progress": [],
                "review": [],
                "completed": []
            }

            active_tasks = 0
            completed_tasks = 0
            overdue_tasks = 0
            high_priority_tasks = 0

            for task in tasks:
                # Определяем статус
                status = "to_do"
                is_completed = False

                if task.column:
                    column_name = task.column.name.lower()
                    if task.column.is_done_column:
                        status = "completed"
                        is_completed = True
                    elif "проверк" in column_name:
                        status = "review"
                    elif "работ" in column_name:
                        status = "in_progress"
                    else:
                        status = "to_do"

                # Формируем DTO задачи для карточки
                task_dto = self._task_to_analytics_dto(task, status, is_completed)

                if status in grouped_tasks:
                    grouped_tasks[status].append(task_dto)
                else:
                    grouped_tasks["to_do"].append(task_dto)

                if is_completed or task.is_archived:
                    completed_tasks += 1
                else:
                    active_tasks += 1

                if task.deadline and not is_completed and not task.is_archived:
                    if task.deadline.date() < datetime.now().date():
                        overdue_tasks += 1

                if task.priority.value in ["high", "critical"]:
                    high_priority_tasks += 1

            # Участники проекта
            members_stmt = select(EmployeeProject).where(
                EmployeeProject.project_id == project.id
            )
            members = list(self.session.scalars(members_stmt))

            employees = []
            for member in members:
                emp = self.employees_session.get(Employee, member.employee_id)
                if emp:
                    # Считаем статистику сотрудника в этом проекте
                    emp_tasks = [t for t in tasks if t.assigned_to == emp.id]
                    active = sum(
                        1 for t in emp_tasks if not (t.column and t.column.is_done_column) and not t.is_archived)
                    completed = sum(1 for t in emp_tasks if (t.column and t.column.is_done_column) or t.is_archived)

                    employees.append({
                        "id": emp.id,
                        "name": self._format_employee_name(emp),
                        "is_admin": member.is_admin or False,
                        "active_tasks": active,
                        "completed_tasks": completed,
                        "active": active,
                        "completed": completed
                    })

            result.append({
                "id": project.id,
                "name": project.name,
                "description": project.description or "",
                "is_archived": project.is_archived,
                "created_at": project.created_at.strftime("%d.%m.%Y") if project.created_at else "",
                "created_at_str": project.created_at.strftime("%d.%m.%Y") if project.created_at else "",
                "total_tasks": len(tasks),
                "active_tasks": active_tasks,
                "completed_tasks": completed_tasks,
                "overdue_tasks": overdue_tasks,
                "high_priority_tasks": high_priority_tasks,
                "members": employees,
                "employees": employees,
                "member_count": len(employees),
                "emp_count": len(employees),
                "grouped_tasks": grouped_tasks,
                "status_display": "Активный" if not project.is_archived else "Архивный"
            })

        return result

    # ======================================================
    # Вспомогательные методы
    # ======================================================

    def _get_department_name(self, department_id: Optional[int]) -> str:
        """Получить название отдела по ID (из БД employees)"""
        if not department_id:
            return "—"
        dept = self.employees_session.get(Department, department_id)
        return dept.name if dept else "—"

    def _get_division_name(self, division_id: Optional[int]) -> str:
        """Получить название подразделения по ID (из БД employees)"""
        if not division_id:
            return "—"
        div = self.employees_session.get(Division, division_id)
        return div.name if div else "—"

    def _format_employee_name(self, emp: Employee) -> str:
        """Форматирует ФИО сотрудника"""
        parts = [emp.last_name or "", emp.first_name or ""]
        if emp.middle_name:
            parts.append(emp.middle_name)
        # Убираем пустые части
        return " ".join([p for p in parts if p]) or f"ID:{emp.id}"

    def _task_to_analytics_dto(self, task: Task, status: str, is_completed: bool) -> Dict:
        """Преобразует задачу в DTO для аналитики"""
        # Получаем теги
        task_tags = self.tag_repo.get_task_tags(task.id)
        tags_list = [tag.name for tag in task_tags]

        # Получаем создателя (из БД employees)
        creator_name = "Неизвестен"
        if task.created_by:
            creator = self.employees_session.get(Employee, task.created_by)
            if creator:
                creator_name = self._format_employee_name(creator)

        return {
            "id": task.id,
            "title": task.title,
            "description": task.description or "",
            "priority": task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
            "status": status,
            "is_overdue": task.deadline and task.deadline.date() < datetime.now().date() and not is_completed,
            "is_completed": is_completed,
            "created_at_str": task.created_at.strftime("%d.%m.%Y") if task.created_at else "",
            "due_date_str": task.deadline.strftime("%d.%m.%Y") if task.deadline else "",
            "completed_at_str": task.archived_at.strftime("%d.%m.%Y") if task.archived_at else "",
            "creator_name": creator_name,
            "tags_list": tags_list,
            "project_name": self.session.get(Project, task.project_id).name if task.project_id else ""
        }

    def _project_to_dict(self, project: Project) -> Dict:
        """Преобразует проект в словарь для карточки сотрудника"""
        # Считаем задачи проекта
        tasks = self.session.scalars(
            select(Task).where(Task.project_id == project.id)
        ).all()

        # Подсчет выполненных задач
        completed_tasks = 0
        for task in tasks:
            if task.column and task.column.is_done_column:
                completed_tasks += 1

        return {
            "id": project.id,
            "name": project.name,
            "created_at": project.created_at.strftime("%d.%m.%Y") if project.created_at else "",
            "tasks_total": len(tasks),
            "tasks_done": completed_tasks,
            "tasks": tasks,
            "is_archived": project.is_archived
        }