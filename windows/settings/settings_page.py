# windows/settings/settings_page.py

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QMessageBox, QTabWidget
from PyQt6.QtCore import pyqtSignal, QTimer
import os

from services.employee_service.employee_service import EmployeeService
from windows.settings.columns.columns_tab import ColumnsTab
from windows.settings.tags.tags_tab import TagsTab
from windows.settings.employees.employees_tab import EmployeesTab
from windows.settings.departments.departments_tab import DepartmentsTab
from windows.settings.divisions.divisions_tab import DivisionsTab
from windows.permissions.ui_permission_mixin import UIPermissionMixin
from database import get_employees_session


class SettingsPage(QWidget, UIPermissionMixin):
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
        # НЕ вызываем setup_permission_ui здесь,
        # так как сервис прав ещё не установлен

    def set_permission_service(self, permission_service):
        """Устанавливает сервис прав и передаёт его во все вкладки"""
        self._permission_service = permission_service

        # Передаём сервис прав во все вкладки
        tabs = [
            getattr(self, 'employees_tab', None),
            getattr(self, 'departments_tab', None),
            getattr(self, 'divisions_tab', None),
            getattr(self, 'columns_tab', None),
            getattr(self, 'tags_tab', None),
        ]

        for tab in tabs:
            if tab and hasattr(tab, 'set_permission_service'):
                tab.set_permission_service(permission_service)

        # Настраиваем UI
        self.setup_permission_ui()

    def setup_permission_ui(self):
        """Настройка UI в зависимости от прав"""
        # Проверяем, может ли пользователь видеть настройки
        if self._permission_service and not self._permission_service.can_view_settings():
            # Если не может видеть настройки - скрываем страницу
            self.setVisible(False)
            return

        # Если включен read-only режим, применяем его ко всем вкладкам
        if self._read_only_mode:
            self._apply_read_only_to_all_tabs()

    def _apply_read_only_to_all_tabs(self):
        """Применяет read-only режим ко всем вкладкам"""
        tabs = [
            getattr(self, 'employees_tab', None),
            getattr(self, 'departments_tab', None),
            getattr(self, 'divisions_tab', None),
            getattr(self, 'columns_tab', None),
            getattr(self, 'tags_tab', None),
        ]

        for tab in tabs:
            if tab and hasattr(tab, 'set_read_only_mode'):
                tab.set_read_only_mode(True)
            elif tab and hasattr(tab, '_read_only_mode'):
                tab._read_only_mode = True
                if hasattr(tab, 'setup_permission_ui'):
                    tab.setup_permission_ui()

        # Переименовываем кнопки во всех вкладках
        self._rename_all_edit_buttons()

    def _rename_all_edit_buttons(self):
        """Переименовывает все кнопки редактирования на 'Подробнее'"""
        tabs = [
            getattr(self, 'employees_tab', None),
            getattr(self, 'departments_tab', None),
            getattr(self, 'divisions_tab', None),
            getattr(self, 'columns_tab', None),
            getattr(self, 'tags_tab', None),
        ]

        for tab in tabs:
            if tab and hasattr(tab, '_rename_edit_buttons'):
                tab._rename_edit_buttons()

    def showEvent(self, event):
        """Срабатывает при каждом показе страницы"""
        super().showEvent(event)
        QTimer.singleShot(100, self._refresh_all_tabs)

    def _refresh_all_tabs(self):
        """Обновляет все вкладки настроек"""
        if hasattr(self, 'employees_tab') and hasattr(self.employees_tab, 'load_employees'):
            self.employees_tab.load_employees()
        if hasattr(self, 'departments_tab') and hasattr(self.departments_tab, 'load_departments'):
            self.departments_tab.load_departments()
        if hasattr(self, 'divisions_tab') and hasattr(self.divisions_tab, 'load_divisions'):
            self.divisions_tab.load_divisions()
        if hasattr(self, 'columns_tab') and hasattr(self.columns_tab, 'load_columns'):
            self.columns_tab.load_columns()
        if hasattr(self, 'tags_tab') and hasattr(self.tags_tab, 'load_tags'):
            self.tags_tab.load_tags()

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