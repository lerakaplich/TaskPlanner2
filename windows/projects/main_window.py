import os
import sys

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QSizePolicy, QSpacerItem, QWidget, QDialog
from PyQt6.QtWidgets import QMessageBox

from database import get_tasks_session
from services.analytics_service import AnalyticsService
from services.archive_service import ArchiveService
from services.chat_service import ChatService
from services.overtime_service import OvertimeService
from services.projects_service import ProjectsService
from windows.analytics.analytics_page import AnalyticsPage
from windows.archive.archive_page import ArchivePage
from windows.chat.chat_page import ChatPage
from windows.gantt.gantt_chart import GanttChartWidget
from windows.my_tasks.my_tasks_page import MyTasksPage
from windows.other_tasks.others_tasks_page import OthersTasksPage
from windows.overtime.overtime_page import OvertimePage
from windows.profile.profile_page import ProfilePage
from windows.projects.project_card import ProjectCard
from windows.projects.project_edit_dialog import ProjectEditDialog
from windows.settings.settings_page import SettingsPage


class MainWindow(QMainWindow):

    def __init__(self, session, user_id, socket_client=None):
        super().__init__()
        self.current_user_id = user_id
        self.socket_client = socket_client
        self.current_user = self.get_user_by_id(session, user_id)
        self.session = session
        self.current_search_query = ""
        self.current_status_filter = "Все"
        self.current_owner_filter = False
        self.current_columns = -1
        self.project_cards = []

        # 2. Инициализируем сервисы
        self.project_service = ProjectsService(session)
        self.analytics_service = AnalyticsService(session)
        self.overtime_service = OvertimeService(session)
        self.chat_service = ChatService(self.session)
        self.archive_service = ArchiveService(session)

        # Устанавливаем текущего пользователя в сервисах
        self.project_service.set_current_user_id(user_id)
        self.analytics_service.set_current_user_id(user_id)
        self.overtime_service.set_current_user_id(user_id)

        # 3. Загружаем UI
        ui_root = os.path.join(os.path.dirname(__file__), "..", "..", "ui")
        uic.loadUi(os.path.join(ui_root, "projects", "main_window.ui"), self)
        uic.loadUi(os.path.join(ui_root, "left_panel.ui"), self.leftPanel)

        # 4. Настройка навигации
        self.nav_buttons = [
            self.leftPanel.btnMain, self.leftPanel.btnMyTasks,
            self.leftPanel.btnOtherTasks, self.leftPanel.btnGantt,
            self.leftPanel.btnAnalytics, self.leftPanel.btnChat,
            self.leftPanel.btnOvertime, self.leftPanel.btnSettings
        ]
        if hasattr(self.leftPanel, 'btnArchive'):
            self.nav_buttons.append(self.leftPanel.btnArchive)

        # 5. Инициализация логики
        self.init_pages()
        self.connect_signals()
        self.setup_initial_state()
        self.update_profile_button()

        # Подключаем сигналы сокета
        self.setup_socket_handlers()

        self.showMaximized()

    # ==========================================
    # ЛЕНИВАЯ ЗАГРУЗКА СТРАНИЦ
    # ==========================================

    def init_pages(self):
        """Инициализация - создаем только страницу проектов, остальные лениво"""
        self.pages = {}  # Словарь для хранения созданных страниц

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
        self.PAGE_PROFILE = 9  # Профиль не в стеке, добавляется отдельно

        # Главная страница (список проектов) уже есть в UI
        self.contentStack.setCurrentIndex(self.PAGE_PROJECTS)

    def _get_or_create_page(self, page_name, creator_func, insert_index):
        """Универсальный метод для ленивой загрузки страниц"""
        if page_name not in self.pages:
            self.pages[page_name] = creator_func()
            # Проверяем, не вставлена ли уже страница
            existing = self.contentStack.widget(insert_index)
            if existing != self.pages[page_name]:
                self.contentStack.insertWidget(insert_index, self.pages[page_name])
        return self.pages[page_name]

    def get_my_tasks_page(self):
        """Ленивая загрузка страницы Мои задачи"""
        return self._get_or_create_page(
            'my_tasks',
            lambda: MyTasksPage(
                db_session=self.session,
                current_user={"id": self.current_user_id, "last_name": "", "first_name": ""}
            ),
            self.PAGE_MY_TASKS
        )

    def get_other_tasks_page(self):
        """Ленивая загрузка страницы Чужие задачи"""
        return self._get_or_create_page(
            'other_tasks',
            lambda: OthersTasksPage(
                parent=self,
                current_user={"id": self.current_user_id, "last_name": "", "first_name": ""},
                project_id=2
            ),
            self.PAGE_OTHER_TASKS
        )

    def get_gantt_page(self):
        """Ленивая загрузка страницы Ганта"""
        return self._get_or_create_page(
            'gantt',
            lambda: GanttChartWidget(service=self.project_service),
            self.PAGE_GANTT
        )

    def get_analytics_page(self):
        """Ленивая загрузка страницы Аналитики"""
        return self._get_or_create_page(
            'analytics',
            lambda: AnalyticsPage(session=self.session),
            self.PAGE_ANALYTICS
        )

    def get_chat_page(self):
        """Ленивая загрузка страницы Чата"""
        return self._get_or_create_page(
            'chat',
            lambda: ChatPage(
                session=self.session,
                service=self.chat_service,
                projects_service=self.project_service,
                current_user_id=self.current_user_id,
                sio=self.socket_client
            ),
            self.PAGE_CHAT
        )

    def get_overtime_page(self):
        """Ленивая загрузка страницы Переработок"""
        return self._get_or_create_page(
            'overtime',
            lambda: OvertimePage(service=self.overtime_service),
            self.PAGE_OVERTIME
        )

    def get_settings_page(self):
        """Ленивая загрузка страницы Настроек"""
        return self._get_or_create_page(
            'settings',
            lambda: SettingsPage(session=self.session),
            self.PAGE_SETTINGS
        )

    def get_archive_page(self):
        """Ленивая загрузка страницы Архива"""
        return self._get_or_create_page(
            'archive',
            lambda: ArchivePage(service=self.archive_service),
            self.PAGE_ARCHIVE
        )

    def get_profile_page(self):
        """Ленивая загрузка страницы Профиля"""
        if 'profile' not in self.pages:
            from windows.profile.profile_page import ProfilePage
            self.pages['profile'] = ProfilePage(
                employee_id=self.current_user.get('id'),
                current_user=self.current_user,
                parent=self
            )
            self.contentStack.addWidget(self.pages['profile'])
        return self.pages['profile']

    # ==========================================
    # НАВИГАЦИЯ
    # ==========================================

    def switch_page(self, page_index):
        """Переключение между страницами с ленивой загрузкой"""
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
            # Обновляем страницу архива
            if 'archive' in self.pages:
                self.pages['archive'].show_projects_list()

        self.contentStack.setCurrentIndex(page_index)

        # Обновляем состояние кнопок навигации
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == page_index)

    def show_profile(self):
        """Показать страницу профиля"""
        profile_page = self.get_profile_page()
        # Обновляем данные профиля
        profile_page.employee_id = self.current_user.get('id')
        profile_page.current_user = self.current_user
        profile_page.load_employee()
        if hasattr(profile_page, 'chart_widget'):
            profile_page.chart_widget.load_data(self.current_user.get('id'))

        self.contentStack.setCurrentWidget(profile_page)

    # ==========================================
    # ОСТАЛЬНЫЕ МЕТОДЫ
    # ==========================================

    def on_auth_success(self, data):
        """Обработчик успешной аутентификации"""
        print(f"✅ Socket auth success for user {data.get('user_id')}")
        self.socket_client.get_online_users()
        self.join_user_chat_rooms()

    def on_new_message(self, data):
        """Обработчик нового сообщения"""
        print(f"📨 New message in chat {data.get('chat_id')}")
        self.show_message_notification(data)

    def show_message_notification(self, message_data):
        """Показать уведомление о новом сообщении"""
        sender_name = message_data.get('sender_name', 'Unknown')
        content = message_data.get('content', '')[:50]
        print(f"🔔 Notification: {sender_name}: {content}")

    def on_chat_created(self, data):
        print(f"📢 New chat created: {data.get('id')}")

    def on_chat_deleted(self, data):
        print(f"🗑️ Chat deleted: {data.get('chat_id')}")

    def on_socket_connected(self):
        print("✅ Socket connected in MainWindow")
        if hasattr(self, 'current_user_id') and self.current_user_id:
            self.socket_client.authenticate(self.current_user_id)

    def on_socket_disconnected(self):
        print("⚠️ Socket disconnected in MainWindow")

    def setup_socket_handlers(self):
        if not self.socket_client:
            print("⚠️ Socket client not available")
            return
        self.socket_client.connected.connect(self.on_socket_connected)
        self.socket_client.disconnected.connect(self.on_socket_disconnected)
        self.socket_client.auth_success.connect(self.on_auth_success)
        self.socket_client.new_message.connect(self.on_new_message)
        self.socket_client.chat_created.connect(self.on_chat_created)
        self.socket_client.chat_deleted.connect(self.on_chat_deleted)
        print("✅ Socket handlers configured")

    def update_profile_button(self):
        if hasattr(self, 'btnProfile'):
            last_name = self.current_user.get('last_name', '')
            first_name = self.current_user.get('first_name', '')
            middle_name = self.current_user.get('middle_name', '')
            if last_name and first_name:
                first_initial = first_name[0] + '.' if first_name else ''
                middle_initial = middle_name[0] + '.' if middle_name else ''
                display_name = f"{last_name} {first_initial}{middle_initial}"
            else:
                display_name = f"User {self.current_user.get('id', '')}"
            self.btnProfile.setText(display_name)
            full_name = f"{last_name} {first_name} {middle_name}".strip()
            if full_name:
                self.btnProfile.setToolTip(full_name)

    def get_user_by_id(self, session, user_id):
        try:
            from models.employees import Employee, EmployeeData
            from sqlalchemy import select
            from database import get_employees_session, get_tasks_session

            # 1. Получаем сотрудника из БД employees
            emp_session = get_employees_session()
            if emp_session is None:
                print("❌ Нет подключения к БД employees")
                return {
                    'id': user_id,
                    'last_name': 'Неизвестен',
                    'first_name': '',
                    'middle_name': '',
                    'rights': 'user'
                }

            stmt = select(Employee).where(Employee.id == user_id)
            user = emp_session.scalar(stmt)

            if not user:
                emp_session.close()
                return {
                    'id': user_id,
                    'last_name': 'Неизвестен',
                    'first_name': '',
                    'middle_name': '',
                    'rights': 'user'
                }

            # 2. Получаем роль из EmployeeData (БД taskplanner)
            role = 'user'
            tasks_session = get_tasks_session()
            if tasks_session:
                try:
                    emp_data = tasks_session.query(EmployeeData).filter(
                        EmployeeData.employee_id == user_id
                    ).first()
                    if emp_data and emp_data.role:
                        role = emp_data.role.value
                    else:
                        role = 'user'
                except Exception as e:
                    print(f"⚠️ Ошибка получения роли: {e}")
                finally:
                    tasks_session.close()

            user_data = {
                'id': user.id,
                'last_name': user.last_name,
                'first_name': user.first_name,
                'middle_name': user.middle_name or '',
                'rights': role,  # ← используем роль из EmployeeData
                'position': user.position or '',
                'phone_number': user.phone_number or '',
                'email': user.email or ''
            }

            emp_session.close()
            return user_data

        except Exception as e:
            print(f"Ошибка при загрузке пользователя: {e}")
            import traceback
            traceback.print_exc()

        return {
            'id': user_id,
            'last_name': 'Неизвестен',
            'first_name': '',
            'middle_name': '',
            'rights': 'user'
        }

    def refresh_projects_view(self):
        if hasattr(self, 'project_cards') and self.project_cards:
            for card in self.project_cards:
                self.projectsGrid.removeWidget(card)
                card.deleteLater()
        self.project_cards = []
        try:
            projects_dtos = self.project_service.get_projects_for_cards(
                search_query=self.current_search_query,
                status_filter=self.current_status_filter,
                owner_filter=self.current_owner_filter
            )
        except Exception as e:
            print(f"Ошибка при загрузке проектов: {e}")
            return
        for dto in projects_dtos:
            card = ProjectCard(project_id=dto.id, project_data=dto)
            card.edit_clicked.connect(self.edit_project)
            card.open_clicked.connect(self.open_project)
            card.archive_clicked.connect(self.archive_project)
            self.project_cards.append(card)
        self.current_columns = -1
        self.adjust_card_columns()
        print(f"UI обновлен: отображено {len(self.project_cards)} проектов.")

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
            # Очищаем сессию (локально и в БД)
            from windows.login.login_window import LoginWindow
            login_window = LoginWindow()
            login_window.clear_session()

            # Закрываем главное окно
            self.close()

            # Создаем и показываем новое окно входа
            self.login_window = LoginWindow()
            self.login_window.show()

    def connect_signals(self):
        self.nav_map = {
            self.leftPanel.btnMain: self.PAGE_PROJECTS,
            self.leftPanel.btnMyTasks: self.PAGE_MY_TASKS,
            self.leftPanel.btnOtherTasks: self.PAGE_OTHER_TASKS,
            self.leftPanel.btnGantt: self.PAGE_GANTT,
            self.leftPanel.btnAnalytics: self.PAGE_ANALYTICS,
            self.leftPanel.btnChat: self.PAGE_CHAT,
            self.leftPanel.btnOvertime: self.PAGE_OVERTIME,
            self.leftPanel.btnSettings: self.PAGE_SETTINGS
        }
        if hasattr(self.leftPanel, 'btnArchive'):
            self.nav_map[self.leftPanel.btnArchive] = self.PAGE_ARCHIVE
        for btn, index in self.nav_map.items():
            btn.clicked.connect(lambda checked, i=index: self.switch_page(i))
        if hasattr(self, 'searchInput'):
            self.searchInput.textChanged.connect(self.search_projects)
        if hasattr(self, 'filterCombo'):
            self.filterCombo.currentTextChanged.connect(self.filter_projects)
        if hasattr(self, 'btnCreateProject'):
            self.btnCreateProject.clicked.connect(self.create_project)
        if hasattr(self.leftPanel, 'btnCollapse'):
            self.leftPanel.btnCollapse.clicked.connect(self.toggle_left_panel)
        if hasattr(self, 'btnNotifications'):
            self.btnNotifications.clicked.connect(self.show_notifications)
        if hasattr(self, 'btnProfile'):
            self.btnProfile.clicked.connect(self.show_profile)
        if hasattr(self.leftPanel, 'btnLogout'):
            self.leftPanel.btnLogout.clicked.connect(self.logout)
        self.contentStack.currentChanged.connect(self.on_stack_page_changed)

    def on_stack_page_changed(self, index):
        if index == self.PAGE_PROJECTS:
            self.refresh_projects_view()
        elif index == self.PAGE_CHAT and 'chat' in self.pages:
            self.pages['chat'].load_chat_list()

    def setup_initial_state(self):
        self.contentStack.setCurrentIndex(self.PAGE_PROJECTS)
        self.nav_buttons = [
            self.leftPanel.btnMain,
            self.leftPanel.btnMyTasks,
            self.leftPanel.btnOtherTasks,
            self.leftPanel.btnGantt,
            self.leftPanel.btnAnalytics,
            self.leftPanel.btnChat,
            self.leftPanel.btnOvertime,
            self.leftPanel.btnSettings,
            self.leftPanel.btnArchive
        ]
        self.button_texts = {
            self.leftPanel.btnMain: "🚚 Проекты",
            self.leftPanel.btnMyTasks: "✅ Мои задачи",
            self.leftPanel.btnOtherTasks: "👥 Чужие задачи",
            self.leftPanel.btnGantt: "📈 Диаграмма Ганта",
            self.leftPanel.btnAnalytics: "📊 Аналитика/Навыки",
            self.leftPanel.btnChat: "💬 Чат",
            self.leftPanel.btnOvertime: "♻️ Переработки",
            self.leftPanel.btnSettings: "⚙️ Настройки",
            self.leftPanel.btnArchive: "📦 Архив"
        }
        self.button_icons = {
            self.leftPanel.btnMain: "🚚",
            self.leftPanel.btnMyTasks: "✅",
            self.leftPanel.btnOtherTasks: "👥",
            self.leftPanel.btnGantt: "📈",
            self.leftPanel.btnAnalytics: "📊",
            self.leftPanel.btnChat: "💬",
            self.leftPanel.btnOvertime: "♻️",
            self.leftPanel.btnSettings: "⚙️",
            self.leftPanel.btnArchive: "📦"
        }
        self.refresh_projects_view()

    def edit_project(self, project_id):
        project_dto = self.project_service.get_project_for_edit(project_id)
        if not project_dto:
            QMessageBox.warning(self, "Ошибка", "Проект не найден")
            return
        from database import get_employees_session  # ← ДОБАВИТЬ
        from models.employees import Employee
        from sqlalchemy import select

        emp_session = get_employees_session()  # ← ИСПРАВЛЕНО
        if emp_session is None:
            QMessageBox.warning(self, "Ошибка", "Нет подключения к БД сотрудников")
            return

        participants_full = []
        if project_dto.member_ids:
            stmt = select(Employee).where(Employee.id.in_(project_dto.member_ids))
            employees = emp_session.scalars(stmt).all()
            for emp in employees:
                participants_full.append({
                    'id': emp.id,
                    'last_name': emp.last_name,
                    'first_name': emp.first_name,
                    'middle_name': emp.middle_name or '',
                    'position': emp.position or 'Сотрудник'
                })
        admins_full = []
        if project_dto.admin_ids:
            stmt = select(Employee).where(Employee.id.in_(project_dto.admin_ids))
            employees = emp_session.scalars(stmt).all()
            for emp in employees:
                admins_full.append({
                    'id': emp.id,
                    'last_name': emp.last_name,
                    'first_name': emp.first_name,
                    'middle_name': emp.middle_name or '',
                    'position': emp.position or 'Сотрудник'
                })
        emp_session.close()  # ← ЗАКРЫВАЕМ СЕССИЮ

        dialog_data = {
            'id': project_dto.id,
            'name': project_dto.name,
            'description': project_dto.description,
            'is_active': not project_dto.is_archived,
            'created_date': project_dto.created_at.strftime('%d.%m.%Y') if project_dto.created_at else '',
            'participants': participants_full,
            'admins': admins_full,
            'participants_ids': project_dto.member_ids,
            'admins_ids': project_dto.admin_ids,
            'selected_columns_data': project_dto.selected_columns_data
        }
        dialog = ProjectEditDialog(dialog_data, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            raw_results = dialog.get_project_data()
            project_dto.name = raw_results['name']
            project_dto.description = raw_results['description']
            project_dto.is_archived = not raw_results.get('is_active', True)
            project_dto.selected_columns_data = raw_results.get('selected_columns_data', [])

            def str_to_ids(s):
                return [int(i.strip()) for i in s.split(',') if i.strip().isdigit()]

            project_dto.member_ids = str_to_ids(raw_results['participants_ids'])
            project_dto.admin_ids = str_to_ids(raw_results['admins_ids'])
            if self.project_service.update_project(project_id, project_dto):
                self.refresh_projects_view()
                QMessageBox.information(self, "Успех", "Проект обновлен")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_card_columns()

    def adjust_card_columns(self):
        if not hasattr(self, 'project_cards') or not self.project_cards:
            return
        grid = self.projectsGrid
        width = self.scrollAreaWidgetContents.width() if self.scrollAreaWidgetContents else 0
        if width > 1200:
            columns = 4
        elif width > 900:
            columns = 3
        elif width > 600:
            columns = 2
        else:
            columns = 1
        if columns != self.current_columns:
            self.current_columns = columns
            while grid.count():
                item = grid.takeAt(0)
                if isinstance(item, QSpacerItem):
                    del item
            for i, card in enumerate(self.project_cards):
                row, col = divmod(i, columns)
                grid.addWidget(card, row, col)
            last_row = (len(self.project_cards) + columns - 1) // columns
            grid.addItem(
                QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding),
                last_row, 0, 1, columns
            )

    def create_project(self):
        from windows.projects.project_creation_dialog import ProjectCreationDialog
        dialog = ProjectCreationDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            raw_data = dialog.get_project_data()
            new_project_dto = self.project_service.create_new_project(raw_data, creator_id=self.current_user_id)
            if new_project_dto:
                self.refresh_projects_view()
                QMessageBox.information(self, "Успех", f"Проект '{new_project_dto.name}' успешно создан!")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось создать проект в базе данных.")

    def toggle_left_panel(self):
        current_width = self.leftPanel.width()
        if current_width > 100:
            self.leftPanel.setMaximumWidth(80)
            self.leftPanel.btnCollapse.setText("▶")
            self.leftPanel.label.setText("МАЗ")
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
        else:
            self.leftPanel.setMaximumWidth(280)
            self.leftPanel.btnCollapse.setText("◀ Свернуть")
            self.leftPanel.label.setText("МАЗ Проекты")
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

    def open_project(self, project_id):
        from windows.projects.project_view_page import ProjectViewPage
        project_page = ProjectViewPage(
            session=self.session,
            project_id=project_id,
            service=self.project_service,
            parent=self
        )
        self.contentStack.addWidget(project_page)
        self.contentStack.setCurrentWidget(project_page)

    def search_projects(self, text):
        self.current_search_query = text
        self.refresh_projects_view()

    def filter_projects(self, filter_text):
        if filter_text == "Мои проекты":
            self.current_owner_filter = True
            self.current_status_filter = "Все"
        else:
            self.current_owner_filter = False
            self.current_status_filter = filter_text
        self.refresh_projects_view()

    def show_notifications(self):
        print("Показать уведомления...")

    def join_user_chat_rooms(self):
        try:
            from services.chat_service import ChatService
            from database import get_tasks_session  # ← чаты в taskplanner

            # Чаты хранятся в taskplanner, это правильно
            chat_session = get_tasks_session()
            if chat_session is None:
                print("⚠️ Нет подключения к БД чатов")
                return

            chat_service = ChatService(chat_session)
            user_chats = chat_service.get_user_chats(self.current_user_id)
            for chat in user_chats:
                self.socket_client.join_chat_room(chat.id)
            chat_session.close()
        except Exception as e:
            print(f"Error joining chat rooms: {e}")

    def archive_project(self, project_id: int) -> bool:
        try:
            project_name = ""
            for card in self.project_cards:
                if card.project_id == project_id:
                    project_name = card.projectTitle.text()
                    break
            result = self.project_service.archive_project(project_id)
            if result:
                if hasattr(self, 'filterCombo'):
                    self.filterCombo.blockSignals(True)
                    index = self.filterCombo.findText("Активные")
                    if index >= 0:
                        self.filterCombo.setCurrentIndex(index)
                        self.current_status_filter = "Активные"
                        self.current_owner_filter = False
                    self.filterCombo.blockSignals(False)
                self.refresh_projects_view()
                if 'archive' in self.pages:
                    self.pages['archive'].show_projects_list()
                QMessageBox.information(self, "Архивация", f"Проект '{project_name}' перемещён в архив.")
                return True
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось архивировать проект")
                return False
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при архивации: {str(e)}")
            return False