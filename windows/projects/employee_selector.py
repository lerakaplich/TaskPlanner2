# windows/projects/employee_selector.py

import os
import sys
from functools import partial
from typing import List, Dict

from PyQt6 import uic
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QDialog, QCheckBox, QLabel

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class EmployeeSelectorDialog(QDialog):
    """Диалог выбора сотрудников с поиском и фильтрацией"""

    employees_selected = pyqtSignal(list)

    def __init__(self, parent=None, service=None, mode="participants"):
        super().__init__(parent)
        self.service = service
        self.mode = mode
        self.readonly_mode = False
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
        self.departments_dict = {}
        self.divisions_dict = {}
        self.department_to_divisions = {}
        self.division_to_departments = {}
        self.updating_filters = False

        # Загрузка UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "projects")
        uic.loadUi(os.path.join(ui_path, "employee_selector.ui"), self)

        # Подключение сигналов
        self.searchInput.textChanged.connect(self.on_search_text_changed)
        self.departmentFilter.currentTextChanged.connect(self.on_department_changed)
        self.subDepartmentFilter.currentTextChanged.connect(self.on_sub_department_changed)
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

            self.departments_dict = {}
            for dept_id, dept_name in self.departments_list:
                self.departments_dict[dept_name] = dept_id

            self.divisions_dict = {}
            for div_id, div_name in self.divisions_list:
                self.divisions_dict[div_name] = div_id

            self.department_to_divisions = {}
            self.division_to_departments = {}

            for emp in self.all_employees:
                dept_id = emp.get('department_id')
                div_id = emp.get('division_id')

                if dept_id and div_id:
                    if dept_id not in self.department_to_divisions:
                        self.department_to_divisions[dept_id] = set()
                    self.department_to_divisions[dept_id].add(div_id)

                    if div_id not in self.division_to_departments:
                        self.division_to_departments[div_id] = set()
                    self.division_to_departments[div_id].add(dept_id)

            print(f"📊 Загружено отделов: {len(self.departments_dict)}")
            print(f"📊 Загружено подразделений: {len(self.divisions_dict)}")
        else:
            print("⚠️ Сервис не передан, данные не загружены")
            self.all_employees = []
            self.divisions_list = []
            self.departments_list = []

    def setup_filters(self):
        """Настройка фильтров отделов и подразделений"""
        self.departmentFilter.blockSignals(True)
        self.departmentFilter.clear()
        self.departmentFilter.addItem("Все отделы")
        for dept_id, dept_name in sorted(self.departments_list, key=lambda x: x[1]):
            self.departmentFilter.addItem(dept_name)
        self.departmentFilter.setCurrentIndex(0)
        self.departmentFilter.blockSignals(False)

        self.subDepartmentFilter.blockSignals(True)
        self.subDepartmentFilter.clear()
        self.subDepartmentFilter.addItem("Все подразделения")
        for div_id, div_name in sorted(self.divisions_list, key=lambda x: x[1]):
            self.subDepartmentFilter.addItem(div_name)
        self.subDepartmentFilter.setCurrentIndex(0)
        self.subDepartmentFilter.blockSignals(False)

        self.subDepartmentFilter.setEnabled(len(self.divisions_list) > 0)

    def set_readonly_mode(self, readonly: bool):
        """Устанавливает режим только для чтения"""
        self.readonly_mode = readonly
        if readonly:
            self.setWindowTitle(f"Просмотр {'участников' if self.mode == 'participants' else 'администраторов'}")
            # Скрываем кнопку выбора
            if hasattr(self, 'selectBtn'):
                self.selectBtn.hide()
            # Скрываем чекбокс "Выбрать всех"
            if hasattr(self, 'selectAllCheckBox'):
                self.selectAllCheckBox.hide()
            # Поиск и фильтры оставляем включёнными
        else:
            if hasattr(self, 'selectBtn'):
                self.selectBtn.show()
            if hasattr(self, 'selectAllCheckBox'):
                self.selectAllCheckBox.show()

    def _update_departments_filter(self, division_name):
        """Обновляет список отделов в зависимости от выбранного подразделения"""
        if self.updating_filters:
            return

        self.updating_filters = True

        self.departmentFilter.blockSignals(True)
        self.departmentFilter.clear()
        self.departmentFilter.addItem("Все отделы")

        if division_name and division_name != "Все подразделения":
            division_id = self.divisions_dict.get(division_name)

            if division_id:
                dept_ids = self.division_to_departments.get(division_id, set())

                for dept_id in sorted(dept_ids):
                    for d_id, d_name in self.departments_list:
                        if d_id == dept_id:
                            self.departmentFilter.addItem(d_name)
                            break

                print(f"🔍 Для подразделения '{division_name}' найдено отделов: {len(dept_ids)}")
            else:
                print(f"⚠️ Не найден ID для подразделения '{division_name}'")
        else:
            for dept_id, dept_name in sorted(self.departments_list, key=lambda x: x[1]):
                self.departmentFilter.addItem(dept_name)

        self.departmentFilter.setEnabled(self.departmentFilter.count() > 1)
        self.departmentFilter.blockSignals(False)
        self.updating_filters = False

    def _update_sub_departments_filter(self, department_name):
        """Обновляет список подразделений"""
        if self.updating_filters:
            return

        self.updating_filters = True

        current_division = self.subDepartmentFilter.currentText()

        self.subDepartmentFilter.blockSignals(True)
        self.subDepartmentFilter.clear()
        self.subDepartmentFilter.addItem("Все подразделения")

        for div_id, div_name in sorted(self.divisions_list, key=lambda x: x[1]):
            self.subDepartmentFilter.addItem(div_name)

        if current_division in [div_name for _, div_name in self.divisions_list]:
            index = self.subDepartmentFilter.findText(current_division)
            if index >= 0:
                self.subDepartmentFilter.setCurrentIndex(index)
        else:
            self.subDepartmentFilter.setCurrentIndex(0)

        self.subDepartmentFilter.setEnabled(self.subDepartmentFilter.count() > 1)
        self.subDepartmentFilter.blockSignals(False)
        self.updating_filters = False

    def showEvent(self, event):
        """Срабатывает каждый раз при открытии диалога"""
        super().showEvent(event)
        if not self.readonly_mode:
            self.searchInput.clear()
            self.updating_filters = True

            self.departmentFilter.blockSignals(True)
            self.departmentFilter.setCurrentIndex(0)
            self.departmentFilter.blockSignals(False)

            self.subDepartmentFilter.blockSignals(True)
            self.subDepartmentFilter.setCurrentIndex(0)
            self.subDepartmentFilter.blockSignals(False)

            self.updating_filters = False
            QTimer.singleShot(0, self._refresh_filters)

    def _refresh_filters(self):
        """Обновляет фильтры и отображение"""
        if self.service and not self.readonly_mode:
            data = self.service.load_employee_selector_data()
            self.all_employees = data.get('employees', self.all_employees)
            selected_ids = self.selected_employees.copy()
            self.selected_employees = selected_ids
        self.apply_filters()

    def on_search_text_changed(self, text):
        """Запуск таймера поиска при вводе текста"""
        self.search_timer.start(300)

    def on_department_changed(self, department):
        """Обработка изменения выбранного отдела"""
        self._update_sub_departments_filter(department)
        self.apply_filters()

    def on_sub_department_changed(self, sub_department):
        """Обработка изменения выбранного подразделения"""
        self._update_departments_filter(sub_department)
        self.apply_filters()

    def apply_filters(self):
        """Применяет все фильтры к списку сотрудников"""
        department_name = self.departmentFilter.currentText()
        division_name = self.subDepartmentFilter.currentText()
        search_text = self.searchInput.text()

        filtered = self.all_employees.copy()

        if department_name and department_name != "Все отделы":
            department_id = self.departments_dict.get(department_name)
            if department_id:
                filtered = [emp for emp in filtered if emp.get('department_id') == department_id]
            else:
                filtered = []

        if division_name and division_name != "Все подразделения" and filtered:
            division_id = self.divisions_dict.get(division_name)
            if division_id:
                filtered = [emp for emp in filtered if emp.get('division_id') == division_id]
            else:
                filtered = []

        if search_text and filtered:
            search_lower = search_text.lower().strip()
            filtered = [
                emp for emp in filtered
                if search_lower in emp.get('full_name', '').lower()
                   or search_lower in emp.get('last_name', '').lower()
                   or search_lower in emp.get('first_name', '').lower()
                   or search_lower in emp.get('position', '').lower()
            ]

        self.filtered_employees = filtered
        self.sort_employees()
        self.display_employees()

    def sort_employees(self):
        """Сортировка через сервис"""
        if self.service and not self.readonly_mode:
            self.filtered_employees = self.service.sort_employees_for_selector(
                self.filtered_employees, self.selected_employees
            )
        else:
            def get_sort_key(emp):
                # В режиме просмотра не пересортировываем
                is_selected = emp['id'] in self.selected_employees
                return (0 if is_selected else 1, -emp.get('usage_count', 0))
            self.filtered_employees.sort(key=get_sort_key)

    def display_employees(self):
        """Отображение отфильтрованных сотрудников с чекбоксами"""
        layout = self.scrollAreaWidgetContents.layout()

        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.checkboxes.clear()
        self.employee_checkbox_map.clear()

        if not self.filtered_employees:
            label = QLabel("Сотрудники не найдены")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #B8B8B5; font-size: 14px; padding: 40px;")
            layout.addWidget(label)
            self.update_selected_count()
            return

        # Разделяем на выбранных и остальных
        selected_emps = [emp for emp in self.filtered_employees if emp['id'] in self.selected_employees]
        other_emps = [emp for emp in self.filtered_employees if emp['id'] not in self.selected_employees]

        if self.readonly_mode:
            # В режиме просмотра показываем всех сотрудников, но чекбоксы отключены
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
                    checkbox = self._create_readonly_checkbox(emp)
                    layout.addWidget(checkbox)
                    self.checkboxes.append(checkbox)

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
                    checkbox = self._create_readonly_checkbox(emp)
                    layout.addWidget(checkbox)
                    self.checkboxes.append(checkbox)
        else:
            # Режим редактирования
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

    def _create_readonly_checkbox(self, emp: Dict) -> QCheckBox:
        """Создает чекбокс для просмотра (только чтение)"""
        display_text = emp['full_name']
        checkbox = QCheckBox(display_text)

        tooltip_lines = []
        if emp.get('position'):
            tooltip_lines.append(f"Должность: {emp['position']}")
        if emp.get('email'):
            tooltip_lines.append(f"Email: {emp['email']}")

        usage_count = emp.get('usage_count', 0)
        if usage_count > 0:
            tooltip_lines.append(f"📊 Использован в {usage_count} задачах")

        checkbox.setToolTip("\n".join(tooltip_lines) if tooltip_lines else "Нет дополнительной информации")

        if emp['id'] in self.selected_employees:
            checkbox.setChecked(True)

        # Отключаем чекбокс (только для просмотра)
        checkbox.setEnabled(False)

        return checkbox

    def _create_checkbox(self, emp: Dict) -> QCheckBox:
        """Создает активный чекбокс для редактирования"""
        display_text = emp['full_name']
        checkbox = QCheckBox(display_text)

        tooltip_lines = []
        if emp.get('position'):
            tooltip_lines.append(f"Должность: {emp['position']}")
        if emp.get('email'):
            tooltip_lines.append(f"Email: {emp['email']}")

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
        if self.readonly_mode:
            return
        if state == Qt.CheckState.Checked.value:
            self.selected_employees.add(emp_id)
        elif state == Qt.CheckState.Unchecked.value:
            self.selected_employees.discard(emp_id)

        self.update_selected_count()

    def on_select_all_changed(self, state):
        """Обработка изменения состояния чекбокса 'Выбрать всех'"""
        if self.readonly_mode:
            return

        self.selectAllCheckBox.blockSignals(True)

        if state == Qt.CheckState.Checked.value:
            for emp in self.filtered_employees:
                self.selected_employees.add(emp['id'])
        elif state == Qt.CheckState.Unchecked.value:
            for emp in self.filtered_employees:
                self.selected_employees.discard(emp['id'])

        self._update_checkboxes_state()
        self.update_selected_count()

        self.selectAllCheckBox.blockSignals(False)
        self.sort_employees()

    def update_selected_count(self):
        """Обновление счетчика выбранных сотрудников"""
        count = len(self.selected_employees)
        if hasattr(self, 'selectedCountLabel'):
            self.selectedCountLabel.setText(f"Выбрано: {count}")

    def _update_checkboxes_state(self):
        """Обновляет состояние всех существующих чекбоксов"""
        for checkbox, emp_id in self.employee_checkbox_map.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(emp_id in self.selected_employees)
            checkbox.blockSignals(False)

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
        if not self.readonly_mode:
            self.employees_selected.emit(self.get_selected_employees())
        super().accept()