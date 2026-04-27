# windows/projects/column_selector.py

import os
import sys
from typing import List, Dict, Optional
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QCheckBox, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class ColumnSelectorDialog(QDialog):
    """
    Диалог выбора колонок для проекта с поиском и группировкой
    Аналогичен EmployeeSelectorDialog
    """

    columns_selected = pyqtSignal(list)

    def __init__(self, parent=None, template_columns: List[Dict] = None, preselected_keys: List[str] = None):
        super().__init__(parent)

        # Данные
        self.all_columns = template_columns or []
        self.filtered_columns = self.all_columns.copy()  # 👈 ИНИЦИАЛИЗИРУЕМ!
        self.selected_columns_keys = set(preselected_keys or [])
        self.column_checkboxes = {}
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filters)

        # Загрузка UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "projects")
        uic.loadUi(os.path.join(ui_path, "column_selector.ui"), self)

        # Подключение сигналов
        self.searchInput.textChanged.connect(self.on_search_text_changed)
        self.selectAllCheckBox.stateChanged.connect(self.on_select_all_changed)
        self.selectBtn.clicked.connect(self.accept)

        # Получаем layout
        self.columns_layout = self.scrollAreaWidgetContents.layout()
        if self.columns_layout is None:
            from PyQt6.QtWidgets import QVBoxLayout
            self.columns_layout = QVBoxLayout(self.scrollAreaWidgetContents)
            self.columns_layout.setSpacing(5)
            self.columns_layout.setContentsMargins(10, 10, 10, 10)

        # Отображаем колонки
        self.display_columns()

        print(f"📊 ColumnSelectorDialog: загружено {len(self.all_columns)} колонок")
        for col in self.all_columns:
            print(f"   - {col.get('name')}")

    def on_search_text_changed(self, text):
        self.search_timer.start(300)

    def apply_filters(self):
        search_text = self.searchInput.text().lower().strip()

        if not search_text:
            self.filtered_columns = self.all_columns.copy()
        else:
            self.filtered_columns = []
            for col in self.all_columns:
                col_name = col.get('name', '').lower()
                col_key = col.get('col_key', '').lower()
                if search_text in col_name or search_text in col_key:
                    self.filtered_columns.append(col)

        self.display_columns()

    def clear_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def display_columns(self):
        print(f"🔍 display_columns: filtered_columns count = {len(self.filtered_columns)}")

        self.clear_layout(self.columns_layout)
        self.column_checkboxes.clear()
        self.selectAllCheckBox.setChecked(False)

        if not self.filtered_columns:
            label = QLabel("Колонки не найдены")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #B8B8B5; font-size: 14px; padding: 40px;")
            self.columns_layout.addWidget(label)
            self.selectAllCheckBox.setEnabled(False)
            self.update_selected_count()
            return

        print(f"📊 Отображение {len(self.filtered_columns)} колонок:")

        for col in self.filtered_columns:
            col_name = col.get('name', 'Без названия')
            col_key = col.get('col_key', col_name.lower().replace(' ', '_'))
            col_description = col.get('description', '')
            col_id = col.get('id')

            print(f"   - Создаем чекбокс: {col_name} (id={col_id})")

            checkbox = QCheckBox(col_name)
            checkbox.setProperty('col_key', col_key)
            checkbox.setProperty('col_data', col)
            checkbox.setProperty('col_id', col_id)

            if col_description:
                checkbox.setToolTip(col_description)

            checkbox.setChecked(col_key in self.selected_columns_keys)

            checkbox.setStyleSheet("""
                QCheckBox {
                    font-size: 13px;
                    color: #1B232A;
                    padding: 5px;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #D9D9D6;
                    border-radius: 4px;
                    background-color: white;
                }
                QCheckBox::indicator:checked {
                    background-color: #D22730;
                    border-color: #D22730;
                }
                QCheckBox::indicator:hover {
                    border-color: #D22730;
                }
            """)

            self.column_checkboxes[col_key] = checkbox
            checkbox.stateChanged.connect(lambda checked, key=col_key: self._on_checkbox_changed(key, checked))

            self.columns_layout.addWidget(checkbox)

        self.columns_layout.addStretch()
        self.update_selected_count()
        self._update_select_all_state()

    def _on_checkbox_changed(self, col_key: str, state):
        if state == Qt.CheckState.Checked.value:
            self.selected_columns_keys.add(col_key)
            print(f"✅ Добавлена колонка: {col_key}")
        elif state == Qt.CheckState.Unchecked.value:
            self.selected_columns_keys.discard(col_key)
            print(f"❌ Удалена колонка: {col_key}")

        self.update_selected_count()
        self._update_select_all_state()

    def _update_select_all_state(self):
        if len(self.selected_columns_keys) == len(self.filtered_columns) and len(self.filtered_columns) > 0:
            self.selectAllCheckBox.setCheckState(Qt.CheckState.Checked)
        elif self.selectAllCheckBox.checkState() == Qt.CheckState.Checked:
            self.selectAllCheckBox.setCheckState(Qt.CheckState.Unchecked)

    def on_select_all_changed(self, state):
        if state == Qt.CheckState.Checked:
            for col in self.filtered_columns:
                col_key = col.get('col_key', col.get('name', '').lower().replace(' ', '_'))
                self.selected_columns_keys.add(col_key)
            for checkbox in self.column_checkboxes.values():
                checkbox.setChecked(True)
        elif state == Qt.CheckState.Unchecked:
            self.selected_columns_keys.clear()
            for checkbox in self.column_checkboxes.values():
                checkbox.setChecked(False)
        self.update_selected_count()

    def update_selected_count(self):
        count = len(self.selected_columns_keys)
        self.selectedCountLabel.setText(f"Выбрано: {count}")
        print(f"📊 Выбрано колонок: {count}, keys: {sorted(self.selected_columns_keys)}")

    def get_selected_columns_data(self) -> List[Dict]:
        """Возвращает данные выбранных колонок с полной информацией (включая col_key)"""
        selected = []
        for col in self.all_columns:
            col_key = col.get('col_key', col.get('name', '').lower().replace(' ', '_'))
            if col_key in self.selected_columns_keys:
                # Убеждаемся, что в данных есть col_key
                col_copy = col.copy()
                if 'col_key' not in col_copy:
                    col_copy['col_key'] = col_key
                selected.append(col_copy)
        return selected

    def get_selected_keys(self) -> List[str]:
        return list(self.selected_columns_keys)

    def accept(self):
        self.columns_selected.emit(self.get_selected_columns_data())
        super().accept()