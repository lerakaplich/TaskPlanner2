# windows/other_tasks/others_tasks_page.py

import os
from typing import Dict, List

from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent
from PyQt6.QtWidgets import QWidget, QScrollArea, QHBoxLayout, QSizePolicy, QMessageBox

from database import get_tasks_session
from services.tasks_service.tasks_service import TasksService
from windows.other_tasks.others_task_card import OthersTaskCard
from windows.widgets.kanban_column import KanbanColumn


class OthersTasksPage(QWidget):
    """Страница Чужие задачи - ТОЛЬКО UI"""

    taskUpdated = pyqtSignal()
    open_project_requested = pyqtSignal(int)

    def __init__(self, parent=None, current_user=None, project_id=None, column_service=None, permission_service=None):
        super().__init__(parent)

        self._is_loading = False
        self._is_refreshing = False
        self._first_show = True
        self._current_project_id = None
        self.permission_service = permission_service

        self.current_user = current_user

        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "other_tasks")
        uic.loadUi(os.path.join(ui_path, "others_tasks_page.ui"), self)

        self.columns = {}
        self.column_widgets = []
        self._all_projects = []

        self.db_session = get_tasks_session()
        self.service = TasksService(
            db_session=self.db_session,
            current_user=self.current_user,
            mode="others",
            column_service=column_service
        )

        from windows.other_tasks.others_tasks_handlers import OthersTasksHandlers
        self._handlers = OthersTasksHandlers(self)

        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.setup_kanban()
        self._load_projects_for_filter()
        self._setup_permission_ui()
        self._connect_signals()

    def _can_edit_or_delete_task(self, task_creator_id: int = None) -> bool:
        """Проверяет, может ли пользователь редактировать/удалять задачу"""
        if not self.permission_service:
            print("⚠️ _can_edit_or_delete_task: permission_service отсутствует -> True")
            return True

        # ✅ СНАЧАЛА ПРОВЕРЯЕМ РОЛЬ ПРИЛОЖЕНИЯ
        app_role = self.permission_service.app_manager.role
        print(f"🔍 _can_edit_or_delete_task: app_role = {app_role}, task_creator_id = {task_creator_id}")

        if app_role.value in ('super_admin', 'superadmin', 'admin'):
            print(f"   ✅ Суперадмин/админ -> True")
            return True

        # Затем проверяем права в проекте
        if self._current_project_id:
            result = self.permission_service.can_edit_task(
                self._current_project_id,
                task_creator_id
            )
            print(f"   🔍 can_edit_task({self._current_project_id}) = {result}")
            return result

        print(f"   ❌ Нет прав -> False")
        return False

    # windows/other_tasks/others_tasks_page.py

    # Добавьте эти методы в класс OthersTasksPage:

    def dragEnterEvent(self, event):
        """Обработка входа drag в страницу"""
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Обработка движения drag над страницей"""
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()
        else:
            event.ignore()

    # windows/other_tasks/others_tasks_page.py

    def dropEvent(self, event):
        """Обработка drop на страницу"""
        print(f"🐛🐛🐛 OthersTasksPage.dropEvent ВЫЗВАН! 🐛🐛🐛")
        mime_data = event.mimeData()
        if not mime_data.hasFormat("application/x-task"):
            print(f"   ⛔ Нет формата application/x-task")
            event.ignore()
            return

        try:
            # Десериализуем данные задачи
            task_json = mime_data.data("application/x-task").data().decode("utf-8")
            import json
            task_data = json.loads(task_json)
            task_id = task_data.get("id")
            print(f"   📦 Получена задача: id={task_id}, status={task_data.get('status')}")

            if not task_id:
                event.ignore()
                return

            # Определяем, на какую колонку упала задача
            global_pos = self.mapToGlobal(event.position().toPoint())

            target_column = None
            for column in self.column_widgets:
                column_pos = column.mapFromGlobal(global_pos)
                if column.rect().contains(column_pos):
                    target_column = column
                    print(f"   🎯 Найдена колонка: {column.column_name}")
                    break

            if not target_column:
                print(f"   ⛔ Колонка не найдена")
                event.ignore()
                return

            # Получаем текущий статус задачи
            task = self.service.get_task_by_id(task_id)
            if not task:
                print(f"   ⛔ Задача {task_id} не найдена в БД")
                event.ignore()
                return

            old_status = task.get("status")
            new_status = target_column.column_name

            if old_status == new_status:
                print(f"   ⏭️ Статус не изменился: {old_status} -> {new_status}")
                event.ignore()
                return

            print(f"   🔄 Перемещение задачи {task_id} из '{old_status}' в '{new_status}'")

            # Перемещаем задачу
            result = self.service.move_task_to_column(task_id, target_column.column_id)

            if result:
                print(f"   ✅ Задача перемещена успешно")
                # Обновляем UI
                self.update_task_card(result)
                self.update_statistics()
                self.taskUpdated.emit()
                event.acceptProposedAction()
            else:
                print(f"   ❌ Ошибка при перемещении")
                event.ignore()

        except Exception as e:
            print(f"❌ Ошибка при drop: {e}")
            import traceback
            traceback.print_exc()
            event.ignore()

    def _can_create_task(self) -> bool:
        return self._handlers.can_create_task()

    def _can_archive_task(self, task_creator_id: int = None) -> bool:
        """Проверяет, может ли пользователь архивировать задачу"""
        if not self.permission_service:
            return True

        # ✅ СНАЧАЛА ПРОВЕРЯЕМ РОЛЬ ПРИЛОЖЕНИЯ
        app_role = self.permission_service.app_manager.role
        if app_role.value in ('super_admin', 'superadmin', 'admin'):
            return True

        # Затем проверяем права в проекте
        if self._current_project_id:
            return self.permission_service.can_edit_task(
                self._current_project_id,
                task_creator_id
            )
        return False

    def _setup_permission_ui(self):
        if hasattr(self, 'btnCreateTask'):
            self.btnCreateTask.setVisible(self._can_create_task())

    # ==========================================================
    # ПОДКЛЮЧЕНИЕ СИГНАЛОВ
    # ==========================================================

    def _connect_signals(self):
        self.priorityFilter.currentTextChanged.connect(self._on_filter_changed)
        self.projectFilter.currentTextChanged.connect(self._on_project_filter_changed)

        if hasattr(self, 'btnCreateTask'):
            self.btnCreateTask.clicked.connect(self._handlers.on_create_task)

    def _on_filter_changed(self):
        self.filter_tasks()

    def _on_project_filter_changed(self):
        project_id = self.projectFilter.currentData()
        self._current_project_id = project_id
        self._rebuild_board_for_project(project_id)
        self._handlers.load_tasks_for_current_project()

    # ==========================================================
    # СОЗДАНИЕ КАРТОЧЕК
    # ==========================================================

    def create_task_card(self, task_data: Dict) -> OthersTaskCard:
        """Создает карточку задачи с учетом прав"""
        task_creator_id = task_data.get('created_by')

        can_edit = self._can_edit_or_delete_task(task_creator_id)
        can_archive = self._can_archive_task(task_creator_id)
        can_drag = can_edit  # <-- ДОБАВЛЯЕМ: перетаскивать можно только если есть права на редактирование

        print(f"🐛 create_task_card: task_id={task_data.get('id')}, can_edit={can_edit}, can_drag={can_drag}")

        card = OthersTaskCard(
            task_data,
            service=self.service,
            is_creator=(task_creator_id == self.current_user.get('id')),
            can_edit_delete=can_edit,
            can_archive=can_archive,
            can_drag=can_drag  # <-- ПЕРЕДАЕМ
        )
        return card

    def connect_task_card_signals(self, card):
        card.editRequested.connect(self._handlers.on_edit_task)
        card.deleteRequested.connect(self._handlers.on_delete_task)
        card.archiveRequested.connect(self._handlers.on_archive_task)
        card.duplicateRequested.connect(self._handlers.on_duplicate_task)
        card.pauseRequested.connect(self._handlers.on_pause_task)
        card.resumeRequested.connect(self._handlers.on_resume_task)
        card.moveToDoneColumn.connect(self._handlers.on_move_to_done)
        card.project_clicked.connect(self._handlers.on_project_clicked)
        card.drag_started.connect(self._on_drag_started)

    # ==========================================================
    # ЗАГРУЗКА ПРОЕКТОВ ДЛЯ ФИЛЬТРА
    # ==========================================================

    def _load_projects_for_filter(self):
        user_id = self.current_user.get("id") if self.current_user else None
        if not user_id:
            return

        projects = self.service.crud.get_projects_for_filter_others(user_id)

        self.projectFilter.blockSignals(True)
        self.projectFilter.clear()
        self.projectFilter.addItem("Все проекты", None)
        for project in projects:
            self.projectFilter.addItem(project["name"], project["id"])
        self.projectFilter.blockSignals(False)

    # ==========================================================
    # ПОСТРОЕНИЕ ДОСКИ
    # ==========================================================

    def setup_kanban(self):
        self._rebuild_columns_ui(self.service.get_column_data())

    def _rebuild_board_for_project(self, project_id: int = None):
        if hasattr(self.service.crud, '_column_cache'):
            self.service.crud._column_cache = None

        if project_id:
            column_data = self.service.crud.get_project_columns_by_ids(project_id)
        else:
            column_data = self.service.get_column_data()

        self._rebuild_columns_ui(column_data)

    # windows/other_tasks/others_tasks_page.py

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
        # ВАЖНО: включаем приём drop
        scroll_area.setAcceptDrops(True)
        # Устанавливаем, что виджет принимает drop
        scroll_area.setAttribute(Qt.WidgetAttribute.WA_AcceptDrops, True)

        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setSpacing(16)
        columns_layout.setContentsMargins(10, 10, 10, 10)
        columns_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # ВАЖНО: включаем приём drop
        columns_container.setAcceptDrops(True)
        columns_container.setAttribute(Qt.WidgetAttribute.WA_AcceptDrops, True)

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
        # ВАЖНО: включаем приём drop
        vertical_scroll.setAcceptDrops(True)
        vertical_scroll.setAttribute(Qt.WidgetAttribute.WA_AcceptDrops, True)

        vertical_scroll.setWidget(scroll_area)
        self.kanbanLayout.addWidget(vertical_scroll)

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            QTimer.singleShot(10, self._handlers.load_tasks)
        else:
            QTimer.singleShot(10, self._handlers.full_reload)

    def load_tasks(self):
        self._handlers.load_tasks()

    def full_reload(self):
        self._handlers.full_reload()

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

            self.setup_kanban()
            self._load_projects_for_filter()

            self.clear_all_columns()
            tasks = self.service.load_tasks()

            for task in tasks:
                card = self.create_task_card(task)
                self.connect_task_card_signals(card)
                column_name = task.get("status")
                if column_name in self.columns:
                    column = self.columns[column_name]
                    if card.parent() != column.tasks_container:
                        card.setParent(column.tasks_container)
                    column.add_task(card)

            self.update_statistics()
            self.updateGeometry()

        except Exception as e:
            print(f"❌ Ошибка при обновлении колонок: {e}")
        finally:
            self._is_refreshing = False

    def add_task_card(self, task_data: Dict):
        card = self.create_task_card(task_data)
        self.connect_task_card_signals(card)

        column_name = task_data.get("status")
        if column_name in self.columns:
            column = self.columns[column_name]
            if card.parent() != column.tasks_container:
                card.setParent(column.tasks_container)
            column.add_task(card)
            column.updateGeometry()

    def remove_task_card(self, task_id: int):
        for column in self.column_widgets:
            for card in column.get_tasks():
                if hasattr(card, 'task_data') and card.task_data.get("id") == task_id:
                    column.remove_task(card)
                    return

    def update_task_card(self, updated_task: Dict):
        task_id = updated_task.get("id")
        new_status = updated_task.get("status")

        found_card = None
        found_column = None

        for column in self.column_widgets:
            for card in column.get_tasks():
                if hasattr(card, 'task_data') and card.task_data.get("id") == task_id:
                    found_card = card
                    found_column = column
                    break
            if found_card:
                break

        if not found_card:
            self.load_tasks()
            return

        old_status = found_card.task_data.get("status")

        if old_status != new_status:
            found_column.remove_task(found_card)
            found_card.deleteLater()

            new_column = self.columns.get(new_status)
            if new_column:
                new_card = self.create_task_card(updated_task)
                self.connect_task_card_signals(new_card)
                new_column.add_task(new_card)
            else:
                found_card.update_task_data(updated_task)
                found_column.add_task(found_card)
        else:
            found_card.update_task_data(updated_task)

        self.updateGeometry()
        self.update_statistics()

        for column in self.column_widgets:
            column.update_count(len(column.get_tasks()))
            column.updateGeometry()

    def _update_existing_task_card(self, task_id: int, updated_task: Dict):
        for column in self.column_widgets:
            for card in column.get_tasks():
                if hasattr(card, 'task_data') and card.task_data.get("id") == task_id:
                    card.task_data.update(updated_task)
                    card._update_pause_indicator()
                    return

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

    # ==========================================================
    # СТАТИСТИКА
    # ==========================================================

    def update_statistics(self):
        all_tasks = []
        for column in self.column_widgets:
            for card in column.get_tasks():
                all_tasks.append(card.task_data)

        stats = self.service.crud.get_task_statistics_others(all_tasks)

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
            tasks_count = len(column.get_tasks())
            column.update_count(tasks_count)

    # ==========================================================
    # ФИЛЬТРАЦИЯ
    # ==========================================================

    def filter_tasks(self):
        priority = self.priorityFilter.currentText()
        project_id = self.projectFilter.currentData()

        all_tasks = []
        for column in self.column_widgets:
            for card in column.get_tasks():
                all_tasks.append(card.task_data)

        filtered_ids = self.service.crud.filter_tasks_by_priority_and_project_ids(
            all_tasks, priority, project_id
        )

        for column in self.column_widgets:
            for card in column.get_tasks():
                card.setVisible(card.task_data.get("id") in filtered_ids)

    def _on_drag_started(self, task_data: dict):
        pass

    def closeEvent(self, event):
        self.db_session.close()
        super().closeEvent(event)