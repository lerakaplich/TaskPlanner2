import os

from PyQt6 import uic
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
                             QPushButton, QMenu, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QAction
from PyQt6.uic import loadUi


class OthersTaskCard(QFrame):
    """Карточка задачи для Создателя (с возможностями редактирования)"""

    editRequested = pyqtSignal(int)
    deleteRequested = pyqtSignal(int)
    archiveRequested = pyqtSignal(int)
    approveRequested = pyqtSignal(int)
    returnToWorkRequested = pyqtSignal(int)

    def __init__(self, task_data, is_creator=False, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self.is_creator = is_creator


        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/analytics/employees/
            "..", "..",  # поднимаемся до корня проекта
            "ui", "other_tasks"  # спускаемся в нужную подпапку ui
        )
        uic.loadUi(os.path.join(ui_path, "task_card.ui"), self)

        self.setObjectName("TaskCard")

        self.setup_ui()
        self.setup_context_menu()


    def setup_ui(self):
        """Настройка UI карточки на основе данных"""
        # Заголовок задачи
        self.taskTitleLabel.setText(self.task_data.get("title", "Без названия"))

        # Проект
        project_name = self.task_data.get("project", "Без проекта")
        self.projectButton.setText(project_name)

        # Приоритет
        priority = self.task_data.get("priority", "medium")
        priority_text = {
            "low": "Низкий",
            "medium": "Средний",
            "high": "Высокий",
            "critical": "Критический"
        }.get(priority, "Средний")

        self.priorityValueLabel.setText(priority_text)

        # Цвет приоритета
        priority_colors = {
            "low": "#4CAF50",  # зеленый
            "medium": "#FFA726",  # оранжевый
            "high": "#D22730",  # красный
            "critical": "#D22730"  # красный
        }

        priority_color = priority_colors.get(priority, "#FFA726")
        self.priorityValueLabel.setStyleSheet(f"""
            QLabel {{
                background-color: {priority_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
                text-align: center;
            }}
        """)

        # Описание задачи
        description = self.task_data.get("description", "")
        if description:
            self.descriptionText.setPlainText(description)
            self.descriptionText.show()
        else:
            self.descriptionText.hide()

        # Исполнитель
        assignee = self.task_data.get("assignee", "")
        if assignee:
            self.executorLabel.setText(f"Исполнитель: {assignee}")
            self.executorLabel.show()
        else:
            self.executorLabel.hide()

        # Дата создания
        created_at = self.task_data.get("created_at", "")
        if created_at:
            self.createdLabel.setText(f"Создана: {created_at}")
        else:
            self.createdLabel.hide()

        # Автор (создатель)
        creator = self.task_data.get("creator", "")
        if creator:
            self.authorLabel.setText(f"Автор: {creator}")

        # Дедлайн
        deadline = self.task_data.get("deadline", "")
        if deadline:
            self.deadlineLabel.setText(f"До: {deadline}")

            # Проверка на просрочку
            from PyQt6.QtCore import QDate
            current_date = QDate.currentDate()
            try:
                deadline_date = QDate.fromString(deadline, "dd.MM.yyyy")
                if deadline_date and deadline_date < current_date and not self.task_data.get("completed", False):
                    self.deadlineLabel.setStyleSheet("""
                        QLabel {
                            font-size: 11px;
                            color: #D22730;
                            font-weight: bold;
                        }
                    """)
            except:
                pass
        else:
            self.deadlineLabel.hide()

        # Дата обновления
        updated_at = self.task_data.get("updated_at", "")
        if updated_at:
            self.updatedLabel.setText(f"Обновление: {updated_at}")
        else:
            self.updatedLabel.hide()

        # Теги
        self.setup_tags()

    def setup_tags(self):
        """Настройка тегов"""
        # Очищаем существующие теги
        for i in reversed(range(self.tagsLayout.count())):
            widget = self.tagsLayout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Добавляем новые теги
        tags = self.task_data.get("tags", [])
        for tag in tags:
            if isinstance(tag, dict):
                tag_text = tag.get("text", tag.get("name", ""))
            else:
                tag_text = str(tag)

            if tag_text:
                tag_button = QPushButton(tag_text)
                tag_button.setStyleSheet("""
                    QPushButton {
                        font-size: 11px;
                        padding: 3px 8px;
                        border-radius: 12px;
                        font-weight: bold;
                        background-color: #E8F5E9;
                        color: #2E7D32;
                        border: 1px solid #C8E6C9;
                        
                        
                    }
                    QPushButton:hover {
                        background-color: #C8E6C9;
                    }
                """)
                tag_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                tag_button.setCursor(Qt.CursorShape.PointingHandCursor)
                self.tagsLayout.addWidget(tag_button)

        # Добавляем растягивающийся спейсер
        self.tagsLayout.addStretch()

    def setup_context_menu(self):
        """Настройка контекстного меню"""
        self.context_menu = QMenu(self)

        # Разные действия в зависимости от статуса задачи
        status = self.task_data.get("status", "todo")

        # Общие действия
        edit_action = QAction("✏️ Редактировать", self)
        edit_action.triggered.connect(lambda: self.editRequested.emit(self.task_data["id"]))
        self.context_menu.addAction(edit_action)

        delete_action = QAction("🗑️ Удалить", self)
        delete_action.triggered.connect(lambda: self.deleteRequested.emit(self.task_data["id"]))
        self.context_menu.addAction(delete_action)

        self.context_menu.addSeparator()

        # Действия для задач "На проверке"
        if status == "review":
            approve_action = QAction("✅ Одобрить выполнение", self)
            approve_action.triggered.connect(lambda: self.approveRequested.emit(self.task_data["id"]))
            self.context_menu.addAction(approve_action)

            return_action = QAction("↩️ Вернуть на доработку", self)
            return_action.triggered.connect(lambda: self.returnToWorkRequested.emit(self.task_data["id"]))
            self.context_menu.addAction(return_action)

        # Действия для выполненных задач
        elif status == "done":
            archive_action = QAction("📁 Архивировать", self)
            archive_action.triggered.connect(lambda: self.archiveRequested.emit(self.task_data["id"]))
            self.context_menu.addAction(archive_action)

        # Действия для других статусов
        else:
            mark_done_action = QAction("✓ Отметить выполненной", self)
            mark_done_action.triggered.connect(lambda: self.mark_as_done())
            self.context_menu.addAction(mark_done_action)

    def show_context_menu(self):
        """Показ контекстного меню"""
        if self.is_creator:
            self.context_menu.exec(self.mapToGlobal(self.menuButton.pos()))

    def mark_as_done(self):
        """Отметить задачу как выполненную"""
        self.task_data["status"] = "done"
        self.task_data["completed"] = True

    def update_task_data(self, new_data):
        """Обновление данных задачи"""
        self.task_data.update(new_data)
        self.setup_ui()