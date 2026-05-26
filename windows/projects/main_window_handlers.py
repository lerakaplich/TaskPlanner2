# windows/projects/main_window_handlers.py

from PyQt6.QtWidgets import QMessageBox, QDialog, QSizePolicy, QSpacerItem
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from services.employee_service.employee_service import EmployeeService
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

        # windows/projects/main_window_handlers.py

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

                # Обновляем страницу архива если она открыта
                if 'archive' in self.main.pages:
                    self.main.pages['archive'].refresh_current_view()

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


class NavigationHandler(QObject):
    """Обработчик навигации и ленивой загрузки страниц"""

    columns_updated = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.pages = {}
        self._is_switching = False  # Флаг для предотвращения множественных переключений
        self._pending_switch = None  # Ожидаемое переключение
        self._loading_pages = set()

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

    def refresh_task_pages_columns(self):
        """Обновить колонки на страницах задач"""
        print("🔄 Обновление колонок на страницах задач")

        if 'my_tasks' in self.pages:
            print("   - Обновляем страницу Мои задачи")
            QTimer.singleShot(50, self.pages['my_tasks'].refresh_columns)
        else:
            print("   - Страница Мои задачи еще не создана")

        if 'other_tasks' in self.pages:
            print("   - Обновляем страницу Чужие задачи")
            QTimer.singleShot(50, self.pages['other_tasks'].refresh_columns)
        else:
            print("   - Страница Чужие задачи еще не создана")

    def switch_page(self, page_index):
        """Переключение между страницами с защитой от быстрых кликов и отладкой"""
        print(f"\n{'=' * 60}")
        print(f"🔀 ПЕРЕКЛЮЧЕНИЕ СТРАНИЦЫ: index={page_index}")
        print(f"   - Текущая страница: {self.main.contentStack.currentIndex()}")
        print(f"   - Загружено страниц в кэше: {list(self.pages.keys())}")
        print(f"   - is_switching: {self._is_switching}")
        print(f"   - pending_switch: {self._pending_switch}")

        # Защита от множественных переключений
        if self._is_switching:
            self._pending_switch = page_index
            print(f"   ⏳ Переключение уже выполняется, сохраняем pending={page_index}")
            return

        self._is_switching = True

        # Определяем имя страницы для отладки
        page_names = {
            self.PAGE_PROJECTS: "Проекты",
            self.PAGE_MY_TASKS: "Мои задачи",
            self.PAGE_OTHER_TASKS: "Чужие задачи",
            self.PAGE_GANTT: "Гант",
            self.PAGE_ANALYTICS: "Аналитика",
            self.PAGE_CHAT: "Чат",
            self.PAGE_OVERTIME: "Переработки",
            self.PAGE_SETTINGS: "Настройки",
            self.PAGE_ARCHIVE: "Архив",
            self.PAGE_PROFILE: "Профиль"
        }
        page_name = page_names.get(page_index, f"Неизвестная({page_index})")
        print(f"   🎯 Целевая страница: {page_name}")

        try:
            # Флаг, была ли страница создана сейчас
            page_was_created = False

            # Создаем страницу при первом открытии
            if page_index == self.PAGE_MY_TASKS:
                print("   📄 Создаём/получаем страницу Мои задачи...")
                page_was_created = 'my_tasks' not in self.pages
                self.get_my_tasks_page()

                # Перезагружаем задачи при повторном открытии
                if not page_was_created and 'my_tasks' in self.pages:
                    print("   🔄 Страница уже была в кэше, перезагружаем задачи...")
                    self.pages['my_tasks'].load_tasks()

            elif page_index == self.PAGE_OTHER_TASKS:
                print("   📄 Создаём/получаем страницу Чужие задачи...")
                page_was_created = 'other_tasks' not in self.pages
                self.get_other_tasks_page()

                # ВАЖНО: Даже если страница уже была в кэше, перезагружаем задачи
                if not page_was_created and 'other_tasks' in self.pages:
                    print("   🔄 Страница уже была в кэше, перезагружаем задачи...")
                    self.pages['other_tasks'].load_tasks()

            elif page_index == self.PAGE_GANTT:
                print("   📄 Создаём/получаем страницу Гант...")
                self.get_gantt_page()
            elif page_index == self.PAGE_ANALYTICS:
                print("   📄 Создаём/получаем страницу Аналитика...")
                self.get_analytics_page()
            elif page_index == self.PAGE_CHAT:
                print("   📄 Создаём/получаем страницу Чат...")
                self.get_chat_page()
            elif page_index == self.PAGE_OVERTIME:
                print("   📄 Создаём/получаем страницу Переработки...")
                self.get_overtime_page()
            elif page_index == self.PAGE_SETTINGS:
                print("   📄 Создаём/получаем страницу Настройки...")
                self.get_settings_page()
            elif page_index == self.PAGE_ARCHIVE:
                print("   📄 Создаём/получаем страницу Архив...")
                page_was_created = 'archive' not in self.pages
                self.get_archive_page()

                if 'archive' in self.pages:
                    print("   📂 Показываем список проектов в архиве...")
                    # ВАЖНО: Принудительно обновляем содержимое архива
                    if hasattr(self.pages['archive'], 'refresh_current_view'):
                        self.pages['archive'].refresh_current_view()
                    elif hasattr(self.pages['archive'], 'show_projects_list'):
                        self.pages['archive'].show_projects_list()
                    else:
                        # Если нет метода, просто показываем список проектов
                        self.pages['archive']._update_projects_view()

            elif page_index == self.PAGE_PROJECTS:
                print("   📄 Страница Проекты всегда доступна (индекс 0)")

            # Показываем страницу
            print(f"   📺 Переключаем contentStack на индекс {page_index}")
            self.main.contentStack.setCurrentIndex(page_index)

            # Проверяем, успешно ли переключилось
            current_idx = self.main.contentStack.currentIndex()
            if current_idx == page_index:
                print(f"   ✅ Успешно переключено на {page_name} (индекс {current_idx})")
            else:
                print(f"   ⚠️ Ожидался индекс {page_index}, но текущий {current_idx}")

            # Обновляем состояние кнопок навигации
            self._update_nav_buttons_state(page_index)

        except Exception as e:
            print(f"   ❌ ОШИБКА при переключении на {page_name}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print(f"   🔓 Снимаем блокировку через 300мс")
            QTimer.singleShot(300, self._on_switch_complete)

        print(f"{'=' * 60}\n")

    def _update_nav_buttons_state(self, active_index):
        """Обновляет состояние кнопок навигации"""
        # Определяем стили для нормального состояния
        normal_style = """
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
        """

        # Определяем стили для активного (checked) состояния
        checked_style = """
            QPushButton {
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px 20px;
                text-align: left;
                border: none;
                background-color: #2C3640;
                border-left: 4px solid #ccab6e;
            }
        """

        # Определяем стили для свернутой панели
        collapsed_normal_style = """
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
        """

        collapsed_checked_style = """
            QPushButton {
                color: white;
                font-size: 20px;
                padding: 15px 0px;
                text-align: center;
                border: none;
                background-color: #2C3640;
                border-left: 4px solid #ccab6e;
            }
        """

        # Проверяем, свернута ли панель
        is_collapsed = self.main.leftPanel.width() <= 100

        for i, btn in enumerate(self.main.nav_buttons):
            if i == active_index:
                if is_collapsed:
                    btn.setStyleSheet(collapsed_checked_style)
                else:
                    btn.setStyleSheet(checked_style)
                btn.setChecked(True)
            else:
                if is_collapsed:
                    btn.setStyleSheet(collapsed_normal_style)
                else:
                    btn.setStyleSheet(normal_style)
                btn.setChecked(False)

    def _on_switch_complete(self):
        """Обработчик завершения переключения"""
        print(f"✅ _on_switch_complete: is_switching={self._is_switching}, pending={self._pending_switch}")
        self._is_switching = False

        if self._pending_switch is not None:
            pending = self._pending_switch
            self._pending_switch = None
            print(f"🔄 Выполняем отложенное переключение на {pending}")
            self.switch_page(pending)

    def get_my_tasks_page(self):
        """Возвращает страницу моих задач с подключенными сигналами"""
        print("   🚀 get_my_tasks_page вызван")

        if 'my_tasks' not in self.pages:
            from windows.my_tasks.my_tasks_page import MyTasksPage

            self.main.contentStack.setUpdatesEnabled(False)

            try:
                print("   🏗️ Создаём экземпляр MyTasksPage...")
                self.pages['my_tasks'] = MyTasksPage(
                    db_session=self.main.session,
                    current_user={"id": self.main.current_user_id, "last_name": "", "first_name": ""},
                    column_service=self.main.column_service
                )
                print("   🔗 Подключаем сигнал open_project_requested...")
                self.pages['my_tasks'].open_project_requested.connect(self.open_project_by_id)

                print(f"   📌 Вставляем в contentStack на позицию {self.PAGE_MY_TASKS}")
                self.main.contentStack.insertWidget(self.PAGE_MY_TASKS, self.pages['my_tasks'])
                print("   ✅ MyTasksPage создана и вставлена")

            except Exception as e:
                print(f"   ❌ Ошибка создания MyTasksPage: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.main.contentStack.setUpdatesEnabled(True)

        return self.pages['my_tasks']

    def get_other_tasks_page(self):
        """Возвращает страницу чужих задач с подключенными сигналами"""
        print("   🚀 get_other_tasks_page вызван")

        if 'other_tasks' not in self.pages:
            from windows.other_tasks.others_tasks_page import OthersTasksPage

            self.main.contentStack.setUpdatesEnabled(False)

            try:
                print("   🏗️ Создаём экземпляр OthersTasksPage...")
                self.pages['other_tasks'] = OthersTasksPage(
                    parent=self.main,
                    current_user={"id": self.main.current_user_id, "last_name": "", "first_name": ""},
                    project_id=2,
                    column_service=self.main.column_service
                )
                print("   🔗 Подключаем сигнал open_project_requested...")
                self.pages['other_tasks'].open_project_requested.connect(self.open_project_by_id)

                print(f"   📌 Вставляем в contentStack на позицию {self.PAGE_OTHER_TASKS}")
                self.main.contentStack.insertWidget(self.PAGE_OTHER_TASKS, self.pages['other_tasks'])
                print("   ✅ OthersTasksPage создана и вставлена")

            except Exception as e:
                print(f"   ❌ Ошибка создания OthersTasksPage: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.main.contentStack.setUpdatesEnabled(True)

        return self.pages['other_tasks']

    def open_project_by_id(self, project_id: int):
        """Открыть страницу проекта по ID"""
        from windows.projects.project_view_page import ProjectViewPage

        project_page = ProjectViewPage(
            session=self.main.session,
            project_id=project_id,
            service=self.main.project_service,
            parent=self.main
        )
        self.main.contentStack.addWidget(project_page)
        self.main.contentStack.setCurrentWidget(project_page)

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
        """Универсальный метод для ленивой загрузки страниц с отладкой"""
        print(f"   🔍 _get_or_create_page: page_name={page_name}, insert_index={insert_index}")

        if page_name not in self.pages:
            print(f"   📦 Страница {page_name} отсутствует в кэше, создаём...")

            # Проверяем, не создаётся ли уже эта страница
            if page_name in self._loading_pages:
                print(f"   ⏳ Страница {page_name} уже создаётся, ждём...")
                # Ждём немного и возвращаем существующую
                QTimer.singleShot(100, lambda: None)
                return self.pages.get(page_name)

            self._loading_pages.add(page_name)

            try:
                self.pages[page_name] = creator_func()
                print(f"   ✅ Страница {page_name} создана")

                existing = self.main.contentStack.widget(insert_index)
                if existing != self.pages[page_name]:
                    print(f"   📌 Вставляем страницу в contentStack на позицию {insert_index}")
                    self.main.contentStack.insertWidget(insert_index, self.pages[page_name])
                else:
                    print(f"   ℹ️ Страница уже была на позиции {insert_index}")

            except Exception as e:
                print(f"   ❌ Ошибка создания страницы {page_name}: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self._loading_pages.discard(page_name)
        else:
            print(f"   ✅ Страница {page_name} уже есть в кэше")

        return self.pages[page_name]

    def _recreate_page(self, page_name):
        """Пересоздать страницу (для обновления колонок)"""
        if page_name in self.pages:
            # Сохраняем старую страницу
            old_page = self.pages[page_name]

            # Удаляем из contentStack если она там есть
            index = self.main.contentStack.indexOf(old_page)
            if index >= 0:
                self.main.contentStack.removeWidget(old_page)

            # Удаляем из словаря
            del self.pages[page_name]
            old_page.deleteLater()

            # Пересоздаем страницу
            if page_name == 'my_tasks':
                self.get_my_tasks_page()
            elif page_name == 'other_tasks':
                self.get_other_tasks_page()

            # Если страница была активна, переключаемся на неё
            if self.main.contentStack.currentIndex() == index:
                self.main.contentStack.setCurrentWidget(self.pages[page_name])

    def get_gantt_page(self):
        """Возвращает страницу диаграммы Ганта"""
        from windows.gantt.gantt_widget import GanttWidget

        if 'gantt' not in self.pages:
            print("   🏗️ Создаём GanttWidget...")
            self.pages['gantt'] = GanttWidget(
                session=self.main.session,
                current_user_id=self.main.current_user_id,
                project_service=self.main.project_service
            )
            print(f"   📌 Вставляем в contentStack на позицию {self.PAGE_GANTT}")
            self.main.contentStack.insertWidget(self.PAGE_GANTT, self.pages['gantt'])
            print("   ✅ GanttWidget создан и вставлен")

        return self.pages['gantt']

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

        employee_service = EmployeeService()

        return self._get_or_create_page(
            'overtime',
            lambda: OvertimePage(
                service=self.main.overtime_service,
                employee_service=employee_service
            ),
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