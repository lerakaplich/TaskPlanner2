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
    employee_saved = pyqtSignal(dict)  # ← Добавь эту строку

    def __init__(self, parent=None, employee_data=None):
        super().__init__(parent)

        # Определяем путь к UI файлу
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "settings", "employees", "employee_dialog.ui"
        )

        # Загружаем UI
        uic.loadUi(ui_path, self)

        # === ОПРЕДЕЛЯЕМ РЕЖИМ ===
        self.is_edit_mode = employee_data is not None and employee_data.get('id') is not None

        # Тестовые данные для комбобоксов
        self.test_divisions = [
            {"id": 1, "name": "Производственное подразделение №1"},
            {"id": 2, "name": "Производственное подразделение №2"},
            {"id": 3, "name": "Административное подразделение"},
        ]

        self.test_departments = {
            1: [
                {"id": 1, "name": "Сборочный цех"},
                {"id": 2, "name": "Сварочный цех"},
                {"id": 3, "name": "Лаборатория контроля"},
            ],
            2: [
                {"id": 4, "name": "Механический цех"},
                {"id": 5, "name": "Заготовительный цех"},
            ],
            3: [
                {"id": 6, "name": "Бухгалтерия"},
                {"id": 7, "name": "Отдел кадров"},
                {"id": 8, "name": "IT отдел"},
            ]
        }

        # Загружаем данные в комбобоксы
        self.load_divisions()

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
        else:
            self.setWindowTitle("Добавление нового сотрудника")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Добавление нового сотрудника")

        # Если это редактирование — заполняем данные
        if self.is_edit_mode:
            self.load_employee_data(employee_data)

        # Устанавливаем максимальную дату рождения
        self.dateEditBirthDate.setMaximumDate(QDate.currentDate())

    def setup_phone_validators(self):
        """Настройка валидаторов для телефонных номеров"""
        # В реальном приложении здесь можно добавить валидаторы
        # Например: QRegularExpressionValidator для формата +7 (XXX) XXX-XX-XX
        pass

    def load_divisions(self):
        """Загрузка подразделений в комбобокс"""
        self.comboBoxDivision.clear()
        self.comboBoxDivision.addItem("Выберите подразделение", None)

        for division in self.test_divisions:
            self.comboBoxDivision.addItem(division["name"], division["id"])

    def on_division_changed(self, index):
        """
        Обработчик изменения выбранного подразделения
        Загружает соответствующие отделы
        """
        self.comboBoxDepartment.clear()
        self.comboBoxDepartment.addItem("Выберите отдел", None)

        if index <= 0:  # Первый элемент "Выберите подразделение"
            return

        division_id = self.comboBoxDivision.currentData()

        if division_id in self.test_departments:
            for department in self.test_departments[division_id]:
                self.comboBoxDepartment.addItem(department["name"], department["id"])

    def add_division(self):
        """Открытие диалога добавления нового подразделения"""
        dialog = DivisionDialog(parent=self)  # parent=self — важно для модальности
        dialog.division_saved.connect(self.on_division_saved)  # подключаем сигнал
        dialog.exec()  # модальное окно

    def on_division_saved(self, division_data):
        """Обработка сохранения нового подразделения"""
        # Добавляем в тестовый список
        new_id = max([d["id"] for d in self.test_divisions] or [0]) + 1
        new_division = {
            "id": new_id,
            "name": division_data["name"]
        }
        self.test_divisions.append(new_division)

        # Добавляем пустой список отделов для нового подразделения
        self.test_departments[new_id] = []

        # Обновляем комбобокс подразделений
        self.load_divisions()

        # Автоматически выбираем только что добавленное подразделение
        for i in range(self.comboBoxDivision.count()):
            if self.comboBoxDivision.itemData(i) == new_id:
                self.comboBoxDivision.setCurrentIndex(i)
                break

        QMessageBox.information(
            self,
            "Успешно",
            f"Подразделение «{division_data['name']}» добавлено"
        )

    def add_department(self):
        """Открытие диалога добавления нового отдела"""
        division_id = self.comboBoxDivision.currentData()

        if not division_id:
            QMessageBox.warning(self, "Внимание", "Сначала выберите подразделение!")
            return

        dialog = DepartmentDialog(parent=self)
        dialog.department_saved.connect(lambda dept_data: self.on_department_saved(division_id, dept_data))
        dialog.exec()

    def on_department_saved(self, division_id, department_data):
        """Обработка сохранения нового отдела"""
        if division_id not in self.test_departments:
            self.test_departments[division_id] = []

        new_id = max([d["id"] for d in self.test_departments[division_id]] or [0]) + 1
        new_department = {
            "id": new_id,
            "name": department_data["name"]
        }
        self.test_departments[division_id].append(new_department)

        # Обновляем список отделов для текущего подразделения
        self.on_division_changed(self.comboBoxDivision.currentIndex())

        # Автоматически выбираем новый отдел
        for i in range(self.comboBoxDepartment.count()):
            if self.comboBoxDepartment.itemData(i) == new_id:
                self.comboBoxDepartment.setCurrentIndex(i)
                break

        QMessageBox.information(
            self,
            "Успешно",
            f"Отдел «{department_data['name']}» добавлен"
        )

    def validate_data(self):
        """
        Проверка заполнения обязательных полей

        Returns:
            tuple: (is_valid, error_message)
        """
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

        # Валидация email (простая проверка)
        email = self.lineEditEmail.text().strip()
        if email and "@" not in email:
            return False, "Пожалуйста, введите корректный email"

        return True, ""

    def get_employee_data(self):
        """
        Получение данных из формы

        Returns:
            dict: Словарь с данными сотрудника
        """
        return {
            "last_name": self.lineEditLastName.text().strip(),
            "first_name": self.lineEditFirstName.text().strip(),
            "middle_name": self.lineEditMiddleName.text().strip() or None,
            "birth_date": self.dateEditBirthDate.date().toPyDate(),
            "division_id": self.comboBoxDivision.currentData(),
            "division_name": self.comboBoxDivision.currentText(),
            "department_id": self.comboBoxDepartment.currentData(),
            "department_name": self.comboBoxDepartment.currentText(),
            "position": self.lineEditPosition.text().strip(),
            "role": self.comboBoxRole.currentText(),
            "phone_number": self.lineEditMobilePhone.text().strip(),
            "work_number": self.lineEditWorkPhone.text().strip() or None,
            "email": self.lineEditEmail.text().strip() or None,
        }

    def load_employee_data(self, data):
        """
        Заполнение формы данными сотрудника

        Args:
            data: словарь с данными сотрудника
        """
        self.lineEditLastName.setText(data.get("last_name", ""))
        self.lineEditFirstName.setText(data.get("first_name", ""))
        self.lineEditMiddleName.setText(data.get("middle_name", ""))

        if data.get("birth_date"):
            birth_date = data["birth_date"]
            if isinstance(birth_date, date):
                self.dateEditBirthDate.setDate(QDate(birth_date.year, birth_date.month, birth_date.day))

        # Выбор подразделения и отдела
        if data.get("division_id"):
            for i in range(self.comboBoxDivision.count()):
                if self.comboBoxDivision.itemData(i) == data["division_id"]:
                    self.comboBoxDivision.setCurrentIndex(i)
                    break

        if data.get("department_id"):
            # После выбора подразделения, отделы уже загружены
            for i in range(self.comboBoxDepartment.count()):
                if self.comboBoxDepartment.itemData(i) == data["department_id"]:
                    self.comboBoxDepartment.setCurrentIndex(i)
                    break

        self.lineEditPosition.setText(data.get("position", ""))

        # Выбор роли
        role_index = self.comboBoxRole.findText(data.get("role", "Пользователь"))
        if role_index >= 0:
            self.comboBoxRole.setCurrentIndex(role_index)

        self.lineEditMobilePhone.setText(data.get("phone_number", ""))
        self.lineEditWorkPhone.setText(data.get("work_number", ""))
        self.lineEditEmail.setText(data.get("email", ""))

    def save_employee(self):
        """Сохранение сотрудника"""
        # Валидация данных
        is_valid, error_msg = self.validate_data()

        if not is_valid:
            QMessageBox.warning(self, "Внимание", error_msg)
            return

        employee_data = self.get_employee_data()

        # Вывод в консоль (для отладки)
        print("=" * 50)
        print("Данные сотрудника:")
        for key, value in employee_data.items():
            print(f"{key}: {value}")
        print("=" * 50)

        # Отправляем сигнал с данными
        self.employee_saved.emit(employee_data)

        # Показываем сообщение и закрываем диалог
        QMessageBox.information(
            self,
            "Успешно",
            f"Сотрудник {employee_data['last_name']} {employee_data['first_name']}\n"
            f"успешно сохранен!"
        )

        self.accept()

    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        # Здесь можно добавить проверку на несохраненные изменения
        event.accept()

    def setup_keyboard_navigation(self):
        """Настройка перехода между полями по стрелкам Вверх/Вниз"""

        # Список всех полей в нужном порядке (от первого к последнему)
        self.fields = [
            self.lineEditLastName,  # Фамилия
            self.lineEditFirstName,  # Имя
            self.lineEditMiddleName,  # Отчество
            self.dateEditBirthDate,  # Дата рождения
            self.comboBoxDivision,  # Подразделение
            self.comboBoxDepartment,  # Отдел
            self.lineEditPosition,  # Должность
            self.comboBoxRole,  # Роль
            self.lineEditMobilePhone,  # Моб. телефон
            self.lineEditWorkPhone,  # Рабочий телефон
            self.lineEditEmail,  # Email
            # Добавляй сюда новые поля, если появятся
        ]

        # Подключаем обработчик клавиш для каждого поля
        for i, widget in enumerate(self.fields):
            widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Обработка нажатия стрелок Вверх и Вниз"""
        if event.type() == QtCore.QEvent.Type.KeyPress:
            key = event.key()

            # Находим текущий индекс поля
            try:
                current_index = self.fields.index(obj)
            except ValueError:
                return super().eventFilter(obj, event)

            if key == QtCore.Qt.Key.Key_Down:
                # Переход к следующему полю
                next_index = (current_index + 1) % len(self.fields)
                self.fields[next_index].setFocus()
                return True

            elif key == QtCore.Qt.Key.Key_Up:
                # Переход к предыдущему полю
                prev_index = (current_index - 1) % len(self.fields)
                self.fields[prev_index].setFocus()
                return True

        # Если не наша клавиша — передаём дальше
        return super().eventFilter(obj, event)

def main():
    """Основная функция для тестирования"""
    app = QApplication(sys.argv)

    # Создаем диалог с тестовыми данными для редактирования
    test_data = {
        "last_name": "Иванов",
        "first_name": "Иван",
        "middle_name": "Иванович",
        "birth_date": date(1990, 5, 15),
        "division_id": 1,
        "department_id": 1,
        "position": "Инженер-программист",
        "role": "Пользователь",
        "phone_number": "+7 (999) 123-45-67",
        "work_number": "+7 (495) 123-45-67",
        "email": "ivan.ivanov@example.com"
    }

    # Для создания нового сотрудника передаем None
    dialog = EmployeeDialog(employee_data=None)  # Для редактирования передать test_data

    dialog.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()