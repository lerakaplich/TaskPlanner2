# windows/settings/settings_page.py

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QMessageBox, QTabWidget
from PyQt6.QtCore import pyqtSignal
import os

from services.employee_service.employee_service import EmployeeService
from windows.settings.columns.columns_tab import ColumnsTab
from windows.settings.tags.tags_tab import TagsTab
from windows.settings.employees.employees_tab import EmployeesTab
from windows.settings.departments.departments_tab import DepartmentsTab
from windows.settings.divisions.divisions_tab import DivisionsTab
from database import get_employees_session


class SettingsPage(QWidget):
    """Страница настроек - ТОЛЬКО UI логика"""

    item_added = pyqtSignal(str, dict)
    item_edited = pyqtSignal(str, dict)
    item_deleted = pyqtSignal(str, int)

    def __init__(self, parent=None, session=None):
        super().__init__(parent)

        self.employees_db_session = get_employees_session()
        self.session = session
        self.employee_service = None

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

    def setup_tabs(self):
        """Создание и настройка всех вкладок"""
        self.tags_tab = TagsTab()
        self.employees_tab = EmployeesTab()
        self.departments_tab = DepartmentsTab()
        self.divisions_tab = DivisionsTab()
        self.columns_tab = ColumnsTab()

        # Создаём сервис
        if self.employees_db_session:
            self.employee_service = EmployeeService(self.employees_db_session)

            # Передаём сервис во вкладки
            self.employees_tab.set_employee_service(self.employee_service)
            self.departments_tab.set_employee_service(self.employee_service)
            self.divisions_tab.set_employee_service(self.employee_service)

            # Передаём сессии для других вкладок
            self.columns_tab.set_session(self.session)
            self.tags_tab.set_session(self.session)

        # Подключаем сигналы
        self.tags_tab.item_deleted.connect(self.on_item_deleted)
        self.employees_tab.item_deleted.connect(self.on_item_deleted)
        self.departments_tab.item_deleted.connect(self.on_item_deleted)
        self.divisions_tab.item_deleted.connect(self.on_item_deleted)
        self.columns_tab.item_deleted.connect(self.on_item_deleted)

        # Подключаем сигналы добавления/обновления
        self.employees_tab.employee_added.connect(lambda data: self.item_added.emit("employee", data))
        self.employees_tab.employee_updated.connect(lambda data: self.item_edited.emit("employee", data))

        # Добавляем вкладки
        if hasattr(self, 'tabWidget') and isinstance(self.tabWidget, QTabWidget):
            self.tabWidget.clear()
            self.tabWidget.addTab(self.employees_tab, "Сотрудники")
            self.tabWidget.addTab(self.departments_tab, "Отделы")
            self.tabWidget.addTab(self.divisions_tab, "Подразделения")
            self.tabWidget.addTab(self.columns_tab, "Колонки")
            self.tabWidget.addTab(self.tags_tab, "Темы")

        # Подключаем смену вкладки
        if hasattr(self, 'tabWidget'):
            self.tabWidget.currentChanged.connect(self.on_tab_changed)

    def on_item_deleted(self, item_type: str, item_id: int):
        """Обработчик удаления - пробрасывает сигнал"""
        self.item_deleted.emit(item_type, item_id)

    def on_tab_changed(self, index: int):
        """Срабатывает при смене вкладки"""
        tab_names = ["Сотрудники", "Отделы", "Подразделения", "Колонки", "Темы"]
        if index < len(tab_names):
            print(f"Переключено на вкладку: {tab_names[index]}")