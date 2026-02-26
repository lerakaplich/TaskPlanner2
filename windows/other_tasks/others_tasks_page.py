import os
import json

from PyQt6 import uic
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
                             QScrollArea, QMessageBox, QApplication)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent

from windows.other_tasks.others_task_card import OthersTaskCard
from windows.other_tasks.task_dialog import TaskDialog


class OthersTasksPage(QWidget):
    """Страница Чужие задачи - для Создателя задач с drag & drop"""

    taskUpdated = pyqtSignal()  # Сигнал при обновлении задачи

    def __init__(self, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "other_tasks"
        )
        uic.loadUi(os.path.join(ui_path, "others_tasks_page.ui"), self)

        # Включаем прием drop для всей страницы
        self.setAcceptDrops(True)

        # Настраиваем канбан-доску
        self.setup_kanban()

        # Настраиваем задачи
        self.setup_tasks()

        # Подключаем сигналы
        self.priorityFilter.currentTextChanged.connect(self.filter_tasks)
        self.projectFilter.currentTextChanged.connect(self.filter_tasks)
        self.btnCreateTask.clicked.connect(self.create_new_task)

        # Подключаем сигнал перемещения для обновления статистики
        self.taskUpdated.connect(self.update_statistics)

    def setup_kanban(self):
        """Настройка канбан-доски"""
        self.kanbanLayout.setSpacing(15)

        # Создаем 4 колонки (как создатель видим все задачи)
        self.columns = {
            "todo": self.create_column("📝 К ВЫПОЛНЕНИЮ", "#2196F3", "todo"),
            "progress": self.create_column("🔧 В РАБОТЕ", "#FF9800", "progress"),
            "review": self.create_column("👀 НА ПРОВЕРКЕ", "#9C27B0", "review"),
            "done": self.create_column("✅ ВЫПОЛНЕНО", "#4CAF50", "done")
        }

        for column in self.columns.values():
            self.kanbanLayout.addWidget(column)

    def create_column(self, title, color, status):
        """Создание одной колонки канбан-доски"""
        column = QFrame()
        column.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
            }}
        """)

        # Устанавливаем свойство для идентификации колонки
        column.setProperty("column_status", status)
        column.setAcceptDrops(True)

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
        tasks_container.setAcceptDrops(True)

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
        column.column_status = status

        return column

    def clear_all_columns(self):
        """Полная очистка всех колонок перед фильтрацией"""
        for column in self.columns.values():
            layout = column.tasks_layout
            while layout.count() > 1:  # оставляем stretch
                item = layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()

    def setup_tasks(self):
        """Настройка начальных задач (задачи, созданные текущим пользователем)"""
        # Тестовые данные - задачи, созданные текущим пользователем как Создателем
        self.sample_tasks = [
            # === Разработка новой кабины ===
            {
                "id": 101,
                "title": "Согласовать эргономику кресла",
                "description": "Провести экспертизу и внести правки",
                "project": "Разработка новой кабины",
                "creator": "Вы",
                "assignee": "Иванов А.С.",
                "priority": "high",
                "deadline": "10.03.2026",
                "status": "todo",
                "created_at": "15.02.2026",
                "updated_at": "20.02.2026",
                "tags": [{"text": "Эргономика", "type": "design"}],
                "completed": False
            },
            {
                "id": 102,
                "title": "Разработать 3D-модель панели",
                "description": "Создать модель в SolidWorks",
                "project": "Разработка новой кабины",
                "creator": "Вы",
                "assignee": "Петров В.И.",
                "priority": "high",
                "deadline": "25.03.2026",
                "status": "progress",
                "created_at": "18.02.2026",
                "updated_at": "22.02.2026",
                "tags": [{"text": "3D", "type": "development"}],
                "completed": False
            },
            {
                "id": 201,
                "title": "Настроить интеграцию с 1С",
                "description": "Обмен данными между модулями",
                "project": "Внедрение ERP-системы",
                "creator": "Вы",
                "assignee": "Сидорова Е.П.",
                "priority": "critical",
                "deadline": "05.04.2026",
                "status": "todo",
                "created_at": "20.02.2026",
                "updated_at": "21.02.2026",
                "tags": [{"text": "Интеграция", "type": "dev"}],
                "completed": False
            },
            {
                "id": 301,
                "title": "Замена гидравлики на участке №3",
                "description": "Демонтаж + монтаж нового оборудования",
                "project": "Модернизация конвейера",
                "creator": "Вы",
                "assignee": "Ковалёв Д.А.",
                "priority": "high",
                "deadline": "01.03.2026",
                "status": "progress",
                "created_at": "10.02.2026",
                "updated_at": "23.02.2026",
                "tags": [{"text": "Оборудование", "type": "production"}],
                "completed": False
            },
            {
                "id": 401,
                "title": "Разработать дизайн главной страницы",
                "description": "Макеты в Figma + адаптив",
                "project": "Разработка сайта",
                "creator": "Вы",
                "assignee": "Морозова А.С.",
                "priority": "medium",
                "deadline": "15.03.2026",
                "status": "todo",
                "created_at": "12.02.2026",
                "updated_at": "20.02.2026",
                "tags": [{"text": "UI/UX", "type": "design"}],
                "completed": False
            }
        ]

        # Словарь для быстрого доступа к задачам по ID
        self.tasks_dict = {task["id"]: task for task in self.sample_tasks}

        # Распределяем задачи по колонкам
        self.all_tasks = []
        for task_data in self.sample_tasks:
            task_card = OthersTaskCard(task_data, is_creator=True)
            task_card.setParent(self)
            task_card.editRequested.connect(self.edit_task)
            task_card.deleteRequested.connect(self.delete_task)
            task_card.archiveRequested.connect(self.archive_task)
            task_card.approveRequested.connect(self.approve_task)
            task_card.returnToWorkRequested.connect(self.return_to_work)
            task_card.moveToDoneColumn.connect(self.move_task_to_done)

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

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Обработка входа перетаскивания"""
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Обработка перемещения над областью"""
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Обработка сброса задачи"""
        if not event.mimeData().hasFormat("application/x-task"):
            return

        # Получаем данные задачи
        task_data = json.loads(event.mimeData().data("application/x-task").data().decode())

        # Находим виджет карточки
        source_card = self.find_task_card(task_data["id"])
        if not source_card:
            return

        # Определяем целевую колонку
        target_column = None
        pos = event.position().toPoint()

        for column in self.columns.values():
            if column.geometry().contains(pos):
                target_column = column
                break

        if not target_column:
            return

        # Получаем статус целевой колонки
        new_status = target_column.column_status

        # Получаем старый статус
        old_status = task_data["status"]

        # Если статус не изменился, ничего не делаем
        if old_status == new_status:
            event.acceptProposedAction()
            return

        # Удаляем карточку из старой колонки
        source_card.parent().layout().removeWidget(source_card)

        # Обновляем статус в данных
        task_data["status"] = new_status
        task_data["updated_at"] = QDate.currentDate().toString("dd.MM.yyyy")

        if new_status == "done":
            task_data["completed"] = True
        else:
            task_data["completed"] = False

        source_card.task_data.update(task_data)

        # Обновляем данные в словаре
        self.tasks_dict[task_data["id"]] = task_data

        # Обновляем данные в sample_tasks
        for i, task in enumerate(self.sample_tasks):
            if task["id"] == task_data["id"]:
                self.sample_tasks[i] = task_data
                break

        # Добавляем в новую колонку
        target_column.tasks_layout.insertWidget(
            target_column.tasks_layout.count() - 1,
            source_card
        )

        # Обновляем статистику
        self.update_statistics()
        self.taskUpdated.emit()

        event.acceptProposedAction()

    def find_task_card(self, task_id):
        """Поиск карточки задачи по ID"""
        for task_card in self.all_tasks:
            if task_card.task_data.get("id") == task_id:
                return task_card
        return None

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
            new_task_data["id"] = len(self.sample_tasks) + 1000  # Генерируем новый ID
            new_task_data["creator"] = "Вы"
            new_task_data["created_at"] = QDate.currentDate().toString("dd.MM.yyyy")
            new_task_data["updated_at"] = QDate.currentDate().toString("dd.MM.yyyy")
            new_task_data["completed"] = False

            self.sample_tasks.append(new_task_data)
            self.tasks_dict[new_task_data["id"]] = new_task_data

            # Создаем карточку задачи
            task_card = OthersTaskCard(new_task_data, is_creator=True)
            task_card.setParent(self)
            task_card.editRequested.connect(self.edit_task)
            task_card.deleteRequested.connect(self.delete_task)
            task_card.archiveRequested.connect(self.archive_task)
            task_card.approveRequested.connect(self.approve_task)
            task_card.returnToWorkRequested.connect(self.return_to_work)
            task_card.moveToDoneColumn.connect(self.move_task_to_done)

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

                # Сохраняем старый статус для проверки
                old_status = task_data["status"]

                task_data.update(updated_data)
                task_data["updated_at"] = QDate.currentDate().toString("dd.MM.yyyy")

                # Если статус изменился, перемещаем карточку
                if old_status != task_data["status"]:
                    self.move_task_between_columns(task_id, old_status, task_data["status"])

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
            # Удаляем из sample_tasks и tasks_dict
            self.sample_tasks = [t for t in self.sample_tasks if t["id"] != task_id]
            if task_id in self.tasks_dict:
                del self.tasks_dict[task_id]

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
            old_status = task_data["status"]

            # Помечаем как выполненную
            task_data["status"] = "done"
            task_data["completed"] = True
            task_data["updated_at"] = QDate.currentDate().toString("dd.MM.yyyy")

            # Перемещаем в колонку "Выполнено"
            self.move_task_between_columns(task_id, old_status, "done")

            self.update_statistics()
            self.taskUpdated.emit()

            QMessageBox.information(self, "Архивация", "Задача архивирована")

    def approve_task(self, task_id):
        """Одобрение задачи на проверке"""
        task_data = next((t for t in self.sample_tasks if t["id"] == task_id), None)
        if task_data and task_data["status"] == "review":
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

        if task_card and from_status in self.columns and to_status in self.columns:
            # Удаляем из старой колонки
            old_layout = self.columns[from_status].tasks_layout
            for i in range(old_layout.count()):
                widget = old_layout.itemAt(i).widget()
                if widget == task_card:
                    old_layout.takeAt(i)
                    break

            # Добавляем в новую колонку
            new_layout = self.columns[to_status].tasks_layout
            new_layout.insertWidget(new_layout.count() - 1, task_card)

    def move_task_to_done(self, task_id):
        """Переместить задачу в колонку 'Выполнено'"""
        # Находим данные задачи
        task_data = next((t for t in self.sample_tasks if t["id"] == task_id), None)
        if not task_data:
            return

        old_status = task_data["status"]

        # Обновляем статус
        task_data["status"] = "done"
        task_data["completed"] = True
        task_data["updated_at"] = QDate.currentDate().toString("dd.MM.yyyy")

        # Перемещаем карточку между колонками
        self.move_task_between_columns(task_id, old_status, "done")

        # Обновляем статистику
        self.update_statistics()
        self.taskUpdated.emit()