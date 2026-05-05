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
        role = self.employee_data.get('role', 'user')
        # Если пришло поле 'rights' (старое), используем его
        if not role or role == 'user':
            rights = self.employee_data.get('rights', 'user')
        else:
            rights = role

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
        if position is None or position == '':
            position = '—'
        if hasattr(self, 'positionValue'):
            self.positionValue.setText(position)

        # ===== ОТДЕЛ =====
        # Пробуем получить название отдела из разных полей
        department_name = '—'

        # 1. Сначала пробуем department_name (уже готовое название)
        if self.employee_data.get('department_name') and self.employee_data.get('department_name') != '—':
            department_name = self.employee_data.get('department_name')
        # 2. Пробуем department (объект)
        elif self.employee_data.get('department'):
            dept = self.employee_data['department']
            if isinstance(dept, dict):
                department_name = dept.get('name', '—')
            else:
                department_name = str(dept) if str(dept) != '—' else '—'
        # 3. Пробуем получить из parent через get_department_name
        elif self.employee_data.get('department_id') and self.employee_data.get('department_id') != '—':
            dept_id = self.employee_data.get('department_id')
            if hasattr(self, 'parent') and hasattr(self.parent(), 'get_department_name'):
                dept_name = self.parent().get_department_name(dept_id)
                if dept_name and dept_name != '—':
                    department_name = dept_name

        if hasattr(self, 'departmentValue'):
            self.departmentValue.setText(department_name)
            # Показываем секцию только если есть название
            has_dept = department_name != '—'
            if hasattr(self, 'departmentSectionLabel'):
                self.departmentSectionLabel.setVisible(has_dept)
            self.departmentValue.setVisible(has_dept)

        # ===== ПОДРАЗДЕЛЕНИЕ =====
        division_name = '—'

        # 1. Сначала пробуем division_name (уже готовое название)
        if self.employee_data.get('division_name') and self.employee_data.get('division_name') != '—':
            division_name = self.employee_data.get('division_name')
        # 2. Пробуем division (объект)
        elif self.employee_data.get('division'):
            div = self.employee_data['division']
            if isinstance(div, dict):
                division_name = div.get('name', '—')
            else:
                division_name = str(div) if str(div) != '—' else '—'
        # 3. Пробуем получить из parent через get_division_name
        elif self.employee_data.get('division_id') and self.employee_data.get('division_id') != '—':
            div_id = self.employee_data.get('division_id')
            if hasattr(self, 'parent') and hasattr(self.parent(), 'get_division_name'):
                div_name = self.parent().get_division_name(div_id)
                if div_name and div_name != '—':
                    division_name = div_name

        if hasattr(self, 'divisionValue'):
            self.divisionValue.setText(division_name)
            has_div = division_name != '—'
            if hasattr(self, 'divisionSectionLabel'):
                self.divisionSectionLabel.setVisible(has_div)
            self.divisionValue.setVisible(has_div)

        # Мобильный телефон
        phone = self.employee_data.get('phone_number', '')
        if phone:
            # Убираем +375 если есть для отображения
            display_phone = phone
            if phone.startswith('375'):
                display_phone = '+' + phone
            elif phone.startswith('+'):
                display_phone = phone
        else:
            display_phone = '—'

        if hasattr(self, 'mobilePhoneValue'):
            self.mobilePhoneValue.setText(display_phone)
            has_phone = phone and phone != ''
            self.mobilePhoneValue.setVisible(has_phone)
            if hasattr(self, 'mobilePhoneLabel'):
                self.mobilePhoneLabel.setVisible(has_phone)

        # Рабочий телефон
        work_phone = self.employee_data.get('work_number', '')
        if hasattr(self, 'workPhoneValue'):
            self.workPhoneValue.setText(work_phone if work_phone else '—')
            has_work_phone = work_phone and work_phone != ''
            self.workPhoneValue.setVisible(has_work_phone)
            if hasattr(self, 'workPhoneLabel'):
                self.workPhoneLabel.setVisible(has_work_phone)

        # Email
        email = self.employee_data.get('email', '')
        if hasattr(self, 'emailValue'):
            self.emailValue.setText(email if email else '—')
            has_email = bool(email and email != '')  # ← ПРЕОБРАЗУЕМ В BOOL
            self.emailValue.setVisible(has_email)
            if hasattr(self, 'emailLabel'):
                self.emailLabel.setVisible(has_email)