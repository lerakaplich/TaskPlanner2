from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QMessageBox, QTabWidget
from PyQt6.QtCore import pyqtSignal
import os

# Импорт вкладок (все наследуются от BaseTab)
from windows.settings.columns.columns_tab import ColumnsTab
from windows.settings.tags.tags_tab import TagsTab
from windows.settings.employees.employees_tab import EmployeesTab
from windows.settings.departments.departments_tab import DepartmentsTab
from windows.settings.divisions.divisions_tab import DivisionsTab

# windows/settings/settings_page.py

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QMessageBox, QTabWidget
from PyQt6.QtCore import pyqtSignal
import os

from windows.settings.columns.columns_tab import ColumnsTab
from windows.settings.tags.tags_tab import TagsTab
from windows.settings.employees.employees_tab import EmployeesTab
from windows.settings.departments.departments_tab import DepartmentsTab
from windows.settings.divisions.divisions_tab import DivisionsTab
from services.employee_service import EmployeeService


class SettingsPage(QWidget):
    """Страница настроек с вкладками"""

    item_added = pyqtSignal(str, dict)
    item_edited = pyqtSignal(str, dict)
    item_deleted = pyqtSignal(str, int)

    def __init__(self, parent=None, session=None):  # ← ДОБАВЬТЕ session
        super().__init__(parent)

        self.session = session  # ← СОХРАНЯЕМ СЕССИЮ

        self.all_employees = []
        self.all_departments = []
        self.all_divisions = []
        self.all_tags = []
        self.all_columns = []

        # Загрузка основного UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "settings", "settings_page.ui"
        )

        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"Файл не найден: {ui_path}")

        uic.loadUi(ui_path, self)

        self.setup_tabs()

        # Загружаем реальные данные из БД
        if self.session:
            self.load_data_from_db()
        else:
            self.load_sample_data()  # fallback

    def setup_tabs(self):
        """Создание и настройка всех вкладок"""
        # Создаём вкладки
        self.tags_tab = TagsTab()
        self.employees_tab = EmployeesTab()
        self.departments_tab = DepartmentsTab()
        self.divisions_tab = DivisionsTab()
        self.columns_tab = ColumnsTab()

        # Если есть сессия, передаём сервис во вкладку сотрудников
        if hasattr(self, 'session') and self.session:
            employee_service = EmployeeService(self.session)
            self.employees_tab.set_employee_service(employee_service)
            self.employees_tab.set_session(self.session)  # ← ДОБАВЬТЕ ЭТУ СТРОКУ

            # Передаём session во вкладки отделов и подразделений
            self.departments_tab.set_session(self.session)
            self.divisions_tab.set_session(self.session)
            self.columns_tab.set_session(self.session)

        # Подключаем сигналы
        self.tags_tab.item_deleted.connect(self.on_item_deleted)
        self.employees_tab.item_deleted.connect(self.on_item_deleted)
        self.departments_tab.item_deleted.connect(self.on_item_deleted)
        self.divisions_tab.item_deleted.connect(self.on_item_deleted)
        self.columns_tab.item_deleted.connect(self.on_item_deleted)  # ← Убедитесь, что это есть
        self.divisions_tab.item_deleted.connect(self.on_division_deleted)
        self.columns_tab.item_deleted.connect(self.on_item_deleted)

        # Подключаем сигналы добавления/обновления сотрудников
        self.employees_tab.employee_added.connect(lambda data: self.on_item_added("employee", data))
        self.employees_tab.employee_updated.connect(lambda data: self.on_item_edited("employee", data))

        # Подключаем сигналы изменения цвета
        self.tags_tab.item_color_changed.connect(self.on_tag_color_changed)
        self.columns_tab.item_color_changed.connect(self.on_column_color_changed)

        # Добавляем вкладки
        if hasattr(self, 'tabWidget') and isinstance(self.tabWidget, QTabWidget):
            self.tabWidget.clear()
            self.tabWidget.addTab(self.employees_tab, "Сотрудники")
            self.tabWidget.addTab(self.departments_tab, "Отделы")
            self.tabWidget.addTab(self.divisions_tab, "Подразделения")
            self.tabWidget.addTab(self.columns_tab, "Колонки")
            self.tabWidget.addTab(self.tags_tab, "Хэштеги")

        # Настройка фильтров
        self.setup_employees_filters()

        # Подключаем смену вкладки
        if hasattr(self, 'tabWidget'):
            self.tabWidget.currentChanged.connect(self.on_tab_changed)

    def on_item_added(self, item_type: str, data: dict):
        """Обработчик добавления элемента"""
        print(f"Добавлен {item_type}: {data}")
        self.item_added.emit(item_type, data)

    def on_item_edited(self, item_type: str, data: dict):
        """Обработчик редактирования элемента"""
        print(f"Изменён {item_type}: {data}")
        self.item_edited.emit(item_type, data)

    # windows/settings/settings_page.py

    def load_data_from_db(self):
        """Загрузка реальных данных из БД"""
        from services.employee_service import EmployeeService
        from services.column_service import ColumnService  # ← ДОБАВИТЬ

        employee_service = EmployeeService(self.session)
        column_service = ColumnService(self.session)  # ← ДОБАВИТЬ

        # Загружаем сотрудников
        self.all_employees = employee_service.get_all_employees()
        self.employees_tab.load_data(self.all_employees)

        # Загружаем отделы
        self.all_departments = employee_service.get_all_departments()
        self.departments_tab.load_data(self.all_departments)
        self.departments_tab.set_employees(self.all_employees)

        # Загружаем подразделения
        self.all_divisions = employee_service.get_all_divisions()
        self.departments_tab.all_divisions = self.all_divisions
        self.departments_tab.load_division_filters()
        self.divisions_tab.load_data(self.all_divisions)
        self.divisions_tab.set_employees(self.all_employees)

        # Загружаем колонки (шаблоны)  ← ДОБАВИТЬ ЭТУ СЕКЦИЮ
        self.all_columns = column_service.get_template_columns()
        print(f"📊 Загружено шаблонов колонок из БД: {len(self.all_columns)}")
        self.columns_tab.load_data(self.all_columns)

        # Настраиваем фильтры
        self.employees_tab.load_filter_data(self.all_departments, self.all_divisions)

    def on_division_deleted(self, item_type: str, division_id: int):
        """Обработка удаления подразделения"""
        if item_type == "division":
            from services.employee_service import EmployeeService
            employee_service = EmployeeService(self.session)

            if employee_service.delete_division_in_db(division_id):
                # Обновляем локальный список
                self.all_divisions = [d for d in self.all_divisions if d.get('id') != division_id]
                self.divisions_tab.load_data(self.all_divisions)
                QMessageBox.information(self, "Успех", "Подразделение удалено")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить подразделение")

    def setup_employees_filters(self):
        """Настройка фильтров во вкладке Сотрудники"""
        if hasattr(self.employees_tab, 'setup_filters'):
            self.employees_tab.setup_filters(
                self.all_departments,
                self.all_divisions
            )

    def connect_add_buttons(self):
        """Подключение кнопок "Добавить" из вкладок"""
        # Кнопки теперь находятся внутри каждой вкладки (self.btnAddXXX)
        if hasattr(self.tags_tab, 'btnAddTag'):
            self.tags_tab.btnAddTag.clicked.connect(lambda: self.add_item("tag"))

        if hasattr(self.employees_tab, 'btnAddEmployee'):
            self.employees_tab.btnAddEmployee.clicked.connect(lambda: self.add_item("employee"))

        if hasattr(self.departments_tab, 'btnAddDepartment'):
            self.departments_tab.btnAddDepartment.clicked.connect(lambda: self.add_item("department"))

        if hasattr(self.divisions_tab, 'btnAddDivision'):
            self.divisions_tab.btnAddDivision.clicked.connect(lambda: self.add_item("division"))

        if hasattr(self.columns_tab, 'btnAddColumn'):
            self.columns_tab.btnAddColumn.clicked.connect(lambda: self.add_item("column"))

    def add_item(self, item_type: str):
        """Вызывается при нажатии кнопки "Добавить" """
        type_names = {
            "tag": "тег",
            "employee": "сотрудника",
            "department": "отдел",
            "division": "подразделение",
            "column": "колонку"
        }
        name = type_names.get(item_type, "элемент")
        QMessageBox.information(self, "Добавление",
                                f"Здесь будет открыта форма добавления нового {name}")

        # В будущем здесь можно эмитировать сигнал:
        # self.item_added.emit(item_type, {})

    def on_item_deleted(self, item_type: str, item_id: int):
        """Обработчик удаления из любой вкладки"""
        print(f"Удалён {item_type} с ID = {item_id}")
        self.item_deleted.emit(item_type, item_id)

    def on_column_color_changed(self, column_id: int, new_color: str):
        """Изменение цвета колонки"""
        print(f"Цвет колонки {column_id} изменён на {new_color}")

        for column in self.all_columns:
            if column.get('id') == column_id:
                column['color'] = new_color
                break

        self.item_edited.emit("column", {"id": column_id, "color": new_color})

    def on_tag_color_changed(self, tag_id: int, new_color: str):
        """Изменение цвета тега"""
        print(f"Цвет тега {tag_id} изменён на {new_color}")

        for tag in self.all_tags:
            if tag.get('id') == tag_id:
                tag['color'] = new_color
                break

        self.item_edited.emit("tag", {"id": tag_id, "color": new_color})

    def on_tab_changed(self, index: int):
        """Срабатывает при смене вкладки"""
        tab_names = ["Сотрудники", "Отделы", "Подразделения", "Колонки", "Хэштеги"]
        if index < len(tab_names):
            print(f"Переключено на вкладку: {tab_names[index]}")

    def load_sample_data(self):
        """Загрузка тестовых данных"""
        # Теги
        self.all_tags = [
            {"id": 1, "name": "проект", "color": "#ccab6e", "count": 15},
            {"id": 2, "name": "срочно", "color": "#ff6b6b", "count": 8},
            {"id": 3, "name": "важно", "color": "#4ecdc4", "count": 12},
            {"id": 4, "name": "обучение", "color": "#45b7d1", "count": 5},
            {"id": 5, "name": "отчет", "color": "#96ceb4", "count": 10},
        ]

        # Отделы
        self.all_departments = [
            {"id": 1, "number": 101, "name": "IT отдел", "boss": "Иванов И.И.",
             "phone_number": "+375 (17) 123-45-67", "division": "Северное подразделение"},
            {"id": 2, "number": 102, "name": "HR отдел", "boss": "Петрова А.С.",
             "division": "Центральное подразделение"},
            {"id": 3, "number": 103, "name": "Бухгалтерия",
             "bosses": ["Сидоров П.П.", "Козлова Е.В."], "phone_number": "+375 (17) 234-56-78",
             "division": "Южное подразделение"},
        ]

        # Подразделения
        self.all_divisions = [
            {"id": 1, "number": 1, "name": "Северное подразделение", "boss": "Козлов А.А.",
             "phone_number": "+375 (17) 111-22-33", "workshop_code": "С-001"},
            {"id": 2, "number": 2, "name": "Южное подразделение", "boss": "Морозов В.В.",
             "phone_number": "+375 (17) 444-55-66", "workshop_code": "Ю-002"},
            {"id": 3, "number": 3, "name": "Центральное подразделение", "boss": "Весенний Г.Г.",
             "workshop_code": "Ц-003"},
        ]

        # Сотрудники
        self.all_employees = [
            {"id": 1, "last_name": "Иванов", "first_name": "Иван", "middle_name": "Иванович",
             "position": "Ведущий разработчик", "department": self.all_departments[0],
             "department_id": 1, "division": self.all_divisions[0], "division_id": 1,
             "phone_number": "+375 (29) 123-45-67", "email": "ivanov@company.com", "rights": "admin"},
            {"id": 2, "last_name": "Петрова", "first_name": "Анна", "middle_name": "Сергеевна",
             "position": "HR-менеджер", "department": self.all_departments[1], "department_id": 2,
             "division": self.all_divisions[2], "division_id": 3,
             "phone_number": "+375 (33) 234-56-78", "email": "petrova@company.com", "rights": "user"},
            {"id": 3, "last_name": "Сидоров", "first_name": "Петр", "middle_name": "Петрович",
             "position": "Системный администратор", "department": self.all_departments[0], "department_id": 1,
             "division": self.all_divisions[1], "division_id": 2,
             "phone_number": "+375 (29) 345-67-89", "rights": "superadmin"},
            {"id": 4, "last_name": "Козлова", "first_name": "Елена", "middle_name": "Владимировна",
             "position": "Бухгалтер", "department": self.all_departments[2], "department_id": 3,
             "division": self.all_divisions[0], "division_id": 1,
             "phone_number": "+375 (29) 456-78-90", "email": "kozlova@company.com", "rights": "user"},
            {"id": 5, "last_name": "Морозов", "first_name": "Дмитрий", "middle_name": "Александрович",
             "position": "Начальник отдела", "department": self.all_departments[0], "department_id": 1,
             "division": self.all_divisions[2], "division_id": 3,
             "phone_number": "+375 (33) 567-89-01", "email": "morozov@company.com", "rights": "admin"}
        ]
        self.all_columns = [
            {"id": 1, "project_id": 1, "name": "К выполнению", "color": "#ccab6e", "position": 1,
             "is_done_column": False},
            {"id": 2, "project_id": 1, "name": "В работе", "color": "#45b7d1", "position": 2, "is_done_column": False},
            {"id": 3, "project_id": 1, "name": "На проверке", "color": "#f9ca24", "position": 3,
             "is_done_column": False},
            {"id": 4, "project_id": 1, "name": "Готово", "color": "#6ab04c", "position": 4, "is_done_column": True},
        ]
        # Загружаем данные во вкладки

        self.tags_tab.load_data(self.all_tags)
        self.employees_tab.load_data(self.all_employees)
        self.departments_tab.load_data(self.all_departments)
        self.divisions_tab.load_data(self.all_divisions)
        self.columns_tab.load_data(self.all_columns)
        # Загружаем данные для фильтров сотрудников
        self.employees_tab.load_filter_data(self.all_departments, self.all_divisions)