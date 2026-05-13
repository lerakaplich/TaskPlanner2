# services/analytics_service/employees_analytics.py

from typing import List, Dict, Any, Optional
from sqlalchemy import select, or_
from datetime import datetime
from models.tasks import Task
from models.projects import Project, EmployeeProject
from models.employees import Employee, EmployeeData
from repositories.tag_repo import TagRepo
from .analytics_base_service import AnalyticsBaseService
from .kpd_calculator import KPDCalculator


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
            "tag_analytics": stats["tag_analytics"],
            "kpd": stats["kpd"],
            "overtime_hours": stats["overtime_hours"]
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
            if card_data:
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

    def get_employees_rating(self) -> List[Dict[str, Any]]:
        """Получить список сотрудников, отсортированный по КПД (убывание)"""
        employees = self.get_all_employees_with_stats()
        # Сортируем по КПД (completed_tasks / total_tasks) в убывающем порядке
        employees.sort(
            key=lambda x: x.get('completed_tasks', 0) / x.get('total_tasks', 1) if x.get('total_tasks', 0) > 0 else 0,
            reverse=True
        )
        return employees

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
        """Получить статистику сотрудника с расчетом КПД по новой формуле"""
        from sqlalchemy import select, or_
        from models.tasks import Task
        from models.employees import EmployeeNote

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

        # 2. Задачи сотрудника с прогрессом
        tasks_stmt = select(Task).where(
            or_(
                Task.assigned_to == employee_id,
                Task.created_by == employee_id
            )
        )
        all_tasks = list(self.session.scalars(tasks_stmt))

        # Получаем прогресс для каждой задачи
        from models.task_progress import TaskProgress
        tasks_data = []
        for task in all_tasks:
            # Получаем прогресс
            progress = self.session.query(TaskProgress).filter(
                TaskProgress.task_id == task.id
            ).first()
            progress_percent = progress.progress_percent if progress else 0

            is_completed = False
            if task.column:
                is_completed = task.column.is_done_column

            task_data = {
                "id": task.id,
                "title": task.title,
                "priority": task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
                "difficulty": task.difficulty or 0,
                "progress_percent": progress_percent,
                "is_completed": is_completed or task.is_archived,
                "due_date_str": task.deadline.strftime("%d.%m.%Y") if task.deadline else "",
                "completed_at_str": task.archived_at.strftime("%d.%m.%Y") if task.archived_at else ""
            }
            tasks_data.append(task_data)

        # 3. Часы переработок
        overtime_hours = self._get_employee_overtime_hours(employee_id)

        # 4. Расчет КПД по новой формуле
        kpd_result = KPDCalculator.calculate_employee_kpd(tasks_data, overtime_hours)

        # Подсчет активных/выполненных задач
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

        # 5. Аналитика по тегам
        tag_analytics = self._get_employee_tag_analytics(employee_id, all_tasks)

        return {
            "active_projects": active_projects,
            "completed_projects": completed_projects,
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
            "total_tasks": len(all_tasks),
            "tag_analytics": tag_analytics,
            "kpd": kpd_result["total_kpd"] / 100,
            "kpd_percent": kpd_result["total_kpd"],
            "weighted_kpd": kpd_result["weighted_kpd"],
            "overtime_hours": overtime_hours,
            # Добавляем для тултипа дополнительную информацию
            "kpd_details": {
                "completed_count": completed_tasks,
                "total_count": len(all_tasks),
                "weighted_score": kpd_result["weighted_kpd"],
                "overtime_penalty": 1.0 - (
                    kpd_result["total_kpd"] / kpd_result["weighted_kpd"] if kpd_result["weighted_kpd"] > 0 else 0)
            }
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

    def _get_employee_overtime_hours(self, employee_id: int) -> float:
        """Получить общее количество часов переработок сотрудника"""
        try:
            from database import get_tasks_session
            from models.employees import EmployeeNote  # Исправлено: используем EmployeeNote вместо OvertimeNote

            overtime_session = get_tasks_session()
            if overtime_session is None:
                return 0.0

            from datetime import datetime
            overtimes = overtime_session.query(EmployeeNote).filter(
                EmployeeNote.employee_id == employee_id
            ).all()

            total_hours = 0.0
            for ot in overtimes:
                if ot.overtime_start and ot.overtime_end:
                    start = datetime.combine(datetime.today(), ot.overtime_start)
                    end = datetime.combine(datetime.today(), ot.overtime_end)
                    if end < start:
                        end = end.replace(day=end.day + 1)
                    hours = (end - start).total_seconds() / 3600
                    total_hours += hours

            overtime_session.close()
            return round(total_hours, 1)
        except Exception as e:
            print(f"❌ Ошибка при получении переработок для сотрудника {employee_id}: {e}")
            return 0.0