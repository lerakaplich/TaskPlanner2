# windows/settings/settings_page.py

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
from services.employee_service import EmployeeService
from database import get_employees_session


class SettingsPage(QWidget):
    """Страница настроек с вкладками"""

    item_added = pyqtSignal(str, dict)
    item_edited = pyqtSignal(str, dict)
    item_deleted = pyqtSignal(str, int)

    def __init__(self, parent=None, session=None):
        super().__init__(parent)

        self.employees_db_session = get_employees_session()
        self.session = session

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
        self.load_data_from_db()

    def setup_tabs(self):
        """Создание и настройка всех вкладок"""
        self.tags_tab = TagsTab()
        self.employees_tab = EmployeesTab()
        self.departments_tab = DepartmentsTab()
        self.divisions_tab = DivisionsTab()
        self.columns_tab = ColumnsTab()

        # ===== ИСПРАВЛЕНИЕ: используем employee_service для вкладок =====
        if hasattr(self, 'employees_db_session') and self.employees_db_session:
            employee_service = EmployeeService(self.employees_db_session)

            # Передаём сервис во вкладки
            self.employees_tab.set_employee_service(employee_service)
            self.departments_tab.set_employee_service(employee_service)
            self.divisions_tab.set_employee_service(employee_service)  # ← ИЗМЕНЕНО: вместо set_session

            # Передаём сессии для других вкладок
            self.columns_tab.set_session(self.session)
            self.tags_tab.set_session(self.session)
        else:
            print("⚠️ Нет employees_db_session для EmployeeService")

        # Подключаем сигналы
        self.tags_tab.item_deleted.connect(self.on_tag_deleted)
        self.tags_tab.item_deleted.connect(self.on_item_deleted)
        self.employees_tab.item_deleted.connect(self.on_item_deleted)
        self.departments_tab.item_deleted.connect(self.on_item_deleted)
        self.divisions_tab.item_deleted.connect(self.on_item_deleted)
        self.columns_tab.item_deleted.connect(self.on_item_deleted)
        self.divisions_tab.item_deleted.connect(self.on_division_deleted)

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
            self.tabWidget.addTab(self.tags_tab, "Темы")

        # Настройка фильтров
        self.setup_employees_filters()

        # Подключаем смену вкладки
        if hasattr(self, 'tabWidget'):
            self.tabWidget.currentChanged.connect(self.on_tab_changed)

    def on_tag_deleted(self, item_type: str, tag_id: int):
        """Обработчик удаления тега"""
        if item_type != "tag":
            return

        from services.tag_service import TagService
        tag_service = TagService(self.session)

        if tag_service.delete_tag(tag_id):
            self.all_tags = [t for t in self.all_tags if t.get('id') != tag_id]
            self.tags_tab.load_data(self.all_tags)
            QMessageBox.information(self, "Успех", "Тема удалена")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось удалить тему")

    def on_item_added(self, item_type: str, data: dict):
        """Обработчик добавления элемента"""
        print(f"Добавлен {item_type}: {data}")
        self.item_added.emit(item_type, data)

    def on_item_edited(self, item_type: str, data: dict):
        """Обработчик редактирования элемента"""
        print(f"Изменён {item_type}: {data}")
        self.item_edited.emit(item_type, data)

    def load_data_from_db(self):
        """Загрузка реальных данных из БД"""
        from services.employee_service import EmployeeService
        from services.column_service import ColumnService
        from services.tag_service import TagService

        employee_service = EmployeeService(self.employees_db_session)
        column_service = ColumnService(self.session)
        tag_service = TagService(self.session)

        # Загружаем сотрудников через сервис
        self.all_employees = employee_service.get_all_employees()
        self.employees_tab.load_data(self.all_employees)

        # Загружаем отделы
        self.all_departments = employee_service.get_all_departments()
        self.departments_tab.load_data(self.all_departments)

        # Загружаем подразделения
        self.all_divisions = employee_service.get_all_divisions()
        self.departments_tab.all_divisions = self.all_divisions
        self.departments_tab.load_division_filters()
        self.divisions_tab.load_data(self.all_divisions)

        # Загружаем колонки (шаблоны)
        self.all_columns = column_service.get_template_columns()
        print(f"📊 Загружено шаблонов колонок из БД: {len(self.all_columns)}")
        self.columns_tab.load_data(self.all_columns)

        # Загружаем темы
        self.all_tags = tag_service.get_all_tags()
        print(f"📊 Загружено тем из БД: {len(self.all_tags)}")
        self.tags_tab.set_session(self.session)
        self.tags_tab.load_data(self.all_tags)

        # Настраиваем фильтры
        self.employees_tab.load_filter_data(self.all_departments, self.all_divisions)

    def on_division_deleted(self, item_type: str, division_id: int):
        """Обработка удаления подразделения"""
        if item_type == "division":
            from services.employee_service import EmployeeService
            employee_service = EmployeeService(self.employees_db_session)

            if employee_service.delete_division(division_id):
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
        tab_names = ["Сотрудники", "Отделы", "Подразделения", "Колонки", "Темы"]
        if index < len(tab_names):
            print(f"Переключено на вкладку: {tab_names[index]}")