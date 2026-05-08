# services/employee_service/employee_crud_service.py

from typing import List, Optional, Dict, Any
from sqlalchemy import text
from datetime import datetime
from models.employees import Employee, EmployeeData, RoleEnum
from .employee_base_service import EmployeeBaseService


class EmployeeCrudService(EmployeeBaseService):
    """CRUD операции с сотрудниками"""

    def get_all_employees(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Получить всех сотрудников"""
        try:
            employees = self.session.query(Employee).all()
            result = []
            for emp in employees:
                if active_only:
                    emp_data = self.tasks_session.query(EmployeeData).filter(
                        EmployeeData.employee_id == emp.id
                    ).first()
                    if emp_data and not emp_data.is_active:
                        continue
                result.append(self._employee_to_dict(emp))
            return result
        except Exception as e:
            print(f"❌ Ошибка в get_all_employees: {e}")
            return []

    def get_employee_card_data(self, employee_id: int = None) -> Dict[str, Any]:
        """Возвращает данные сотрудника для карточки"""
        try:
            if employee_id is None:
                employees = self.session.query(Employee).all()
                return [self._employee_to_card_dict(emp) for emp in employees]
            else:
                employee = self.repo.get_by_id(employee_id)
                return self._employee_to_card_dict(employee) if employee else None
        except Exception as e:
            print(f"❌ Ошибка в get_employee_card_data: {e}")
            return [] if employee_id is None else None

    def get_employee_full_info(self, employee_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает полную информацию о сотруднике для диалога редактирования"""
        try:
            employee = self.repo.get_by_id(employee_id)
            if not employee:
                return None

            role = 'user'
            if self.tasks_session:
                try:
                    emp_data = self.tasks_session.query(EmployeeData).filter(
                        EmployeeData.employee_id == employee.id
                    ).first()
                    if emp_data:
                        role = emp_data.role.value if hasattr(emp_data.role, 'value') else str(emp_data.role)
                except Exception:
                    pass

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
        try:
            employee = self.repo.get_by_id(employee_id)
            return self._employee_to_dict(employee) if employee else None
        except Exception as e:
            print(f"❌ Ошибка при получении сотрудника {employee_id}: {e}")
            return None

    def get_employee_by_chat_id(self, chat_id: int) -> Optional[Dict[str, Any]]:
        employee = self.repo.get_by_chat_id(chat_id)
        return self._employee_to_dict(employee) if employee else None

    def search_employees(self, query: str) -> List[Dict[str, Any]]:
        employees = self.repo.search(query)
        return [self._employee_to_dict(emp) for emp in employees]

    def create_employee(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            clean_data = {k: v for k, v in data.items()
                          if k not in ['rights', 'is_active', 'role']}
            employee = self.repo.create(clean_data)
            self.session.commit()
            return self._employee_to_dict(employee)
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании сотрудника: {e}")
            return None

    def update_employee(self, employee_id: int, data: Dict[str, Any]) -> bool:
        try:
            employee = self.repo.get_by_id(employee_id)
            if not employee:
                return False

            employee_fields = ['last_name', 'first_name', 'middle_name', 'position',
                               'department_id', 'division_id', 'organization_id',
                               'work_number', 'phone_number', 'email', 'chat_id', 'birth_date']

            for key, value in data.items():
                if key in employee_fields and value is not None:
                    setattr(employee, key, value)

            self.session.commit()

            if 'role' in data and data['role']:
                role_value = data['role']
                if isinstance(role_value, str):
                    role_value = RoleEnum(role_value)
                self.repo.update_role(employee_id, role_value)

            if 'is_active' in data and data['is_active'] is not None:
                self.repo.set_active(employee_id, data['is_active'])

            if self.tasks_session:
                self.tasks_session.commit()

            return True
        except Exception as e:
            self.session.rollback()
            if self.tasks_session:
                self.tasks_session.rollback()
            print(f"❌ Ошибка при обновлении сотрудника: {e}")
            return False

    def delete_employee(self, employee_id: int) -> bool:
        try:
            result = self.repo.delete(employee_id)
            self.tasks_session.commit()
            self.session.commit()
            return result
        except Exception as e:
            self.session.rollback()
            self.tasks_session.rollback()
            print(f"❌ Ошибка при удалении сотрудника: {e}")
            return False

    def save_employee_from_dialog(self, employee_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            employee_id = employee_data.get('id')

            if employee_id:
                success = self.update_employee(employee_id, employee_data)
                if success:
                    return self.get_employee_card_data(employee_id)
                return None
            else:
                clean_data = {k: v for k, v in employee_data.items()
                              if k not in ['id', 'rights', 'role', 'generated_password']}
                employee = self.repo.create(clean_data)
                self.session.commit()

                role = employee_data.get('rights') or employee_data.get('role', 'user')
                if role:
                    role_value = RoleEnum(role) if isinstance(role, str) else role
                    self.repo.update_role(employee.id, role_value)
                    if self.tasks_session:
                        self.tasks_session.commit()

                return self.get_employee_card_data(employee.id)
        except Exception as e:
            self.session.rollback()
            if self.tasks_session:
                self.tasks_session.rollback()
            print(f"❌ Ошибка в save_employee_from_dialog: {e}")
            return None

    def _employee_to_dict(self, employee: Employee) -> Dict[str, Any]:
        if employee is None:
            return {}

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
            'full_name': self._get_full_name(employee),
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
            'is_active': True,
            'role': 'user',
            'last_login': None,
        }

    def _employee_to_card_dict(self, employee: Employee) -> Dict[str, Any]:
        if employee is None:
            return {}

        role = 'user'
        if self.tasks_session:
            try:
                emp_data = self.tasks_session.query(EmployeeData).filter(
                    EmployeeData.employee_id == employee.id
                ).first()
                if emp_data:
                    role = emp_data.role.value if hasattr(emp_data.role, 'value') else str(emp_data.role)
            except Exception:
                pass

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
            'full_name': self._get_full_name(employee),
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
            'is_active': True,
        }