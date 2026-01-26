import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QFrame, QSizePolicy, QSpacerItem, QWidget
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi
from my_tasks_page import MyTasksPage  # Импортируем класс MyTasksPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Загружаем UI из файла
        loadUi("main_window.ui", self)
        loadUi("left_panel.ui", self.leftPanel)

        # Инициализация страницы Мои задачи
        self.init_my_tasks_page()

        # Подключаем сигналы к слотам
        self.connect_signals()

        # Инициализация
        self.setup_initial_state()

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

    def connect_signals(self):
        """Подключение всех сигналов к слотам"""
        # Навигационные кнопки
        self.leftPanel.btnMain.clicked.connect(lambda: self.switch_page(0))
        self.leftPanel.btnMyTasks.clicked.connect(lambda: self.switch_page(1))
        self.leftPanel.btnOtherTasks.clicked.connect(lambda: self.switch_page(2))
        self.leftPanel.btnGantt.clicked.connect(lambda: self.switch_page(3))
        self.leftPanel.btnAnalytics.clicked.connect(lambda: self.switch_page(4))
        self.leftPanel.btnChat.clicked.connect(lambda: self.switch_page(5))
        self.leftPanel.btnSettings.clicked.connect(lambda: self.switch_page(6))

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

    def setup_initial_state(self):
        """Начальная настройка интерфейса"""
        # Устанавливаем первую страницу активной
        self.contentStack.setCurrentIndex(0)

        # Создаем группу для навигационных кнопок
        self.nav_buttons = [
            self.leftPanel.btnMain,
            self.leftPanel.btnMyTasks,
            self.leftPanel.btnOtherTasks,
            self.leftPanel.btnGantt,
            self.leftPanel.btnAnalytics,
            self.leftPanel.btnChat,
            self.leftPanel.btnSettings
        ]

        # Сохраняем оригинальные тексты кнопок
        self.button_texts = {
            self.leftPanel.btnMain: "📊  Доски/Главная",
            self.leftPanel.btnMyTasks: "✅  Мои задачи",
            self.leftPanel.btnOtherTasks: "👥  Чужие задачи",
            self.leftPanel.btnGantt: "📈  Диаграмма Ганта",
            self.leftPanel.btnAnalytics: "📊  Аналитика/Навыки",
            self.leftPanel.btnChat: "💬  Чат",
            self.leftPanel.btnSettings: "⚙️  Настройки"
        }

        # Сохраняем оригинальные иконки (первые символы текста)
        self.button_icons = {
            self.leftPanel.btnMain: "📊",
            self.leftPanel.btnMyTasks: "✅",
            self.leftPanel.btnOtherTasks: "👥",
            self.leftPanel.btnGantt: "📈",
            self.leftPanel.btnAnalytics: "📊",
            self.leftPanel.btnChat: "💬",
            self.leftPanel.btnSettings: "⚙️"
        }

        # Настройка адаптивности карточек
        self.setup_responsive_cards()

    def setup_responsive_cards(self):
        """Настройка адаптивности карточек проектов"""
        projects = [
            {
                "title": "Разработка новой кабины",
                "progress": 75,
                "owner": "Петров А.В.",
                "start": "01.09.2024",
                "participants": 8,
                "deadline": "15.12.2024",
                "is_critical": True
            },
            {
                "title": "Внедрение ERP-системы",
                "progress": 45,
                "owner": "Сидорова Е.П.",
                "start": "15.08.2024",
                "participants": 15,
                "deadline": "30.03.2025",
                "is_critical": False
            },
            {
                "title": "Модернизация конвейера",
                "progress": 90,
                "owner": "Иванов И.И.",
                "start": "01.07.2024",
                "participants": 12,
                "deadline": "10.11.2024",
                "is_critical": True
            },
            {
                "title": "Разработка сайта",
                "progress": 30,
                "owner": "Кузнецов С.П.",
                "start": "01.10.2024",
                "participants": 5,
                "deadline": "15.02.2025",
                "is_critical": False
            }
        ]

        self.project_cards = []
        for i, proj in enumerate(projects):
            card = QFrame(self.scrollAreaWidgetContents)
            loadUi("project_card.ui", card)

            card.projectTitle.setText(proj["title"])
            card.progressBar.setValue(proj["progress"])
            card.projectInfo.setText(f"Владелец: {proj['owner']}")
            card.startDate.setText(f"Старт: {proj['start']}")
            card.participants.setText(f"Участники: {proj['participants']} чел.")
            card.deadline.setText(f"До {proj['deadline']}")
            if proj["is_critical"]:
                card.deadline.setStyleSheet("font-size: 11px; color: #D22730; padding: 4px 8px; background-color: #FFEEEE; border-radius: 4px;")
            else:
                card.deadline.setStyleSheet("font-size: 11px; color: #666; padding: 4px 8px; background-color: #F0F0F0; border-radius: 4px;")

            card.btnOpen.clicked.connect(lambda checked, pid=i+1: self.open_project(pid))

            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.project_cards.append(card)

        self.current_columns = 0
        self.adjust_card_columns()

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

    def switch_page(self, page_index):
        """Переключение между страницами"""
        self.contentStack.setCurrentIndex(page_index)

        # Обновляем состояние кнопок навигации
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == page_index)

    def create_project(self):
        from project_creation_dialog import ProjectCreationDialog

        dialog = ProjectCreationDialog(self)

        if dialog.exec():
            project = dialog.get_project_data()
            print("Проект создан:", project)

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

    def search_projects(self, text):
        """Поиск проектов"""
        print(f"Поиск: {text}")

    def filter_projects(self, filter_text):
        """Фильтрация проектов"""
        print(f"Фильтр: {filter_text}")

    def show_notifications(self):
        """Показать уведомления"""
        print("Показать уведомления...")

    def show_profile(self):
        """Показать профиль"""
        print("Показать профиль...")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Устанавливаем стиль приложения
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())