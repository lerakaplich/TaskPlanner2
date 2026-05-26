# windows/projects/base_project_dialog.py

import os
import sys
from typing import List, Dict, Optional
from PyQt6 import uic
from PyQt6.QtCore import QDate, pyqtSignal, Qt
from PyQt6.QtWidgets import QDialog, QMessageBox, QComboBox, QCheckBox, QVBoxLayout, QWidget, QLabel

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class BaseProjectDialog(QDialog):
    """Базовый класс для диалогов создания и редактирования проектов"""

    columns_changed = pyqtSignal(dict)

    def __init__(self, parent=None, title="Проект", project_data=None, service=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "ui", "projects"
        )
        uic.loadUi(os.path.join(ui_path, "project_creation_dialog.ui"), self)

        self.service = service
        self.project_data = project_data or {}
        self.participants = []
        self.admins = []
        self.all_columns = []  # Все доступные канбан-колонки
        self.column_checkboxes = {}  # Словарь чекбоксов: col_key -> checkbox
        self.selected_columns_data = []  # Выбранные колонки

        # Настройка UI
        self.setup_base_ui()
        self.connect_signals()
        self.setup_manager_selector()
        self.hide_field_checkboxes()  # Скрываем чекбоксы полей проекта
        self.load_columns()

        # Загружаем данные проекта если есть
        if project_data:
            self.load_project_data()

    def connect_signals(self):
        """Подключает сигналы"""
        self.participantsBtn.clicked.connect(self.select_participants)
        self.adminsBtn.clicked.connect(self.select_admins)

    def setup_base_ui(self):
        """Базовая настройка UI"""
        current_date = QDate.currentDate().toString("dd.MM.yyyy")
        self.dateLabel.setText(f"Создан: {current_date}")
        self.createBtn.setText("Создать проект")

        # Переименовываем GroupBox для колонок
        if hasattr(self, 'columnsGroupBox'):
            self.columnsGroupBox.setTitle("Выбор канбан-колонок для проекта")

    def hide_field_checkboxes(self):
        """Скрывает ненужные чекбоксы полей проекта"""
        field_checkboxes = [
            'colNameCheckbox', 'colDescriptionCheckbox', 'colStatusCheckbox',
            'colCreatedDateCheckbox', 'colDeadlineCheckbox',
            'colParticipantsCheckbox', 'colProgressCheckbox'
        ]
        for cb_name in field_checkboxes:
            if hasattr(self, cb_name):
                getattr(self, cb_name).hide()

    def load_columns(self):
        """Загружает доступные канбан-колонки и создает чекбоксы"""
        if not self.service:
            return

        # Получаем все доступные колонки
        self.all_columns = self.service.get_template_columns_for_selector()

        if not hasattr(self, 'columnsGroupBox'):
            return

        # Получаем layout внутри GroupBox
        columns_layout = self.columnsGroupBox.layout()
        if columns_layout is None:
            columns_layout = QVBoxLayout(self.columnsGroupBox)
            self.columnsGroupBox.setLayout(columns_layout)

        # Удаляем старые динамически созданные чекбоксы колонок
        for checkbox in self.column_checkboxes.values():
            if checkbox and checkbox.parent():
                checkbox.deleteLater()
        self.column_checkboxes.clear()

        # Создаем новые чекбоксы для каждой колонки
        for col in self.all_columns:
            col_id = col.get('id')
            col_name = col.get('name', 'Без названия')
            col_key = col.get('col_key', col_name.lower().replace(' ', '_'))
            # Красный цвет для всех чекбоксов как в UI
            col_color = "#D22730"

            checkbox = QCheckBox(col_name)
            checkbox.setProperty('col_id', col_id)
            checkbox.setProperty('col_key', col_key)
            checkbox.setProperty('col_data', col)
            checkbox.setChecked(False)

            # Стиль с красным цветом как в UI
            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    font-size: 13px;
                    color: #1B232A;
                    padding: 5px;
                    spacing: 8px;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border: 2px solid #1B232A;
                    border-radius: 4px;
                    background-color: white;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {col_color};
                    border: 2px solid {col_color};
                }}
                QCheckBox::indicator:hover {{
                    border-color: #D22730;
                }}
            """)

            checkbox.stateChanged.connect(lambda checked, key=col_key: self._on_column_checkbox_changed(key, checked))
            self.column_checkboxes[col_key] = checkbox
            columns_layout.addWidget(checkbox)

        # Добавляем растяжку в конец
        columns_layout.addStretch()

    def _on_column_checkbox_changed(self, col_key: str, state):
        """Обработчик изменения состояния чекбокса колонки"""
        # Находим колонку по ключу
        col = None
        for c in self.all_columns:
            if c.get('col_key', c.get('name', '').lower().replace(' ', '_')) == col_key:
                col = c
                break

        if not col:
            return

        if state == Qt.CheckState.Checked.value:
            # Добавляем колонку в список выбранных
            if col not in self.selected_columns_data:
                self.selected_columns_data.append(col)
        else:
            # Удаляем колонку из списка выбранных
            if col in self.selected_columns_data:
                self.selected_columns_data.remove(col)

    def get_selected_column_keys(self) -> List[str]:
        """Возвращает список ключей выбранных колонок"""
        return [col.get('col_key', col.get('name', '').lower().replace(' ', '_'))
                for col in self.selected_columns_data]

    def setup_manager_selector(self):
        """Настройка комбобокса куратора"""
        combo = self._get_manager_combo()
        if combo is None:
            return

        combo.clear()
        combo.addItem("Выберите куратора", None)

        if self.service:
            managers = self.service.load_employees_for_manager_combo()
            for manager in managers:
                combo.addItem(manager['display_name'], manager['id'])
            print(f"✅ Загружено {len(managers)} сотрудников в комбобокс куратора")

    def _get_manager_combo(self) -> Optional[QComboBox]:
        """Возвращает комбобокс куратора"""
        if hasattr(self, 'comboManager'):
            return self.comboManager
        elif hasattr(self, 'comboManagers'):
            return self.comboManagers
        return None

    def get_manager_id(self) -> Optional[int]:
        """Возвращает ID выбранного куратора"""
        combo = self._get_manager_combo()
        if combo:
            return combo.currentData()
        return None

    def get_manager_name(self) -> Optional[str]:
        """Возвращает имя выбранного куратора"""
        combo = self._get_manager_combo()
        if combo:
            return combo.currentText()
        return None

    def select_participants(self):
        try:
            from windows.projects.employee_selector import EmployeeSelectorDialog

            dialog = EmployeeSelectorDialog(self, service=self.service, mode="participants")

            if self.participants:
                preselected_ids = [p.get('id') if isinstance(p, dict) else p for p in self.participants]
                dialog.set_preselected(preselected_ids)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.participants = dialog.get_selected_employees()
                self.update_participants_button_text()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при выборе участников: {e}")

    def select_admins(self):
        try:
            from windows.projects.employee_selector import EmployeeSelectorDialog

            dialog = EmployeeSelectorDialog(self, service=self.service, mode="admins")

            if self.admins:
                preselected_ids = [a.get('id') if isinstance(a, dict) else a for a in self.admins]
                dialog.set_preselected(preselected_ids)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.admins = dialog.get_selected_employees()
                self.update_admins_button_text()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при выборе администраторов: {e}")

    def update_participants_button_text(self):
        """Обновить текст на кнопке участников"""
        count = len(self.participants)
        if count == 0:
            self.participantsBtn.setText("Выбрать участников")
        elif count == 1:
            emp = self.participants[0]
            if isinstance(emp, dict) and self.service:
                name = self.service.get_employee_display_name(emp['id'])
                self.participantsBtn.setText(f"Участник: {name}")
            else:
                self.participantsBtn.setText(f"Участник: 1 чел.")
        else:
            self.participantsBtn.setText(f"Участники ({count} чел.)")

    def update_admins_button_text(self):
        """Обновить текст на кнопке администраторов"""
        count = len(self.admins)
        if count == 0:
            self.adminsBtn.setText("Выбрать администраторов")
        elif count == 1:
            emp = self.admins[0]
            if isinstance(emp, dict) and self.service:
                name = self.service.get_employee_display_name(emp['id'])
                self.adminsBtn.setText(f"Администратор: {name}")
            else:
                self.adminsBtn.setText(f"Администратор: 1 чел.")
        else:
            self.adminsBtn.setText(f"Администраторы ({count} чел.)")

    def load_project_data(self):
        """Загрузка данных проекта"""
        self.nameInput.setText(self.project_data.get('name', ''))
        self.descInput.setPlainText(self.project_data.get('description', ''))

        is_active = self.project_data.get('is_active', True)
        if isinstance(is_active, str):
            is_active = is_active.lower() == 'true'
        self.activeCheckbox.setChecked(is_active)

        # Устанавливаем куратора
        manager_id = self.project_data.get('manager_id')
        if manager_id:
            combo = self._get_manager_combo()
            if combo:
                for i in range(combo.count()):
                    if combo.itemData(i) == manager_id:
                        combo.setCurrentIndex(i)
                        break

        # Загружаем выбранные канбан-колонки
        self.selected_columns_data = []
        selected_keys = []

        if 'selected_columns_data' in self.project_data and self.project_data['selected_columns_data']:
            self.selected_columns_data = self.project_data['selected_columns_data']
            selected_keys = [col.get('col_key', col.get('name', '').lower().replace(' ', '_'))
                             for col in self.selected_columns_data]
        elif self.project_data.get('selected_columns'):
            selected_keys = self.project_data.get('selected_columns', [])
            # Восстанавливаем данные колонок из ключей
            self._restore_columns_from_keys(selected_keys)

        # Устанавливаем состояние чекбоксов
        for col_key, checkbox in self.column_checkboxes.items():
            checkbox.setChecked(col_key in selected_keys)

        # Загружаем участников и администраторов
        self._load_participants_and_admins()

    def _restore_columns_from_keys(self, column_keys: List[str]):
        """Восстанавливает выбранные колонки из ключей"""
        if not self.service or not column_keys:
            return

        all_columns = self.service.get_template_columns_for_selector()
        self.selected_columns_data = []
        for col in all_columns:
            col_key = col.get('col_key', col.get('name', '').lower().replace(' ', '_'))
            if col_key in column_keys:
                self.selected_columns_data.append(col)

    def _load_participants_and_admins(self):
        """Загрузка участников и администраторов через сервис"""
        member_ids = []
        admin_ids = []

        if hasattr(self.project_data, 'member_ids'):
            member_ids = self.project_data.member_ids or []
            admin_ids = self.project_data.admin_ids or []
        else:
            member_ids = self.project_data.get('member_ids', [])
            admin_ids = self.project_data.get('admin_ids', [])

        if member_ids and self.service:
            # Загружаем через сервис
            employees = self.service.load_employees_by_ids(member_ids)
            self.participants = employees
            self.admins = [emp for emp in employees if emp['id'] in admin_ids]
        else:
            # Формат из старых данных
            participants_data = self.project_data.get('participants', [])
            self.participants = self._normalize_employee_data(participants_data)
            admins_data = self.project_data.get('admins', [])
            self.admins = self._normalize_employee_data(admins_data)

        self.update_participants_button_text()
        self.update_admins_button_text()

    def _normalize_employee_data(self, data):
        """Приведение данных сотрудников к единому формату"""
        if not data:
            return []
        if isinstance(data, str):
            ids = [int(id.strip()) for id in data.split(',') if id.strip()]
            return [{'id': emp_id, 'last_name': f"User{emp_id}", 'first_name': f"User{emp_id}"} for emp_id in ids]
        if isinstance(data, list):
            normalized = []
            for item in data:
                if isinstance(item, dict):
                    if 'id' in item:
                        if 'first_name' not in item:
                            item['first_name'] = f"User{item['id']}"
                        if 'last_name' not in item:
                            item['last_name'] = f"LastName{item['id']}"
                        normalized.append(item)
                elif isinstance(item, int):
                    normalized.append({'id': item, 'first_name': f"User{item}", 'last_name': f"LastName{item}"})
            return normalized
        return []

    def get_project_data(self):
        """Получить данные нового проекта"""
        participants_ids = [str(p.get('id', '')) if isinstance(p, dict) else str(p) for p in self.participants]
        admins_ids = [str(a.get('id', '')) if isinstance(a, dict) else str(a) for a in self.admins]

        data = {
            'name': self.nameInput.text(),
            'description': self.descInput.toPlainText(),
            'participants_ids': ','.join(participants_ids) if participants_ids else '',
            'participants': self.participants,
            'admins_ids': ','.join(admins_ids) if admins_ids else '',
            'admins': self.admins,
            'is_active': self.activeCheckbox.isChecked(),
            'created_date': QDate.currentDate().toString("dd.MM.yyyy"),
            'updated_date': QDate.currentDate().toString("dd.MM.yyyy"),
            'selected_columns_data': self.selected_columns_data,  # Канбан-колонки для проекта
            'selected_columns': self.get_selected_column_keys(),
            'manager_id': self.get_manager_id(),
        }

        # Если это редактирование, добавляем ID
        if self.project_data and self.project_data.get('id'):
            data['id'] = self.project_data.get('id')

        return data

    def validate_input(self):
        """Проверка введенных данных"""
        if not self.nameInput.text().strip():
            QMessageBox.warning(self, "Предупреждение", "Введите название проекта")
            return False

        if not self.selected_columns_data:
            QMessageBox.warning(self, "Предупреждение", "Выберите хотя бы одну колонку для отображения в проекте!")
            return False

        return True

    def _create_employee_stub(self, emp_id: int) -> Dict:
        """Создает заглушку для сотрудника"""
        return {
            'id': emp_id,
            'last_name': f"User{emp_id}",
            'first_name': f"User{emp_id}",
            'middle_name': '',
            'position': 'Сотрудник'
        }