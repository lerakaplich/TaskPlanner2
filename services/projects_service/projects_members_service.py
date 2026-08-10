# services/projects_service/projects_members_service.py

from typing import List, Dict, Optional
from sqlalchemy import text


class ProjectsMembersService:
    """Управление участниками проектов"""

    def __init__(self, session, employees_session, employee_repo):
        self.session = session
        self.employees_session = employees_session
        self.employee_repo = employee_repo

    def _ensure_local_employee(self, external_employee_id: int) -> Optional[int]:
        """Проверяет наличие записи сотрудника в БД taskplanner.public.employees_data"""
        try:
            check_data_stmt = text("""
                SELECT employee_id FROM public.employees_data WHERE employee_id = :emp_id
            """)
            data_exists = self.session.execute(check_data_stmt, {'emp_id': external_employee_id}).first()

            if not data_exists:
                insert_data_stmt = text("""
                    INSERT INTO public.employees_data (employee_id, is_active, role)
                    VALUES (:emp_id, :is_active, :role)
                """)
                self.session.execute(insert_data_stmt, {
                    'emp_id': external_employee_id,
                    'is_active': True,
                    'role': 'user'
                })
                self.session.flush()

            return external_employee_id
        except Exception as e:
            print(f"⚠️ Ошибка при создании локальной записи сотрудника: {e}")
            return None

    def load_employees_for_selector(self) -> List[Dict]:
        """Загружает список сотрудников для выбора"""
        from models.employees import Employee
        from sqlalchemy import select

        stmt = select(Employee).order_by(Employee.last_name)
        employees = self.employees_session.scalars(stmt).all()

        result = []
        for emp in employees:
            result.append({
                'id': emp.id,
                'last_name': emp.last_name,
                'first_name': emp.first_name,
                'middle_name': emp.middle_name or '',
                'position': emp.position or 'Сотрудник',
                'phone': emp.phone_number or '',
                'department_id': emp.department_id,
                'division_id': emp.division_id
            })
        return result

    def load_employees_for_manager_combo(self) -> List[Dict]:
        """Загружает сотрудников для комбобокса куратора"""
        from models.employees import Employee
        from sqlalchemy import select

        stmt = select(Employee).order_by(Employee.last_name)
        employees = self.employees_session.scalars(stmt).all()

        result = []
        for emp in employees:
            full_name = f"{emp.last_name} {emp.first_name}"
            if emp.middle_name:
                full_name += f" {emp.middle_name}"
            result.append({
                'id': emp.id,
                'display_name': full_name
            })
        return result

    def load_employees_by_ids(self, employee_ids: List[int]) -> List[Dict]:
        """Загружает сотрудников по списку ID"""
        if not employee_ids:
            return []

        from models.employees import Employee
        from sqlalchemy import select

        stmt = select(Employee).where(Employee.id.in_(employee_ids))
        employees = self.employees_session.scalars(stmt).all()

        result = []
        for emp in employees:
            result.append({
                'id': emp.id,
                'last_name': emp.last_name,
                'first_name': emp.first_name,
                'middle_name': emp.middle_name or '',
                'position': emp.position or 'Сотрудник',
                'phone': emp.phone_number or ''
            })
        return result

    def get_employee_display_name(self, employee_id: int) -> str:
        """Возвращает короткое ФИО для отображения"""
        employee = self.employee_repo.get_by_id(employee_id)
        if not employee:
            return f"ID: {employee_id}"

        first_initial = f"{employee.first_name[0]}." if employee.first_name else ""
        middle_initial = f"{employee.middle_name[0]}." if employee.middle_name else ""
        return f"{employee.last_name} {first_initial}{middle_initial}".strip()

    def get_user_by_id(self, user_id: int) -> Dict:
        """Получает данные пользователя по ID"""
        from models.employees import Employee, EmployeeData
        from sqlalchemy import select
        from server_app.database import get_tasks_session

        emp_session = self.employees_session
        if emp_session is None:
            return {'id': user_id, 'last_name': 'Неизвестен', 'first_name': '', 'middle_name': '', 'rights': 'user'}

        try:
            stmt = select(Employee).where(Employee.id == user_id)
            user = emp_session.scalar(stmt)

            if not user:
                return {'id': user_id, 'last_name': 'Неизвестен', 'first_name': '', 'middle_name': '', 'rights': 'user'}

            # Получаем роль из EmployeeData
            role = 'user'
            tasks_session = get_tasks_session()
            if tasks_session:
                try:
                    stmt = select(EmployeeData.role).where(EmployeeData.employee_id == user_id)
                    emp_data_role = tasks_session.scalar(stmt)
                    if emp_data_role:
                        role = emp_data_role.value if hasattr(emp_data_role, 'value') else str(emp_data_role)
                except Exception as e:
                    print(f"⚠️ Ошибка получения роли: {e}")
                finally:
                    tasks_session.close()

            return {
                'id': user.id,
                'last_name': user.last_name,
                'first_name': user.first_name,
                'middle_name': user.middle_name or '',
                'rights': role,
                'position': user.position or '',
                'phone_number': user.phone_number or '',
                'email': user.email or ''
            }
        finally:
            pass  # Не закрываем employees_session, она общая

    def load_employee_selector_data(self) -> Dict:
        """Загружает данные для диалога выбора сотрудников"""
        from models.employees import Employee, Division, Department
        from sqlalchemy import select

        result = {
            'employees': [],
            'divisions': [],    # Список кортежей (id, name)
            'departments': []   # Список кортежей (id, name)
        }

        # Загружаем подразделения с ID и названием
        try:
            stmt = select(Division.id, Division.name).where(Division.name.isnot(None)).order_by(Division.name)
            divisions = self.employees_session.execute(stmt).all()
            result['divisions'] = [(div_id, div_name) for div_id, div_name in divisions]
        except Exception as e:
            print(f"⚠️ Ошибка загрузки подразделений: {e}")

        # Загружаем отделы с ID и названием
        try:
            stmt = select(Department.id, Department.name).where(Department.name.isnot(None)).order_by(Department.name)
            departments = self.employees_session.execute(stmt).all()
            result['departments'] = [(dept_id, dept_name) for dept_id, dept_name in departments]
        except Exception as e:
            print(f"⚠️ Ошибка загрузки отделов: {e}")

        # Загружаем сотрудников
        try:
            stmt = select(Employee).order_by(Employee.last_name)
            employees = self.employees_session.scalars(stmt).all()

            for emp in employees:
                full_name = self._get_employee_full_name(emp)
                if full_name:
                    result['employees'].append({
                        'id': emp.id,
                        'full_name': full_name,
                        'last_name': emp.last_name or '',
                        'first_name': emp.first_name or '',
                        'middle_name': emp.middle_name or '',
                        'position': emp.position or '',
                        'phone': emp.phone_number or '',
                        'email': emp.email or '',
                        'is_admin': False,
                        'usage_count': 0,
                        'department_id': emp.department_id,
                        'division_id': emp.division_id,
                        'role': 'user'
                    })
        except Exception as e:
            print(f"❌ Ошибка загрузки сотрудников: {e}")

        return result

    def _get_employee_full_name(self, employee) -> str:
        """Возвращает ФИО сотрудника"""
        if not employee:
            return "Неизвестный"
        parts = []
        if hasattr(employee, 'last_name') and employee.last_name:
            parts.append(employee.last_name)
        if hasattr(employee, 'first_name') and employee.first_name:
            parts.append(employee.first_name)
        if hasattr(employee, 'middle_name') and employee.middle_name:
            parts.append(employee.middle_name)
        return " ".join(parts) if parts else f"User {employee.id if hasattr(employee, 'id') else '?'}"