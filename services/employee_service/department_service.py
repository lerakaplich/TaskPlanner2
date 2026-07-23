# services/employee_service/department_service.py

from typing import List, Optional, Dict, Any
from sqlalchemy import text
from models.employees import Department, Division
from .employee_base_service import EmployeeBaseService


class DepartmentService(EmployeeBaseService):
    """Работа с отделами"""

    def get_all_departments(self) -> List[Dict[str, Any]]:
        """Получить все отделы"""
        try:
            departments = self.session.query(Department).order_by(Department.name).all()
            return [self._department_to_dict(dept) for dept in departments]
        except Exception as e:
            print(f"❌ Ошибка загрузки отделов: {e}")
            return []

    def get_department_card_data(self, department_id: int = None) -> Dict[str, Any]:
        """Возвращает данные отдела для карточки"""
        try:
            if department_id is None:
                departments = self.session.query(Department).all()
                return [self._department_to_card_dict(dept) for dept in departments]
            else:
                department = self.session.get(Department, department_id)
                return self._department_to_card_dict(department) if department else None
        except Exception as e:
            print(f"❌ Ошибка в get_department_card_data: {e}")
            return [] if department_id is None else None

    def get_department_by_id(self, department_id: int) -> Optional[Dict[str, Any]]:
        try:
            department = self.session.get(Department, department_id)
            return self._department_to_dict(department) if department else None
        except Exception as e:
            print(f"❌ Ошибка загрузки отдела {department_id}: {e}")
            return None

    def get_other_departments(self, exclude_department_id: int) -> List[Dict[str, Any]]:
        try:
            departments = self.session.query(Department).filter(
                Department.id != exclude_department_id
            ).all()
            return [self._department_to_card_dict(dept) for dept in departments]
        except Exception as e:
            print(f"❌ Ошибка в get_other_departments: {e}")
            return []

    def create_department(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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

    def save_department_from_dialog(self, department_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            department_id = department_data.get('id')
            if department_id:
                success = self.update_department(department_id, department_data)
                if success:
                    return self.get_department_card_data(department_id)
                return None
            else:
                return self.create_department(department_data)
        except Exception as e:
            print(f"❌ Ошибка в save_department_from_dialog: {e}")
            return None

    def filter_departments(self, departments: List[Dict], search_text: str = None,
                           division_id: int = None) -> List[Dict]:
        filtered = departments.copy()
        if search_text:
            search_lower = search_text.lower().strip()
            filtered = [d for d in filtered if search_lower in d.get('name', '').lower()]
        if division_id:
            filtered = [d for d in filtered if d.get('division_id') == division_id]
        return filtered

    def get_filtered_departments_data(self, search_text: str = None,
                                      division_id: int = None) -> List[Dict]:
        all_departments = self.get_department_card_data()
        return self.filter_departments(all_departments, search_text, division_id)

    def validate_department_form(self, form_data: Dict[str, Any]) -> tuple[bool, str]:
        if not form_data.get('name', '').strip():
            return False, "Название отдела обязательно!"

        number = form_data.get('number')
        if not number:
            return False, "Номер отдела обязателен!"

        try:
            int(number)
        except (ValueError, TypeError):
            return False, "Номер отдела должен быть числом!"

        if not form_data.get('phone_number', '').strip():
            return False, "Укажите номер телефона!"

        if not form_data.get('division_id'):
            return False, "Выберите подразделение!"

        return True, ""

    def _department_to_dict(self, department: Department) -> Dict[str, Any]:
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
        except Exception:
            result['division_name'] = '—'
        return result

    def debug_department_boss(self, department_id: int):
        """Отладочный метод для проверки поля boss"""
        try:
            department = self.session.get(Department, department_id)
            if department:
                print(f"🔍 Отладка отдела ID={department_id}")
                print(f"   Название: {department.name}")
                print(f"   boss (сырое значение): '{department.boss}'")
                print(f"   boss тип: {type(department.boss)}")
                boss_ids = self._parse_boss_ids(department.boss)
                print(f"   boss_ids (распарсенные): {boss_ids}")
                return boss_ids
        except Exception as e:
            print(f"❌ Ошибка отладки: {e}")
        return []

    def _department_to_card_dict(self, department: Department) -> Dict[str, Any]:
        if department is None:
            return {}

        division_name = '—'
        if department.division_id:
            try:
                division = self.session.get(Division, department.division_id)
                if division:
                    division_name = division.name
            except Exception:
                pass

        boss_ids = self._parse_boss_ids(department.boss)  # <-- Парсит boss_ids
        boss_names = []
        for emp_id in boss_ids:
            emp_name = self.get_employee_short_name(emp_id)
            if emp_name:
                boss_names.append(emp_name)

        return {
            'id': department.id,
            'number': department.number,
            'name': department.name,
            'boss': department.boss,
            'boss_ids': boss_ids,  # <-- Возвращает boss_ids
            'boss_names': boss_names,
            'phone_number': department.phone_number,
            'division_id': department.division_id,
            'division_name': division_name,
            'organization_id': department.organization_id,
        }