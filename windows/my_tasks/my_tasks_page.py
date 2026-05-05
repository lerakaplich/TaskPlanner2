# windows/my_tasks/my_tasks_page.py

import os
from typing import Dict

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QScrollArea, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent

from services.tasks_service.tasks_service import TasksService
from windows.my_tasks.task_card import TaskCard
from windows.widgets.kanban_column import KanbanColumn

class MyTasksPage(QWidget):
    """Страница Мои задачи (только UI слой)"""

    task_moved = pyqtSignal()

    def __init__(self, db_session, current_user, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "my_tasks"
        )
        uic.loadUi(os.path.join(ui_path, "my_tasks_page.ui"), self)

        # Сервис - режим "my" (только мои задачи)
        self.service = TasksService(
            db_session=db_session,
            current_user=current_user,
            mode="my"
        )

        self.columns = {}
        self.column_widgets = []
        self.current_user = current_user

        self.setup_board()
        self.load_tasks()

        # Drag & Drop
        self.setAcceptDrops(True)

        # Фильтры
        self.priorityFilter.currentTextChanged.connect(self._on_filter_changed)

    # ==========================================================
    # Настройка UI
    # ==========================================================

    def setup_board(self):
        """Создает колонки канбан-доски"""
        self.clear_layout(self.kanbanLayout)

        column_data = self.service.get_columns_for_board()
        if not column_data:
            print("⚠️ Нет колонок для отображения")
            return

        # Горизонтальный скролл
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:horizontal {
                background: #f0f0f0;
                height: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: #c0c0c0;
                border-radius: 5px;
            }
        """)

        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setSpacing(16)
        columns_layout.setContentsMargins(10, 10, 10, 10)

        self.columns.clear()
        self.column_widgets.clear()

        for col in sorted(column_data, key=lambda x: x["position"]):
            print(f"📦 Создаем колонку: {col['name']}")
            column_widget = KanbanColumn(col)
            self.columns[col["name"]] = column_widget
            self.column_widgets.append(column_widget)
            columns_layout.addWidget(column_widget)

        columns_layout.addStretch()
        scroll_area.setWidget(columns_container)

        # Вертикальный скролл
        vertical_scroll = QScrollArea()
        vertical_scroll.setWidgetResizable(True)
        vertical_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        vertical_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        vertical_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 5px;
            }
        """)

        vertical_scroll.setWidget(scroll_area)
        self.kanbanLayout.addWidget(vertical_scroll)

        print(f"✅ Создано {len(self.column_widgets)} колонок")

    def clear_layout(self, layout):
        """Очищает layout"""
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    # ==========================================================
    # Загрузка и отображение задач
    # ==========================================================

    def load_tasks(self):
        """Загружает и отображает задачи"""
        tasks = self.service.get_tasks_for_board()

        print(f"\n📊 Загрузка моих задач: {len(tasks)}")
        for task in tasks:
            print(f"  - {task.get('title')} (проект: {task.get('project_name')}, статус: {task.get('status')})")

        self.clear_all_columns()

        for task in tasks:
            task_card = TaskCard(task)
            self._connect_task_card_signals(task_card)

            column_name = task.get("status")
            if column_name in self.columns:
                column = self.columns[column_name]
                column.add_task(task_card)
                print(f"  ✅ Добавлена задача '{task.get('title')}' в колонку '{column_name}'")
            else:
                print(f"  ⚠️ Колонка '{column_name}' не найдена")

        self.update_statistics()

    def clear_all_columns(self):
        """Очищает все колонки от карточек"""
        for column in self.column_widgets:
            column.clear_tasks()

    def _connect_task_card_signals(self, card):
        """Подключает сигналы карточки"""
        card.edit_requested.connect(self._on_edit_task)
        card.delete_requested.connect(self._on_delete_task)
        card.archive_requested.connect(self._on_archive_task)
        card.duplicate_requested.connect(self._on_duplicate_task)
        card.drag_started.connect(self._on_drag_started)

    # ==========================================================
    # Обновление UI
    # ==========================================================

    def update_task_card(self, updated_task: Dict):
        """Обновляет карточку задачи в UI"""
        for column in self.column_widgets:
            for card in column.get_tasks():
                if hasattr(card, 'task_id') and card.task_id == updated_task["id"]:
                    old_status = card.task_data.get("status")
                    new_status = updated_task.get("status")

                    if old_status != new_status:
                        column.remove_task(card)
                        new_column = self.columns.get(new_status)
                        if new_column:
                            new_column.add_task(card)
                            print(f"✅ Задача '{card.task_data.get('title')}' перемещена в колонку '{new_status}'")

                    card.update_task_data(updated_task)
                    return

    def update_statistics(self):
        """Обновляет статистику"""
        stats = self.service.get_statistics_for_display()

        for column in self.column_widgets:
            tasks_in_column = len(column.get_tasks())
            column.update_count(tasks_in_column)

        if hasattr(self, 'totalTasksLabel'):
            self.totalTasksLabel.setText(f"📊 Всего задач: {stats['total']}")

        if hasattr(self, 'completedTasksLabel'):
            self.completedTasksLabel.setText(f"✅ Выполнено: {stats['done']}")

        if hasattr(self, 'overdueTasksLabel'):
            self.overdueTasksLabel.setText(f"⏰ Просрочено: {stats['overdue']}")

        if hasattr(self, 'overallProgress'):
            self.overallProgress.setValue(self.service.get_progress_percent())

    # ==========================================================
    # Обработчики действий (вызывают сервис)
    # ==========================================================

    def _on_edit_task(self, task_id: int):
        """Редактирование задачи"""
        print(f"✏️ Редактирование задачи {task_id}")
        # TODO: открыть диалог редактирования

    def _on_delete_task(self, task_id: int):
        """Удаление задачи"""
        reply = QMessageBox.question(
            self, "Удаление",
            "Вы уверены, что хотите удалить задачу?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.service.delete_task_by_id(task_id):
                self.load_tasks()
                QMessageBox.information(self, "Успех", "Задача удалена")

    def _on_archive_task(self, task_id: int):
        """Архивирование задачи"""
        if self.service.archive_task_by_id(task_id):
            self.load_tasks()
            QMessageBox.information(self, "Успех", "Задача архивирована")

    def _on_duplicate_task(self, task_id: int):
        """Дублирование задачи"""
        new_task = self.service.duplicate_task(task_id)
        if new_task:
            self.load_tasks()
            QMessageBox.information(self, "Успех", "Задача дублирована")

    def _on_drag_started(self, task_data: dict):
        """Начало перетаскивания задачи"""
        print(f"🖱️ Начато перетаскивание задачи {task_data.get('id')}")

    def _on_filter_changed(self):
        """Изменение фильтра"""
        self.filter_tasks()

    def filter_tasks(self):
        """Фильтрация задач по приоритету"""
        priority = self.priorityFilter.currentText()

        all_tasks = []
        for column in self.column_widgets:
            for card in column.get_tasks():
                all_tasks.append(card.task_data)

        filtered = self.service.filter_tasks_by_priority(all_tasks, priority)

        filtered_ids = {t["id"] for t in filtered}
        for column in self.column_widgets:
            for card in column.get_tasks():
                if card.task_id in filtered_ids:
                    card.show()
                else:
                    card.hide()

    # ==========================================================
    # Drag & Drop
    # ==========================================================

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        data = self.service.deserialize_task_from_drag(
            event.mimeData().data("application/x-task")
        )
        if not data:
            event.ignore()
            return

        target_column = self.get_target_column(event.position().toPoint())
        if not target_column:
            event.ignore()
            return

        task_id = data.get("id")
        old_status = data.get("status")
        new_status = target_column.column_name

        if old_status == new_status:
            event.ignore()
            return

        print(f"🔄 Перемещение задачи {task_id}: {old_status} -> {new_status}")

        # Используем метод из TasksMoveService
        result = self.service.move_task(task_id, new_status)
        if result:
            old_column_name, task = result
            self.update_task_card(task)
            self.update_statistics()
            self.task_moved.emit()
            event.acceptProposedAction()
        else:
            event.ignore()

    def get_target_column(self, pos: QPoint):
        """Определяет колонку, на которую произошёл сброс"""
        for column in self.column_widgets:
            if column.geometry().contains(pos):
                return column
        return None