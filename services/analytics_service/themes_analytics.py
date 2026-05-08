# services/analytics_service/themes_analytics.py

from typing import List, Dict, Any
from repositories.tag_repo import TagRepo
from models.tasks import Task
from models.projects import Project
from models.employees import Employee
from .analytics_base_service import AnalyticsBaseService


class ThemesAnalytics(AnalyticsBaseService):
    """Аналитика по темам/тегам"""

    def __init__(self, session):
        super().__init__(session)
        self.tag_repo = TagRepo(session)

    def get_themes_stats(self) -> List[Dict[str, Any]]:
        """Получить статистику по всем темам (тегам)"""
        all_tags = self.tag_repo.get_all(include_archived=False)
        result = []

        for tag in all_tags:
            task_ids = self.tag_repo.get_tasks_by_tag(tag.id)
            tasks = []
            for task_id in task_ids:
                task = self.session.get(Task, task_id)
                if task and not task.is_archived:
                    tasks.append(task)

            project_stats = self._get_project_stats_for_tag(tasks)
            employee_stats = self._get_employee_stats_for_tag(tasks)

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

        return sorted(result, key=lambda x: x["task_count"], reverse=True)

    def get_theme_card_data(self, theme_data: Dict[str, Any]) -> Dict[str, Any]:
        """Подготавливает данные для карточки темы"""
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

    def _get_project_stats_for_tag(self, tasks: List[Task]) -> Dict:
        """Получить статистику по проектам для тега"""
        project_stats = {}
        for task in tasks:
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

                is_completed = False
                if task.column:
                    is_completed = task.column.is_done_column
                if is_completed:
                    project_stats[project_name]["completed_count"] += 1

        return project_stats

    def _get_employee_stats_for_tag(self, tasks: List[Task]) -> Dict:
        """Получить статистику по сотрудникам для тега"""
        employee_stats = {}
        for task in tasks:
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

        for emp_name, stats in employee_stats.items():
            if stats["task_count"] > 0:
                stats["avg_kpi"] = round(stats["completed_count"] / stats["task_count"], 2)

        return employee_stats

    def _prepare_theme_employee_stats(self, employee_stats: List[Dict]) -> List[Dict]:
        """Подготавливает статистику сотрудников для отображения"""
        result = []
        for stat in employee_stats:
            if not isinstance(stat, dict):
                continue

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

        result.sort(key=lambda x: x.get("avg_kpi", 0), reverse=True)
        return result

    def _prepare_theme_project_stats(self, project_stats: List[Dict]) -> List[Dict]:
        """Подготавливает статистику проектов для отображения"""
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

        result.sort(key=lambda x: x.get("task_count", 0), reverse=True)
        return result