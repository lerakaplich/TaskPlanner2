# windows/other_tasks/others_task_card.py

import json
from typing import Optional
from PyQt6.QtWidgets import QMenu, QApplication, QLabel, QHBoxLayout, QWidget
from PyQt6.QtCore import pyqtSignal, Qt, QMimeData
from PyQt6.QtGui import QAction, QPixmap, QPainter, QDrag

from windows.my_tasks.task_card import TaskCard
from services.tasks_service.tasks_service import TasksService


class OthersTaskCard(TaskCard):
    """
    UI карточка задачи для чужих задач.
    Отображение + прогноз времени + права доступа.
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

    def __init__(
        self,
        task_data,
        service: Optional[TasksService] = None,
        is_creator=False,
        parent=None,
        can_edit_delete=False,
        can_archive=False,
        can_move=False,
        can_drag=False
    ):
        super().__init__(task_data, parent)

        self.is_creator = is_creator
        self.service = service
        self.can_edit_delete = can_edit_delete
        self.can_archive = can_archive
        self.can_move = can_move
        self._can_drag = can_move
        self.drag_start_position = None

        # Флаг для прогноза
        self._prediction_widget = None

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

        # Добавляем прогноз времени
        self._add_prediction_widget()

    def _add_prediction_widget(self):
        """Добавляет виджет с прогнозом времени выполнения"""
        # Удаляем старый виджет если есть
        if self._prediction_widget:
            self._prediction_widget.deleteLater()
            self._prediction_widget = None

        predicted_hours = self.task_data.get("predicted_hours", 0)
        predicted_days = self.task_data.get("predicted_days", 0)
        confidence = self.task_data.get("prediction_confidence", 0)

        if predicted_hours <= 0:
            return

        # Создаём контейнер для прогноза
        self._prediction_widget = QWidget()
        pred_layout = QHBoxLayout(self._prediction_widget)
        pred_layout.setContentsMargins(0, 4, 0, 4)
        pred_layout.setSpacing(8)

        # Иконка прогноза
        icon_label = QLabel("⏱")
        icon_label.setStyleSheet("font-size: 14px; border: none;")
        pred_layout.addWidget(icon_label)

        # Текст прогноза
        pred_text = f"Прогноз: {predicted_hours:.1f} ч"
        if predicted_days > 0:
            pred_text += f" ({predicted_days:.1f} дн)"

        pred_label = QLabel(pred_text)
        pred_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #666;
                border: none;
                font-weight: 500;
            }
        """)
        pred_layout.addWidget(pred_label)

        # Индикатор уверенности
        if confidence > 0:
            confidence_text = self._get_confidence_text(confidence)
            confidence_label = QLabel(confidence_text)
            confidence_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 10px;
                    color: {self._get_confidence_color(confidence)};
                    border: none;
                    background-color: {self._get_confidence_bg(confidence)};
                    border-radius: 8px;
                    padding: 1px 8px;
                }}
            """)
            pred_layout.addWidget(confidence_label)

        pred_layout.addStretch()

        # Вставляем виджет после описания
        self._insert_prediction_widget()

    def _get_confidence_text(self, confidence: float) -> str:
        """Возвращает текстовое описание уверенности"""
        if confidence >= 0.8:
            return "✓ Высокая уверенность"
        elif confidence >= 0.5:
            return "• Средняя уверенность"
        else:
            return "○ Низкая уверенность"

    def _get_confidence_color(self, confidence: float) -> str:
        """Возвращает цвет для уверенности"""
        if confidence >= 0.8:
            return "#2E7D32"
        elif confidence >= 0.5:
            return "#F57C00"
        else:
            return "#D32F2F"

    def _get_confidence_bg(self, confidence: float) -> str:
        """Возвращает цвет фона для уверенности"""
        if confidence >= 0.8:
            return "#E8F5E9"
        elif confidence >= 0.5:
            return "#FFF3E0"
        else:
            return "#FFEBEE"

    def _insert_prediction_widget(self):
        """Вставляет виджет прогноза в layout"""
        if not self._prediction_widget:
            return

        layout = self.layout()
        if not layout:
            return

        # Ищем позицию для вставки (после описания, перед прогрессом)
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget() == self.descriptionText:
                layout.insertWidget(i + 1, self._prediction_widget)
                return

        # Если не нашли описание, вставляем после createdLabel
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and hasattr(item.widget(), 'objectName') and item.widget().objectName() == "createdLabel":
                layout.insertWidget(i + 1, self._prediction_widget)
                return

        # Или в конец
        layout.addWidget(self._prediction_widget)

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
        """Показывает полное контекстное меню (с учётом прав)"""
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

        # ===== РЕДАКТИРОВАНИЕ И УДАЛЕНИЕ (только если есть права) =====
        if self.can_edit_delete:
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

        # ===== АРХИВИРОВАНИЕ (только если есть права) =====
        if self.can_archive:
            archive_action = QAction("Архивировать", self)
            archive_action.triggered.connect(
                lambda: self.archiveRequested.emit(self.task_data["id"])
            )
            menu.addAction(archive_action)

        # ===== ПОКАЗАТЬ ПРОГНОЗ (всегда) =====
        predicted_hours = self.task_data.get("predicted_hours", 0)
        if predicted_hours > 0:
            menu.addSeparator()
            info_action = QAction(
                f"⏱ Прогноз: {predicted_hours:.1f} ч ({self.task_data.get('predicted_days', 0):.1f} дн)",
                self
            )
            info_action.setEnabled(False)
            menu.addAction(info_action)

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

        print(f"🐛 mouseMoveEvent: _can_drag = {self._can_drag}, task_id = {self.task_data.get('id')}")

        if not self._can_drag:
            print(f"   ⛔ Drag запрещён (can_drag=False)")
            return

        print(f"   ✅ Drag разрешён, начинаем перетаскивание")

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

        result = drag.exec(Qt.DropAction.MoveAction)
        print(f"   🏁 Drag завершён с результатом: {result}")