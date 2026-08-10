# repositories/employee_repo.py
from select import select
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from models.employees import Employee


class EmployeeRepo:
    """Репозиторий для работы с моделью Employee"""

    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> List[Employee]:
        """Получить всех сотрудников"""
        return self.session.query(Employee).all()

    def get_by_id(self, employee_id: int) -> Optional[Employee]:
        """Получить сотрудника по ID"""
        return self.session.get(Employee, employee_id)

    def get_by_chat_id(self, chat_id: int) -> Optional[Employee]:
        """Получить сотрудника по chat_id"""
        return self.session.query(Employee).filter(Employee.chat_id == chat_id).first()

    def search(self, query: str) -> List[Employee]:
        """Поиск сотрудников по ФИО"""
        search = f"%{query}%"
        return self.session.query(Employee).filter(
            (Employee.last_name.ilike(search)) |
            (Employee.first_name.ilike(search)) |
            (Employee.middle_name.ilike(search))
        ).all()

    def create(self, data: Dict[str, Any]) -> Employee:
        """Создать сотрудника"""
        employee = Employee(**data)
        self.session.add(employee)
        self.session.flush()
        return employee

    def update(self, employee_id: int, data: Dict[str, Any]) -> Optional[Employee]:
        """Обновить сотрудника"""
        employee = self.get_by_id(employee_id)
        if not employee:
            return None

        for key, value in data.items():
            if hasattr(employee, key) and value is not None:
                setattr(employee, key, value)

        self.session.flush()
        return employee

    def update_role(self, employee_id: int, role) -> bool:
        """Обновляет роль сотрудника через EmployeeData"""
        from models.employees import EmployeeData
        from server_app.database import get_tasks_session

        tasks_session = get_tasks_session()
        try:
            emp_data = tasks_session.query(EmployeeData).filter(
                EmployeeData.employee_id == employee_id
            ).first()

            if emp_data:
                emp_data.role = role
                tasks_session.flush()
                return True
            return False
        except Exception as e:
            print(f"❌ Ошибка обновления роли: {e}")
            return False

    def set_active(self, employee_id: int, is_active: bool) -> bool:
        """Устанавливает статус активности через EmployeeData"""
        from models.employees import EmployeeData
        from server_app.database import get_tasks_session

        tasks_session = get_tasks_session()
        try:
            emp_data = tasks_session.query(EmployeeData).filter(
                EmployeeData.employee_id == employee_id
            ).first()

            if emp_data:
                emp_data.is_active = is_active
                tasks_session.flush()
                return True
            return False
        except Exception as e:
            print(f"❌ Ошибка установки статуса: {e}")
            return False

    def delete(self, employee_id: int) -> bool:
        """Мягкое удаление (установка is_active=False)"""
        return self.set_active(employee_id, False)

    def hard_delete(self, employee_id: int) -> bool:
        """Полное удаление из БД"""
        employee = self.get_by_id(employee_id)
        if not employee:
            return False

        self.session.delete(employee)
        self.session.flush()
        return True

    def get_with_kpd(self, employee_id: int) -> Optional[Dict[str, Any]]:
        """Получить сотрудника вместе с данными КПД"""
        employee = self.get_by_id(employee_id)
        if not employee:
            return None

        employee_data = employee.employee_data

        return {
            "id": employee.id,
            "number": employee.number,
            "full_name": f"{employee.last_name} {employee.first_name} {employee.middle_name or ''}".strip(),
            "position": employee.position,
            "kpd_rating": employee_data.kpd_rating if employee_data else 0.0,
            "kpd_level": employee_data.kpd_level if employee_data else "Нет данных",
            "on_time_rate": employee_data.on_time_rate if employee_data else 0.0,
            "tasks_completed_total": employee_data.tasks_completed_total if employee_data else 0,
            "tasks_completed_on_time": employee_data.tasks_completed_on_time if employee_data else 0,
            "avg_task_completion_days": employee_data.avg_task_completion_days if employee_data else 0.0,
            "last_calculated": employee_data.kpd_last_calculated if employee_data else None
        }

    def get_all_with_kpd(self) -> List[Dict[str, Any]]:
        """Получить всех сотрудников с данными КПД"""
        employees = self.get_all()
        result = []

        for emp in employees:
            emp_data = emp.employee_data
            result.append({
                "id": emp.id,
                "number": emp.number,
                "full_name": f"{emp.last_name} {emp.first_name} {emp.middle_name or ''}".strip(),
                "position": emp.position,
                "kpd_rating": emp_data.kpd_rating if emp_data else 0.0,
                "kpd_level": emp_data.kpd_level if emp_data else "Нет данных",
                "tasks_completed": emp_data.tasks_completed_total if emp_data else 0
            })

        # Сортируем по КПД
        result.sort(key=lambda x: x["kpd_rating"], reverse=True)
        return result

    def get_by_department(self, department_id: int) -> List[Employee]:
        stmt = select(Employee).where(Employee.department_id == department_id).order_by(Employee.last_name)
        return list(self.session.scalars(stmt))

    def get_by_division(self, division_id: int) -> List[Employee]:
        stmt = select(Employee).where(Employee.division_id == division_id).order_by(Employee.last_name)
        return list(self.session.scalars(stmt))

    def search(self, query: str) -> List[Employee]:
        search_pattern = f"%{query}%"
        stmt = select(Employee).where(
            (Employee.last_name.ilike(search_pattern)) |
            (Employee.first_name.ilike(search_pattern)) |
            (Employee.middle_name.ilike(search_pattern))
        ).order_by(Employee.last_name)
        return list(self.session.scalars(stmt))

    # =========================
    # Создание
    # =========================
    def create(self, data: dict) -> Employee:
        max_number = self.session.query(func.max(Employee.number)).scalar()
        next_number = (max_number + 1) if max_number else 1

        employee = Employee(
            number=next_number,
            **data
        )
        self.session.add(employee)
        self.session.flush()
        return employee

    # =========================
    # Обновление
    # =========================
    def update(self, employee_id: int, data: dict) -> Optional[Employee]:
        employee = self.get_by_id(employee_id)
        if not employee:
            return None

        employee_fields = ['last_name', 'first_name', 'middle_name', 'position',
                           'department_id', 'division_id', 'organization_id',
                           'work_number', 'phone_number', 'email', 'chat_id', 'birth_date']

        for key, value in data.items():
            if key in employee_fields and value is not None:
                setattr(employee, key, value)

        return employee

    def get_full_name(self, employee_id: int) -> str:
        try:
            employee = self.get_by_id(employee_id)
            if not employee:
                return "Не назначен"

            parts = []
            if hasattr(employee, 'last_name') and employee.last_name:
                parts.append(employee.last_name)
            if hasattr(employee, 'first_name') and employee.first_name:
                parts.append(employee.first_name)
            if hasattr(employee, 'middle_name') and employee.middle_name:
                parts.append(employee.middle_name)

            full_name = ' '.join(parts).strip()
            return full_name if full_name else f"ID: {employee_id}"
        except Exception as e:
            print(f"⚠️ Ошибка в get_full_name: {e}")
            return f"ID: {employee_id}"

    # =========================
    # Удаление (только в employees)
    # =========================
    def hard_delete(self, employee_id: int) -> bool:
        employee = self.get_by_id(employee_id)
        if employee:
            self.session.delete(employee)
            return True
        return False