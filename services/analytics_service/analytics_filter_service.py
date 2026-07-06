# services/analytics_service/analytics_filter_service.py

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from models.tasks import Task
from models.employees import Employee, EmployeeNote, Department
from .kpd_calculator import KPDCalculator


class AnalyticsFilterService:
    """Сервис для фильтрации и расчёта данных аналитики"""

    def __init__(self, session, employees_session):
        self.session = session
        self.employees_session = employees_session

    # ==================== ПЕРИОДЫ ====================

    def get_period_options(self) -> List[Dict[str, str]]:
        """Возвращает список доступных периодов"""
        return [
            {"name": "Все время", "value": "all"},
            {"name": "Текущий год", "value": "year"},
            {"name": "Текущий квартал", "value": "quarter"},
            {"name": "Текущий месяц", "value": "month"},
            {"name": "Последние 30 дней", "value": "last_30_days"},
            {"name": "Последние 90 дней", "value": "last_90_days"}
        ]

    def get_date_range(self, period: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Возвращает начальную и конечную дату для периода"""
        now = datetime.now()

        ranges = {
            "all": (None, None),
            "year": (datetime(now.year, 1, 1), now),
            "quarter": (datetime(now.year, (now.month - 1) // 3 * 3 + 1, 1), now),
            "month": (datetime(now.year, now.month, 1), now),
            "last_30_days": (now - timedelta(days=30), now),
            "last_90_days": (now - timedelta(days=90), now),
        }
        return ranges.get(period, (None, None))

    # ==================== ФИЛЬТРАЦИЯ ПО ОТДЕЛУ ====================

    def filter_by_department(self, employees_data: List[Dict], filter_value: Any) -> List[Dict]:
        """Фильтрует сотрудников по отделу"""
        if filter_value == "all":
            return employees_data

        department_id = self._extract_department_id(filter_value)
        if department_id:
            return [emp for emp in employees_data if emp.get("department_id") == department_id]
        return employees_data

    def _extract_department_id(self, filter_value) -> Optional[int]:
        """Извлекает ID отдела из значения фильтра"""
        if isinstance(filter_value, int):
            return filter_value
        if isinstance(filter_value, str):
            if filter_value.startswith("dept_"):
                try:
                    return int(filter_value.split("_")[1])
                except (ValueError, IndexError):
                    return None
            if filter_value.isdigit():
                return int(filter_value)
        return None

    def get_tasks_for_period(self, start_date: datetime, end_date: datetime) -> Dict[int, Dict]:
        """
        Получает задачи сотрудников за период и рассчитывает КПД.
        Возвращает: {employee_id: {tasks, completed_count, total_count, kpd_percent, weighted_kpd, overtime}}
        """
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
            self._add_overtime_for_period(result, start_date, end_date)

            return result

        except Exception as e:
            print(f"❌ Ошибка получения задач за период: {e}")
            return {}

    def _add_overtime_for_period(self, result: Dict, start_date: datetime, end_date: datetime):
        """Добавляет переработки за период в результат"""
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

    # ==================== ФИЛЬТРАЦИЯ СОТРУДНИКОВ ====================

    def filter_employees_by_period(
            self,
            employees_data: List[Dict],
            period: str
    ) -> List[Dict]:
        """Фильтрует сотрудников по периоду с пересчётом КПД"""
        if period == "all" or not employees_data:
            return employees_data

        start_date, end_date = self.get_date_range(period)
        if start_date is None:
            return employees_data

        tasks_by_employee = self.get_tasks_for_period(start_date, end_date)

        result = []
        for emp in employees_data:
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

        return result

    # ==================== ОТДЕЛЫ ====================

    def get_departments(self) -> List[Dict[str, Any]]:
        """Получить список всех отделов"""
        departments = self.employees_session.query(Department).order_by(Department.name).all()
        return [{"id": dept.id, "name": dept.name} for dept in departments]