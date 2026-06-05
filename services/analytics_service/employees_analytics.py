# services/analytics_service/employees_analytics.py

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from models.employees import Employee, EmployeeData, Department, EmployeeNote
from models.projects import Project, EmployeeProject
from models.tasks import Task
from .analytics_base_service import AnalyticsBaseService
from .kpd_calculator import KPDCalculator


class EmployeesAnalytics(AnalyticsBaseService):
    """Аналитика по сотрудникам - вся бизнес-логика здесь"""

    def __init__(self, session):
        super().__init__(session)

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
            "active_projects_count": len(stats["active_projects"]),
            "completed_projects_count": len(stats["completed_projects"]),
            "active_tasks": stats["active_tasks"],
            "completed_tasks": stats["completed_tasks"],
            "overdue_tasks": stats["overdue_tasks"],
            "total_tasks": stats["total_tasks"],
            "tag_analytics": stats["tag_analytics"],
            "kpd": stats["kpd"],
            "kpd_percent": stats.get("kpd_percent", 0),
            "weighted_kpd": stats.get("weighted_kpd", 0),
            "overtime_hours": stats["overtime_hours"],
            "kpd_rating": stats.get("kpd_rating", 0),
            "on_time_rate": stats.get("on_time_rate", 0)
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
        return self.get_all_employees_for_cards(active_only=True)

    def get_employees_rating(self) -> List[Dict[str, Any]]:
        """Получить список сотрудников, отсортированный по КПД"""
        employees = self.get_all_employees_with_stats()
        employees.sort(key=lambda x: x.get('kpd_percent', 0), reverse=True)
        return employees

    def _get_date_range_for_period(self, period: str) -> tuple:
        """Возвращает начальную и конечную дату для выбранного периода"""
        now = datetime.now()

        if period == "all":
            return None, None
        elif period == "year":
            return datetime(now.year, 1, 1), now
        elif period == "quarter":
            quarter = (now.month - 1) // 3 + 1
            start_month = (quarter - 1) * 3 + 1
            return datetime(now.year, start_month, 1), now
        elif period == "month":
            return datetime(now.year, now.month, 1), now
        elif period == "last_30_days":
            return now - timedelta(days=30), now
        elif period == "last_90_days":
            return now - timedelta(days=90), now
        return None, None

    def get_employees_rating_by_period(self, period: str) -> List[Dict[str, Any]]:
        """Получить рейтинг сотрудников за указанный период"""
        print(f"\n📊 EmployeesAnalytics.get_employees_rating_by_period: period={period}")

        if period == "all":
            return self.get_employees_rating()

        start_date, end_date = self._get_date_range_for_period(period)
        if start_date is None:
            return self.get_employees_rating()

        print(f"   Диапазон: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")

        all_employees = self.get_all_employees_with_stats()
        tasks_by_employee = self._get_tasks_for_period(start_date, end_date)

        result = []
        for emp in all_employees:
            emp_id = emp.get("id")
            tasks_info = tasks_by_employee.get(emp_id, {
                "completed": 0, "total": 0, "kpd_percent": 0, "weighted_kpd": 0, "overtime": 0
            })

            emp_copy = emp.copy()
            emp_copy["completed_tasks"] = tasks_info["completed"]
            emp_copy["total_tasks"] = tasks_info["total"]
            emp_copy["kpd_percent"] = tasks_info["kpd_percent"]
            emp_copy["weighted_kpd"] = tasks_info["weighted_kpd"]
            emp_copy["kpd"] = tasks_info["kpd_percent"] / 100 if tasks_info["kpd_percent"] > 0 else 0
            emp_copy["overtime_hours"] = tasks_info.get("overtime", 0)
            result.append(emp_copy)

        result.sort(key=lambda x: x.get('kpd_percent', 0), reverse=True)
        print(f"   Обработано сотрудников: {len(result)}")
        return result

    def _get_tasks_for_period(self, start_date: datetime, end_date: datetime) -> Dict:
        """Получает задачи сотрудников за период и рассчитывает КПД"""
        try:
            # Завершенные задачи за период
            completed_tasks = self.session.query(Task).filter(
                Task.completed == True,
                Task.completed_at >= start_date,
                Task.completed_at <= end_date
            ).all()

            # Активные задачи, созданные в период
            active_tasks = self.session.query(Task).filter(
                Task.completed == False,
                Task.created_at >= start_date,
                Task.created_at <= end_date
            ).all()

            all_tasks = completed_tasks + active_tasks

            # Группируем по сотрудникам
            result = {}
            for task in all_tasks:
                if not task.assigned_to:
                    continue

                emp_id = task.assigned_to
                if emp_id not in result:
                    result[emp_id] = {
                        "tasks": [], "completed_count": 0, "total_count": 0, "overtime": 0.0
                    }

                result[emp_id]["tasks"].append(task)
                result[emp_id]["total_count"] += 1
                if task.completed:
                    result[emp_id]["completed_count"] += 1

            # Рассчитываем КПД
            for emp_id, data in result.items():
                if data["tasks"]:
                    kpd_result = KPDCalculator.calculate_employee_kpd(data["tasks"])
                    data["kpd_percent"] = kpd_result["total_kpd"]
                    data["weighted_kpd"] = kpd_result["weighted_kpd"]
                    data["completed"] = data["completed_count"]
                    data["total"] = data["total_count"]
                else:
                    data["kpd_percent"] = 0
                    data["weighted_kpd"] = 0
                    data["completed"] = 0
                    data["total"] = 0

            # Переработки за период
            overtimes = self.employees_session.query(EmployeeNote).filter(
                EmployeeNote.overtime_date >= start_date.date(),
                EmployeeNote.overtime_date <= end_date.date()
            ).all()

            for ot in overtimes:
                emp_id = ot.employee_id
                if emp_id not in result:
                    result[emp_id] = {
                        "tasks": [], "completed_count": 0, "total_count": 0, "overtime": 0.0,
                        "kpd_percent": 0, "weighted_kpd": 0, "completed": 0, "total": 0
                    }

                if ot.overtime_start and ot.overtime_end:
                    start = datetime.combine(ot.overtime_date, ot.overtime_start)
                    end = datetime.combine(ot.overtime_date, ot.overtime_end)
                    if end < start:
                        end = end.replace(day=end.day + 1)
                    hours = (end - start).total_seconds() / 3600
                    result[emp_id]["overtime"] += hours

            return result

        except Exception as e:
            print(f"❌ Ошибка получения задач за период: {e}")
            return {}

    def _get_employee_subordinates_kpd(self, employee_id: int) -> Dict[str, Any]:
        """
        Рассчитывает суммарный КПД подчинённых сотрудника.
        Возвращает словарь с aggregated_kpd и списком подчинённых.
        """
        from services.employee_service.employee_base_service import EmployeeBaseService

        emp_base = EmployeeBaseService(self.employees_session)
        subordinates_ids = emp_base.get_subordinates(employee_id)

        if not subordinates_ids:
            return {
                "total_kpd": 0,
                "weighted_kpd": 0,
                "subordinates_count": 0,
                "subordinates": []
            }

        total_kpd = 0
        total_weighted_kpd = 0
        subordinates_data = []

        for sub_id in subordinates_ids:
            # Получаем КПД подчинённого (без учёта его подчинённых, чтобы избежать рекурсии)
            sub_stats = self._get_employee_stats(sub_id, include_subordinates=False)
            sub_kpd = sub_stats.get("kpd_percent", 0)
            sub_weighted = sub_stats.get("weighted_kpd", 0)

            total_kpd += sub_kpd
            total_weighted_kpd += sub_weighted

            sub_emp = self.employees_session.get(Employee, sub_id)
            subordinates_data.append({
                "id": sub_id,
                "name": self._format_employee_name(sub_emp) if sub_emp else f"ID:{sub_id}",
                "kpd_percent": sub_kpd,
                "weighted_kpd": sub_weighted
            })

        return {
            "total_kpd": total_kpd,
            "weighted_kpd": total_weighted_kpd,
            "subordinates_count": len(subordinates_ids),
            "subordinates": subordinates_data
        }

    def filter_employees_by_department(self, employees_data: List[Dict], department_id: Optional[int]) -> List[Dict]:
        """Фильтрует сотрудников по отделу"""
        if not department_id or department_id == 0:
            return employees_data
        return [emp for emp in employees_data if emp.get("department_id") == department_id]

    def get_departments_list(self) -> List[Dict[str, Any]]:
        """Получить список всех отделов"""
        departments = self.employees_session.query(Department).order_by(Department.name).all()
        return [{"id": dept.id, "name": dept.name} for dept in departments]

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
        return {
            "employee_name": "Нет данных",
            "avg_kpi": 0,
            "completed_count": 0,
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0
        }

    def _get_employee_stats(self, employee_id: int, include_subordinates: bool = True) -> Dict[str, Any]:
        """
        Получить статистику сотрудника с расчётом КПД.
        Если include_subordinates=True, включает КПД подчинённых.
        """
        from sqlalchemy import select, or_

        # Проекты сотрудника
        projects_stmt = select(Project).join(
            EmployeeProject, Project.id == EmployeeProject.project_id
        ).where(EmployeeProject.employee_id == employee_id)
        all_projects = list(self.session.scalars(projects_stmt))

        active_projects = []
        completed_projects = []

        for p in all_projects:
            proj_dict = {
                "id": p.id,
                "name": p.name,
                "created_at": p.created_at.strftime("%d.%m.%Y") if p.created_at else "",
                "tasks_total": 0,
                "tasks_done": 0,
                "is_archived": p.is_archived
            }
            project_tasks = self.session.scalars(
                select(Task).where(Task.project_id == p.id)
            ).all()
            proj_dict["tasks_total"] = len(project_tasks)
            proj_dict["tasks_done"] = sum(1 for t in project_tasks
                                          if t.completed or (t.column and t.column.is_done_column))

            if p.is_archived:
                completed_projects.append(proj_dict)
            else:
                active_projects.append(proj_dict)

        # Задачи сотрудника
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
            if task.completed:
                completed_tasks += 1
            else:
                active_tasks += 1
            if task.is_overdue:
                overdue_tasks += 1

        overtime_hours = self._get_employee_overtime_hours(employee_id)
        kpd_result = KPDCalculator.calculate_employee_kpd(all_tasks)
        tag_analytics = self._get_employee_tag_analytics(employee_id, all_tasks)

        employee_data = self.session.query(EmployeeData).filter(
            EmployeeData.employee_id == employee_id
        ).first()

        # Получаем КПД подчинённых
        subordinates_kpd = {"total_kpd": 0, "weighted_kpd": 0, "subordinates_count": 0}
        if include_subordinates:
            subordinates_kpd = self._get_employee_subordinates_kpd(employee_id)

        kpd_result = KPDCalculator.calculate_employee_kpd(all_tasks)

        # ИТОГОВЫЙ КПД РУКОВОДИТЕЛЯ = собственный КПД * 0.5 + КПД подчинённых * 0.5
        own_kpd = kpd_result["total_kpd"]
        own_weighted = kpd_result["weighted_kpd"]

        if subordinates_kpd["subordinates_count"] > 0:
            # Если есть подчинённые - усредняем их КПД
            avg_sub_kpd = subordinates_kpd["total_kpd"] / subordinates_kpd["subordinates_count"]
            avg_sub_weighted = subordinates_kpd["weighted_kpd"] / subordinates_kpd["subordinates_count"]

            # Вес: 50% собственный, 50% подчинённые
            final_kpd = (own_kpd * 0.5) + (avg_sub_kpd * 0.5)
            final_weighted = (own_weighted * 0.5) + (avg_sub_weighted * 0.5)
        else:
            final_kpd = own_kpd
            final_weighted = own_weighted

        employee_data = self.session.query(EmployeeData).filter(
            EmployeeData.employee_id == employee_id
        ).first()

        return {
            "active_projects": active_projects,
            "completed_projects": completed_projects,
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
            "total_tasks": len(all_tasks),
            "tag_analytics": tag_analytics,
            "kpd": final_kpd / 100 if final_kpd > 0 else 0,
            "kpd_percent": final_kpd,
            "weighted_kpd": final_weighted,
            "own_kpd_percent": own_kpd,  # Сохраняем собственный КПД для отладки
            "subordinates_count": subordinates_kpd["subordinates_count"],
            "subordinates_kpd_avg": (subordinates_kpd["total_kpd"] / subordinates_kpd["subordinates_count"]) if
            subordinates_kpd["subordinates_count"] > 0 else 0,
            "overtime_hours": overtime_hours,
            "kpd_rating": employee_data.kpd_rating if employee_data else 0,
            "on_time_rate": employee_data.on_time_rate if employee_data else 0,
        }

    def _get_employee_tag_analytics(self, employee_id: int, tasks: List[Task]) -> List[Dict]:
        from repositories.tag_repo import TagRepo
        tag_repo = TagRepo(self.session)

        tag_stats = {}
        for task in tasks:
            task_tags = tag_repo.get_task_tags(task.id)
            for tag in task_tags:
                tag_name = tag.name
                if tag_name not in tag_stats:
                    tag_stats[tag_name] = {"tag": tag_name, "count": 0, "completed": 0, "kpd": 0.0}
                tag_stats[tag_name]["count"] += 1
                if task.completed:
                    tag_stats[tag_name]["completed"] += 1

        for tag_name, stats in tag_stats.items():
            if stats["count"] > 0:
                stats["kpd"] = round(stats["completed"] / stats["count"], 2)

        return sorted(tag_stats.values(), key=lambda x: x["count"], reverse=True)

    def _get_employee_overtime_hours(self, employee_id: int) -> float:
        try:
            from database import get_tasks_session
            overtime_session = get_tasks_session()
            if overtime_session is None:
                return 0.0

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
            print(f"❌ Ошибка получения переработок: {e}")
            return 0.0