# services/employee_service.py (исправленный фасад)

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from database import get_employees_session, get_tasks_session
from models.employees import Employee, Division
from repositories.employee_repo import EmployeeRepo
from repositories.employee_data_repo import EmployeeDataRepo
from services.employee_service.column_service import ColumnService
from services.employee_service.department_service import DepartmentService
from services.employee_service.division_service import DivisionService
from services.employee_service.employee_base_service import EmployeeBaseService
from services.employee_service.tag_service import TagService
from sqlalchemy import text

class EmployeeService:
    """Главный сервис для работы с сотрудниками, отделами, подразделениями (фасад)"""

    def __init__(self, session: Session = None):
        self.session = session or get_employees_session()
        self.tasks_session = get_tasks_session()
        self._own_session = session is None

        # Инициализация репозиториев
        self.employee_repo = EmployeeRepo(self.session)
        self.employee_data_repo = EmployeeDataRepo(self.tasks_session)

        # Инициализация подсервисов
        self.base = EmployeeBaseService(self.session)
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
    # Вспомогательные методы преобразования
    # =====================================================
    def _employee_to_dict(self, employee: Employee) -> Dict[str, Any]:
        """Преобразует модель Employee в словарь"""
        if employee is None:
            return {}

        # Получаем данные из EmployeeData
        emp_data = self.employee_data_repo.get_by_id(employee.id)

        # Получаем названия отдела и подразделения
        department_name = '—'
        if employee.department_id:
            try:
                result = self.session.execute(
                    text("SELECT name FROM departments WHERE id = :dept_id"),
                    {'dept_id': employee.department_id}
                ).fetchone()
                if result:
                    department_name = result[0]
            except Exception:
                pass

        division_name = '—'
        if employee.division_id:
            try:
                result = self.session.execute(
                    text("SELECT name FROM divisions WHERE id = :div_id"),
                    {'div_id': employee.division_id}
                ).fetchone()
                if result:
                    division_name = result[0]
            except Exception:
                pass

        return {
            'id': employee.id,
            'number': employee.number,
            'last_name': employee.last_name,
            'first_name': employee.first_name,
            'middle_name': employee.middle_name,
            'full_name': self.base._get_full_name(employee),
            'position': employee.position,
            'phone_number': employee.phone_number,
            'work_number': employee.work_number,
            'email': employee.email,
            'chat_id': employee.chat_id,
            'birth_date': employee.birth_date,
            'department_id': employee.department_id,
            'department_name': department_name,
            'division_id': employee.division_id,
            'division_name': division_name,
            'is_active': emp_data.is_active if emp_data else True,
            'role': emp_data.role.value if emp_data and emp_data.role else 'user',
            'last_login': emp_data.last_login.isoformat() if emp_data and emp_data.last_login else None,
        }

    def _employee_to_card_dict(self, employee: Employee) -> Dict[str, Any]:
        """Преобразует модель Employee в словарь для карточки"""
        if employee is None:
            return {}

        # Получаем данные из EmployeeData
        emp_data = self.employee_data_repo.get_by_id(employee.id)
        role = emp_data.role.value if emp_data and emp_data.role else 'user'

        # Получаем названия
        department_name = '—'
        if employee.department_id:
            try:
                result = self.session.execute(
                    text("SELECT name FROM departments WHERE id = :dept_id"),
                    {'dept_id': employee.department_id}
                ).fetchone()
                if result:
                    department_name = result[0]
            except Exception:
                pass

        division_name = '—'
        if employee.division_id:
            try:
                result = self.session.execute(
                    text("SELECT name FROM divisions WHERE id = :div_id"),
                    {'div_id': employee.division_id}
                ).fetchone()
                if result:
                    division_name = result[0]
            except Exception:
                pass

        return {
            'id': employee.id,
            'last_name': employee.last_name or '',
            'first_name': employee.first_name or '',
            'middle_name': employee.middle_name or '',
            'full_name': self.base._get_full_name(employee),
            'position': employee.position or '—',
            'phone_number': employee.phone_number or '',
            'work_number': employee.work_number or '',
            'email': employee.email or '',
            'chat_id': employee.chat_id,
            'birth_date': employee.birth_date,
            'department_id': employee.department_id,
            'department_name': department_name,
            'division_id': employee.division_id,
            'division_name': division_name,
            'role': role,
            'rights': role,
            'is_active': emp_data.is_active if emp_data else True,
        }

    # =====================================================
    # Прокси для сотрудников (синхронизация двух БД)
    # =====================================================
    def get_all_employees(self) -> List[Dict[str, Any]]:
        """Получить всех сотрудников из БД employees с данными из EmployeeData"""
        employees = self.employee_repo.get_all()
        return [self._employee_to_dict(emp) for emp in employees]

    def get_employee_card_data(self, employee_id: int = None) -> Dict[str, Any]:
        """Возвращает данные сотрудника для карточки"""
        try:
            if employee_id is None:
                employees = self.employee_repo.get_all()
                return [self._employee_to_card_dict(emp) for emp in employees]
            else:
                employee = self.employee_repo.get_by_id(employee_id)
                return self._employee_to_card_dict(employee) if employee else None
        except Exception as e:
            print(f"❌ Ошибка в get_employee_card_data: {e}")
            return [] if employee_id is None else None

    def get_employees_for_division_selector(self) -> List[Dict[str, Any]]:
        """
        Возвращает список сотрудников для выбора руководителей в диалоге подразделения.
        Возвращает: [{'id': 1, 'full_name': 'Иванов Иван Иванович', 'position': 'Начальник цеха'}, ...]
        """
        employees = self.employee_repo.get_all()
        result = []
        for emp in employees:
            full_name = self.base._get_full_name(emp)
            result.append({
                'id': emp.id,
                'full_name': full_name,
                'position': emp.position or 'Сотрудник'
            })
        return result

    def get_employees_for_department_selector(self) -> List[Dict[str, Any]]:
        """
        Возвращает список сотрудников для выбора руководителей в диалоге отдела.
        """
        return self.get_employees_for_division_selector()

    def get_employee_full_info(self, employee_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает полную информацию о сотруднике для диалога редактирования"""
        try:
            employee = self.employee_repo.get_by_id(employee_id)
            if not employee:
                return None

            emp_data = self.employee_data_repo.get_by_id(employee_id)
            role = emp_data.role.value if emp_data and emp_data.role else 'user'

            return {
                'id': employee.id,
                'last_name': employee.last_name,
                'first_name': employee.first_name,
                'middle_name': employee.middle_name,
                'birth_date': employee.birth_date,
                'division_id': employee.division_id,
                'department_id': employee.department_id,
                'position': employee.position,
                'rights': role,
                'phone_number': employee.phone_number,
                'work_number': employee.work_number,
                'email': employee.email,
            }
        except Exception as e:
            print(f"❌ Ошибка в get_employee_full_info: {e}")
            return None

    def get_employee_by_id(self, employee_id: int) -> Optional[Dict[str, Any]]:
        employee = self.employee_repo.get_by_id(employee_id)
        return self._employee_to_dict(employee) if employee else None

    def get_employee_by_chat_id(self, chat_id: int) -> Optional[Dict[str, Any]]:
        employee = self.employee_repo.get_by_chat_id(chat_id)
        return self._employee_to_dict(employee) if employee else None

    def search_employees(self, query: str) -> List[Dict[str, Any]]:
        employees = self.employee_repo.search(query)
        return [self._employee_to_dict(emp) for emp in employees]

    def create_employee(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создаёт сотрудника в обеих БД"""
        try:
            # 1. Создаём запись в employees
            clean_data = {k: v for k, v in data.items()
                          if k not in ['rights', 'is_active', 'role']}
            employee = self.employee_repo.create(clean_data)

            # 2. Создаём запись в EmployeeData (taskplanner)
            role = data.get('rights') or data.get('role', 'user')
            from models.employees import RoleEnum
            role_value = RoleEnum(role) if isinstance(role, str) else role
            self.employee_data_repo.create(employee.id, role_value)

            # 3. Коммитим обе транзакции
            self.session.commit()
            self.tasks_session.commit()

            return self._employee_to_dict(employee)
        except Exception as e:
            self.session.rollback()
            self.tasks_session.rollback()
            print(f"❌ Ошибка при создании сотрудника: {e}")
            return None

    def update_employee(self, employee_id: int, data: Dict[str, Any]) -> bool:
        """Обновляет сотрудника в обеих БД"""
        try:
            # 1. Обновляем в employees
            employee = self.employee_repo.update(employee_id, data)
            if not employee:
                return False
            self.session.commit()

            # 2. Обновляем в EmployeeData (taskplanner)
            if 'role' in data and data['role']:
                from models.employees import RoleEnum
                role_value = data['role']
                if isinstance(role_value, str):
                    role_value = RoleEnum(role_value)
                self.employee_data_repo.update_role(employee_id, role_value)

            if 'is_active' in data and data['is_active'] is not None:
                self.employee_data_repo.set_active(employee_id, data['is_active'])

            self.tasks_session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            self.tasks_session.rollback()
            print(f"❌ Ошибка при обновлении сотрудника: {e}")
            return False

    def delete_employee(self, employee_id: int) -> bool:
        """Мягкое удаление сотрудника (только в EmployeeData)"""
        try:
            result = self.employee_data_repo.set_active(employee_id, False)
            if result:
                self.tasks_session.commit()
            return result
        except Exception as e:
            self.tasks_session.rollback()
            print(f"❌ Ошибка при удалении сотрудника: {e}")
            return False

    def hard_delete_employee(self, employee_id: int) -> bool:
        """Полное удаление сотрудника из обеих БД"""
        try:
            # 1. Удаляем из EmployeeData (taskplanner)
            # Сначала проверяем, есть ли записи
            emp_data = self.employee_data_repo.get_by_id(employee_id)
            if emp_data:
                self.tasks_session.delete(emp_data)

            # 2. Удаляем из employees
            result = self.employee_repo.hard_delete(employee_id)

            # 3. Коммитим
            self.session.commit()
            self.tasks_session.commit()
            return result
        except Exception as e:
            self.session.rollback()
            self.tasks_session.rollback()
            print(f"❌ Ошибка при полном удалении сотрудника: {e}")
            return False

    def save_employee_from_dialog(self, employee_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Сохраняет сотрудника из диалога (создание или обновление)"""
        employee_id = employee_data.get('id')

        if employee_id:
            success = self.update_employee(employee_id, employee_data)
            if success:
                return self.get_employee_card_data(employee_id)
            return None
        else:
            return self.create_employee(employee_data)

    def delete_employee_by_id(self, employee_id: int) -> bool:
        """Удаляет сотрудника по ID (мягкое удаление)"""
        return self.delete_employee(employee_id)

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
    # Прокси для подразделений (только employees)
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
    # Прокси для тегов (только taskplanner)
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
    # Прокси для колонок (только taskplanner)
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

    def get_filter_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Возвращает данные для фильтров (отделы и подразделения)"""
        try:
            # Получаем отделы напрямую через SQLAlchemy
            from models.employees import Department, Division

            departments = self.session.query(Department).order_by(Department.name).all()
            divisions = self.session.query(Division).order_by(Division.name).all()

            departments_list = []
            for dept in departments:
                departments_list.append({
                    'id': dept.id,
                    'name': dept.name,
                    'number': dept.number,
                    'division_id': dept.division_id
                })

            divisions_list = []
            for div in divisions:
                divisions_list.append({
                    'id': div.id,
                    'name': div.name,
                    'number': div.number
                })

            print(f"📊 get_filter_data: отделов={len(departments_list)}, подразделений={len(divisions_list)}")

            return {
                'departments': departments_list,
                'divisions': divisions_list
            }
        except Exception as e:
            print(f"❌ Ошибка в get_filter_data: {e}")
            return {'departments': [], 'divisions': []}

    def get_all_employees_for_selector(self) -> List[Dict[str, Any]]:
        employees = self.employee_repo.get_all()
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
        employee = self.employee_repo.get_by_id(employee_id)
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
    # Методы каскадного удаления
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