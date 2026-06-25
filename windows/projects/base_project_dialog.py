# windows/projects/base_project_dialog.py
import os
import sys
from typing import List, Dict, Optional
from PyQt6 import uic
from PyQt6.QtCore import QDate, pyqtSignal, Qt
from PyQt6.QtWidgets import QDialog, QMessageBox, QComboBox, QCheckBox, QVBoxLayout

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.projects_service.project_dialog_service import ProjectDialogService


class BaseProjectDialog(QDialog):
    """Базовый класс для диалогов проектов - только UI, логика в сервисе"""

    columns_changed = pyqtSignal(dict)

    def __init__(self, parent=None, title="Проект", project_data=None, service=None, creator_id=None):
        super().__init__(parent)

        # Создаём сервис диалогов
        self.dialog_service = ProjectDialogService(service, creator_id)
        self.project_service = service
        self.project_data = project_data or {}

        # UI данные
        self.participants = []
        self.admins = []
        self.all_columns = []
        self.column_checkboxes = {}
        self.selected_columns_data = []

        # Загружаем UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "projects")
        uic.loadUi(os.path.join(ui_path, "project_creation_dialog.ui"), self)

        # Настраиваем UI
        self._setup_ui()

        # Загружаем данные
        self._load_columns()
        self._setup_manager_selector()
        self._hide_field_checkboxes()

        if project_data:
            self.load_project_data()

    def _setup_ui(self):
        """Базовая настройка UI"""
        current_date = self.dialog_service.get_current_date()
        self.dateLabel.setText(f"Создан: {current_date}")
        self.createBtn.setText("Создать проект")

        # Подключаем сигналы
        self.participantsBtn.clicked.connect(self.select_participants)
        self.adminsBtn.clicked.connect(self.select_admins)

    def _hide_field_checkboxes(self):
        """Скрывает ненужные чекбоксы"""
        field_checkboxes = [
            'colNameCheckbox', 'colDescriptionCheckbox', 'colStatusCheckbox',
            'colCreatedDateCheckbox', 'colDeadlineCheckbox',
            'colParticipantsCheckbox', 'colProgressCheckbox'
        ]
        for cb_name in field_checkboxes:
            if hasattr(self, cb_name):
                getattr(self, cb_name).hide()

    def _load_columns(self):
        """Загружает колонки через сервис"""
        self.all_columns = self.dialog_service.get_template_columns()

        if not hasattr(self, 'columnsGroupBox'):
            return

        columns_layout = self.columnsGroupBox.layout()
        if columns_layout is None:
            columns_layout = QVBoxLayout(self.columnsGroupBox)
            self.columnsGroupBox.setLayout(columns_layout)

        # Очищаем существующие чекбоксы
        for checkbox in self.column_checkboxes.values():
            if checkbox and checkbox.parent():
                checkbox.deleteLater()
        self.column_checkboxes.clear()

        # Создаём новые чекбоксы
        for col in self.all_columns:
            checkbox = self._create_column_checkbox(col)
            self.column_checkboxes[col['col_key']] = checkbox
            columns_layout.addWidget(checkbox)

        columns_layout.addStretch()

    def _create_column_checkbox(self, col: Dict) -> QCheckBox:
        """Создаёт чекбокс для колонки"""
        checkbox = QCheckBox(col['name'])
        checkbox.setProperty('col_key', col['col_key'])
        checkbox.setProperty('col_data', col)
        checkbox.setChecked(False)

        checkbox.setStyleSheet("""
            QCheckBox { font-size: 13px; color: #1B232A; padding: 5px; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #1B232A; border-radius: 4px; background-color: white; }
            QCheckBox::indicator:checked { background-color: #D22730; border: 2px solid #D22730; }
            QCheckBox::indicator:hover { border-color: #D22730; }
        """)

        checkbox.stateChanged.connect(
            lambda checked, key=col['col_key']: self._on_column_changed(key, checked)
        )

        return checkbox

    def _on_column_changed(self, col_key: str, state):
        """Обработчик изменения состояния чекбокса колонки"""
        col = next((c for c in self.all_columns if c['col_key'] == col_key), None)
        if not col:
            return

        if state == Qt.CheckState.Checked.value:
            if col not in self.selected_columns_data:
                self.selected_columns_data.append(col)
        else:
            if col in self.selected_columns_data:
                self.selected_columns_data.remove(col)

    def _setup_manager_selector(self):
        """Настройка комбобокса куратора"""
        combo = self._get_manager_combo()
        if combo is None:
            return

        combo.clear()
        combo.addItem("Выберите куратора", None)

        managers = self.dialog_service.get_employees_for_manager_combo()
        for manager in managers:
            combo.addItem(manager['display_name'], manager['id'])

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
        return combo.currentData() if combo else None

    def get_manager_name(self) -> Optional[str]:
        """Возвращает имя выбранного куратора"""
        combo = self._get_manager_combo()
        return combo.currentText() if combo else None

    def select_participants(self):
        """Выбор участников"""
        from windows.projects.employee_selector import EmployeeSelectorDialog

        dialog = EmployeeSelectorDialog(self, service=self.project_service, mode="participants")
        if self.participants:
            preselected_ids = [p.get('id') if isinstance(p, dict) else p for p in self.participants]
            dialog.set_preselected(preselected_ids)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.participants = dialog.get_selected_employees()
            self._update_participants_button_text()

    def select_admins(self):
        """Выбор администраторов"""
        from windows.projects.employee_selector import EmployeeSelectorDialog

        dialog = EmployeeSelectorDialog(self, service=self.project_service, mode="admins")
        if self.admins:
            preselected_ids = [a.get('id') if isinstance(a, dict) else a for a in self.admins]
            dialog.set_preselected(preselected_ids)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.admins = dialog.get_selected_employees()
            self._update_admins_button_text()

    def _update_participants_button_text(self):
        """Обновляет текст кнопки участников"""
        count = len(self.participants)
        if count == 0:
            self.participantsBtn.setText("Выбрать участников")
        elif count == 1:
            emp = self.participants[0]
            name = self.dialog_service.get_employee_display_name(emp['id'])
            self.participantsBtn.setText(f"Участник: {name}")
        else:
            self.participantsBtn.setText(f"Участники ({count} чел.)")

    def _update_admins_button_text(self):
        """Обновляет текст кнопки администраторов"""
        count = len(self.admins)
        if count == 0:
            self.adminsBtn.setText("Выбрать администраторов")
        elif count == 1:
            emp = self.admins[0]
            name = self.dialog_service.get_employee_display_name(emp['id'])
            self.adminsBtn.setText(f"Администратор: {name}")
        else:
            self.adminsBtn.setText(f"Администраторы ({count} чел.)")

    def load_project_data(self):
        """Загружает данные проекта"""
        if hasattr(self, 'nameInput'):
            self.nameInput.setText(self.project_data.get('name', ''))

        if hasattr(self, 'descInput'):
            self.descInput.setPlainText(self.project_data.get('description', ''))

        is_active = self.project_data.get('is_active', True)
        if isinstance(is_active, str):
            is_active = is_active.lower() == 'true'

        if hasattr(self, 'activeCheckbox'):
            self.activeCheckbox.setChecked(is_active)

        # Загружаем куратора
        manager_id = self.project_data.get('manager_id')
        if manager_id:
            combo = self._get_manager_combo()
            if combo:
                for i in range(combo.count()):
                    if combo.itemData(i) == manager_id:
                        combo.setCurrentIndex(i)
                        break

        # Загружаем колонки
        self.selected_columns_data = []
        selected_keys = []

        if 'selected_columns_data' in self.project_data:
            self.selected_columns_data = self.project_data['selected_columns_data']
            selected_keys = [col.get('col_key') for col in self.selected_columns_data]
        elif self.project_data.get('selected_columns'):
            selected_keys = self.project_data.get('selected_columns', [])
            self.selected_columns_data = self.dialog_service.get_selected_columns_by_keys(
                self.all_columns, selected_keys
            )

        for col_key, checkbox in self.column_checkboxes.items():
            checkbox.setChecked(col_key in selected_keys)

        # Загружаем участников
        self._load_participants_and_admins()

    def _load_participants_and_admins(self):
        """Загружает участников и администраторов"""
        member_ids = self.project_data.get('member_ids', [])
        admin_ids = self.project_data.get('admin_ids', [])

        if member_ids and self.project_service:
            employees = self.project_service.load_employees_by_ids(member_ids)
            self.participants = employees
            self.admins = [emp for emp in employees if emp['id'] in admin_ids]
        else:
            self.participants = self._normalize_data(self.project_data.get('participants', []))
            self.admins = self._normalize_data(self.project_data.get('admins', []))

        # ✅ ВАЖНО: Убеждаемся, что все администраторы есть в participants
        for admin in self.admins:
            admin_id = admin.get('id') if isinstance(admin, dict) else admin
            if admin_id and not any(
                    p.get('id') == admin_id if isinstance(p, dict) else p == admin_id for p in self.participants):
                self.participants.append(admin)

        self._update_participants_button_text()
        self._update_admins_button_text()

    def _normalize_data(self, data) -> List[Dict]:
        """Нормализует данные сотрудников"""
        if not data:
            return []
        if isinstance(data, str):
            ids = [int(id.strip()) for id in data.split(',') if id.strip()]
            return [{'id': emp_id, 'last_name': f"User{emp_id}", 'first_name': f"User{emp_id}"} for emp_id in ids]
        if isinstance(data, list):
            normalized = []
            for item in data:
                if isinstance(item, dict) and 'id' in item:
                    normalized.append(item)
                elif isinstance(item, int):
                    normalized.append({'id': item, 'first_name': f"User{item}", 'last_name': f"LastName{item}"})
            return normalized
        return []

    def get_selected_column_keys(self) -> List[str]:
        """Возвращает ключи выбранных колонок"""
        return [col['col_key'] for col in self.selected_columns_data]

    def get_project_data(self) -> Dict:
        """Возвращает данные проекта"""
        participants_ids = set()
        for p in self.participants:
            emp_id = p.get('id') if isinstance(p, dict) else p
            if emp_id:
                participants_ids.add(str(emp_id))

        admins_ids = set()
        for a in self.admins:
            emp_id = a.get('id') if isinstance(a, dict) else a
            if emp_id:
                admins_ids.add(str(emp_id))

        manager_id = self.get_manager_id()
        if manager_id:
            participants_ids.add(str(manager_id))

        # ✅ ВАЖНО: ВСЕ администраторы должны быть в участниках
        for admin_id in admins_ids:
            participants_ids.add(admin_id)

        data = {
            'name': self.nameInput.text() if hasattr(self, 'nameInput') else '',
            'description': self.descInput.toPlainText() if hasattr(self, 'descInput') else '',
            'participants_ids': ','.join(participants_ids),
            'participants': self.participants,
            'admins_ids': ','.join(admins_ids),
            'admins': self.admins,
            'is_active': self.activeCheckbox.isChecked() if hasattr(self, 'activeCheckbox') else True,
            'created_date': self.dialog_service.get_current_date(),
            'selected_columns_data': self.selected_columns_data,
            'selected_columns': self.get_selected_column_keys(),
            'manager_id': manager_id,
        }

        if self.project_data and self.project_data.get('id'):
            data['id'] = self.project_data.get('id')

        return data

    def validate_input(self) -> bool:
        """Проверяет введённые данные"""
        if hasattr(self, 'nameInput') and not self.nameInput.text().strip():
            QMessageBox.warning(self, "Предупреждение", "Введите название проекта")
            return False

        if not self.selected_columns_data:
            QMessageBox.warning(self, "Предупреждение", "Выберите хотя бы одну колонку")
            return False

        return True