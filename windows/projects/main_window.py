import os
import sys

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QFrame, QSizePolicy, QSpacerItem, QWidget, QDialog
from PyQt6.uic import loadUi  # <-- Добавьте эту строку
from windows.analytics.analytics_page import AnalyticsPage
from windows.archive.archive_page import ArchivePage
from windows.gantt.gantt_chart import GanttChartWidget
from windows.my_tasks.my_tasks_page import MyTasksPage
from windows.other_tasks.others_tasks_page import OthersTasksPage
from windows.overtime.overtime_page import OvertimePage
from windows.profile.profile_page import ProfilePage
from windows.projects.project_creation_dialog import ProjectCreationDialog


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/analytics/employees/
            "..", "..",  # поднимаемся до корня проекта
            "ui", "projects"  # спускаемся в нужную подпапку ui
        )
        uic.loadUi(os.path.join(ui_path, "main_window.ui"), self)

        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/analytics/employees/
            "..", "..",  # поднимаемся до корня проекта
            "ui"  # спускаемся в нужную подпапку ui
        )
        uic.loadUi(os.path.join(ui_path, "left_panel.ui"), self.leftPanel)


        # Инициализация страниц
        self.init_pages()

        # Подключаем сигналы к слотам
        self.connect_signals()

        # Инициализация
        self.setup_initial_state()
        self.showMaximized()

    def get_test_gantt_tasks(self):
        return [
            {
                "id": 1,
                "title": "Проектирование UI",
                "start": "2026-02-01",
                "end": "2026-02-05",
                "progress": 100
            },
            {
                "id": 2,
                "title": "Верстка экранов",
                "start": "2026-02-06",
                "end": "2026-02-12",
                "progress": 60
            },
            {
                "id": 3,
                "title": "Логика приложения",
                "start": "2026-02-10",
                "end": "2026-02-18",
                "progress": 20
            }
        ]

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

    # Обновляем метод init_pages в MainWindow
    def init_pages(self):
        """Инициализация всех страниц"""

        # 0 — Главная (уже есть в UI)

        # 1 — Мои задачи
        self.my_tasks_page_instance = MyTasksPage()
        old_page = self.findChild(QWidget, "myTasksPage")
        if old_page:
            index = self.contentStack.indexOf(old_page)
            old_page.deleteLater()
            self.contentStack.insertWidget(index, self.my_tasks_page_instance)

        # 2 — Чужие задачи
        self.other_tasks_page_instance = OthersTasksPage()
        other_old = self.findChild(QWidget, "otherTasksPage")
        if other_old:
            index = self.contentStack.indexOf(other_old)
            other_old.deleteLater()
            self.contentStack.insertWidget(index, self.other_tasks_page_instance)

        # 3 — Диаграмма Ганта
        self.gantt_page_instance = GanttChartWidget()
        gantt_old = self.findChild(QWidget, "ganttPage")
        if gantt_old:
            index = self.contentStack.indexOf(gantt_old)
            gantt_old.deleteLater()
            self.contentStack.insertWidget(index, self.gantt_page_instance)

        # 4 — Аналитика / Навыки
        self.analytics_page_instance = AnalyticsPage()
        analytics_old = self.findChild(QWidget, "analyticsPage")
        if analytics_old:
            index = self.contentStack.indexOf(analytics_old)
            analytics_old.deleteLater()
            self.contentStack.insertWidget(index, self.analytics_page_instance)

        # 5 — Чат (если есть в UI)

        # 6 — Переработки
        self.overtime_page_instance = OvertimePage()
        overtime_old = self.findChild(QWidget, "overtimePage")
        if overtime_old:
            index = self.contentStack.indexOf(overtime_old)
            overtime_old.deleteLater()
            self.contentStack.insertWidget(index, self.overtime_page_instance)

        # 7 — Настройки (если есть в UI)

        # 8 — Архив (новая страница)
        self.init_archive_page()

        # Отдельная страница профиля
        self.profile_page_instance = ProfilePage()
        self.contentStack.addWidget(self.profile_page_instance)

    # Обновляем метод connect_signals в MainWindow
    def connect_signals(self):
        """Подключение всех сигналов к слотам"""
        # Навигационные кнопки
        self.leftPanel.btnMain.clicked.connect(lambda: self.switch_page(0))
        self.leftPanel.btnMyTasks.clicked.connect(lambda: self.switch_page(1))
        self.leftPanel.btnOtherTasks.clicked.connect(lambda: self.switch_page(2))
        self.leftPanel.btnGantt.clicked.connect(lambda: self.switch_page(3))
        self.leftPanel.btnAnalytics.clicked.connect(lambda: self.switch_page(4))
        self.leftPanel.btnChat.clicked.connect(lambda: self.switch_page(5))
        self.leftPanel.btnOvertime.clicked.connect(lambda: self.switch_page(6))
        self.leftPanel.btnSettings.clicked.connect(lambda: self.switch_page(7))

        # Добавляем кнопку для архива, если её нет в левой панели
        if hasattr(self.leftPanel, 'btnArchive'):
            self.leftPanel.btnArchive.clicked.connect(lambda: self.switch_page(8))

        # Кнопки действий
        self.btnCreateProject.clicked.connect(self.create_project)
        self.leftPanel.btnCollapse.clicked.connect(self.toggle_left_panel)

        # Поиск
        self.searchInput.textChanged.connect(self.search_projects)

        # Фильтр
        self.filterCombo.currentTextChanged.connect(self.filter_projects)

        # Уведомления
        self.btnNotifications.clicked.connect(self.show_notifications)

        # Профиль
        self.btnProfile.clicked.connect(self.show_profile)

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

    def show_profile(self):
        """Показать страницу профиля (не трогает навигационные кнопки)"""
        self.contentStack.setCurrentWidget(self.profile_page_instance)

    # Остальной код полностью без изменений
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
            self.leftPanel.btnSettings
        ]
        self.button_texts = {
            self.leftPanel.btnMain: "🚚 Проекты",
            self.leftPanel.btnMyTasks: "✅ Мои задачи",
            self.leftPanel.btnOtherTasks: "👥 Чужие задачи",
            self.leftPanel.btnGantt: "📈 Диаграмма Ганта",
            self.leftPanel.btnAnalytics: "📊 Аналитика/Навыки",
            self.leftPanel.btnChat: "💬 Чат",
            self.leftPanel.btnOvertime: "♻️ Переработки",
            self.leftPanel.btnSettings: "⚙️ Настройки"
        }
        self.button_icons = {
            self.leftPanel.btnMain: "🚚",
            self.leftPanel.btnMyTasks: "✅",
            self.leftPanel.btnOtherTasks: "👥",
            self.leftPanel.btnGantt: "📈",
            self.leftPanel.btnAnalytics: "📊",
            self.leftPanel.btnChat: "💬",
            self.leftPanel.btnOvertime: "♻️",
            self.leftPanel.btnSettings: "⚙️"
        }
        self.setup_responsive_cards()

    def init_my_tasks_page(self):
        """Инициализация страницы Мои задачи"""
        # Создаем страницу Мои задачи
        self.my_tasks_page_instance = MyTasksPage()

        # Заменяем пустую страницу myTasksPage на нашу кастомную страницу
        old_page = self.findChild(QWidget, "myTasksPage")
        if old_page:
            # Получаем индекс страницы в contentStack
            index = self.contentStack.indexOf(old_page)
            # Удаляем старую страницу
            old_page.deleteLater()
            # Добавляем новую страницу на тот же индекс
            self.contentStack.insertWidget(index, self.my_tasks_page_instance)

            # Обновляем ссылку на страницу
            self.myTasksPage = self.my_tasks_page_instance

    def setup_responsive_cards(self):
        """Настройка адаптивности карточек проектов"""
        projects = [
            {
                "id": 1,
                "title": "Разработка новой кабины",
                "name": "Разработка новой кабины",
                "progress": 75,
                "owner": "Петров А.В.",
                "start_date": "01.09.2024",
                "deadline": "15.12.2024",
                "is_critical": True,
                "participants": [1, 2, 3, 4, 5, 6, 7, 8],
                "admins": [1, 2],
                "description": "Проект по разработке новой кабины для автомобиля",
                "status": "Активен",
                "end_date": "15.12.2024"
            },
            {
                "id": 2,
                "title": "Внедрение ERP-системы",
                "name": "Внедрение ERP-системы",
                "progress": 45,
                "owner": "Сидорова Е.П.",
                "start_date": "15.08.2024",
                "deadline": "30.03.2025",
                "is_critical": False,
                "participants": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                "admins": [1, 3, 5],
                "description": "Внедрение корпоративной ERP-системы",
                "status": "Активен",
                "end_date": "30.03.2025"
            },
            {
                "id": 3,
                "title": "Модернизация конвейера",
                "name": "Модернизация конвейера",
                "progress": 90,
                "owner": "Иванов И.И.",
                "start_date": "01.07.2024",
                "deadline": "10.11.2024",
                "is_critical": True,
                "participants": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                "admins": [1, 4],
                "description": "Модернизация производственного конвейера",
                "status": "Активен",
                "end_date": "10.11.2024"
            },
            {
                "id": 4,
                "title": "Разработка сайта",
                "name": "Разработка сайта",
                "progress": 30,
                "owner": "Кузнецов С.П.",
                "start_date": "01.10.2024",
                "deadline": "15.02.2025",
                "is_critical": False,
                "participants": [1, 2, 3, 4, 5],
                "admins": [1],
                "description": "Разработка корпоративного сайта",
                "status": "Активен",
                "end_date": "15.02.2025"
            }
        ]

        from windows.projects.project_card import ProjectCard

        self.project_cards = []
        for proj in projects:
            card = ProjectCard(proj["id"], proj, self.scrollAreaWidgetContents)

            # Подключаем сигналы
            card.open_clicked.connect(self.open_project)
            card.edit_clicked.connect(self.edit_project)

            self.project_cards.append(card)

        self.current_columns = 0
        self.adjust_card_columns()

    def edit_project(self, project_id):
        """Редактирование проекта"""
        print(f"Редактирование проекта {project_id}...")

        # Находим данные проекта
        project_data = None
        for card in self.project_cards:
            if card.project_id == project_id:
                project_data = card.project_data
                break

        if not project_data:
            return

        from windows.projects.project_edit_dialog import ProjectEditDialog

        dialog = ProjectEditDialog(project_data, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_data = dialog.get_project_data()
            print("Проект обновлен:", updated_data)

            # Обновляем данные в карточке
            for card in self.project_cards:
                if card.project_id == project_id:
                    card.update_data(updated_data)
                    break

            # Здесь можно добавить сохранение в БД
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Проект обновлен",
                f"Проект '{updated_data['name']}' успешно обновлен!\n\n"
                f"Участников: {len(updated_data.get('participants', []))}\n"
                f"Администраторов: {len(updated_data.get('admins', []))}"
            )
    def resizeEvent(self, event):
        """Обработка изменения размера окна для адаптивности"""
        super().resizeEvent(event)
        self.adjust_card_columns()

    def adjust_card_columns(self):
        """Настройка количества колонок в зависимости от ширины окна"""
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

        if columns != self.current_columns or grid.count() == 0:
            # Очищаем grid
            while grid.count():
                item = grid.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

            # Добавляем карточки заново
            for i, card in enumerate(self.project_cards):
                row = i // columns
                col = i % columns
                grid.addWidget(card, row, col)

            # Добавляем вертикальный спейсер в конце для выравнивания сверху
            rows = (len(self.project_cards) + columns - 1) // columns
            spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
            grid.addItem(spacer, rows, 0, 1, columns)

            self.current_columns = columns

    def create_project(self):
        """Открыть диалог создания нового проекта"""
        dialog = ProjectCreationDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            project = dialog.get_project_data()
            print("Проект создан:", project)

            # Здесь можно добавить:
            # - Сохранение в БД
            # - Обновление списка проектов
            # - Показ уведомления
            # - Открытие созданного проекта

            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Проект создан",
                f"Проект '{project['name']}' успешно создан!"
            )


    def refresh_projects_list(self, new_project=None):
        """Обновление списка проектов после создания"""
        if new_project:
            # Добавление нового проекта в список
            # Здесь должен быть код для динамического добавления карточки проекта
            print(f"Добавление проекта '{new_project['name']}' в список")

            # Можно вызвать метод для перезагрузки всех проектов
            # self.load_projects()
            pass

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
        """Открыть проект по ID"""
        print(f"Открытие проекта {project_id}...")

        # Здесь можно загрузить данные проекта из базы данных
        # Для примера создаем тестовые данные
        project_data = {
            'id': project_id,
            'name': f'Проект #{project_id}: Разработка новой CRM системы',
            'description': 'Проект по созданию современной CRM системы для отдела продаж с интеграцией существующих сервисов и аналитикой в реальном времени. Включает модули управления контактами, сделками, задачами и отчетами.',
            'status': 'Активен',
            'start_date': '01.02.2024',
            'end_date': '30.06.2024',
            'progress': 45,
            'admins': [
                'Иванов Иван Иванович (Руководитель проекта)',
                'Петрова Анна Сергеевна (Технический директор)',
                'Сидоров Алексей Владимирович (Ведущий разработчик)'
            ],
            'participants': [
                'Кузнецова Елена Павловна (Аналитик)',
                'Васильев Дмитрий Николаевич (Backend-разработчик)',
                'Михайлова Ольга Андреевна (Frontend-разработчик)',
                'Новиков Павел Игоревич (Тестировщик)',
                'Соколова Татьяна Валерьевна (Дизайнер)',
                'Морозов Артем Викторович (DevOps)',
                'Волкова Наталья Сергеевна (Project Manager)',
                'Козлов Максим Денисович (Аналитик данных)'
            ]
        }

        # Создаем страницу проекта
        from windows.projects.project_view_page import ProjectViewPage
        self.project_view_page = ProjectViewPage(project_data)

        # Добавляем в стек контента
        self.contentStack.addWidget(self.project_view_page)

        # Переключаемся на страницу проекта
        self.contentStack.setCurrentWidget(self.project_view_page)

    def search_projects(self, text):
        """Поиск проектов"""
        print(f"Поиск: {text}")

    def filter_projects(self, filter_text):
        """Фильтрация проектов"""
        print(f"Фильтр: {filter_text}")

    def show_notifications(self):
        """Показать уведомления"""
        print("Показать уведомления...")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Устанавливаем стиль приложения
    app.setStyle("Fusion")

    window = MainWindow()
          # ← Вот это изменение

    sys.exit(app.exec())