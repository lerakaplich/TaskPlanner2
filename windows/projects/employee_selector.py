# windows/projects/employee_selector.py

import os
import sys
from typing import List, Dict, Optional, Set
from collections import Counter
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QApplication, QVBoxLayout, QCheckBox, QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from database import get_employees_session, get_tasks_session  # ← ДОБАВИТЬ get_tasks_session
from models.employees import Employee, Division, Department, EmployeeData  # ← ДОБАВИТЬ EmployeeData
from sqlalchemy import select, func


class EmployeeSelectorDialog(QDialog):
    """Диалог выбора сотрудников с поиском и фильтрацией"""

    employees_selected = pyqtSignal(list)

    def __init__(self, parent=None, mode="participants"):
        super().__init__(parent)
        self.mode = mode
        self.all_employees = []
        self.filtered_employees = []
        self.checkboxes = []
        self.selected_employees = set()
        self.employee_checkbox_map = {}
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filters)

        # Статистика использования сотрудников
        self.employee_usage_count = Counter()
        # Кэш для ролей сотрудников
        self.employee_role_cache = {}

        # Кэш для подразделений и отделов
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
        self.load_divisions()
        self.load_departments()
        self.load_employee_roles()  # ← НОВЫЙ МЕТОД
        self.load_employee_usage_stats()
        self.load_employees_from_db()
        self.setup_filters()
        self.selected_employees.clear()

        QTimer.singleShot(0, self.apply_filters)

    def load_divisions(self):
        """Загрузка списка подразделений из БД"""
        try:
            session = get_employees_session()
            divisions = session.query(Division).order_by(Division.name).all()
            self.divisions_list = [div.name for div in divisions if div.name]
            session.close()
            print(f"✅ Загружено подразделений: {len(self.divisions_list)}")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки подразделений: {e}")
            self.divisions_list = []

    def load_departments(self):
        """Загрузка списка отделов из БД"""
        try:
            session = get_employees_session()
            departments = session.query(Department).order_by(Department.name).all()
            self.departments_list = [dept.name for dept in departments if dept.name]
            session.close()
            print(f"✅ Загружено отделов: {len(self.departments_list)}")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки отделов: {e}")
            self.departments_list = []

    def load_employee_roles(self):
        """Загружает роли сотрудников из EmployeeData (БД taskplanner)"""
        try:
            tasks_session = get_tasks_session()
            if tasks_session:
                results = tasks_session.query(EmployeeData.employee_id, EmployeeData.role).all()
                for emp_id, role in results:
                    if role:
                        self.employee_role_cache[emp_id] = role.value if hasattr(role, 'value') else str(role)
                tasks_session.close()
                print(f"📊 Загружены роли для {len(self.employee_role_cache)} сотрудников")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки ролей: {e}")

    def load_employee_usage_stats(self):
        """Загружает статистику использования сотрудников в задачах"""
        try:
            from models.tasks import Task
            from database import get_tasks_session

            session = get_tasks_session()
            if session:
                results = session.query(Task.assigned_to, func.count(Task.id)).filter(
                    Task.assigned_to.isnot(None)
                ).group_by(Task.assigned_to).all()

                for emp_id, count in results:
                    self.employee_usage_count[emp_id] = count

                session.close()
                print(f"📊 Загружена статистика использования {len(self.employee_usage_count)} сотрудников")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки статистики: {e}")

    def load_employees_from_db(self):
        """Загрузка сотрудников из БД employees"""
        try:
            session = get_employees_session()
            employees = session.query(Employee).order_by(Employee.last_name).all()

            self.all_employees = []
            for emp in employees:
                full_name = self._get_full_name(emp)

                if full_name:
                    role = self.employee_role_cache.get(emp.id, 'user')
                    is_admin = role in ['admin', 'superadmin']

                    self.all_employees.append({
                        'id': emp.id,
                        'full_name': full_name,
                        'last_name': emp.last_name or '',
                        'first_name': emp.first_name or '',
                        'middle_name': emp.middle_name or '',
                        'position': emp.position or '',
                        'phone': emp.phone_number or '',
                        'email': emp.email or '',
                        'is_admin': is_admin,  # ← ИСПРАВЛЕНО
                        'usage_count': self.employee_usage_count.get(emp.id, 0),
                        'department_id': emp.department_id,
                        'division_id': emp.division_id,
                        'role': role  # ← ДОБАВИМ для информации
                    })

            session.close()
            print(f"✅ Загружено сотрудников: {len(self.all_employees)}")

        except Exception as e:
            print(f"❌ Ошибка загрузки сотрудников: {e}")
            import traceback
            traceback.print_exc()

    def _get_full_name(self, employee: Employee) -> str:
        """Формирует ФИО сотрудника"""
        parts = [employee.last_name, employee.first_name]
        if employee.middle_name:
            parts.append(employee.middle_name)
        return ' '.join(parts).strip()

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

        # Включаем фильтры, только если есть данные
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
        # Перезагружаем роли и статистику
        self.load_employee_roles()
        self.load_employee_usage_stats()
        self.load_employees_from_db()
        self.apply_filters()

    def on_department_changed(self, department):
        """Обработка изменения выбранного отдела"""
        self.apply_filters()

    def on_search_text_changed(self, text):
        """Запуск таймера поиска при вводе текста"""
        self.search_timer.start(300)

    def apply_filters(self):
        """Применение всех фильтров (поиск, отдел, подразделение)"""
        search_text = self.searchInput.text().lower().strip()
        selected_dept = self.departmentFilter.currentText()
        if selected_dept == "Все отделы":
            selected_dept = None
        selected_sub = self.subDepartmentFilter.currentText()
        if selected_sub == "Все подразделения":
            selected_sub = None

        filtered = []

        for emp in self.all_employees:
            # Поиск по ФИО
            if search_text:
                if search_text not in emp['full_name'].lower():
                    continue

            filtered.append(emp)

        self.filtered_employees = filtered
        self.sort_employees()
        self.display_employees()

    def sort_employees(self):
        """
        Сортировка сотрудников:
        1. Выбранные сотрудники (всегда вверху)
        2. Остальные сортируются по частоте использования (от большего к меньшему)
        """

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

        # Отображаем остальных с разделителем (если есть выбранные)
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
        """Создает чекбокс для сотрудника (только ФИО)"""

        # Только ФИО
        display_text = emp['full_name']

        checkbox = QCheckBox(display_text)

        # Вся дополнительная информация в tooltip
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

        from functools import partial
        checkbox.stateChanged.connect(partial(self._on_checkbox_changed, emp['id']))

        return checkbox

    def _on_checkbox_changed(self, emp_id: int, state):
        """Обработчик изменения состояния чекбокса"""
        if state == Qt.CheckState.Checked.value:
            self.selected_employees.add(emp_id)
            print(f"✅ Добавлен ID: {emp_id}")
        elif state == Qt.CheckState.Unchecked.value:
            self.selected_employees.discard(emp_id)
            print(f"❌ Удален ID: {emp_id}")

        # Обновляем сортировку и отображение (выбранные уходят вверх)
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