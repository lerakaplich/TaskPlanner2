from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
                             QCheckBox, QPushButton, QScrollArea, QComboBox,
                             QLineEdit, QProgressBar, QMenu, QApplication, QSizePolicy)
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QPoint
from PyQt6.QtGui import QDrag, QPixmap, QPainter
from PyQt6.uic import loadUi
import json


class TaskCard(QFrame):
    """Карточка задачи с поддержкой drag&drop"""

    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.task_data = task_data

        # Загружаем UI из файла
        loadUi("task_card.ui", self)


        self.setObjectName("taskCard")

        self.setup_ui()
        self.setAcceptDrops(True)

    def setup_ui(self):
        """Настройка UI карточки на основе данных"""
        # Устанавливаем фиксированные размеры
        self.setMinimumHeight(180)
        self.setMaximumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Заполняем данные
        self.checkboxTitle.setText(self.task_data["title"])
        self.checkboxTitle.stateChanged.connect(self.on_checkbox_changed)

        # Описание
        if self.task_data.get("description"):
            self.descriptionLabel.setText(self.task_data["description"])
            self.descriptionLabel.show()
        else:
            self.descriptionLabel.hide()

        # Теги
        if self.task_data.get("tags"):
            self.setup_tags()
        else:
            # Скрываем layout с тегами если их нет
            for i in reversed(range(self.tagsLayout.count())):
                self.tagsLayout.itemAt(i).widget().setParent(None)

        # Дедлайн
        deadline_text = self.task_data.get("deadline", "")
        self.deadlineLabel.setText(f"⏰ {deadline_text}")
        self.update_deadline_style()

        # Проект
        self.projectLabel.setText(self.task_data["project"])

        # Аватар
        self.avatarLabel.setText(self.task_data.get("assignee_initials", "ИИ"))

        # Кнопки действий
        self.setup_action_buttons()

        # Соединяем сигналы
        self.menuButton.clicked.connect(self.show_context_menu)

        # Устанавливаем цвет левой границы в зависимости от приоритета
        self.update_card_style()

    def setup_tags(self):
        """Настройка тегов"""
        # Очищаем существующие теги
        for i in reversed(range(self.tagsLayout.count())):
            widget = self.tagsLayout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Добавляем новые теги
        for tag in self.task_data["tags"]:
            tag_label = QLabel(tag["text"])
            color_map = {
                "Дизайн": "#E3F2FD",
                "Срочно": "#FFF3E0",
                "ERP": "#E8F5E9",
                "Баг": "#FFEBEE",
                "Разработка": "#F3E5F5",
                "Тестирование": "#FFF3E0"
            }
            text_color_map = {
                "Дизайн": "#1565C0",
                "Срочно": "#EF6C00",
                "ERP": "#2E7D32",
                "Баг": "#D22730",
                "Разработка": "#7B1FA2",
                "Тестирование": "#EF6C00"
            }
            bg_color = color_map.get(tag["type"], "#F0F0F0")
            text_color = text_color_map.get(tag["type"], "#666")

            tag_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 11px;
                    padding: 3px 8px;
                    border-radius: 12px;
                    font-weight: bold;
                    background-color: {bg_color};
                    color: {text_color};
                    border: 1px solid {bg_color};
                }}
            """)
            tag_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self.tagsLayout.addWidget(tag_label)

        # Добавляем растягивающийся спейсер
        self.tagsLayout.addStretch()

    def update_deadline_style(self):
        """Обновление стиля дедлайна"""
        deadline_text = self.task_data.get("deadline", "")

        # Определяем цвет дедлайна
        if "Просрочено" in deadline_text:
            deadline_color = "#D22730"
            deadline_bg = "#FFEBEE"
        elif self.task_data.get("priority") == "high":
            deadline_color = "#FF9800"
            deadline_bg = "#FFF3E0"
        elif "✅" in deadline_text:
            deadline_color = "#4CAF50"
            deadline_bg = "#E8F5E9"
        else:
            deadline_color = "#666"
            deadline_bg = "#F5F5F5"

        self.deadlineLabel.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;
                color: {deadline_color};
                padding: 2px 6px;
                background-color: {deadline_bg};
                border-radius: 4px;
                font-weight: bold;
            }}
        """)

    def setup_action_buttons(self):
        """Настройка кнопок действий"""
        # Кнопка подзадач
        if self.task_data.get("has_subtasks", False):
            self.subtaskButton.setText(f"+ Подзадача ({self.task_data.get('subtask_count', 0)})")
            self.subtaskButton.clicked.connect(lambda: self.on_add_subtask())
            self.subtaskButton.show()
        else:
            self.subtaskButton.hide()

        # Кнопка комментариев
        comment_count = self.task_data.get('comment_count', 0)
        self.commentButton.setText(f"💬 {comment_count}")
        self.commentButton.clicked.connect(lambda: self.on_show_comments())

        # Кнопка вложений
        attachment_count = self.task_data.get('attachment_count', 0)
        self.attachmentButton.setText(f"📎 {attachment_count}")
        self.attachmentButton.clicked.connect(lambda: self.on_show_attachments())

    def update_card_style(self):
        """Обновление стиля карточки"""
        priority_color = {
            "high": "#D22730",
            "medium": "#FFA726",
            "low": "#4CAF50"
        }.get(self.task_data.get("priority", "medium"), "#FFA726")

        if self.task_data.get("completed"):
            self.setStyleSheet(f"""
                QFrame#taskCard {{
                    background-color: #F8F9FA;
                    border-radius: 10px;
                    border: 1px dashed #C8E6C9;
                    padding: 15px;
                    border-left: 4px solid #4CAF50;
                    opacity: 0.9;
                    min-height: 180px;
                    max-height: 220px;
                }}
                QFrame#taskCard:hover {{
                    border: 2px solid #4CAF50;
                    box-shadow: 0 4px 12px rgba(76, 175, 80, 0.2);
                    cursor: move;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#taskCard {{
                    background-color: #FFFFFF;
                    border-radius: 10px;
                    border: 1px solid #E0E0E0;
                    padding: 15px;
                    border-left: 4px solid {priority_color};
                    min-height: 180px;
                    max-height: 220px;
                }}
                QFrame#taskCard:hover {{
                    border: 2px solid #ccab6e;
                    box-shadow: 0 4px 12px rgba(204, 171, 110, 0.2);
                    cursor: move;
                }}
            """)

    def on_checkbox_changed(self, state):
        """Обработка изменения чекбокса"""
        if state == Qt.CheckState.Checked.value:
            self.task_data["completed"] = True
            self.setStyleSheet(f"""
                QFrame#taskCard {{
                    background-color: #F8F9FA;
                    border-radius: 10px;
                    border: 1px dashed #C8E6C9;
                    padding: 15px;
                    border-left: 4px solid #4CAF50;
                    opacity: 0.9;
                    min-height: 180px;
                    max-height: 220px;
                }}
                QFrame#taskCard:hover {{
                    border: 2px solid #4CAF50;
                    box-shadow: 0 4px 12px rgba(76, 175, 80, 0.2);
                    cursor: move;
                }}
            """)

    def show_context_menu(self):
        """Показать контекстное меню"""
        menu = QMenu(self)

        edit_action = menu.addAction("✏️ Редактировать")
        delete_action = menu.addAction("🗑️ Удалить")
        move_action = menu.addAction("📤 Переместить в...")
        duplicate_action = menu.addAction("📋 Дублировать")

        action = menu.exec(self.menuButton.mapToGlobal(QPoint(0, self.menuButton.height())))

        if action == edit_action:
            self.on_edit_task()
        elif action == delete_action:
            self.on_delete_task()
        elif action == move_action:
            self.on_move_task()
        elif action == duplicate_action:
            self.on_duplicate_task()

    def on_add_subtask(self):
        """Добавить подзадачу"""
        print(f"Добавить подзадачу для: {self.task_data['title']}")

    def on_show_comments(self):
        """Показать комментарии"""
        print(f"Показать комментарии для: {self.task_data['title']}")

    def on_show_attachments(self):
        """Показать вложения"""
        print(f"Показать вложения для: {self.task_data['title']}")

    def on_edit_task(self):
        """Редактировать задачу"""
        print(f"Редактировать: {self.task_data['title']}")

    def on_delete_task(self):
        """Удалить задачу"""
        print(f"Удалить: {self.task_data['title']}")

    def on_move_task(self):
        """Переместить задачу"""
        print(f"Переместить: {self.task_data['title']}")

    def on_duplicate_task(self):
        """Дублировать задачу"""
        print(f"Дублировать: {self.task_data['title']}")

    def mousePressEvent(self, event):
        """Начало перетаскивания"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Обработка перемещения мыши для drag&drop"""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime_data = QMimeData()

        # Сохраняем данные задачи
        task_json = json.dumps(self.task_data)
        mime_data.setText(task_json)
        drag.setMimeData(mime_data)

        # Создаем изображение для перетаскивания
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setOpacity(0.7)
        self.render(painter)
        painter.end()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())

        drag.exec(Qt.DropAction.MoveAction)
        self.hide()


