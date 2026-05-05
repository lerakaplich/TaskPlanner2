import json
import os

from PyQt6 import uic
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QPoint
from PyQt6.QtGui import QDrag, QPixmap, QPainter
from PyQt6.QtWidgets import QFrame, QPushButton, QMenu, QApplication, QSizePolicy


class TaskCard(QFrame):
    """UI карточки задачи"""

    edit_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal(dict)
    archive_requested = pyqtSignal(dict)
    duplicate_requested = pyqtSignal(dict)

    def __init__(self, task_data, parent=None):
        super().__init__(parent)

        self.task_data = task_data
        self.drag_start_position = None

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "my_tasks"
        )

        uic.loadUi(os.path.join(ui_path, "task_card.ui"), self)

        self.setObjectName("TaskCard")
        self.setAcceptDrops(True)

        # 👇 КЛЮЧЕВОЕ: Minimum по вертикали, Preferred по горизонтали
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.setMaximumWidth(330)
        self.setMinimumWidth(300)
        self.setMinimumHeight(0)

        # Отключаем растяжение
        self.setContentsMargins(0, 0, 0, 0)

        self.fill_ui()

        self.menuButton.clicked.connect(self.show_context_menu)

    def set_difficulty_display(self, difficulty):
        """Устанавливает отображение сложности (цифра со звездой)"""
        if not hasattr(self, 'difficultyValueLabel'):
            return

        try:
            value = float(difficulty) if difficulty else 0
        except (ValueError, TypeError):
            value = 0

        value = max(0, min(5, value))

        if value == int(value):
            display_value = int(value)
        else:
            display_value = value

        self.difficultyValueLabel.setText(f"{display_value}⭐")

        if value >= 4:
            color = "#D22730"
            bg_color = "#FFEBEE"
        elif value >= 3:
            color = "#FF9800"
            bg_color = "#FFF3E0"
        elif value >= 1:
            color = "#4CAF50"
            bg_color = "#E8F5E9"
        else:
            color = "#9E9E9E"
            bg_color = "#F5F5F5"

        self.difficultyValueLabel.setStyleSheet(f"""
            font-size: 12px;
            font-weight: bold;
            color: {color};
            background-color: {bg_color};
            border-radius: 10px;
            padding: 2px 8px;
        """)

        difficulty_widget = self.difficultyLayout.parentWidget()
        if difficulty_widget:
            difficulty_widget.setVisible(value > 0)

    def fill_ui(self):
        """Заполнение карточки готовыми данными"""

        # Название задачи
        title = self.task_data.get("title", "")
        self.taskTitleLabel.setText(title if title else "Без названия")

        # Проект
        project_name = self.task_data.get("project_name", "")
        if project_name:
            self.projectButton.setText(f"📁 {project_name}")
            self.projectButton.show()
            self.projectLabel.show()
        else:
            self.projectButton.hide()
            self.projectLabel.hide()

        # Приоритет
        priority_text = self.task_data.get("priority_text", "")
        priority_color = self.task_data.get("priority_color", "#FFA726")

        if priority_text:
            self.priorityValueLabel.setText(priority_text)
            self.priorityValueLabel.setStyleSheet(
                f"background-color:{priority_color};"
                "color:white;border-radius:6px;padding:6px 12px;font-weight:bold;"
            )
            self.priorityValueLabel.show()
            self.priorityLabel.show()
        else:
            self.priorityValueLabel.hide()
            self.priorityLabel.hide()

        # Описание
        description = self.task_data.get("description", "")
        if description and description.strip():
            self.descriptionText.setPlainText(description)
            self.descriptionText.show()
            doc_height = self.descriptionText.document().size().height()
            self.descriptionText.setFixedHeight(min(int(doc_height) + 10, 80))
        else:
            self.descriptionText.hide()
            self.descriptionText.setFixedHeight(0)

        # Дата создания
        created_text = self.task_data.get("created_text", "")
        if created_text:
            self.createdLabel.setText(f"📅 Создана: {created_text}")
            self.createdLabel.show()
        else:
            self.createdLabel.hide()

        # Дата обновления
        updated_text = self.task_data.get("updated_text", "")
        created_text_simple = self.task_data.get("created_text", "")
        if updated_text and updated_text != created_text_simple:
            self.updatedLabel.setText(f"🔄 Обновление: {updated_text}")
            self.updatedLabel.show()
        else:
            self.updatedLabel.hide()

        # Автор
        author = self.task_data.get("author_text", "")
        if author:
            self.authorLabel.setText(f"👤 Автор: {author}")
            self.authorLabel.show()
        else:
            self.authorLabel.hide()

        # Исполнитель
        executor = self.task_data.get("executor_text", "")
        if executor:
            self.executorLabel.setText(f"👥 Исполнитель: {executor}")
            self.executorLabel.show()
        else:
            self.executorLabel.hide()

        # Дедлайн
        deadline_text = self.task_data.get("deadline_text", "")
        if deadline_text:
            self.deadlineLabel.setText(f"⏰ {deadline_text}")
            deadline_color = self.task_data.get('deadline_color', '#666')
            self.deadlineLabel.setStyleSheet(
                f"font-size: 11px; color: {deadline_color}; font-weight: bold;"
            )
            self.deadlineLabel.show()
        else:
            self.deadlineLabel.hide()

        # Сложность
        difficulty = self.task_data.get("difficulty", 0)
        self.set_difficulty_display(difficulty)

        # Теги
        self.setup_tags()

        # Обновляем размер
        self.adjustSize()
        self.updateGeometry()

    def setup_tags(self):
        """Настройка отображения тегов"""
        for i in reversed(range(self.tagsLayout.count())):
            w = self.tagsLayout.itemAt(i).widget()
            if w:
                w.deleteLater()

        tags = self.task_data.get("tags", [])

        tags_widget = self.tagsLayout.parentWidget()
        if tags:
            for tag in tags:
                # Преобразуем tag в строку, если это не строка
                tag_str = tag.name if hasattr(tag, 'name') else str(tag)
                tag_button = QPushButton(tag_str)
                tag_button.setStyleSheet("""
                    QPushButton{
                        font-size: 10px;
                        padding: 2px 8px;
                        border-radius: 10px;
                        background: #E8F5E9;
                        color: #2E7D32;
                        border: 1px solid #C8E6C9;
                    }
                """)
                tag_button.setCursor(Qt.CursorShape.PointingHandCursor)
                tag_button.setFixedHeight(22)
                self.tagsLayout.addWidget(tag_button)

            if tags_widget:
                tags_widget.show()
        else:
            if tags_widget:
                tags_widget.hide()

        self.tagsLayout.addStretch()

    def update_task_data(self, new_data):
        """Обновляет данные карточки"""
        self.task_data.update(new_data)
        self.fill_ui()

    def show_context_menu(self):
        """Показать контекстное меню"""
        menu = QMenu(self)

        edit_action = menu.addAction("Редактировать")
        duplicate_action = menu.addAction("Дублировать")
        menu.addSeparator()
        delete_action = menu.addAction("Удалить")
        archive_action = menu.addAction("Архивировать")

        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 6px 0;
                font-size: 14px;
            }
            QMenu::item {
                padding: 10px 30px 10px 15px;
                color: #1B232A;
            }
            QMenu::item:selected {
                background-color: #ccab6e;
                color: white;
                border-radius: 6px;
                margin: 2px 6px;
            }
        """)

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
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        if not self.drag_start_position:
            return

        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime = QMimeData()

        task_json = json.dumps(self.task_data, ensure_ascii=False, default=str)
        mime.setData("application/x-task", task_json.encode("utf-8"))

        drag.setMimeData(mime)

        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setOpacity(0.7)
        self.render(painter)
        painter.end()

        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())

        drag.exec(Qt.DropAction.MoveAction)