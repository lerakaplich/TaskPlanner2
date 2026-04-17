"""
employee_dialog.py
Диалог добавления/редактирования сотрудника
"""

import os
import sys
from datetime import date
from PyQt6.QtWidgets import (
    QApplication, QDialog, QMessageBox, QInputDialog
)
from PyQt6 import uic, QtCore
from PyQt6.QtCore import QDate, pyqtSignal

from windows.settings.departments.department_dialog import DepartmentDialog
from windows.settings.divisions.division_dialog import DivisionDialog


class EmployeeDialog(QDialog):
    """Диалоговое окно для добавления/редактирования сотрудника"""
    employee_saved = pyqtSignal(dict)

    def __init__(self, parent=None, employee_data=None, session=None):
        super().__init__(parent)

        self.session = session
        self.employee_data = employee_data
        self.all_divisions = []
        self.all_departments = []
        self.departments_by_division = {}

        # Определяем путь к UI файлу
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "settings", "employees", "employee_dialog.ui"
        )

        # Загружаем UI
        uic.loadUi(ui_path, self)

        # Загружаем реальные данные из БД
        self.load_divisions_from_db()
        self.load_departments_from_db()

        # === ОПРЕДЕЛЯЕМ РЕЖИМ ===
        self.is_edit_mode = employee_data is not None and employee_data.get('id') is not None

        # Загружаем данные в комбобоксы
        self.load_divisions_combo()

        # Настраиваем валидацию и клавиатуру
        self.setup_phone_validators()
        self.setup_keyboard_navigation()

        # Подключаем сигналы
        self.btnSave.clicked.connect(self.save_employee)
        self.btnAddDivision.clicked.connect(self.add_division)
        self.btnAddDepartment.clicked.connect(self.add_department)
        self.comboBoxDivision.currentIndexChanged.connect(self.on_division_changed)

        # === УСТАНАВЛИВАЕМ ЗАГОЛОВКИ В ЗАВИСИМОСТИ ОТ РЕЖИМА ===
        if self.is_edit_mode:
            self.setWindowTitle("Редактирование сотрудника")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Редактирование сотрудника")
            self.load_employee_data(employee_data)
        else:
            self.setWindowTitle("Добавление нового сотрудника")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Добавление нового сотрудника")

        # Устанавливаем максимальную дату рождения
        self.dateEditBirthDate.setMaximumDate(QDate.currentDate())

    def load_divisions_from_db(self):
        """Загрузка подразделений из БД"""
        try:
            if self.session:
                from services.employee_service import EmployeeService
                employee_service = EmployeeService(self.session)
                self.all_divisions = employee_service.get_all_divisions()
                print(f"✅ Загружено {len(self.all_divisions)} подразделений")
        except Exception as e:
            print(f"❌ Ошибка загрузки подразделений: {e}")
            self.all_divisions = []

    def load_departments_from_db(self):
        """Загрузка отделов из БД"""
        try:
            if self.session:
                from services.employee_service import EmployeeService
                employee_service = EmployeeService(self.session)
                self.all_departments = employee_service.get_all_departments()
                # Группируем отделы по подразделениям
                self.departments_by_division = {}
                for dept in self.all_departments:
                    div_id = dept.get('division_id')
                    if div_id not in self.departments_by_division:
                        self.departments_by_division[div_id] = []
                    self.departments_by_division[div_id].append(dept)
                print(f"✅ Загружено {len(self.all_departments)} отделов")
        except Exception as e:
            print(f"❌ Ошибка загрузки отделов: {e}")
            self.all_departments = []
            self.departments_by_division = {}

    def load_divisions_combo(self):
        """Загрузка подразделений в комбобокс"""
        self.comboBoxDivision.clear()
        self.comboBoxDivision.addItem("Выберите подразделение", None)

        for division in self.all_divisions:
            self.comboBoxDivision.addItem(division.get("name", "Без названия"), division.get("id"))

    def on_division_changed(self, index):
        """Обработчик изменения выбранного подразделения - загружает соответствующие отделы"""
        self.comboBoxDepartment.clear()
        self.comboBoxDepartment.addItem("Выберите отдел", None)

        if index <= 0:
            return

        division_id = self.comboBoxDivision.currentData()

        if division_id in self.departments_by_division:
            for department in self.departments_by_division[division_id]:
                self.comboBoxDepartment.addItem(department.get("name", "Без названия"), department.get("id"))

    def add_division(self):
        """Открытие диалога добавления нового подразделения"""
        if not self.session:
            QMessageBox.warning(self, "Ошибка", "Нет подключения к БД")
            return
        dialog = DivisionDialog(parent=self, division_data=None, session=self.session)
        dialog.division_saved.connect(self.on_division_saved)
        dialog.exec()

    def on_division_saved(self, division_data):
        """Обработка сохранения нового подразделения"""
        # Обновляем список подразделений
        self.load_divisions_from_db()
        self.load_divisions_combo()

        # Выбираем новое подразделение
        new_id = division_data.get('id')
        for i in range(self.comboBoxDivision.count()):
            if self.comboBoxDivision.itemData(i) == new_id:
                self.comboBoxDivision.setCurrentIndex(i)
                break

        QMessageBox.information(self, "Успешно", f"Подразделение «{division_data.get('name')}» добавлено")

    def add_department(self):
        """Открытие диалога добавления нового отдела"""
        division_id = self.comboBoxDivision.currentData()

        if not division_id:
            QMessageBox.warning(self, "Внимание", "Сначала выберите подразделение!")
            return

        if not self.session:
            QMessageBox.warning(self, "Ошибка", "Нет подключения к БД")
            return

        dialog = DepartmentDialog(parent=self, department_data=None, session=self.session)
        dialog.department_saved.connect(self.on_department_saved)
        dialog.exec()

    def on_department_saved(self, department_data):
        """Обработка сохранения нового отдела"""
        # Обновляем список отделов
        self.load_departments_from_db()

        # Обновляем отделы для текущего подразделения
        division_id = self.comboBoxDivision.currentData()
        self.on_division_changed(self.comboBoxDivision.currentIndex())

        # Выбираем новый отдел
        new_id = department_data.get('id')
        for i in range(self.comboBoxDepartment.count()):
            if self.comboBoxDepartment.itemData(i) == new_id:
                self.comboBoxDepartment.setCurrentIndex(i)
                break

        QMessageBox.information(self, "Успешно", f"Отдел «{department_data.get('name')}» добавлен")

    def setup_phone_validators(self):
        """Настройка валидаторов для телефонных номеров"""
        pass

    def validate_data(self):
        """Проверка заполнения обязательных полей"""
        if not self.lineEditLastName.text().strip():
            return False, "Пожалуйста, заполните поле 'Фамилия'"

        if not self.lineEditFirstName.text().strip():
            return False, "Пожалуйста, заполните поле 'Имя'"

        if self.comboBoxDivision.currentData() is None:
            return False, "Пожалуйста, выберите подразделение"

        if self.comboBoxDepartment.currentData() is None:
            return False, "Пожалуйста, выберите отдел"

        if not self.lineEditPosition.text().strip():
            return False, "Пожалуйста, заполните поле 'Должность'"

        if not self.lineEditMobilePhone.text().strip():
            return False, "Пожалуйста, заполните поле 'Моб. телефон'"

        email = self.lineEditEmail.text().strip()
        if email and "@" not in email:
            return False, "Пожалуйста, введите корректный email"

        return True, ""

    def get_employee_data(self):
        """Получение данных из формы"""
        rights_map = {
            "Пользователь": "user",
            "Администратор": "admin",
            "Суперадминистратор": "superadmin"
        }
        role_text = self.comboBoxRole.currentText()

        division_id = self.comboBoxDivision.currentData()
        department_id = self.comboBoxDepartment.currentData()

        print(f"📋 Выбранное подразделение ID: {division_id}")
        print(f"📋 Выбранный отдел ID: {department_id}")

        return {
            "id": self.employee_data.get('id') if self.employee_data else None,
            "last_name": self.lineEditLastName.text().strip(),
            "first_name": self.lineEditFirstName.text().strip(),
            "middle_name": self.lineEditMiddleName.text().strip() or None,
            "birth_date": self.dateEditBirthDate.date().toPyDate(),
            "division_id": division_id,
            "department_id": department_id,
            "position": self.lineEditPosition.text().strip(),
            "rights": rights_map.get(role_text, "user"),
            "phone_number": self.lineEditMobilePhone.text().strip(),
            "work_number": self.lineEditWorkPhone.text().strip() or None,
            "email": self.lineEditEmail.text().strip() or None,
        }

    def load_employee_data(self, data):
        """Заполнение формы данными сотрудника"""
        self.lineEditLastName.setText(data.get("last_name", ""))
        self.lineEditFirstName.setText(data.get("first_name", ""))
        self.lineEditMiddleName.setText(data.get("middle_name", ""))

        if data.get("birth_date"):
            birth_date = data["birth_date"]
            if isinstance(birth_date, date):
                self.dateEditBirthDate.setDate(QDate(birth_date.year, birth_date.month, birth_date.day))

        # Выбор подразделения
        division_id = data.get("division_id")
        if division_id:
            for i in range(self.comboBoxDivision.count()):
                if self.comboBoxDivision.itemData(i) == division_id:
                    self.comboBoxDivision.setCurrentIndex(i)
                    break

        # После выбора подразделения загружаются отделы, затем выбираем отдел
        department_id = data.get("department_id")
        if department_id:
            # Небольшая задержка для загрузки отделов
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, lambda: self.select_department(department_id))

        self.lineEditPosition.setText(data.get("position", ""))

        # Выбор роли
        rights = data.get("rights", "user")
        role_map = {
            "user": "Пользователь",
            "admin": "Администратор",
            "superadmin": "Суперадминистратор"
        }
        role_text = role_map.get(rights, "Пользователь")
        role_index = self.comboBoxRole.findText(role_text)
        if role_index >= 0:
            self.comboBoxRole.setCurrentIndex(role_index)

        self.lineEditMobilePhone.setText(data.get("phone_number", ""))
        self.lineEditWorkPhone.setText(data.get("work_number", ""))
        self.lineEditEmail.setText(data.get("email", ""))

    def select_department(self, department_id):
        """Выбор отдела в комбобоксе после загрузки"""
        for i in range(self.comboBoxDepartment.count()):
            if self.comboBoxDepartment.itemData(i) == department_id:
                self.comboBoxDepartment.setCurrentIndex(i)
                break

    def save_employee(self):
        """Сохранение сотрудника"""
        is_valid, error_msg = self.validate_data()

        if not is_valid:
            QMessageBox.warning(self, "Внимание", error_msg)
            return

        employee_data = self.get_employee_data()

        print("=" * 50)
        print("Данные сотрудника:")
        for key, value in employee_data.items():
            print(f"{key}: {value}")
        print("=" * 50)

        self.employee_saved.emit(employee_data)
        self.accept()

    def closeEvent(self, event):
        event.accept()

    def setup_keyboard_navigation(self):
        """Настройка перехода между полями по стрелкам Вверх/Вниз"""
        self.fields = [
            self.lineEditLastName,
            self.lineEditFirstName,
            self.lineEditMiddleName,
            self.dateEditBirthDate,
            self.comboBoxDivision,
            self.comboBoxDepartment,
            self.lineEditPosition,
            self.comboBoxRole,
            self.lineEditMobilePhone,
            self.lineEditWorkPhone,
            self.lineEditEmail,
        ]

        for widget in self.fields:
            widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.KeyPress:
            key = event.key()
            try:
                current_index = self.fields.index(obj)
            except ValueError:
                return super().eventFilter(obj, event)

            if key == QtCore.Qt.Key.Key_Down:
                next_index = (current_index + 1) % len(self.fields)
                self.fields[next_index].setFocus()
                return True
            elif key == QtCore.Qt.Key.Key_Up:
                prev_index = (current_index - 1) % len(self.fields)
                self.fields[prev_index].setFocus()
                return True

        return super().eventFilter(obj, event)