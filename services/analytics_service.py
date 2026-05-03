# services/analytics_service.py

from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_

from models.tasks import Task, TaskTag, Tag
from models.projects import Project, EmployeeProject, BoardColumn
from models.employees import Employee, Department, Division  # ← ИСПРАВЛЕНО
from repositories.tag_repo import TagRepo


class AnalyticsService:
    """Сервис для аналитики по сотрудникам, темам и проектам"""

    def __init__(self, session: Session):
        self.session = session
        self.tag_repo = TagRepo(session)
        self.current_user_id = None

    def set_current_user_id(self, user_id: int):
        """Устанавливает ID текущего пользователя"""
        self.current_user_id = user_id
        print(f"📊 AnalyticsService: current_user_id = {user_id}")

    # ======================================================
    # Аналитика по сотрудникам
    # ======================================================

    def get_all_employees_with_stats(self) -> List[Dict[str, Any]]:
        """
        Получить всех сотрудников со статистикой:
        - активные проекты (где сотрудник участник)
        - выполненные задачи
        - активные задачи
        - просроченные задачи
        - аналитика по тегам
        """
        # Получаем всех сотрудников
        stmt = select(Employee).order_by(Employee.last_name)  # ← ИСПРАВЛЕНО
        employees = list(self.session.scalars(stmt))

        result = []
        for emp in employees:
            stats = self._get_employee_stats(emp.id)
            result.append({
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
            })

        return result

    def _get_employee_stats(self, employee_id: int) -> Dict[str, Any]:
        """Получить статистику сотрудника"""
        from datetime import datetime

        # 1. Проекты сотрудника
        projects_stmt = select(Project).join(
            EmployeeProject, Project.id == EmployeeProject.project_id
        ).where(EmployeeProject.employee_id == employee_id)

        all_projects = list(self.session.scalars(projects_stmt))

        # Активные проекты (не архивные) и выполненные проекты (архивные)
        active_projects = []
        completed_projects = []

        print(f"📊 Сотрудник {employee_id}: найдено проектов: {len(all_projects)}")

        for p in all_projects:
            proj_dict = self._project_to_dict(p)
            print(f"   Проект: {p.name}, is_archived={p.is_archived}")
            if p.is_archived:
                completed_projects.append(proj_dict)
            else:
                active_projects.append(proj_dict)

        # 2. Задачи сотрудника (как исполнитель или создатель)
        tasks_stmt = select(Task).where(
            or_(
                Task.assigned_to == employee_id,
                Task.created_by == employee_id
            )
        )
        all_tasks = list(self.session.scalars(tasks_stmt))

        print(f"   Найдено задач: {len(all_tasks)}")

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
        print(f"   Аналитика по темам: {len(tag_analytics)}")

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
                    emp = self.session.get(Employee, task.assigned_to)  # ← ИСПРАВЛЕНО
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
                emp = self.session.get(Employee, member.employee_id)  # ← ИСПРАВЛЕНО
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

            print(f"📊 Проект: {project.name}")
            print(f"   Всего задач: {len(tasks)}")
            print(f"   grouped_tasks: to_do={len(grouped_tasks['to_do'])}, in_progress={len(grouped_tasks['in_progress'])}, review={len(grouped_tasks['review'])}, completed={len(grouped_tasks['completed'])}")
            print(f"   Сотрудников: {len(employees)}")

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

    def _task_to_analytics_dto(self, task: Task, status: str, is_completed: bool) -> Dict:
        """Преобразует задачу в DTO для аналитики"""
        # Получаем теги
        task_tags = self.tag_repo.get_task_tags(task.id)
        tags_list = [tag.name for tag in task_tags]

        # Получаем создателя
        creator_name = "Неизвестен"
        if task.created_by:
            creator = self.session.get(Employee, task.created_by)  # ← ИСПРАВЛЕНО
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

    def _format_employee_name(self, emp: Employee) -> str:  # ← ИСПРАВЛЕНО
        """Форматирует ФИО сотрудника"""
        parts = [emp.last_name, emp.first_name]
        if emp.middle_name:
            parts.append(emp.middle_name)
        return " ".join(parts)

    def _get_department_name(self, department_id: Optional[int]) -> str:
        """Получить название отдела по ID"""
        if not department_id:
            return "—"
        dept = self.session.get(Department, department_id)  # ← ИСПРАВЛЕНО
        return dept.name if dept else "—"

    def _get_division_name(self, division_id: Optional[int]) -> str:
        """Получить название подразделения по ID"""
        if not division_id:
            return "—"
        div = self.session.get(Division, division_id)  # ← ИСПРАВЛЕНО
        return div.name if div else "—"

    def _project_to_dict(self, project: Project) -> Dict:
        """Преобразует проект в словарь для карточки сотрудника"""
        from datetime import datetime

        # Считаем задачи проекта
        tasks = self.session.scalars(
            select(Task).where(Task.project_id == project.id)
        ).all()

        # Подсчет выполненных задач
        completed_tasks = 0
        for task in tasks:
            if task.column and task.column.is_done_column:
                completed_tasks += 1

        print(f"      Проект {project.name}: задач={len(tasks)}, выполнено={completed_tasks}")

        return {
            "id": project.id,
            "name": project.name,
            "created_at": project.created_at.strftime("%d.%m.%Y") if project.created_at else "",
            "tasks_total": len(tasks),
            "tasks_done": completed_tasks,
            "tasks": tasks,
            "is_archived": project.is_archived
        }