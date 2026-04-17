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

        fio = ' '.join(part for part in [last_name, first_name, middle_name] if part)
        self.nameLabel.setText(fio)

        # === РОЛЬ ===
        rights = self.employee_data.get('rights', 'user')
        role_text = {
            'superadmin': 'Суперадминистратор',
            'admin': 'Администратор',
            'user': 'Пользователь'
        }.get(rights, 'Пользователь')

        self.roleLabel.setText(role_text)

        role_colors = {
            'superadmin': '#D22730',  # красный
            'admin': '#ccab6e',  # золотой
            'user': '#1B232A'  # тёмно-серый
        }

        self.roleLabel.setStyleSheet(f"""
            QLabel#roleLabel {{
                background-color: {role_colors.get(rights, '#1B232A')};
                color: white;
                padding: 4px 14px;
                border-radius: 12px;
                font-weight: bold;
            }}
        """)
        self.roleLabel.setFixedHeight(28)

        # Должность
        position = self.employee_data.get('position', '—')
        if hasattr(self, 'positionValue'):
            self.positionValue.setText(position)

        # Отдел
        dept_name = '—'
        if self.employee_data.get('department'):
            dept = self.employee_data['department']
            dept_name = dept.get('name', str(dept)) if isinstance(dept, dict) else str(dept)
        elif self.employee_data.get('department_id'):
            dept_id = self.employee_data.get('department_id')
            if hasattr(self, 'parent') and hasattr(self.parent(), 'get_department_name'):
                dept_name = self.parent().get_department_name(dept_id)
            else:
                dept_name = f"Отдел ID: {dept_id}"
        elif self.employee_data.get('department_name'):
            dept_name = self.employee_data.get('department_name')

        if hasattr(self, 'departmentValue'):
            self.departmentValue.setText(dept_name)
            if hasattr(self, 'departmentSectionLabel'):
                self.departmentSectionLabel.setVisible(dept_name != '—')
            self.departmentValue.setVisible(dept_name != '—')

        # Подразделение
        div_name = '—'
        if self.employee_data.get('division'):
            div = self.employee_data['division']
            div_name = div.get('name', str(div)) if isinstance(div, dict) else str(div)
        elif self.employee_data.get('division_id'):
            div_id = self.employee_data.get('division_id')
            if hasattr(self, 'parent') and hasattr(self.parent(), 'get_division_name'):
                div_name = self.parent().get_division_name(div_id)
            else:
                div_name = f"Подразделение ID: {div_id}"
        elif self.employee_data.get('division_name'):
            div_name = self.employee_data.get('division_name')

        if hasattr(self, 'divisionValue'):
            self.divisionValue.setText(div_name)
            if hasattr(self, 'divisionSectionLabel'):
                self.divisionSectionLabel.setVisible(div_name != '—')
            self.divisionValue.setVisible(div_name != '—')

        # Мобильный телефон
        phone = self.employee_data.get('phone_number', '')
        if hasattr(self, 'mobilePhoneValue'):
            self.mobilePhoneValue.setText(phone if phone else '—')
            self.mobilePhoneValue.setVisible(bool(phone))
            if hasattr(self, 'mobilePhoneLabel'):
                self.mobilePhoneLabel.setVisible(bool(phone))

        # Рабочий телефон
        work_phone = self.employee_data.get('work_number', '')
        if hasattr(self, 'workPhoneValue'):
            self.workPhoneValue.setText(work_phone if work_phone else '—')
            self.workPhoneValue.setVisible(bool(work_phone))
            if hasattr(self, 'workPhoneLabel'):
                self.workPhoneLabel.setVisible(bool(work_phone))

        # Email
        email = self.employee_data.get('email', '')
        if hasattr(self, 'emailValue'):
            self.emailValue.setText(email if email else '—')
            self.emailValue.setVisible(bool(email))
            if hasattr(self, 'emailLabel'):
                self.emailLabel.setVisible(bool(email))