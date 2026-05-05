# windows/projects/employee_selector.py

import os
import sys
from typing import List, Dict, Optional, Set
from functools import partial
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QCheckBox, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class EmployeeSelectorDialog(QDialog):
    """Диалог выбора сотрудников с поиском и фильтрацией"""

    employees_selected = pyqtSignal(list)

    def __init__(self, parent=None, service=None, mode="participants"):
        super().__init__(parent)
        self.service = service
        self.mode = mode
        self.all_employees = []
        self.filtered_employees = []
        self.checkboxes = []
        self.selected_employees = set()
        self.employee_checkbox_map = {}
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filters)

        # Данные для фильтров
        self.divisions_list = []
        self.departments_list = []

        # Загрузка UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "projects")
        uic.loadUi(os.path.join(ui_path, "employee_selector.ui"), self)

        # Подключение сигналов
        self.searchInput.textChanged.connect(self.on_search_text_changed)
        self.departmentFilter.currentTextChanged.connect(self.on_department_changed)
        self.subDepartmentFilter.currentTextChanged.connect(self.apply_filters)
        self.selectAllCheckBox.stateChanged.connect(self.on_select_all_changed)
        self.selectBtn.clicked.connect(self.accept)

        # Инициализация
        self.load_initial_data()
        self.setup_filters()
        self.selected_employees.clear()

        QTimer.singleShot(0, self.apply_filters)

    def load_initial_data(self):
        """Загружает данные через сервис"""
        if self.service:
            data = self.service.load_employee_selector_data()
            self.all_employees = data.get('employees', [])
            self.divisions_list = data.get('divisions', [])
            self.departments_list = data.get('departments', [])
            # selected_employees не загружаем - они будут установлены через set_preselected
        else:
            print("⚠️ Сервис не передан, данные не загружены")
            self.all_employees = []
            self.divisions_list = []
            self.departments_list = []

    def setup_filters(self):
        """Настройка фильтров отделов и подразделений"""
        # Настройка фильтра отделов
        self.departmentFilter.blockSignals(True)
        self.departmentFilter.clear()
        self.departmentFilter.addItem("Все отделы")
        for dept in sorted(self.departments_list):
            self.departmentFilter.addItem(dept)
        self.departmentFilter.setCurrentIndex(0)
        self.departmentFilter.blockSignals(False)

        # Настройка фильтра подразделений
        self.subDepartmentFilter.blockSignals(True)
        self.subDepartmentFilter.clear()
        self.subDepartmentFilter.addItem("Все подразделения")
        for div in sorted(self.divisions_list):
            self.subDepartmentFilter.addItem(div)
        self.subDepartmentFilter.setCurrentIndex(0)
        self.subDepartmentFilter.blockSignals(False)

        self.subDepartmentFilter.setEnabled(len(self.divisions_list) > 0)

    def showEvent(self, event):
        """Срабатывает каждый раз при открытии диалога"""
        super().showEvent(event)
        self.searchInput.clear()
        # Сбрасываем фильтры
        self.departmentFilter.blockSignals(True)
        self.departmentFilter.setCurrentIndex(0)
        self.departmentFilter.blockSignals(False)
        self.subDepartmentFilter.blockSignals(True)
        self.subDepartmentFilter.setCurrentIndex(0)
        self.subDepartmentFilter.blockSignals(False)
        QTimer.singleShot(0, self._refresh_filters)

    def _refresh_filters(self):
        """Обновляет фильтры и отображение"""
        if self.service:
            data = self.service.load_employee_selector_data()
            self.all_employees = data.get('employees', self.all_employees)
            # Сохраняем выбранных сотрудников по ID
            selected_ids = self.selected_employees.copy()
            self.selected_employees = selected_ids
        self.apply_filters()

    def on_department_changed(self, department):
        """Обработка изменения выбранного отдела"""
        self.apply_filters()

    def on_search_text_changed(self, text):
        """Запуск таймера поиска при вводе текста"""
        self.search_timer.start(300)

    def apply_filters(self):
        """Применение всех фильтров"""
        search_text = self.searchInput.text()

        # Фильтрация через сервис
        if self.service:
            self.filtered_employees = self.service.filter_employees_by_search(self.all_employees, search_text)
        else:
            # Fallback если нет сервиса
            if not search_text:
                self.filtered_employees = self.all_employees.copy()
            else:
                search_lower = search_text.lower().strip()
                self.filtered_employees = []
                for emp in self.all_employees:
                    if search_lower in emp['full_name'].lower():
                        self.filtered_employees.append(emp)

        self.sort_employees()
        self.display_employees()

    def sort_employees(self):
        """Сортировка через сервис"""
        if self.service:
            self.filtered_employees = self.service.sort_employees_for_selector(
                self.filtered_employees, self.selected_employees
            )
        else:
            # Fallback
            def get_sort_key(emp):
                is_selected = emp['id'] in self.selected_employees
                return (0 if is_selected else 1, -emp.get('usage_count', 0))

            self.filtered_employees.sort(key=get_sort_key)

    def display_employees(self):
        """Отображение отфильтрованных сотрудников с чекбоксами"""
        layout = self.scrollAreaWidgetContents.layout()

        # Полная очистка
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.checkboxes.clear()
        self.employee_checkbox_map.clear()

        self.selectAllCheckBox.setChecked(False)
        self.selectAllCheckBox.setEnabled(True)

        if not self.filtered_employees:
            label = QLabel("Сотрудники не найдены")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #B8B8B5; font-size: 14px; padding: 40px;")
            layout.addWidget(label)
            self.selectAllCheckBox.setEnabled(False)
            self.update_selected_count()
            return

        # Разделяем на выбранных и остальных
        selected_emps = [emp for emp in self.filtered_employees if emp['id'] in self.selected_employees]
        other_emps = [emp for emp in self.filtered_employees if emp['id'] not in self.selected_employees]

        # Отображаем выбранных сотрудников с разделителем
        if selected_emps:
            separator = QLabel("✓ ВЫБРАННЫЕ")
            separator.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    font-weight: bold;
                    color: #D22730;
                    padding: 8px 0px 4px 0px;
                    border-bottom: 1px solid #D9D9D6;
                }
            """)
            layout.addWidget(separator)

            for emp in selected_emps:
                checkbox = self._create_checkbox(emp)
                layout.addWidget(checkbox)
                self.checkboxes.append(checkbox)

        # Отображаем остальных с разделителем
        if other_emps:
            if selected_emps:
                separator = QLabel("ВСЕ СОТРУДНИКИ")
                separator.setStyleSheet("""
                    QLabel {
                        font-size: 11px;
                        font-weight: bold;
                        color: #666;
                        padding: 16px 0px 4px 0px;
                        border-bottom: 1px solid #D9D9D6;
                    }
                """)
                layout.addWidget(separator)

            for emp in other_emps:
                checkbox = self._create_checkbox(emp)
                layout.addWidget(checkbox)
                self.checkboxes.append(checkbox)

        layout.addStretch()
        self.update_selected_count()

    def _create_checkbox(self, emp: Dict) -> QCheckBox:
        """Создает чекбокс для сотрудника"""
        display_text = emp['full_name']
        checkbox = QCheckBox(display_text)

        # Tooltip с дополнительной информацией
        tooltip_lines = []
        if emp.get('position'):
            tooltip_lines.append(f"Должность: {emp['position']}")
        if emp.get('phone'):
            tooltip_lines.append(f"Телефон: {emp['phone']}")
        if emp.get('email'):
            tooltip_lines.append(f"Email: {emp['email']}")
        if emp.get('role'):
            role_display = {'user': 'Пользователь', 'admin': 'Администратор', 'superadmin': 'Суперадминистратор'}
            tooltip_lines.append(f"Роль: {role_display.get(emp['role'], emp['role'])}")

        usage_count = emp.get('usage_count', 0)
        if usage_count > 0:
            tooltip_lines.append(f"📊 Использован в {usage_count} задачах")

        checkbox.setToolTip("\n".join(tooltip_lines) if tooltip_lines else "Нет дополнительной информации")

        self.employee_checkbox_map[checkbox] = emp['id']

        if emp['id'] in self.selected_employees:
            checkbox.setChecked(True)

        checkbox.stateChanged.connect(partial(self._on_checkbox_changed, emp['id']))

        return checkbox

    def _on_checkbox_changed(self, emp_id: int, state):
        """Обработчик изменения состояния чекбокса"""
        if state == Qt.CheckState.Checked.value:
            self.selected_employees.add(emp_id)
        elif state == Qt.CheckState.Unchecked.value:
            self.selected_employees.discard(emp_id)

        self.sort_employees()
        self.display_employees()
        self.update_selected_count()
        self._update_select_all_state()

    def _update_select_all_state(self):
        """Обновление состояния чекбокса 'Выбрать всех'"""
        if len(self.selected_employees) == len(self.filtered_employees) and len(self.filtered_employees) > 0:
            self.selectAllCheckBox.setCheckState(Qt.CheckState.Checked)
        elif self.selectAllCheckBox.checkState() == Qt.CheckState.Checked:
            self.selectAllCheckBox.setCheckState(Qt.CheckState.Unchecked)

    def on_select_all_changed(self, state):
        """Обработка изменения состояния чекбокса 'Выбрать всех'"""
        if state == Qt.CheckState.Checked:
            for emp in self.filtered_employees:
                self.selected_employees.add(emp['id'])
        elif state == Qt.CheckState.Unchecked:
            for emp in self.filtered_employees:
                self.selected_employees.discard(emp['id'])

        self.sort_employees()
        self.display_employees()
        self.update_selected_count()

    def update_selected_count(self):
        """Обновление счетчика выбранных сотрудников"""
        count = len(self.selected_employees)
        self.selectedCountLabel.setText(f"Выбрано: {count}")

    def get_selected_employees(self) -> List[Dict]:
        """Получение списка выбранных сотрудников с полной информацией"""
        selected = []
        for emp in self.all_employees:
            if emp['id'] in self.selected_employees:
                selected.append(emp)
        return selected

    def get_selected_ids(self) -> List[int]:
        """Получение списка ID выбранных сотрудников"""
        return list(self.selected_employees)

    def set_preselected(self, employee_ids: List[int]):
        """Установка предвыбранных сотрудников"""
        self.selected_employees = set(employee_ids)
        self.sort_employees()
        self.display_employees()

    def accept(self):
        """Переопределяем accept для возврата данных"""
        self.employees_selected.emit(self.get_selected_employees())
        super().accept()