class MyTasksPage(QWidget):
    """Страница Мои задачи"""

    # Остальной код MyTasksPage остается без изменений
    def __init__(self, parent=None):
        super().__init__(parent)
        # Устанавливаем стиль для всего виджета
        self.setStyleSheet("""
            QWidget {
                background-color: #F5F5F7;
                font-family: 'Segoe UI', Arial;
            }
        """)

        loadUi("my_tasks_page.ui", self)
        self.setup_tasks()
        self.connect_signals()
        self.update_statistics()

        # Настройка адаптивного отображения
        self.setup_responsive_layout()

    def setup_responsive_layout(self):
        """Настройка адаптивного расположения колонок"""
        # Устанавливаем гибкую политику размера для контейнера канбана
        self.kanbanContainer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Настройка скролла с отступами
        self.setup_scroll_areas()

        # Настройка динамического изменения размера колонок
        self.columnTodo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.columnInProgress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.columnReview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.columnDone.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Устанавливаем стили для колонок
        column_style = """
            QFrame {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E0E0E0;
                min-width: 280px;
                margin: 5px;
            }
            QFrame:hover {
                border: 2px solid #E8E8E8;
            }
        """

        self.columnTodo.setStyleSheet(column_style)
        self.columnInProgress.setStyleSheet(column_style)
        self.columnReview.setStyleSheet(column_style)
        self.columnDone.setStyleSheet(column_style)

    def setup_scroll_areas(self):
        """Настройка скролл-областей с отступами"""
        scroll_areas = [
            (self.todoScrollArea, self.todoTasksContainer),
            (self.inProgressScrollArea, self.inProgressTasksContainer),
            (self.reviewScrollArea, self.reviewTasksContainer),
            (self.doneScrollArea, self.doneTasksContainer)
        ]

        for scroll_area, container in scroll_areas:
            # Устанавливаем отступы для скролла от надписей
            scroll_bar = scroll_area.verticalScrollBar()
            scroll_bar.setStyleSheet("""
                QScrollBar:vertical {
                    background: #F5F5F7;
                    width: 12px;
                    margin: 15px 3px 15px 3px;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical {
                    background: #C1C1C1;
                    min-height: 20px;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #A8A8A8;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)

            # Устанавливаем отступы для контейнера задач
            container.layout().setContentsMargins(10, 15, 10, 15)
            container.layout().setSpacing(10)

    def connect_signals(self):
        """Подключение сигналов"""
        self.btnAddTask.clicked.connect(self.create_new_task)
        self.btnShowArchived.clicked.connect(self.show_archive)
        self.btnArchiveDone.clicked.connect(self.archive_completed_tasks)
        self.searchTasksInput.textChanged.connect(self.search_tasks)
        self.priorityFilter.currentTextChanged.connect(self.filter_tasks)
        self.projectFilter.currentTextChanged.connect(self.filter_tasks)

        # Подключаем кнопки добавления задач в колонки
        self.btnAddToTodo.clicked.connect(lambda: self.add_task_to_column("todo"))
        self.btnAddToInProgress.clicked.connect(lambda: self.add_task_to_column("in_progress"))
        self.btnAddToReview.clicked.connect(lambda: self.add_task_to_column("review"))

    def setup_tasks(self):
        """Настройка начальных задач"""
        # Тестовые данные задач
        self.sample_tasks = [
            {
                "id": 1,
                "title": "Разработать макет интерфейса",
                "description": "Создать 3D-модель новой кабины водителя с учетом эргономики",
                "project": "Разработка новой кабины",
                "priority": "high",
                "deadline": "До 10.12.2024",
                "status": "todo",
                "tags": [
                    {"text": "Дизайн", "type": "Дизайн"},
                    {"text": "Срочно", "type": "Срочно"}
                ],
                "assignee_initials": "ИИ",
                "comment_count": 2,
                "attachment_count": 1,
                "has_subtasks": True,
                "subtask_count": 3,
                "completed": False
            },
            {
                "id": 2,
                "title": "Написание ТЗ для модуля А",
                "description": "Подготовить техническое задание для модуля бухгалтерии",
                "project": "Внедрение ERP-системы",
                "priority": "medium",
                "deadline": "До 20.12.2024",
                "status": "in_progress",
                "tags": [
                    {"text": "ERP", "type": "ERP"}
                ],
                "assignee_initials": "ПА",
                "comment_count": 0,
                "attachment_count": 0,
                "completed": False
            },
            {
                "id": 3,
                "title": "Исправить баг в отчете",
                "description": "Исправить расчет себестоимости в еженедельном отчете",
                "project": "Разработка сайта",
                "priority": "high",
                "deadline": "Просрочено 2 дня",
                "status": "in_progress",
                "tags": [
                    {"text": "Баг", "type": "Баг"}
                ],
                "assignee_initials": "СК",
                "comment_count": 5,
                "attachment_count": 2,
                "completed": False
            },
            {
                "id": 4,
                "title": "Согласование бюджета",
                "description": "Согласовать бюджет на следующий квартал с финансовым отделом",
                "project": "Модернизация конвейера",
                "priority": "low",
                "deadline": "✅ 05.12.2024",
                "status": "done",
                "assignee_initials": "ЕП",
                "comment_count": 3,
                "attachment_count": 4,
                "completed": True
            },
            {
                "id": 5,
                "title": "Провести тестирование API",
                "description": "Протестировать новые endpoints API для интеграции",
                "project": "Разработка новой кабины",
                "priority": "medium",
                "deadline": "До 15.12.2024",
                "status": "review",
                "tags": [
                    {"text": "Тестирование", "type": "Тестирование"}
                ],
                "assignee_initials": "МК",
                "comment_count": 1,
                "attachment_count": 0,
                "completed": False
            }
        ]

        # Получаем контейнеры для задач
        self.todo_container = self.findChild(QWidget, "todoTasksContainer")
        self.in_progress_container = self.findChild(QWidget, "inProgressTasksContainer")
        self.review_container = self.findChild(QWidget, "reviewTasksContainer")
        self.done_container = self.findChild(QWidget, "doneTasksContainer")

        # Устанавливаем отступы для контейнеров задач
        for container in [self.todo_container, self.in_progress_container,
                          self.review_container, self.done_container]:
            if container and container.layout():
                container.layout().setContentsMargins(10, 15, 10, 15)

        # Распределяем задачи по колонкам
        self.todo_tasks = []
        self.in_progress_tasks = []
        self.review_tasks = []
        self.done_tasks = []

        for task in self.sample_tasks:
            task_card = TaskCard(task)
            if task["status"] == "todo":
                self.todo_tasks.append(task_card)
                self.todo_container.layout().addWidget(task_card)
            elif task["status"] == "in_progress":
                self.in_progress_tasks.append(task_card)
                self.in_progress_container.layout().addWidget(task_card)
            elif task["status"] == "review":
                self.review_tasks.append(task_card)
                self.review_container.layout().addWidget(task_card)
            elif task["status"] == "done":
                self.done_tasks.append(task_card)
                self.done_container.layout().addWidget(task_card)

        # Обновляем заголовки колонок
        self.update_column_titles()

        # Заполняем фильтр проектов
        projects = set(task["project"] for task in self.sample_tasks)
        self.projectFilter.clear()
        self.projectFilter.addItems(["Все проекты"] + sorted(list(projects)))

    def update_column_titles(self):
        """Обновить заголовки колонок с количеством задач"""
        self.columnTitleTodo.setText(f"📝 К выполнению ({len(self.todo_tasks)})")
        self.columnTitleInProgress.setText(f"🔧 В работе ({len(self.in_progress_tasks)})")
        self.columnTitleReview.setText(f"👀 На проверке ({len(self.review_tasks)})")
        self.columnTitleDone.setText(f"✅ Выполнено ({len(self.done_tasks)})")

    def update_statistics(self):
        """Обновление статистики"""
        total_tasks = (len(self.todo_tasks) + len(self.in_progress_tasks) +
                       len(self.review_tasks) + len(self.done_tasks))

        completed_tasks = len(self.done_tasks)

        # Расчет процента выполнения
        progress = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0

        # Обновляем метки
        self.totalTasksLabel.setText(f"📊 Всего задач: {total_tasks}")
        self.completedTasksLabel.setText(f"✅ Выполнено: {completed_tasks}")

        # Подсчет просроченных задач
        overdue_count = 0
        for task in self.sample_tasks:
            if "Просрочено" in task.get("deadline", ""):
                overdue_count += 1

        self.overdueTasksLabel.setText(f"⏰ Просрочено: {overdue_count}")
        self.overallProgress.setValue(progress)

        # Устанавливаем цвет прогресс-бара
        if progress < 30:
            color = "#D22730"
        elif progress < 70:
            color = "#FFA726"
        else:
            color = "#4CAF50"

        self.overallProgress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                text-align: center;
                background-color: #F5F5F5;
                height: 12px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 6px;
            }}
        """)

    def create_new_task(self):
        """Создать новую задачу"""
        print("Создание новой задачи...")

    def show_archive(self):
        """Показать архив задач"""
        print("Показать архив...")

    def archive_completed_tasks(self):
        """Архивировать выполненные задачи"""
        print("Архивирование выполненных задач...")

    def search_tasks(self, text):
        """Поиск задач"""
        print(f"Поиск: {text}")

    def filter_tasks(self):
        """Фильтрация задач"""
        priority_filter = self.priorityFilter.currentText()
        project_filter = self.projectFilter.currentText()
        print(f"Фильтр: приоритет={priority_filter}, проект={project_filter}")

    def add_task_to_column(self, column_id):
        """Добавить задачу в колонку"""
        print(f"Добавить задачу в колонку: {column_id}")

    def resizeEvent(self, event):
        """Обработка изменения размера окна для адаптивности"""
        super().resizeEvent(event)
        self.adjust_columns_layout()

    def adjust_columns_layout(self):
        """Адаптивное изменение расположения колонок"""
        width = self.kanbanContainer.width()

        # Определяем количество колонок в зависимости от ширины
        if width < 1200:
            # Для узких экранов - 2 колонки
            cols = 2
        elif width < 1600:
            # Для средних экранов - 3 колонки
            cols = 3
        else:
            # Для широких экранов - 4 колонки
            cols = 4

        # Рассчитываем оптимальную ширину колонок
        margin = 20  # отступ между колонками
        column_width = (width - (margin * (cols - 1))) // cols

        # Устанавливаем минимальную ширину для колонок
        min_width = 280
        if column_width < min_width:
            column_width = min_width
            # Пересчитываем количество колонок
            cols = max(1, width // (min_width + margin))

        # Устанавливаем фиксированную ширину для колонок
        for column in [self.columnTodo, self.columnInProgress,
                       self.columnReview, self.columnDone]:
            column.setMinimumWidth(column_width)
            column.setMaximumWidth(column_width)