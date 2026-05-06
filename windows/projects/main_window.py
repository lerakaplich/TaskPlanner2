# windows/projects/main_window.py

import os
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QMessageBox

from services.analytics_service import AnalyticsService
from services.archive_service import ArchiveService
from services.chat_service import ChatService
from services.overtime_service import OvertimeService
from services.projects_service.projects_service import ProjectsService

from windows.projects.main_window_handlers import (
    ProjectViewHandler, NavigationHandler, UIHandler, SocketHandler
)


class MainWindow(QMainWindow):
    """Главное окно приложения - только инициализация и координация"""

    def __init__(self, session, user_id, socket_client=None):
        super().__init__()

        # Базовые данные
        self.session = session
        self.current_user_id = user_id
        self.socket_client = socket_client
        self.current_user = None  # будет загружен через сервис

        # Состояние фильтров
        self.current_search_query = ""
        self.current_status_filter = "Все"
        self.current_owner_filter = False
        self.current_columns = -1
        self.project_cards = []
        self.pages = {}

        # Инициализация
        self._init_services()
        self._load_current_user()
        self._setup_ui()
        self._init_handlers()
        self._setup_navigation()
        self._setup_socket()

        self.showMaximized()

    def _init_services(self):
        """Инициализация сервисов"""
        self.project_service = ProjectsService(self.session)
        self.analytics_service = AnalyticsService(self.session)
        self.overtime_service = OvertimeService(self.session)
        self.chat_service = ChatService(self.session)
        self.archive_service = ArchiveService(self.session)

        # Устанавливаем текущего пользователя
        self.project_service.set_current_user_id(self.current_user_id)
        self.analytics_service.set_current_user_id(self.current_user_id)
        self.overtime_service.set_current_user_id(self.current_user_id)

    def _load_current_user(self):
        """Загрузка текущего пользователя через сервис"""
        self.current_user = self.project_service.get_user_by_id(self.current_user_id)

    def _setup_ui(self):
        """Загрузка UI файлов"""
        ui_root = os.path.join(os.path.dirname(__file__), "..", "..", "ui")
        uic.loadUi(os.path.join(ui_root, "projects", "main_window.ui"), self)
        uic.loadUi(os.path.join(ui_root, "left_panel.ui"), self.leftPanel)

    def _init_handlers(self):
        """Инициализация обработчиков"""
        self.project_handler = ProjectViewHandler(self)
        self.navigation = NavigationHandler(self)
        self.ui_handler = UIHandler(self)
        self.socket_handler = SocketHandler(self)

        # Сохраняем индексы страниц для доступа из других обработчиков
        self.page_indices = self.navigation.get_page_index()

    def _setup_navigation(self):
        """Настройка навигации"""
        # Подключаем кнопки навигации
        self.nav_map = {
            self.leftPanel.btnMain: self.navigation.PAGE_PROJECTS,
            self.leftPanel.btnMyTasks: self.navigation.PAGE_MY_TASKS,
            self.leftPanel.btnOtherTasks: self.navigation.PAGE_OTHER_TASKS,
            self.leftPanel.btnGantt: self.navigation.PAGE_GANTT,
            self.leftPanel.btnAnalytics: self.navigation.PAGE_ANALYTICS,
            self.leftPanel.btnChat: self.navigation.PAGE_CHAT,
            self.leftPanel.btnOvertime: self.navigation.PAGE_OVERTIME,
            self.leftPanel.btnSettings: self.navigation.PAGE_SETTINGS
        }
        if hasattr(self.leftPanel, 'btnArchive'):
            self.nav_map[self.leftPanel.btnArchive] = self.navigation.PAGE_ARCHIVE

        # Подключаем сигналы
        for btn, index in self.nav_map.items():
            btn.clicked.connect(lambda checked, i=index: self.navigation.switch_page(i))

        if hasattr(self, 'btnCreateProject'):
            self.btnCreateProject.clicked.connect(self.project_handler.create_project)
        if hasattr(self, 'btnProfile'):
            self.btnProfile.clicked.connect(self.navigation.show_profile)
        if hasattr(self.leftPanel, 'btnCollapse'):
            self.leftPanel.btnCollapse.clicked.connect(self.ui_handler.toggle_left_panel)
        if hasattr(self.leftPanel, 'btnLogout'):
            self.leftPanel.btnLogout.clicked.connect(self.logout)
        if hasattr(self, 'searchInput'):
            self.searchInput.textChanged.connect(self.project_handler.search_projects)
        if hasattr(self, 'filterCombo'):
            self.filterCombo.currentTextChanged.connect(self.project_handler.filter_projects)
        if hasattr(self, 'btnNotifications'):
            self.btnNotifications.clicked.connect(self._show_notifications)

        self.contentStack.currentChanged.connect(self._on_stack_page_changed)

        # Начальное состояние
        self.ui_handler.setup_initial_state()
        self.ui_handler.update_profile_button()
        self.project_handler.refresh_projects_view()

    def _setup_socket(self):
        """Настройка WebSocket"""
        self.socket_handler.setup_handlers()

    def _on_stack_page_changed(self, index):
        """Обработчик смены страницы"""
        if index == self.navigation.PAGE_PROJECTS:
            self.project_handler.refresh_projects_view()
        elif index == self.navigation.PAGE_CHAT and 'chat' in self.pages:
            self.pages['chat'].load_chat_list()

    def _show_notifications(self):
        print("Показать уведомления...")

    # Прокси-методы для доступа из обработчиков
    def refresh_projects_view(self):
        self.project_handler.refresh_projects_view()

    def edit_project(self, project_id):
        self.project_handler.edit_project(project_id)

    def create_project(self):
        self.project_handler.create_project()

    def archive_project(self, project_id):
        self.project_handler.archive_project(project_id)

    def open_project(self, project_id):
        self.project_handler.open_project(project_id)

    def search_projects(self, text):
        self.project_handler.search_projects(text)

    def filter_projects(self, filter_text):
        self.project_handler.filter_projects(filter_text)

    def toggle_left_panel(self):
        self.ui_handler.toggle_left_panel()

    def show_profile(self):
        self.navigation.show_profile()

    def switch_page(self, index):
        self.navigation.switch_page(index)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.project_handler._adjust_card_columns()

    def logout(self):
        """Выход из системы"""
        reply = QMessageBox.question(
            self,
            "Выход",
            "Вы уверены, что хотите выйти из системы?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            from services.auth_service import AuthService

            # Очищаем сессию через AuthService
            auth_service = AuthService()
            user_id = self.current_user.get('id') if self.current_user else None
            auth_service.clear_session(user_id)
            auth_service.clear_current_user()

            # Закрываем текущее окно
            self.close()

            # Создаем и показываем окно входа
            from windows.login.login_window import LoginWindow
            self.login_window = LoginWindow()
            self.login_window.show()

            # Важно: сохраняем ссылку на окно, чтобы оно не было удалено сборщиком мусора
            # и показываем его после закрытия главного окна
            if hasattr(self, 'parent()'):
                # Если есть родительское окно, показываем относительно него
                pass