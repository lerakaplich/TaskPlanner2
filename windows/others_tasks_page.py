import os
import sys
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
                             QPushButton, QScrollArea, QComboBox,
                             QLineEdit, QProgressBar, QSpacerItem,
                             QSizePolicy, QMenu, QMessageBox, QDialog,
                             QTextEdit, QDateEdit, QFormLayout, QDialogButtonBox)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QFont, QAction
from PyQt6.uic import loadUi

from others_task_card import OthersTaskCard
from task_dialog import TaskDialog  # Импортируем новый диалог


class OthersTasksPage(QWidget):
    """Страница Чужие задачи - для Создателя задач"""

    taskUpdated = pyqtSignal()  # Сигнал при обновлении задачи

    def __init__(self, parent=None):
        super().__init__(parent)

        # Загружаем UI из файла
        self.ui_path = os.path.join(os.path.dirname(__file__), "..", "ui")

        # Загружаем UI из файла
        loadUi(os.path.join(self.ui_path, "others_tasks_page.ui"), self)
        # Настраиваем канбан-доску
        self.setup_kanban()

        # Настраиваем задачи
        self.setup_tasks()

        # Подключаем сигналы
        self.priorityFilter.currentTextChanged.connect(self.filter_tasks)
        self.projectFilter.currentTextChanged.connect(self.filter_tasks)
        self.btnCreateTask.clicked.connect(self.create_new_task)

    def setup_kanban(self):
        """Настройка канбан-доски"""
        self.kanbanLayout.setSpacing(15)

        # Создаем 4 колонки (как создатель видим все задачи)
        self.columns = {
            "todo": self.create_column("📝 К ВЫПОЛНЕНИЮ", "#2196F3"),
            "progress": self.create_column("🔧 В РАБОТЕ", "#FF9800"),
            "review": self.create_column("👀 НА ПРОВЕРКЕ", "#9C27B0"),
            "done": self.create_column("✅ ВЫПОЛНЕНО", "#4CAF50")
        }

        for column in self.columns.values():
            self.kanbanLayout.addWidget(column)

    def create_column(self, title, color):
        """Создание одной колонки канбан-доски"""
        column = QFrame()
        column.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border: 1px solid #E0E0E0;
            }}
        """)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Заголовок колонки
        header = QHBoxLayout()

        title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {color};")
        header.addWidget(title_label)

        count_label = QLabel("0")
        count_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: white;
                background-color: #666;
                border-radius: 10px;
                padding: 2px 8px;
                font-weight: bold;
            }
        """)
        header.addWidget(count_label)

        header.addStretch()
        layout.addLayout(header)

        # Скроллируемая область для задач
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #F5F5F5;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #C1C1C1;
                border-radius: 4px;
                min-height: 20px;
            }
        """)

        # Контейнер для задач
        tasks_container = QWidget()
        tasks_container.setStyleSheet("background-color: transparent;")
        tasks_layout = QVBoxLayout()
        tasks_layout.setSpacing(8)
        tasks_layout.setContentsMargins(2, 2, 2, 2)
        tasks_layout.addStretch()  # Добавляем спейсер в конец
        tasks_container.setLayout(tasks_layout)

        scroll_area.setWidget(tasks_container)
        layout.addWidget(scroll_area)

        column.setLayout(layout)

        # Сохраняем ссылки на важные элементы
        column.tasks_container = tasks_container
        column.tasks_layout = tasks_layout
        column.count_label = count_label

        return column

    def setup_tasks(self):
        """Настройка начальных задач (задачи, созданные текущим пользователем)"""
        # Тестовые данные - задачи, созданные текущим пользователем как Создателем
        self.sample_tasks = [
            {
                "id": 1,
                "title": "Разработать дизайн главной страницы",
                "description": "Создать современный дизайн главной страницы сайта с адаптивной версткой",
                "project": "Разработка сайта компании",
                "creator": "Вы",  # Текущий пользователь - создатель
                "assignee": "Алексей Петров",  # Исполнитель
                "priority": "high",
                "deadline": "20.12.2024",
                "status": "todo",
                "created_at": "15.11.2024",
                "updated_at": "18.11.2024",
                "tags": [
                    {"text": "Дизайн", "type": "design"},
                    {"text": "СРОЧНО", "type": "urgent"}
                ],
                "completed": False
            },
            {
                "id": 2,
                "title": "Исправить баг в модуле авторизации",
                "description": "Пользователи не могут войти в систему после обновления",
                "project": "Внутренний портал",
                "creator": "Вы",
                "assignee": "Мария Сидорова",
                "priority": "critical",
                "deadline": "10.12.2024",
                "status": "progress",
                "created_at": "10.11.2024",
                "updated_at": "19.11.2024",
                "tags": [
                    {"text": "Баг", "type": "bug"},
                    {"text": "Безопасность", "type": "security"}
                ],
                "completed": False
            },
            {
                "id": 3,
                "title": "Написать документацию для API",
                "description": "Подготовить подробную документацию для REST API",
                "project": "Мобильное приложение",
                "creator": "Вы",
                "assignee": "Иван Иванов",
                "priority": "medium",
                "deadline": "25.12.2024",
                "status": "review",
                "created_at": "05.11.2024",
                "updated_at": "17.11.2024",
                "tags": [
                    {"text": "Документация", "type": "docs"},
                    {"text": "Разработка", "type": "development"}
                ],
                "completed": False
            },
            {
                "id": 4,
                "title": "Провести тестирование новой функции",
                "description": "Протестировать функцию импорта данных из Excel",
                "project": "ERP система",
                "creator": "Вы",
                "assignee": "Ольга Ковалева",
                "priority": "low",
                "deadline": "05.12.2024",
                "status": "done",
                "created_at": "01.11.2024",
                "updated_at": "05.11.2024",
                "tags": [
                    {"text": "Тестирование", "type": "testing"}
                ],
                "completed": True
            },
            {
                "id": 5,
                "title": "Обновить контакты клиентов",
                "description": "Обновить базу данных контактов ключевых клиентов",
                "project": "CRM система",
                "creator": "Вы",
                "assignee": "Сергей Васильев",
                "priority": "medium",
                "deadline": "15.12.2024",
                "status": "todo",
                "created_at": "12.11.2024",
                "updated_at": "12.11.2024",
                "tags": [
                    {"text": "Данные", "type": "data"}
                ],
                "completed": False
            }
        ]

        # Распределяем задачи по колонкам
        self.all_tasks = []
        for task_data in self.sample_tasks:
            task_card = OthersTaskCard(task_data, is_creator=True)
            task_card.editRequested.connect(self.edit_task)
            task_card.deleteRequested.connect(self.delete_task)
            task_card.archiveRequested.connect(self.archive_task)
            task_card.approveRequested.connect(self.approve_task)
            task_card.returnToWorkRequested.connect(self.return_to_work)

            self.all_tasks.append(task_card)

            # Добавляем в соответствующую колонку
            status = task_data["status"]
            if status == "todo":
                self.columns["todo"].tasks_layout.insertWidget(
                    self.columns["todo"].tasks_layout.count() - 1, task_card
                )
            elif status == "progress":
                self.columns["progress"].tasks_layout.insertWidget(
                    self.columns["progress"].tasks_layout.count() - 1, task_card
                )
            elif status == "review":
                self.columns["review"].tasks_layout.insertWidget(
                    self.columns["review"].tasks_layout.count() - 1, task_card
                )
            elif status == "done":
                self.columns["done"].tasks_layout.insertWidget(
                    self.columns["done"].tasks_layout.count() - 1, task_card
                )

        # Обновляем статистику
        self.update_statistics()

        # Заполняем фильтр проектов
        projects = set(task["project"] for task in self.sample_tasks)
        self.projectFilter.addItems(["Все проекты"] + sorted(list(projects)))

    def update_statistics(self):
        """Обновление статистики"""
        # Подсчет задач по статусам
        todo_count = len([t for t in self.sample_tasks if t["status"] == "todo"])
        progress_count = len([t for t in self.sample_tasks if t["status"] == "progress"])
        review_count = len([t for t in self.sample_tasks if t["status"] == "review"])
        done_count = len([t for t in self.sample_tasks if t["status"] == "done"])

        total_count = len(self.sample_tasks)

        # Обновляем заголовки колонок
        self.columns["todo"].count_label.setText(str(todo_count))
        self.columns["progress"].count_label.setText(str(progress_count))
        self.columns["review"].count_label.setText(str(review_count))
        self.columns["done"].count_label.setText(str(done_count))

        # Обновляем статистику
        self.totalTasksLabel.setText(f"📊 Всего задач: {total_count}")
        self.inProgressLabel.setText(f"🔧 В работе: {progress_count + review_count}")

        # Подсчет просроченных задач
        overdue_count = 0
        current_date = QDate.currentDate()
        for task in self.sample_tasks:
            deadline = task.get("deadline", "")
            if deadline:
                try:
                    deadline_date = QDate.fromString(deadline, "dd.MM.yyyy")
                    if deadline_date and deadline_date < current_date and not task.get("completed", False):
                        overdue_count += 1
                except:
                    pass

        self.overdueTasksLabel.setText(f"⏰ Просрочено: {overdue_count}")

        # Расчет и установка прогресса
        completed_count = len([t for t in self.sample_tasks if t.get("completed", False)])
        progress = int((completed_count / total_count * 100)) if total_count > 0 else 0
        self.overallProgress.setValue(progress)

    def filter_tasks(self):
        """Фильтрация задач"""
        priority_filter = self.priorityFilter.currentText()
        project_filter = self.projectFilter.currentText()

        priority_map = {
            "Все приоритеты": None,
            "Высокий": "high",
            "Средний": "medium",
            "Низкий": "low"
        }

        selected_priority = priority_map.get(priority_filter)

        # Скрываем все задачи
        for task_card in self.all_tasks:
            task_card.hide()

            # Проверяем фильтры
            task_data = task_card.task_data
            show = True

            if selected_priority and task_data.get("priority") != selected_priority:
                show = False

            if project_filter != "Все проекты" and task_data.get("project") != project_filter:
                show = False

            if show:
                task_card.show()

    def create_new_task(self):
        """Создание новой задачи с использованием универсального диалога"""
        dialog = TaskDialog(self, mode='create')
        if dialog.exec():
            new_task_data = dialog.get_task_data()
            new_task_data["id"] = len(self.sample_tasks) + 1
            new_task_data["creator"] = "Вы"
            new_task_data["created_at"] = QDate.currentDate().toString("dd.MM.yyyy")
            new_task_data["updated_at"] = QDate.currentDate().toString("dd.MM.yyyy")
            new_task_data["completed"] = False

            self.sample_tasks.append(new_task_data)

            # Создаем карточку задачи
            task_card = OthersTaskCard(new_task_data, is_creator=True)
            task_card.editRequested.connect(self.edit_task)
            task_card.deleteRequested.connect(self.delete_task)
            task_card.archiveRequested.connect(self.archive_task)
            task_card.approveRequested.connect(self.approve_task)
            task_card.returnToWorkRequested.connect(self.return_to_work)

            self.all_tasks.append(task_card)

            # Добавляем в соответствующую колонку
            status = new_task_data["status"]
            if status == "todo":
                self.columns["todo"].tasks_layout.insertWidget(
                    self.columns["todo"].tasks_layout.count() - 1, task_card
                )
            elif status == "progress":
                self.columns["progress"].tasks_layout.insertWidget(
                    self.columns["progress"].tasks_layout.count() - 1, task_card
                )
            elif status == "review":
                self.columns["review"].tasks_layout.insertWidget(
                    self.columns["review"].tasks_layout.count() - 1, task_card
                )
            elif status == "done":
                self.columns["done"].tasks_layout.insertWidget(
                    self.columns["done"].tasks_layout.count() - 1, task_card
                )

            # Обновляем фильтр проектов
            current_projects = [self.projectFilter.itemText(i) for i in range(self.projectFilter.count())]
            if new_task_data["project"] not in current_projects:
                self.projectFilter.addItem(new_task_data["project"])

            self.update_statistics()
            self.taskUpdated.emit()

    def edit_task(self, task_id):
        """Редактирование задачи с использованием универсального диалога"""
        task_data = next((t for t in self.sample_tasks if t["id"] == task_id), None)
        if task_data:
            dialog = TaskDialog(self, task_data=task_data, mode='edit')
            if dialog.exec():
                updated_data = dialog.get_task_data()
                task_data.update(updated_data)
                task_data["updated_at"] = QDate.currentDate().toString("dd.MM.yyyy")

                # Обновляем карточку
                for task_card in self.all_tasks:
                    if task_card.task_data["id"] == task_id:
                        task_card.update_task_data(task_data)
                        break

                self.update_statistics()
                self.taskUpdated.emit()

    def delete_task(self, task_id):
        """Удаление задачи"""
        reply = QMessageBox.question(
            self, 'Удаление задачи',
            'Вы уверены, что хотите удалить эту задачу?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Удаляем из sample_tasks
            self.sample_tasks = [t for t in self.sample_tasks if t["id"] != task_id]

            # Удаляем карточку
            for i, task_card in enumerate(self.all_tasks):
                if task_card.task_data["id"] == task_id:
                    task_card.deleteLater()
                    self.all_tasks.pop(i)
                    break

            self.update_statistics()
            self.taskUpdated.emit()

    def archive_task(self, task_id):
        """Архивация задачи"""
        task_data = next((t for t in self.sample_tasks if t["id"] == task_id), None)
        if task_data:
            # Помечаем как выполненную и убираем из отображения
            task_data["status"] = "done"
            task_data["completed"] = True
            task_data["updated_at"] = QDate.currentDate().toString("dd.MM.yyyy")

            # Перемещаем в колонку "Выполнено"
            self.move_task_between_columns(task_id, task_data.get("old_status", "todo"), "done")

            self.update_statistics()
            self.taskUpdated.emit()

            QMessageBox.information(self, "Архивация", "Задача архивирована")

    def approve_task(self, task_id):
        """Одобрение задачи на проверке"""
        task_data = next((t for t in self.sample_tasks if t["id"] == task_id), None)
        if task_data and task_data["status"] == "review":
            reply = QMessageBox.question(
                self, 'Одобрение задачи',
                'Одобрить выполнение задачи?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                task_data["status"] = "done"
                task_data["completed"] = True
                task_data["updated_at"] = QDate.currentDate().toString("dd.MM.yyyy")

                # Перемещаем карточку
                self.move_task_between_columns(task_id, "review", "done")

                self.update_statistics()
                self.taskUpdated.emit()

    def return_to_work(self, task_id):
        """Возврат задачи на доработку"""
        task_data = next((t for t in self.sample_tasks if t["id"] == task_id), None)
        if task_data and task_data["status"] == "review":
            reply = QMessageBox.question(
                self, 'Возврат задачи',
                'Вернуть задачу на доработку?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                task_data["status"] = "progress"
                task_data["updated_at"] = QDate.currentDate().toString("dd.MM.yyyy")

                # Перемещаем карточку
                self.move_task_between_columns(task_id, "review", "progress")

                self.update_statistics()
                self.taskUpdated.emit()

    def move_task_between_columns(self, task_id, from_status, to_status):
        """Перемещение задачи между колонками"""
        # Находим карточку
        task_card = None
        for card in self.all_tasks:
            if card.task_data["id"] == task_id:
                task_card = card
                break

        if task_card:
            # Удаляем из старой колонки
            if from_status in self.columns:
                old_layout = self.columns[from_status].tasks_layout
                for i in range(old_layout.count()):
                    widget = old_layout.itemAt(i).widget()
                    if widget == task_card:
                        old_layout.takeAt(i)
                        widget.setParent(None)
                        break

            # Добавляем в новую колонку
            if to_status in self.columns:
                new_layout = self.columns[to_status].tasks_layout
                new_layout.insertWidget(new_layout.count() - 1, task_card)