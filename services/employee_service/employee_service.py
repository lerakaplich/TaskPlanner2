# services/employee_service.py (обновленный фасад)

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from database import get_employees_session, get_tasks_session

from models.employees import Division, Employee
from .column_service import ColumnService
from .employee_base_service import EmployeeBaseService
from .employee_crud_service import EmployeeCrudService
from .department_service import DepartmentService
from .division_service import DivisionService
from .tag_service import TagService


class EmployeeService:
    """Главный сервис для работы с сотрудниками, отделами, подразделениями, тегами и колонками (фасад)"""

    def __init__(self, session: Session = None):
        self.session = session or get_employees_session()
        self.tasks_session = get_tasks_session()
        self._own_session = session is None

        # Инициализация подсервисов
        self.base = EmployeeBaseService(self.session)
        self.employees = EmployeeCrudService(self.session)
        self.departments = DepartmentService(self.session)
        self.divisions = DivisionService(self.session)
        self.tags = TagService(self.tasks_session)
        self.columns = ColumnService(self.tasks_session)

    def close(self):
        if self._own_session and self.session:
            self.session.close()
        if self.tasks_session:
            self.tasks_session.close()

    # =====================================================
    # Прокси для сотрудников
    # =====================================================
    def get_all_employees(self, active_only: bool = True) -> List[Dict[str, Any]]:
        return self.employees.get_all_employees(active_only)

    def get_employee_card_data(self, employee_id: int = None) -> Dict[str, Any]:
        return self.employees.get_employee_card_data(employee_id)

    def get_employee_full_info(self, employee_id: int) -> Optional[Dict[str, Any]]:
        return self.employees.get_employee_full_info(employee_id)

    def get_employee_by_id(self, employee_id: int) -> Optional[Dict[str, Any]]:
        return self.employees.get_employee_by_id(employee_id)

    def get_employee_by_chat_id(self, chat_id: int) -> Optional[Dict[str, Any]]:
        return self.employees.get_employee_by_chat_id(chat_id)

    def search_employees(self, query: str) -> List[Dict[str, Any]]:
        return self.employees.search_employees(query)

    def create_employee(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.employees.create_employee(data)

    def update_employee(self, employee_id: int, data: Dict[str, Any]) -> bool:
        return self.employees.update_employee(employee_id, data)

    def delete_employee(self, employee_id: int) -> bool:
        return self.employees.delete_employee(employee_id)

    def delete_employee_by_id(self, employee_id: int) -> bool:
        return self.employees.delete_employee(employee_id)

    def save_employee_from_dialog(self, employee_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.employees.save_employee_from_dialog(employee_data)

    # =====================================================
    # Прокси для отделов
    # =====================================================
    def get_all_departments(self) -> List[Dict[str, Any]]:
        return self.departments.get_all_departments()

    def get_department_card_data(self, department_id: int = None) -> Dict[str, Any]:
        return self.departments.get_department_card_data(department_id)

    def get_department_by_id(self, department_id: int) -> Optional[Dict[str, Any]]:
        return self.departments.get_department_by_id(department_id)

    def get_other_departments(self, exclude_department_id: int) -> List[Dict[str, Any]]:
        return self.departments.get_other_departments(exclude_department_id)

    def create_department(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.departments.create_department(data)

    def update_department(self, department_id: int, data: Dict[str, Any]) -> bool:
        return self.departments.update_department(department_id, data)

    def delete_department(self, department_id: int) -> bool:
        return self.departments.delete_department(department_id)

    def save_department_from_dialog(self, department_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.departments.save_department_from_dialog(department_data)

    def filter_departments(self, departments: List[Dict], search_text: str = None,
                           division_id: int = None) -> List[Dict]:
        return self.departments.filter_departments(departments, search_text, division_id)

    def get_filtered_departments_data(self, search_text: str = None,
                                      division_id: int = None) -> List[Dict]:
        return self.departments.get_filtered_departments_data(search_text, division_id)

    def validate_department_form(self, form_data: Dict[str, Any]) -> tuple[bool, str]:
        return self.departments.validate_department_form(form_data)

    # =====================================================
    # Прокси для подразделений
    # =====================================================
    def get_all_divisions(self) -> List[Dict[str, Any]]:
        return self.divisions.get_all_divisions()

    def get_division_card_data(self, division_id: int = None) -> Dict[str, Any]:
        return self.divisions.get_division_card_data(division_id)

    def get_division_by_id(self, division_id: int) -> Optional[Dict[str, Any]]:
        return self.divisions.get_division_by_id(division_id)

    def get_other_divisions(self, exclude_division_id: int) -> List[Dict[str, Any]]:
        return self.divisions.get_other_divisions(exclude_division_id)

    def create_division(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.divisions.create_division(data)

    def update_division(self, division_id: int, data: Dict[str, Any]) -> bool:
        return self.divisions.update_division(division_id, data)

    def delete_division(self, division_id: int) -> bool:
        return self.divisions.delete_division(division_id)

    def save_division_from_dialog(self, division_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.divisions.save_division_from_dialog(division_data)

    def prepare_division_for_dialog(self, division_id: int) -> Optional[Dict[str, Any]]:
        return self.divisions.prepare_division_for_dialog(division_id)

    def validate_division_form(self, form_data: Dict[str, Any]) -> tuple[bool, str]:
        return self.divisions.validate_division_form(form_data)

    # =====================================================
    # Прокси для тегов
    # =====================================================
    def get_all_tags(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        return self.tags.get_all_tags(include_archived)

    def get_tag_by_id(self, tag_id: int) -> Optional[Dict[str, Any]]:
        return self.tags.get_tag_by_id(tag_id)

    def create_tag(self, tag_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.tags.create_tag(tag_data)

    def update_tag(self, tag_id: int, tag_data: Dict[str, Any]) -> bool:
        return self.tags.update_tag(tag_id, tag_data)

    def delete_tag(self, tag_id: int) -> bool:
        return self.tags.delete_tag(tag_id)

    def hard_delete_tag(self, tag_id: int) -> bool:
        return self.tags.hard_delete_tag(tag_id)

    def get_tag_usage_count(self, tag_id: int) -> int:
        return self.tags.get_tag_usage_count(tag_id)

    def add_tag_usage_count(self, tags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self.tags.add_tag_usage_count(tags)

    # =====================================================
    # Прокси для колонок
    # =====================================================
    def get_all_template_columns(self) -> List[Dict[str, Any]]:
        return self.columns.get_template_columns()

    def get_column_by_id(self, column_id: int) -> Optional[Dict[str, Any]]:
        return self.columns.get_column_by_id(column_id)

    def create_template_column(self, column_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.columns.create_template_column(column_data)

    def update_template_column(self, column_id: int, column_data: Dict[str, Any]) -> bool:
        return self.columns.update_template_column(column_id, column_data)

    def delete_template_column(self, column_id: int) -> bool:
        return self.columns.delete_template_column(column_id)

    def hard_delete_template_column(self, column_id: int) -> bool:
        return self.columns.hard_delete_template_column(column_id)

    # =====================================================
    # Дополнительные методы
    # =====================================================
    def get_filter_data(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            'departments': self.get_all_departments(),
            'divisions': self.get_all_divisions()
        }

    def get_all_employees_for_selector(self) -> List[Dict[str, Any]]:
        employees = self.session.query(Employee).all()
        result = []
        for emp in employees:
            full_name = self.base._get_full_name(emp)
            result.append({
                'id': emp.id,
                'full_name': full_name,
                'position': emp.position or 'Сотрудник'
            })
        return result

    def get_divisions_for_selector(self) -> List[Dict[str, Any]]:
        divisions = self.session.query(Division).all()
        result = []
        for div in divisions:
            result.append({
                'id': div.id,
                'name': div.name,
                'number': div.number,
                'display_name': f"{div.name}" + (f" (№{div.number})" if div.number else "")
            })
        return result

    def get_employee_short_name(self, employee_id: int) -> str:
        return self.base.get_employee_short_name(employee_id)

    def get_role_display_name(self, role: str) -> str:
        return self.base.get_role_display_name(role)

    def get_role_color(self, role: str) -> str:
        return self.base.get_role_color(role)

    def format_phone_display(self, phone: str) -> str:
        return self.base.format_phone_display(phone)

    def prepare_employee_for_display(self, employee_data: Dict[str, Any]) -> Dict[str, Any]:
        result = employee_data.copy()
        if result.get('phone_number'):
            result['display_phone'] = self.base.format_phone_display(result['phone_number'])
        else:
            result['display_phone'] = '—'
        role = result.get('rights') or result.get('role', 'user')
        result['role_display'] = self.base.get_role_display_name(role)
        result['role_color'] = self.base.get_role_color(role)
        return result

    def get_roles_list(self) -> List[str]:
        return ['Пользователь', 'Администратор', 'Суперадминистратор']

    def validate_employee_form(self, form_data: Dict[str, Any]) -> tuple[bool, str]:
        if not form_data.get('last_name', '').strip():
            return False, "Пожалуйста, заполните поле 'Фамилия'"
        if not form_data.get('first_name', '').strip():
            return False, "Пожалуйста, заполните поле 'Имя'"
        if not form_data.get('division_id'):
            return False, "Пожалуйста, выберите подразделение"
        if not form_data.get('department_id'):
            return False, "Пожалуйста, выберите отдел"
        if not form_data.get('position', '').strip():
            return False, "Пожалуйста, заполните поле 'Должность'"
        phone = form_data.get('phone_number', '')
        if not phone:
            return False, "Пожалуйста, заполните поле 'Моб. телефон'"
        phone_digits = ''.join(c for c in phone if c.isdigit())
        if len(phone_digits) not in [9, 12]:
            return False, "Введите 9 цифр номера телефона (без +375)"
        email = form_data.get('email', '')
        if email and '@' not in email:
            return False, "Пожалуйста, введите корректный email"
        return True, ""

    def generate_registration_password(self) -> str:
        import secrets
        import string
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))

    def get_employee_full_name(self, employee_id: int) -> str:
        employee = self.employees.repo.get_by_id(employee_id)
        if employee:
            return self.base._get_full_name(employee)
        return 'Неизвестный'

    def delete_employee_by_id_with_check(self, employee_id: int) -> Dict[str, Any]:
        """Удаляет сотрудника с проверками"""
        try:
            from models.tasks import Task
            tasks_count = self.tasks_session.query(Task).filter(
                Task.assigned_to == employee_id,
                Task.is_archived == False
            ).count()

            if tasks_count > 0:
                return {
                    'success': False,
                    'message': f'Нельзя удалить сотрудника, у которого есть {tasks_count} активных задач. Сначала переназначьте задачи.'
                }

            result = self.delete_employee(employee_id)
            if result:
                return {'success': True, 'message': 'Сотрудник успешно удалён'}
            else:
                return {'success': False, 'message': 'Ошибка при удалении сотрудника'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # =====================================================
    # Методы каскадного удаления (оставляем в фасаде)
    # =====================================================
    def has_employees_in_department(self, department_id: int) -> bool:
        return self.departments.has_employees_in_department(department_id)

    def has_employees_in_division(self, division_id: int) -> bool:
        return self.divisions.has_employees_in_division(division_id)

    def has_departments_in_division(self, division_id: int) -> bool:
        return self.divisions.has_departments_in_division(division_id)

    def delete_division_cascade(self, division_id: int) -> bool:
        return self.divisions.delete_division_cascade(division_id)

    def reassign_division_dependencies(self, from_division_id: int, to_division_id: int) -> bool:
        return self.divisions.reassign_division_dependencies(from_division_id, to_division_id)

    def delete_department_cascade(self, department_id: int) -> bool:
        return self.departments.delete_department_cascade(department_id)

    def reassign_department_employees(self, from_department_id: int, to_department_id: int) -> bool:
        return self.departments.reassign_department_employees(from_department_id, to_department_id)

    def delete_department_by_id(self, department_id: int, delete_employees: bool = False,
                                target_department_id: int = None) -> bool:
        return self.departments.delete_department_by_id(department_id, delete_employees, target_department_id)

    def delete_division_by_id(self, division_id: int, delete_departments: bool = False,
                              target_division_id: int = None) -> bool:
        return self.divisions.delete_division_by_id(division_id, delete_departments, target_division_id)