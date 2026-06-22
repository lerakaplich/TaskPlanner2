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
    """Сервис аутентификации пользователей - ВСЯ ЛОГИКА ЗДЕСЬ"""

    def __init__(self):
        self._current_user = None

    # ==========================================================
    # УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЕМ
    # ==========================================================

    def get_current_user(self) -> Optional[Dict]:
        return self._current_user

    def set_current_user(self, user_data: Dict):
        self._current_user = user_data

    def clear_current_user(self):
        self._current_user = None

    def is_authenticated(self) -> bool:
        return self._current_user is not None

    def has_permission(self, required_role: str) -> bool:
        if not self._current_user:
            return False
        user_role = self._current_user.get('rights', 'user')
        if required_role == 'admin':
            return user_role in ['admin', 'superadmin']
        if required_role == 'superadmin':
            return user_role == 'superadmin'
        return True

    # ==========================================================
    # ВАЛИДАЦИЯ ТЕЛЕФОНА
    # ==========================================================

    def validate_phone(self, phone: str) -> bool:
        """Проверяет формат номера телефона"""
        digits = self.extract_phone_digits(phone)
        return len(digits) == 12 and digits.startswith('375')

    def extract_phone_digits(self, phone: str) -> str:
        """Извлекает только цифры из номера телефона"""
        return ''.join(filter(str.isdigit, phone))

    def format_phone_for_display(self, phone_digits: str) -> str:
        """Форматирует номер телефона для отображения"""
        if len(phone_digits) == 12 and phone_digits.startswith('375'):
            return f"+{phone_digits[0:3]} ({phone_digits[3:5]}) {phone_digits[5:8]}-{phone_digits[8:10]}-{phone_digits[10:12]}"
        return phone_digits

    # ==========================================================
    # АУТЕНТИФИКАЦИЯ
    # ==========================================================

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
            user = self._find_user_by_phone(emp_session, clean_phone)
            if not user:
                return None

            user_id = user.id

            if not self._verify_user_password(user_id, password):
                return None

            role = self._get_user_role(user_id)

            return self._build_user_data(user, role)

        except Exception as e:
            print(f"❌ Ошибка аутентификации: {e}")
            return None
        finally:
            emp_session.close()

    def _find_user_by_phone(self, session, phone: str) -> Optional[Employee]:
        """Находит пользователя по номеру телефона с разными форматами"""
        # Прямой поиск
        stmt = select(Employee).where(Employee.phone_number == phone)
        user = session.scalar(stmt)

        if not user and phone.startswith('375'):
            # Формат 8ХХХ...
            alt_phone = '8' + phone[3:]
            stmt = select(Employee).where(Employee.phone_number == alt_phone)
            user = session.scalar(stmt)

        if not user:
            # Формат +375...
            plus_phone = '+' + phone
            stmt = select(Employee).where(Employee.phone_number == plus_phone)
            user = session.scalar(stmt)

        return user

    def _verify_user_password(self, user_id: int, password: str) -> bool:
        """Проверяет пароль пользователя"""
        tasks_session = get_tasks_session()
        if not tasks_session:
            return False

        try:
            employee_data = tasks_session.query(EmployeeData).filter(
                EmployeeData.employee_id == user_id
            ).first()

            if not employee_data or not employee_data.password_hash:
                return False

            return verify_password(password, employee_data.password_hash)

        except Exception as e:
            print(f"⚠️ Ошибка проверки пароля: {e}")
            return False
        finally:
            tasks_session.close()

    def _get_user_role(self, user_id: int) -> str:
        """Получает роль пользователя"""
        tasks_session = get_tasks_session()
        if not tasks_session:
            return 'user'

        try:
            stmt = select(EmployeeData.role).where(EmployeeData.employee_id == user_id)
            role = tasks_session.scalar(stmt)
            return role.value if role else 'user'
        except Exception as e:
            print(f"⚠️ Ошибка получения роли: {e}")
            return 'user'
        finally:
            tasks_session.close()

    def _build_user_data(self, user: Employee, role: str) -> Dict:
        """Собирает данные пользователя"""
        return {
            'id': user.id,
            'last_name': user.last_name,
            'first_name': user.first_name,
            'middle_name': user.middle_name or '',
            'rights': role,
            'position': user.position or '',
            'phone_number': user.phone_number,
            'email': user.email or ''
        }

    # ==========================================================
    # УПРАВЛЕНИЕ СЕССИЕЙ
    # ==========================================================

    def save_session(self, user_data: Dict) -> bool:
        """Сохраняет сессию для автологина"""
        try:
            session_token = secrets.token_hex(32)

            # Локальное сохранение
            if not self._save_local_session(user_data, session_token):
                return False

            # Сохранение в БД
            if not self._save_session_token(user_data.get('id'), session_token):
                return False

            print(f"✅ Сессия сохранена")
            return True

        except Exception as e:
            print(f"❌ Ошибка сохранения сессии: {e}")
            return False

    def _save_local_session(self, user_data: Dict, session_token: str) -> bool:
        """Сохраняет сессию локально"""
        try:
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

            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения локальной сессии: {e}")
            return False

    def _save_session_token(self, user_id: int, session_token: str) -> bool:
        """Сохраняет токен сессии в БД"""
        tasks_session = get_tasks_session()
        if not tasks_session:
            return False

        try:
            stmt = update(EmployeeData).where(
                EmployeeData.employee_id == user_id
            ).values(app_session_token=session_token, updated_at=datetime.now())
            tasks_session.execute(stmt)
            tasks_session.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения токена в БД: {e}")
            tasks_session.rollback()
            return False
        finally:
            tasks_session.close()

    def load_session(self) -> Optional[Dict]:
        """Загружает сохраненную сессию"""
        try:
            session_data = self._load_local_session()
            if not session_data:
                return None

            if not self._verify_session_token(session_data):
                return None

            user_data = self._get_user_data_by_id(session_data.get("user_id"))
            if user_data:
                print(f"✅ Восстановлена сессия для пользователя {user_data.get('last_name')}")
                return user_data

            return None

        except Exception as e:
            print(f"❌ Ошибка загрузки сессии: {e}")
            return None

    def _load_local_session(self) -> Optional[Dict]:
        """Загружает локальную сессию"""
        try:
            config_dir = Path.home() / ".taskplanner"
            session_path = config_dir / "session.json"

            if not session_path.exists():
                return None

            with open(session_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not data.get("user_id") or not data.get("phone_number"):
                return None

            return data

        except Exception as e:
            print(f"❌ Ошибка загрузки локальной сессии: {e}")
            return None

    def _verify_session_token(self, session_data: Dict) -> bool:
        """Проверяет валидность токена сессии"""
        tasks_session = get_tasks_session()
        if not tasks_session:
            return False

        try:
            stmt = select(EmployeeData.employee_id).where(
                EmployeeData.employee_id == session_data.get("user_id"),
                EmployeeData.app_session_token == session_data.get("session_token")
            )
            employee_id = tasks_session.scalar(stmt)

            if not employee_id:
                print("❌ Токен сессии недействителен")
                self._delete_local_session()
                return False

            return True

        except Exception as e:
            print(f"❌ Ошибка проверки токена: {e}")
            return False
        finally:
            tasks_session.close()

    def _get_user_data_by_id(self, user_id: int) -> Optional[Dict]:
        """Получает данные пользователя по ID"""
        emp_session = get_employees_session()
        if not emp_session:
            return None

        try:
            user = emp_session.get(Employee, user_id)
            if not user:
                return None

            role = self._get_user_role(user_id)

            return self._build_user_data(user, role)

        except Exception as e:
            print(f"❌ Ошибка получения данных пользователя: {e}")
            return None
        finally:
            emp_session.close()

    def _delete_local_session(self) -> bool:
        """Удаляет локальный файл сессии"""
        try:
            config_dir = Path.home() / ".taskplanner"
            session_path = config_dir / "session.json"
            if session_path.exists():
                session_path.unlink()
                print("✅ Локальная сессия очищена")
            return True
        except Exception as e:
            print(f"❌ Ошибка удаления локальной сессии: {e}")
            return False

    def clear_session(self, user_id: Optional[int] = None) -> bool:
        """Удаляет сохраненную сессию"""
        try:
            self._delete_local_session()

            if user_id:
                self._delete_session_token(user_id)

            return True

        except Exception as e:
            print(f"❌ Ошибка удаления сессии: {e}")
            return False

    def _delete_session_token(self, user_id: int) -> bool:
        """Удаляет токен сессии из БД"""
        tasks_session = get_tasks_session()
        if not tasks_session:
            return False

        try:
            stmt = update(EmployeeData).where(
                EmployeeData.employee_id == user_id
            ).values(app_session_token=None, updated_at=datetime.now())
            tasks_session.execute(stmt)
            tasks_session.commit()
            print(f"✅ Токен сессии удален из БД для пользователя {user_id}")
            return True
        except Exception as e:
            print(f"❌ Ошибка удаления токена из БД: {e}")
            tasks_session.rollback()
            return False
        finally:
            tasks_session.close()

    # ==========================================================
    # РЕГИСТРАЦИЯ
    # ==========================================================

    def send_registration_request(self, employee_data: Dict) -> bool:
        """Отправляет запрос на регистрацию через сокет"""
        try:
            from utils.socket_manager import get_socket_client

            socket_client = get_socket_client()

            if not socket_client.is_connected():
                return False

            from datetime import date
            data_for_send = {}
            for key, value in employee_data.items():
                if isinstance(value, date):
                    data_for_send[key] = value.isoformat()
                else:
                    data_for_send[key] = value

            socket_client.request_registration(data_for_send)
            return True

        except Exception as e:
            print(f"❌ Ошибка отправки запроса на регистрацию: {e}")
            return False

    def get_registration_success_message(self, employee_data: Dict) -> str:
        """Возвращает сообщение об успешной отправке заявки"""
        full_name = f"{employee_data.get('last_name')} {employee_data.get('first_name')}"
        if employee_data.get('middle_name'):
            full_name += f" {employee_data.get('middle_name')}"

        return (
            f"✅ Ваша заявка на регистрацию отправлена!\n\n"
            f"📋 ФИО: {full_name}\n"
            f"📞 Телефон: {employee_data.get('phone_number')}\n\n"
            f"Для получения пароля:\n"
            f"1. Перейдите в Telegram бота\n"
            f"2. Нажмите /start\n"
            f"3. Отправьте ваш номер телефона\n"
            f"4. После одобрения вы получите пароль\n\n"
            f"Обычно это занимает несколько минут."
        )

    def get_forgot_password_message(self) -> str:
        """Возвращает сообщение для восстановления пароля"""
        return (
            "🔐 Восстановление пароля\n\n"
            "Для сброса пароля:\n\n"
            "1. Перейдите в Telegram бота\n"
            "2. Отправьте команду /reset_password\n"
            "3. Следуйте инструкциям бота\n\n"
            "Важно: Новый пароль будет отправлен в Telegram.\n\n"
            "Если у вас нет Telegram, обратитесь к администратору."
        )

    def get_bot_link(self) -> str:
        """Возвращает ссылку на Telegram бота"""
        return "https://t.me/TaskPlanner2035Vikusik_bot"