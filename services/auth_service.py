# services/auth_service.py

import hashlib
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy import select, update

from database import get_employees_session, get_tasks_session
from models.employees import Employee, EmployeeData


def hash_password(password: str) -> str:
    """Хеширование пароля SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    if not hashed_password:
        return False
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


class AuthService:
    """Сервис аутентификации пользователей"""

    def __init__(self):
        self._current_user = None

    def get_current_user(self) -> Optional[Dict]:
        """Возвращает текущего авторизованного пользователя"""
        return self._current_user

    def set_current_user(self, user_data: Dict):
        """Устанавливает текущего пользователя"""
        self._current_user = user_data

    def clear_current_user(self):
        """Очищает текущего пользователя"""
        self._current_user = None

    def validate_phone(self, phone: str) -> bool:
        """Проверяет формат номера телефона"""
        digits = ''.join(filter(str.isdigit, phone))
        return len(digits) == 12 and digits.startswith('375')

    def extract_phone_digits(self, phone: str) -> str:
        """Извлекает только цифры из номера телефона"""
        return ''.join(filter(str.isdigit, phone))

    def format_phone_for_display(self, phone_digits: str) -> str:
        """Форматирует номер телефона для отображения"""
        if len(phone_digits) == 12 and phone_digits.startswith('375'):
            return f"+{phone_digits[0:3]} ({phone_digits[3:5]}) {phone_digits[5:8]}-{phone_digits[8:10]}-{phone_digits[10:12]}"
        return phone_digits

    def authenticate(self, phone: str, password: str) -> Optional[Dict]:
        """
        Аутентифицирует пользователя.
        Возвращает данные пользователя или None.
        """
        clean_phone = self.extract_phone_digits(phone)

        if len(clean_phone) != 12 or not clean_phone.startswith('375'):
            return None

        emp_session = get_employees_session()
        if emp_session is None:
            return None

        try:
            # Поиск сотрудника по телефону
            stmt = select(Employee).where(Employee.phone_number == clean_phone)
            user = emp_session.scalar(stmt)

            if not user:
                # Пробуем другие форматы
                if clean_phone.startswith('375'):
                    alt_phone = '8' + clean_phone[3:]
                    stmt = select(Employee).where(Employee.phone_number == alt_phone)
                    user = emp_session.scalar(stmt)

                if not user:
                    plus_phone = '+' + clean_phone
                    stmt = select(Employee).where(Employee.phone_number == plus_phone)
                    user = emp_session.scalar(stmt)

            if not user:
                return None

            user_id = user.id
            role = 'user'

            # Проверка пароля через EmployeeData
            tasks_session = get_tasks_session()
            if tasks_session:
                try:
                    employee_data = tasks_session.query(EmployeeData).filter(
                        EmployeeData.employee_id == user_id
                    ).first()

                    if employee_data and employee_data.password_hash:
                        if not verify_password(password, employee_data.password_hash):
                            return None

                    role = employee_data.role.value if employee_data and employee_data.role else 'user'

                except Exception as e:
                    print(f"⚠️ Ошибка получения EmployeeData: {e}")
                finally:
                    tasks_session.close()

            return {
                'id': user_id,
                'last_name': user.last_name,
                'first_name': user.first_name,
                'middle_name': user.middle_name,
                'rights': role,
                'position': user.position,
                'phone_number': user.phone_number,
                'email': user.email
            }

        except Exception as e:
            print(f"❌ Ошибка аутентификации: {e}")
            return None
        finally:
            emp_session.close()

    def save_session(self, user_data: Dict) -> bool:
        """
        Сохраняет сессию для автологина (локально и в БД)
        Возвращает True при успехе
        """
        try:
            session_token = secrets.token_hex(32)

            # Локальное сохранение
            config_dir = Path.home() / ".taskplanner"
            config_dir.mkdir(exist_ok=True)
            session_path = config_dir / "session.json"

            data_to_save = {
                "user_id": int(user_data.get("id")),
                "phone_number": str(user_data.get("phone_number")),
                "session_token": session_token,
                "last_name": str(user_data.get("last_name")),
                "first_name": str(user_data.get("first_name")),
                "middle_name": str(user_data.get("middle_name") or ""),
                "rights": str(user_data.get("rights")),
                "position": str(user_data.get("position") or ""),
                "email": str(user_data.get("email") or "")
            }

            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)

            # Сохранение в БД
            tasks_session = get_tasks_session()
            if tasks_session:
                try:
                    stmt = update(EmployeeData).where(
                        EmployeeData.employee_id == user_data.get('id')
                    ).values(app_session_token=session_token, updated_at=datetime.now())
                    tasks_session.execute(stmt)
                    tasks_session.commit()
                except Exception as db_err:
                    print(f"❌ Ошибка сохранения токена в БД: {db_err}")
                    tasks_session.rollback()
                finally:
                    tasks_session.close()

            print(f"✅ Сессия сохранена")
            return True

        except Exception as e:
            print(f"❌ Ошибка сохранения сессии: {e}")
            return False

    def load_session(self) -> Optional[Dict]:
        """
        Загружает сохраненную сессию и проверяет валидность токена
        Возвращает данные пользователя или None
        """
        try:
            config_dir = Path.home() / ".taskplanner"
            session_path = config_dir / "session.json"

            if not session_path.exists():
                return None

            with open(session_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not data.get("user_id") or not data.get("phone_number"):
                return None

            session_token = data.get("session_token")

            # Проверка токена в БД
            tasks_session = get_tasks_session()
            if not tasks_session:
                return None

            try:
                stmt = select(EmployeeData.employee_id).where(
                    EmployeeData.employee_id == data.get("user_id"),
                    EmployeeData.app_session_token == session_token
                )
                employee_id = tasks_session.scalar(stmt)

                if not employee_id:
                    print("❌ Токен сессии недействителен")
                    session_path.unlink()
                    return None

                # Получение данных сотрудника
                emp_session = get_employees_session()
                if not emp_session:
                    return None

                user = emp_session.get(Employee, employee_id)
                if not user:
                    session_path.unlink()
                    return None

                # Получение роли
                role_stmt = select(EmployeeData.role).where(EmployeeData.employee_id == employee_id)
                role = tasks_session.scalar(role_stmt)

                user_data = {
                    'id': user.id,
                    'last_name': user.last_name,
                    'first_name': user.first_name,
                    'middle_name': user.middle_name or '',
                    'position': user.position or '',
                    'phone_number': user.phone_number,
                    'email': user.email or '',
                    'rights': role.value if role else 'user'
                }

                emp_session.close()
                print(f"✅ Восстановлена сессия для пользователя {user.last_name}")
                return user_data

            except Exception as e:
                print(f"❌ Ошибка проверки токена: {e}")
                return None
            finally:
                tasks_session.close()

        except Exception as e:
            print(f"❌ Ошибка загрузки сессии: {e}")
            return None

    def clear_session(self, user_id: Optional[int] = None) -> bool:
        """
        Удаляет сохраненную сессию
        Если передан user_id, удаляет токен из БД для этого пользователя
        """
        try:
            # Удаление локального файла
            config_dir = Path.home() / ".taskplanner"
            session_path = config_dir / "session.json"
            if session_path.exists():
                session_path.unlink()
                print("✅ Локальная сессия очищена")

            # Удаление токена из БД
            if user_id:
                tasks_session = get_tasks_session()
                if tasks_session:
                    try:
                        stmt = update(EmployeeData).where(
                            EmployeeData.employee_id == user_id
                        ).values(app_session_token=None, updated_at=datetime.now())
                        tasks_session.execute(stmt)
                        tasks_session.commit()
                        print(f"✅ Токен сессии удален из БД для пользователя {user_id}")
                    except Exception as db_err:
                        print(f"❌ Ошибка удаления токена из БД: {db_err}")
                        tasks_session.rollback()
                    finally:
                        tasks_session.close()

            return True

        except Exception as e:
            print(f"❌ Ошибка удаления сессии: {e}")
            return False

    def is_authenticated(self) -> bool:
        """Проверяет, есть ли авторизованный пользователь"""
        return self._current_user is not None

    def has_permission(self, required_role: str) -> bool:
        """Проверяет права пользователя"""
        if not self._current_user:
            return False
        user_role = self._current_user.get('rights', 'user')
        if required_role == 'admin':
            return user_role in ['admin', 'superadmin']
        if required_role == 'superadmin':
            return user_role == 'superadmin'
        return True