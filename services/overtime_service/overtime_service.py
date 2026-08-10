# services/overtime_service/overtime_service.py

from typing import List, Dict, Optional, Tuple
from PyQt6.QtCore import QDate, QTime
from sqlalchemy.orm import Session

from server_app.database import get_tasks_session, get_employees_session
from .overtime_base_service import OvertimeBaseService
from .overtime_crud_service import OvertimeCrudService
from .overtime_import_service import OvertimeImportService
from .overtime_export_service import OvertimeExportService


class OvertimeService:
    """Главный сервис для работы с переработками (фасад)"""

    def __init__(self, session: Session = None):
        self.session = session or get_tasks_session()
        self.employees_session = get_employees_session()
        self._own_session = session is None

        self.base = OvertimeBaseService()
        self.crud = OvertimeCrudService(self.session, self.employees_session)
        self.importer = OvertimeImportService(self.session, self.employees_session)
        self.exporter = OvertimeExportService()

        self.current_user_id = None

    def close(self):
        if self._own_session and self.session:
            self.session.close()
        if self.employees_session:
            self.employees_session.close()

    def set_current_user_id(self, user_id: int):
        self.current_user_id = user_id

    # ======================================================
    # Прокси для CRUD операций
    # ======================================================
    def get_all_employees(self) -> List[Dict]:
        return self.crud.get_all_employees()

    def get_projects(self, only_active: bool = True) -> List[Dict]:
        """Получает проекты, в которых участвует текущий пользователь"""
        return self.crud.get_projects(only_active, self.current_user_id)

    def get_tasks_for_project(self, project_id: int) -> List[Dict]:
        """Получить задачи по ID проекта"""
        return self.crud.get_tasks_for_project(project_id)

    def get_tasks_for_project_by_name(self, project_name: str) -> List[Dict]:
        """Получить задачи по названию проекта"""
        return self.crud.get_tasks_for_project_by_name(project_name)

    def get_project_id_by_name(self, project_name: str) -> Optional[int]:
        """Получить ID проекта по названию"""
        try:
            projects = self.crud.get_projects(only_active=True)
            for project in projects:
                if project['name'] == project_name:
                    return project['id']
            return None
        except Exception as e:
            print(f"❌ Ошибка при поиске ID проекта: {e}")
            return None

    def load_overtimes(self) -> Tuple[List[Dict], List[Dict]]:
        if not self.current_user_id:
            return [], []
        return self.crud.load_overtimes(self.current_user_id)

    def add_overtime(self, date: QDate, start_time: QTime, end_time: QTime,
                     description: str, employee_id: Optional[int] = None,
                     project_id: Optional[int] = None,
                     task_id: Optional[int] = None) -> Optional[Dict]:
        return self.crud.add_overtime(date, start_time, end_time, description,
                                      self.current_user_id, employee_id, project_id, task_id)

    def filter_overtimes(self, overtimes: List[Dict], **filters) -> List[Dict]:
        return self.crud.filter_overtimes(overtimes, **filters)

    def calculate_duration(self, start_time, end_time) -> str:
        return self.base.calculate_duration(start_time, end_time)

    def format_time_period(self, start_time, end_time) -> str:
        return self.base.format_time_period(start_time, end_time)

    # ======================================================
    # Прокси для импорта
    # ======================================================
    def import_overtimes_from_file(self, file_path: str, progress_callback=None) -> Dict:
        return self.importer.import_from_excel(file_path, progress_callback)

    def get_overtime_by_id(self, overtime_id: int) -> Optional[Dict]:
        return self.crud.get_overtime_by_id(overtime_id)

    def update_overtime(self, overtime_id: int, date: QDate, start_time: QTime, end_time: QTime,
                        description: str, employee_id: Optional[int] = None,
                        project_id: Optional[int] = None,
                        task_id: Optional[int] = None) -> Optional[Dict]:
        return self.crud.update_overtime(
            overtime_id, date, start_time, end_time, description,
            self.current_user_id, employee_id, project_id, task_id
        )

    def delete_overtime(self, overtime_id: int) -> bool:
        return self.crud.delete_overtime(overtime_id)

    # ======================================================
    # Прокси для экспорта
    # ======================================================
    def export_overtimes(self, overtimes: List[Dict], start_date: QDate, end_date: QDate,
                         file_path: str, department: Optional[str] = None,
                         division: Optional[str] = None) -> str:
        return self.exporter.export_overtimes(overtimes, start_date, end_date,
                                              file_path, department, division)

    def generate_filename(self, start_date: QDate, end_date: QDate,
                          department: Optional[str] = None,
                          division: Optional[str] = None) -> str:
        return self.exporter.generate_filename(start_date, end_date, department, division)