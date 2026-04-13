from pathlib import Path

from PyQt6 import QtWidgets, QtCore, uic
from PyQt6.QtCore import pyqtSignal, Qt, QEvent
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QWidget, QPushButton, QLineEdit, QMessageBox


class DivisionDialog(QDialog):
    """Диалог добавления/редактирования подразделения"""

    division_saved = pyqtSignal(dict)  # Сигнал при сохранении подразделения

    def __init__(self, parent=None, division_data=None, session=None):
        super().__init__(parent)

        self.session = session
        self.division_data = division_data
        self.employees = []

        script_dir = Path(__file__).resolve().parent
        ui_path = script_dir.parent.parent.parent / "ui" / "settings" / "divisions" / "division_dialog.ui"

        print(f"Загрузка UI из: {ui_path}")

        if not ui_path.exists():
            raise FileNotFoundError(f"UI файл не найден:\n{ui_path}")

        uic.loadUi(str(ui_path), self)

        self.init_ui()

        # Загружаем реальных сотрудников
        self.load_real_employees()

        self.setup_heads_combo()

        if self.division_data:
            self.load_division_data()

        self.btnSave.clicked.connect(self.save_division)
        self.setup_keyboard_navigation()

    def load_real_employees(self):
        """Загрузка реальных сотрудников из БД"""
        try:
            if self.session:
                from services.employee_service import EmployeeService
                employee_service = EmployeeService(self.session)
                real_employees = employee_service.get_all_employees()

                print(f"🔍 Получено сотрудников из БД: {len(real_employees)}")
                if real_employees:
                    print(f"   Пример первого сотрудника: {real_employees[0]}")

                self.employees = []
                for emp in real_employees:
                    last_name = emp.get('last_name', '')
                    first_name = emp.get('first_name', '')
                    middle_name = emp.get('middle_name', '')

                    full_name = f"{last_name} {first_name}"
                    if middle_name:
                        full_name += f" {middle_name}"

                    position = emp.get('position', 'Сотрудник')
                    if not position:
                        position = 'Сотрудник'

                    self.employees.append({
                        "id": emp['id'],
                        "full_name": full_name,
                        "position": position
                    })

                print(f"✅ Загружено {len(self.employees)} сотрудников для выбора")

                if not self.employees:
                    print("⚠️ Нет сотрудников для отображения, используем тестовые данные")
                    self.employees = self.get_test_employees()
            else:
                print("⚠️ Нет сессии БД, используем тестовые данные")
                self.employees = self.get_test_employees()
        except Exception as e:
            print(f"❌ Ошибка загрузки сотрудников: {e}")
            import traceback
            traceback.print_exc()
            self.employees = self.get_test_employees()

    def get_test_employees(self):
        """Тестовые данные (запасной вариант)"""
        print("📋 Используем тестовые данные сотрудников")
        return [
            {"id": 1, "full_name": "Иванов Иван Иванович", "position": "Директор подразделения"},
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
        """Настройка UI элементов"""
        if self.division_data:
            self.setWindowTitle("Редактирование подразделения")
            self.titleLabel.setText("Редактирование подразделения")
        else:
            self.setWindowTitle("Добавление подразделения")
            self.titleLabel.setText("Добавление нового подразделения")

    def setup_heads_combo(self):
        """Создаём popup с поиском и чекбоксами для выбора руководителей"""
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

        print(f"📋 Создаем чекбоксы для {len(self.employees)} сотрудников")

        # Чекбоксы для сотрудников
        self.head_checkboxes = []
        for emp in self.employees:
            cb_text = f"{emp['full_name']} — {emp['position']}"
            cb = QtWidgets.QCheckBox(cb_text)
            cb.setProperty("employee_id", emp['id'])
            cb.setProperty("employee_name", emp['full_name'])
            cb.setProperty("full_text", f"{emp['full_name']} {emp['position']}".lower())
            cb.stateChanged.connect(self.update_selected_heads_text)
            self.heads_layout.addWidget(cb)
            self.head_checkboxes.append(cb)

        # Кнопки Выбрать всех / Снять всех
        btn_layout = QtWidgets.QHBoxLayout()
        select_all_btn = QPushButton("Выбрать всех")
        clear_all_btn = QPushButton("Снять выделение")

        select_all_btn.clicked.connect(self.select_all_heads)
        clear_all_btn.clicked.connect(self.clear_all_heads)

        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(clear_all_btn)
        self.heads_layout.addLayout(btn_layout)
        self.heads_layout.addStretch()

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
                            padding: 0px 12px;   /* вертикальный padding убрали */
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
        self.comboHeads.setEditable(True)
        line_edit = self.comboHeads.lineEdit()
        line_edit.setReadOnly(True)
        line_edit.setCursor(Qt.CursorShape.PointingHandCursor)

        # Сохраняем ссылку на popup
        self.heads_popup = self.popup

        self.update_selected_heads_text()

        # Устанавливаем фильтр событий на комбобокс и его lineEdit
        self.comboHeads.installEventFilter(self)
        line_edit.installEventFilter(self)

        print("✅ Popup для выбора руководителей настроен")

    def eventFilter(self, obj, event):
        """Фильтр событий для навигации по стрелкам и открытия popup"""
        # Открываем popup при клике на комбобокс или его lineEdit
        if event.type() == QEvent.Type.MouseButtonPress:
            if obj == self.comboHeads or obj == self.comboHeads.lineEdit():
                print("🖱️ Клик по комбобоксу!")
                # Позиционируем popup под комбобоксом
                pos = self.comboHeads.mapToGlobal(QtCore.QPoint(0, self.comboHeads.height()))
                self.heads_popup.move(pos)
                self.heads_popup.show()
                return True

        # Навигация по стрелкам
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

    def filter_employees(self, text):
        """Фильтрация списка сотрудников"""
        text = text.lower().strip()
        visible_count = 0
        for cb in self.head_checkboxes:
            full_text = cb.property("full_text")
            is_visible = text in full_text if text else True
            cb.setVisible(is_visible)
            if is_visible:
                visible_count += 1

    def select_all_heads(self):
        """Выбрать всех видимых руководителей"""
        for cb in self.head_checkboxes:
            if cb.isVisible():
                cb.setChecked(True)

    def clear_all_heads(self):
        """Снять выделение со всех руководителей"""
        for cb in self.head_checkboxes:
            cb.setChecked(False)

    def update_selected_heads_text(self):
        """Обновление текста в комбобоксе с выбранными руководителями"""
        selected = []
        for cb in self.head_checkboxes:
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
            self.comboHeads.setEditText(text)
        else:
            self.comboHeads.setEditText("▼ Выберите руководителей")

    def load_division_data(self):
        """Загрузка данных подразделения для редактирования"""
        self.lineEditName.setText(self.division_data.get("name", ""))
        self.lineEditNumber.setText(str(self.division_data.get("number", "")))
        self.lineEditPhone.setText(self.division_data.get("phone", ""))
        self.textEditDescription.setText(self.division_data.get("description", ""))

        saved_ids = self.division_data.get("heads", [])
        print(f"📋 Загружаем сохраненных руководителей: {saved_ids}")

        selected_count = 0
        for cb in self.head_checkboxes:
            if cb.property("employee_id") in saved_ids:
                cb.setChecked(True)
                selected_count += 1
        print(f"✅ Выбрано {selected_count} руководителей из сохраненных")

        self.update_selected_heads_text()

    def save_division(self):
        """Сохранение подразделения"""
        name = self.lineEditName.text().strip()
        number = self.lineEditNumber.text().strip()
        phone = self.lineEditPhone.text().strip()
        description = self.textEditDescription.toPlainText().strip()
        workshop_code = getattr(self, 'lineEditWorkshopCode', None)
        workshop_code_value = workshop_code.text().strip() if workshop_code else ""

        # Валидация
        if not name:
            QMessageBox.warning(self, "Ошибка", "Название подразделения обязательно!")
            return

        if not number:
            QMessageBox.warning(self, "Ошибка", "Номер подразделения обязателен!")
            return

        if not number.isdigit():
            QMessageBox.warning(self, "Ошибка", "Номер подразделения должен быть числом!")
            return

        if not phone:
            QMessageBox.warning(self, "Ошибка", "Укажите номер телефона!")
            return

        selected_heads = [cb.property("employee_id") for cb in self.head_checkboxes if cb.isChecked()]
        selected_names = [cb.property("employee_name") for cb in self.head_checkboxes if cb.isChecked()]

        print(f"💾 Сохраняем подразделение: {name}")
        print(f"   Выбранные руководители (ID): {selected_heads}")
        print(f"   Выбранные руководители (имена): {selected_names}")

        division_info = {
            "name": name,
            "number": int(number),
            "phone_number": phone,  # ← ИСПРАВЛЕНО: было 'phone', стало 'phone_number'
            "description": description,
            "workshop_code": workshop_code_value,
            "heads": selected_heads,
            "heads_names": selected_names,
            "boss": ", ".join(selected_names) if selected_names else ""
        }

        if self.division_data and "id" in self.division_data:
            division_info["id"] = self.division_data["id"]

        self.division_saved.emit(division_info)
        self.accept()

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