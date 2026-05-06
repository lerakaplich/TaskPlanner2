# windows/login/login_window.py

from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QColor, QAction
from PyQt6.QtWidgets import (
    QDialog, QMessageBox, QGraphicsDropShadowEffect, QLineEdit
)

from services.auth_service import AuthService


class LoginWindow(QDialog):
    login_success = pyqtSignal(dict)

    def __init__(self, parent=None, auth_service: AuthService = None):
        super().__init__(parent)

        self.auth_service = auth_service or AuthService()
        self.project_root = Path(__file__).parent.parent.parent
        self._login_in_progress = False

        # Загрузка UI
        ui_path = self.project_root / "ui" / "login" / "login_window.ui"
        if not ui_path.exists():
            raise FileNotFoundError(f"Файл интерфейса не найден: {ui_path}")

        uic.loadUi(str(ui_path), self)

        self.showMaximized()
        self.setup_ui()
        self.setup_signals()
        self.setup_password_eye()
        self._try_auto_login()

    # ==========================================================
    # Настройка UI
    # ==========================================================

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

        # Логотип
        logo_path = self.project_root / "images" / "logo.png"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                self.logoLabel.setPixmap(scaled)
                self.logoLabel.setStyleSheet("background: transparent;")

        # Настройка поля телефона с маской
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

        self._load_side_images()

    def _load_side_images(self):
        """Загрузка боковых изображений"""
        images_dir = self.project_root / "images"

        image_configs = [
            ("checkbox.png", self.checkboxImageLabel, 150),
            ("qr.jpg", self.qrImageLabel, 250),
            ("clock.png", self.clockImageLabel, 150),
            ("gear.png", self.gearImageLabel, 150),
        ]

        for filename, label, size in image_configs:
            path = images_dir / filename
            if path.exists():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)
                    label.setPixmap(scaled)
                    label.setScaledContents(False)

    def setup_password_eye(self):
        """Настройка кнопки показа/скрытия пароля"""
        self.toggle_password_action = QAction(self.passwordInput)
        self.password_visible = False
        self._update_eye_icon(False)

        self.passwordInput.addAction(
            self.toggle_password_action,
            QLineEdit.ActionPosition.TrailingPosition
        )
        self.toggle_password_action.triggered.connect(self._toggle_password_visibility)

        # Удаляем старую кнопку
        if hasattr(self, 'togglePasswordBtn'):
            self.togglePasswordBtn.deleteLater()

    def _update_eye_icon(self, visible: bool):
        """Обновляет иконку глаза"""
        images_dir = self.project_root / "images"
        icon_name = "eye_open.png" if visible else "eye_closed.png"
        icon_path = images_dir / icon_name

        if icon_path.exists():
            self.toggle_password_action.setIcon(QIcon(str(icon_path)))
        else:
            self.toggle_password_action.setText("👁" if visible else "👁‍🗨")

    def _toggle_password_visibility(self):
        """Переключение видимости пароля"""
        self.password_visible = not self.password_visible
        mode = QLineEdit.EchoMode.Normal if self.password_visible else QLineEdit.EchoMode.Password
        self.passwordInput.setEchoMode(mode)
        self._update_eye_icon(self.password_visible)

    def setup_signals(self):
        """Настройка сигналов"""
        self.loginBtn.clicked.connect(self._on_login_clicked)
        self.forgotPasswordBtn.clicked.connect(self._on_forgot_clicked)
        self.requestBtn.clicked.connect(self._on_request_clicked)
        self.phoneInput.returnPressed.connect(self._on_login_clicked)
        self.passwordInput.returnPressed.connect(self._on_login_clicked)

    # ==========================================================
    # Автологин
    # ==========================================================

    def _try_auto_login(self):
        """Попытка автоматического входа по сохраненной сессии"""
        user_data = self.auth_service.load_session()
        if user_data:
            self.auth_service.set_current_user(user_data)
            self.login_success.emit(user_data)
            QTimer.singleShot(100, self.accept)

    # ==========================================================
    # Обработчики действий
    # ==========================================================

    def _on_login_clicked(self):
        """Обработчик нажатия кнопки входа"""
        if self._login_in_progress:
            return

        self._login_in_progress = True

        phone = self.phoneInput.text()
        password = self.passwordInput.text().strip()

        # Валидация
        if not phone or phone == "+375 (  )   -  -" or phone.count("_") > 0:
            QMessageBox.warning(self, "Ошибка", "Введите номер телефона")
            self._login_in_progress = False
            return

        if not password:
            QMessageBox.warning(self, "Ошибка", "Введите пароль")
            self._login_in_progress = False
            return

        if not self.auth_service.validate_phone(phone):
            QMessageBox.warning(self, "Ошибка",
                                "Неверный формат номера телефона.\nНомер должен содержать 12 цифр и начинаться с 375.")
            self._login_in_progress = False
            return

        # Аутентификация
        user_data = self.auth_service.authenticate(phone, password)

        if user_data:
            self.auth_service.set_current_user(user_data)

            if self.rememberCheckbox.isChecked():
                self.auth_service.save_session(user_data)
            else:
                self.auth_service.clear_session(user_data.get('id'))

            self.login_success.emit(user_data)
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный номер телефона или пароль")
            self._login_in_progress = False

    def _on_forgot_clicked(self):
        """Обработчик кнопки 'Забыли пароль'"""
        bot_link = "https://t.me/TaskPlanner2035Vikusik_bot"

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Восстановление пароля")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText(
            f"🔐 Восстановление пароля\n\n"
            f"Для сброса пароля:\n\n"
            f"1. Перейдите в Telegram бота:\n"
            f"   {bot_link}\n"
            f"2. Отправьте команду /reset_password\n"
            f"3. Следуйте инструкциям бота\n\n"
            f"Важно: Новый пароль будет отправлен в Telegram.\n\n"
            f"Если у вас нет Telegram, обратитесь к администратору."
        )

        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl

        open_bot_btn = msg_box.addButton("Перейти в Telegram бота", QMessageBox.ButtonRole.ActionRole)
        open_bot_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(bot_link)))
        msg_box.addButton(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def _on_request_clicked(self):
        """Открытие формы регистрации нового сотрудника"""
        try:
            from database import get_tasks_session
            from windows.settings.employees.employee_dialog import EmployeeDialog
            from services.employee_service import EmployeeService  # Добавить импорт

            # Создаем сервис сотрудников вместо передачи сессии напрямую
            employee_service = EmployeeService()

            dialog = EmployeeDialog(
                parent=self,
                employee_data=None,
                employee_service=employee_service,  # ← Используем employee_service вместо session
                is_registration_mode=True
            )
            dialog.employee_saved.connect(self._send_registration_request)
            dialog.exec()

            # Закрываем сервис после использования
            employee_service.close()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть форму регистрации: {e}")

    def _send_registration_request(self, employee_data):
        """Отправляет запрос на регистрацию"""
        try:
            from utils.socket_manager import get_socket_client

            socket_client = get_socket_client()

            if not socket_client.is_connected():
                QMessageBox.warning(self, "Нет подключения", "Нет подключения к серверу. Попробуйте позже.")
                return

            # Преобразуем дату в строку
            from datetime import date
            employee_data_for_send = {}
            for key, value in employee_data.items():
                if isinstance(value, date):
                    employee_data_for_send[key] = value.isoformat()
                else:
                    employee_data_for_send[key] = value

            socket_client.request_registration(employee_data_for_send)

            # Показываем окно с ссылкой на бота
            bot_link = "https://t.me/TaskPlanner2035Vikusik_bot"

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Заявка отправлена")
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText(
                f"✅ Ваша заявка на регистрацию отправлена!\n\n"
                f"📋 ФИО: {employee_data.get('last_name')} {employee_data.get('first_name')} {employee_data.get('middle_name') or ''}\n"
                f"📞 Телефон: {employee_data.get('phone_number')}\n\n"
                f"Для получения пароля:\n"
                f"1. Перейдите в Telegram бота:\n"
                f"   {bot_link}\n"
                f"2. Нажмите /start\n"
                f"3. Отправьте ваш номер телефона\n"
                f"4. После одобрения вы получите пароль\n\n"
                f"Обычно это занимает несколько минут."
            )

            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl

            open_bot_btn = msg_box.addButton("Перейти в Telegram бота", QMessageBox.ButtonRole.ActionRole)
            open_bot_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(bot_link)))
            msg_box.addButton(QMessageBox.StandardButton.Ok)
            msg_box.exec()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось отправить заявку: {e}")

    # ==========================================================
    # Публичные методы
    # ==========================================================

    def logout(self):
        """Выход из системы"""
        user_id = self.auth_service.get_current_user().get('id') if self.auth_service.get_current_user() else None
        self.auth_service.clear_session(user_id)
        self.auth_service.clear_current_user()
        self.phoneInput.clear()
        self.passwordInput.clear()
        self.rememberCheckbox.setChecked(False)
        QMessageBox.information(self, "Выход", "Вы успешно вышли из системы")
        self.show()

    def get_authenticated_user(self):
        """Возвращает данные авторизованного пользователя"""
        return self.auth_service.get_current_user()

    # ==========================================================
    # Обработчики событий
    # ==========================================================

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            self._on_login_clicked()
        else:
            super().keyPressEvent(event)