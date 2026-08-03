# windows/projects/main_window_handlers.py

from PyQt6.QtWidgets import QMessageBox, QDialog, QSizePolicy, QSpacerItem, QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt

from services.employee_service.employee_service import EmployeeService
from windows.other_tasks.others_tasks_page import OthersTasksPage
from windows.projects.project_card import ProjectCard
from windows.projects.project_edit_dialog import ProjectEditDialog
from windows.projects.project_creation_dialog import ProjectCreationDialog
from windows.projects.project_view_page import ProjectViewPage


class GlobalSearchHandler:
    """Обработчик глобального поиска по всем страницам"""

    def __init__(self, main_window):
        self.main = main_window
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        self._last_query = ""
        self._is_searching = False
        self._search_results = []

    def search_all(self, query: str):
        """Глобальный поиск по всем страницам с задержкой 300мс"""
        query = query.strip()
        self._last_query = query
        self.search_timer.stop()
        self.search_timer.start(300)

    def _perform_search(self):
        """Выполняет поиск по всем страницам"""
        query = self._last_query.lower().strip()

        if self._is_searching:
            return

        self._is_searching = True

        try:
            self._clear_search_results()

            if not query:
                self._restore_default_view()
                self._update_search_status("")
                return

            total_found = 0

            # ... существующие поиски ...
            total_found += self._search_projects(query)
            total_found += self._search_my_tasks(query)
            total_found += self._search_other_tasks(query)
            total_found += self._search_overtime(query)
            total_found += self._search_chats(query)
            total_found += self._search_archive(query)
            total_found += self._search_employees(query)
            total_found += self._search_departments(query)
            total_found += self._search_divisions(query)
            total_found += self._search_tags(query)
            total_found += self._search_columns(query)
            total_found += self._search_analytics(query)

            # ⭐ ДОБАВЛЯЕМ ПОИСК ПО ГАНТУ
            total_found += self._search_gantt(query)

            self._update_search_status(query, total_found)

        except Exception as e:
            print(f"⚠️ Ошибка при выполнении поиска: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._is_searching = False

    def _search_analytics(self, query: str) -> int:
        """Поиск по аналитике (все вкладки)"""
        if 'analytics' not in self.main.navigation.pages:
            return 0

        page = self.main.navigation.pages['analytics']
        if hasattr(page, 'apply_search_filter'):
            page.apply_search_filter(query)
            if hasattr(page, 'get_filtered_count'):
                return page.get_filtered_count()
        return 0

    def _search_departments(self, query: str) -> int:
        """Поиск по отделам (вкладка Настройки)"""
        if 'settings' not in self.main.navigation.pages:
            return 0

        page = self.main.navigation.pages['settings']
        if hasattr(page, 'departments_tab'):
            tab = page.departments_tab
            if tab is not None and hasattr(tab, 'apply_search_filter'):
                tab.apply_search_filter(query)
                if hasattr(tab, 'get_filtered_count'):
                    return tab.get_filtered_count()
        return 0

    def _search_divisions(self, query: str) -> int:
        """Поиск по подразделениям (вкладка Настройки)"""
        if 'settings' not in self.main.navigation.pages:
            return 0

        page = self.main.navigation.pages['settings']
        if hasattr(page, 'divisions_tab'):
            tab = page.divisions_tab
            if tab is not None and hasattr(tab, 'apply_search_filter'):
                tab.apply_search_filter(query)
                if hasattr(tab, 'get_filtered_count'):
                    return tab.get_filtered_count()
        return 0

    def _search_tags(self, query: str) -> int:
        """Поиск по тегам (вкладка Настройки)"""
        if 'settings' not in self.main.navigation.pages:
            return 0

        page = self.main.navigation.pages['settings']
        if hasattr(page, 'tags_tab'):
            tab = page.tags_tab
            if tab is not None and hasattr(tab, 'apply_search_filter'):
                tab.apply_search_filter(query)
                if hasattr(tab, 'get_filtered_count'):
                    return tab.get_filtered_count()
        return 0

    def _search_columns(self, query: str) -> int:
        """Поиск по колонкам (вкладка Настройки)"""
        if 'settings' not in self.main.navigation.pages:
            return 0

        page = self.main.navigation.pages['settings']
        if hasattr(page, 'columns_tab'):
            tab = page.columns_tab
            if tab is not None and hasattr(tab, 'apply_search_filter'):
                tab.apply_search_filter(query)
                if hasattr(tab, 'get_filtered_count'):
                    return tab.get_filtered_count()
        return 0

    def _search_projects(self, query: str) -> int:
        """Поиск по проектам с учётом всех полей"""
        if not hasattr(self.main, 'project_handler'):
            return 0

        all_projects = self.main.project_service.get_projects_for_cards(
            search_query="",
            status_filter="Все",
            owner_filter=False
        )

        filtered = []
        for project in all_projects:
            if self._project_matches(project, query):
                filtered.append(project)

        # Если на странице проектов - обновляем
        if self.main.contentStack.currentIndex() == 0:
            self._update_projects_view(filtered)

        self._search_results = filtered
        return len(filtered)

    def _project_matches(self, project, query: str) -> bool:
        """Проверяет соответствие проекта запросу по всем полям"""
        query_lower = query.lower()

        # Базовые поля проекта
        fields_to_check = [
            getattr(project, 'name', '') or '',
            getattr(project, 'description', '') or '',
            getattr(project, 'customer', '') or '',
            getattr(project, 'contract_number', '') or '',
            getattr(project, 'status', '') or '',
            getattr(project, 'type', '') or '',
        ]

        # Проверяем базовые поля
        for field in fields_to_check:
            if query_lower in field.lower():
                return True

        # Проверяем владельца (owner_name)
        owner_name = getattr(project, 'owner_name', '') or ''
        if query_lower in owner_name.lower():
            return True

        # Проверяем куратора (manager_name)
        manager_name = getattr(project, 'manager_name', '') or ''
        if manager_name and query_lower in manager_name.lower():
            return True

        # Проверяем ID проекта
        project_id = getattr(project, 'id', None)
        if project_id and query_lower in str(project_id):
            return True

        # Проверяем дату создания
        created_at = getattr(project, 'created_at', '') or ''
        if created_at and query_lower in str(created_at):
            return True

        # Проверяем количество задач
        tasks_total = getattr(project, 'tasks_total', 0)
        if tasks_total and query_lower in str(tasks_total):
            return True

        # Проверяем количество выполненных задач
        tasks_done = getattr(project, 'tasks_done', 0)
        if tasks_done and query_lower in str(tasks_done):
            return True

        # Проверяем прогресс (если есть)
        if hasattr(project, 'tasks_total') and hasattr(project, 'tasks_done'):
            if project.tasks_total > 0:
                progress = int((project.tasks_done / project.tasks_total) * 100)
                if query_lower in str(progress):
                    return True

        # Проверяем количество участников
        member_count = getattr(project, 'member_count', 0)
        if member_count and query_lower in str(member_count):
            return True

        # Проверяем количество администраторов
        admin_count = getattr(project, 'admin_count', 0)
        if admin_count and query_lower in str(admin_count):
            return True

        # Проверяем количество колонок
        columns_count = getattr(project, 'columns_count', 0)
        if columns_count and query_lower in str(columns_count):
            return True

        # Проверяем статус архивации
        is_archived = getattr(project, 'is_archived', False)
        if is_archived:
            if query_lower in 'архив' or query_lower in 'archived' or query_lower in 'archive':
                return True
        else:
            if query_lower in 'актив' or query_lower in 'active':
                return True

        # Проверяем участников проекта (если есть список участников)
        if hasattr(project, 'members') and project.members:
            for member in project.members:
                if hasattr(member, 'full_name'):
                    member_name = member.full_name or ''
                elif hasattr(member, 'name'):
                    member_name = member.name or ''
                else:
                    member_name = str(member) if member else ''

                if query_lower in member_name.lower():
                    return True

        return False

    def _search_my_tasks(self, query: str) -> int:
        """Поиск по моим задачам"""
        if 'my_tasks' not in self.main.navigation.pages:
            return 0

        page = self.main.navigation.pages['my_tasks']
        if hasattr(page, 'apply_search_filter'):
            page.apply_search_filter(query)
            if hasattr(page, 'get_filtered_count'):
                return page.get_filtered_count()
        return 0

    def _search_other_tasks(self, query: str) -> int:
        """Поиск по чужим задачам"""
        if 'other_tasks' not in self.main.navigation.pages:
            return 0

        page = self.main.navigation.pages['other_tasks']
        if hasattr(page, 'apply_search_filter'):
            page.apply_search_filter(query)
            if hasattr(page, 'get_filtered_count'):
                return page.get_filtered_count()
        return 0

    def _search_overtime(self, query: str) -> int:
        """Поиск по переработкам"""
        if 'overtime' not in self.main.navigation.pages:
            return 0

        page = self.main.navigation.pages['overtime']
        if hasattr(page, 'apply_search_filter'):
            page.apply_search_filter(query)
            if hasattr(page, 'get_filtered_count'):
                return page.get_filtered_count()
        return 0

    def _search_chats(self, query: str) -> int:
        """Поиск по чатам"""
        if 'chat' not in self.main.navigation.pages:
            return 0

        page = self.main.navigation.pages['chat']
        if hasattr(page, 'apply_search_filter'):
            page.apply_search_filter(query)
            if hasattr(page, 'get_filtered_count'):
                return page.get_filtered_count()
        return 0

    def _search_archive(self, query: str) -> int:
        """Поиск по архиву"""
        if 'archive' not in self.main.navigation.pages:
            return 0

        page = self.main.navigation.pages['archive']
        if hasattr(page, 'apply_search_filter'):
            page.apply_search_filter(query)
            if hasattr(page, 'get_filtered_count'):
                return page.get_filtered_count()
        return 0

    def _search_employees(self, query: str) -> int:
        """Поиск по сотрудникам (вкладка Настройки)"""
        if 'settings' not in self.main.navigation.pages:
            return 0

        page = self.main.navigation.pages['settings']
        if hasattr(page, 'employees_tab'):
            employees_tab = page.employees_tab
            if employees_tab is not None and hasattr(employees_tab, 'apply_search_filter'):
                employees_tab.apply_search_filter(query)
                if hasattr(employees_tab, 'get_filtered_count'):
                    return employees_tab.get_filtered_count()
        return 0

    def _update_projects_view(self, projects):
        """Обновляет отображение проектов"""
        if not hasattr(self.main, 'project_cards'):
            return

        for card in self.main.project_cards:
            self.main.projectsGrid.removeWidget(card)
            card.deleteLater()
        self.main.project_cards = []

        for project in projects:
            card = ProjectCard(
                project_id=project.id,
                project_data=project,
                parent=None,
                service=self.main.project_service,
                permission_service=self.main.permission_service
            )
            card.edit_clicked.connect(self.main.edit_project)
            card.open_clicked.connect(self.main.open_project)
            card.archive_clicked.connect(self.main.archive_project)
            card.view_clicked.connect(self.main.view_project)
            self.main.project_cards.append(card)

        self.main.current_columns = -1
        self.main.project_handler._adjust_card_columns()

    def _clear_search_results(self):
        """Очищает результаты поиска"""
        pass

    def _restore_default_view(self):
        """Восстанавливает стандартный вид"""
        if hasattr(self.main, 'project_handler'):
            self.main.project_handler.refresh_projects_view()

        for page_name in ['my_tasks', 'other_tasks', 'overtime', 'chat', 'archive']:
            if page_name in self.main.navigation.pages:
                page = self.main.navigation.pages[page_name]
                if hasattr(page, 'clear_search_filter'):
                    page.clear_search_filter()

        # ⭐ Восстанавливаем аналитику
        if 'analytics' in self.main.navigation.pages:
            page = self.main.navigation.pages['analytics']
            if hasattr(page, 'clear_search_filter'):
                page.clear_search_filter()
            elif hasattr(page, 'force_refresh_display'):
                page.force_refresh_display()

        # ⭐ Восстанавливаем Гант
        if 'gantt' in self.main.navigation.pages:
            page = self.main.navigation.pages['gantt']
            if hasattr(page, 'clear_search_filter'):
                page.clear_search_filter()

        # Восстанавливаем все вкладки настроек
        if 'settings' in self.main.navigation.pages:
            page = self.main.navigation.pages['settings']

            # Сотрудники
            if hasattr(page, 'employees_tab'):
                tab = page.employees_tab
                if tab is not None and hasattr(tab, 'clear_search_filter'):
                    tab.clear_search_filter()

            # Отделы
            if hasattr(page, 'departments_tab'):
                tab = page.departments_tab
                if tab is not None and hasattr(tab, 'clear_search_filter'):
                    tab.clear_search_filter()

            # Подразделения
            if hasattr(page, 'divisions_tab'):
                tab = page.divisions_tab
                if tab is not None and hasattr(tab, 'clear_search_filter'):
                    tab.clear_search_filter()

            # Теги
            if hasattr(page, 'tags_tab'):
                tab = page.tags_tab
                if tab is not None and hasattr(tab, 'clear_search_filter'):
                    tab.clear_search_filter()

            # Колонки
            if hasattr(page, 'columns_tab'):
                tab = page.columns_tab
                if tab is not None and hasattr(tab, 'clear_search_filter'):
                    tab.clear_search_filter()

    def _update_search_status(self, query: str, count: int = 0):
        """Обновляет статусную строку"""
        if not query:
            self.main.statusBar().showMessage("Готов")
            return

        if count > 0:
            self.main.statusBar().showMessage(f"🔍 Найдено: {count} результатов по запросу '{query}'")
        else:
            self.main.statusBar().showMessage(f"🔍 Ничего не найдено по запросу '{query}'")

    def _search_gantt(self, query: str) -> int:
        """Поиск по диаграмме Ганта (задачи, проекты, исполнители)"""
        if 'gantt' not in self.main.navigation.pages:
            return 0

        page = self.main.navigation.pages['gantt']

        # Если запрос пустой - очищаем поиск
        if not query:
            if hasattr(page, 'clear_search_filter'):
                page.clear_search_filter()
            return 0

        # Применяем поиск
        if hasattr(page, 'apply_search_filter'):
            page.apply_search_filter(query)
            if hasattr(page, 'get_filtered_count'):
                return page.get_filtered_count()
        return 0

class ProjectViewHandler:
    """Обработчик операций с проектами (CRUD)"""

    def __init__(self, main_window):
        self.main = main_window

    def view_project(self, project_id):
        """Просмотр проекта в режиме только для чтения"""
        project_dto = self.main.project_service.get_project_for_edit(project_id)
        if not project_dto:
            QMessageBox.warning(self.main, "Ошибка", "Проект не найден")
            return

        dialog_data = self.main.project_service.prepare_edit_dialog_data(project_dto)
        dialog = ProjectEditDialog(dialog_data, parent=self.main, service=self.main.project_service)
        dialog.permission_service = self.main.permission_service
        dialog.setup_edit_mode(project_id)
        dialog.exec()

    def edit_project(self, project_id):
        """Редактирование проекта с проверкой прав"""
        project_dto = self.main.project_service.get_project_for_edit(project_id)
        if not project_dto:
            QMessageBox.warning(self.main, "Ошибка", "Проект не найден")
            return

        if self.main.permission_service and not self.main.permission_service.can_edit_project(project_id):
            self.view_project(project_id)
            return

        dialog_data = self.main.project_service.prepare_edit_dialog_data(project_dto)
        dialog = ProjectEditDialog(dialog_data, parent=self.main, service=self.main.project_service)
        dialog.permission_service = self.main.permission_service
        dialog.setup_edit_mode(project_id)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            raw_results = dialog.get_project_data()
            updated_dto = self.main.project_service.update_project_from_dialog(project_id, raw_results)

            if updated_dto and self.main.project_service.update_project(project_id, updated_dto):
                self.refresh_projects_view()
                QMessageBox.information(self.main, "Успех", "Проект обновлен")

    def refresh_projects_view(self):
        """Обновление списка проектов"""
        print(f"\n🔄 ОБНОВЛЕНИЕ ПРОЕКТОВ")
        print(f"   permission_service существует: {self.main.permission_service is not None}")

        if self.main.permission_service:
            print(f"   Роль пользователя: {self.main.permission_service.app_manager.role.value}")

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
            print(f"   Загружено проектов: {len(projects_dtos)}")
        except Exception as e:
            print(f"Ошибка при загрузке проектов: {e}")
            return

        for dto in projects_dtos:
            card = ProjectCard(
                project_id=dto.id,
                project_data=dto,
                parent=None,
                service=self.main.project_service,
                permission_service=self.main.permission_service
            )
            card.edit_clicked.connect(self.main.edit_project)
            card.open_clicked.connect(self.main.open_project)
            card.archive_clicked.connect(self.main.archive_project)
            card.view_clicked.connect(self.main.view_project)
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

    def create_project(self):
        """Создание нового проекта с автоматическим созданием чата"""
        dialog = ProjectCreationDialog(
            parent=self.main,
            service=self.main.project_service,
            creator_id=self.main.current_user_id
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            raw_data = dialog.get_project_data()

            new_project_dto = self.main.project_service.create_project_with_chat(
                raw_data,
                creator_id=self.main.current_user_id
            )

            if new_project_dto:
                self.refresh_projects_view()

                if 'chat' in self.main.pages:
                    self.main.pages['chat'].load_chat_list()

                QMessageBox.information(
                    self.main,
                    "Успех",
                    f"Проект '{new_project_dto.name}' успешно создан!\n"
                    f"Автоматически создан чат для обсуждения проекта."
                )
            else:
                QMessageBox.critical(self.main, "Ошибка", "Не удалось создать проект в базе данных.")

    def archive_project(self, project_id):
        """Архивация проекта с проверкой прав"""
        try:
            if self.main.permission_service and not self.main.permission_service.can_archive_project(project_id):
                QMessageBox.warning(
                    self.main,
                    "Доступ запрещён",
                    "У вас нет прав на архивацию этого проекта.\n"
                    "Архивировать проект могут: руководитель проекта, куратор, администратор, суперадминистратор."
                )
                return False

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
            project_service=self.main.project_service,
            parent=self.main
        )
        self.main.contentStack.addWidget(project_page)
        self.main.contentStack.setCurrentWidget(project_page)

    def search_projects(self, text):
        """Поиск проектов (оставлено для обратной совместимости)"""
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
        self._is_switching = False
        self._pending_switch = None
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
            QTimer.singleShot(50, self.pages['my_tasks'].refresh_columns)

        if 'other_tasks' in self.pages:
            QTimer.singleShot(50, self.pages['other_tasks'].refresh_columns)

    def switch_page(self, page_index):
        """Переключение между страницами с защитой от быстрых кликов"""
        print(f"\n{'=' * 60}")
        print(f"🔀 ПЕРЕКЛЮЧЕНИЕ СТРАНИЦЫ: index={page_index}")

        if self._is_switching:
            self._pending_switch = page_index
            return

        self._is_switching = True

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
            if page_index == self.PAGE_MY_TASKS:
                page_was_created = 'my_tasks' not in self.pages
                self.get_my_tasks_page()
                if not page_was_created and 'my_tasks' in self.pages:
                    self.pages['my_tasks'].load_tasks()

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
                try:
                    self.get_settings_page()
                except RuntimeError as e:
                    print(f"   ⚠️ Ошибка при получении страницы Настройки: {e}")
                    if 'settings' in self.pages:
                        del self.pages['settings']
                    self.get_settings_page()
            elif page_index == self.PAGE_ARCHIVE:
                self.get_archive_page()
                if 'archive' in self.pages:
                    if hasattr(self.pages['archive'], 'refresh_current_view'):
                        self.pages['archive'].refresh_current_view()
                    elif hasattr(self.pages['archive'], 'show_projects_list'):
                        self.pages['archive'].show_projects_list()
                    else:
                        self.pages['archive']._update_projects_view()

            elif page_index == self.PAGE_PROJECTS:
                pass

            self.main.contentStack.setCurrentIndex(page_index)

            current_idx = self.main.contentStack.currentIndex()
            if current_idx == page_index:
                print(f"   ✅ Успешно переключено на {page_name}")
            else:
                print(f"   ⚠️ Ожидался индекс {page_index}, но текущий {current_idx}")

            self._update_nav_buttons_state(page_index)

        except Exception as e:
            print(f"   ❌ ОШИБКА при переключении на {page_name}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            QTimer.singleShot(300, self._on_switch_complete)

        print(f"{'=' * 60}\n")

    def _update_nav_buttons_state(self, active_index):
        """Обновляет состояние кнопок навигации"""
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
        self._is_switching = False

        if self._pending_switch is not None:
            pending = self._pending_switch
            self._pending_switch = None
            self.switch_page(pending)

    def get_my_tasks_page(self):
        """Возвращает страницу моих задач"""
        if 'my_tasks' not in self.pages:
            from windows.my_tasks.my_tasks_page import MyTasksPage

            self.pages['my_tasks'] = MyTasksPage(
                db_session=self.main.session,
                current_user={"id": self.main.current_user_id, "last_name": "", "first_name": ""},
                column_service=self.main.column_service,
                permission_service=self.main.permission_service
            )
            self.pages['my_tasks'].open_project_requested.connect(self.open_project_by_id)
            self.main.contentStack.insertWidget(self.PAGE_MY_TASKS, self.pages['my_tasks'])

        return self.pages['my_tasks']

    def get_other_tasks_page(self):
        """Возвращает страницу чужих задач"""
        from windows.other_tasks.others_tasks_page import OthersTasksPage

        if 'other_tasks' in self.pages:
            old_page = self.pages['other_tasks']
            index = self.main.contentStack.indexOf(old_page)
            if index >= 0:
                self.main.contentStack.removeWidget(old_page)
            old_page.deleteLater()
            del self.pages['other_tasks']

        current_user = self.main.current_user if self.main.current_user else {
            "id": self.main.current_user_id,
            "last_name": "",
            "first_name": "",
            "middle_name": ""
        }

        self.pages['other_tasks'] = OthersTasksPage(
            parent=self.main,
            current_user=current_user,
            project_id=2,
            column_service=self.main.column_service,
            permission_service=self.main.permission_service
        )
        self.pages['other_tasks'].open_project_requested.connect(self.open_project_by_id)
        self.main.contentStack.insertWidget(self.PAGE_OTHER_TASKS, self.pages['other_tasks'])

        return self.pages['other_tasks']

    def open_project_by_id(self, project_id: int):
        """Открыть страницу проекта по ID"""
        from windows.projects.project_view_page import ProjectViewPage

        project_page = ProjectViewPage(
            session=self.main.session,
            project_id=project_id,
            project_service=self.main.project_service,
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
        """Универсальный метод для ленивой загрузки страниц"""
        if page_name not in self.pages:
            if page_name in self._loading_pages:
                return self.pages.get(page_name)

            self._loading_pages.add(page_name)

            try:
                self.pages[page_name] = creator_func()
                existing = self.main.contentStack.widget(insert_index)
                if existing != self.pages[page_name]:
                    self.main.contentStack.insertWidget(insert_index, self.pages[page_name])
            except Exception as e:
                print(f"   ❌ Ошибка создания страницы {page_name}: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self._loading_pages.discard(page_name)

        return self.pages[page_name]

    def get_gantt_page(self):
        """Возвращает страницу диаграммы Ганта"""
        from windows.gantt.gantt_widget import GanttWidget

        if 'gantt' in self.pages:
            old_page = self.pages['gantt']
            index = self.main.contentStack.indexOf(old_page)
            if index >= 0:
                self.main.contentStack.removeWidget(old_page)
            old_page.deleteLater()
            del self.pages['gantt']

        self.pages['gantt'] = GanttWidget(
            session=self.main.session,
            current_user_id=self.main.current_user_id,
            project_service=self.main.project_service,
            permission_service=self.main.permission_service
        )
        self.main.contentStack.insertWidget(self.PAGE_GANTT, self.pages['gantt'])

        return self.pages['gantt']

    def get_profile_page(self):
        if 'profile' not in self.pages:
            from windows.profile.profile_page import ProfilePage
            self.pages['profile'] = ProfilePage(
                employee_id=self.main.current_user.get('id'),
                current_user=self.main.current_user,
                parent=self.main
            )
            self.pages['profile'].logout_requested.connect(self.main.logout)
            self.main.contentStack.addWidget(self.pages['profile'])
        return self.pages['profile']

    def get_analytics_page(self):
        """Возвращает страницу аналитики"""
        from windows.analytics.analytics_page import AnalyticsPage

        if 'analytics' in self.pages:
            old_page = self.pages['analytics']
            index = self.main.contentStack.indexOf(old_page)
            if index >= 0:
                self.main.contentStack.removeWidget(old_page)
            old_page.deleteLater()
            del self.pages['analytics']

        self.pages['analytics'] = AnalyticsPage(session=self.main.session)
        self.main.contentStack.insertWidget(self.PAGE_ANALYTICS, self.pages['analytics'])

        return self.pages['analytics']

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
        """Возвращает страницу переработок"""
        from windows.overtime.overtime_page import OvertimePage

        employee_service = EmployeeService()

        if 'overtime' in self.pages:
            old_page = self.pages['overtime']
            index = self.main.contentStack.indexOf(old_page)
            if index >= 0:
                self.main.contentStack.removeWidget(old_page)
            old_page.deleteLater()
            del self.pages['overtime']

        page = OvertimePage(
            service=self.main.overtime_service,
            employee_service=employee_service,
            permission_service=self.main.permission_service
        )

        existing_widget = self.main.contentStack.widget(self.PAGE_OVERTIME)
        if existing_widget:
            self.main.contentStack.removeWidget(existing_widget)
            existing_widget.deleteLater()

        self.main.contentStack.insertWidget(self.PAGE_OVERTIME, page)
        self.pages['overtime'] = page

        return page

    def get_settings_page(self):
        """Возвращает страницу настроек"""
        from windows.settings.settings_page import SettingsPage

        if 'settings' in self.pages:
            try:
                old_page = self.pages['settings']
                if old_page:
                    if hasattr(old_page, '_refresh_all_tabs'):
                        old_page._refresh_all_tabs()
                    old_page.show()
                    old_page.update()
                    return old_page
            except RuntimeError:
                if 'settings' in self.pages:
                    del self.pages['settings']

        if 'settings' not in self.pages:
            existing_widget = self.main.contentStack.widget(self.PAGE_SETTINGS)
            if existing_widget:
                try:
                    self.main.contentStack.removeWidget(existing_widget)
                    existing_widget.deleteLater()
                except RuntimeError:
                    pass

            self.pages['settings'] = SettingsPage(session=self.main.session)

            if hasattr(self.main, 'permission_service'):
                self.pages['settings'].set_permission_service(self.main.permission_service)

            self.main.contentStack.insertWidget(self.PAGE_SETTINGS, self.pages['settings'])

        return self.pages['settings']

    def get_archive_page(self):
        """Возвращает страницу архива"""
        from windows.archive.archive_page import ArchivePage

        if 'archive' in self.pages:
            old_page = self.pages['archive']
            index = self.main.contentStack.indexOf(old_page)
            if index >= 0:
                self.main.contentStack.removeWidget(old_page)
            old_page.deleteLater()
            del self.pages['archive']

        self.pages['archive'] = ArchivePage(
            service=self.main.archive_service,
            permission_service=self.main.permission_service
        )
        self.main.contentStack.insertWidget(self.PAGE_ARCHIVE, self.pages['archive'])

        return self.pages['archive']

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