# services/analytics_service/employees_analytics.py

from typing import List, Dict, Any, Optional
from sqlalchemy import select, or_
from datetime import datetime
from models.tasks import Task
from models.projects import Project, EmployeeProject
from models.employees import Employee, EmployeeData
from repositories.tag_repo import TagRepo
from .analytics_base_service import AnalyticsBaseService


class EmployeesAnalytics(AnalyticsBaseService):
    """Аналитика по сотрудникам"""

    def __init__(self, session):
        super().__init__(session)
        self.tag_repo = TagRepo(session)

    def get_employee_card_data(self, employee_id: int) -> Dict[str, Any]:
        """Получить данные сотрудника для карточки EmployeeCard"""
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
        """Получить всех сотрудников с данными для карточек"""
        from sqlalchemy import select
        stmt = select(Employee).order_by(Employee.last_name)
        employees = list(self.employees_session.scalars(stmt))

        result = []
        for emp in employees:
            if active_only:
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
        from sqlalchemy import select
        stmt = select(Employee).order_by(Employee.last_name)
        employees = list(self.employees_session.scalars(stmt))

        result = []
        for emp in employees:
            emp_data = self.session.query(EmployeeData).filter(
                EmployeeData.employee_id == emp.id
            ).first()
            is_active = emp_data.is_active if emp_data else True

            if not is_active:
                continue

            card_data = self.get_employee_card_data(emp.id)
            if card_data:
                result.append(card_data)

        return result

    def filter_employees_by_name(self, employees_data: List[Dict], search_text: str) -> List[Dict]:
        """Фильтрует сотрудников по имени"""
        if not search_text:
            return employees_data
        search_lower = search_text.lower()
        return [
            emp for emp in employees_data
            if search_lower in emp.get("name", "").lower()
               or search_lower in emp.get("last_name", "").lower()
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

    def _get_employee_stats(self, employee_id: int) -> Dict[str, Any]:
        """Получить статистику сотрудника"""
        from sqlalchemy import select, or_

        # 1. Проекты сотрудника
        projects_stmt = select(Project).join(
            EmployeeProject, Project.id == EmployeeProject.project_id
        ).where(EmployeeProject.employee_id == employee_id)

        all_projects = list(self.session.scalars(projects_stmt))

        active_projects = []
        completed_projects = []

        for p in all_projects:
            proj_dict = self._project_to_dict(p)
            if p.is_archived:
                completed_projects.append(proj_dict)
            else:
                active_projects.append(proj_dict)

        # 2. Задачи сотрудника
        tasks_stmt = select(Task).where(
            or_(
                Task.assigned_to == employee_id,
                Task.created_by == employee_id
            )
        )
        all_tasks = list(self.session.scalars(tasks_stmt))

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

            if task.deadline and not is_completed and not task.is_archived:
                if task.deadline.date() < datetime.now().date():
                    overdue_tasks += 1

        # 3. Аналитика по тегам
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

                is_completed = False
                if task.column:
                    is_completed = task.column.is_done_column
                if is_completed or task.is_archived:
                    tag_stats[tag_name]["completed"] += 1

        for tag_name, stats in tag_stats.items():
            if stats["count"] > 0:
                stats["kpd"] = round(stats["completed"] / stats["count"], 2)

        return sorted(tag_stats.values(), key=lambda x: x["count"], reverse=True)