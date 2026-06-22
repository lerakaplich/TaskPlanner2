# services/projects_service/project_dialog_service.py
from typing import List, Dict, Optional, Any
from PyQt6.QtCore import QDate


class ProjectDialogService:
    """Сервис для работы с диалогами проектов"""

    def __init__(self, project_service, current_user_id: int = None):
        self.project_service = project_service
        self.current_user_id = current_user_id

    def get_employees_for_selector(self) -> List[Dict]:
        """Возвращает список сотрудников для селектора"""
        return self.project_service.load_employees_for_selector()

    def get_employees_for_manager_combo(self) -> List[Dict]:
        """Возвращает список сотрудников для комбобокса куратора"""
        return self.project_service.load_employees_for_manager_combo()

    def get_employee_display_name(self, employee_id: int) -> str:
        """Возвращает отображаемое имя сотрудника"""
        return self.project_service.get_employee_display_name(employee_id)

    def get_template_columns(self) -> List[Dict]:
        """Возвращает шаблонные колонки"""
        return self.project_service.get_template_columns_for_selector()

    def validate_project_data(self, data: Dict) -> Optional[str]:
        """Валидирует данные проекта"""
        return self.project_service.validate_project_data(data)

    def prepare_creation_data(self, raw_data: Dict) -> Dict:
        """Подготавливает данные для создания проекта"""
        return self.project_service.prepare_project_data_for_creation(raw_data, self.current_user_id)

    def prepare_edit_data(self, project_dto) -> Dict:
        """Подготавливает данные для редактирования проекта"""
        return self.project_service.prepare_edit_dialog_data(project_dto)

    def compare_changes(self, original: Dict, current: Dict) -> bool:
        """Сравнивает изменения в данных проекта"""
        return self.project_service.compare_project_changes(original, current)

    def ensure_admins_in_participants(self, participants: List[Dict], admins: List[Dict]) -> List[Dict]:
        """Убеждается, что администраторы присутствуют в списке участников"""
        return self.project_service.ensure_admins_in_participants(participants, admins)

    def get_selected_columns_by_keys(self, all_columns: List[Dict], selected_keys: List[str]) -> List[Dict]:
        """Возвращает выбранные колонки по ключам"""
        return self.project_service.get_selected_columns_by_keys(all_columns, selected_keys)

    def filter_employees_by_search(self, employees: List[Dict], search_text: str) -> List[Dict]:
        """Фильтрует сотрудников по поисковому запросу"""
        return self.project_service.filter_employees_by_search(employees, search_text)

    def sort_employees_for_selector(self, employees: List[Dict], selected_ids: set) -> List[Dict]:
        """Сортирует сотрудников для селектора"""
        return self.project_service.sort_employees_for_selector(employees, selected_ids)

    def load_employee_selector_data(self) -> Dict:
        """Загружает данные для селектора сотрудников"""
        return self.project_service.load_employee_selector_data()

    def get_current_date(self) -> str:
        """Возвращает текущую дату в формате DD.MM.YYYY"""
        return QDate.currentDate().toString("dd.MM.yyyy")