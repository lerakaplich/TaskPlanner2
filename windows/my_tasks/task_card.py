import json
import os

from PyQt6 import uic
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QPoint
from PyQt6.QtGui import QDrag, QPixmap, QPainter
from PyQt6.QtWidgets import QFrame, QPushButton, QMenu, QApplication


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

        self.fill_ui()

        self.menuButton.clicked.connect(self.show_context_menu)

    # ---------------------------------------------------
    # UI
    # ---------------------------------------------------

    def fill_ui(self):
        """Заполнение карточки готовыми данными"""

        self.taskTitleLabel.setText(self.task_data.get("title", ""))

        self.projectButton.setText(self.task_data.get("project_name", ""))

        priority_text = self.task_data.get("priority_text", "Средний")
        priority_color = self.task_data.get("priority_color", "#FFA726")

        self.priorityValueLabel.setText(priority_text)
        self.priorityValueLabel.setStyleSheet(
            f"background-color:{priority_color};"
            "color:white;border-radius:6px;padding:6px 12px;font-weight:bold;"
        )

        description = self.task_data.get("description", "")

        if description:
            self.descriptionText.setPlainText(description)
            self.descriptionText.show()
        else:
            self.descriptionText.hide()

        self.createdLabel.setText(self.task_data.get("created_text", ""))
        self.updatedLabel.setText(self.task_data.get("updated_text", ""))

        author = self.task_data.get("author_text")

        if author:
            self.authorLabel.setText(f"Автор: {author}")

        executor = self.task_data.get("executor_text")

        if executor:
            self.executorLabel.setText(f"Исполнитель: {executor}")
            self.executorLabel.show()
        else:
            self.executorLabel.hide()

        deadline_text = self.task_data.get("deadline_text")

        if deadline_text:
            self.deadlineLabel.setText(deadline_text)
            self.deadlineLabel.setStyleSheet(
                f"color:{self.task_data.get('deadline_color','#666')};font-weight:bold;"
            )
            self.deadlineLabel.show()
        else:
            self.deadlineLabel.hide()

        self.setup_tags()

    # ---------------------------------------------------
    # TAGS
    # ---------------------------------------------------

    def setup_tags(self):

        for i in reversed(range(self.tagsLayout.count())):
            w = self.tagsLayout.itemAt(i).widget()
            if w:
                w.deleteLater()

        tags = self.task_data.get("tags", [])

        for tag in tags:

            tag_button = QPushButton(tag)

            tag_button.setStyleSheet("""
                QPushButton{
                    font-size:11px;
                    padding:3px 8px;
                    border-radius:12px;
                    background:#E8F5E9;
                    color:#2E7D32;
                    border:1px solid #C8E6C9;
                    font-weight:bold;
                }
            """)

            self.tagsLayout.addWidget(tag_button)

        self.tagsLayout.addStretch()

    # ---------------------------------------------------
    # CONTEXT MENU
    # ---------------------------------------------------

    def show_context_menu(self):

        menu = QMenu(self)

        edit_action = menu.addAction("Редактировать")
        delete_action = menu.addAction("Удалить")
        archive_action = menu.addAction("Архивировать")
        duplicate_action = menu.addAction("Дублировать")

        action = menu.exec(
            self.menuButton.mapToGlobal(QPoint(0, self.menuButton.height()))
        )

        if action == edit_action:
            self.edit_requested.emit(self.task_data)

        elif action == delete_action:
            self.delete_requested.emit(self.task_data)

        elif action == archive_action:
            self.archive_requested.emit(self.task_data)

        elif action == duplicate_action:
            self.duplicate_requested.emit(self.task_data)

    # ---------------------------------------------------
    # DRAG & DROP
    # ---------------------------------------------------

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

        task_json = json.dumps(self.task_data, ensure_ascii=False)

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