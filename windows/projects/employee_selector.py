import os
import sys
from typing import List, Dict, Optional, Set
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QApplication, QVBoxLayout, QCheckBox, QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal


class EmployeeSelectorDialog(QDialog):
    """
    Диалог выбора сотрудников с поиском и фильтрацией по отделам
    Используется для выбора как участников, так и администраторов проекта
    """

    # Сигнал для возврата выбранных сотрудников
    employees_selected = pyqtSignal(list)

    def __init__(self, parent=None, mode="participants"):
        """
        :param parent: родительский виджет
        :param mode: режим работы ("participants" - участники, "admins" - администраторы)
        """
        super().__init__(parent)
        self.mode = mode
        self.all_employees = []  # Все сотрудники из тестовых данных
        self.filtered_employees = []  # Отфильтрованные сотрудники
        self.checkboxes = []  # Список чекбоксов
        self.selected_employees = set()  # Множество выбранных ID
        self.employee_checkbox_map = {}  # Словарь для связи чекбокса с ID сотрудника
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filters)

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/projects/
            "..", "..",  # поднимаемся до корня проекта
            "ui", "projects"  # спускаемся в нужную подпапку ui
        )
        uic.loadUi(os.path.join(ui_path, "employee_selector.ui"), self)

        # Подключение сигналов
        self.searchInput.textChanged.connect(self.on_search_text_changed)
        self.departmentFilter.currentTextChanged.connect(self.on_department_changed)
        self.selectAllCheckBox.stateChanged.connect(self.on_select_all_changed)
        self.selectBtn.clicked.connect(self.accept)

        # Загрузка тестовых данных
        self.load_test_data()
        self.load_departments()
        self.display_employees()

    def load_test_data(self):
        """Загрузка тестовых данных о сотрудниках"""
        self.all_employees = [
            {
                'id': 1,
                'last_name': 'Иванов',
                'first_name': 'Иван',
                'middle_name': 'Иванович',
                'position': 'Генеральный директор',
                'department': 'Руководство',
                'sub_department': '',
                'phone': '+7 (999) 123-45-67',
                'is_admin': True
            },
            {
                'id': 2,
                'last_name': 'Петров',
                'first_name': 'Петр',
                'middle_name': 'Петрович',
                'position': 'Технический директор',
                'department': 'Руководство',
                'sub_department': '',
                'phone': '+7 (999) 234-56-78',
                'is_admin': True
            },
            {
                'id': 3,
                'last_name': 'Сидорова',
                'first_name': 'Анна',
                'middle_name': 'Сергеевна',
                'position': 'Ведущий разработчик',
                'department': 'IT',
                'sub_department': 'Разработка',
                'phone': '+7 (999) 345-67-89',
                'is_admin': False
            },
            {
                'id': 4,
                'last_name': 'Козлов',
                'first_name': 'Дмитрий',
                'middle_name': 'Алексеевич',
                'position': 'Разработчик',
                'department': 'IT',
                'sub_department': 'Разработка',
                'phone': '+7 (999) 456-78-90',
                'is_admin': False
            },
            {
                'id': 5,
                'last_name': 'Морозова',
                'first_name': 'Елена',
                'middle_name': 'Владимировна',
                'position': 'Тестировщик',
                'department': 'IT',
                'sub_department': 'Тестирование',
                'phone': '+7 (999) 567-89-01',
                'is_admin': False
            },
            {
                'id': 6,
                'last_name': 'Волков',
                'first_name': 'Александр',
                'middle_name': 'Игоревич',
                'position': 'Системный администратор',
                'department': 'IT',
                'sub_department': 'Инфраструктура',
                'phone': '+7 (999) 678-90-12',
                'is_admin': False
            },
            {
                'id': 7,
                'last_name': 'Соколова',
                'first_name': 'Мария',
                'middle_name': 'Дмитриевна',
                'position': 'Менеджер проектов',
                'department': 'Управление проектами',
                'sub_department': '',
                'phone': '+7 (999) 789-01-23',
                'is_admin': True
            },
            {
                'id': 8,
                'last_name': 'Лебедев',
                'first_name': 'Андрей',
                'middle_name': 'Николаевич',
                'position': 'Аналитик',
                'department': 'Управление проектами',
                'sub_department': 'Аналитика',
                'phone': '+7 (999) 890-12-34',
                'is_admin': False
            },
            {
                'id': 9,
                'last_name': 'Новикова',
                'first_name': 'Татьяна',
                'middle_name': 'Александровна',
                'position': 'Дизайнер',
                'department': 'Маркетинг',
                'sub_department': 'Дизайн',
                'phone': '+7 (999) 901-23-45',
                'is_admin': False
            },
            {
                'id': 10,
                'last_name': 'Федоров',
                'first_name': 'Максим',
                'middle_name': 'Олегович',
                'position': 'Маркетолог',
                'department': 'Маркетинг',
                'sub_department': 'Продвижение',
                'phone': '+7 (999) 012-34-56',
                'is_admin': False
            },
            {
                'id': 11,
                'last_name': 'Михайлов',
                'first_name': 'Михаил',
                'middle_name': 'Михайлович',
                'position': 'HR-менеджер',
                'department': 'HR',
                'sub_department': '',
                'phone': '+7 (999) 123-45-67',
                'is_admin': False
            },
            {
                'id': 12,
                'last_name': 'Алексеева',
                'first_name': 'Наталья',
                'middle_name': 'Павловна',
                'position': 'Бухгалтер',
                'department': 'Финансы',
                'sub_department': 'Бухгалтерия',
                'phone': '+7 (999) 234-56-78',
                'is_admin': False
            },
            {
                'id': 13,
                'last_name': 'Григорьев',
                'first_name': 'Сергей',
                'middle_name': 'Викторович',
                'position': 'Финансовый аналитик',
                'department': 'Финансы',
                'sub_department': 'Аналитика',
                'phone': '+7 (999) 345-67-89',
                'is_admin': False
            },
            {
                'id': 14,
                'last_name': 'Васильева',
                'first_name': 'Ольга',
                'middle_name': 'Ивановна',
                'position': 'Секретарь',
                'department': 'Администрация',
                'sub_department': '',
                'phone': '+7 (999) 456-78-90',
                'is_admin': False
            },
            {
                'id': 15,
                'last_name': 'Павлов',
                'first_name': 'Денис',
                'middle_name': 'Сергеевич',
                'position': 'DevOps-инженер',
                'department': 'IT',
                'sub_department': 'Инфраструктура',
                'phone': '+7 (999) 567-89-01',
                'is_admin': False
            }
        ]


    # 2. В методе on_select_all_changed
    def on_select_all_changed(self, state):
        """Обработка изменения состояния чекбокса 'Выбрать всех'"""
        if state == Qt.CheckState.Checked:  # ← исправлено
            for emp in self.filtered_employees:
                self.selected_employees.add(emp['id'])
            for checkbox, emp in zip(self.checkboxes, self.filtered_employees):
                checkbox.setChecked(True)
        elif state == Qt.CheckState.Unchecked:  # ← исправлено
            for emp in self.filtered_employees:
                self.selected_employees.discard(emp['id'])
            for checkbox in self.checkboxes:
                checkbox.setChecked(False)
        self.update_selected_count()

    def load_departments(self):
        """Загрузка списка отделов из тестовых данных"""
        departments = set()
        for emp in self.all_employees:
            if emp['department']:
                departments.add(emp['department'])

        self.departmentFilter.clear()
        self.departmentFilter.addItem("Все отделы", None)

        for dept in sorted(departments):
            self.departmentFilter.addItem(dept, dept)

    def load_sub_departments(self, department):
        """Загрузка подразделений для выбранного отдела"""
        if not department or department == "Все отделы":
            self.subDepartmentFilter.clear()
            self.subDepartmentFilter.addItem("Все подразделения", None)
            self.subDepartmentFilter.setEnabled(False)
            return

        sub_departments = set()
        for emp in self.all_employees:
            if emp['department'] == department and emp['sub_department']:
                sub_departments.add(emp['sub_department'])

        self.subDepartmentFilter.clear()
        self.subDepartmentFilter.addItem("Все подразделения", None)
        self.subDepartmentFilter.setEnabled(True)

        for sub in sorted(sub_departments):
            self.subDepartmentFilter.addItem(sub, sub)

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

    def display_employees(self):
        """Отображение отфильтрованных сотрудников с чекбоксами"""
        # Очищаем старые чекбоксы
        layout = self.scrollAreaWidgetContents.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.checkboxes = []
        self.employee_checkbox_map.clear()

        if not self.filtered_employees:
            # Показываем сообщение, если нет результатов
            label = QLabel("Сотрудники не найдены")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #B8B8B5; font-size: 14px; padding: 20px;")
            layout.addWidget(label)
            self.selectAllCheckBox.setChecked(False)
            self.selectAllCheckBox.setEnabled(False)
            self.update_selected_count()
            return

        self.selectAllCheckBox.setEnabled(True)

        # Создаем чекбоксы для каждого сотрудника
        for emp in self.filtered_employees:
            full_name = f"{emp['last_name']} {emp['first_name']}"
            if emp['middle_name']:
                full_name += f" {emp['middle_name']}"

            # Формируем текст с должностью и отделом
            info_parts = []
            if emp['position']:
                info_parts.append(emp['position'])
            if emp['department']:
                info_parts.append(f"({emp['department']})")

            info_text = " ".join(info_parts)
            if info_text:
                display_text = f"{full_name} — {info_text}"
            else:
                display_text = full_name

            checkbox = QCheckBox(display_text)

            # Добавляем номер телефона в tooltip
            if emp['phone']:
                checkbox.setToolTip(f"Телефон: {emp['phone']}")

            # Сохраняем ID сотрудника для этого чекбокса
            self.employee_checkbox_map[checkbox] = emp['id']

            # Устанавливаем состояние чекбокса
            if emp['id'] in self.selected_employees:
                checkbox.setChecked(True)

            # Подключаем сигнал - ИСПРАВЛЕНО: используем отдельный метод
            checkbox.stateChanged.connect(
                lambda checked, eid=emp['id']: self._handle_checkbox(eid, checked)
            )

            layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)

        # Добавляем растяжку в конце
        layout.addStretch()

        self.update_selected_count()

    def _handle_checkbox(self, emp_id: int, state):
        """Простой обработчик для одного чекбокса"""
        if state == Qt.CheckState.Checked:
            self.selected_employees.add(emp_id)
        else:
            self.selected_employees.discard(emp_id)

        self.update_selected_count()
        self._update_select_all_state()

    def _update_select_all_state(self):
        if len(self.selected_employees) == len(self.filtered_employees):
            self.selectAllCheckBox.setCheckState(Qt.CheckState.Checked)
        elif self.selectAllCheckBox.checkState() == Qt.CheckState.Checked:
            self.selectAllCheckBox.setCheckState(Qt.CheckState.Unchecked)

    def on_checkbox_state_changed(self, state):
        """Обработка изменения состояния любого чекбокса"""
        checkbox = self.sender()
        if checkbox is None:
            return

        emp_id = self.employee_checkbox_map.get(checkbox)
        if emp_id is None:
            return

        # ИСПРАВЛЕНО
        if state == Qt.CheckState.Checked:
            self.selected_employees.add(emp_id)
        else:
            self.selected_employees.discard(emp_id)

        self.update_selected_count()

        # Обновляем "Выбрать всех"
        if len(self.selected_employees) == len(self.filtered_employees):
            self.selectAllCheckBox.setCheckState(Qt.CheckState.Checked)
        elif self.selectAllCheckBox.checkState() == Qt.CheckState.Checked:
            self.selectAllCheckBox.setCheckState(Qt.CheckState.Unchecked)


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
        self.display_employees()

    def accept(self):
        """Переопределяем accept для возврата данных"""
        self.employees_selected.emit(self.get_selected_employees())
        super().accept()


# Для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Создаем диалог в режиме выбора участников
    dialog = EmployeeSelectorDialog(mode="participants")

    # Можно предустановить выбранных сотрудников (например, Иванова и Петрова)
    # dialog.set_preselected([1, 2])

    if dialog.exec() == QDialog.DialogCode.Accepted:
        selected = dialog.get_selected_employees()
        print("Выбраны сотрудники:")
        for emp in selected:
            print(f"- {emp['last_name']} {emp['first_name']} (ID: {emp['id']}, Отдел: {emp['department']})")

    sys.exit(app.exec())