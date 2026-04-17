import sys
import os
from pathlib import Path
from PyQt6 import QtWidgets, QtCore, uic
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QWidget, QPushButton, QLineEdit, QLabel, QMessageBox, \
    QHBoxLayout, QComboBox
from PyQt6.QtCore import pyqtSignal, Qt, QEvent, QTimer


class DepartmentDialog(QDialog):
    department_saved = pyqtSignal(dict)

    def __init__(self, parent=None, department_data=None, session=None):
        super().__init__(parent)

        self.session = session
        self.department_data = department_data
        self.employees = []
        self.divisions = []
        self.selected_manager_ids = set()  # Храним выбранные ID руководителей

        script_dir = Path(__file__).resolve().parent
        ui_path = script_dir.parent.parent.parent / "ui" / "settings" / "departments" / "department_dialog.ui"

        print(f"Загрузка UI из: {ui_path}")

        if not ui_path.exists():
            raise FileNotFoundError(f"UI файл не найден:\n{ui_path}")

        uic.loadUi(str(ui_path), self)

        self.init_ui()

        # Загружаем данные из БД
        self.load_real_employees()
        self.load_divisions()

        self.setup_managers_combo()
        self.setup_divisions_combo()

        # Загружаем сохранённых руководителей после создания чекбоксов
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

    def load_divisions(self):
        """Загрузка подразделений из БД"""
        try:
            if self.session:
                from services.employee_service import EmployeeService
                employee_service = EmployeeService(self.session)
                real_divisions = employee_service.get_all_divisions()

                self.divisions = []
                for div in real_divisions:
                    self.divisions.append({
                        "id": div['id'],
                        "name": div['name'],
                        "number": div.get('number', '')
                    })

                print(f"✅ Загружено {len(self.divisions)} подразделений для выбора")
            else:
                self.divisions = self.get_test_divisions()
        except Exception as e:
            print(f"❌ Ошибка загрузки подразделений: {e}")
            self.divisions = self.get_test_divisions()

    def get_test_divisions(self):
        return [
            {"id": 1, "name": "Северное подразделение", "number": 1},
            {"id": 2, "name": "Южное подразделение", "number": 2},
            {"id": 3, "name": "Центральное подразделение", "number": 3},
        ]

    def get_test_employees(self):
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

    def setup_divisions_combo(self):
        self.comboBoxDivision.clear()
        self.comboBoxDivision.addItem("— Выберите подразделение —", None)
        for div in self.divisions:
            display_text = f"{div['name']}"
            if div.get('number'):
                display_text += f" (№{div['number']})"
            self.comboBoxDivision.addItem(display_text, div['id'])

    def setup_managers_combo(self):
        """Создаём popup с поиском и чекбоксами"""
        self.managers_widget = QWidget()
        self.managers_layout = QVBoxLayout(self.managers_widget)
        self.managers_layout.setSpacing(8)
        self.managers_layout.setContentsMargins(10, 10, 10, 10)

        # Строка поиска
        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText("Поиск по имени или должности...")
        self.search_line.textChanged.connect(self.on_search_text_changed)
        self.search_line.setMinimumHeight(32)
        self.managers_layout.addWidget(self.search_line)

        # Кнопки Выбрать всех / Снять всех
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Выбрать всех")
        clear_all_btn = QPushButton("Снять выделение")

        select_all_btn.clicked.connect(self.select_all_managers)
        clear_all_btn.clicked.connect(self.clear_all_managers)

        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(clear_all_btn)
        self.managers_layout.addLayout(btn_layout)

        # Контейнер для чекбоксов
        self.checkboxes_container = QWidget()
        self.checkboxes_layout = QVBoxLayout(self.checkboxes_container)
        self.checkboxes_layout.setSpacing(8)
        self.checkboxes_layout.setContentsMargins(0, 0, 0, 0)
        self.managers_layout.addWidget(self.checkboxes_container)

        print(f"📋 Создаем чекбоксы для {len(self.employees)} сотрудников")

        # Сохраняем все чекбоксы в словарь по ID
        self.checkboxes_by_id = {}
        self.checkboxes_list = []

        for emp in self.employees:
            cb_text = f"{emp['full_name']} — {emp['position']}"
            cb = QtWidgets.QCheckBox(cb_text)
            cb.setProperty("employee_id", emp['id'])
            cb.setProperty("employee_name", emp['full_name'])
            cb.setProperty("full_text", f"{emp['full_name']} {emp['position']}".lower())
            # Подключаем сигнал с сохранением ID
            cb.toggled.connect(lambda checked, eid=emp['id']: self.on_checkbox_toggled(eid, checked))
            self.checkboxes_by_id[emp['id']] = cb
            self.checkboxes_list.append(cb)

        # Добавляем чекбоксы в layout
        for cb in self.checkboxes_list:
            self.checkboxes_layout.addWidget(cb)
        self.checkboxes_layout.addStretch()

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

        self.heads_popup = self.popup

        self.update_selected_managers_text()

        self.comboManagers.installEventFilter(self)
        line_edit.installEventFilter(self)

        print("✅ Popup для выбора руководителей настроен")

    def on_checkbox_toggled(self, employee_id: int, checked: bool):
        """Обработчик изменения состояния чекбокса"""
        if checked:
            self.selected_manager_ids.add(employee_id)
        else:
            self.selected_manager_ids.discard(employee_id)
        self.update_selected_managers_text()

    def update_checkboxes_visibility(self):
        """Обновляет видимость чекбоксов на основе поискового запроса"""
        search_text = self.search_line.text().lower().strip()
        for cb in self.checkboxes_list:
            full_text = cb.property("full_text")
            is_visible = not search_text or search_text in full_text
            cb.setVisible(is_visible)

    def on_search_text_changed(self, text):
        """Обработчик изменения текста поиска"""
        self.update_checkboxes_visibility()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if obj == self.comboManagers or obj == self.comboManagers.lineEdit():
                print("🖱️ Клик по комбобоксу!")
                # Обновляем видимость перед показом
                self.update_checkboxes_visibility()
                pos = self.comboManagers.mapToGlobal(QtCore.QPoint(0, self.comboManagers.height()))
                self.heads_popup.move(pos)
                self.heads_popup.show()
                return True

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

    def select_all_managers(self):
        """Выбрать всех видимых руководителей"""
        for cb in self.checkboxes_list:
            if cb.isVisible():
                cb.setChecked(True)
        self.update_selected_managers_text()

    def clear_all_managers(self):
        """Снять выделение со всех руководителей"""
        for cb in self.checkboxes_list:
            cb.setChecked(False)
        self.update_selected_managers_text()

    def update_selected_managers_text(self):
        """Обновление текста в комбобоксе с выбранными руководителями"""
        selected = []
        for emp_id in self.selected_manager_ids:
            cb = self.checkboxes_by_id.get(emp_id)
            if cb:
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
        """Загрузка данных отдела для редактирования"""
        self.lineEditName.setText(self.department_data.get("name", ""))
        self.lineEditNumber.setText(str(self.department_data.get("number", "")))

        phone = self.department_data.get("phone_number", "") or self.department_data.get("phone", "")
        self.lineEditPhone.setText(phone)

        division_id = self.department_data.get("division_id")
        if division_id:
            index = self.comboBoxDivision.findData(division_id)
            if index >= 0:
                self.comboBoxDivision.setCurrentIndex(index)

        boss_field = self.department_data.get("boss", "")
        saved_ids = []

        if boss_field and isinstance(boss_field, str):
            for part in boss_field.split(','):
                part = part.strip()
                if part and part.isdigit():
                    saved_ids.append(int(part))

        print(f"📋 Загружаем сохраненных руководителей из boss='{boss_field}': {saved_ids}")

        # Устанавливаем выбранных руководителей
        self.selected_manager_ids.clear()
        for emp_id in saved_ids:
            self.selected_manager_ids.add(emp_id)
            cb = self.checkboxes_by_id.get(emp_id)
            if cb:
                cb.setChecked(True)

        self.update_selected_managers_text()

    def save_department(self):
        name = self.lineEditName.text().strip()
        number = self.lineEditNumber.text().strip()
        phone = self.lineEditPhone.text().strip()
        division_id = self.comboBoxDivision.currentData()

        if not name:
            QMessageBox.warning(self, "Ошибка", "Название отдела обязательно!")
            return
        if not number:
            QMessageBox.warning(self, "Ошибка", "Номер отдела обязателен!")
            return
        if not number.isdigit():
            QMessageBox.warning(self, "Ошибка", "Номер отдела должен быть числом!")
            return
        if not phone:
            QMessageBox.warning(self, "Ошибка", "Укажите номер телефона!")
            return
        if not division_id:
            QMessageBox.warning(self, "Ошибка", "Выберите подразделение!")
            return

        selected_managers = list(self.selected_manager_ids)
        selected_names = []
        for emp_id in selected_managers:
            cb = self.checkboxes_by_id.get(emp_id)
            if cb:
                selected_names.append(cb.property("employee_name"))

        boss_string = ','.join(str(hid) for hid in selected_managers) if selected_managers else ""

        print(f"💾 Сохраняем отдел: {name}")
        print(f"   Подразделение ID: {division_id}")
        print(f"   Выбранные руководители (ID): {selected_managers}")
        print(f"   Boss строка: '{boss_string}'")

        department_info = {
            "name": name,
            "number": int(number),
            "phone": phone,
            "division_id": division_id,
            "boss": boss_string,
            "managers": selected_managers,
            "managers_names": selected_names
        }

        if self.department_data and "id" in self.department_data:
            department_info["id"] = self.department_data["id"]

        self.department_saved.emit(department_info)
        self.accept()

    def setup_keyboard_navigation(self):
        self.fields = [
            self.lineEditName,
            self.lineEditNumber,
            self.lineEditPhone,
            self.comboBoxDivision,
            self.comboManagers,
        ]
        for widget in self.fields:
            if widget is not None:
                widget.installEventFilter(self)