# windows/my_tasks/my_tasks_page.py

import os
from typing import Dict, List

from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent
from PyQt6.QtWidgets import QWidget, QScrollArea, QHBoxLayout, QMessageBox

from services.tasks_service.tasks_service import TasksService
from windows.my_tasks.task_card import TaskCard
from windows.widgets.kanban_column import KanbanColumn


class MyTasksPage(QWidget):
    """Страница Мои задачи - ТОЛЬКО UI"""

    task_moved = pyqtSignal()
    open_project_requested = pyqtSignal(int)

    def __init__(self, db_session, current_user, parent=None, column_service=None, permission_service=None):
        super().__init__(parent)

        self._is_loading = False
        self._is_refreshing = False
        self._loaded = False
        self._first_show = True
        self._current_project_id = None
        self.permission_service = permission_service

        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "my_tasks")
        uic.loadUi(os.path.join(ui_path, "my_tasks_page.ui"), self)

        self.service = TasksService(
            db_session=db_session,
            current_user=current_user,
            mode="my",
            column_service=column_service
        )

        self.columns = {}
        self.column_widgets = []
        self.current_user = current_user

        # Инициализация обработчиков
        from windows.my_tasks.my_tasks_handlers import MyTasksHandlers
        self._handlers = MyTasksHandlers(self)

        self.setup_board()
        self.setAcceptDrops(True)

        self.priorityFilter.currentTextChanged.connect(self._on_filter_changed)
        self.projectFilter.currentTextChanged.connect(self._on_project_filter_changed)

        self._load_projects_for_filter()

    # ==========================================================
    # ПРАВА ДОСТУПА (делегирует обработчику)
    # ==========================================================

    def _can_delete_task(self) -> bool:
        return self._handlers.can_delete_task()

    def _can_archive_task(self) -> bool:
        return self._handlers.can_archive_task()

    # ==========================================================
    # ПОДКЛЮЧЕНИЕ СИГНАЛОВ КАРТОЧКИ
    # ==========================================================

    def _connect_task_card_signals(self, card):
        """Подключает сигналы карточки"""
        card.edit_requested.connect(self._handlers.on_edit_task)

        if self._can_delete_task():
            card.delete_requested.connect(self._handlers.on_delete_task)
        else:
            card.set_delete_button_visible(False)

        if self._can_archive_task():
            card.archive_requested.connect(self._handlers.on_archive_task)
        else:
            card.set_archive_button_visible(False)

        card.duplicate_requested.connect(self._handlers.on_duplicate_task)
        card.pause_requested.connect(self._handlers.on_pause_task)
        card.resume_requested.connect(self._handlers.on_resume_task)
        card.drag_started.connect(self._on_drag_started)
        card.progress_changed.connect(self._handlers.on_progress_changed)
        card.project_clicked.connect(self._handlers.on_project_clicked)

    # ==========================================================
    # ЗАГРУЗКА ПРОЕКТОВ ДЛЯ ФИЛЬТРА
    # ==========================================================

    def _load_projects_for_filter(self):
        """Загружает проекты для выпадающего списка"""
        user_id = self.current_user.get("id") if self.current_user else None
        if not user_id:
            return

        projects = self.service.crud.get_projects_for_filter(user_id)

        self.projectFilter.blockSignals(True)
        self.projectFilter.clear()
        self.projectFilter.addItem("Все проекты", None)
        for project in projects:
            self.projectFilter.addItem(project["name"], project["id"])
        self.projectFilter.blockSignals(False)

    # ==========================================================
    # ФИЛЬТРЫ
    # ==========================================================

    def _on_project_filter_changed(self):
        project_id = self.projectFilter.currentData()
        self._current_project_id = project_id
        self._rebuild_board_for_project(project_id)
        self._load_tasks_for_current_project()

    def _on_filter_changed(self):
        self.filter_tasks()

    def filter_tasks(self):
        """Фильтрация задач по приоритету и проекту"""
        priority = self.priorityFilter.currentText()
        project_id = self.projectFilter.currentData()

        all_tasks = []
        for column in self.column_widgets:
            for card in column.get_tasks():
                all_tasks.append(card.task_data)

        filtered_ids = self.service.filter.get_filtered_task_ids(all_tasks, priority, project_id)

        for column in self.column_widgets:
            for card in column.get_tasks():
                card.setVisible(card.task_id in filtered_ids)

    # ==========================================================
    # ЗАГРУЗКА ЗАДАЧ
    # ==========================================================

    def _load_tasks_for_current_project(self):
        if self._is_loading:
            return

        self._is_loading = True

        try:
            self.clear_all_columns()
            all_tasks = self.service.get_tasks_for_board()
            filtered_tasks = self.service.crud.get_tasks_for_project_filter(all_tasks, self._current_project_id)

            self.setUpdatesEnabled(False)
            for column in self.column_widgets:
                column.setUpdatesEnabled(False)

            for task in filtered_tasks:
                column_name = task.get("status")
                if column_name and column_name in self.columns:
                    task_card = TaskCard(task)
                    self._connect_task_card_signals(task_card)
                    self.columns[column_name].add_task(task_card)

            for column in self.column_widgets:
                column.setUpdatesEnabled(True)
            self.setUpdatesEnabled(True)

            self.update_statistics()
            self.updateGeometry()

        except Exception as e:
            print(f"❌ Ошибка загрузки задач: {e}")
            self.setUpdatesEnabled(True)
            for column in self.column_widgets:
                column.setUpdatesEnabled(True)
        finally:
            self._is_loading = False

    def load_tasks(self):
        if self._is_loading or self._loaded:
            return

        self._is_loading = True

        try:
            self.clear_all_columns()
            tasks = self.service.get_tasks_for_board()

            self.setUpdatesEnabled(False)
            for column in self.column_widgets:
                column.setUpdatesEnabled(False)

            for task in tasks:
                column_name = task.get("status")
                if not column_name or column_name not in self.columns:
                    continue

                task_card = TaskCard(task)
                self._connect_task_card_signals(task_card)
                self.columns[column_name].add_task(task_card)

            for column in self.column_widgets:
                column.setUpdatesEnabled(True)
            self.setUpdatesEnabled(True)

            self.update_statistics()
            self._loaded = True

        except Exception as e:
            print(f"❌ Ошибка при загрузке задач: {e}")
            self.setUpdatesEnabled(True)
            for column in self.column_widgets:
                column.setUpdatesEnabled(True)
        finally:
            self._is_loading = False

    # ==========================================================
    # ПОСТРОЕНИЕ ДОСКИ
    # ==========================================================

    def setup_board(self):
        self._rebuild_columns_ui(self.service.get_columns_for_board())

    def _rebuild_board_for_project(self, project_id: int = None):
        if hasattr(self.service.crud, '_column_cache'):
            self.service.crud._column_cache = None

        if project_id:
            column_data = self.service.crud.get_project_columns(project_id)
        else:
            column_data = self.service.get_columns_for_board()

        self._rebuild_columns_ui(column_data)

    def _rebuild_columns_ui(self, column_data: List[Dict]):
        self.clear_layout(self.kanbanLayout)

        if not column_data:
            return

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:horizontal { background: #f0f0f0; height: 10px; border-radius: 5px; }
            QScrollBar::handle:horizontal { background: #c0c0c0; border-radius: 5px; }
        """)

        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setSpacing(16)
        columns_layout.setContentsMargins(10, 10, 10, 10)
        columns_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.columns.clear()
        self.column_widgets.clear()

        for col in sorted(column_data, key=lambda x: x["position"]):
            column_widget = KanbanColumn(col)
            self.columns[col["name"]] = column_widget
            self.column_widgets.append(column_widget)
            columns_layout.addWidget(column_widget)
            column_widget.task_dropped.connect(self._handlers.on_task_dropped)

        scroll_area.setWidget(columns_container)

        vertical_scroll = QScrollArea()
        vertical_scroll.setWidgetResizable(True)
        vertical_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        vertical_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        vertical_scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { background: #f0f0f0; width: 10px; border-radius: 5px; }
            QScrollBar::handle:vertical { background: #c0c0c0; border-radius: 5px; }
        """)

        vertical_scroll.setWidget(scroll_area)
        self.kanbanLayout.addWidget(vertical_scroll)

    # ==========================================================
    # СТАТИСТИКА
    # ==========================================================

    def update_statistics(self):
        all_tasks = []
        for column in self.column_widgets:
            for card in column.get_tasks():
                all_tasks.append(card.task_data)

        stats = self.service.crud.get_task_statistics(all_tasks)

        if hasattr(self, 'totalTasksLabel'):
            self.totalTasksLabel.setText(f"📊 Всего задач: {stats['total']}")

        if hasattr(self, 'inProgressLabel'):
            self.inProgressLabel.setText(f"🔧 В работе: {stats['in_progress']}")

        if hasattr(self, 'overdueTasksLabel'):
            self.overdueTasksLabel.setText(f"⏰ Просрочено: {stats['overdue']}")

        if hasattr(self, 'overallProgress'):
            self.overallProgress.setValue(stats['avg_progress'])
            self.overallProgress.setFormat(f"Общий прогресс: {stats['avg_progress']}%")

        for column in self.column_widgets:
            tasks_count = self.service.crud.get_column_tasks_count(column.column_name, all_tasks)
            column.update_count(tasks_count)

    # ==========================================================
    # ОБНОВЛЕНИЕ КАРТОЧЕК
    # ==========================================================

    def update_task_card(self, updated_task: Dict):
        task_id = updated_task.get("id")
        new_status = updated_task.get("status")

        found = False
        for column in self.column_widgets:
            for card in column.get_tasks()[:]:
                if getattr(card, 'task_id', None) == task_id:
                    found = True
                    old_status = card.task_data.get("status")

                    if old_status != new_status:
                        column.remove_task(card)
                        new_column = self.columns.get(new_status)
                        if new_column:
                            card.update_task_data(updated_task)
                            new_column.add_task(card)
                    else:
                        card.update_task_data(updated_task)
                    break
            if found:
                break

        if not found:
            self.load_tasks()

        self.updateGeometry()

    def _update_progress_in_ui(self, task_id: int, progress_percent: int):
        for column in self.column_widgets:
            for card in column.get_tasks():
                if getattr(card, 'task_id', None) == task_id:
                    card.task_data["progress_percent"] = progress_percent
                    card.overallProgress.blockSignals(True)
                    card.overallProgress.setValue(progress_percent)
                    card.overallProgress.setFormat(f"Общий прогресс: {progress_percent}%")
                    card.overallProgress.blockSignals(False)
                    return

    def _update_task_card_data(self, task_id: int, updated_task: Dict):
        for column in self.column_widgets:
            for card in column.get_tasks():
                if getattr(card, 'task_id', None) == task_id:
                    for key, value in updated_task.items():
                        card.task_data[key] = value
                    card._update_pause_indicator()
                    return

    def _remove_task_card_from_ui(self, task_id: int):
        for column in self.column_widgets:
            for card in column.get_tasks()[:]:
                if getattr(card, 'task_id', None) == task_id:
                    column.remove_task(card)
                    card.deleteLater()
                    return
        self.load_tasks()

    def _find_column_by_id(self, column_id: int) -> Optional[KanbanColumn]:
        for col in self.column_widgets:
            if col.column_id == column_id:
                return col
        return None

    # ==========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ==========================================================

    def clear_all_columns(self):
        for column in self.column_widgets:
            column.clear_tasks()

    def clear_layout(self, layout):
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    def _on_drag_started(self, task_data: dict):
        pass

    def refresh_columns(self):
        if self._is_refreshing:
            return

        self._is_refreshing = True

        try:
            if hasattr(self.service.crud, '_column_cache'):
                self.service.crud._column_cache = None

            all_tasks = []
            for column in self.column_widgets:
                for card in column.get_tasks():
                    all_tasks.append(card.task_data)

            self.setup_board()

            for task in all_tasks:
                task_card = TaskCard(task)
                self._connect_task_card_signals(task_card)
                column_name = task.get("status")
                if column_name in self.columns:
                    self.columns[column_name].add_task(task_card)

            self.update_statistics()
            self.updateGeometry()

        except Exception as e:
            print(f"❌ Ошибка при обновлении колонок: {e}")
        finally:
            self._is_refreshing = False

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            QTimer.singleShot(10, self.load_tasks)

    # ==========================================================
    # DRAG & DROP
    # ==========================================================

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        mime_data = event.mimeData()
        if not mime_data.hasFormat("application/x-task"):
            event.ignore()
            return

        data = self.service.deserialize_task_from_drag(mime_data.data("application/x-task"))
        if not data:
            event.ignore()
            return

        task_id = data.get("id")
        if not task_id:
            event.ignore()
            return

        global_pos = self.mapToGlobal(event.position().toPoint())

        target_column = None
        for column in self.column_widgets:
            column_pos = column.mapFromGlobal(global_pos)
            if column.rect().contains(column_pos):
                target_column = column
                break

        if not target_column:
            event.ignore()
            return

        new_status = target_column.column_name
        old_status = data.get("status")

        if old_status == new_status:
            event.ignore()
            return

        result = self.service.move_task(task_id, new_status)
        if result:
            old_column_name, updated_task = result
            self.update_task_card(updated_task)
            self.update_statistics()
            self.task_moved.emit()
            event.acceptProposedAction()
        else:
            event.ignore()