# windows/other_tasks/others_task_card.py

import json
from typing import Optional
from PyQt6.QtWidgets import QMenu, QApplication
from PyQt6.QtCore import pyqtSignal, Qt, QMimeData
from PyQt6.QtGui import QAction, QPixmap, QPainter, QDrag

from windows.my_tasks.task_card import TaskCard
from services.tasks_service.tasks_service import TasksService


class OthersTaskCard(TaskCard):
    """
    UI карточка задачи. Только отображение и сигналы.
    Вся логика в сервисе.
    """

    moveToDoneColumn = pyqtSignal(int)
    editRequested = pyqtSignal(int)
    deleteRequested = pyqtSignal(int)
    archiveRequested = pyqtSignal(int)
    approveRequested = pyqtSignal(int)
    returnToWorkRequested = pyqtSignal(int)

    def __init__(self, task_data, service: Optional[TasksService] = None,
                 is_creator=False, parent=None):
        super().__init__(task_data, parent)

        self.is_creator = is_creator
        self.service = service
        self.drag_start_position = None

        self._disconnect_parent_signals()
        self.setup_creator_context_menu()
        self.setup_creator_ui()

    # =====================================================
    # UI helpers
    # =====================================================

    def _disconnect_parent_signals(self):
        """Отключение сигналов родителя."""
        try:
            self.edit_requested.disconnect()
        except TypeError:
            pass
        try:
            self.delete_requested.disconnect()
        except TypeError:
            pass
        try:
            self.archive_requested.disconnect()
        except TypeError:
            pass
        try:
            self.duplicate_requested.disconnect()
        except TypeError:
            pass

    def setup_creator_ui(self):
        """Обновление UI для создателя."""
        assignee_id = self.task_data.get("assigned_to")

        if self.service:
            assignee_text = self.service.format_assignee_name(assignee_id)
        else:
            assignee_text = self.task_data.get("assignee_name", "")

        if assignee_text:
            self.executorLabel.setText(f"Исполнитель: {assignee_text}")
            self.executorLabel.show()
        else:
            self.executorLabel.hide()

        self.update_deadline_color()

        # Обновляем сложность
        difficulty = self.task_data.get("difficulty", 0)
        self._set_difficulty_display(difficulty)

    def update_deadline_color(self):
        """Обновляет цвет дедлайна."""
        deadline = self.task_data.get("deadline", "")
        completed = self.task_data.get("completed", False)

        if self.service and self.service.is_deadline_overdue(deadline, completed):
            self.deadlineLabel.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    color: #D22730;
                    font-weight: bold;
                }
            """)

    # =====================================================
    # Контекстное меню
    # =====================================================

    def setup_creator_context_menu(self):
        """Настройка контекстного меню."""
        try:
            self.menuButton.clicked.disconnect()
        except TypeError:
            pass
        self.menuButton.clicked.connect(self.show_creator_context_menu)

    def show_creator_context_menu(self):
        """Показывает контекстное меню."""
        if not self.is_creator:
            return

        menu = QMenu(self)
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

        status = self.task_data.get("status")

        edit_action = QAction("Редактировать", self)
        edit_action.triggered.connect(
            lambda: self.editRequested.emit(self.task_data["id"])
        )
        menu.addAction(edit_action)

        delete_action = QAction("Удалить", self)
        delete_action.triggered.connect(
            lambda: self.deleteRequested.emit(self.task_data["id"])
        )
        menu.addAction(delete_action)
        menu.addSeparator()

        if status == "review":
            approve_action = QAction("Одобрить выполнение", self)
            approve_action.triggered.connect(
                lambda: self.approveRequested.emit(self.task_data["id"])
            )
            menu.addAction(approve_action)

            return_action = QAction("Вернуть на доработку", self)
            return_action.triggered.connect(
                lambda: self.returnToWorkRequested.emit(self.task_data["id"])
            )
            menu.addAction(return_action)

        elif status == "done":
            archive_action = QAction("Архивировать", self)
            archive_action.triggered.connect(
                lambda: self.archiveRequested.emit(self.task_data["id"])
            )
            menu.addAction(archive_action)

        else:
            done_action = QAction("✓ Отметить выполненной", self)
            done_action.triggered.connect(self.mark_as_done)
            menu.addAction(done_action)

        menu.exec(self.menuButton.mapToGlobal(self.menuButton.rect().bottomLeft()))

    def mark_as_done(self):
        """Отмечает задачу как выполненную."""
        self.moveToDoneColumn.emit(self.task_data["id"])

    def update_task_data(self, new_data):
        """Обновляет данные задачи."""
        self.task_data.update(new_data)
        self.fill_ui()
        self.setup_creator_ui()

    def mousePressEvent(self, event):
        """Обработка нажатия мыши."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Обработка перемещения мыши для drag."""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        if self.drag_start_position is None:
            return

        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime_data = QMimeData()

        if self.service:
            task_json = self.service.serialize_task_for_drag(self.task_data)
        else:
            task_json = json.dumps(self.task_data, ensure_ascii=False, default=str)

        mime_data.setText(task_json)
        mime_data.setData("application/x-task", task_json.encode("utf-8"))
        drag.setMimeData(mime_data)

        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setOpacity(0.7)
        self.render(painter)
        painter.end()

        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        """Обработка входа drag."""
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Обработка движения drag."""
        event.acceptProposedAction()

    def dropEvent(self, event):
        """Обработка сброса drag."""
        event.acceptProposedAction()