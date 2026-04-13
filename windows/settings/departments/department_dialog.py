import sys
import os
from pathlib import Path
from PyQt6 import QtWidgets, QtCore, uic
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QWidget, QPushButton, QLineEdit, QLabel, QMessageBox
from PyQt6.QtCore import pyqtSignal, Qt, QEvent


class DepartmentDialog(QDialog):
    department_saved = pyqtSignal(dict)

    def __init__(self, parent=None, department_data=None, session=None):
        super().__init__(parent)

        self.session = session
        self.department_data = department_data
        self.employees = []

        script_dir = Path(__file__).resolve().parent
        ui_path = script_dir.parent.parent.parent / "ui" / "settings" / "departments" / "department_dialog.ui"

        print(f"Загрузка UI из: {ui_path}")

        if not ui_path.exists():
            raise FileNotFoundError(f"UI файл не найден:\n{ui_path}")

        uic.loadUi(str(ui_path), self)

        self.init_ui()

        # Загружаем реальных сотрудников
        self.load_real_employees()

        self.setup_managers_combo()

        if self.department_data:
            self.load_department_data()

        self.btnSave.clicked.connect(self.save_department)
        self.setup_keyboard_navigation()

    def load_real_employees(self):
        """Загрузка реальных сотрудников из БД"""
        try:
            if self.session:
                from services.employee_service import EmployeeService
                employee_service = EmployeeService(self.session)
                real_employees = employee_service.get_all_employees()

                self.employees = []
                for emp in real_employees:
                    full_name = f"{emp['last_name']} {emp['first_name']}"
                    if emp.get('middle_name'):
                        full_name += f" {emp['middle_name']}"

                    self.employees.append({
                        "id": emp['id'],
                        "full_name": full_name,
                        "position": emp.get('position', 'Сотрудник')
                    })

                print(f"✅ Загружено {len(self.employees)} реальных сотрудников для выбора")
            else:
                self.employees = self.get_test_employees()
        except Exception as e:
            print(f"❌ Ошибка загрузки сотрудников: {e}")
            self.employees = self.get_test_employees()

    def get_test_employees(self):
        """Тестовые данные (запасной вариант)"""
        return [
            {"id": 1, "full_name": "Иванов Иван Иванович", "position": "Директор"},
            {"id": 2, "full_name": "Петров Петр Петрович", "position": "Заместитель директора"},
            {"id": 3, "full_name": "Сидорова Анна Владимировна", "position": "Начальник отдела"},
            {"id": 4, "full_name": "Козлов Дмитрий Сергеевич", "position": "Ведущий специалист"},
            {"id": 5, "full_name": "Михайлова Елена Александровна", "position": "Специалист"},
            {"id": 6, "full_name": "Николаев Андрей Викторович", "position": "Менеджер"},
            {"id": 7, "full_name": "Смирнова Ольга Петровна", "position": "Главный бухгалтер"},
            {"id": 8, "full_name": "Федоров Алексей Сергеевич", "position": "Системный администратор"},
            {"id": 9, "full_name": "Морозова Екатерина Дмитриевна", "position": "HR-директор"},
            {"id": 10, "full_name": "Волков Артем Николаевич", "position": "Руководитель отдела продаж"},
        ]

    def init_ui(self):
        if self.department_data:
            self.setWindowTitle("Редактирование отдела")
            self.titleLabel.setText("Редактирование отдела")
        else:
            self.setWindowTitle("Добавление отдела")
            self.titleLabel.setText("Добавление нового отдела")

    def setup_managers_combo(self):
        """Создаём popup с поиском и чекбоксами"""
        self.managers_widget = QWidget()
        self.managers_layout = QVBoxLayout(self.managers_widget)
        self.managers_layout.setSpacing(8)
        self.managers_layout.setContentsMargins(10, 10, 10, 10)

        # Строка поиска
        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText("Поиск по имени или должности...")
        self.search_line.textChanged.connect(self.filter_employees)
        self.search_line.setMinimumHeight(32)
        self.managers_layout.addWidget(self.search_line)

        # Чекбоксы
        self.manager_checkboxes = []
        for emp in self.employees:
            cb = QtWidgets.QCheckBox(f"{emp['full_name']} — {emp['position']}")
            cb.setProperty("employee_id", emp['id'])
            cb.setProperty("employee_name", emp['full_name'])
            cb.setProperty("full_text", f"{emp['full_name']} {emp['position']}".lower())
            cb.stateChanged.connect(self.update_selected_managers_text)
            self.managers_layout.addWidget(cb)
            self.manager_checkboxes.append(cb)

        # Кнопки Выбрать всех / Снять всех
        btn_layout = QtWidgets.QHBoxLayout()
        select_all_btn = QPushButton("Выбрать всех")
        clear_all_btn = QPushButton("Снять выделение")

        select_all_btn.clicked.connect(self.select_all_managers)
        clear_all_btn.clicked.connect(self.clear_all_managers)

        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(clear_all_btn)
        self.managers_layout.addLayout(btn_layout)
        self.managers_layout.addStretch()

        # ScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.managers_widget)
        scroll_area.setMinimumHeight(300)
        scroll_area.setMaximumHeight(300)

        # Popup
        self.popup = QtWidgets.QWidget()
        self.popup.setMinimumWidth(500)
        self.popup.setMaximumWidth(600)
        self.popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.popup.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 8px;
            }
            QLineEdit {
                border: 2px solid #e9ecef;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border: 2px solid #D22730;
                color: #2c3e50;
            }
            QCheckBox {
                font-size: 13px;
                color: #2c3e50;
                padding: 5px 4px;
            }
            QCheckBox::indicator {
                width: 18px; height: 18px;
                border: 2px solid #e0e0e0;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background-color: #D22730;
                border-color: #D22730;
            }
            QPushButton {
                background-color: #1B232A;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0px 12px;
                font-size: 12px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #09131B;
            }
            QPushButton:pressed {
                background-color: #030B12;
            }
            QScrollBar:vertical {
                background: #F5F5F5;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #C1C1C1;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar:horizontal {
                border: none;
                background: #F5F5F5;
                height: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #c1c1c1;
                border-radius: 4px;
                min-width: 20px;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                border: none;
                background: none;
            }
        """)

        popup_layout = QVBoxLayout(self.popup)
        popup_layout.setContentsMargins(8, 8, 8, 8)
        popup_layout.addWidget(scroll_area)

        # Настройка ComboBox
        self.comboManagers.setEditable(True)
        line_edit = self.comboManagers.lineEdit()
        line_edit.setReadOnly(True)
        line_edit.setCursor(Qt.CursorShape.PointingHandCursor)

        self.comboManagers.mousePressEvent = self.show_managers_popup

        self.update_selected_managers_text()

    def filter_employees(self, text):
        """Фильтрация списка сотрудников"""
        text = text.lower().strip()
        for cb in self.manager_checkboxes:
            full_text = cb.property("full_text")
            cb.setVisible(text in full_text if text else True)

    def show_managers_popup(self, event):
        pos = self.comboManagers.mapToGlobal(QtCore.QPoint(0, self.comboManagers.height() + 4))
        self.popup.move(pos)
        self.popup.show()

    def select_all_managers(self):
        for cb in self.manager_checkboxes:
            if cb.isVisible():
                cb.setChecked(True)

    def clear_all_managers(self):
        for cb in self.manager_checkboxes:
            cb.setChecked(False)

    def update_selected_managers_text(self):
        selected = []
        for cb in self.manager_checkboxes:
            if cb.isChecked():
                name = cb.property("employee_name")
                if name:
                    parts = name.split()
                    if len(parts) >= 2:
                        short = f"{parts[0]} {parts[1][0]}."
                        if len(parts) > 2:
                            short += f"{parts[2][0]}."
                        selected.append(short)

        if selected:
            text = f"✓ Выбрано ({len(selected)}): {', '.join(selected[:3])}"
            if len(selected) > 3:
                text += f" и ещё {len(selected) - 3}"
            self.comboManagers.setEditText(text)
        else:
            self.comboManagers.setEditText("▼ Выберите руководителей")

    def load_department_data(self):
        self.lineEditName.setText(self.department_data.get("name", ""))
        self.lineEditNumber.setText(str(self.department_data.get("number", "")))
        self.lineEditPhone.setText(self.department_data.get("phone", ""))

        saved_ids = self.department_data.get("managers", [])
        for cb in self.manager_checkboxes:
            if cb.property("employee_id") in saved_ids:
                cb.setChecked(True)

        self.update_selected_managers_text()

    def save_department(self):
        name = self.lineEditName.text().strip()
        number = self.lineEditNumber.text().strip()
        phone = self.lineEditPhone.text().strip()

        if not name:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Название отдела обязательно!")
            return
        if not number.isdigit():
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Номер отдела должен быть числом!")
            return
        if not phone:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Укажите номер телефона!")
            return

        selected_managers = [cb.property("employee_id") for cb in self.manager_checkboxes if cb.isChecked()]
        selected_names = [cb.property("employee_name") for cb in self.manager_checkboxes if cb.isChecked()]

        department_info = {
            "name": name,
            "number": int(number),
            "phone": phone,
            "managers": selected_managers,
            "managers_names": selected_names
        }

        if self.department_data and "id" in self.department_data:
            department_info["id"] = self.department_data["id"]

        self.department_saved.emit(department_info)
        self.accept()

    def setup_keyboard_navigation(self):
        """Навигация по полям с помощью стрелок ↑ ↓"""
        self.fields = [
            self.lineEditName,
            self.lineEditNumber,
            self.lineEditPhone,
            self.comboManagers,
        ]

        for widget in self.fields:
            if widget is not None:
                widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Обработка стрелок Вверх и Вниз"""
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()

            try:
                current_index = self.fields.index(obj)
            except (ValueError, AttributeError):
                return super().eventFilter(obj, event)

            if key == Qt.Key.Key_Down:
                next_index = (current_index + 1) % len(self.fields)
                next_widget = self.fields[next_index]
                if next_widget:
                    next_widget.setFocus()
                return True

            elif key == Qt.Key.Key_Up:
                prev_index = (current_index - 1) % len(self.fields)
                prev_widget = self.fields[prev_index]
                if prev_widget:
                    prev_widget.setFocus()
                return True

        return super().eventFilter(obj, event)