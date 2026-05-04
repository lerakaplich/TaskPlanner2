# services/employee_service.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, text
import traceback
from datetime import datetime  # ← ДОБАВИТЬ

from database import get_employees_session, get_tasks_session
from models.employees import Employee, Department, Division, EmployeeData, RoleEnum
from repositories.employee_repo import EmployeeRepo


class EmployeeService:
    """Сервис для работы с сотрудниками, отделами и подразделениями"""

    def __init__(self, session: Session = None):
        # Сессия для employees (сотрудники, отделы, подразделения)
        self.session = session or get_employees_session()  # ← Используем employees_session
        # Сессия для taskplanner (employees_data)
        self.tasks_session = get_tasks_session()
        self.repo = EmployeeRepo(self.session)  # ← репозиторий использует ту же сессию
        self._own_session = session is None

    def close(self):
        """Закрыть сессии, если они были созданы внутри сервиса"""
        if self._own_session and self.session:
            self.session.close()
        if self.tasks_session:
            self.tasks_session.close()

    def _ensure_session_valid(self):
        """Проверяет и пересоздает сессию если она в ошибке"""
        try:
            # Проверяем, жива ли сессия
            self.session.execute(text("SELECT 1"))
        except Exception as e:
            print(f"⚠️ Сессия в ошибке, пересоздаем: {e}")
            if self._own_session and self.session:
                self.session.rollback()
                self.session.close()
            self.session = get_employees_session()
            self.repo = EmployeeRepo(self.session)
            print("✅ Сессия пересоздана")

    # =========================
    # Сотрудники
    # =========================
    def get_all_employees(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Получить всех сотрудников"""
        if self.session is None:
            print("❌ Нет сессии БД")
            return []

        try:
            self._ensure_session_valid()
            # Получаем всех сотрудников
            employees = self.session.query(Employee).all()

            result = []
            for emp in employees:
                if active_only:
                    # Проверяем активность через EmployeeData
                    emp_data = self.tasks_session.query(EmployeeData).filter(
                        EmployeeData.employee_id == emp.id
                    ).first()
                    if emp_data and not emp_data.is_active:
                        continue
                result.append(self._employee_to_dict(emp))

            return result
        except Exception as e:
            print(f"❌ Ошибка в get_all_employees: {e}")
            traceback.print_exc()
            return []

    # =========================
    # Отделы (из БД employees)
    # =========================
    def get_all_departments(self) -> List[Dict[str, Any]]:
        """Получить все отделы (из БД employees)"""
        if self.session is None:
            print("❌ Нет сессии БД для отделов")
            return []

        try:
            self._ensure_session_valid()

            # Проверяем, есть ли таблица departments
            check = self.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'departments'
                )
            """)).scalar()
            print(f"📌 Таблица departments существует: {check}")

            if not check:
                print("❌ Таблица departments не найдена!")
                return []

            departments = self.session.query(Department).order_by(Department.name).all()
            print(f"📌 Найдено отделов: {len(departments)}")
            return [self._department_to_dict(dept) for dept in departments]
        except Exception as e:
            print(f"❌ Ошибка загрузки отделов: {e}")
            traceback.print_exc()
            if self._own_session:
                self.session = get_employees_session()
                self.repo = EmployeeRepo(self.session)
            return []

    def get_all_divisions(self) -> List[Dict[str, Any]]:
        """Получить все подразделения (из БД employees)"""
        if self.session is None:
            print("❌ Нет сессии БД для подразделений")
            return []

        try:
            db_name = self.session.execute(text("SELECT current_database()")).scalar()
            print(f"📌 [get_all_divisions] Текущая БД: {db_name}")

            search_path = self.session.execute(text("SHOW search_path")).scalar()
            print(f"📌 [get_all_divisions] search_path: {search_path}")

            tables = self.session.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)).fetchall()
            print(f"📌 [get_all_divisions] Таблицы в public: {[t[0] for t in tables]}")

            check = self.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'divisions'
                )
            """)).scalar()
            print(f"📌 Таблица divisions существует: {check}")

            if not check:
                print("❌ Таблица divisions не найдена!")
                return []

            divisions = self.session.query(Division).order_by(Division.name).all()
            print(f"📌 Найдено подразделений: {len(divisions)}")
            return [self._division_to_dict(div) for div in divisions]
        except Exception as e:
            print(f"❌ Ошибка загрузки подразделений: {e}")
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
            # Убираем rights и другие несуществующие поля
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
        """Обновить данные сотрудника"""
        try:
            # Отделяем поля Employee от полей EmployeeData
            employee_fields = ['last_name', 'first_name', 'middle_name', 'position',
                               'department_id', 'division_id', 'organization_id',
                               'work_number', 'phone_number', 'email', 'chat_id', 'birth_date']

            employee_data = {k: v for k, v in data.items() if k in employee_fields and v is not None}

            if employee_data:
                employee = self.repo.update(employee_id, employee_data)

            # Обновляем роль если передана
            if 'role' in data and data['role']:
                role_value = data['role']
                if isinstance(role_value, str):
                    role_value = RoleEnum(role_value)
                self.repo.update_role(employee_id, role_value)

            # Обновляем статус активности если передан
            if 'is_active' in data and data['is_active'] is not None:
                self.repo.set_active(employee_id, data['is_active'])

            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении сотрудника: {e}")
            return False

    def delete_employee(self, employee_id: int) -> bool:
        """Мягкое удаление сотрудника"""
        try:
            result = self.repo.delete(employee_id)
            self.tasks_session.commit()  # Коммитим изменения в EmployeeData
            self.session.commit()
            return result
        except Exception as e:
            self.session.rollback()
            self.tasks_session.rollback()
            print(f"❌ Ошибка при удалении сотрудника: {e}")
            return False

    def _employee_to_dict(self, employee: Employee) -> Dict[str, Any]:
        """Преобразует модель сотрудника в словарь"""
        if employee is None:
            return {}

        # Получаем данные из employees_data (в БД taskplanner!)
        employee_data = None
        if self.tasks_session:
            try:
                employee_data = self.tasks_session.query(EmployeeData).filter(
                    EmployeeData.employee_id == employee.id
                ).first()
            except Exception as e:
                print(f"⚠️ Ошибка получения EmployeeData для {employee.id}: {e}")

        # Получаем название отдела (из БД employees)
        department_name = None
        if employee.department_id:
            try:
                dept = self.session.query(Department).filter(Department.id == employee.department_id).first()
                department_name = dept.name if dept else None
            except Exception as e:
                print(f"⚠️ Ошибка получения отдела: {e}")

        # Получаем название подразделения (из БД employees)
        division_name = None
        if employee.division_id:
            try:
                div = self.session.query(Division).filter(Division.id == employee.division_id).first()
                division_name = div.name if div else None
            except Exception as e:
                print(f"⚠️ Ошибка получения подразделения: {e}")

        return {
            'id': employee.id,
            'number': employee.number,
            'last_name': employee.last_name,
            'first_name': employee.first_name,
            'middle_name': employee.middle_name,
            'full_name': f"{employee.last_name} {employee.first_name} {employee.middle_name or ''}".strip(),
            'position': employee.position,
            'phone_number': employee.phone_number,
            'work_number': employee.work_number,
            'email': employee.email,
            'chat_id': employee.chat_id,
            'birth_date': employee.birth_date,
            'department_id': employee.department_id,
            'department_name': department_name or '—',
            'division_id': employee.division_id,
            'division_name': division_name or '—',
            # Данные из EmployeeData
            'is_active': employee_data.is_active if employee_data else True,
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
    # Отделы (из БД employees)
    # =========================
    def get_department_by_id(self, department_id: int) -> Optional[Dict[str, Any]]:
        """Получить отдел по ID"""
        try:
            department = self.session.get(Department, department_id)
            return self._department_to_dict(department) if department else None
        except Exception as e:
            print(f"❌ Ошибка загрузки отдела {department_id}: {e}")
            return None

    def create_department(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создать отдел (в БД employees)"""
        try:
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
        """Обновить отдел (в БД employees)"""
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
        """Удалить отдел (из БД employees)"""
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

        try:
            if department.division_id:
                division = self.session.get(Division, department.division_id)
                result['division_name'] = division.name if division else '—'
            else:
                result['division_name'] = '—'
        except Exception as e:
            print(f"⚠️ Ошибка получения подразделения для отдела: {e}")
            result['division_name'] = '—'

        return result

    # =========================
    # Подразделения (из БД employees)
    # =========================
    def get_division_by_id(self, division_id: int) -> Optional[Dict[str, Any]]:
        """Получить подразделение по ID"""
        try:
            division = self.session.get(Division, division_id)
            return self._division_to_dict(division) if division else None
        except Exception as e:
            print(f"❌ Ошибка загрузки подразделения {division_id}: {e}")
            return None

    def create_division(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создать подразделение (в БД employees)"""
        try:
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
        """Обновить подразделение (в БД employees)"""
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
        """Удалить подразделение (из БД employees)"""
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
        try:
            count = self.session.query(Employee).filter(Employee.department_id == department_id).count()
            return count > 0
        except Exception as e:
            print(f"❌ Ошибка проверки сотрудников в отделе: {e}")
            return False

    def has_employees_in_division(self, division_id: int) -> bool:
        """Проверяет, есть ли сотрудники в подразделении"""
        try:
            count = self.session.query(Employee).filter(Employee.division_id == division_id).count()
            return count > 0
        except Exception as e:
            print(f"❌ Ошибка проверки сотрудников в подразделении: {e}")
            return False

    def has_departments_in_division(self, division_id: int) -> bool:
        """Проверяет, есть ли отделы в подразделении"""
        try:
            count = self.session.query(Department).filter(Department.division_id == division_id).count()
            return count > 0
        except Exception as e:
            print(f"❌ Ошибка проверки отделов в подразделении: {e}")
            return False