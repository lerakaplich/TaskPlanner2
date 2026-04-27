# ===================================================================
# ФАЙЛ: windows/login/login_window.py
# PyQt6 — ПРЕМИУМ-СТРАНИЦА АВТОРИЗАЦИИ TaskPlanner
# ===================================================================

import sys
import json
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QDialog, QMessageBox, QGraphicsDropShadowEffect, QLineEdit, QPushButton, QApplication
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QIcon, QColor

# Импортируем для проверки пароля
try:
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    HAS_PASSLIB = True
except ImportError:
    HAS_PASSLIB = False
    import hashlib

    print("⚠️ passlib не установлен, используется простой хеш")


class LoginWindow(QDialog):
    def __init__(self, parent=None, auth_service=None):
        super().__init__(parent)

        self.auth_service = auth_service
        self.project_root = Path(__file__).parent.parent.parent

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
        self.create_eye_button()
        self.load_side_images()

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

    def create_eye_button(self):
        """Создание кнопки-глаза"""
        self.togglePasswordBtn = QPushButton(self.passwordInput)
        self.togglePasswordBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.togglePasswordBtn.setFixedSize(28, 28)
        self.togglePasswordBtn.setStyleSheet("background: transparent; border: none;")

        # Загружаем иконки
        images_dir = self.project_root / "images"
        if (images_dir / "eye_closed.png").exists():
            self.eye_closed_icon = QIcon(str(images_dir / "eye_closed.png"))
            self.togglePasswordBtn.setIcon(self.eye_closed_icon)
            self.togglePasswordBtn.setIconSize(QSize(28, 28))

        if (images_dir / "eye_open.png").exists():
            self.eye_open_icon = QIcon(str(images_dir / "eye_open.png"))

        self.togglePasswordBtn.clicked.connect(self.toggle_password_visibility)
        self.position_eye_button()

    def position_eye_button(self):
        """Позиционирование кнопки-глаза"""
        if hasattr(self, 'togglePasswordBtn') and self.togglePasswordBtn:
            try:
                rect = self.passwordInput.rect()
                x = rect.width() - 50
                y = (rect.height() - self.togglePasswordBtn.height()) // 2
                self.togglePasswordBtn.move(x, y)
                self.togglePasswordBtn.raise_()
            except:
                pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_eye_button()

    def toggle_password_visibility(self):
        """Переключение видимости пароля"""
        if self.passwordInput.echoMode() == QLineEdit.EchoMode.Password:
            self.passwordInput.setEchoMode(QLineEdit.EchoMode.Normal)
            if hasattr(self, 'eye_open_icon'):
                self.togglePasswordBtn.setIcon(self.eye_open_icon)
        else:
            self.passwordInput.setEchoMode(QLineEdit.EchoMode.Password)
            if hasattr(self, 'eye_closed_icon'):
                self.togglePasswordBtn.setIcon(self.eye_closed_icon)

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

    def on_login_clicked(self):
        phone = self.phoneInput.text().strip()
        password = self.passwordInput.text().strip()
        empty_mask = "+375 (  )   -  -"

        if not phone or phone == empty_mask:
            QMessageBox.warning(self, "Ошибка", "Введите номер телефона")
            return

        if not password:
            QMessageBox.warning(self, "Ошибка", "Введите пароль")
            return

        clean_phone = self.extract_phone_digits(phone)

        if len(clean_phone) != 12 or not clean_phone.startswith('375'):
            QMessageBox.warning(self, "Ошибка",
                                "Неверный формат номера телефона.\nНомер должен начинаться с +375 и содержать 12 цифр.")
            return

        try:
            from database import get_tasks_session
            from models.employees import ExternalEmployee
            from sqlalchemy import select

            session = get_tasks_session()

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

            session.close()

            if user:
                user_id = user.id

                # Проверяем пароль
                if user.password_hash:
                    if HAS_PASSLIB:
                        if not pwd_context.verify(password, user.password_hash):
                            QMessageBox.warning(self, "Ошибка", "Неверный пароль")
                            return
                    else:
                        # Простая проверка для теста
                        if hashlib.sha256(password.encode()).hexdigest() != user.password_hash:
                            QMessageBox.warning(self, "Ошибка", "Неверный пароль")
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
                        return

                self.set_authenticated_user({
                    'id': user_id,
                    'last_name': user.last_name,
                    'first_name': user.first_name,
                    'middle_name': user.middle_name,
                    'rights': user.rights,
                    'position': user.position,
                    'phone_number': user.phone_number,
                    'email': user.email
                })

                if self.rememberCheckbox.isChecked():
                    self.save_credentials(clean_phone, password)
                else:
                    self.clear_saved_credentials()

                self.accept()
            else:
                QMessageBox.warning(self, "Ошибка",
                                    f"Пользователь с номером {self.format_phone_for_display(clean_phone)} не найден")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при подключении к базе данных: {e}")

    def save_credentials(self, phone, password):
        """Сохраняет учетные данные"""
        try:
            config_dir = Path.home() / ".taskplanner"
            config_dir.mkdir(exist_ok=True)
            config_file = config_dir / "auth_config.json"
            data = {"phone": phone, "password": password, "remember": True}
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Ошибка сохранения учетных данных: {e}")

    def load_saved_credentials(self):
        """Загружает сохраненные учетные данные"""
        try:
            config_file = Path.home() / ".taskplanner" / "auth_config.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get("remember"):
                    phone = data.get("phone", "")
                    if phone and len(phone) == 12 and phone.startswith('375'):
                        formatted = self.format_phone_for_display(phone)
                        self.phoneInput.setText(formatted)
                        self.passwordInput.setText(data.get("password", ""))
                        self.rememberCheckbox.setChecked(True)
        except Exception as e:
            print(f"Ошибка загрузки учетных данных: {e}")

    def clear_saved_credentials(self):
        """Удаляет сохраненные учетные данные"""
        try:
            config_file = Path.home() / ".taskplanner" / "auth_config.json"
            if config_file.exists():
                config_file.unlink()
        except Exception as e:
            print(f"Ошибка удаления учетных данных: {e}")

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
            from services.employee_service import EmployeeService

            # Получаем сессию
            session = get_tasks_session()

            # Создаем EmployeeService
            employee_service = EmployeeService(session)

            # Открываем диалог добавления сотрудника (без данных - режим создания)
            dialog = EmployeeDialog(parent=self, employee_data=None, session=session)

            # Обработчик сохранения
            def on_employee_saved(employee_data):
                try:
                    # Сохраняем в БД
                    new_employee = employee_service.create_employee_in_db(employee_data)
                    if new_employee:
                        QMessageBox.information(
                            self,
                            "Заявка отправлена",
                            f"Ваша заявка на регистрацию отправлена администратору.\n"
                            f"После одобрения вы получите пароль для входа."
                        )
                    else:
                        QMessageBox.warning(self, "Ошибка", "Не удалось сохранить данные")
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {e}")

            dialog.employee_saved.connect(on_employee_saved)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть форму регистрации: {e}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            self.on_login_clicked()
        else:
            super().keyPressEvent(event)