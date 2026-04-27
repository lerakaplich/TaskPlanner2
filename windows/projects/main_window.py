import os
import sys

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QSizePolicy, QSpacerItem, QWidget, QDialog
from PyQt6.QtWidgets import QMessageBox

from database import get_tasks_session
from services.analytics_service import AnalyticsService
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

    def __init__(self, session, user_id, socket_client=None):  # Добавлен socket_client с значением по умолчанию
        super().__init__()
        self.current_user_id = user_id
        self.socket_client = socket_client  # Сохраняем socket_client
        # 👇 ДОБАВЛЯЕМ СЛОВАРЬ current_user
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
        self.update_profile_button()  # 👈 ДОБАВЛЯЕМ ОБНОВЛЕНИЕ КНОПКИ

        # 👇 ДОБАВЛЯЕМ: Подключаем сигналы сокета
        self.setup_socket_handlers()

        self.showMaximized()

    def on_auth_success(self, data):
        """Обработчик успешной аутентификации"""
        print(f"✅ Socket auth success for user {data.get('user_id')}")
        # При успешной аутентификации можно запросить список онлайн пользователей
        self.socket_client.get_online_users()

        # Присоединяемся к комнатам чатов пользователя
        self.join_user_chat_rooms()

    def on_new_message(self, data):
        """Обработчик нового сообщения"""
        print(f"📨 New message in chat {data.get('chat_id')}")
        # Здесь можно показать уведомление о новом сообщении
        # если текущая страница не является чатом с этим ID
        self.show_message_notification(data)

    def show_message_notification(self, message_data):
        """Показать уведомление о новом сообщении"""
        # Здесь можно реализовать показ всплывающего уведомления
        # Например, через QSystemTrayIcon или кастомный виджет
        sender_name = message_data.get('sender_name', 'Unknown')
        chat_id = message_data.get('chat_id')
        content = message_data.get('content', '')[:50]

        print(f"🔔 Notification: {sender_name}: {content}")
        # TODO: Добавить визуальное уведомление

    def on_chat_created(self, data):
        """Обработчик создания нового чата"""
        print(f"📢 New chat created: {data.get('id')}")
        # Обновляем список чатов, если страница чата открыта

    def on_chat_deleted(self, data):
        """Обработчик удаления чата"""
        print(f"🗑️ Chat deleted: {data.get('chat_id')}")
        # Обновляем список чатов, если страница чата открыта

    def on_socket_connected(self):
        """Обработчик подключения к серверу"""
        print("✅ Socket connected in MainWindow")
        # Если пользователь уже авторизован, отправляем повторную аутентификацию
        if hasattr(self, 'current_user_id') and self.current_user_id:
            self.socket_client.authenticate(self.current_user_id)

    def on_socket_disconnected(self):
        """Обработчик отключения от сервера"""
        print("⚠️ Socket disconnected in MainWindow")
        # Можно показать уведомление пользователю

    def setup_socket_handlers(self):
        """Настройка обработчиков сокет-событий"""
        if not self.socket_client:
            print("⚠️ Socket client not available")
            return

        # Подключаем сигналы сокета к соответствующим методам
        self.socket_client.connected.connect(self.on_socket_connected)
        self.socket_client.disconnected.connect(self.on_socket_disconnected)
        self.socket_client.auth_success.connect(self.on_auth_success)
        self.socket_client.new_message.connect(self.on_new_message)
        self.socket_client.chat_created.connect(self.on_chat_created)
        self.socket_client.chat_deleted.connect(self.on_chat_deleted)

        print("✅ Socket handlers configured")

    def update_profile_button(self):
        """Обновляет текст на кнопке профиля с Фамилией И.О."""
        if hasattr(self, 'btnProfile'):
            last_name = self.current_user.get('last_name', '')
            first_name = self.current_user.get('first_name', '')
            middle_name = self.current_user.get('middle_name', '')

            # Формируем Фамилию и инициалы
            if last_name and first_name:
                # Берем первую букву имени и отчества
                first_initial = first_name[0] + '.' if first_name else ''
                middle_initial = middle_name[0] + '.' if middle_name else ''

                # Формат: "Фамилия И.О."
                display_name = f"{last_name} {first_initial}{middle_initial}"
            else:
                # Если данных нет, используем логин или ID
                display_name = f"User {self.current_user.get('id', '')}"

            self.btnProfile.setText(display_name)

            # Добавляем тултип с полным именем
            full_name = f"{last_name} {first_name} {middle_name}".strip()
            if full_name:
                self.btnProfile.setToolTip(full_name)

    def get_user_by_id(self, session, user_id):
        """Получает данные пользователя по ID из БД"""
        try:
            from models.employees import ExternalEmployee
            from sqlalchemy import select

            stmt = select(ExternalEmployee).where(ExternalEmployee.id == user_id)
            user = session.scalar(stmt)

            if user:
                return {
                    'id': user.id,
                    'last_name': user.last_name,
                    'first_name': user.first_name,
                    'middle_name': user.middle_name,
                    'rights': user.rights,
                    'position': user.position,
                    'phone_number': user.phone_number,
                    'email': user.email
                }
        except Exception as e:
            print(f"❌ Ошибка при загрузке пользователя: {e}")

        # Возвращаем заглушку если не найден
        return {
            'id': user_id,
            'last_name': 'Неизвестен',
            'first_name': '',
            'middle_name': '',
            'rights': 'user'
        }

    def init_archive_page(self):
        """Инициализация страницы архива"""
        self.archive_page_instance = ArchivePage()

        # Ищем существующую страницу архива в contentStack
        archive_old = self.findChild(QWidget, "archivePage")
        if archive_old:
            index = self.contentStack.indexOf(archive_old)
            archive_old.deleteLater()
            self.contentStack.insertWidget(index, self.archive_page_instance)
        else:
            # Если страницы нет, добавляем в конец
            self.contentStack.addWidget(self.archive_page_instance)
            # Обновляем навигационные кнопки, если нужно добавить кнопку архива

    def init_pages(self):
        """Инициализация всех страниц"""

        # Мои задачи
        self.my_tasks_page_instance = MyTasksPage(
            db_session=self.session,
            current_user={"id": self.current_user_id, "last_name": "", "first_name": ""}
        )
        self._replace_in_stack("myTasksPage", self.my_tasks_page_instance)

        # Чужие задачи
        self.other_tasks_page_instance = OthersTasksPage(
            parent=self,
            current_user={"id": self.current_user_id, "last_name": "", "first_name": ""},
            project_id=2
        )
        self._replace_in_stack("otherTasksPage", self.other_tasks_page_instance)

        # Гант
        self.gantt_page_instance = GanttChartWidget(service=self.project_service)
        self._replace_in_stack("ganttPage", self.gantt_page_instance)

        # Аналитика - ИСПРАВЛЕНО: передаем session вместо service
        self.analytics_page_instance = AnalyticsPage(session=self.session)  # ← ИСПРАВЛЕНО
        self._replace_in_stack("analyticsPage", self.analytics_page_instance)

        # Инициализация Чата
        self.chat_page_instance = ChatPage(
            session=self.session,
            service=self.chat_service,
            projects_service=self.project_service,
            current_user_id=self.current_user_id,
            sio=self.socket_client
        )
        self._replace_in_stack("chatPage", self.chat_page_instance)

        # Переработки
        self.overtime_page_instance = OvertimePage(service=self.overtime_service)
        self._replace_in_stack("overtimePage", self.overtime_page_instance)

        # Архив
        from services.archive_service import ArchiveService
        archive_service = ArchiveService(self.session)
        self.archive_page_instance = ArchivePage(service=archive_service)
        self._replace_in_stack("archivePage", self.archive_page_instance)

        # Настройки
        self.settings_page_instance = SettingsPage(session=self.session)
        self._replace_in_stack("settingsPage", self.settings_page_instance)

        # Профиль
        self.profile_page_instance = ProfilePage(
            employee_id=self.current_user_id,
            current_user=self.current_user,
            parent=self,
            service=self.project_service
        )
        # Добавляем в стек, но не заменяем существующий (если есть)
        if not self.findChild(QWidget, "profilePage"):
            self.contentStack.addWidget(self.profile_page_instance)
        else:
            self._replace_in_stack("profilePage", self.profile_page_instance)

    def show_profile(self):
        """Показать страницу профиля"""
        if hasattr(self, 'profile_page_instance'):
            # Обновляем данные профиля для текущего пользователя
            self.profile_page_instance.employee_id = self.current_user.get('id')
            self.profile_page_instance.current_user = self.current_user
            self.profile_page_instance.load_employee()
            # Обновляем график
            if hasattr(self.profile_page_instance, 'chart_widget'):
                self.profile_page_instance.chart_widget.load_data(self.current_user.get('id'))
        else:
            # Если страница профиля не создана, создаем заново
            from windows.profile.profile_page import ProfilePage
            self.profile_page_instance = ProfilePage(
                employee_id=self.current_user.get('id'),
                current_user=self.current_user,
                parent=self
            )
            self.contentStack.addWidget(self.profile_page_instance)

        self.contentStack.setCurrentWidget(self.profile_page_instance)

    def refresh_projects_view(self):
        """Обновление списка проектов из БД и перерисовка UI."""
        # 1. Очистка старых карточек
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
            print(f"Критическая ошибка при загрузке проектов: {e}")
            return

        for dto in projects_dtos:
            card = ProjectCard(project_id=dto.id, project_data=dto)

            # Подключаем сигналы
            card.edit_clicked.connect(self.edit_project)
            card.open_clicked.connect(self.open_project)
            card.archive_clicked.connect(self.archive_project)  # 👈 ДОБАВИТЬ ЭТУ СТРОКУ

            self.project_cards.append(card)

        self.current_columns = -1
        self.adjust_card_columns()
        print(f"UI обновлен: отображено {len(self.project_cards)} проектов.")

    def connect_signals(self):
        """
        Подключение всех сигналов интерфейса к соответствующим слотам (обработчикам).
        Централизованное управление событиями MainWindow.
        """
        # ==========================================
        # 1. Навигация по страницам (contentStack)
        # ==========================================
        # Создаем маппинг кнопок к индексам страниц для чистоты кода
        self.nav_map = {
            self.leftPanel.btnMain: 0,
            self.leftPanel.btnMyTasks: 1,
            self.leftPanel.btnOtherTasks: 2,
            self.leftPanel.btnGantt: 3,
            self.leftPanel.btnAnalytics: 4,
            self.leftPanel.btnChat: 5,
            self.leftPanel.btnOvertime: 6,
            self.leftPanel.btnSettings: 7
        }
        if hasattr(self.leftPanel, 'btnArchive'):
            self.nav_map[self.leftPanel.btnArchive] = 8

        for btn, index in self.nav_map.items():
            btn.clicked.connect(lambda checked, i=index: self.switch_page(i))

        # ==========================================
        # 2. Поиск и Фильтрация (Data Flow)
        # ==========================================
        # Поиск: срабатывает при каждом изменении текста
        if hasattr(self, 'searchInput'):
            self.searchInput.textChanged.connect(self.search_projects)

        if hasattr(self, 'filterCombo'):
            # 👈 ИСПРАВЛЕНО: передаем текст, а не индекс
            self.filterCombo.currentTextChanged.connect(self.filter_projects)

        # ==========================================
        # 3. Кнопки действий и системные функции
        # ==========================================
        # Создание нового проекта
        if hasattr(self, 'btnCreateProject'):
            self.btnCreateProject.clicked.connect(self.create_project)

        # Сворачивание/разворачивание левой панели
        if hasattr(self.leftPanel, 'btnCollapse'):
            self.leftPanel.btnCollapse.clicked.connect(self.toggle_left_panel)

        # Уведомления (заглушка)
        if hasattr(self, 'btnNotifications'):
            self.btnNotifications.clicked.connect(self.show_notifications)

        # Профиль пользователя
        if hasattr(self, 'btnProfile'):
            self.btnProfile.clicked.connect(self.show_profile)

        # Общий сигнал для обновления данных при переключении на главную страницу
        # (Чтобы данные всегда были актуальны при возврате в список проектов)
        self.contentStack.currentChanged.connect(self.on_stack_page_changed)

    def on_stack_page_changed(self, index):
        """Дополнительный обработчик смены страницы в StackedWidget"""
        if index == 0:  # Если вернулись на страницу списка проектов
            self.refresh_projects_view()
        elif index == 5:  # Индекс страницы чата
            if hasattr(self, 'chat_page_instance'):
                self.chat_page_instance.load_chat_list()

    def _replace_in_stack(self, object_name, new_widget):
        """Вспомогательный метод для замены виджетов"""
        placeholder = self.findChild(QWidget, object_name)
        if placeholder:
            index = self.contentStack.indexOf(placeholder)
            self.contentStack.removeWidget(placeholder)
            placeholder.deleteLater()
            self.contentStack.insertWidget(index, new_widget)
        else:
            self.contentStack.addWidget(new_widget)

    def switch_page(self, page_index):
        """Переключение между основными страницами (0–7)"""
        page_map = {
            'main': 0,
            'my_tasks': 1,
            'other_tasks': 2,
            'gantt': 3,
            'analytics': 4,
            'chat': 5,
            'overtime': 6,
            'settings': 7
        }

        if isinstance(page_index, str):
            page_index = page_map.get(page_index, 0)

        self.contentStack.setCurrentIndex(page_index)

        # Обновляем состояние кнопок навигации
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == page_index)

    def setup_initial_state(self):
        """Начальная настройка интерфейса"""
        self.contentStack.setCurrentIndex(0)
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

    def init_my_tasks_page(self):
        """Инициализация страницы Мои задачи"""
        # Создаем сессию для страницы задач
        tasks_session = get_tasks_session()

        # Создаем страницу Мои задачи
        self.my_tasks_page_instance = MyTasksPage(
            db_session=tasks_session,  # 👈 ПЕРЕДАЕМ СЕССИЮ
            current_user=self.current_user
        )

        # Заменяем пустую страницу myTasksPage на нашу кастомную страницу
        old_page = self.findChild(QWidget, "myTasksPage")
        if old_page:
            index = self.contentStack.indexOf(old_page)
            old_page.deleteLater()
            self.contentStack.insertWidget(index, self.my_tasks_page_instance)
            self.myTasksPage = self.my_tasks_page_instance

    def edit_project(self, project_id):
        project_dto = self.project_service.get_project_for_edit(project_id)
        if not project_dto:
            QMessageBox.warning(self, "Ошибка", "Проект не найден")
            return

        from database import get_tasks_session
        from models.employees import ExternalEmployee
        from sqlalchemy import select

        session = get_tasks_session()

        participants_full = []
        if project_dto.member_ids:
            stmt = select(ExternalEmployee).where(ExternalEmployee.id.in_(project_dto.member_ids))
            employees = session.scalars(stmt).all()
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
            stmt = select(ExternalEmployee).where(ExternalEmployee.id.in_(project_dto.admin_ids))
            employees = session.scalars(stmt).all()
            for emp in employees:
                admins_full.append({
                    'id': emp.id,
                    'last_name': emp.last_name,
                    'first_name': emp.first_name,
                    'middle_name': emp.middle_name or '',
                    'position': emp.position or 'Сотрудник'
                })

        session.close()

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
            'selected_columns_data': project_dto.selected_columns_data  # 👈 УЖЕ ЕСТЬ
        }

        dialog = ProjectEditDialog(dialog_data, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            raw_results = dialog.get_project_data()
            print(
                f"📊 Результат из диалога: selected_columns_data={len(raw_results.get('selected_columns_data', []))}")  # 👈 ОТЛАДКА

            project_dto.name = raw_results['name']
            project_dto.description = raw_results['description']
            project_dto.is_archived = not raw_results.get('is_active', True)

            # 👇 ОБНОВЛЯЕМ КОЛОНКИ
            project_dto.selected_columns_data = raw_results.get('selected_columns_data', [])

            def str_to_ids(s):
                return [int(i.strip()) for i in s.split(',') if i.strip().isdigit()]

            project_dto.member_ids = str_to_ids(raw_results['participants_ids'])
            project_dto.admin_ids = str_to_ids(raw_results['admins_ids'])

            if self.project_service.update_project(project_id, project_dto):
                self.refresh_projects_view()
                QMessageBox.information(self, "Успех", "Проект обновлен")

    def resizeEvent(self, event):
        """Обработка изменения размера окна для адаптивности"""
        super().resizeEvent(event)
        self.adjust_card_columns()

    def adjust_card_columns(self):
        """Настройка количества колонок в зависимости от ширины окна"""
        if not hasattr(self, 'project_cards') or not self.project_cards:
            return
        grid = self.projectsGrid
        width = self.scrollAreaWidgetContents.width() if self.scrollAreaWidgetContents else 0

        # Определяем количество колонок в зависимости от ширины
        if width > 1200:
            columns = 4
        elif width > 900:
            columns = 3
        elif width > 600:
            columns = 2
        else:
            columns = 1

        # Перестраиваем сетку только если число колонок изменилось
        if columns != self.current_columns:
            self.current_columns = columns

            # 1. Удаляем все элементы из сетки (не удаляя сами виджеты!)
            while grid.count():
                item = grid.takeAt(0)
                if isinstance(item, QSpacerItem):
                    del item  # удаляем только спейсеры

            # 2. Раскладываем карточки по новым позициям
            for i, card in enumerate(self.project_cards):
                row, col = divmod(i, columns)
                grid.addWidget(card, row, col)

            # 3. Добавляем "пружину" (spacer) вниз, чтобы карточки были прижаты к верху
            last_row = (len(self.project_cards) + columns - 1) // columns
            grid.addItem(
                QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding),
                last_row, 0, 1, columns
            )

    def create_project(self):
        """Открыть диалог создания нового проекта"""
        from windows.projects.project_creation_dialog import ProjectCreationDialog
        dialog = ProjectCreationDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            raw_data = dialog.get_project_data()

            # Передаем наш ID в сервис
            new_project_dto = self.project_service.create_new_project(
                raw_data,
                creator_id=self.current_user_id
            )

            if new_project_dto:
                # Обновляем список карточек на главном экране
                self.refresh_projects_view()

                QMessageBox.information(
                    self,
                    "Успех",
                    f"Проект '{new_project_dto.name}' успешно создан!\n"
                    f"Созданы стандартные колонки задач и добавлено участников: {len(new_project_dto.member_ids)}"
                )

                # Опционально: можно сразу открыть созданный проект
                # self.open_project_detail(new_project_dto.id)
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось создать проект в базе данных.")

    def toggle_left_panel(self):
        """Свернуть/развернуть левую панель"""
        current_width = self.leftPanel.width()

        if current_width > 100:  # Развернуто - сворачиваем
            self.leftPanel.setMaximumWidth(80)
            self.leftPanel.btnCollapse.setText("▶")
            self.leftPanel.label.setText("МАЗ")

            # Убираем текст, оставляем только иконки
            for btn in self.nav_buttons:
                btn.setText(self.button_icons[btn])
                # Уменьшаем отступы для компактного вида
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

        else:  # Свернуто - разворачиваем
            self.leftPanel.setMaximumWidth(280)
            self.leftPanel.btnCollapse.setText("◀ Свернуть")
            self.leftPanel.label.setText("МАЗ Проекты")

            # Восстанавливаем полный текст
            for btn in self.nav_buttons:
                btn.setText(self.button_texts[btn])
                # Восстанавливаем оригинальные стили
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
        """Переход на страницу проекта (Канбан-доска)"""
        from windows.projects.project_view_page import ProjectViewPage
        # Мы передаем сервис, чтобы страница могла сама вызывать get_project_board_data
        # Это чище, чем передавать готовое DTO, которое может устареть
        project_page = ProjectViewPage(
            session=self.session,
            project_id=project_id,
            service=self.project_service,
            parent=self
        )

        self.contentStack.addWidget(project_page)
        self.contentStack.setCurrentWidget(project_page)

    def search_projects(self, text):
        """Вызывается при изменении текста в поле поиска"""
        self.current_search_query = text
        # Каждый раз перерисовываем карточки с учетом нового текста
        self.refresh_projects_view()

    def filter_projects(self, filter_text):
        """Вызывается при выборе фильтра (Все, Активные, Архив, Мои проекты)"""
        print(f"📊 Выбран фильтр: {filter_text}")  # 👈 ОТЛАДКА

        if filter_text == "Мои проекты":
            self.current_owner_filter = True
            self.current_status_filter = "Все"  # Сбрасываем статусный фильтр
        else:
            self.current_owner_filter = False
            self.current_status_filter = filter_text

        self.refresh_projects_view()

    def show_notifications(self):
        """Показать уведомления"""
        print("Показать уведомления...")

    def join_user_chat_rooms(self):
        """Присоединение к комнатам чатов пользователя"""
        try:
            from services.chat_service import ChatService
            chat_service = ChatService(self.session)
            user_chats = chat_service.get_user_chats(self.current_user_id)

            print(f"📋 Найдено чатов для пользователя {self.current_user_id}: {len(user_chats)}")

            for chat in user_chats:
                self.socket_client.join_chat_room(chat.id)
                print(f"👥 Joined chat room: {chat.id}")
        except Exception as e:
            print(f"❌ Error joining chat rooms: {e}")
            import traceback
            traceback.print_exc()

    def archive_project(self, project_id: int) -> bool:
        """
        Архивирует проект (устанавливает is_archived = True)
        """
        print(f"\n🔍 АРХИВАЦИЯ: Начало архивации проекта {project_id}")
        try:
            # Запоминаем имя проекта для уведомления
            project_name = ""
            for card in self.project_cards:
                if card.project_id == project_id:
                    project_name = card.projectTitle.text()
                    break

            # Архивируем проект
            result = self.project_service.archive_project(project_id)

            if result:
                print(f"✅ АРХИВАЦИЯ: Проект {project_id} успешно архивирован")
                print(f"📊 Текущий фильтр до архивации: {self.current_status_filter}")

                # 👇 ИСПРАВЛЕНО: Устанавливаем фильтр "Активные" принудительно
                if hasattr(self, 'filterCombo'):
                    self.filterCombo.blockSignals(True)

                    # Находим индекс пункта "Активные"
                    index = self.filterCombo.findText("Активные")
                    if index >= 0:
                        print(f"📊 Принудительно переключаем фильтр на: Активные")
                        self.filterCombo.setCurrentIndex(index)
                        # ЯВНО устанавливаем current_status_filter
                        self.current_status_filter = "Активные"
                        self.current_owner_filter = False

                    self.filterCombo.blockSignals(False)

                # Обновляем отображение проектов
                self.refresh_projects_view()

                # 👇 ВАЖНО: Обновляем страницу архива, если она существует
                if hasattr(self, 'archive_page_instance'):
                    print(f"📦 Обновляем страницу архива после архивации")
                    self.archive_page_instance.show_projects_list()

                # Показываем уведомление
                QMessageBox.information(
                    self,
                    "Архивация",
                    f"Проект '{project_name}' перемещён в архив.\n\n"
                    "Чтобы увидеть архивные проекты, нажмите кнопку 📦 Архив в левом меню."
                )

                return True
            else:
                print(f"❌ АРХИВАЦИЯ: Не удалось архивировать проект {project_id}")
                QMessageBox.warning(self, "Ошибка", "Не удалось архивировать проект")
                return False

        except Exception as e:
            print(f"❌ АРХИВАЦИЯ: Ошибка при архивации проекта: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Ошибка при архивации: {str(e)}")
            return False

    def show_archive(self):
        """Показать страницу архива"""
        print("📦 Открываем страницу архива")

        # Переключаем на страницу архива (индекс 8)
        self.switch_page(8)

        # Обновляем страницу архива
        if hasattr(self, 'archive_page_instance'):
            self.archive_page_instance.show_projects_list()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Устанавливаем стиль приложения
    app.setStyle("Fusion")

    window = MainWindow()
          # ← Вот это изменение

    sys.exit(app.exec())