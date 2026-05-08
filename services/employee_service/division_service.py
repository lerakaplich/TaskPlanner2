# services/employee_service/division_service.py

from typing import List, Optional, Dict, Any
from models.employees import Division, Department, Employee
from .employee_base_service import EmployeeBaseService


class DivisionService(EmployeeBaseService):
    """Работа с подразделениями"""

    def get_all_divisions(self) -> List[Dict[str, Any]]:
        """Получить все подразделения"""
        try:
            divisions = self.session.query(Division).order_by(Division.name).all()
            return [self._division_to_dict(div) for div in divisions]
        except Exception as e:
            print(f"❌ Ошибка загрузки подразделений: {e}")
            return []

    def get_division_card_data(self, division_id: int = None) -> Dict[str, Any]:
        """Возвращает данные подразделения для карточки"""
        try:
            if division_id is None:
                divisions = self.session.query(Division).all()
                return [self._division_to_card_dict(div) for div in divisions]
            else:
                division = self.session.get(Division, division_id)
                return self._division_to_card_dict(division) if division else None
        except Exception as e:
            print(f"❌ Ошибка в get_division_card_data: {e}")
            return [] if division_id is None else None

    def get_division_by_id(self, division_id: int) -> Optional[Dict[str, Any]]:
        try:
            division = self.session.get(Division, division_id)
            return self._division_to_dict(division) if division else None
        except Exception as e:
            print(f"❌ Ошибка загрузки подразделения {division_id}: {e}")
            return None

    def get_other_divisions(self, exclude_division_id: int) -> List[Dict[str, Any]]:
        try:
            divisions = self.session.query(Division).filter(
                Division.id != exclude_division_id
            ).all()
            return [self._division_to_card_dict(div) for div in divisions]
        except Exception as e:
            print(f"❌ Ошибка в get_other_divisions: {e}")
            return []

    def create_division(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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

    def save_division_from_dialog(self, division_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            division_id = division_data.get('id')
            if division_id:
                success = self.update_division(division_id, division_data)
                if success:
                    return self.get_division_card_data(division_id)
                return None
            else:
                return self.create_division(division_data)
        except Exception as e:
            print(f"❌ Ошибка в save_division_from_dialog: {e}")
            return None

    def prepare_division_for_dialog(self, division_id: int) -> Optional[Dict[str, Any]]:
        try:
            division = self.session.get(Division, division_id)
            if not division:
                return None

            return {
                'id': division.id,
                'name': division.name,
                'number': division.number,
                'phone_number': division.phone_number,
                'workshop_code': division.workshop_code or '',
                'boss_ids': self._parse_boss_ids(division.boss),
                'boss': division.boss,
            }
        except Exception as e:
            print(f"❌ Ошибка в prepare_division_for_dialog: {e}")
            return None

    def validate_division_form(self, form_data: Dict[str, Any]) -> tuple[bool, str]:
        if not form_data.get('name', '').strip():
            return False, "Название подразделения обязательно!"

        number = form_data.get('number')
        if not number:
            return False, "Номер подразделения обязателен!"

        try:
            int(number)
        except (ValueError, TypeError):
            return False, "Номер подразделения должен быть числом!"

        if not form_data.get('phone_number', '').strip():
            return False, "Укажите номер телефона!"

        return True, ""

    def _division_to_dict(self, division: Division) -> Dict[str, Any]:
        return {
            'id': division.id,
            'number': division.number,
            'name': division.name,
            'boss': division.boss,
            'phone_number': division.phone_number,
            'workshop_code': division.workshop_code,
        }

    def _division_to_card_dict(self, division: Division) -> Dict[str, Any]:
        if division is None:
            return {}

        boss_ids = self._parse_boss_ids(division.boss)
        boss_names = []
        for emp_id in boss_ids:
            emp_name = self.get_employee_short_name(emp_id)
            if emp_name:
                boss_names.append(emp_name)

        return {
            'id': division.id,
            'number': division.number,
            'name': division.name,
            'boss': division.boss,
            'boss_ids': boss_ids,
            'boss_names': boss_names,
            'phone_number': division.phone_number,
            'workshop_code': division.workshop_code or '',
            'organization_id': division.organization_id,
        }