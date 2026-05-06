from pathlib import Path

from PyQt6 import QtWidgets, QtCore, uic
from PyQt6.QtCore import pyqtSignal, Qt, QEvent
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QWidget, QPushButton, QLineEdit, QMessageBox, QHBoxLayout


class DivisionDialog(QDialog):
    """Диалог добавления/редактирования подразделения"""

    division_saved = pyqtSignal(dict)

    def __init__(self, parent=None, division_data=None, employee_service=None):
        super().__init__(parent)

        self.employee_service = employee_service
        self.division_data = division_data
        self.selected_manager_ids = set()
        self.employees = []

        script_dir = Path(__file__).resolve().parent
        ui_path = script_dir.parent.parent.parent / "ui" / "settings" / "divisions" / "division_dialog.ui"

        if not ui_path.exists():
            raise FileNotFoundError(f"UI файл не найден:\n{ui_path}")

        uic.loadUi(str(ui_path), self)

        self.init_ui()
        self.load_data_from_service()
        self.setup_heads_combo()

        if self.division_data:
            self.load_division_data()

        self.btnSave.clicked.connect(self.save_division)
        self.setup_keyboard_navigation()

    def load_data_from_service(self):
        """Загружает данные через сервис"""
        if self.employee_service:
            self.employees = self.employee_service.get_employees_for_selector()
            print(f"✅ Загружено {len(self.employees)} сотрудников")
        else:
            self.employees = []

    def init_ui(self):
        """Настройка UI"""
        if self.division_data and self.division_data.get('id'):
            self.setWindowTitle("Редактирование подразделения")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Редактирование подразделения")
        else:
            self.setWindowTitle("Добавление подразделения")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Добавление нового подразделения")

    def setup_heads_combo(self):
        """Создаёт popup с поиском и чекбоксами для выбора руководителей"""
        self.heads_widget = QWidget()
        self.heads_layout = QVBoxLayout(self.heads_widget)
        self.heads_layout.setSpacing(8)
        self.heads_layout.setContentsMargins(10, 10, 10, 10)

        # Строка поиска
        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText("Поиск по имени или должности...")
        self.search_line.textChanged.connect(self.filter_employees)
        self.search_line.setMinimumHeight(32)
        self.heads_layout.addWidget(self.search_line)

        # Кнопки Выбрать всех / Снять всех
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Выбрать всех")
        clear_all_btn = QPushButton("Снять выделение")

        select_all_btn.clicked.connect(self.select_all_heads)
        clear_all_btn.clicked.connect(self.clear_all_heads)

        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(clear_all_btn)
        self.heads_layout.addLayout(btn_layout)

        # Контейнер для чекбоксов
        self.checkboxes_container = QWidget()
        self.checkboxes_layout = QVBoxLayout(self.checkboxes_container)
        self.checkboxes_layout.setSpacing(8)
        self.checkboxes_layout.setContentsMargins(0, 0, 0, 0)
        self.heads_layout.addWidget(self.checkboxes_container)

        # Чекбоксы для сотрудников
        self.all_checkboxes = []
        self.checkboxes_by_id = {}

        for emp in self.employees:
            cb_text = f"{emp['full_name']} — {emp['position']}"
            cb = QtWidgets.QCheckBox(cb_text)
            cb.setProperty("employee_id", emp['id'])
            cb.setProperty("employee_name", emp['full_name'])
            cb.setProperty("full_text", f"{emp['full_name']} {emp['position']}".lower())
            cb.toggled.connect(lambda checked, eid=emp['id']: self.on_checkbox_toggled(eid, checked))
            self.checkboxes_by_id[emp['id']] = cb
            self.all_checkboxes.append(cb)
            self.checkboxes_layout.addWidget(cb)

        self.checkboxes_layout.addStretch()

        # ScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.heads_widget)
        scroll_area.setMinimumHeight(300)
        scroll_area.setMaximumHeight(300)

        # Popup окно
        self.popup = QtWidgets.QWidget()
        self.popup.setMinimumWidth(500)
        self.popup.setMaximumWidth(600)
        self.popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.popup.setStyleSheet(self._get_popup_stylesheet())

        popup_layout = QVBoxLayout(self.popup)
        popup_layout.setContentsMargins(8, 8, 8, 8)
        popup_layout.addWidget(scroll_area)

        # Настройка ComboBox
        self.comboHeads.setEditable(True)
        line_edit = self.comboHeads.lineEdit()
        line_edit.setReadOnly(True)
        line_edit.setCursor(Qt.CursorShape.PointingHandCursor)

        self.comboHeads.installEventFilter(self)
        line_edit.installEventFilter(self)

        self.update_selected_heads_text()

    def _get_popup_stylesheet(self) -> str:
        """Возвращает стили для popup"""
        return """
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
        """

    def on_checkbox_toggled(self, employee_id: int, checked: bool):
        """Обработчик изменения состояния чекбокса"""
        if checked:
            self.selected_manager_ids.add(employee_id)
        else:
            self.selected_manager_ids.discard(employee_id)
        self.update_selected_heads_text()

    def filter_employees(self, text):
        """Фильтрация списка сотрудников"""
        text = text.lower().strip()
        for cb in self.all_checkboxes:
            full_text = cb.property("full_text")
            is_visible = text in full_text if text else True
            cb.setVisible(is_visible)

    def eventFilter(self, obj, event):
        """Фильтр событий для навигации по стрелкам и открытия popup"""
        if event.type() == QEvent.Type.MouseButtonPress:
            if obj == self.comboHeads or obj == self.comboHeads.lineEdit():
                pos = self.comboHeads.mapToGlobal(QtCore.QPoint(0, self.comboHeads.height()))
                self.popup.move(pos)
                self.popup.show()
                return True

        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            try:
                current_index = self.fields.index(obj)
            except (ValueError, AttributeError):
                return super().eventFilter(obj, event)

            if key == Qt.Key.Key_Down:
                next_index = (current_index + 1) % len(self.fields)
                if self.fields[next_index]:
                    self.fields[next_index].setFocus()
                return True
            elif key == Qt.Key.Key_Up:
                prev_index = (current_index - 1) % len(self.fields)
                if self.fields[prev_index]:
                    self.fields[prev_index].setFocus()
                return True

        return super().eventFilter(obj, event)

    def select_all_heads(self):
        """Выбрать всех видимых руководителей"""
        for cb in self.all_checkboxes:
            if cb.isVisible():
                cb.setChecked(True)

    def clear_all_heads(self):
        """Снять выделение со всех руководителей"""
        for cb in self.all_checkboxes:
            cb.setChecked(False)

    def update_selected_heads_text(self):
        """Обновление текста в комбобоксе с выбранными руководителями"""
        selected = []
        for emp_id in self.selected_manager_ids:
            cb = self.checkboxes_by_id.get(emp_id)
            if cb and cb.isChecked():
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
            self.comboHeads.setEditText(text)
        else:
            self.comboHeads.setEditText("▼ Выберите руководителей")

    def load_division_data(self):
        """Загрузка данных подразделения для редактирования"""
        self.lineEditName.setText(self.division_data.get("name", ""))
        self.lineEditNumber.setText(str(self.division_data.get("number", "")))
        self.lineEditPhone.setText(self.division_data.get("phone_number", ""))
        self.textEditDescription.setText(self.division_data.get("workshop_code", ""))

        # Устанавливаем выбранных руководителей
        self.selected_manager_ids.clear()
        boss_ids = self.division_data.get("boss_ids", [])
        for emp_id in boss_ids:
            self.selected_manager_ids.add(emp_id)
            cb = self.checkboxes_by_id.get(emp_id)
            if cb:
                cb.setChecked(True)

        self.update_selected_heads_text()

    def get_division_data(self) -> dict:
        """Получение данных из формы"""
        number_text = self.lineEditNumber.text().strip()
        number = int(number_text) if number_text.isdigit() else 0

        boss_string = ','.join(str(hid) for hid in self.selected_manager_ids) if self.selected_manager_ids else ""

        return {
            "id": self.division_data.get('id') if self.division_data else None,
            "name": self.lineEditName.text().strip(),
            "number": number,
            "phone_number": self.lineEditPhone.text().strip(),
            "workshop_code": self.textEditDescription.toPlainText().strip(),
            "boss": boss_string,
        }

    def save_division(self):
        """Сохранение подразделения через сервис"""
        if not self.employee_service:
            QMessageBox.warning(self, "Ошибка", "Сервис не инициализирован")
            return

        division_data = self.get_division_data()

        # Валидация через сервис
        is_valid, error_msg = self.employee_service.validate_division_form(division_data)

        if not is_valid:
            QMessageBox.warning(self, "Ошибка", error_msg)
            return

        # Сохраняем через сервис
        result = self.employee_service.save_division_from_dialog(division_data)

        if result:
            self.division_saved.emit(result)
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось сохранить подразделение")

    def setup_keyboard_navigation(self):
        """Навигация по полям с помощью стрелок ↑ ↓"""
        self.fields = [
            self.lineEditName,
            self.lineEditNumber,
            self.lineEditPhone,
            self.textEditDescription,
            self.comboHeads,
        ]
        for widget in self.fields:
            if widget is not None:
                widget.installEventFilter(self)