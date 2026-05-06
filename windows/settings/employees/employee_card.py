from PyQt6 import uic
from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import pyqtSignal
import os


class EmployeeCard(QFrame):
    """Карточка сотрудника на всю ширину"""

    edit_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)

    def __init__(self, employee_data, employee_service, parent=None):
        super().__init__(parent)
        self.employee_data = employee_data
        self.employee_service = employee_service
        self.employee_id = employee_data.get('id', 0)

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "settings", "employees", "employee_card.ui"
        )
        uic.loadUi(ui_path, self)

        self.fill_data()
        self.connect_signals()

    def connect_signals(self):
        """Подключение сигналов"""
        self.editButton.clicked.connect(lambda: self.edit_clicked.emit(self.employee_id))
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

        # Мобильный телефон
        display_phone = display_data.get('display_phone', '—')
        if hasattr(self, 'mobilePhoneValue'):
            self.mobilePhoneValue.setText(display_phone)
            has_phone = display_phone != '—'
            self.mobilePhoneValue.setVisible(has_phone)
            if hasattr(self, 'mobilePhoneLabel'):
                self.mobilePhoneLabel.setVisible(has_phone)

        # Рабочий телефон
        work_phone = display_data.get('work_number', '')
        if hasattr(self, 'workPhoneValue'):
            self.workPhoneValue.setText(work_phone if work_phone else '—')
            has_work_phone = bool(work_phone)
            self.workPhoneValue.setVisible(has_work_phone)
            if hasattr(self, 'workPhoneLabel'):
                self.workPhoneLabel.setVisible(has_work_phone)

        # Email
        email = display_data.get('email', '')
        if hasattr(self, 'emailValue'):
            self.emailValue.setText(email if email else '—')
            has_email = bool(email)
            self.emailValue.setVisible(has_email)
            if hasattr(self, 'emailLabel'):
                self.emailLabel.setVisible(has_email)