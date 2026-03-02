import os
from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QScrollArea, QFrame, QGridLayout,
                             QSizePolicy, QSpacerItem, QMessageBox, QLineEdit)


class ArchivePage(QWidget):
    """Страница архива с проектами и задачами"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("archivePage")

        # Загрузка UI из файла
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "archive"
        )
        uic.loadUi(os.path.join(ui_path, "archive_page.ui"), self)

        # Данные
        self.archived_projects = []
        self.archived_tasks = []
        self.project_cards = []
        self.current_project_id = None
        self.task_cards = []  # Список для хранения карточек задач

        # Подключение сигналов
        self.back_button.clicked.connect(self.show_projects_list)

        # Инициализация UI
        self.load_test_data()
        self.show_projects_list()

    def load_test_data(self):
        """Загрузка тестовых данных"""
        # Тестовые проекты
        self.archived_projects = [
            {
                "id": 1,
                "name": "Разработка новой CRM (завершен)",
                "description": "Проект по разработке CRM системы, завершен в 2025 году",
                "archived_at": "2025-12-15",
                "archived_tasks_count": 3,
                "created_at": "2025-01-10"
            },
            {
                "id": 2,
                "name": "Модернизация конвейера (старая версия)",
                "description": "Устаревшая версия проекта модернизации",
                "archived_at": "2025-10-20",
                "archived_tasks_count": 2,
                "created_at": "2025-03-15"
            },
            {
                "id": 3,
                "name": "Внедрение ERP (тестовый период)",
                "description": "Тестовая версия ERP системы, заменена новой",
                "archived_at": "2026-01-05",
                "archived_tasks_count": 1,
                "created_at": "2025-06-01"
            }
        ]

        # Тестовые задачи (архивированные)
        self.archived_tasks = [
            {
                "id": 101,
                "title": "Написание технической документации (устаревшая)",
                "description": "Старая версия документации, заменена новой",
                "project": "Разработка новой CRM",
                "project_id": 1,
                "priority": "medium",
                "tags": ["документация", "устаревшее"],
                "created_at": "2025-10-10",
                "updated_at": "2025-12-01",
                "author": {"last_name": "Иванов", "first_name": "Иван", "middle_name": "Иванович"},
                "assignee": {"last_name": "Петров", "first_name": "Петр", "middle_name": "Петрович"},
                "deadline": "2025-11-01",
                "due_date": "2025-11-01"
            },
            {
                "id": 102,
                "title": "Интеграция со старым API",
                "description": "Интеграция с устаревшим API, больше не используется",
                "project": "Разработка новой CRM",
                "project_id": 1,
                "priority": "high",
                "tags": ["api", "интеграция"],
                "created_at": "2025-09-05",
                "updated_at": "2025-11-20",
                "author": {"last_name": "Сидоров", "first_name": "Сидор", "middle_name": "Сидорович"},
                "assignee": {"last_name": "Иванов", "first_name": "Иван", "middle_name": "Иванович"},
                "deadline": "2025-10-15",
                "due_date": "2025-10-15"
            },
            {
                "id": 103,
                "title": "Настройка сервера (устаревшая конфигурация)",
                "description": "Старая конфигурация сервера, заменена новой",
                "project": "Разработка новой CRM",
                "project_id": 1,
                "priority": "critical",
                "tags": ["сервер", "конфигурация"],
                "created_at": "2025-08-12",
                "updated_at": "2025-10-01",
                "author": {"last_name": "Петров", "first_name": "Петр", "middle_name": "Петрович"},
                "assignee": {"last_name": "Смирнов", "first_name": "Алексей", "middle_name": "Алексеевич"},
                "deadline": "2025-09-30",
                "due_date": "2025-09-30"
            },
            {
                "id": 104,
                "title": "Обучение сотрудников (старая версия)",
                "description": "Устаревшие материалы для обучения",
                "project": "Модернизация конвейера",
                "project_id": 2,
                "priority": "low",
                "tags": ["обучение", "материалы"],
                "created_at": "2025-11-01",
                "updated_at": "2025-12-10",
                "author": {"last_name": "Кузнецова", "first_name": "Елена", "middle_name": "Павловна"},
                "assignee": {"last_name": "Васильев", "first_name": "Дмитрий", "middle_name": "Николаевич"},
                "deadline": "2025-12-20",
                "due_date": "2025-12-20"
            },
            {
                "id": 105,
                "title": "Дизайн старой версии приложения",
                "description": "Макеты устаревшего дизайна",
                "project": "Модернизация конвейера",
                "project_id": 2,
                "priority": "medium",
                "tags": ["дизайн", "макеты"],
                "created_at": "2025-09-20",
                "updated_at": "2025-11-15",
                "author": {"last_name": "Михайлова", "first_name": "Ольга", "middle_name": "Андреевна"},
                "assignee": {"last_name": "Новиков", "first_name": "Павел", "middle_name": "Игоревич"},
                "deadline": "2025-11-01",
                "due_date": "2025-11-01"
            }
        ]

    def show_projects_list(self):
        """Показать список проектов"""
        self.current_project_id = None
        self.section_title.setText("Архивированные проекты")
        self.back_button.hide()

        # Показываем виджет проектов, скрываем виджет задач
        self.projects_widget.show()
        self.tasks_widget.hide()

        # Очищаем и заполняем проекты
        self.clear_projects()

        if not self.archived_projects:
            self.empty_label.show()
            self.projects_widget.hide()
            return

        self.empty_label.hide()
        self.projects_widget.show()

        # Создаем карточки проектов
        self.project_cards = []
        columns = self.calculate_columns()

        for i, project in enumerate(self.archived_projects):
            # Подсчитываем количество задач для проекта
            tasks_count = len([t for t in self.archived_tasks if t.get("project_id") == project["id"]])
            project["archived_tasks_count"] = tasks_count

            from windows.archive.archived_project_card import ArchivedProjectCard
            card = ArchivedProjectCard(project["id"], project, self)

            # Подключаем сигналы
            card.clicked.connect(self.on_project_clicked)
            card.restore_requested.connect(self.on_restore_project)
            card.delete_permanently_requested.connect(self.on_delete_project_permanently)

            self.project_cards.append(card)

            row = i // columns
            col = i % columns
            self.projects_layout.addWidget(card, row, col)

        # Добавляем растяжку
        rows = (len(self.archived_projects) + columns - 1) // columns
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.projects_layout.addItem(spacer, rows, 0, 1, columns)

    def show_project_tasks(self, project_id):
        """Показать задачи конкретного проекта (карточки располагаются вправо)"""
        self.current_project_id = project_id

        # Находим проект
        project = next((p for p in self.archived_projects if p["id"] == project_id), None)
        if project:
            self.section_title.setText(f"Задачи проекта: {project['name']}")

        self.back_button.show()

        # Скрываем виджет проектов, показываем виджет задач
        self.projects_widget.hide()
        self.tasks_widget.show()

        # Очищаем задачи
        self.clear_tasks()

        # Фильтруем задачи проекта
        project_tasks = [t for t in self.archived_tasks if t.get("project_id") == project_id]

        if not project_tasks:
            no_tasks_label = QLabel("📭 В этом проекте нет архивированных задач")
            no_tasks_label.setStyleSheet("""
                color: #999999;
                font-size: 18px;
                padding: 50px;
                background-color: #f9f9f9;
                border-radius: 10px;
            """)
            no_tasks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tasks_layout.addWidget(no_tasks_label, 0, 0, 1, self.calculate_columns())
            return

        # Создаем карточки задач (располагаем в сетке - вправо и вниз)
        self.task_cards = []
        columns = self.calculate_columns()

        from windows.archive.archived_task_card import ArchivedTaskCard

        for i, task in enumerate(project_tasks):
            card = ArchivedTaskCard(task, self)
            card.restore_requested.connect(self.on_restore_task)
            card.delete_permanently_requested.connect(self.on_delete_task_permanently)
            self.task_cards.append(card)

            row = i // columns
            col = i % columns
            self.tasks_layout.addWidget(card, row, col)

        # Добавляем растяжку
        rows = (len(project_tasks) + columns - 1) // columns
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.tasks_layout.addItem(spacer, rows, 0, 1, columns)

    def on_project_clicked(self, project_id):
        """Обработка клика по проекту"""
        self.show_project_tasks(project_id)

    def clear_projects(self):
        """Очистка списка проектов"""
        while self.projects_layout.count():
            item = self.projects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.project_cards.clear()

    def clear_tasks(self):
        """Очистка списка задач"""
        while self.tasks_layout.count():
            item = self.tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.task_cards.clear()

    def calculate_columns(self):
        """Расчет количества колонок в зависимости от ширины"""
        width = self.width()
        if width > 1400:
            return 4
        elif width > 1100:
            return 3
        elif width > 800:
            return 2
        else:
            return 1

    def resizeEvent(self, event):
        """Обработка изменения размера"""
        super().resizeEvent(event)
        if self.current_project_id is None:
            self.show_projects_list()
        else:
            self.show_project_tasks(self.current_project_id)

    def on_search(self, text):
        """Обработка поиска"""
        if not text:
            if self.current_project_id is None:
                self.show_projects_list()
            else:
                self.show_project_tasks(self.current_project_id)
            return

        text = text.lower()

        if self.current_project_id is None:
            # Поиск по проектам
            filtered_projects = [p for p in self.archived_projects
                                 if text in p["name"].lower() or
                                 (p.get("description") and text in p["description"].lower())]

            # Временно показываем отфильтрованные проекты
            self.clear_projects()

            if not filtered_projects:
                self.empty_label.setText("🔍 Ничего не найдено")
                self.empty_label.show()
                self.projects_widget.hide()
                return

            self.empty_label.hide()
            self.projects_widget.show()

            columns = self.calculate_columns()
            from windows.archive.archived_project_card import ArchivedProjectCard

            for i, project in enumerate(filtered_projects):
                card = ArchivedProjectCard(project["id"], project, self)
                card.clicked.connect(self.on_project_clicked)
                card.restore_requested.connect(self.on_restore_project)
                card.delete_permanently_requested.connect(self.on_delete_project_permanently)

                row = i // columns
                col = i % columns
                self.projects_layout.addWidget(card, row, col)
        else:
            # Поиск по задачам текущего проекта
            project_tasks = [t for t in self.archived_tasks
                             if t.get("project_id") == self.current_project_id and
                             (text in t["title"].lower() or
                              (t.get("description") and text in t["description"].lower()))]

            self.clear_tasks()

            if not project_tasks:
                no_tasks_label = QLabel("🔍 Ничего не найдено")
                no_tasks_label.setStyleSheet("color: #999999; font-size: 18px; padding: 50px;")
                no_tasks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tasks_layout.addWidget(no_tasks_label, 0, 0, 1, self.calculate_columns())
                return

            columns = self.calculate_columns()
            from windows.archive.archived_task_card import ArchivedTaskCard

            for i, task in enumerate(project_tasks):
                card = ArchivedTaskCard(task, self)
                card.restore_requested.connect(self.on_restore_task)
                card.delete_permanently_requested.connect(self.on_delete_task_permanently)

                row = i // columns
                col = i % columns
                self.tasks_layout.addWidget(card, row, col)

    def on_restore_project(self, project_data):
        """Восстановление проекта"""
        reply = QMessageBox.question(
            self,
            "Восстановление проекта",
            f"Восстановить проект '{project_data['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.archived_projects = [p for p in self.archived_projects if p["id"] != project_data["id"]]
            self.show_projects_list()
            QMessageBox.information(self, "Успех", f"Проект '{project_data['name']}' восстановлен")

    def on_restore_task(self, task_data):
        """Восстановление задачи"""
        reply = QMessageBox.question(
            self,
            "Восстановление задачи",
            f"Восстановить задачу '{task_data['title']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.archived_tasks = [t for t in self.archived_tasks if t["id"] != task_data["id"]]
            if self.current_project_id:
                self.show_project_tasks(self.current_project_id)
            QMessageBox.information(self, "Успех", f"Задача '{task_data['title']}' восстановлена")

    def on_delete_project_permanently(self, project_data):
        """Полное удаление проекта"""
        reply = QMessageBox.warning(
            self,
            "Удаление проекта",
            f"Вы уверены, что хотите навсегда удалить проект '{project_data['name']}'?\n"
            f"Это действие нельзя отменить. Все связанные задачи также будут удалены.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.archived_tasks = [t for t in self.archived_tasks if t.get("project_id") != project_data["id"]]
            self.archived_projects = [p for p in self.archived_projects if p["id"] != project_data["id"]]
            self.show_projects_list()
            QMessageBox.information(self, "Удалено", f"Проект '{project_data['name']}' удален навсегда")

    def on_delete_task_permanently(self, task_data):
        """Полное удаление задачи"""
        reply = QMessageBox.warning(
            self,
            "Удаление задачи",
            f"Вы уверены, что хотите навсегда удалить задачу '{task_data['title']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.archived_tasks = [t for t in self.archived_tasks if t["id"] != task_data["id"]]
            if self.current_project_id:
                self.show_project_tasks(self.current_project_id)
            QMessageBox.information(self, "Удалено", f"Задача '{task_data['title']}' удалена навсегда")