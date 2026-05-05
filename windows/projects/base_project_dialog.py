# windows/projects/base_project_dialog.py

import os
import sys
from typing import List, Dict, Optional
from PyQt6 import uic
from PyQt6.QtCore import QDate, pyqtSignal, Qt
from PyQt6.QtWidgets import QDialog, QMessageBox, QComboBox

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

        # Хранение выбранных колонок
        self.selected_columns_data = []
        self.selected_columns_keys = []

        # Загружаем шаблонные колонки через сервис
        self.template_columns = self._load_template_columns()

        # Настройка UI
        self.setup_base_ui()
        self.connect_signals()
        self.setup_manager_selector()

        # Загружаем данные проекта если есть
        if project_data:
            self.load_project_data()

        # Скрываем старый GroupBox с чекбоксами (если есть)
        if hasattr(self, 'columnsGroupBox'):
            self.columnsGroupBox.hide()

    def _load_template_columns(self) -> List[Dict]:
        """Загружает шаблонные колонки через сервис"""
        if self.service:
            return self.service.load_template_columns()
        return []

    def connect_signals(self):
        """Подключает сигналы"""
        self.participantsBtn.clicked.connect(self.select_participants)
        self.adminsBtn.clicked.connect(self.select_admins)

        if hasattr(self, 'columnBtn'):
            self.columnBtn.clicked.connect(self.select_columns)
            self.columnBtn.setCursor(Qt.CursorShape.PointingHandCursor)

    def setup_base_ui(self):
        """Базовая настройка UI"""
        current_date = QDate.currentDate().toString("dd.MM.yyyy")
        self.dateLabel.setText(f"Создан: {current_date}")
        self.createBtn.setText("Создать проект")

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

    def update_columns_button_text(self):
        """Обновляет текст на кнопке выбора колонок"""
        if not hasattr(self, 'columnBtn'):
            return
        count = len(self.selected_columns_data)
        if count != 0:
            self.columnBtn.setText(f"Выбрано колонок: {count}")

    def select_columns(self):
        """Открыть диалог выбора колонок"""
        try:
            from windows.projects.column_selector import ColumnSelectorDialog

            dialog = ColumnSelectorDialog(
                self,
                service=self.service,  # ← передаем сервис
                preselected_keys=self.selected_columns_keys
            )

            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.selected_columns_data = dialog.get_selected_columns_data()
                self.selected_columns_keys = dialog.get_selected_keys()
                self.update_columns_button_text()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при выборе колонок: {e}")

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

        # Загружаем колонки
        if 'selected_columns_data' in self.project_data and self.project_data['selected_columns_data']:
            self.selected_columns_data = self.project_data['selected_columns_data']
            self.selected_columns_keys = [col.get('col_key', '') for col in self.selected_columns_data]
            self.update_columns_button_text()

        # Загружаем участников и администраторов
        self._load_participants_and_admins()

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
            'selected_columns': self.selected_columns_keys,
            'selected_columns_data': self.selected_columns_data,
            'columns_display_names': {col['col_key']: col['name'] for col in self.selected_columns_data},
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