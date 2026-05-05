# windows/projects/main_window_handlers.py

from PyQt6.QtWidgets import QMessageBox, QDialog, QSizePolicy, QSpacerItem
from PyQt6.QtCore import QObject, pyqtSignal
from windows.projects.project_card import ProjectCard
from windows.projects.project_edit_dialog import ProjectEditDialog
from windows.projects.project_creation_dialog import ProjectCreationDialog
from windows.projects.project_view_page import ProjectViewPage


class ProjectViewHandler:
    """Обработчик операций с проектами (CRUD)"""

    def __init__(self, main_window):
        self.main = main_window

    def refresh_projects_view(self):
        """Обновление списка проектов"""
        if hasattr(self.main, 'project_cards') and self.main.project_cards:
            for card in self.main.project_cards:
                self.main.projectsGrid.removeWidget(card)
                card.deleteLater()
        self.main.project_cards = []

        try:
            projects_dtos = self.main.project_service.get_projects_for_cards(
                search_query=self.main.current_search_query,
                status_filter=self.main.current_status_filter,
                owner_filter=self.main.current_owner_filter
            )
        except Exception as e:
            print(f"Ошибка при загрузке проектов: {e}")
            return

        for dto in projects_dtos:
            card = ProjectCard(
                project_id=dto.id,
                project_data=dto,
                parent=None,
                service=self.main.project_service
            )
            card.edit_clicked.connect(self.main.edit_project)
            card.open_clicked.connect(self.main.open_project)
            card.archive_clicked.connect(self.main.archive_project)
            self.main.project_cards.append(card)

        self.main.current_columns = -1
        self._adjust_card_columns()
        print(f"UI обновлен: отображено {len(self.main.project_cards)} проектов.")

    def _adjust_card_columns(self):
        """Адаптация количества колонок под размер окна"""
        if not hasattr(self.main, 'project_cards') or not self.main.project_cards:
            return
        grid = self.main.projectsGrid
        width = self.main.scrollAreaWidgetContents.width() if self.main.scrollAreaWidgetContents else 0
        if width > 1200:
            columns = 4
        elif width > 900:
            columns = 3
        elif width > 600:
            columns = 2
        else:
            columns = 1
        if columns != self.main.current_columns:
            self.main.current_columns = columns
            while grid.count():
                item = grid.takeAt(0)
                if isinstance(item, QSpacerItem):
                    del item
            for i, card in enumerate(self.main.project_cards):
                row, col = divmod(i, columns)
                grid.addWidget(card, row, col)
            last_row = (len(self.main.project_cards) + columns - 1) // columns
            grid.addItem(
                QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding),
                last_row, 0, 1, columns
            )

    def edit_project(self, project_id):
        """Редактирование проекта"""
        project_dto = self.main.project_service.get_project_for_edit(project_id)
        if not project_dto:
            QMessageBox.warning(self.main, "Ошибка", "Проект не найден")
            return

        dialog_data = self.main.project_service.prepare_edit_dialog_data(project_dto)
        dialog = ProjectEditDialog(dialog_data, parent=self.main, service=self.main.project_service)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            raw_results = dialog.get_project_data()
            updated_dto = self.main.project_service.update_project_from_dialog(project_id, raw_results)

            if updated_dto and self.main.project_service.update_project(project_id, updated_dto):
                self.refresh_projects_view()
                QMessageBox.information(self.main, "Успех", "Проект обновлен")

    def create_project(self):
        """Создание нового проекта"""
        dialog = ProjectCreationDialog(
            parent=self.main,
            service=self.main.project_service,
            creator_id=self.main.current_user_id
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            raw_data = dialog.get_project_data()
            new_project_dto = self.main.project_service.create_new_project(raw_data,
                                                                           creator_id=self.main.current_user_id)

            if new_project_dto:
                self.refresh_projects_view()
                QMessageBox.information(self.main, "Успех", f"Проект '{new_project_dto.name}' успешно создан!")
            else:
                QMessageBox.critical(self.main, "Ошибка", "Не удалось создать проект в базе данных.")

    def archive_project(self, project_id):
        """Архивация проекта"""
        try:
            project_name = ""
            for card in self.main.project_cards:
                if card.project_id == project_id:
                    project_name = card.projectTitle.text()
                    break
            result = self.main.project_service.archive_project(project_id)
            if result:
                if hasattr(self.main, 'filterCombo'):
                    self.main.filterCombo.blockSignals(True)
                    index = self.main.filterCombo.findText("Активные")
                    if index >= 0:
                        self.main.filterCombo.setCurrentIndex(index)
                        self.main.current_status_filter = "Активные"
                        self.main.current_owner_filter = False
                    self.main.filterCombo.blockSignals(False)
                self.refresh_projects_view()
                if 'archive' in self.main.pages:
                    self.main.pages['archive'].show_projects_list()
                QMessageBox.information(self.main, "Архивация", f"Проект '{project_name}' перемещён в архив.")
                return True
            else:
                QMessageBox.warning(self.main, "Ошибка", "Не удалось архивировать проект")
                return False
        except Exception as e:
            QMessageBox.critical(self.main, "Ошибка", f"Ошибка при архивации: {str(e)}")
            return False

    def open_project(self, project_id):
        """Открытие страницы проекта"""
        project_page = ProjectViewPage(
            session=self.main.session,
            project_id=project_id,
            service=self.main.project_service,
            parent=self.main
        )
        self.main.contentStack.addWidget(project_page)
        self.main.contentStack.setCurrentWidget(project_page)

    def search_projects(self, text):
        """Поиск проектов"""
        self.main.current_search_query = text
        self.refresh_projects_view()

    def filter_projects(self, filter_text):
        """Фильтрация проектов"""
        if filter_text == "Мои проекты":
            self.main.current_owner_filter = True
            self.main.current_status_filter = "Все"
        else:
            self.main.current_owner_filter = False
            self.main.current_status_filter = filter_text
        self.refresh_projects_view()


class NavigationHandler:
    """Обработчик навигации и ленивой загрузки страниц"""

    def __init__(self, main_window):
        self.main = main_window
        self.pages = {}

        # Индексы страниц
        self.PAGE_PROJECTS = 0
        self.PAGE_MY_TASKS = 1
        self.PAGE_OTHER_TASKS = 2
        self.PAGE_GANTT = 3
        self.PAGE_ANALYTICS = 4
        self.PAGE_CHAT = 5
        self.PAGE_OVERTIME = 6
        self.PAGE_SETTINGS = 7
        self.PAGE_ARCHIVE = 8
        self.PAGE_PROFILE = 9

    def get_page_index(self):
        return {
            'projects': self.PAGE_PROJECTS,
            'my_tasks': self.PAGE_MY_TASKS,
            'other_tasks': self.PAGE_OTHER_TASKS,
            'gantt': self.PAGE_GANTT,
            'analytics': self.PAGE_ANALYTICS,
            'chat': self.PAGE_CHAT,
            'overtime': self.PAGE_OVERTIME,
            'settings': self.PAGE_SETTINGS,
            'archive': self.PAGE_ARCHIVE,
            'profile': self.PAGE_PROFILE
        }

    def _get_or_create_page(self, page_name, creator_func, insert_index):
        """Универсальный метод для ленивой загрузки страниц"""
        if page_name not in self.pages:
            self.pages[page_name] = creator_func()
            existing = self.main.contentStack.widget(insert_index)
            if existing != self.pages[page_name]:
                self.main.contentStack.insertWidget(insert_index, self.pages[page_name])
        return self.pages[page_name]

    def get_my_tasks_page(self):
        from windows.my_tasks.my_tasks_page import MyTasksPage
        return self._get_or_create_page(
            'my_tasks',
            lambda: MyTasksPage(
                db_session=self.main.session,
                current_user={"id": self.main.current_user_id, "last_name": "", "first_name": ""}
            ),
            self.PAGE_MY_TASKS
        )

    def get_other_tasks_page(self):
        from windows.other_tasks.others_tasks_page import OthersTasksPage
        return self._get_or_create_page(
            'other_tasks',
            lambda: OthersTasksPage(
                parent=self.main,
                current_user={"id": self.main.current_user_id, "last_name": "", "first_name": ""},
                project_id=2
            ),
            self.PAGE_OTHER_TASKS
        )

    def get_gantt_page(self):
        from windows.gantt.gantt_chart import GanttChartWidget
        from services.gantt_service import GanttService
        return self._get_or_create_page(
            'gantt',
            lambda: GanttChartWidget(service=GanttService(self.main.session, self.main.current_user_id)),
            self.PAGE_GANTT
        )

    def get_analytics_page(self):
        from windows.analytics.analytics_page import AnalyticsPage
        return self._get_or_create_page(
            'analytics',
            lambda: AnalyticsPage(session=self.main.session),
            self.PAGE_ANALYTICS
        )

    def get_chat_page(self):
        from windows.chat.chat_page import ChatPage
        return self._get_or_create_page(
            'chat',
            lambda: ChatPage(
                session=self.main.session,
                service=self.main.chat_service,
                projects_service=self.main.project_service,
                current_user_id=self.main.current_user_id,
                sio=self.main.socket_client
            ),
            self.PAGE_CHAT
        )

    def get_overtime_page(self):
        from windows.overtime.overtime_page import OvertimePage
        return self._get_or_create_page(
            'overtime',
            lambda: OvertimePage(service=self.main.overtime_service),
            self.PAGE_OVERTIME
        )

    def get_settings_page(self):
        from windows.settings.settings_page import SettingsPage
        return self._get_or_create_page(
            'settings',
            lambda: SettingsPage(session=self.main.session),
            self.PAGE_SETTINGS
        )

    def get_archive_page(self):
        from windows.archive.archive_page import ArchivePage
        return self._get_or_create_page(
            'archive',
            lambda: ArchivePage(service=self.main.archive_service),
            self.PAGE_ARCHIVE
        )

    def get_profile_page(self):
        if 'profile' not in self.pages:
            from windows.profile.profile_page import ProfilePage
            self.pages['profile'] = ProfilePage(
                employee_id=self.main.current_user.get('id'),
                current_user=self.main.current_user,
                parent=self.main
            )
            self.main.contentStack.addWidget(self.pages['profile'])
        return self.pages['profile']

    def switch_page(self, page_index):
        """Переключение между страницами"""
        # Создаем страницу при первом открытии
        if page_index == self.PAGE_MY_TASKS:
            self.get_my_tasks_page()
        elif page_index == self.PAGE_OTHER_TASKS:
            self.get_other_tasks_page()
        elif page_index == self.PAGE_GANTT:
            self.get_gantt_page()
        elif page_index == self.PAGE_ANALYTICS:
            self.get_analytics_page()
        elif page_index == self.PAGE_CHAT:
            self.get_chat_page()
        elif page_index == self.PAGE_OVERTIME:
            self.get_overtime_page()
        elif page_index == self.PAGE_SETTINGS:
            self.get_settings_page()
        elif page_index == self.PAGE_ARCHIVE:
            self.get_archive_page()
            if 'archive' in self.pages:
                self.pages['archive'].show_projects_list()

        self.main.contentStack.setCurrentIndex(page_index)

        # Обновляем состояние кнопок навигации
        for i, btn in enumerate(self.main.nav_buttons):
            btn.setChecked(i == page_index)

    def show_profile(self):
        """Показать страницу профиля"""
        profile_page = self.get_profile_page()
        profile_page.employee_id = self.main.current_user.get('id')
        profile_page.current_user = self.main.current_user
        profile_page.load_employee()
        if hasattr(profile_page, 'chart_widget'):
            profile_page.chart_widget.load_data(self.main.current_user.get('id'))
        self.main.contentStack.setCurrentWidget(profile_page)


class UIHandler:
    """Обработчик UI (левая панель, кнопки)"""

    def __init__(self, main_window):
        self.main = main_window
        self.nav_buttons = []
        self.button_texts = {}
        self.button_icons = {}

    def setup_initial_state(self):
        """Начальная настройка UI"""
        self.main.contentStack.setCurrentIndex(0)
        self._init_nav_buttons()
        self._init_button_texts()
        self._init_button_icons()

    def _init_nav_buttons(self):
        self.nav_buttons = [
            self.main.leftPanel.btnMain,
            self.main.leftPanel.btnMyTasks,
            self.main.leftPanel.btnOtherTasks,
            self.main.leftPanel.btnGantt,
            self.main.leftPanel.btnAnalytics,
            self.main.leftPanel.btnChat,
            self.main.leftPanel.btnOvertime,
            self.main.leftPanel.btnSettings,
            self.main.leftPanel.btnArchive
        ]
        self.main.nav_buttons = self.nav_buttons

    def _init_button_texts(self):
        self.button_texts = {
            self.main.leftPanel.btnMain: "🚚 Проекты",
            self.main.leftPanel.btnMyTasks: "✅ Мои задачи",
            self.main.leftPanel.btnOtherTasks: "👥 Чужие задачи",
            self.main.leftPanel.btnGantt: "📈 Диаграмма Ганта",
            self.main.leftPanel.btnAnalytics: "📊 Аналитика/Навыки",
            self.main.leftPanel.btnChat: "💬 Чат",
            self.main.leftPanel.btnOvertime: "♻️ Переработки",
            self.main.leftPanel.btnSettings: "⚙️ Настройки",
            self.main.leftPanel.btnArchive: "📦 Архив"
        }
        self.main.button_texts = self.button_texts

    def _init_button_icons(self):
        self.button_icons = {
            self.main.leftPanel.btnMain: "🚚",
            self.main.leftPanel.btnMyTasks: "✅",
            self.main.leftPanel.btnOtherTasks: "👥",
            self.main.leftPanel.btnGantt: "📈",
            self.main.leftPanel.btnAnalytics: "📊",
            self.main.leftPanel.btnChat: "💬",
            self.main.leftPanel.btnOvertime: "♻️",
            self.main.leftPanel.btnSettings: "⚙️",
            self.main.leftPanel.btnArchive: "📦"
        }
        self.main.button_icons = self.button_icons

    def toggle_left_panel(self):
        """Сворачивание/разворачивание левой панели"""
        current_width = self.main.leftPanel.width()
        if current_width > 100:
            self._collapse_panel()
        else:
            self._expand_panel()

    def _collapse_panel(self):
        self.main.leftPanel.setMaximumWidth(80)
        self.main.leftPanel.btnCollapse.setText("▶")
        self.main.leftPanel.label.setText("МАЗ")
        for btn in self.nav_buttons:
            btn.setText(self.button_icons[btn])
            btn.setStyleSheet("""
                QPushButton {
                    color: white;
                    font-size: 20px;
                    padding: 15px 0px;
                    text-align: center;
                    border: none;
                    background-color: transparent;
                }
                QPushButton:hover {
                    background-color: #2C3640;
                    border-left: 4px solid #D22730;
                }
                QPushButton:checked {
                    background-color: #2C3640;
                    border-left: 4px solid #ccab6e;
                }
            """)

    def _expand_panel(self):
        self.main.leftPanel.setMaximumWidth(280)
        self.main.leftPanel.btnCollapse.setText("◀ Свернуть")
        self.main.leftPanel.label.setText("МАЗ Проекты")
        for btn in self.nav_buttons:
            btn.setText(self.button_texts[btn])
            btn.setStyleSheet("""
                QPushButton {
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 15px 20px;
                    text-align: left;
                    border: none;
                    background-color: transparent;
                }
                QPushButton:hover {
                    background-color: #2C3640;
                    border-left: 4px solid #D22730;
                }
                QPushButton:checked {
                    background-color: #2C3640;
                    border-left: 4px solid #ccab6e;
                }
            """)

    def update_profile_button(self):
        """Обновление кнопки профиля"""
        if hasattr(self.main, 'btnProfile'):
            last_name = self.main.current_user.get('last_name', '')
            first_name = self.main.current_user.get('first_name', '')
            middle_name = self.main.current_user.get('middle_name', '')
            if last_name and first_name:
                first_initial = first_name[0] + '.' if first_name else ''
                middle_initial = middle_name[0] + '.' if middle_name else ''
                display_name = f"{last_name} {first_initial}{middle_initial}"
            else:
                display_name = f"User {self.main.current_user.get('id', '')}"
            self.main.btnProfile.setText(display_name)
            full_name = f"{last_name} {first_name} {middle_name}".strip()
            if full_name:
                self.main.btnProfile.setToolTip(full_name)


class SocketHandler:
    """Обработчик WebSocket соединения"""

    def __init__(self, main_window):
        self.main = main_window

    def setup_handlers(self):
        """Настройка обработчиков сокета"""
        if not self.main.socket_client:
            print("⚠️ Socket client not available")
            return
        self.main.socket_client.connected.connect(self._on_connected)
        self.main.socket_client.disconnected.connect(self._on_disconnected)
        self.main.socket_client.auth_success.connect(self._on_auth_success)
        self.main.socket_client.new_message.connect(self._on_new_message)
        self.main.socket_client.chat_created.connect(self._on_chat_created)
        self.main.socket_client.chat_deleted.connect(self._on_chat_deleted)
        print("✅ Socket handlers configured")

    def _on_connected(self):
        print("✅ Socket connected in MainWindow")
        if hasattr(self.main, 'current_user_id') and self.main.current_user_id:
            self.main.socket_client.authenticate(self.main.current_user_id)

    def _on_disconnected(self):
        print("⚠️ Socket disconnected in MainWindow")

    def _on_auth_success(self, data):
        print(f"✅ Socket auth success for user {data.get('user_id')}")
        self.main.socket_client.get_online_users()
        self._join_user_chat_rooms()

    def _on_new_message(self, data):
        print(f"📨 New message in chat {data.get('chat_id')}")
        self._show_message_notification(data)

    def _on_chat_created(self, data):
        print(f"📢 New chat created: {data.get('id')}")

    def _on_chat_deleted(self, data):
        print(f"🗑️ Chat deleted: {data.get('chat_id')}")

    def _show_message_notification(self, message_data):
        sender_name = message_data.get('sender_name', 'Unknown')
        content = message_data.get('content', '')[:50]
        print(f"🔔 Notification: {sender_name}: {content}")

    def _join_user_chat_rooms(self):
        try:
            from services.chat_service import ChatService
            from database import get_tasks_session

            chat_session = get_tasks_session()
            if chat_session is None:
                print("⚠️ Нет подключения к БД чатов")
                return

            chat_service = ChatService(chat_session)
            user_chats = self.main.project_service.get_user_chats(self.main.current_user_id)
            for chat in user_chats:
                self.main.socket_client.join_chat_room(chat.id)
            chat_session.close()
        except Exception as e:
            print(f"Error joining chat rooms: {e}")