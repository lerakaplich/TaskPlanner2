# services/gantt_service.py

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from PyQt6.QtGui import QPainter
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from database import get_employees_session
from models.tasks import Task
from models.projects import Project
from models.employees import Employee


class GanttService:
    """Сервис для работы с диаграммой Ганта"""

    def __init__(self, session: Session, current_user_id: int = None):
        self.session = session
        self.employees_session = get_employees_session()
        self.current_user_id = current_user_id

    def __del__(self):
        try:
            if self.employees_session:
                self.employees_session.close()
        except:
            pass

    def set_current_user_id(self, user_id: int):
        self.current_user_id = user_id

    def get_projects_for_gantt(self) -> List[Dict]:
        """Получает список проектов для выбора"""
        stmt = select(Project).where(Project.is_archived == False).order_by(Project.name)
        projects = self.session.scalars(stmt).all()
        return [{"id": p.id, "name": p.name} for p in projects]

    def get_project_tasks_for_gantt(self, project_id: int, filters: Dict = None) -> Dict:
        """
        Получает задачи проекта с учетом фильтров.
        filters: {'my_tasks': bool, 'overdue': bool, 'in_progress': bool, 'completed': bool, 'search': str}
        """
        project = self.session.get(Project, project_id)
        if not project:
            return self._get_empty_result()

        stmt = select(Task).where(
            Task.project_id == project_id,
            Task.is_archived == False
        )
        tasks = self.session.scalars(stmt).all()

        if not tasks:
            return self._get_empty_result()

        today = datetime.now().date()
        gantt_tasks = []

        for task in tasks:
            # Применяем фильтры
            if filters:
                if filters.get('my_tasks') and task.assigned_to != self.current_user_id:
                    continue
                if filters.get('overdue') and not self._is_overdue(task, today):
                    continue
                if filters.get('completed') and not self._is_completed(task):
                    continue
                if filters.get('in_progress') and (self._is_completed(task) or self._is_overdue(task, today)):
                    continue
                if filters.get('search'):
                    search = filters['search'].lower()
                    if search not in task.title.lower():
                        continue

            assignee_name = self._get_employee_name(task.assigned_to) if task.assigned_to else ""
            is_completed = self._is_completed(task)
            is_overdue = self._is_overdue(task, today)
            priority_value = task.priority.value if hasattr(task.priority, 'value') else str(task.priority)
            is_critical = priority_value in ["high", "critical"]

            start_date = task.created_at.date() if task.created_at else today
            end_date = task.deadline.date() if task.deadline else start_date + timedelta(days=7)

            gantt_tasks.append({
                "id": task.id,
                "title": task.title,
                "description": task.description or "",
                "start_date": start_date,
                "end_date": end_date,
                "assignee": assignee_name,
                "assignee_id": task.assigned_to,
                "is_critical": is_critical,
                "dependencies": [],
                "children": [],
                "project_id": task.project_id,
                "status": task.column.name if task.column else "unknown",
                "is_completed": is_completed,
                "is_overdue": is_overdue,
                "duration_days": (end_date - start_date).days + 1,
                "priority": priority_value
            })

        if not gantt_tasks:
            return self._get_empty_result()

        start = min(t["start_date"] for t in gantt_tasks)
        end = max(t["end_date"] for t in gantt_tasks)
        total = len(gantt_tasks)
        completed = sum(1 for t in gantt_tasks if t["is_completed"])
        overdue = sum(1 for t in gantt_tasks if t["is_overdue"])

        return {
            "tasks": gantt_tasks,
            "project_start": start,
            "project_end": end,
            "total_tasks": total,
            "completed_tasks": completed,
            "overdue_tasks": overdue,
            "in_progress_tasks": total - completed,
            "project_name": project.name
        }

    def _is_completed(self, task: Task) -> bool:
        return task.column and task.column.is_done_column

    def _is_overdue(self, task: Task, today: datetime.date) -> bool:
        if task.deadline and not self._is_completed(task):
            return task.deadline.date() < today
        return False

    def _get_empty_result(self) -> Dict:
        today = datetime.now().date()
        return {
            "tasks": [],
            "project_start": today,
            "project_end": today + timedelta(days=30),
            "total_tasks": 0,
            "completed_tasks": 0,
            "overdue_tasks": 0,
            "in_progress_tasks": 0,
            "project_name": ""
        }

    def _get_employee_name(self, employee_id: int) -> str:
        try:
            employee = self.employees_session.get(Employee, employee_id)
            if employee:
                name = f"{employee.last_name} {employee.first_name[0] if employee.first_name else ''}."
                if employee.middle_name:
                    name += f" {employee.middle_name[0]}."
                return name
        except Exception as e:
            print(f"⚠️ Ошибка получения имени сотрудника: {e}")
        return ""

    def export_to_image(self, scene, filepath: str) -> bool:
        """Экспорт диаграммы в изображение"""
        try:
            from PyQt6.QtGui import QPixmap
            rect = scene.sceneRect()
            pixmap = QPixmap(int(rect.width()), int(rect.height()))
            pixmap.fill()
            painter = QPainter(pixmap)
            scene.render(painter)
            painter.end()
            return pixmap.save(filepath)
        except Exception as e:
            print(f"Ошибка экспорта: {e}")
            return False

    def add_task(self, project_id: int, title: str, start_date: datetime, end_date: datetime, assigned_to: int = None) -> Optional[int]:
        """Создает новую задачу"""
        try:
            new_task = Task(
                project_id=project_id,
                title=title,
                description="",
                deadline=end_date,
                created_at=start_date,
                created_by=self.current_user_id,
                assigned_to=assigned_to,
                priority="medium",
                position=0
            )
            self.session.add(new_task)
            self.session.commit()
            return new_task.id
        except Exception as e:
            self.session.rollback()
            print(f"Ошибка создания задачи: {e}")
            return None

    def update_task_dates(self, task_id: int, start_date: datetime.date, end_date: datetime.date) -> bool:
        task = self.session.get(Task, task_id)
        if task:
            if hasattr(task, 'deadline'):
                task.deadline = datetime.combine(end_date, datetime.min.time())
            self.session.commit()
            return True
        return False

    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        task = self.session.get(Task, task_id)
        if not task:
            return None
        return {
            "id": task.id,
            "title": task.title,
            "start_date": task.created_at.date() if task.created_at else datetime.now().date(),
            "end_date": task.deadline.date() if task.deadline else datetime.now().date() + timedelta(days=7),
            "assignee": self._get_employee_name(task.assigned_to) if task.assigned_to else "",
            "assignee_id": task.assigned_to
        }