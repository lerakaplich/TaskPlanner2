# services/employee_service.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, text
import traceback
from datetime import datetime  # ← ДОБАВИТЬ

from database import get_employees_session, get_tasks_session
from models.employees import Employee, Department, Division, EmployeeData, RoleEnum
from models.projects import BoardColumn
from models.tasks import Tag, TaskTag
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

    def get_employee_card_data(self, employee_id: int = None) -> Dict[str, Any]:
        """
        Возвращает данные сотрудника для карточки
        Если employee_id не указан или None, возвращает всех сотрудников
        """
        try:
            self._ensure_session_valid()

            if employee_id is None:
                # Возвращаем всех сотрудников
                employees = self.session.query(Employee).all()
                return [self._employee_to_card_dict(emp) for emp in employees]
            else:
                # Возвращаем одного сотрудника
                employee = self.repo.get_by_id(employee_id)
                return self._employee_to_card_dict(employee) if employee else None
        except Exception as e:
            print(f"❌ Ошибка в get_employee_card_data: {e}")
            traceback.print_exc()
            return [] if employee_id is None else None

    def _employee_to_card_dict(self, employee: Employee) -> Dict[str, Any]:
        """Преобразует модель сотрудника в словарь для карточки"""
        if employee is None:
            return {}

        # Получаем роль
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

        # Получаем отдел
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

        # Получаем подразделение
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
            'rights': role,  # Для обратной совместимости
            'is_active': True,
        }

    def save_employee_from_dialog(self, employee_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Сохраняет сотрудника из данных диалога
        Если есть id - обновляет, если нет - создает нового
        """
        try:
            employee_id = employee_data.get('id')

            if employee_id:
                # Обновляем существующего
                success = self.update_employee(employee_id, employee_data)
                if success:
                    return self.get_employee_card_data(employee_id)
                return None
            else:
                # Создаем нового
                # Убираем поля, которые не нужны при создании
                clean_data = {k: v for k, v in employee_data.items()
                              if k not in ['id', 'rights', 'role', 'generated_password']}
                employee = self.repo.create(clean_data)
                self.session.commit()

                # Устанавливаем роль если передана
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
            traceback.print_exc()
            return None

    def delete_employee_by_id(self, employee_id: int) -> bool:
        """Удаляет сотрудника по ID"""
        return self.delete_employee(employee_id)

    def get_filter_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Возвращает данные для фильтров (отделы и подразделения)"""
        return {
            'departments': self.get_all_departments(),
            'divisions': self.get_all_divisions()
        }

    def get_role_display_name(self, role: str) -> str:
        """Возвращает отображаемое имя роли"""
        role_map = {
            'superadmin': 'Суперадминистратор',
            'admin': 'Администратор',
            'user': 'Пользователь'
        }
        return role_map.get(role, 'Пользователь')

    def get_role_color(self, role: str) -> str:
        """Возвращает цвет для роли"""
        role_colors = {
            'superadmin': '#D22730',  # красный
            'admin': '#ccab6e',  # золотой
            'user': '#1B232A'  # тёмно-серый
        }
        return role_colors.get(role, '#1B232A')

    def format_phone_display(self, phone: str) -> str:
        """Форматирует номер телефона для отображения"""
        if not phone:
            return '—'
        if phone.startswith('375'):
            return '+' + phone
        return phone

    def get_employee_full_name(self, employee_id: int) -> str:
        """Возвращает полное ФИО сотрудника по ID"""
        employee = self.repo.get_by_id(employee_id)
        if employee:
            return self._get_full_name(employee)
        return 'Неизвестный'

    def get_roles_list(self) -> List[str]:
        """Возвращает список доступных ролей для отображения в комбобоксе"""
        return ['Пользователь', 'Администратор', 'Суперадминистратор']

    def validate_employee_form(self, form_data: Dict[str, Any]) -> tuple[bool, str]:
        """Валидирует данные формы сотрудника"""
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

        # Очищаем от нецифровых символов
        phone_digits = ''.join(c for c in phone if c.isdigit())
        if len(phone_digits) not in [9, 12]:  # 9 цифр без кода или 375XXXXXXXXX
            return False, "Введите 9 цифр номера телефона (без +375)"

        email = form_data.get('email', '')
        if email and '@' not in email:
            return False, "Пожалуйста, введите корректный email"

        return True, ""

    def generate_registration_password(self) -> str:
        """Генерирует пароль для регистрации"""
        import secrets
        import string
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))

    def prepare_employee_for_display(self, employee_data: Dict[str, Any]) -> Dict[str, Any]:
        """Подготавливает данные сотрудника для отображения в UI"""
        result = employee_data.copy()

        # Форматируем телефон для отображения
        if result.get('phone_number'):
            result['display_phone'] = self.format_phone_display(result['phone_number'])
        else:
            result['display_phone'] = '—'

        # Устанавливаем отображаемое имя роли и цвет
        role = result.get('rights') or result.get('role', 'user')
        result['role_display'] = self.get_role_display_name(role)
        result['role_color'] = self.get_role_color(role)

        return result

    def get_employee_full_info(self, employee_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает полную информацию о сотруднике для диалога редактирования"""
        try:
            employee = self.repo.get_by_id(employee_id)
            if not employee:
                return None

            # Получаем роль
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

    # =========================
    # Отделы
    # =========================
    def get_department_card_data(self, department_id: int = None) -> Dict[str, Any]:
        """
        Возвращает данные отдела для карточки
        Если department_id не указан или None, возвращает все отделы
        """
        try:
            self._ensure_session_valid()

            if department_id is None:
                departments = self.session.query(Department).all()
                return [self._department_to_card_dict(dept) for dept in departments]
            else:
                department = self.session.get(Department, department_id)
                return self._department_to_card_dict(department) if department else None
        except Exception as e:
            print(f"❌ Ошибка в get_department_card_data: {e}")
            traceback.print_exc()
            return [] if department_id is None else None

    def _department_to_card_dict(self, department: Department) -> Dict[str, Any]:
        """Преобразует модель отдела в словарь для карточки"""
        if department is None:
            return {}

        # Получаем название подразделения
        division_name = '—'
        if department.division_id:
            try:
                division = self.session.get(Division, department.division_id)
                if division:
                    division_name = division.name
            except Exception:
                pass

        # Получаем список руководителей
        boss_ids = self._parse_boss_ids(department.boss)
        boss_names = []
        for emp_id in boss_ids:
            emp_name = self.get_employee_short_name(emp_id)
            if emp_name:  # ← Добавляем только если имя не пустое
                boss_names.append(emp_name)

        return {
            'id': department.id,
            'number': department.number,
            'name': department.name,
            'boss': department.boss,
            'boss_ids': boss_ids,
            'boss_names': boss_names,
            'phone_number': department.phone_number,
            'division_id': department.division_id,
            'division_name': division_name,
            'organization_id': department.organization_id,
        }

    def _parse_boss_ids(self, boss_field) -> List[int]:
        """Парсит поле boss и возвращает список ID сотрудников"""
        if not boss_field:
            return []

        if isinstance(boss_field, str):
            if all(c.isdigit() or c == ',' or c.isspace() for c in boss_field):
                ids = []
                for part in boss_field.split(','):
                    part = part.strip()
                    if part and part.isdigit():
                        ids.append(int(part))
                return ids
            return []
        elif isinstance(boss_field, (int, float)):
            return [int(boss_field)]
        elif isinstance(boss_field, list):
            return boss_field
        return []

    def get_employee_short_name(self, employee_id: int) -> str:
        """Возвращает краткое ФИО сотрудника: Фамилия И.О."""
        employee = self.repo.get_by_id(employee_id)
        if not employee:
            return ""  # ← Возвращаем пустую строку вместо ID

        last_name = employee.last_name or ''
        first_name = employee.first_name or ''
        middle_name = employee.middle_name or ''

        initials = ""
        if first_name:
            initials += first_name[0] + "."
        if middle_name:
            initials += middle_name[0] + "."

        result = f"{last_name} {initials}".strip() if initials else last_name
        return result if result.strip() else ""  # ← Если пусто, возвращаем пустую строку

    def get_all_employees_for_selector(self) -> List[Dict[str, Any]]:
        """Возвращает список всех сотрудников для выбора в диалогах"""
        try:
            employees = self.session.query(Employee).all()
            result = []
            for emp in employees:
                full_name = self._get_full_name(emp)
                result.append({
                    'id': emp.id,
                    'full_name': full_name,
                    'position': emp.position or 'Сотрудник'
                })
            return result
        except Exception as e:
            print(f"❌ Ошибка в get_all_employees_for_selector: {e}")
            return []

    def get_divisions_for_selector(self) -> List[Dict[str, Any]]:
        """Возвращает список подразделений для выбора в диалогах"""
        try:
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
        except Exception as e:
            print(f"❌ Ошибка в get_divisions_for_selector: {e}")
            return []

    def save_department_from_dialog(self, department_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Сохраняет отдел из данных диалога
        Если есть id - обновляет, если нет - создает новый
        """
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

    def delete_department_by_id(self, department_id: int, delete_employees: bool = False,
                                target_department_id: int = None) -> bool:
        """
        Удаляет отдел
        Если delete_employees=True и есть сотрудники:
            - если target_department_id указан -> переназначает сотрудников
            - если target_department_id не указан -> удаляет всех сотрудников
        """
        try:
            has_employees = self.has_employees_in_department(department_id)

            if has_employees and target_department_id:
                # Переназначаем сотрудников в другой отдел
                success = self.reassign_department_employees(department_id, target_department_id)
                if not success:
                    return False

            # Удаляем отдел
            if has_employees and not target_department_id and delete_employees:
                # Каскадное удаление
                return self.delete_department_cascade(department_id)
            else:
                return self.delete_department(department_id)
        except Exception as e:
            print(f"❌ Ошибка в delete_department_by_id: {e}")
            return False

    def get_other_departments(self, exclude_department_id: int) -> List[Dict[str, Any]]:
        """Возвращает список всех отделов, кроме указанного"""
        try:
            departments = self.session.query(Department).filter(
                Department.id != exclude_department_id
            ).all()
            return [self._department_to_card_dict(dept) for dept in departments]
        except Exception as e:
            print(f"❌ Ошибка в get_other_departments: {e}")
            return []

    def validate_department_form(self, form_data: Dict[str, Any]) -> tuple[bool, str]:
        """Валидирует данные формы отдела"""
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

    def filter_departments(self, departments: List[Dict], search_text: str = None,
                           division_id: int = None) -> List[Dict]:
        """Фильтрует отделы по поисковому запросу и подразделению"""
        filtered = departments.copy()

        if search_text:
            search_lower = search_text.lower().strip()
            filtered = [d for d in filtered
                        if search_lower in d.get('name', '').lower()]

        if division_id:
            filtered = [d for d in filtered
                        if d.get('division_id') == division_id]

        return filtered

    def get_filtered_departments_data(self, search_text: str = None,
                                      division_id: int = None) -> List[Dict]:
        """Возвращает отфильтрованные отделы с данными для карточек"""
        all_departments = self.get_department_card_data()
        return self.filter_departments(all_departments, search_text, division_id)

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
        try:
            self._ensure_session_valid()
            employee = self.repo.get_by_id(employee_id)
            return self._employee_to_dict(employee) if employee else None
        except Exception as e:
            print(f"❌ Ошибка при получении сотрудника {employee_id}: {e}")
            return None

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
            self._ensure_session_valid()

            # Получаем сотрудника через репозиторий
            employee = self.repo.get_by_id(employee_id)
            if not employee:
                print(f"❌ Сотрудник с ID {employee_id} не найден")
                return False

            # Отделяем поля Employee от полей EmployeeData
            employee_fields = ['last_name', 'first_name', 'middle_name', 'position',
                               'department_id', 'division_id', 'organization_id',
                               'work_number', 'phone_number', 'email', 'chat_id', 'birth_date']

            # Обновляем поля Employee
            for key, value in data.items():
                if key in employee_fields and value is not None:
                    setattr(employee, key, value)

            self.session.commit()

            # Обновляем роль если передана (в EmployeeData)
            if 'role' in data and data['role']:
                role_value = data['role']
                if isinstance(role_value, str):
                    role_value = RoleEnum(role_value)
                self.repo.update_role(employee_id, role_value)

            # Обновляем статус активности если передан
            if 'is_active' in data and data['is_active'] is not None:
                self.repo.set_active(employee_id, data['is_active'])

            # Коммитим изменения в EmployeeData
            if self.tasks_session:
                self.tasks_session.commit()

            print(f"✅ Сотрудник {employee_id} успешно обновлен")
            return True

        except Exception as e:
            self.session.rollback()
            if self.tasks_session:
                self.tasks_session.rollback()
            print(f"❌ Ошибка при обновлении сотрудника: {e}")
            import traceback
            traceback.print_exc()
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

        department_name = '—'
        if employee.department_id:
            try:
                result = self.session.execute(
                    text("SELECT name FROM departments WHERE id = :dept_id"),
                    {'dept_id': employee.department_id}
                ).fetchone()
                if result:
                    department_name = result[0]
                    print(f"  ✓ Найден отдел: ID={employee.department_id} -> '{department_name}'")
                else:
                    print(f"  ✗ Отдел с ID={employee.department_id} не найден")
            except Exception as e:
                print(f"⚠️ Ошибка получения отдела: {e}")

        division_name = '—'
        if employee.division_id:
            try:
                result = self.session.execute(
                    text("SELECT name FROM divisions WHERE id = :div_id"),
                    {'div_id': employee.division_id}
                ).fetchone()
                if result:
                    division_name = result[0]
                    print(f"  ✓ Найдено подразделение: ID={employee.division_id} -> '{division_name}'")
                else:
                    print(f"  ✗ Подразделение с ID={employee.division_id} не найдено")
            except Exception as e:
                print(f"⚠️ Ошибка получения подразделения: {e}")

        result_dict = {
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
            'department_name': department_name,  # ← ДОЛЖНО БЫТЬ vvv, ккаа и т.д.
            'division_id': employee.division_id,
            'division_name': division_name,  # ← ДОЛЖНО БЫТЬ чсмпильдбэ
            'is_active': True,
            'role': 'user',
            'last_login': None,
        }

        print(f"  Результат для сотрудника {employee.id}: отдел='{department_name}', подразделение='{division_name}'")
        return result_dict

    def _get_full_name(self, employee: Employee) -> str:
        """Формирует ФИО сотрудника"""
        parts = [employee.last_name, employee.first_name]
        if employee.middle_name:
            parts.append(employee.middle_name)
        return ' '.join(parts)

    def get_department_by_id(self, department_id: int) -> Optional[Dict[str, Any]]:
        """Получить отдел по ID"""
        try:
            department = self.session.get(Department, department_id)
            return self._department_to_dict(department) if department else None
        except Exception as e:
            print(f"❌ Ошибка загрузки отдела {department_id}: {e}")
            return None

    def delete_division_cascade(self, division_id: int) -> bool:
        """Каскадное удаление подразделения вместе с отделами и сотрудниками"""
        try:
            self._ensure_session_valid()

            # Получаем все отделы в подразделении
            departments = self.session.query(Department).filter(Department.division_id == division_id).all()

            for dept in departments:
                # Удаляем сотрудников в отделе
                employees = self.session.query(Employee).filter(Employee.department_id == dept.id).all()
                for emp in employees:
                    self.repo.delete(emp.id)
                # Удаляем отдел
                self.session.delete(dept)

            # Удаляем подразделение
            division = self.session.get(Division, division_id)
            if division:
                self.session.delete(division)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при каскадном удалении подразделения: {e}")
            return False

    def reassign_division_dependencies(self, from_division_id: int, to_division_id: int) -> bool:
        """Переназначение всех отделов и сотрудников из одного подразделения в другое"""
        try:
            self._ensure_session_valid()

            # Обновляем отделы
            self.session.query(Department).filter(
                Department.division_id == from_division_id
            ).update({Department.division_id: to_division_id})

            # Обновляем сотрудников (через отделы уже обновились)
            # Но также есть сотрудники, у которых division_id напрямую
            self.session.query(Employee).filter(
                Employee.division_id == from_division_id
            ).update({Employee.division_id: to_division_id})

            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при переназначении: {e}")
            return False

    def delete_department_cascade(self, department_id: int) -> bool:
        """Каскадное удаление отдела вместе со всеми сотрудниками"""
        try:
            self._ensure_session_valid()

            # Получаем всех сотрудников в отделе
            employees = self.session.query(Employee).filter(Employee.department_id == department_id).all()

            # Удаляем сотрудников (мягкое удаление через EmployeeData)
            for emp in employees:
                self.repo.delete(emp.id)  # мягкое удаление
                if self.tasks_session:
                    self.tasks_session.commit()

            # Удаляем сам отдел
            department = self.session.get(Department, department_id)
            if department:
                self.session.delete(department)
                self.session.commit()
                return True

            return False
        except Exception as e:
            self.session.rollback()
            if self.tasks_session:
                self.tasks_session.rollback()
            print(f"❌ Ошибка при каскадном удалении отдела: {e}")
            return False

    def reassign_department_employees(self, from_department_id: int, to_department_id: int) -> bool:
        """Переназначение всех сотрудников из одного отдела в другой"""
        try:
            self._ensure_session_valid()

            # Обновляем department_id у всех сотрудников
            result = self.session.query(Employee).filter(
                Employee.department_id == from_department_id
            ).update({Employee.department_id: to_department_id})

            self.session.commit()
            print(f"✅ Переназначено {result} сотрудников из отдела {from_department_id} в отдел {to_department_id}")
            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при переназначении сотрудников: {e}")
            return False

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
    # Подразделения
    # =========================
    def get_division_display_data(self, division_id: int = None) -> Any:
        """
        Возвращает данные подразделения для отображения в карточке
        Если division_id не указан, возвращает список всех подразделений
        """
        return self.get_division_card_data(division_id)

    def get_division_edit_data(self, division_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает данные подразделения для редактирования в диалоге"""
        return self.prepare_division_for_dialog(division_id)

    def get_employees_for_division_selector(self) -> List[Dict[str, Any]]:
        """Возвращает список сотрудников для выбора руководителей"""
        return self.get_employees_for_selector()

    def get_other_divisions_for_reassignment(self, exclude_division_id: int) -> List[Dict[str, Any]]:
        """Возвращает список подразделений для переназначения"""
        return self.get_other_divisions(exclude_division_id)

    def check_division_dependencies(self, division_id: int) -> Dict[str, bool]:
        """Проверяет зависимости подразделения"""
        return {
            'has_departments': self.has_departments_in_division(division_id),
            'has_employees': self.has_employees_in_division(division_id)
        }

    def delete_division_with_options(self, division_id: int, delete_all: bool = False,
                                     target_division_id: int = None) -> bool:
        """
        Удаляет подразделение с опциями:
        - delete_all=True: каскадное удаление всего
        - target_division_id указан: переназначение на другое подразделение
        """
        return self.delete_division_by_id(
            division_id,
            delete_departments=delete_all,
            target_division_id=target_division_id
        )

    def save_division_from_dialog_data(self, division_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Сохраняет подразделение из данных диалога"""
        return self.save_division_from_dialog(division_data)

    def validate_division_form_data(self, form_data: Dict[str, Any]) -> tuple[bool, str]:
        """Валидирует данные формы подразделения"""
        return self.validate_division_form(form_data)

    def get_division_card_data(self, division_id: int = None) -> Dict[str, Any]:
        """
        Возвращает данные подразделения для карточки
        Если division_id не указан или None, возвращает все подразделения
        """
        try:
            self._ensure_session_valid()

            if division_id is None:
                divisions = self.session.query(Division).all()
                return [self._division_to_card_dict(div) for div in divisions]
            else:
                division = self.session.get(Division, division_id)
                return self._division_to_card_dict(division) if division else None
        except Exception as e:
            print(f"❌ Ошибка в get_division_card_data: {e}")
            traceback.print_exc()
            return [] if division_id is None else None

    def _division_to_card_dict(self, division: Division) -> Dict[str, Any]:
        """Преобразует модель подразделения в словарь для карточки"""
        if division is None:
            return {}

        # Получаем список руководителей
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

    def save_division_from_dialog(self, division_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Сохраняет подразделение из данных диалога
        Если есть id - обновляет, если нет - создает новый
        """
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

    def delete_division_by_id(self, division_id: int, delete_departments: bool = False,
                              target_division_id: int = None) -> bool:
        """
        Удаляет подразделение
        Если delete_departments=True и есть зависимые объекты:
            - если target_division_id указан -> переназначает отделы и сотрудников
            - если target_division_id не указан -> удаляет всё каскадно
        """
        try:
            has_departments = self.has_departments_in_division(division_id)
            has_employees = self.has_employees_in_division(division_id)

            if (has_departments or has_employees) and target_division_id:
                # Переназначаем на другое подразделение
                success = self.reassign_division_dependencies(division_id, target_division_id)
                if not success:
                    return False

            # Удаляем подразделение
            if (has_departments or has_employees) and not target_division_id and delete_departments:
                return self.delete_division_cascade(division_id)
            else:
                return self.delete_division(division_id)
        except Exception as e:
            print(f"❌ Ошибка в delete_division_by_id: {e}")
            return False

    def get_other_divisions(self, exclude_division_id: int) -> List[Dict[str, Any]]:
        """Возвращает список всех подразделений, кроме указанного"""
        try:
            divisions = self.session.query(Division).filter(
                Division.id != exclude_division_id
            ).all()
            return [self._division_to_card_dict(div) for div in divisions]
        except Exception as e:
            print(f"❌ Ошибка в get_other_divisions: {e}")
            return []

    def validate_division_form(self, form_data: Dict[str, Any]) -> tuple[bool, str]:
        """Валидирует данные формы подразделения"""
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

    def get_employees_for_selector(self) -> List[Dict[str, Any]]:
        """Возвращает список сотрудников для выбора в диалогах"""
        try:
            employees = self.session.query(Employee).all()
            result = []
            for emp in employees:
                full_name = self._get_full_name(emp)
                result.append({
                    'id': emp.id,
                    'full_name': full_name,
                    'position': emp.position or 'Сотрудник'
                })
            return result
        except Exception as e:
            print(f"❌ Ошибка в get_employees_for_selector: {e}")
            return []

    def prepare_division_for_dialog(self, division_id: int) -> Optional[Dict[str, Any]]:
        """Подготавливает данные подразделения для диалога редактирования"""
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
    # Методы для работы с тегами
    # =========================

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """Возвращает все теги"""
        from models.tasks import Tag
        try:
            tags = self.session.query(Tag).filter(Tag.is_archived == False).order_by(Tag.name).all()
            return [self._tag_to_dict(tag) for tag in tags]
        except Exception as e:
            print(f"❌ Ошибка загрузки тегов: {e}")
            return []

    def get_tag_by_id(self, tag_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает тег по ID"""
        from models.tasks import Tag
        try:
            tag = self.session.get(Tag, tag_id)
            return self._tag_to_dict(tag) if tag and not tag.is_archived else None
        except Exception as e:
            print(f"❌ Ошибка загрузки тега {tag_id}: {e}")
            return None

    def create_tag(self, tag_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создает новый тег"""
        from models.tasks import Tag
        try:
            # Проверяем, не существует ли тег с таким именем
            existing = self.session.query(Tag).filter(Tag.name == tag_data.get('name')).first()
            if existing:
                print(f"⚠️ Тег с именем '{tag_data.get('name')}' уже существует")
                return None

            tag = Tag(
                name=tag_data.get('name'),
                color=tag_data.get('color', '#ccab6e')
            )
            self.session.add(tag)
            self.session.commit()
            self.session.refresh(tag)

            return self._tag_to_dict(tag)
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании тега: {e}")
            return None

    def update_tag(self, tag_id: int, tag_data: Dict[str, Any]) -> bool:
        """Обновляет тег"""
        from models.tasks import Tag
        try:
            tag = self.session.get(Tag, tag_id)
            if not tag or tag.is_archived:
                return False

            # Проверяем уникальность имени
            new_name = tag_data.get('name')
            if new_name and new_name != tag.name:
                existing = self.session.query(Tag).filter(Tag.name == new_name).first()
                if existing:
                    print(f"⚠️ Тег с именем '{new_name}' уже существует")
                    return False
                tag.name = new_name

            if 'color' in tag_data and tag_data['color']:
                tag.color = tag_data['color']

            tag.updated_at = datetime.now()
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении тега: {e}")
            return False

    def delete_tag(self, tag_id: int) -> bool:
        """Удаляет тег (мягкое удаление - архивирует)"""
        from models.tasks import Tag
        try:
            tag = self.session.get(Tag, tag_id)
            if tag:
                tag.is_archived = True
                tag.archived_at = datetime.now()
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при удалении тега: {e}")
            return False

    def hard_delete_tag(self, tag_id: int) -> bool:
        """Полное удаление тега из БД"""
        from models.tasks import Tag
        try:
            tag = self.session.get(Tag, tag_id)
            if tag:
                self.session.delete(tag)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при полном удалении тега: {e}")
            return False

    def get_tag_usage_count(self, tag_id: int) -> int:
        """Возвращает количество использований тега"""
        from models.tasks import TaskTag
        try:
            count = self.session.query(TaskTag).filter(TaskTag.tag_id == tag_id).count()
            return count
        except Exception as e:
            print(f"❌ Ошибка подсчета использований тега: {e}")
            return 0

    def add_tag_usage_count(self, tags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Добавляет количество использований к списку тегов"""
        result = []
        for tag in tags:
            tag_copy = tag.copy()
            tag_copy['usage_count'] = self.get_tag_usage_count(tag.get('id'))
            result.append(tag_copy)
        return result

    def _tag_to_dict(self, tag) -> Dict[str, Any]:
        """Преобразует модель тега в словарь"""
        if tag is None:
            return {}
        return {
            'id': tag.id,
            'name': tag.name,
            'color': tag.color,
            'is_archived': tag.is_archived,
            'created_at': tag.created_at.isoformat() if tag.created_at else None,
            'updated_at': tag.updated_at.isoformat() if tag.updated_at else None,
            'usage_count': 0  # Будет заполнено отдельно
        }

    # =========================
    # Методы для работы с колонками (board_columns)
    # =========================

    def get_all_template_columns(self) -> List[Dict[str, Any]]:
        """Возвращает все шаблонные колонки (без привязки к проекту)"""
        try:
            columns = self.session.query(BoardColumn).filter(
                BoardColumn.project_id == None,
                BoardColumn.is_template == True  # используем is_template вместо is_archived
            ).order_by(BoardColumn.template_order).all()  # используем template_order вместо position
            return [self._column_to_dict(col) for col in columns]
        except Exception as e:
            print(f"❌ Ошибка загрузки шаблонных колонок: {e}")
            return []

    def get_column_by_id(self, column_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает колонку по ID"""
        try:
            column = self.session.get(BoardColumn, column_id)
            return self._column_to_dict(column) if column else None  # убрали проверку is_archived
        except Exception as e:
            print(f"❌ Ошибка загрузки колонки {column_id}: {e}")
            return None

    def create_template_column(self, column_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создает шаблонную колонку"""
        try:
            # Находим максимальный template_order
            max_order = self.session.query(BoardColumn).filter(
                BoardColumn.project_id == None
            ).order_by(BoardColumn.template_order.desc()).first()
            next_order = (max_order.template_order + 1) if max_order and max_order.template_order else 0

            column = BoardColumn(
                name=column_data.get('name'),
                color=column_data.get('color', '#ffffff'),
                is_done_column=column_data.get('is_done_column', False),
                template_order=next_order,
                is_template=True,
                project_id=None
            )
            self.session.add(column)
            self.session.commit()
            self.session.refresh(column)

            return self._column_to_dict(column)
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании шаблонной колонки: {e}")
            return None

    def update_template_column(self, column_id: int, column_data: Dict[str, Any]) -> bool:
        """Обновляет шаблонную колонку"""
        try:
            column = self.session.get(BoardColumn, column_id)
            if not column or column.project_id is not None:
                return False

            if 'name' in column_data and column_data['name']:
                column.name = column_data['name']
            if 'color' in column_data and column_data['color']:
                column.color = column_data['color']
            if 'is_done_column' in column_data:
                column.is_done_column = column_data['is_done_column']

            # Убрали updated_at, его нет в таблице
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении шаблонной колонки: {e}")
            return False

    def delete_template_column(self, column_id: int) -> bool:
        """Удаляет шаблонную колонку (просто удаляем из БД, нет мягкого удаления)"""
        try:
            column = self.session.get(BoardColumn, column_id)
            if column and column.project_id is None:
                self.session.delete(column)  # прямое удаление
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при удалении шаблонной колонки: {e}")
            return False

    def hard_delete_template_column(self, column_id: int) -> bool:
        """Полное удаление шаблонной колонки"""
        return self.delete_template_column(column_id)  # просто вызываем тот же метод

    def _column_to_dict(self, column) -> Dict[str, Any]:
        """Преобразует модель колонки в словарь"""
        if column is None:
            return {}
        return {
            'id': column.id,
            'name': column.name,
            'color': column.color,
            'position': column.template_order if column.template_order else column.position,
            'is_done_column': column.is_done_column,
            'project_id': column.project_id,
            'is_template': column.is_template,
            'template_order': column.template_order,
            'created_at': column.created_at.isoformat() if column.created_at else None,
        }

    # services/employee_service.py - добавить в конец класса EmployeeService

    # =========================
    # Новые методы для работы с данными (вынесенные из UI)
    # =========================

    def load_all_data_for_settings(self) -> Dict[str, Any]:
        """
        Загружает все данные для страницы настроек
        Возвращает словарь со всеми данными
        """
        from services.column_service import ColumnService
        from services.tag_service import TagService

        column_service = ColumnService(self.tasks_session)
        tag_service = TagService(self.tasks_session)

        return {
            'employees': self.get_all_employees(),
            'departments': self.get_all_departments(),
            'divisions': self.get_all_divisions(),
            'columns': column_service.get_template_columns(),
            'tags': tag_service.get_all_tags()
        }

    def delete_employee_by_id_with_check(self, employee_id: int) -> Dict[str, Any]:
        """
        Удаляет сотрудника с проверками
        Возвращает {'success': bool, 'message': str}
        """
        try:
            # Проверяем, есть ли у сотрудника задачи
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

    def delete_department_by_id_with_options(self, department_id: int,
                                             delete_employees: bool = False,
                                             target_department_id: int = None) -> Dict[str, Any]:
        """
        Удаляет отдел с опциями
        Возвращает {'success': bool, 'message': str}
        """
        try:
            has_employees = self.has_employees_in_department(department_id)

            if has_employees and not delete_employees and not target_department_id:
                return {
                    'success': False,
                    'message': 'В отделе есть сотрудники. Выберите: переназначить их в другой отдел или удалить всех сотрудников.'
                }

            success = self.delete_department_by_id(department_id, delete_employees, target_department_id)

            if success:
                return {'success': True, 'message': 'Отдел успешно удалён'}
            else:
                return {'success': False, 'message': 'Ошибка при удалении отдела'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def delete_division_by_id_with_options(self, division_id: int,
                                           delete_departments: bool = False,
                                           target_division_id: int = None) -> Dict[str, Any]:
        """
        Удаляет подразделение с опциями
        Возвращает {'success': bool, 'message': str}
        """
        try:
            has_departments = self.has_departments_in_division(division_id)
            has_employees = self.has_employees_in_division(division_id)

            if (has_departments or has_employees) and not delete_departments and not target_division_id:
                return {
                    'success': False,
                    'message': 'В подразделении есть отделы или сотрудники. Выберите: переназначить их в другое подразделение или удалить всё каскадно.'
                }

            success = self.delete_division_by_id(division_id, delete_departments, target_division_id)

            if success:
                return {'success': True, 'message': 'Подразделение успешно удалено'}
            else:
                return {'success': False, 'message': 'Ошибка при удалении подразделения'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_departments_with_division_names(self) -> List[Dict[str, Any]]:
        """Возвращает список отделов с названиями подразделений для фильтров"""
        return self.get_all_departments()

    def get_divisions_for_filter(self) -> List[Dict[str, Any]]:
        """Возвращает список подразделений для фильтров"""
        return self.get_all_divisions()

    def update_item_color(self, item_type: str, item_id: int, new_color: str) -> bool:
        """Обновляет цвет элемента (тега или колонки)"""
        from services.column_service import ColumnService
        from services.tag_service import TagService

        try:
            if item_type == 'tag':
                tag_service = TagService(self.tasks_session)
                return tag_service.update_tag(item_id, {'color': new_color})
            elif item_type == 'column':
                column_service = ColumnService(self.tasks_session)
                return column_service.update_template_column(item_id, {'color': new_color})
            else:
                return False
        except Exception as e:
            print(f"❌ Ошибка обновления цвета {item_type}: {e}")
            return False

    def filter_employees_by_department(self, employees: List[Dict], department_id: int) -> List[Dict]:
        """Фильтрует сотрудников по отделу"""
        if not department_id:
            return employees
        return [e for e in employees if e.get('department_id') == department_id]

    def filter_employees_by_division(self, employees: List[Dict], division_id: int) -> List[Dict]:
        """Фильтрует сотрудников по подразделению"""
        if not division_id:
            return employees
        return [e for e in employees if e.get('division_id') == division_id]

    def filter_departments_by_division(self, departments: List[Dict], division_id: int) -> List[Dict]:
        """Фильтрует отделы по подразделению"""
        if not division_id:
            return departments
        return [d for d in departments if d.get('division_id') == division_id]

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