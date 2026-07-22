# windows/settings/employees/employee_card.py

from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QMessageBox
from PyQt6.QtCore import pyqtSignal
import os

from services.permissions.app_permissions import AppRole


class EmployeeCard(QFrame):
    """Карточка сотрудника на всю ширину"""

    edit_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)
    open_clicked = pyqtSignal(int)  # <-- ДОБАВЛЯЕМ СИГНАЛ ДЛЯ btnOpen

    def __init__(self, employee_data, employee_service, parent=None, read_only=False, permission_service=None):
        super().__init__(parent)
        self.employee_data = employee_data
        self.employee_service = employee_service
        self.employee_id = employee_data.get('id', 0)
        self.read_only = read_only
        self.permission_service = permission_service
        self._can_view_contacts = self._check_contact_permission()

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "settings", "employees", "employee_card.ui"
        )
        uic.loadUi(ui_path, self)

        self.fill_data()
        self.connect_signals()
        self._apply_read_only_state()
        self._apply_contact_visibility()

    def _check_contact_permission(self) -> bool:
        """Проверяет, может ли пользователь видеть контакты этого сотрудника"""
        if not self.permission_service:
            return True
        return self.permission_service.can_view_contacts(self.employee_id)

    def _apply_contact_visibility(self):
        """Применяет видимость контактной информации"""
        if not self._can_view_contacts:
            if hasattr(self, 'mobilePhoneValue'):
                self.mobilePhoneValue.hide()
            if hasattr(self, 'mobilePhoneLabel'):
                self.mobilePhoneLabel.hide()
            if hasattr(self, 'workPhoneValue'):
                self.workPhoneValue.hide()
            if hasattr(self, 'workPhoneLabel'):
                self.workPhoneLabel.hide()
            if hasattr(self, 'emailValue'):
                self.emailValue.hide()
            if hasattr(self, 'emailLabel'):
                self.emailLabel.hide()
            if hasattr(self, 'contactInfoLabel'):
                self.contactInfoLabel.setText("🔒 Контактная информация скрыта")
                self.contactInfoLabel.setStyleSheet("color: #999; font-size: 11px;")
                self.contactInfoLabel.setVisible(True)

    def _apply_read_only_state(self):
        """Применяет состояние только просмотра с учётом прав"""
        # По умолчанию
        show_open = True
        show_edit = True
        show_delete = True
        edit_text = "Редактировать"

        if self.permission_service:
            # Проверяем права
            can_edit = self.permission_service.can_edit_employee(self.employee_id)
            can_delete = self.permission_service.can_delete_employee(self.employee_id)

            # Если это суперадмин (target) и пользователь - администратор
            target_role = self.employee_data.get('rights', '')
            user_role = self.permission_service.get_app_role()

            if user_role == AppRole.ADMIN and target_role == 'superadmin':
                # Для админа у суперадмина: ТОЛЬКО "Открыть"
                show_edit = False
                show_delete = False
                show_open = True
            elif not can_edit:
                show_edit = False
                show_delete = False
                show_open = True
            elif not can_delete:
                show_delete = False
                show_open = True

        # Применяем read_only режим
        if self.read_only:
            show_edit = False
            show_delete = False
            show_open = True

        # Настраиваем кнопку "Открыть"
        if hasattr(self, 'btnOpen'):
            self.btnOpen.setVisible(show_open)
            if show_open:
                self.btnOpen.show()
            else:
                self.btnOpen.hide()

        # Настраиваем кнопку редактирования
        if hasattr(self, 'editButton'):
            if show_edit:
                self.editButton.setText(edit_text)
                self.editButton.setVisible(True)
                self.editButton.show()
            else:
                self.editButton.setVisible(False)
                self.editButton.hide()

        # Настраиваем кнопку удаления
        if hasattr(self, 'deleteButton'):
            if show_delete:
                self.deleteButton.setVisible(True)
                self.deleteButton.show()
            else:
                self.deleteButton.setVisible(False)
                self.deleteButton.hide()

    def connect_signals(self):
        """Подключение сигналов"""
        # Кнопка "Открыть" - всегда ведёт в профиль
        if hasattr(self, 'btnOpen'):
            self.btnOpen.clicked.connect(lambda: self.open_clicked.emit(self.employee_id))

        # Кнопка "Редактировать" - ведёт в диалог редактирования
        if hasattr(self, 'editButton'):
            self.editButton.clicked.connect(lambda: self.edit_clicked.emit(self.employee_id))

        # Кнопка "Удалить"
        if hasattr(self, 'deleteButton') and self.deleteButton.isVisible():
            self.deleteButton.clicked.connect(lambda: self.delete_clicked.emit(self.employee_id))

    def fill_data(self):
        """Заполнение данными через сервис"""
        # Подготавливаем данные для отображения
        display_data = self.employee_service.prepare_employee_for_display(self.employee_data)

        # ФИО
        fio = display_data.get('full_name', '')
        if not fio:
            last_name = display_data.get('last_name', '')
            first_name = display_data.get('first_name', '')
            middle_name = display_data.get('middle_name', '')
            fio = ' '.join(part for part in [last_name, first_name, middle_name] if part)
        self.nameLabel.setText(fio)

        # Роль
        role_display = display_data.get('role_display', 'Пользователь')
        role_color = display_data.get('role_color', '#1B232A')

        self.roleLabel.setText(role_display)
        self.roleLabel.setStyleSheet(f"""
            QLabel#roleLabel {{
                background-color: {role_color};
                color: white;
                padding: 4px 14px;
                border-radius: 12px;
                font-weight: bold;
            }}
        """)
        self.roleLabel.setFixedHeight(28)

        # Должность
        position = display_data.get('position', '—')
        if position is None or position == '':
            position = '—'
        if hasattr(self, 'positionValue'):
            self.positionValue.setText(position)

        # Отдел
        department_name = display_data.get('department_name', '—')
        if department_name is None or department_name == '':
            department_name = '—'

        if hasattr(self, 'departmentValue'):
            self.departmentValue.setText(department_name)
            has_dept = department_name != '—'
            if hasattr(self, 'departmentSectionLabel'):
                self.departmentSectionLabel.setVisible(has_dept)
            self.departmentValue.setVisible(has_dept)

        # Подразделение
        division_name = display_data.get('division_name', '—')
        if division_name is None or division_name == '':
            division_name = '—'

        if hasattr(self, 'divisionValue'):
            self.divisionValue.setText(division_name)
            has_div = division_name != '—'
            if hasattr(self, 'divisionSectionLabel'):
                self.divisionSectionLabel.setVisible(has_div)
            self.divisionValue.setVisible(has_div)

        # Мобильный телефон (показываем только если есть право)
        display_phone = display_data.get('display_phone', '—')
        if hasattr(self, 'mobilePhoneValue'):
            self.mobilePhoneValue.setText(display_phone)
            has_phone = display_phone != '—'
            show_phone = has_phone and self._can_view_contacts
            self.mobilePhoneValue.setVisible(show_phone)
            if hasattr(self, 'mobilePhoneLabel'):
                self.mobilePhoneLabel.setVisible(show_phone)

        # Рабочий телефон (показываем только если есть право)
        work_phone = display_data.get('work_number', '')
        if hasattr(self, 'workPhoneValue'):
            has_work_phone = bool(work_phone)
            show_work_phone = has_work_phone and self._can_view_contacts
            self.workPhoneValue.setText(work_phone if work_phone else '—')
            self.workPhoneValue.setVisible(show_work_phone)
            if hasattr(self, 'workPhoneLabel'):
                self.workPhoneLabel.setVisible(show_work_phone)

        # Email (показываем только если есть право)
        email = display_data.get('email', '')
        if hasattr(self, 'emailValue'):
            has_email = bool(email)
            show_email = has_email and self._can_view_contacts
            self.emailValue.setText(email if email else '—')
            self.emailValue.setVisible(show_email)
            if hasattr(self, 'emailLabel'):
                self.emailLabel.setVisible(show_email)