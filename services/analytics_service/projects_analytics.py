# services/analytics_service/projects_analytics.py

from typing import List, Dict, Any
from sqlalchemy import select
from datetime import datetime
from models.tasks import Task
from models.projects import Project, EmployeeProject
from models.employees import Employee
from .analytics_base_service import AnalyticsBaseService


class ProjectsAnalytics(AnalyticsBaseService):
    """Аналитика по проектам"""

    def get_projects_stats(self) -> List[Dict[str, Any]]:
        """Получить статистику по всем проектам"""
        from sqlalchemy import select
        stmt = select(Project).order_by(Project.name)
        projects = list(self.session.scalars(stmt))

        result = []
        for project in projects:
            # Задачи проекта
            tasks = self.session.scalars(
                select(Task).where(Task.project_id == project.id)
            ).all()

            # Группируем задачи по статусам
            grouped_tasks = self._group_tasks_by_status(tasks)

            # Статистика задач
            active_tasks = 0
            completed_tasks = 0
            overdue_tasks = 0
            high_priority_tasks = 0

            for task in tasks:
                is_completed = False
                if task.column:
                    is_completed = task.column.is_done_column

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
            employees = self._get_project_employees(project.id, tasks)

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

    def get_project_card_data(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Подготавливает данные для карточки проекта"""
        grouped_tasks = self._prepare_grouped_tasks(project_data.get("grouped_tasks", {}))
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

    def _group_tasks_by_status(self, tasks: List[Task]) -> Dict:
        """Группирует задачи по статусам"""
        grouped_tasks = {
            "to_do": [],
            "in_progress": [],
            "review": [],
            "completed": []
        }

        for task in tasks:
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

            task_dto = self._task_to_analytics_dto(task, status, is_completed)

            if status in grouped_tasks:
                grouped_tasks[status].append(task_dto)
            else:
                grouped_tasks["to_do"].append(task_dto)

        return grouped_tasks

    def _get_project_employees(self, project_id: int, tasks: List[Task]) -> List[Dict]:
        """Получить участников проекта со статистикой"""
        from sqlalchemy import select
        members_stmt = select(EmployeeProject).where(
            EmployeeProject.project_id == project_id
        )
        members = list(self.session.scalars(members_stmt))

        employees = []
        for member in members:
            emp = self.employees_session.get(Employee, member.employee_id)
            if emp:
                emp_tasks = [t for t in tasks if t.assigned_to == emp.id]
                active = sum(
                    1 for t in emp_tasks if not (t.column and t.column.is_done_column) and not t.is_archived)
                completed = sum(1 for t in emp_tasks if (t.column and t.column.is_done_column) or t.is_archived)

                # ✅ ИСПРАВЛЕНО: проверяем роль вместо is_admin
                is_admin = member.role == 'project_manager'

                employees.append({
                    "id": emp.id,
                    "name": self._format_employee_name(emp),
                    "is_admin": is_admin,
                    "active_tasks": active,
                    "completed_tasks": completed,
                    "active": active,
                    "completed": completed
                })

        return employees

    def _prepare_grouped_tasks(self, grouped_tasks: Dict) -> Dict:
        """Подготавливает сгруппированные задачи для отображения"""
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
                if isinstance(task, dict):
                    task_dict = task
                else:
                    task_dict = self._task_to_analytics_dto(
                        task,
                        status_key,
                        status_key == "completed"
                    )
                task_dict["status_display"] = status_map.get(status_key, status_key)
                result[status_key].append(task_dict)

        return result

    def _prepare_employees_data(self, employees: List) -> List[Dict]:
        """Подготавливает данные сотрудников для отображения"""
        result = []
        for emp in employees:
            if isinstance(emp, dict):
                emp_dict = emp.copy()
            else:
                emp_dict = {
                    "id": getattr(emp, 'id', 0),
                    "name": self._format_employee_name(emp) if hasattr(emp, 'last_name') else str(emp),
                    "is_admin": getattr(emp, 'is_admin', False),  # ✅ уже использует getattr с дефолтом
                    "active_tasks": getattr(emp, 'active_tasks', 0),
                    "completed_tasks": getattr(emp, 'completed_tasks', 0),
                    "active": getattr(emp, 'active', 0),
                    "completed": getattr(emp, 'completed', 0)
                }

            emp_dict["employee_name"] = emp_dict.get("name", "Неизвестен")
            emp_dict["active"] = emp_dict.get("active_tasks", emp_dict.get("active", 0))
            emp_dict["completed"] = emp_dict.get("completed_tasks", emp_dict.get("completed", 0))
            result.append(emp_dict)

        return result