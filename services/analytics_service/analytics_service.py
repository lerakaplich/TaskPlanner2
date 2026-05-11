# services/analytics_service/analytics_service.py

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from .analytics_base_service import AnalyticsBaseService
from .employees_analytics import EmployeesAnalytics
from .projects_analytics import ProjectsAnalytics
from .themes_analytics import ThemesAnalytics


class AnalyticsService:
    """Главный сервис аналитики (фасад)"""

    def __init__(self, session: Session):
        self.session = session
        self.base = AnalyticsBaseService(session)
        self.employees = EmployeesAnalytics(session)
        self.projects = ProjectsAnalytics(session)
        self.themes = ThemesAnalytics(session)
        self.current_user_id = None

    def set_current_user_id(self, user_id: int):
        """Устанавливает ID текущего пользователя"""
        self.current_user_id = user_id
        print(f"📊 AnalyticsService: current_user_id = {user_id}")

    # ======================================================
    # Прокси для карточек задач
    # ======================================================
    def get_task_card_data(self, task_data: Dict) -> Dict:
        return self.base.get_task_card_data(task_data)

    def get_task_card_background_color(self, task_data: Dict) -> str:
        return self.base.get_task_card_background_color(task_data)

    def get_task_card_border_color(self, task_data: Dict) -> str:
        return self.base.get_task_card_border_color(task_data)

    # ======================================================
    # Прокси для сотрудников
    # ======================================================
    def get_employee_card_data(self, employee_id: int) -> Dict[str, Any]:
        return self.employees.get_employee_card_data(employee_id)

    def get_all_employees_for_cards(self, active_only: bool = True) -> List[Dict[str, Any]]:
        return self.employees.get_all_employees_for_cards(active_only)

    def get_all_employees_with_stats(self) -> List[Dict[str, Any]]:
        return self.employees.get_all_employees_with_stats()

    def get_employees_rating(self) -> List[Dict[str, Any]]:
        """Получить рейтинг сотрудников по КПД (от лучшего к худшему)"""
        return self.employees.get_employees_rating()

    def filter_employees_by_name(self, employees_data: List[Dict], search_text: str) -> List[Dict]:
        return self.employees.filter_employees_by_name(employees_data, search_text)

    def get_empty_employee_stats(self) -> Dict:
        return self.employees.get_empty_employee_stats()

    # ======================================================
    # Прокси для проектов
    # ======================================================
    def get_projects_stats(self) -> List[Dict[str, Any]]:
        return self.projects.get_projects_stats()

    def get_project_card_data(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.projects.get_project_card_data(project_data)

    def get_status_name(self, status_key: str) -> str:
        return self.projects.get_status_name(status_key)

    def has_tasks_in_project(self, project_data: Dict) -> bool:
        return self.projects.has_tasks_in_project(project_data)

    # ======================================================
    # Прокси для тем
    # ======================================================
    def get_themes_stats(self) -> List[Dict[str, Any]]:
        return self.themes.get_themes_stats()

    def get_theme_card_data(self, theme_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.themes.get_theme_card_data(theme_data)