# repositories/kpd_repo.py

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta

from models.employees import EmployeeData, Employee
from models.tasks import Task


class KPDRepo:
    """Репозиторий для работы с КПД и аналитикой"""

    def __init__(self, session: Session):
        self.session = session

    def get_employee_kpd_history(self, employee_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Получить историю КПД сотрудника за период"""
        # Здесь нужна отдельная таблица для истории КПД
        # Пока возвращаем текущее значение
        emp_data = self.session.scalar(
            select(EmployeeData).where(EmployeeData.employee_id == employee_id)
        )

        if not emp_data:
            return []

        # Получаем выполненные задачи за период
        since_date = datetime.now() - timedelta(days=days)
        tasks = self.session.scalars(
            select(Task).where(
                Task.assigned_to == employee_id,
                Task.completed_at >= since_date,
                Task.completed_at.isnot(None)
            ).order_by(Task.completed_at)
        ).all()

        history = []
        running_avg = 0.0
        for i, task in enumerate(tasks, 1):
            running_avg = (running_avg * (i - 1) + task.kpd_score) / i
            history.append({
                "date": task.completed_at,
                "task_id": task.id,
                "task_title": task.title,
                "kpd_score": task.kpd_score,
                "running_avg": round(running_avg, 2)
            })

        return history

    def get_team_kpd_ranking(self, department_id: int = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Рейтинг КПД по команде/отделу"""
        query = (
            select(EmployeeData, Employee)
            .join(Employee, EmployeeData.employee_id == Employee.id)
            .where(EmployeeData.tasks_completed_total > 0)
            .order_by(desc(EmployeeData.kpd_rating))
            .limit(limit)
        )

        if department_id:
            query = query.where(Employee.department_id == department_id)

        results = []
        for emp_data, employee in self.session.execute(query):
            results.append({
                "employee_id": employee.id,
                "full_name": f"{employee.last_name} {employee.first_name}",
                "position": employee.position,
                "kpd_rating": emp_data.kpd_rating,
                "kpd_level": emp_data.kpd_level,
                "on_time_rate": emp_data.on_time_rate,
                "tasks_completed": emp_data.tasks_completed_total
            })

        return results

    def get_project_kpd_stats(self, project_id: int) -> Dict[str, Any]:
        """Статистика КПД по проекту"""
        from models.projects import BoardColumn

        # Получаем все задачи проекта
        tasks = self.session.scalars(
            select(Task).where(
                Task.project_id == project_id,
                Task.completed_at.isnot(None)
            )
        ).all()

        if not tasks:
            return {
                "total_tasks": 0,
                "avg_kpd": 0.0,
                "tasks_by_priority": {},
                "top_performers": []
            }

        # Средний КПД
        avg_kpd = sum(t.kpd_score for t in tasks) / len(tasks)

        # Распределение по приоритетам
        priority_stats = {}
        for task in tasks:
            priority = task.priority.value
            if priority not in priority_stats:
                priority_stats[priority] = {"count": 0, "avg_kpd": 0.0}
            priority_stats[priority]["count"] += 1
            priority_stats[priority]["avg_kpd"] = (
                    (priority_stats[priority]["avg_kpd"] * (priority_stats[priority]["count"] - 1) + task.kpd_score)
                    / priority_stats[priority]["count"]
            )

        # Лучшие исполнители
        from models.employees import Employee

        performers = self.session.execute(
            select(Employee, func.count(Task.id), func.avg(Task.kpd_score))
            .join(Task, Employee.id == Task.assigned_to)
            .where(Task.project_id == project_id, Task.completed_at.isnot(None))
            .group_by(Employee.id)
            .order_by(func.avg(Task.kpd_score).desc())
            .limit(5)
        ).all()

        top_performers = [
            {
                "employee_id": emp.id,
                "name": f"{emp.last_name} {emp.first_name}",
                "tasks_count": count,
                "avg_kpd": round(float(avg_kpd), 2)
            }
            for emp, count, avg_kpd in performers
        ]

        return {
            "total_tasks": len(tasks),
            "avg_kpd": round(avg_kpd, 2),
            "tasks_by_priority": priority_stats,
            "top_performers": top_performers
        }