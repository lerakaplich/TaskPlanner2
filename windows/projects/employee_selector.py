# windows/projects/employee_selector.py

import os
import sys
from typing import List, Dict, Optional, Set
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QApplication, QVBoxLayout, QCheckBox, QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from database import get_tasks_session
from models.employees import ExternalEmployee
from sqlalchemy import select


class EmployeeSelectorDialog(QDialog):
    """
    Диалог выбора сотрудников с поиском и фильтрацией по отделам
    Используется для выбора как участников, так и администраторов проекта
    """

    # Сигнал для возврата выбранных сотрудников
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
        self.load_employees_from_db()  # 👈 Загружаем реальных сотрудников
        self.load_departments()
        self.selected_employees.clear()

        # Принудительно показываем всех сотрудников сразу
        QTimer.singleShot(0, self.apply_filters)

    def load_employees_from_db(self):
        """Загрузка реальных сотрудников из БД"""
        try:
            session = get_tasks_session()
            stmt = select(ExternalEmployee).order_by(ExternalEmployee.last_name)
            employees = session.scalars(stmt).all()

            self.all_employees = []
            for emp in employees:
                # Определяем отдел (пока заглушка, потом можно добавить из БД)
                department = "IT"
                if emp.position and "директор" in emp.position.lower():
                    department = "Руководство"
                elif emp.position and "менеджер" in emp.position.lower():
                    department = "Управление проектами"

                self.all_employees.append({
                    'id': emp.id,
                    'last_name': emp.last_name,
                    'first_name': emp.first_name,
                    'middle_name': emp.middle_name or '',
                    'position': emp.position or 'Сотрудник',
                    'department': department,
                    'sub_department': '',
                    'phone': emp.phone_number or '',
                    'is_admin': emp.rights == 'superadmin' if emp.rights else False
                })

            print(f"✅ Загружено {len(self.all_employees)} сотрудников из БД")
            session.close()

        except Exception as e:
            print(f"❌ Ошибка загрузки сотрудников из БД: {e}")
            # Если не удалось загрузить, используем тестовые данные
            self.load_test_data()

    def load_departments(self):
        """Загрузка отделов БЕЗ лишних сигналов"""
        departments = {emp['department'] for emp in self.all_employees if emp['department']}

        self.departmentFilter.blockSignals(True)
        self.departmentFilter.clear()
        self.departmentFilter.addItem("Все отделы", None)
        for dept in sorted(departments):
            self.departmentFilter.addItem(dept, dept)
        self.departmentFilter.setCurrentIndex(0)
        self.departmentFilter.blockSignals(False)

        self.load_sub_departments(None)  # для "Все отделы"

    def showEvent(self, event):
        """Срабатывает каждый раз при открытии диалога"""
        super().showEvent(event)
        self.searchInput.clear()
        # Сбрасываем фильтры без лишних сигналов
        self.departmentFilter.blockSignals(True)
        self.departmentFilter.setCurrentIndex(0)
        self.departmentFilter.blockSignals(False)
        self.selected_employees.clear()
        QTimer.singleShot(0, self.apply_filters)

    def load_test_data(self):
        """Загрузка тестовых данных о сотрудниках (резервный вариант)"""
        self.all_employees = [
            {
                'id': 1,
                'last_name': 'Копейкина',
                'first_name': 'Виктория',
                'middle_name': 'Анатольевна',
                'position': 'Руководитель',
                'department': 'Руководство',
                'sub_department': '',
                'phone': '+375 44 574-24-34',
                'is_admin': True
            },
            {
                'id': 2,
                'last_name': 'Каплич',
                'first_name': 'Валерия',
                'middle_name': 'Александровна',
                'position': 'Разработчик',
                'department': 'IT',
                'sub_department': 'Разработка',
                'phone': '+375 29 523-30-26',
                'is_admin': False
            },
            {
                'id': 3,
                'last_name': 'Шершнева',
                'first_name': 'Елена',
                'middle_name': 'Сергеевна',
                'position': 'Аналитик',
                'department': 'Управление проектами',
                'sub_department': 'Аналитика',
                'phone': '+375 29 792-27-24',
                'is_admin': False
            }
        ]
        print("⚠️ Используются тестовые данные сотрудников")

    def load_sub_departments(self, department):
        """Загрузка подразделений"""
        self.subDepartmentFilter.blockSignals(True)
        self.subDepartmentFilter.clear()

        if not department or department == "Все отделы":
            self.subDepartmentFilter.addItem("Все подразделения", None)
            self.subDepartmentFilter.setEnabled(False)
        else:
            sub_departments = {emp['sub_department'] for emp in self.all_employees
                               if emp['department'] == department and emp['sub_department']}
            self.subDepartmentFilter.addItem("Все подразделения", None)
            for sub in sorted(sub_departments):
                self.subDepartmentFilter.addItem(sub, sub)
            self.subDepartmentFilter.setEnabled(True)
            self.subDepartmentFilter.setCurrentIndex(0)

        self.subDepartmentFilter.blockSignals(False)

    def on_department_changed(self, department):
        """Обработка изменения выбранного отдела"""
        self.load_sub_departments(department)
        self.apply_filters()

    def on_search_text_changed(self, text):
        """Запуск таймера поиска при вводе текста"""
        self.search_timer.start(300)  # Задержка 300 мс

    def apply_filters(self):
        """Применение всех фильтров (поиск, отдел, подразделение)"""
        search_text = self.searchInput.text().lower().strip()
        selected_dept = self.departmentFilter.currentData()
        selected_sub = self.subDepartmentFilter.currentData()

        self.filtered_employees = []

        for emp in self.all_employees:
            # Фильтр по отделу
            if selected_dept and selected_dept != "Все отделы":
                if emp['department'] != selected_dept:
                    continue

            # Фильтр по подразделению
            if selected_sub and selected_sub != "Все подразделения":
                if emp['sub_department'] != selected_sub:
                    continue

            # Поиск по имени и фамилии
            if search_text:
                full_name = f"{emp['last_name']} {emp['first_name']} {emp['middle_name']}".lower()
                if (search_text not in full_name and
                        search_text not in emp['last_name'].lower() and
                        search_text not in emp['first_name'].lower()):
                    continue

            self.filtered_employees.append(emp)

        self.display_employees()

    # windows/projects/employee_selector.py

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

        # Создаём чекбоксы
        for emp in self.filtered_employees:
            full_name = f"{emp['last_name']} {emp['first_name']}"
            if emp.get('middle_name'):
                full_name += f" {emp['middle_name']}"

            info = []
            if emp.get('position'):
                info.append(emp['position'])
            if emp.get('department'):
                info.append(f"({emp['department']})")
            display_text = f"{full_name} — {' '.join(info)}" if info else full_name

            checkbox = QCheckBox(display_text)
            if emp.get('phone'):
                checkbox.setToolTip(f"Телефон: {emp['phone']}")

            self.employee_checkbox_map[checkbox] = emp['id']

            if emp['id'] in self.selected_employees:
                checkbox.setChecked(True)

            # 👈 ИСПРАВЛЕНО: используем partial из functools
            from functools import partial
            checkbox.stateChanged.connect(partial(self._on_checkbox_changed, emp['id']))

            layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)

        layout.addStretch()
        self.update_selected_count()

    def _on_checkbox_changed(self, emp_id: int, state):
        """Обработчик изменения состояния чекбокса"""
        print(f"📊 Чекбокс изменен: ID={emp_id}, state={state}")  # 👈 ОТЛАДКА

        if state == Qt.CheckState.Checked.value:  # 👈 ИСПРАВЛЕНО: используем .value
            self.selected_employees.add(emp_id)
            print(f"✅ Добавлен ID: {emp_id}")
        elif state == Qt.CheckState.Unchecked.value:  # 👈 ИСПРАВЛЕНО: используем .value
            self.selected_employees.discard(emp_id)
            print(f"❌ Удален ID: {emp_id}")

        self.update_selected_count()
        self._update_select_all_state()

    def _update_select_all_state(self):
        if len(self.selected_employees) == len(self.filtered_employees):
            self.selectAllCheckBox.setCheckState(Qt.CheckState.Checked)
        elif self.selectAllCheckBox.checkState() == Qt.CheckState.Checked:
            self.selectAllCheckBox.setCheckState(Qt.CheckState.Unchecked)

    def on_select_all_changed(self, state):
        """Обработка изменения состояния чекбокса 'Выбрать всех'"""
        if state == Qt.CheckState.Checked:
            for emp in self.filtered_employees:
                self.selected_employees.add(emp['id'])
            for checkbox in self.checkboxes:
                checkbox.setChecked(True)
        elif state == Qt.CheckState.Unchecked:
            for emp in self.filtered_employees:
                self.selected_employees.discard(emp['id'])
            for checkbox in self.checkboxes:
                checkbox.setChecked(False)
        self.update_selected_count()

    def update_selected_count(self):
        """Обновление счетчика выбранных сотрудников"""
        count = len(self.selected_employees)
        self.selectedCountLabel.setText(f"Выбрано: {count}")
        print(f"📊 Выбрано сотрудников: {count}, IDs: {sorted(self.selected_employees)}")  # 👈 ОТЛАДКА

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
        self.display_employees()

    def accept(self):
        """Переопределяем accept для возврата данных"""
        self.employees_selected.emit(self.get_selected_employees())
        super().accept()