import datetime
import json

from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QPoint
from PyQt6.QtGui import QDrag, QPixmap, QPainter
from PyQt6.QtWidgets import (QFrame, QPushButton, QMenu, QApplication, QSizePolicy)
from PyQt6.uic import loadUi


class TaskCard(QFrame):
    """Карточка задачи с новым дизайном"""

    edit_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal(dict)
    archive_requested = pyqtSignal(dict)
    duplicate_requested = pyqtSignal(dict)

    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self.drag_start_position = None

        # Загружаем UI из файла
        loadUi("task_card.ui", self)
        self.setObjectName("TaskCard")

        self.setup_ui()
        self.setAcceptDrops(True)

        # Настраиваем контекстное меню
        self.menuButton.clicked.connect(self.show_context_menu)

        # Устанавливаем фиксированные размеры
        self.setMinimumHeight(280)
        self.setMaximumHeight(350)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Обновляем стиль карточки
        self.update_card_style()

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

        # Теги
        self.setup_tags()

        # Дата создания
        created_at = self.task_data.get("created_at")
        if created_at:
            if isinstance(created_at, str):
                created_date = created_at.split()[0] if ' ' in created_at else created_at
            else:
                created_date = created_at.strftime("%d.%m.%Y") if hasattr(created_at, 'strftime') else "Неизвестно"
        else:
            created_date = "Неизвестно"

        self.createdLabel.setText(f"Создана: {created_date}")

        # Автор
        author = self.task_data.get("author", {})
        if author:
            last_name = author.get("last_name", "")
            first_name = author.get("first_name", "")
            middle_name = author.get("middle_name", "")

            if first_name and middle_name:
                initials = f"{first_name[0]}.{middle_name[0]}."
            elif first_name:
                initials = f"{first_name[0]}."
            else:
                initials = ""

            author_text = f"{last_name} {initials}" if last_name else "Неизвестен"
        else:
            author_text = "Неизвестен"

        self.authorLabel.setText(f"Автор: {author_text}")

        # Дедлайн
        self.setup_deadline()

        # Дата обновления
        updated_at = self.task_data.get("updated_at")
        if updated_at:
            if isinstance(updated_at, str):
                updated_str = updated_at
            else:
                updated_str = updated_at.strftime("%d.%m.%Y %H:%M") if hasattr(updated_at, 'strftime') else "Неизвестно"
        else:
            updated_str = "Неизвестно"

        self.updatedLabel.setText(f"Обновление: {updated_str}")

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

    def setup_deadline(self):
        """Настройка дедлайна с цветовой индикацией"""
        due_date = self.task_data.get("due_date")
        if not due_date:
            self.deadlineLabel.hide()
            return

        # Показываем метку
        self.deadlineLabel.show()

        # Форматируем дату
        if isinstance(due_date, str):
            deadline_str = due_date
            try:
                deadline_date = datetime.datetime.strptime(due_date, "%Y-%m-%d %H:%M:%S")
            except:
                try:
                    deadline_date = datetime.datetime.strptime(due_date, "%Y-%m-%d")
                except:
                    deadline_date = None
        elif hasattr(due_date, 'strftime'):
            deadline_date = due_date
            deadline_str = due_date.strftime("%d.%m.%Y")
        else:
            deadline_str = str(due_date)
            deadline_date = None

        self.deadlineLabel.setText(f"До: {deadline_str}")

        # Определяем цвет дедлайна
        if deadline_date:
            today = datetime.datetime.now()
            days_diff = (deadline_date - today).days

            if days_diff < 0:
                # Просрочено
                color = "#D22730"  # красный
            elif days_diff == 0:
                # Остался один день
                color = "#FF9800"  # оранжевый
            elif days_diff <= 1:
                # Остался один день
                color = "#FF9800"  # оранжевый
            else:
                # Всё в порядке
                color = "#4CAF50"  # зеленый
        else:
            color = "#666666"  # серый

        self.deadlineLabel.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                color: {color};
                font-weight: bold;
            }}
        """)

    def update_card_style(self):
        """Обновление стиля карточки"""
        # Стиль остается таким же как в UI файле
        pass

    def show_context_menu(self):
        """Показать контекстное меню"""
        menu = QMenu(self)

        edit_action = menu.addAction("✏️ Редактировать")
        delete_action = menu.addAction("🗑️ Удалить")
        archive_action = menu.addAction("📦 Архивировать")
        duplicate_action = menu.addAction("📋 Дублировать")

        # Показываем меню под кнопкой
        action = menu.exec(
            self.menuButton.mapToGlobal(
                QPoint(0, self.menuButton.height())
            )
        )

        if action == edit_action:
            self.edit_requested.emit(self.task_data)
        elif action == delete_action:
            self.delete_requested.emit(self.task_data)
        elif action == archive_action:
            self.archive_requested.emit(self.task_data)
        elif action == duplicate_action:
            self.duplicate_requested.emit(self.task_data)

    def mousePressEvent(self, event):
        """Начало перетаскивания"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Обработка перемещения мыши для drag&drop"""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self.drag_start_position is None:
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime_data = QMimeData()

        # Сохраняем данные задачи
        task_json = json.dumps(self.task_data)
        mime_data.setText(task_json)
        mime_data.setData("application/x-task", task_json.encode())
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