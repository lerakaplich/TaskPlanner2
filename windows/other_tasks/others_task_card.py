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
    duplicateRequested = pyqtSignal(int)
    pauseRequested = pyqtSignal(int)
    resumeRequested = pyqtSignal(int)

    def __init__(self, task_data, service: Optional[TasksService] = None,
                 is_creator=False, parent=None):
        super().__init__(task_data, parent)

        self.is_creator = is_creator
        self.service = service
        self.drag_start_position = None

        self._disconnect_parent_signals()
        self._reconnect_project_signal()
        self.setup_creator_context_menu()
        self.setup_creator_ui()
        self.projectButton.setCursor(Qt.CursorShape.PointingHandCursor)

    def _reconnect_project_signal(self):
        """Повторно подключает сигнал клика по проекту после отключения родительских сигналов"""
        try:
            self.project_clicked.disconnect()
        except TypeError:
            pass

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
        try:
            self.pause_requested.disconnect()
        except TypeError:
            pass
        try:
            self.resume_requested.disconnect()
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
                    border: none;
                }
            """)

    def _on_progress_click(self, event):
        """Запрещаем изменение прогресса в чужих задачах"""
        self.setToolTip("Вы не можете изменять прогресс чужих задач")
        event.accept()

    def setup_creator_context_menu(self):
        """Настройка контекстного меню."""
        try:
            self.menuButton.clicked.disconnect()
        except TypeError:
            pass
        self.menuButton.clicked.connect(self.show_full_context_menu)

    def show_full_context_menu(self):
        """Показывает полное контекстное меню (для всех пользователей)"""
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
        is_paused = self.task_data.get("is_paused", False)
        is_completed = self.task_data.get("completed", False)

        # ===== РЕДАКТИРОВАНИЕ (только для создателя) =====
        if self.is_creator:
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

        # ===== ДУБЛИРОВАНИЕ (доступно всем) =====
        duplicate_action = QAction("Дублировать", self)
        duplicate_action.triggered.connect(
            lambda: self.duplicateRequested.emit(self.task_data["id"])
        )
        menu.addAction(duplicate_action)

        # ===== ПАУЗА/ВОЗОБНОВЛЕНИЕ (для активных задач) =====
        if not is_completed:
            if is_paused:
                pause_action = QAction("Возобновить", self)
                pause_action.triggered.connect(
                    lambda: self.resumeRequested.emit(self.task_data["id"])
                )
            else:
                pause_action = QAction("Пауза", self)
                pause_action.triggered.connect(
                    lambda: self.pauseRequested.emit(self.task_data["id"])
                )
            menu.addAction(pause_action)

        # ===== ОТМЕТИТЬ ВЫПОЛНЕННОЙ (если не в Done колонке) =====
        if status != "Готово" and not is_completed:
            done_action = QAction("Отметить выполненной", self)
            done_action.triggered.connect(self.mark_as_done)
            menu.addAction(done_action)

        # ===== АРХИВИРОВАНИЕ =====
        archive_action = QAction("Архивировать", self)
        archive_action.triggered.connect(
            lambda: self.archiveRequested.emit(self.task_data["id"])
        )
        menu.addAction(archive_action)

        menu.exec(self.menuButton.mapToGlobal(self.menuButton.rect().bottomLeft()))

    def mark_as_done(self):
        """Отмечает задачу как выполненную (перемещает в колонку Готово)"""
        print(f"✅ Отметка задачи {self.task_data['id']} как выполненной")
        self.moveToDoneColumn.emit(self.task_data["id"])

    def update_task_data(self, new_data):
        """Обновляет данные задачи."""
        self.task_data.update(new_data)
        self.fill_ui()
        self.setup_creator_ui()

    def mousePressEvent(self, event):
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

        # Сигнал о начале перетаскивания
        self.drag_started.emit(self.task_data)

        drag = QDrag(self)
        mime_data = QMimeData()

        task_json = json.dumps(self.task_data, ensure_ascii=False, default=str)
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
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        event.acceptProposedAction()