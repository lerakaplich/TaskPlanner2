# windows/projects/main_window.py

import os
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QMessageBox

from services.analytics_service.analytics_service import AnalyticsService
from services.archive_service import ArchiveService
from services.chat_service import ChatService
from services.employee_service.column_service import ColumnService
from services.overtime_service.overtime_service import OvertimeService
from services.projects_service.projects_service import ProjectsService
from services.permissions.permission_service import PermissionService

from windows.projects.main_window_handlers import (
    ProjectViewHandler, NavigationHandler, UIHandler, SocketHandler
)


class MainWindow(QMainWindow):
    """Главное окно приложения - с поддержкой прав доступа"""

    def __init__(self, session, user_id, socket_client=None):
        super().__init__()

        # Базовые данные
        self.session = session
        self.current_user_id = user_id
        self.socket_client = socket_client
        self.current_user = None

        # Состояние фильтров
        self.current_search_query = ""
        self.current_status_filter = "Все"
        self.current_owner_filter = False
        self.current_columns = -1
        self.project_cards = []
        self.pages = {}

        self.column_service = ColumnService()

        # Инициализация
        self._init_services()
        self._load_current_user()

        # Инициализация сервиса прав (после загрузки пользователя)
        self._init_permission_service()

        self._setup_ui()
        self._init_handlers()
        self._setup_navigation()
        self._setup_socket()
        self._setup_column_service()

        # Настройка UI в зависимости от прав
        self._setup_permission_ui()

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

    # windows/projects/main_window.py

    def _init_permission_service(self):
        """Инициализация сервиса прав доступа"""
        try:
            self.permission_service = PermissionService(
                user_id=self.current_user_id,
                app_service=self.project_service,
                project_service=self.project_service,
                employee_service=None,
                session=self.session
            )
            print(f"🔐 Сервис прав инициализирован для пользователя {self.current_user_id}")
            print(f"   Роль в приложении: {self.permission_service.app_manager.role.value}")
        except Exception as e:
            print(f"⚠️ Ошибка инициализации сервиса прав: {e}")
            # Создаём минимальный сервис прав
            from services.permissions.app_permissions import AppPermissionManager, AppRole
            self.permission_service = PermissionService(
                user_id=self.current_user_id,
                app_service=self.project_service,
                project_service=self.project_service,
                employee_service=None,
                session=self.session
            )

    def _load_current_user(self):
        """Загрузка текущего пользователя через сервис"""
        self.current_user = self.project_service.get_user_by_id(self.current_user_id)
        print(f"🔍 Загружен пользователь: {self.current_user}")

        if self.current_user:
            if 'last_name' not in self.current_user:
                self.current_user['last_name'] = ''
            if 'first_name' not in self.current_user:
                self.current_user['first_name'] = ''
            if 'middle_name' not in self.current_user:
                self.current_user['middle_name'] = ''

    # windows/projects/main_window.py

    def _setup_permission_ui(self):
        """Настраивает UI в зависимости от прав пользователя"""
        if not self.permission_service:
            return

        # 1. Кнопка создания проекта
        if hasattr(self, 'btnCreateProject'):
            can_create = self.permission_service.can_show_create_project_button()
            self.btnCreateProject.setVisible(can_create)
            print(f"   btnCreateProject visible: {can_create}")

        # 2. Настройка видимости вкладок в левой панели
        visible_tabs = self.permission_service.app_manager.get_visible_tabs()
        print(f"   📋 visible_tabs: {visible_tabs}")

        tab_buttons = {
            'projects': None,
            'my_tasks': None,
            'other_tasks': None,
            'gantt': None,
            'analytics': None,
            'chat': None,
            'overtime': None,  # ← УБЕДИТЬСЯ, ЧТО ЕСТЬ
            'settings': None,
            'archive': None
        }

        # Получаем кнопки из левой панели
        if hasattr(self.leftPanel, 'btnMain'):
            tab_buttons['projects'] = self.leftPanel.btnMain
        if hasattr(self.leftPanel, 'btnMyTasks'):
            tab_buttons['my_tasks'] = self.leftPanel.btnMyTasks
        if hasattr(self.leftPanel, 'btnOtherTasks'):
            tab_buttons['other_tasks'] = self.leftPanel.btnOtherTasks
        if hasattr(self.leftPanel, 'btnGantt'):
            tab_buttons['gantt'] = self.leftPanel.btnGantt
        if hasattr(self.leftPanel, 'btnAnalytics'):
            tab_buttons['analytics'] = self.leftPanel.btnAnalytics
        if hasattr(self.leftPanel, 'btnChat'):
            tab_buttons['chat'] = self.leftPanel.btnChat
        if hasattr(self.leftPanel, 'btnOvertime'):  # ← УБЕДИТЬСЯ, ЧТО ЕСТЬ
            tab_buttons['overtime'] = self.leftPanel.btnOvertime
        if hasattr(self.leftPanel, 'btnSettings'):
            tab_buttons['settings'] = self.leftPanel.btnSettings
        if hasattr(self.leftPanel, 'btnArchive'):
            tab_buttons['archive'] = self.leftPanel.btnArchive

        # Применяем видимость
        for tab_name, button in tab_buttons.items():
            if button:
                is_visible = tab_name in visible_tabs
                button.setVisible(is_visible)
                print(f"   {tab_name}: visible={is_visible}")

    def _on_columns_updated(self):
        """Обработчик обновления колонок"""
        print("📢 Получен сигнал обновления колонок")

        if hasattr(self, 'navigation') and 'my_tasks' in self.navigation.pages:
            print("   - Прямое обновление страницы Мои задачи")
            my_tasks = self.navigation.pages['my_tasks']
            if hasattr(my_tasks.service.crud, '_column_cache'):
                my_tasks.service.crud._column_cache = None
            my_tasks.refresh_columns()

        if hasattr(self, 'navigation') and 'other_tasks' in self.navigation.pages:
            print("   - Обновляем страницу Чужие задачи")
            self.navigation.pages['other_tasks'].refresh_columns()

        if hasattr(self, 'navigation'):
            self.navigation.refresh_task_pages_columns()

    def _setup_column_service(self):
        """Настройка сервиса колонок и подключение сигналов"""
        self.column_service = ColumnService()
        self.column_service.columns_updated.connect(self._on_columns_updated)
        self.column_service.columns_updated.connect(self._force_refresh_task_pages)

    def _force_refresh_task_pages(self):
        """Принудительное обновление страниц задач"""
        print("📢 Принудительное обновление страниц задач")
        if hasattr(self, 'navigation'):
            if 'my_tasks' in self.navigation.pages:
                self.navigation.pages['my_tasks'].refresh_columns()
            if 'other_tasks' in self.navigation.pages:
                self.navigation.pages['other_tasks'].refresh_columns()

    def get_my_tasks_page_with_signals(self):
        """Создает страницу моих задач с подключенными сигналами"""
        from windows.my_tasks.my_tasks_page import MyTasksPage

        page = MyTasksPage(
            db_session=self.session,
            current_user={"id": self.current_user_id, "last_name": "", "first_name": ""},
            column_service=self.column_service
        )
        page.open_project_requested.connect(self.navigation.open_project_by_id)
        return page

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

        self.page_indices = self.navigation.get_page_index()

    def _setup_navigation(self):
        """Настройка навигации"""
        self.nav_map = {
            self.leftPanel.btnMain: self.navigation.PAGE_PROJECTS,
            self.leftPanel.btnMyTasks: self.navigation.PAGE_MY_TASKS,
            self.leftPanel.btnOtherTasks: self.navigation.PAGE_OTHER_TASKS,
            self.leftPanel.btnGantt: self.navigation.PAGE_GANTT,
            self.leftPanel.btnAnalytics: self.navigation.PAGE_ANALYTICS,
            self.leftPanel.btnChat: self.navigation.PAGE_CHAT,
            self.leftPanel.btnOvertime: self.navigation.PAGE_OVERTIME,  # <-- ДОБАВИТЬ ЭТУ СТРОКУ
            self.leftPanel.btnSettings: self.navigation.PAGE_SETTINGS
        }
        if hasattr(self.leftPanel, 'btnArchive'):
            self.nav_map[self.leftPanel.btnArchive] = self.navigation.PAGE_ARCHIVE

        for btn, index in self.nav_map.items():
            btn.clicked.connect(lambda checked, i=index: self.navigation.switch_page(i))

        # ... остальной код

        if hasattr(self, 'btnCreateProject'):
            self.btnCreateProject.clicked.connect(self.project_handler.create_project)
        if hasattr(self, 'btnProfile'):
            self.btnProfile.clicked.connect(self.navigation.show_profile)
        if hasattr(self.leftPanel, 'btnCollapse'):
            self.leftPanel.btnCollapse.clicked.connect(self.ui_handler.toggle_left_panel)
        if hasattr(self, 'searchInput'):
            self.searchInput.textChanged.connect(self.project_handler.search_projects)
        if hasattr(self, 'filterCombo'):
            self.filterCombo.currentTextChanged.connect(self.project_handler.filter_projects)
        if hasattr(self, 'btnNotifications'):
            self.btnNotifications.clicked.connect(self._show_notifications)

        self.contentStack.currentChanged.connect(self._on_stack_page_changed)

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

    def view_project(self, project_id):
        """Просмотр проекта (без права редактирования)"""
        self.project_handler.view_project(project_id)

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

            auth_service = AuthService()
            user_id = self.current_user.get('id') if self.current_user else None
            auth_service.clear_session(user_id)
            auth_service.clear_current_user()

            self.close()

            from windows.login.login_window import LoginWindow
            self.login_window = LoginWindow()
            self.login_window.show()