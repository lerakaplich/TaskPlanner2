# services/employee_service.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import get_employees_session
from models.employees import Employee, Department, Division, EmployeeData, RoleEnum
from repositories.employee_repo import EmployeeRepo


class EmployeeService:
    """Сервис для работы с сотрудниками, отделами и подразделениями"""

    def __init__(self, session: Session = None):
        self.session = session or get_employees_session()
        self.repo = EmployeeRepo(self.session)
        self._own_session = session is None

    def close(self):
        """Закрыть сессию, если она была создана внутри сервиса"""
        if self._own_session:
            self.session.close()

    # =========================
    # Сотрудники
    # =========================
    def get_all_employees(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Получить всех сотрудников"""
        if self.session is None:
            print("❌ Нет сессии БД")
            return []

        try:
            employees = self.session.query(Employee).filter(
                Employee.is_active == True).all() if active_only else self.session.query(Employee).all()
            return [self._employee_to_dict(emp) for emp in employees]
        except Exception as e:
            print(f"❌ Ошибка в get_all_employees: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_employee_by_id(self, employee_id: int) -> Optional[Dict[str, Any]]:
        """Получить сотрудника по ID"""
        employee = self.repo.get_by_id(employee_id)
        return self._employee_to_dict(employee) if employee else None

    def get_employee_by_chat_id(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Получить сотрудника по chat_id"""
        employee = self.repo.get_by_chat_id(chat_id)
        return self._employee_to_dict(employee) if employee else None

    def search_employees(self, query: str) -> List[Dict[str, Any]]:
        """Поиск сотрудников"""
        employees = self.repo.search(query)
        return [self._employee_to_dict(emp) for emp in employees]

    def create_employee(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создать нового сотрудника"""
        try:
            employee = self.repo.create(data)
            self.session.commit()
            return self._employee_to_dict(employee)
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании сотрудника: {e}")
            return None

    def update_employee(self, employee_id: int, data: Dict[str, Any]) -> bool:
        """Обновить данные сотрудника"""
        try:
            employee = self.repo.update(employee_id, data)
            if employee:
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении сотрудника: {e}")
            return False

    def delete_employee(self, employee_id: int) -> bool:
        """Удалить сотрудника"""
        try:
            result = self.repo.delete(employee_id)
            self.session.commit()
            return result
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при удалении сотрудника: {e}")
            return False

    def _employee_to_dict(self, employee: Employee) -> Dict[str, Any]:
        """Преобразует модель сотрудника в словарь"""
        if employee is None:
            return {}

        # Получаем данные из employees_data (она в той же БД employees)
        employee_data = self.session.query(EmployeeData).filter(EmployeeData.employee_id == employee.id).first()

        # Получаем название отдела
        department_name = None
        if employee.department_id:
            dept = self.session.query(Department).filter(Department.id == employee.department_id).first()
            department_name = dept.name if dept else None

        # Получаем название подразделения
        division_name = None
        if employee.division_id:
            div = self.session.query(Division).filter(Division.id == employee.division_id).first()
            division_name = div.name if div else None

        return {
            'id': employee.id,
            'number': employee.number,
            'last_name': employee.last_name,
            'first_name': employee.first_name,
            'middle_name': employee.middle_name,
            'full_name': f"{employee.last_name} {employee.first_name} {employee.middle_name or ''}".strip(),
            'position': employee.position,
            'rights': employee.rights or 'user',
            'phone_number': employee.phone_number,
            'work_number': getattr(employee, 'work_number', None),
            'email': employee.email,
            'chat_id': employee.chat_id,
            'birth_date': employee.birth_date,
            'department_id': employee.department_id,
            'department_name': department_name or '—',
            'division_id': employee.division_id,
            'division_name': division_name or '—',
            'is_active': employee.is_active,
            'role': employee_data.role.value if employee_data and employee_data.role else 'user',
            'last_login': employee_data.last_login.isoformat() if employee_data and employee_data.last_login else None,
        }

    def _get_full_name(self, employee: Employee) -> str:
        """Формирует ФИО сотрудника"""
        parts = [employee.last_name, employee.first_name]
        if employee.middle_name:
            parts.append(employee.middle_name)
        return ' '.join(parts)

    # =========================
    # Отделы
    # =========================
    def get_all_departments(self) -> List[Dict[str, Any]]:
        """Получить все отделы"""
        departments = self.session.query(Department).order_by(Department.name).all()
        return [self._department_to_dict(dept) for dept in departments]

    def get_department_by_id(self, department_id: int) -> Optional[Dict[str, Any]]:
        """Получить отдел по ID"""
        department = self.session.get(Department, department_id)
        return self._department_to_dict(department) if department else None

    def create_department(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создать отдел"""
        try:
            # Получаем следующий номер
            max_number = self.session.query(Department.number).order_by(Department.number.desc()).first()
            next_number = (max_number[0] + 1) if max_number else 1

            department = Department(
                number=next_number,
                name=data.get('name'),
                phone_number=data.get('phone_number'),
                boss=data.get('boss'),
                division_id=data.get('division_id', 1),
                organization_id=1
            )
            self.session.add(department)
            self.session.commit()
            self.session.refresh(department)

            return self._department_to_dict(department)
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании отдела: {e}")
            return None

    def update_department(self, department_id: int, data: Dict[str, Any]) -> bool:
        """Обновить отдел"""
        try:
            department = self.session.get(Department, department_id)
            if not department:
                return False

            for key, value in data.items():
                if hasattr(department, key) and value is not None:
                    setattr(department, key, value)

            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении отдела: {e}")
            return False

    def delete_department(self, department_id: int) -> bool:
        """Удалить отдел"""
        try:
            department = self.session.get(Department, department_id)
            if department:
                self.session.delete(department)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при удалении отдела: {e}")
            return False

    def _department_to_dict(self, department: Department) -> Dict[str, Any]:
        """Преобразует модель отдела в словарь"""
        result = {
            'id': department.id,
            'number': department.number,
            'name': department.name,
            'boss': department.boss,
            'phone_number': department.phone_number,
            'division_id': department.division_id,
        }

        # Получаем название подразделения
        if department.division_id:
            division = self.session.get(Division, department.division_id)
            result['division_name'] = division.name if division else '—'
        else:
            result['division_name'] = '—'

        return result

    # =========================
    # Подразделения
    # =========================
    def get_all_divisions(self) -> List[Dict[str, Any]]:
        """Получить все подразделения"""
        divisions = self.session.query(Division).order_by(Division.name).all()
        return [self._division_to_dict(div) for div in divisions]

    def get_division_by_id(self, division_id: int) -> Optional[Dict[str, Any]]:
        """Получить подразделение по ID"""
        division = self.session.get(Division, division_id)
        return self._division_to_dict(division) if division else None

    def create_division(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создать подразделение"""
        try:
            # Получаем следующий номер
            max_number = self.session.query(Division.number).order_by(Division.number.desc()).first()
            next_number = (max_number[0] + 1) if max_number else 1

            division = Division(
                number=next_number,
                name=data.get('name'),
                phone_number=data.get('phone_number'),
                workshop_code=data.get('workshop_code', ''),
                boss=data.get('boss'),
                organization_id=1
            )
            self.session.add(division)
            self.session.commit()
            self.session.refresh(division)

            return self._division_to_dict(division)
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании подразделения: {e}")
            return None

    def update_division(self, division_id: int, data: Dict[str, Any]) -> bool:
        """Обновить подразделение"""
        try:
            division = self.session.get(Division, division_id)
            if not division:
                return False

            for key, value in data.items():
                if hasattr(division, key) and value is not None:
                    setattr(division, key, value)

            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении подразделения: {e}")
            return False

    def delete_division(self, division_id: int) -> bool:
        """Удалить подразделение"""
        try:
            division = self.session.get(Division, division_id)
            if division:
                self.session.delete(division)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при удалении подразделения: {e}")
            return False

    def _division_to_dict(self, division: Division) -> Dict[str, Any]:
        """Преобразует модель подразделения в словарь"""
        return {
            'id': division.id,
            'number': division.number,
            'name': division.name,
            'boss': division.boss,
            'phone_number': division.phone_number,
            'workshop_code': division.workshop_code,
        }

    # =========================
    # Проверки зависимостей
    # =========================
    def has_employees_in_department(self, department_id: int) -> bool:
        """Проверяет, есть ли сотрудники в отделе"""
        count = self.session.query(Employee).filter(Employee.department_id == department_id).count()
        return count > 0

    def has_employees_in_division(self, division_id: int) -> bool:
        """Проверяет, есть ли сотрудники в подразделении"""
        count = self.session.query(Employee).filter(Employee.division_id == division_id).count()
        return count > 0

    def has_departments_in_division(self, division_id: int) -> bool:
        """Проверяет, есть ли отделы в подразделении"""
        count = self.session.query(Department).filter(Department.division_id == division_id).count()
        return count > 0