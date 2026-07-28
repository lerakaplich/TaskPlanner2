# windows/settings/departments/department_dialog.py

import os
from pathlib import Path
from typing import Optional

from PyQt6 import QtWidgets, QtCore, uic
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QWidget, QPushButton, QLineEdit, QMessageBox, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt, QEvent


class DepartmentDialog(QDialog):
    department_saved = pyqtSignal(dict)

    def __init__(self, parent=None, department_data=None, employee_service=None,
                 read_only=False, permission_service=None):
        super().__init__(parent)

        self.permission_service = permission_service
        self.employee_service = employee_service
        self.department_data = department_data
        self.read_only = read_only
        self.selected_manager_ids = set()
        self.employees = []
        self.divisions = []
        self.editable_division_ids = set()
        self.editable_division_ids = set()
        self.editable_division_ids = set()  # <-- НОВОЕ
        self.checkboxes_by_id = {}
        self.checkboxes_list = []
        self.popup = None
        self.fields = []

        # Если есть permission_service, проверяем реальные права
        if self.permission_service and department_data:
            actual_read_only = not self._can_edit_this_department(department_data)
            self.read_only = read_only or actual_read_only

        # Определяем путь к UI
        script_dir = Path(__file__).resolve().parent
        ui_path = script_dir.parent.parent.parent / "ui" / "settings" / "departments" / "department_dialog.ui"

        if not ui_path.exists():
            raise FileNotFoundError(f"UI файл не найден:\n{ui_path}")

        uic.loadUi(str(ui_path), self)

        self.init_ui()

        # Загружаем данные через сервис
        self.load_data_from_service()
        self.setup_managers_combo()

        # Загружаем данные для редактирования
        if self.department_data:
            self.load_department_data()

        # Настраиваем комбобокс подразделений ПОСЛЕ загрузки данных
        self.setup_divisions_combo()  # <-- ПЕРЕНЕСТИ СЮДА

        self.btnSave.clicked.connect(self.save_department)
        self.setup_keyboard_navigation()

        # Применяем режим только просмотра
        self._apply_read_only_state()

    def _get_user_division_id(self) -> Optional[int]:
        """
        Возвращает ID подразделения, где пользователь является начальником.
        Если пользователь не является начальником подразделения, возвращает None.
        """
        if not self.permission_service or not self.employee_service:
            return None

        user_id = self.permission_service.user_id
        combined = self.permission_service.get_combined_role()

        # Если пользователь - начальник подразделения
        if combined.is_division_head:
            # Получаем все подразделения
            divisions = self.employee_service.get_all_divisions()
            for div in divisions:
                boss_ids = div.get('boss_ids', [])
                if user_id in boss_ids:
                    return div.get('id')

        return None

    def _can_edit_this_department(self, department_data: dict) -> bool:
        """Проверяет, может ли пользователь редактировать этот отдел"""
        if not self.permission_service:
            return not self.read_only

        user_id = self.permission_service.user_id
        combined = self.permission_service.get_combined_role()

        if combined.is_super_admin or combined.is_admin:
            return True

        if combined.is_department_head:
            boss_ids = department_data.get('boss_ids', [])
            return user_id in boss_ids

        if combined.is_division_head:
            if not self.employee_service:
                return False
            divisions = self.employee_service.get_all_divisions()
            user_division_ids = []
            for div in divisions:
                boss_ids = div.get('boss_ids', [])
                if user_id in boss_ids:
                    user_division_ids.append(div.get('id'))
            department_division_id = department_data.get('division_id')
            return department_division_id in user_division_ids

        return False

    def _apply_read_only_state(self):
        """Применяет состояние только просмотра к диалогу"""
        if self.read_only:
            if hasattr(self, 'btnSave'):
                self.btnSave.setVisible(False)
                self.btnSave.hide()
            self._set_all_fields_read_only()
            if hasattr(self, 'comboBoxDivision'):
                self.comboBoxDivision.setEnabled(False)
            if hasattr(self, 'comboManagers'):
                self.comboManagers.setEnabled(False)

    def _set_all_fields_read_only(self):
        """Блокирует все поля ввода"""
        read_only_fields = [
            self.lineEditName,
            self.lineEditNumber,
            self.lineEditPhone,
        ]

        for field in read_only_fields:
            if field:
                if hasattr(field, 'setReadOnly'):
                    field.setReadOnly(True)
                elif hasattr(field, 'setEnabled'):
                    field.setEnabled(False)

    def load_data_from_service(self):
        """Загружает данные через сервис"""
        if self.employee_service:
            # Получаем ВСЕ подразделения с boss_ids
            all_divisions = self.employee_service.get_divisions_for_selector()

            for div in all_divisions:
                print(f"📋 Подразделение: {div.get('name')}, boss_ids: {div.get('boss_ids', [])}")

            # Определяем, какие подразделения может редактировать пользователь
            self.editable_division_ids = self._get_editable_division_ids(all_divisions)

            # Фильтруем подразделения для отображения в комбобоксе
            if self.permission_service:
                combined = self.permission_service.get_combined_role()

                # Для начальника подразделения - ТОЛЬКО его подразделения
                if combined.is_division_head:
                    self.divisions = [div for div in all_divisions
                                      if div.get('id') in self.editable_division_ids]
                elif combined.is_super_admin or combined.is_admin or combined.is_org_head:
                    self.divisions = all_divisions
                else:
                    self.divisions = [div for div in all_divisions
                                      if div.get('id') in self.editable_division_ids]
            else:
                self.divisions = all_divisions

            self.employees = self.employee_service.get_all_employees_for_selector()

            print(f"✅ Загружено {len(self.employees)} сотрудников, {len(self.divisions)} подразделений")
            print(f"   Редактируемые подразделения: {self.editable_division_ids}")
        else:
            self.employees = []
            self.divisions = []
            self.editable_division_ids = set()

    def _get_editable_division_ids(self, all_divisions: list = None) -> set:
        print(f"🔍 _get_editable_division_ids: ВХОД")
        if not self.permission_service:
            print(f"   permission_service нет, возвращаем все")
            return {div.get('id') for div in (all_divisions or self.divisions) if div.get('id')}

        user_id = self.permission_service.user_id
        combined = self.permission_service.get_combined_role()

        print(f"   user_id={user_id}")
        print(f"   combined.is_super_admin={combined.is_super_admin}")
        print(f"   combined.is_admin={combined.is_admin}")
        print(f"   combined.is_org_head={combined.is_org_head}")
        print(f"   combined.is_division_head={combined.is_division_head}")
        print(f"   combined.is_department_head={combined.is_department_head}")

        # Суперадмин и админ видят все подразделения
        if combined.is_super_admin or combined.is_admin:
            return {div.get('id') for div in (all_divisions or self.divisions) if div.get('id')}

        # Начальник организации видит все
        if combined.is_org_head:
            return {div.get('id') for div in (all_divisions or self.divisions) if div.get('id')}

        # ===== НАЧАЛЬНИК ПОДРАЗДЕЛЕНИЯ - ТОЛЬКО СВОЁ =====
        if combined.is_division_head:
            print(f"   ✅ ПОПАЛИ В ВЕТКУ is_division_head")
            divisions_to_check = all_divisions or self.divisions
            user_division_ids = set()
            for div in divisions_to_check:
                boss_ids = div.get('boss_ids', [])
                print(f"   Проверка div {div.get('id')}: boss_ids={boss_ids}, user_id={user_id}")
                if user_id in boss_ids:
                    user_division_ids.add(div.get('id'))
            print(f"🔍 Начальник подразделения: доступны подразделения {user_division_ids}")
            return user_division_ids

        print(f"   ❌ НЕ ПОПАЛИ НИ В ОДНУ ВЕТКУ, возвращаем пустой set")
        return set()

    def init_ui(self):
        """Настройка UI"""
        if self.read_only:
            self.setWindowTitle("Просмотр отдела")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Просмотр отдела")
        elif self.department_data and self.department_data.get('id'):
            self.setWindowTitle("Редактирование отдела")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Редактирование отдела")
        else:
            self.setWindowTitle("Добавление отдела")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Добавление нового отдела")

    def setup_divisions_combo(self):
        """Настройка комбобокса подразделений с учётом прав"""
        self.comboBoxDivision.clear()

        # Если пользователь - начальник подразделения, показываем только его подразделение
        user_division_id = self._get_user_division_id()

        if user_division_id is not None:
            user_division = None
            for div in self.divisions:
                if div.get('id') == user_division_id:
                    user_division = div
                    break

            if user_division:
                display_text = user_division.get('display_name', user_division.get('name', 'Без названия'))
                self.comboBoxDivision.addItem(display_text, user_division_id)
                self.comboBoxDivision.setEnabled(False)  # Блокируем выбор
                return

        # Стандартное поведение для остальных пользователей
        self.comboBoxDivision.addItem("— Выберите подразделение —", None)

        for div in self.divisions:
            div_id = div.get('id')
            if div_id is None:
                continue

            # Проверяем, может ли пользователь редактировать это подразделение
            can_edit = div_id in self.editable_division_ids if self.editable_division_ids else True

            if self.permission_service:
                combined = self.permission_service.get_combined_role()
                if combined.is_division_head:
                    if not can_edit:
                        continue
                elif not combined.is_super_admin and not combined.is_admin and not combined.is_org_head:
                    if not can_edit:
                        continue

            display_text = div.get('display_name', div.get('name', 'Без названия'))
            self.comboBoxDivision.addItem(display_text, div_id)

        # Если редактируем существующий отдел и его подразделение не в списке
        if self.department_data and self.department_data.get('id'):
            current_division_id = self.department_data.get('division_id')
            if current_division_id and current_division_id not in self.editable_division_ids:
                for div in self.divisions:
                    if div.get('id') == current_division_id:
                        display_text = div.get('display_name', div.get('name', 'Без названия'))
                        self.comboBoxDivision.addItem(f"{display_text} (текущее)", current_division_id)
                        break

        if self.read_only:
            self.comboBoxDivision.setEnabled(False)

    def setup_managers_combo(self):
        """Создаёт popup с поиском и чекбоксами для выбора руководителей"""
        self.managers_widget = QWidget()
        self.managers_layout = QVBoxLayout(self.managers_widget)
        self.managers_layout.setSpacing(8)
        self.managers_layout.setContentsMargins(10, 10, 10, 10)

        # Строка поиска
        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText("Поиск по имени или должности...")
        self.search_line.textChanged.connect(self.on_search_text_changed)
        self.search_line.setMinimumHeight(32)

        if self.read_only:
            self.search_line.setEnabled(False)

        self.managers_layout.addWidget(self.search_line)

        # Кнопки Выбрать всех / Снять всех
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Выбрать всех")
        clear_all_btn = QPushButton("Снять выделение")

        if self.read_only:
            select_all_btn.setVisible(False)
            clear_all_btn.setVisible(False)

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

        # Сохраняем все чекбоксы
        self.checkboxes_by_id = {}
        self.checkboxes_list = []

        for emp in self.employees:
            cb_text = f"{emp['full_name']} — {emp['position']}"
            cb = QtWidgets.QCheckBox(cb_text)
            cb.setProperty("employee_id", emp['id'])
            cb.setProperty("employee_name", emp['full_name'])
            cb.setProperty("full_text", f"{emp['full_name']} {emp['position']}".lower())

            if self.read_only:
                cb.setEnabled(False)

            cb.toggled.connect(lambda checked, eid=emp['id']: self.on_checkbox_toggled(eid, checked))
            self.checkboxes_by_id[emp['id']] = cb
            self.checkboxes_list.append(cb)
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
        self.popup.setStyleSheet(self._get_popup_stylesheet())

        popup_layout = QVBoxLayout(self.popup)
        popup_layout.setContentsMargins(8, 8, 8, 8)
        popup_layout.addWidget(scroll_area)

        # Настройка ComboBox
        self.comboManagers.setEditable(True)
        line_edit = self.comboManagers.lineEdit()
        line_edit.setReadOnly(True)
        line_edit.setCursor(Qt.CursorShape.PointingHandCursor)

        if self.read_only:
            self.comboManagers.setEnabled(False)

        self.comboManagers.installEventFilter(self)
        line_edit.installEventFilter(self)

        self.update_selected_managers_text()

    def save_department(self):
        """Сохранение отдела"""
        if self.read_only:
            QMessageBox.information(self, "Информация", "В режиме просмотра редактирование недоступно")
            return

        if not self.employee_service:
            QMessageBox.warning(self, "Ошибка", "Сервис не инициализирован")
            return

        department_data = self.get_department_data()

        # Для начальника подразделения - принудительно устанавливаем его подразделение
        if self.permission_service:
            combined = self.permission_service.get_combined_role()
            if combined.is_division_head:
                user_division_id = self._get_user_division_id()
                if user_division_id is not None:
                    department_data['division_id'] = user_division_id

        division_id = department_data.get('division_id')

        # Проверка прав
        if self.permission_service:
            combined = self.permission_service.get_combined_role()
            if combined.is_division_head:
                # Проверяем, что подразделение принадлежит пользователю
                if division_id not in self.editable_division_ids:
                    QMessageBox.warning(self, "Ошибка", "У вас нет прав на создание отдела в этом подразделении")
                    return
            elif division_id and self.editable_division_ids:
                if division_id not in self.editable_division_ids:
                    QMessageBox.warning(self, "Ошибка", "У вас нет прав на создание отдела в этом подразделении")
                    return

        is_valid, error_msg = self.employee_service.validate_department_form(department_data)

        if not is_valid:
            QMessageBox.warning(self, "Ошибка", error_msg)
            return

        result = self.employee_service.save_department_from_dialog(department_data)

        if result:
            self.department_saved.emit(result)
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось сохранить отдел")

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
                self.update_checkboxes_visibility()
                pos = self.comboManagers.mapToGlobal(QtCore.QPoint(0, self.comboManagers.height()))
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
        self.lineEditPhone.setText(self.department_data.get("phone_number", ""))

        division_id = self.department_data.get("division_id")
        if division_id:
            index = self.comboBoxDivision.findData(division_id)
            if index >= 0:
                self.comboBoxDivision.setCurrentIndex(index)
        else:
            # Если отдел новый и пользователь - начальник подразделения
            user_division_id = self._get_user_division_id()
            if user_division_id is not None:
                # Проверяем, есть ли подразделение в комбобоксе
                index = self.comboBoxDivision.findData(user_division_id)
                if index >= 0:
                    self.comboBoxDivision.setCurrentIndex(index)

        # Устанавливаем выбранных руководителей
        self.selected_manager_ids.clear()
        boss_ids = self.department_data.get("boss_ids", [])
        for emp_id in boss_ids:
            self.selected_manager_ids.add(emp_id)
            cb = self.checkboxes_by_id.get(emp_id)
            if cb:
                cb.setChecked(True)

        self.update_selected_managers_text()

    def get_department_data(self) -> dict:
        """Получение данных из формы"""
        number_text = self.lineEditNumber.text().strip()
        number = int(number_text) if number_text.isdigit() else 0

        boss_string = ','.join(str(hid) for hid in self.selected_manager_ids) if self.selected_manager_ids else ""

        result = {
            "id": self.department_data.get('id') if self.department_data else None,
            "name": self.lineEditName.text().strip(),
            "number": number,
            "phone_number": self.lineEditPhone.text().strip(),
            "division_id": self.comboBoxDivision.currentData(),
            "boss": boss_string,
        }
        return result

    def setup_keyboard_navigation(self):
        """Настройка перехода между полями"""
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