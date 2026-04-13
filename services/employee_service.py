from typing import List, Optional, Dict, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_employees_session
from models.employees import ExternalEmployee, DepartmentFDW, DivisionFDW


class EmployeeService:
    """Сервис для работы с сотрудниками, отделами и подразделениями"""

    def __init__(self, session: Session):
        self.session = session  # session для чтения (taskplanner через FDW)

    def get_all_employees(self) -> List[Dict[str, Any]]:
        """Получить всех сотрудников"""
        try:
            stmt = select(ExternalEmployee).order_by(ExternalEmployee.last_name)
            employees = self.session.scalars(stmt).all()

            result = []
            for emp in employees:
                result.append(self._employee_to_dict(emp))

            print(f"✅ Загружено {len(result)} сотрудников")
            return result
        except Exception as e:
            print(f"❌ Ошибка при загрузке сотрудников: {e}")
            return []

    def get_employee_by_id(self, employee_id: int) -> Optional[Dict[str, Any]]:
        """Получить сотрудника по ID"""
        try:
            stmt = select(ExternalEmployee).where(ExternalEmployee.id == employee_id)
            employee = self.session.scalar(stmt)
            if employee:
                return self._employee_to_dict(employee)
            return None
        except Exception as e:
            print(f"❌ Ошибка при загрузке сотрудника {employee_id}: {e}")
            return None

    def _employee_to_dict(self, employee: ExternalEmployee) -> Dict[str, Any]:
        """Преобразует модель сотрудника в словарь"""
        result = {
            'id': employee.id,
            'number': employee.number,
            'last_name': employee.last_name,
            'first_name': employee.first_name,
            'middle_name': employee.middle_name,
            'position': employee.position,
            'rights': employee.rights or 'user',
            'phone_number': employee.phone_number,
            'work_number': getattr(employee, 'work_number', None),
            'email': employee.email,
            'birth_date': employee.birth_date,
            'department_id': employee.department_id,
            'division_id': employee.division_id,
        }

        # Получаем информацию об отделе через FDW
        if employee.department_id:
            dept = self.session.get(DepartmentFDW, employee.department_id)
            if dept:
                result['department'] = {
                    'id': dept.id,
                    'number': dept.number,
                    'name': dept.name,
                    'boss': dept.boss,
                    'phone_number': dept.phone_number
                }

        # Получаем информацию о подразделении через FDW
        if employee.division_id:
            div = self.session.get(DivisionFDW, employee.division_id)
            if div:
                result['division'] = {
                    'id': div.id,
                    'number': div.number,
                    'name': div.name,
                    'boss': div.boss,
                    'phone_number': div.phone_number,
                    'workshop_code': div.workshop_code
                }

        return result

    def get_all_departments(self) -> List[Dict[str, Any]]:
        """Получить все отделы через FDW из базы employees"""
        try:
            stmt = select(DepartmentFDW).order_by(DepartmentFDW.name)
            departments = self.session.scalars(stmt).all()

            result = []
            for dept in departments:
                dept_dict = {
                    'id': dept.id,
                    'number': dept.number,
                    'name': dept.name,
                    'boss': dept.boss,
                    'phone_number': dept.phone_number,
                    'division_id': dept.division_id,
                }
                # Получаем название подразделения
                if dept.division_id:
                    div = self.session.get(DivisionFDW, dept.division_id)
                    if div:
                        dept_dict['division'] = div.name
                result.append(dept_dict)

            print(f"✅ Загружено {len(result)} отделов через FDW")
            return result
        except Exception as e:
            print(f"❌ Ошибка при загрузке отделов: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_department_by_id(self, department_id: int) -> Optional[Dict[str, Any]]:
        """Получить отдел по ID"""
        try:
            dept = self.session.get(DepartmentFDW, department_id)
            if dept:
                return {
                    'id': dept.id,
                    'number': dept.number,
                    'name': dept.name,
                    'boss': dept.boss,
                    'phone_number': dept.phone_number,
                    'division_id': dept.division_id,
                }
            return None
        except Exception as e:
            print(f"❌ Ошибка при загрузке отдела {department_id}: {e}")
            return None

    def get_all_divisions(self) -> List[Dict[str, Any]]:
        """Получить все подразделения через FDW из базы employees"""
        try:
            stmt = select(DivisionFDW).order_by(DivisionFDW.name)
            divisions = self.session.scalars(stmt).all()

            result = []
            for div in divisions:
                result.append({
                    'id': div.id,
                    'number': div.number,
                    'name': div.name,
                    'boss': div.boss,
                    'phone_number': div.phone_number,
                    'workshop_code': div.workshop_code,
                })

            print(f"✅ Загружено {len(result)} подразделений через FDW")
            return result
        except Exception as e:
            print(f"❌ Ошибка при загрузке подразделений: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_division_by_id(self, division_id: int) -> Optional[Dict[str, Any]]:
        """Получить подразделение по ID"""
        try:
            div = self.session.get(DivisionFDW, division_id)
            if div:
                return {
                    'id': div.id,
                    'number': div.number,
                    'name': div.name,
                    'boss': div.boss,
                    'phone_number': div.phone_number,
                    'workshop_code': div.workshop_code,
                }
            return None
        except Exception as e:
            print(f"❌ Ошибка при загрузке подразделения {division_id}: {e}")
            return None

    def _get_employees_db_session(self):
        """Получить сессию для прямой записи в базу employees"""
        return get_employees_session()

    def create_division_in_db(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Создание подразделения в базе employees (схема public)
        """
        db_session = self._get_employees_db_session()
        try:
            from models.employees import Division

            # Получаем следующий номер
            max_number = db_session.query(Division.number).order_by(Division.number.desc()).first()
            next_number = (max_number[0] + 1) if max_number else 1

            new_division = Division(
                number=next_number,
                name=data.get('name'),
                phone_number=data.get('phone_number'),
                workshop_code=data.get('workshop_code', ''),  # ← расшифровка
                boss=data.get('boss', ''),
                organization_id=1
            )

            db_session.add(new_division)
            db_session.commit()
            db_session.refresh(new_division)

            print(f"✅ Подразделение создано с ID: {new_division.id}")
            return {
                'id': new_division.id,
                'number': new_division.number,
                'name': new_division.name,
                'phone_number': new_division.phone_number,
                'workshop_code': new_division.workshop_code,  # ← расшифровка
                'boss': new_division.boss,
                'description': data.get('description', '')  # ← добавляем description
            }

        except Exception as e:
            db_session.rollback()
            print(f"❌ Ошибка при создании подразделения: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            db_session.close()

    def update_division_in_db(self, division_id: int, data: Dict[str, Any]) -> bool:
        """
        Обновление подразделения в базе employees (схема public)
        """
        db_session = self._get_employees_db_session()
        try:
            from models.employees import Division

            division = db_session.get(Division, division_id)
            if not division:
                print(f"❌ Подразделение {division_id} не найдено в public.divisions")
                return False

            # Обновляем поля
            if 'name' in data:
                division.name = data['name']
            if 'number' in data:
                division.number = data['number']
            if 'phone_number' in data:
                division.phone_number = data['phone_number']
            if 'workshop_code' in data:  # ← расшифровка
                division.workshop_code = data['workshop_code']
            if 'boss' in data:
                division.boss = data['boss']

            db_session.commit()
            print(f"✅ Подразделение {division_id} обновлено в БД employees (public.divisions)")
            return True

        except Exception as e:
            db_session.rollback()
            print(f"❌ Ошибка при обновлении подразделения: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db_session.close()

    def delete_division_in_db(self, division_id: int) -> bool:
        """
        Удаление подразделения из базы employees (схема public)
        """
        db_session = self._get_employees_db_session()
        try:
            from models.employees import Division

            division = db_session.get(Division, division_id)
            if division:
                db_session.delete(division)
                db_session.commit()
                print(f"✅ Подразделение {division_id} удалено из БД employees (public.divisions)")
                return True
            else:
                print(f"❌ Подразделение {division_id} не найдено в public.divisions")
                return False

        except Exception as e:
            db_session.rollback()
            print(f"❌ Ошибка при удалении подразделения: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db_session.close()

    def create_department_in_db(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Создание отдела в базе employees (схема public)
        """
        db_session = self._get_employees_db_session()
        try:
            from models.employees import Department

            # Получаем следующий номер
            max_number = db_session.query(Department.number).order_by(Department.number.desc()).first()
            next_number = (max_number[0] + 1) if max_number else 1

            new_department = Department(
                number=next_number,
                name=data.get('name'),
                phone_number=data.get('phone'),
                boss=data.get('boss', ''),
                division_id=data.get('division_id', 1),
                organization_id=1
            )

            db_session.add(new_department)
            db_session.commit()
            db_session.refresh(new_department)

            print(f"✅ Отдел создан с ID: {new_department.id}")
            return {
                'id': new_department.id,
                'number': new_department.number,
                'name': new_department.name,
                'phone': new_department.phone_number,
                'boss': new_department.boss,
                'division_id': new_department.division_id,
            }

        except Exception as e:
            db_session.rollback()
            print(f"❌ Ошибка при создании отдела: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            db_session.close()

    def has_departments_in_division(self, division_id: int) -> bool:
        """Проверяет, есть ли отделы в подразделении"""
        db_session = self._get_employees_db_session()
        try:
            from models.employees import Department
            count = db_session.query(Department).filter(Department.division_id == division_id).count()
            return count > 0
        except Exception as e:
            print(f"❌ Ошибка при проверке отделов: {e}")
            return False
        finally:
            db_session.close()

    def has_employees_in_division(self, division_id: int) -> bool:
        """Проверяет, есть ли сотрудники в подразделении"""
        try:
            from models.employees import ExternalEmployee
            stmt = select(ExternalEmployee).where(ExternalEmployee.division_id == division_id)
            count = len(self.session.scalars(stmt).all())
            return count > 0
        except Exception as e:
            print(f"❌ Ошибка при проверке сотрудников: {e}")
            return False

    def delete_division_cascade(self, division_id: int) -> bool:
        """
        Каскадное удаление подразделения со всеми отделами и сотрудниками
        """
        db_session = self._get_employees_db_session()
        try:
            from models.employees import Division, Department
            from models.employees import ExternalEmployee  # для чтения через FDW

            # 1. Получаем ID всех отделов в этом подразделении
            departments = db_session.query(Department.id).filter(Department.division_id == division_id).all()
            department_ids = [d[0] for d in departments]

            # 2. Обновляем сотрудников (устанавливаем division_id = NULL или удаляем)
            # Через основную сессию (FDW) обновить нельзя, поэтому используем прямое подключение
            # Для сотрудников нужно обновить division_id в базе employees
            # Но так как ExternalEmployee только для чтения, нужно использовать прямую сессию
            # Если есть таблица employees в public, обновляем там
            try:
                # Пытаемся обновить через прямую сессию (если есть таблица public.employees)
                from models.employees import LocalEmployee
                db_session.query(LocalEmployee).filter(LocalEmployee.division_id == division_id).update(
                    {'division_id': None}
                )
            except Exception as e:
                print(f"⚠️ Не удалось обновить сотрудников (возможно таблица только для чтения): {e}")

            # 3. Удаляем отделы
            for dept_id in department_ids:
                dept = db_session.get(Department, dept_id)
                if dept:
                    db_session.delete(dept)

            # 4. Удаляем подразделение
            division = db_session.get(Division, division_id)
            if division:
                db_session.delete(division)

            db_session.commit()
            print(f"✅ Каскадное удаление подразделения {division_id} выполнено")
            return True

        except Exception as e:
            db_session.rollback()
            print(f"❌ Ошибка при каскадном удалении подразделения: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db_session.close()

    def reassign_division_dependencies(self, old_division_id: int, new_division_id: int) -> bool:
        """
        Переназначение всех отделов и сотрудников на новое подразделение
        """
        db_session = self._get_employees_db_session()
        try:
            from models.employees import Department

            # 1. Обновляем отделы
            db_session.query(Department).filter(Department.division_id == old_division_id).update(
                {'division_id': new_division_id}
            )

            # 2. Обновляем сотрудников (через прямую сессию, если есть)
            try:
                from models.employees import LocalEmployee
                db_session.query(LocalEmployee).filter(LocalEmployee.division_id == old_division_id).update(
                    {'division_id': new_division_id}
                )
            except Exception as e:
                print(f"⚠️ Не удалось обновить сотрудников: {e}")

            db_session.commit()
            print(f"✅ Переназначены отделы и сотрудники с {old_division_id} на {new_division_id}")
            return True

        except Exception as e:
            db_session.rollback()
            print(f"❌ Ошибка при переназначении: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db_session.close()

    def update_department_in_db(self, department_id: int, data: Dict[str, Any]) -> bool:
        """
        Обновление отдела в базе employees (схема public)
        """
        db_session = self._get_employees_db_session()
        try:
            from models.employees import Department

            department = db_session.get(Department, department_id)
            if not department:
                print(f"❌ Отдел {department_id} не найден в public.departments")
                return False

            if 'name' in data:
                department.name = data['name']
            if 'number' in data:
                department.number = data['number']
            if 'phone' in data:
                department.phone_number = data['phone']
            if 'boss' in data:
                department.boss = data['boss']
            if 'division_id' in data:
                department.division_id = data['division_id']

            db_session.commit()
            print(f"✅ Отдел {department_id} обновлён в БД employees (public.departments)")
            return True

        except Exception as e:
            db_session.rollback()
            print(f"❌ Ошибка при обновлении отдела: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db_session.close()

    def delete_department_in_db(self, department_id: int) -> bool:
        """
        Удаление отдела из базы employees (схема public)
        """
        db_session = self._get_employees_db_session()
        try:
            from models.employees import Department

            department = db_session.get(Department, department_id)
            if department:
                db_session.delete(department)
                db_session.commit()
                print(f"✅ Отдел {department_id} удалён из БД employees (public.departments)")
                return True
            else:
                print(f"❌ Отдел {department_id} не найден в public.departments")
                return False

        except Exception as e:
            db_session.rollback()
            print(f"❌ Ошибка при удалении отдела: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db_session.close()

    def search_employees(self, query: str) -> List[Dict[str, Any]]:
        """Поиск сотрудников"""
        try:
            search = f"%{query}%"
            stmt = select(ExternalEmployee).where(
                (ExternalEmployee.last_name.ilike(search)) |
                (ExternalEmployee.first_name.ilike(search)) |
                (ExternalEmployee.middle_name.ilike(search)) |
                (ExternalEmployee.position.ilike(search))
            ).order_by(ExternalEmployee.last_name)

            employees = self.session.scalars(stmt).all()
            return [self._employee_to_dict(emp) for emp in employees]
        except Exception as e:
            print(f"❌ Ошибка при поиске сотрудников: {e}")
            return []

    def _map_role_to_rights(self, role_text: str) -> str:
        """Преобразует текст роли в значение rights"""
        role_map = {
            'Суперадминистратор': 'superadmin',
            'Администратор': 'admin',
            'Пользователь': 'user'
        }
        return role_map.get(role_text, 'user')

    def create_employee(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        print("⚠️ Создание сотрудников через FDW недоступно (только чтение)")
        return None

    def update_employee(self, employee_id: int, data: Dict[str, Any]) -> bool:
        print("⚠️ Обновление сотрудников через FDW недоступно (только чтение)")
        return False

    def delete_employee(self, employee_id: int) -> bool:
        print("⚠️ Удаление сотрудников через FDW недоступно (только чтение)")
        return False

    def create_department(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        print("⚠️ Создание отделов через FDW недоступно (только чтение)")
        return None

    def update_department(self, department_id: int, data: Dict[str, Any]) -> bool:
        print("⚠️ Обновление отделов через FDW недоступно (только чтение)")
        return False

    def delete_department(self, department_id: int) -> bool:
        print("⚠️ Удаление отделов через FDW недоступно (только чтение)")
        return False

    def create_division(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        print("⚠️ Создание подразделений через FDW недоступно (только чтение)")
        return None

    def update_division(self, division_id: int, data: Dict[str, Any]) -> bool:
        print("⚠️ Обновление подразделений через FDW недоступно (только чтение)")
        return False

    def delete_division(self, division_id: int) -> bool:
        print("⚠️ Удаление подразделений через FDW недоступно (только чтение)")
        return False