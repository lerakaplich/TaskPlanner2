# ===================================================================
# ФАЙЛ: windows/login/login_window.py
# ===================================================================

import sys
import json
from pathlib import Path
from datetime import date

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QDialog, QMessageBox, QGraphicsDropShadowEffect, QLineEdit, QPushButton, QApplication
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QColor, QAction

# Убираем passlib, используем только hashlib
import hashlib
import secrets


def hash_password(password: str) -> str:
    """Хеширование пароля SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    if not hashed_password:
        return False
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


class LoginWindow(QDialog):
    login_success = pyqtSignal(dict)

    def __init__(self, parent=None, auth_service=None):
        super().__init__(parent)

        self.auth_service = auth_service
        self.project_root = Path(__file__).parent.parent.parent
        self._login_in_progress = False

        # Загружаем UI
        ui_path = self.project_root / "ui" / "login" / "login_window.ui"
        if not ui_path.exists():
            raise FileNotFoundError(f"Файл интерфейса не найден: {ui_path}")

        uic.loadUi(str(ui_path), self)

        self.showMaximized()

        # Настройка
        self.setup_ui()
        self.setup_signals()
        self.load_saved_credentials()
        self.load_side_images()

        # Настройка "глазика" для пароля
        self.setup_password_eye()

    def setup_password_eye(self):
        """Настройка кнопки показа/скрытия пароля через QAction"""
        # Создаем действие (иконку) внутри поля
        self.toggle_password_action = QAction(self.passwordInput)
        self.password_visible = False
        self.update_eye_icon(False)

        self.passwordInput.addAction(
            self.toggle_password_action,
            QLineEdit.ActionPosition.TrailingPosition
        )

        self.toggle_password_action.triggered.connect(self.toggle_password_visibility_new)

        # Убираем старую кнопку, если она была создана
        if hasattr(self, 'togglePasswordBtn'):
            self.togglePasswordBtn.deleteLater()

    def update_eye_icon(self, visible):
        """Обновляет иконку глаза в зависимости от состояния"""
        images_dir = self.project_root / "images"
        icon_name = "eye_open.png" if visible else "eye_closed.png"
        icon_path = images_dir / icon_name

        if icon_path.exists():
            self.toggle_password_action.setIcon(QIcon(str(icon_path)))
        else:
            self.toggle_password_action.setText("👁" if visible else "👁‍🗨")

    def toggle_password_visibility_new(self):
        """Переключение видимости пароля (новая версия)"""
        self.password_visible = not self.password_visible
        mode = QLineEdit.EchoMode.Normal if self.password_visible else QLineEdit.EchoMode.Password
        self.passwordInput.setEchoMode(mode)
        self.update_eye_icon(self.password_visible)

    def get_authenticated_user(self):
        """Возвращает данные авторизованного пользователя"""
        return getattr(self, '_authenticated_user', None)

    def set_authenticated_user(self, user_data):
        """Устанавливает данные авторизованного пользователя"""
        self._authenticated_user = user_data

    def setup_ui(self):
        """Настройка UI элементов"""
        # Тень для карточки
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(50)
        shadow.setXOffset(0)
        shadow.setYOffset(20)
        shadow.setColor(QColor(210, 39, 48, 100))
        self.authFrame.setGraphicsEffect(shadow)

        # Тень для логотипа
        logo_shadow = QGraphicsDropShadowEffect()
        logo_shadow.setBlurRadius(35)
        logo_shadow.setXOffset(0)
        logo_shadow.setYOffset(8)
        logo_shadow.setColor(QColor(0, 0, 0, 40))
        self.logoLabel.setGraphicsEffect(logo_shadow)

        # Логотип компании
        logo_path = self.project_root / "images" / "logo.png"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                self.logoLabel.setPixmap(scaled)
                self.logoLabel.setStyleSheet("background: transparent;")

        # НАСТРОЙКА ПОЛЯ ТЕЛЕФОНА С МАСКОЙ
        self.phoneInput.setInputMask("+375 (99) 999-99-99")
        self.phoneInput.setText("")
        self.phoneInput.setPlaceholderText("+375 (XX) XXX-XX-XX")

        self.rememberCheckbox.setChecked(False)

        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )

    def load_side_images(self):
        """Загрузка боковых изображений"""
        images_dir = self.project_root / "images"

        # Загрузка checkbox - 150x150
        checkbox_path = images_dir / "checkbox.png"
        if checkbox_path.exists():
            pixmap = QPixmap(str(checkbox_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                self.checkboxImageLabel.setPixmap(scaled)
                self.checkboxImageLabel.setScaledContents(False)

        # Загрузка QR - 250x250
        qr_path = images_dir / "qr.jpg"
        if qr_path.exists():
            pixmap = QPixmap(str(qr_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                self.qrImageLabel.setPixmap(scaled)
                self.qrImageLabel.setScaledContents(False)

        # Загрузка часов - 150x150
        clock_path = images_dir / "clock.png"
        if clock_path.exists():
            pixmap = QPixmap(str(clock_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                self.clockImageLabel.setPixmap(scaled)
                self.clockImageLabel.setScaledContents(False)

        # Загрузка шестеренки - 150x150
        gear_path = images_dir / "gear.png"
        if gear_path.exists():
            pixmap = QPixmap(str(gear_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                self.gearImageLabel.setPixmap(scaled)
                self.gearImageLabel.setScaledContents(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def toggle_password_visibility(self):
        """Старый метод - оставлен для совместимости"""
        self.toggle_password_visibility_new()

    def setup_signals(self):
        """Настройка сигналов"""
        self.loginBtn.clicked.connect(self.on_login_clicked)
        self.forgotPasswordBtn.clicked.connect(self.on_forgot_clicked)
        self.requestBtn.clicked.connect(self.on_request_clicked)
        self.phoneInput.returnPressed.connect(self.on_login_clicked)
        self.passwordInput.returnPressed.connect(self.on_login_clicked)

    def validate_phone(self, phone):
        """Проверка, что номер телефона имеет правильный формат (375xxxxxxxxx)"""
        digits = ''.join(filter(str.isdigit, phone))
        return len(digits) == 12 and digits.startswith('375')

    def extract_phone_digits(self, phone):
        """Извлекает только цифры из номера телефона"""
        return ''.join(filter(str.isdigit, phone))

    def format_phone_for_display(self, phone_digits):
        """Форматирует номер телефона для отображения в поле ввода"""
        if len(phone_digits) == 12 and phone_digits.startswith('375'):
            return f"+{phone_digits[0:3]} ({phone_digits[3:5]}) {phone_digits[5:8]}-{phone_digits[8:10]}-{phone_digits[10:12]}"
        return phone_digits

    def save_session(self, user_data):
        """Сохраняет сессию для автологина (локально и в БД)"""
        try:
            # Генерируем уникальный токен сессии
            session_token = secrets.token_hex(32)

            # 1. Сохраняем локально
            config_dir = Path.home() / ".taskplanner"
            config_dir.mkdir(exist_ok=True)
            session_path = config_dir / "session.json"

            data_to_save = {
                "user_id": int(user_data.get("id")),
                "phone_number": str(user_data.get("phone_number")),
                "session_token": session_token,  # Сохраняем токен
                "last_name": str(user_data.get("last_name")),
                "first_name": str(user_data.get("first_name")),
                "middle_name": str(user_data.get("middle_name") or ""),
                "rights": str(user_data.get("rights")),
                "position": str(user_data.get("position") or ""),
                "email": str(user_data.get("email") or "")
            }

            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)

            # 2. Сохраняем токен в БД
            from database import get_tasks_session
            from models.employees import ExternalEmployee
            from sqlalchemy import update

            db_session = get_tasks_session()
            try:
                stmt = update(ExternalEmployee).where(
                    ExternalEmployee.id == user_data.get('id')
                ).values(app_session_token=session_token)
                db_session.execute(stmt)
                db_session.commit()
                print(f"✅ Токен сессии сохранен в БД для пользователя {user_data.get('id')}")
            except Exception as db_err:
                print(f"❌ Ошибка сохранения токена в БД: {db_err}")
                db_session.rollback()
            finally:
                db_session.close()

            print(f"✅ Сессия сохранена локально: {session_path}")

        except Exception as e:
            print(f"❌ Ошибка сохранения сессии: {e}")

    def clear_session(self):
        """Удаляет сохраненную сессию (локально и в БД)"""
        try:
            # 1. Удаляем локальный файл
            config_dir = Path.home() / ".taskplanner"
            session_path = config_dir / "session.json"
            if session_path.exists():
                session_path.unlink()
                print("✅ Локальная сессия очищена")

            # 2. Удаляем токен из БД для текущего пользователя
            if hasattr(self, '_authenticated_user') and self._authenticated_user:
                from database import get_tasks_session
                from models.employees import ExternalEmployee
                from sqlalchemy import update

                db_session = get_tasks_session()
                try:
                    stmt = update(ExternalEmployee).where(
                        ExternalEmployee.id == self._authenticated_user.get('id')
                    ).values(app_session_token=None)
                    db_session.execute(stmt)
                    db_session.commit()
                    print(f"✅ Токен сессии удален из БД для пользователя {self._authenticated_user.get('id')}")
                except Exception as db_err:
                    print(f"❌ Ошибка удаления токена из БД: {db_err}")
                    db_session.rollback()
                finally:
                    db_session.close()

        except Exception as e:
            print(f"❌ Ошибка удаления сессии: {e}")

    def load_saved_credentials(self):
        """Загружает сохраненные учетные данные и выполняет автовход с проверкой токена в БД"""
        try:
            config_dir = Path.home() / ".taskplanner"
            session_path = config_dir / "session.json"

            if session_path.exists():
                with open(session_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Если есть сохраненная сессия
                if data.get("user_id") and data.get("phone_number"):
                    session_token = data.get("session_token")

                    # Проверяем токен в БД
                    from database import get_tasks_session
                    from models.employees import ExternalEmployee
                    from sqlalchemy import select

                    db_session = get_tasks_session()
                    try:
                        stmt = select(ExternalEmployee).where(
                            ExternalEmployee.id == data.get("user_id"),
                            ExternalEmployee.app_session_token == session_token
                        )
                        user = db_session.scalar(stmt)

                        if user:
                            print(f"✅ Найдена валидная сессия для пользователя {data.get('phone_number')}")

                            # Восстанавливаем данные пользователя
                            user_data = {
                                'id': user.id,
                                'last_name': user.last_name,
                                'first_name': user.first_name,
                                'middle_name': user.middle_name or '',
                                'rights': user.rights,
                                'position': user.position or '',
                                'phone_number': user.phone_number,
                                'email': user.email or ''
                            }

                            self.set_authenticated_user(user_data)

                            # Отправляем сигнал об успешном входе
                            self.login_success.emit(user_data)

                            # Небольшая задержка для обработки сигнала
                            QTimer.singleShot(100, self.accept)
                            return True
                        else:
                            print(f"❌ Токен сессии недействителен, требуется повторный вход")
                            # Удаляем невалидную сессию
                            session_path.unlink()

                    except Exception as db_err:
                        print(f"❌ Ошибка проверки токена в БД: {db_err}")
                    finally:
                        db_session.close()

        except Exception as e:
            print(f"❌ Ошибка загрузки сессии: {e}")

        return False

    def save_credentials(self, phone, password):
        """Сохраняет учетные данные (если включено запоминание)"""
        try:
            config_dir = Path.home() / ".taskplanner"
            config_dir.mkdir(exist_ok=True)
            config_file = config_dir / "auth_config.json"
            data = {"phone": phone, "password": password, "remember": True}
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            print("✅ Учетные данные сохранены")
        except Exception as e:
            print(f"❌ Ошибка сохранения учетных данных: {e}")

    def clear_saved_credentials(self):
        """Удаляет сохраненные учетные данные"""
        try:
            config_dir = Path.home() / ".taskplanner"
            config_file = config_dir / "auth_config.json"
            if config_file.exists():
                config_file.unlink()
                print("✅ Учетные данные очищены")
        except Exception as e:
            print(f"❌ Ошибка удаления учетных данных: {e}")

    def on_login_clicked(self):
        # Защита от двойного клика
        if self._login_in_progress:
            return

        self._login_in_progress = True

        # Получаем текст из поля с маской
        phone_with_mask = self.phoneInput.text()
        password = self.passwordInput.text().strip()

        # Проверяем, что поле не пустое (маска заполнена)
        if not phone_with_mask or phone_with_mask == "+375 (  )   -  -" or phone_with_mask.count("_") > 0:
            QMessageBox.warning(self, "Ошибка", "Введите номер телефона")
            self._login_in_progress = False
            return

        if not password:
            QMessageBox.warning(self, "Ошибка", "Введите пароль")
            self._login_in_progress = False
            return

        # Извлекаем только цифры из маски
        clean_phone = ''.join(filter(str.isdigit, phone_with_mask))

        # Проверяем, что получилось 12 цифр и начинается с 375
        if len(clean_phone) != 12 or not clean_phone.startswith('375'):
            QMessageBox.warning(self, "Ошибка",
                                "Неверный формат номера телефона.\nНомер должен содержать 12 цифр и начинаться с 375.")
            self._login_in_progress = False
            return

        try:
            from database import get_tasks_session
            from models.employees import ExternalEmployee
            from sqlalchemy import select

            session = get_tasks_session()

            # Ищем пользователя по номеру телефона
            stmt = select(ExternalEmployee).where(ExternalEmployee.phone_number == clean_phone)
            user = session.scalar(stmt)

            if not user:
                # Пробуем другие форматы
                if clean_phone.startswith('375'):
                    alt_phone = '8' + clean_phone[3:]
                    stmt = select(ExternalEmployee).where(ExternalEmployee.phone_number == alt_phone)
                    user = session.scalar(stmt)

                if not user:
                    plus_phone = '+' + clean_phone
                    stmt = select(ExternalEmployee).where(ExternalEmployee.phone_number == plus_phone)
                    user = session.scalar(stmt)

            if user:
                user_id = user.id

                # Проверяем пароль через SHA256
                if user.password_hash:
                    if not verify_password(password, user.password_hash):
                        QMessageBox.warning(self, "Ошибка", "Неверный пароль")
                        session.close()
                        self._login_in_progress = False
                        return
                else:
                    # Для старых аккаунтов без пароля - предупреждение
                    reply = QMessageBox.question(
                        self,
                        "Внимание",
                        "У вашей учетной записи нет пароля. Рекомендуем установить пароль в настройках профиля.\n\n"
                        "Продолжить вход без пароля?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        session.close()
                        self._login_in_progress = False
                        return

                user_data = {
                    'id': user_id,
                    'last_name': user.last_name,
                    'first_name': user.first_name,
                    'middle_name': user.middle_name,
                    'rights': user.rights,
                    'position': user.position,
                    'phone_number': user.phone_number,
                    'email': user.email
                }

                session.close()

                # Логика "Запомнить меня"
                if self.rememberCheckbox.isChecked():
                    self.save_session(user_data)
                else:
                    self.clear_session()

                self.set_authenticated_user(user_data)

                # Отправляем сигнал об успешном входе
                if hasattr(self, 'login_success') and self.login_success:
                    self.login_success.emit(user_data)

                self.accept()
            else:
                session.close()
                QMessageBox.warning(self, "Ошибка",
                                    f"Пользователь с номером {self.format_phone_for_display(clean_phone)} не найден")
                self._login_in_progress = False

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при подключении к базе данных: {e}")
            self._login_in_progress = False

    def on_forgot_clicked(self):
        phone = self.phoneInput.text().strip()
        empty_mask = "+375 (  )   -  -"
        if phone and phone != empty_mask:
            clean_phone = self.extract_phone_digits(phone)
            QMessageBox.information(self, "Восстановление",
                                    f"Инструкции по восстановлению пароля отправлены на номер {self.format_phone_for_display(clean_phone)}")
        else:
            QMessageBox.warning(self, "Ошибка", "Введите номер телефона")

    def on_request_clicked(self):
        """Открытие формы регистрации нового сотрудника"""
        try:
            from database import get_tasks_session
            from windows.settings.employees.employee_dialog import EmployeeDialog

            session = get_tasks_session()

            dialog = EmployeeDialog(
                parent=self,
                employee_data=None,
                session=session,
                is_registration_mode=True
            )

            def on_employee_saved(employee_data):
                try:
                    # Преобразуем дату в строку
                    employee_data_for_send = {}
                    for key, value in employee_data.items():
                        if isinstance(value, date):
                            employee_data_for_send[key] = value.isoformat()
                        else:
                            employee_data_for_send[key] = value

                    # Отправляем через сокет
                    self.send_registration_request(employee_data_for_send)
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Ошибка при отправке данных: {e}")

            dialog.employee_saved.connect(on_employee_saved)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть форму регистрации: {e}")

    def send_registration_request(self, employee_data):
        """Отправляет запрос на регистрацию через сокет и показывает окно со ссылкой"""
        try:
            from utils.socket_manager import get_socket_client

            socket_client = get_socket_client()

            if not socket_client.is_connected():
                QMessageBox.warning(
                    self,
                    "Нет подключения",
                    "Нет подключения к серверу. Попробуйте позже."
                )
                return

            # Отправляем запрос на сервер
            socket_client.request_registration(employee_data)

            # Показываем окно с ссылкой на бота
            bot_link = "https://t.me/TaskPlanner2035Vikusik_bot"

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Заявка отправлена")
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText(
                f"✅ Ваша заявка на регистрацию отправлена!\n\n"
                f"📋 ФИО: {employee_data.get('last_name')} {employee_data.get('first_name')} {employee_data.get('middle_name') or ''}\n"
                f"📞 Телефон: {employee_data.get('phone_number')}\n\n"
                f"📱 *Для получения пароля:*\n"
                f"1. Перейдите в Telegram бота:\n"
                f"   {bot_link}\n"
                f"2. Нажмите /start\n"
                f"3. Отправьте ваш номер телефона\n"
                f"4. После одобрения вы получите пароль\n\n"
                f"⏰ Обычно это занимает несколько минут."
            )

            # Добавляем кнопку для открытия ссылки
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl

            open_bot_btn = msg_box.addButton("Перейти в Telegram бота", QMessageBox.ButtonRole.ActionRole)
            open_bot_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(bot_link)))

            msg_box.addButton(QMessageBox.StandardButton.Ok)
            msg_box.exec()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось отправить заявку: {e}")

    def _prepare_data_for_json(self, data: dict) -> dict:
        """Преобразует date объекты в строки для JSON сериализации"""
        result = {}
        for key, value in data.items():
            if isinstance(value, date):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            self.on_login_clicked()
        else:
            super().keyPressEvent(event)