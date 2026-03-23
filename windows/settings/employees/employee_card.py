from PyQt6 import uic
from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import pyqtSignal
import os


class EmployeeCard(QFrame):
    """Карточка сотрудника на всю ширину"""

    edit_clicked = pyqtSignal(int)  # id сотрудника
    delete_clicked = pyqtSignal(int)  # id сотрудника

    def __init__(self, employee_data, parent=None):
        super().__init__(parent)
        self.employee_data = employee_data
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
        """Заполнение данными"""
        # ФИО
        last_name = self.employee_data.get('last_name', '')
        first_name = self.employee_data.get('first_name', '')
        middle_name = self.employee_data.get('middle_name', '')

        fio_parts = [last_name, first_name, middle_name]
        fio = ' '.join(part for part in fio_parts if part)
        self.nameLabel.setText(fio)

        # Роль
        rights = self.employee_data.get('rights', 'user')
        role_text = {
            'superadmin': 'Суперадминистратор',
            'admin': 'Администратор',
            'user': 'Пользователь'
        }.get(rights, 'Пользователь')

        self.roleLabel.setText(role_text)

        # Цвет роли
        role_colors = {
            'superadmin': '#D22730',  # красный
            'admin': '#ccab6e',  # золотой
            'user': '#1B232A'  # темно-серый
        }
        self.roleLabel.setStyleSheet(f"""
            QLabel#roleLabel {{
                background-color: {role_colors.get(rights, '#1B232A')};
                color: white;
                padding: 3px 10px;
                border-radius: 12px;
                font-weight: bold;
            }}
        """)

        # Должность
        position = self.employee_data.get('position', '—')
        if hasattr(self, 'positionValue'):
            self.positionValue.setText(position)

        # Отдел
        dept_name = '—'
        if self.employee_data.get('department'):
            dept = self.employee_data['department']
            if isinstance(dept, dict):
                dept_name = dept.get('name', '—')
            else:
                dept_name = str(dept)

        if hasattr(self, 'departmentValue'):
            self.departmentValue.setText(dept_name)

        # Подразделение
        div_name = '—'
        if self.employee_data.get('division'):
            div = self.employee_data['division']
            if isinstance(div, dict):
                div_name = div.get('name', '—')
            else:
                div_name = str(div)

        if hasattr(self, 'divisionValue'):
            self.divisionValue.setText(div_name)

        # Мобильный телефон
        phone = self.employee_data.get('phone_number', '')
        if phone and hasattr(self, 'mobilePhoneValue'):
            self.mobilePhoneValue.setText(phone)
            self.mobilePhoneValue.setVisible(True)
            if hasattr(self, 'mobilePhoneLabel'):
                self.mobilePhoneLabel.setVisible(True)
        else:
            if hasattr(self, 'mobilePhoneValue'):
                self.mobilePhoneValue.setVisible(False)
            if hasattr(self, 'mobilePhoneLabel'):
                self.mobilePhoneLabel.setVisible(False)

        # Рабочий телефон (пока нет в данных)
        if hasattr(self, 'workPhoneValue'):
            self.workPhoneValue.setVisible(False)
        if hasattr(self, 'workPhoneLabel'):
            self.workPhoneLabel.setVisible(False)

        # Email
        email = self.employee_data.get('email', '')
        if email and hasattr(self, 'emailValue'):
            self.emailValue.setText(email)
            self.emailValue.setVisible(True)
            if hasattr(self, 'emailLabel'):
                self.emailLabel.setVisible(True)
        else:
            if hasattr(self, 'emailValue'):
                self.emailValue.setVisible(False)
            if hasattr(self, 'emailLabel'):
                self.emailLabel.setVisible(False)