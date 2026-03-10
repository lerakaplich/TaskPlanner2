# windows/other_tasks/others_tasks_page.py

import os
from typing import Dict, Optional, List
from PyQt6.QtWidgets import (QWidget, QFrame, QLabel, QScrollArea,
                             QMessageBox, QSizePolicy, QSplitter,
                             QVBoxLayout, QHBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent

from database import get_tasks_session
from services.tasks_service import TasksService  # 👈 ИЗМЕНЕНО: TasksService вместо OtherTasksService
from windows.other_tasks.others_task_card import OthersTaskCard
from windows.other_tasks.task_dialog import TaskDialog
from PyQt6 import uic

from windows.shared.kanban_column import KanbanColumn


class OthersTasksPage(QWidget):
    taskUpdated = pyqtSignal()

    def __init__(self, parent=None, current_user=None, project_id=2):
        super().__init__(parent)

        self.current_user = current_user or {"id": 1, "last_name": "Копейкина", "first_name": "Виктория", "middle_name": "Анатольевна"}
        self.project_id = project_id

        # Загружаем UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "other_tasks")
        uic.loadUi(os.path.join(ui_path, "others_tasks_page.ui"), self)

        self.columns = {}  # id -> widget
        self.column_widgets = []  # список виджетов колонок

        # Инициализация сервиса
        self.db_session = get_tasks_session()
        self.service = TasksService(
            self.db_session,
            project_id=self.project_id,
            current_user=self.current_user,
            mode="others"
        )

        # Настройка UI
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.setup_kanban()
        self.load_tasks()
        self.connect_signals()

    def connect_signals(self):
        """Подключает сигналы UI."""
        self.priorityFilter.currentTextChanged.connect(self.filter_tasks)
        self.projectFilter.currentTextChanged.connect(self.filter_tasks)
        self.btnCreateTask.clicked.connect(self.create_new_task)

    # =====================================================
    # Настройка UI
    # =====================================================

    # Заменить метод setup_kanban:
    def setup_kanban(self):
        """Создает колонки канбан-доски."""
        self.clear_layout(self.kanbanLayout)

        column_data = self.service.get_column_data()
        if not column_data:
            print("⚠️ Нет колонок для отображения")
            return

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(5)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #E0E0E0;
                border-radius: 2px;
            }
            QSplitter::handle:hover {
                background-color: #ccab6e;
            }
        """)

        self.columns.clear()
        self.column_widgets.clear()

        for col in sorted(column_data, key=lambda x: x["position"]):
            column_widget = KanbanColumn(col)  # 👈 Используем общий класс
            self.columns[col["id"]] = column_widget
            self.column_widgets.append(column_widget)
            splitter.addWidget(column_widget)

        # Устанавливаем начальные размеры
        sizes = self.service.get_initial_sizes(len(column_data), self.width() - 50)
        if sizes:
            splitter.setSizes(sizes)

        self.kanbanLayout.addWidget(splitter)

    def clear_layout(self, layout):
        """Очищает layout."""
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    # =====================================================
    # Работа с задачами
    # =====================================================

    def load_tasks(self):
        """Загружает задачи из сервиса."""
        tasks = self.service.load_tasks()
        self.clear_all_columns()

        for task in tasks:
            self.add_task_card(task)

        self.update_statistics()

    def add_task_card(self, task_data: Dict):
        """Добавляет карточку задачи в колонку."""
        card = self.create_task_card(task_data)
        self.connect_task_card_signals(card)

        column_id = task_data.get("column_id")
        if column_id in self.columns:
            column = self.columns[column_id]
            column.tasks_layout.insertWidget(
                column.tasks_layout.count() - 1,
                card
            )

    def create_task_card(self, task_data: Dict) -> QWidget:
        """Создает карточку задачи (может быть переопределено в наследниках)."""
        return OthersTaskCard(task_data, service=self.service, is_creator=True)

    def connect_task_card_signals(self, card):
        """Подключает сигналы карточки (может быть переопределено)."""
        card.editRequested.connect(self.edit_task)
        card.deleteRequested.connect(self.delete_task)
        card.archiveRequested.connect(self.archive_task)
        card.approveRequested.connect(self.approve_task)
        card.returnToWorkRequested.connect(self.return_to_work)
        card.moveToDoneColumn.connect(self.move_to_done)

    def move_task_card(self, task_id: int, from_column: str, to_column: str):
        """Перемещает карточку между колонками."""
        card = None
        source_column = None

        for col in self.column_widgets:
            layout = col.tasks_layout
            for i in range(layout.count()):
                w = layout.itemAt(i).widget()
                if w and hasattr(w, 'task_data') and w.task_data["id"] == task_id:
                    card = w
                    source_column = col
                    layout.takeAt(i)
                    break
            if card:
                break

        target_column = None
        for col in self.column_widgets:
            if col.column_name == to_column:
                target_column = col
                break

        if card and target_column:
            target_column.tasks_layout.insertWidget(
                target_column.tasks_layout.count() - 1,
                card
            )

    def clear_all_columns(self):
        """Очищает все колонки от карточек."""
        for column in self.column_widgets:
            layout = column.tasks_layout
            while layout.count() > 1:
                item = layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()

    # =====================================================
    # CRUD операции
    # =====================================================

    def create_new_task(self):
        """Создает новую задачу."""
        print("\n=== ОТЛАДКА: Создание новой задачи ===")

        dialog = TaskDialog(self, mode="create", current_user=self.current_user)
        dialog.set_service(self.service)
        dialog.task_saved.connect(self.on_task_saved)  # 👈 Подключаем сигнал

        dialog.exec()

    def edit_task(self, task_id: int):
        """Редактирует задачу."""
        task = self.service.get_task_by_id(task_id)
        if not task:
            return

        dialog = TaskDialog(self, task_data=task, mode="edit", current_user=self.current_user)
        dialog.set_service(self.service)
        dialog.task_saved.connect(self.on_task_updated)  # 👈 Подключаем сигнал для обновления

        dialog.exec()

    def on_task_saved(self, task_id, form_data):
        """Обработчик создания задачи."""
        print("\n=== ОТЛАДКА: Создание задачи ===")
        print(f"Данные из диалога: {form_data}")

        try:
            new_task = self.service.create_task(form_data)
            print(f"✅ Задача создана: {new_task}")

            self.add_task_card(new_task)
            self.update_statistics()
            self.taskUpdated.emit()
            print("✅ Задача добавлена в UI")

        except Exception as e:
            print(f"❌ ОШИБКА при создании задачи: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать задачу: {str(e)}")

    def on_task_updated(self, task_id, form_data):
        """Обработчик обновления задачи."""
        print("\n=== ОТЛАДКА: Обновление задачи ===")
        print(f"ID задачи: {task_id}")
        print(f"Данные из диалога: {form_data}")

        try:
            updated_task = self.service.update_task(task_id, form_data)
            if updated_task:
                print(f"✅ Задача обновлена: {updated_task}")

                self.update_task_card(updated_task)
                self.update_statistics()
                self.taskUpdated.emit()
                print("✅ Задача обновлена в UI")
            else:
                print("❌ Задача не найдена")

        except Exception as e:
            print(f"❌ ОШИБКА при обновлении задачи: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить задачу: {str(e)}")

    def delete_task(self, task_id: int):
        """Удаляет задачу."""
        reply = QMessageBox.question(
            self, "Удаление",
            "Вы уверены, что хотите удалить задачу?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.service.delete_task(task_id)
            self.remove_task_card(task_id)
            self.update_statistics()
            self.taskUpdated.emit()

    def update_task_card(self, updated_task: Dict):
        """Обновляет карточку задачи."""
        for column in self.column_widgets:
            layout = column.tasks_layout
            for i in range(layout.count()):
                w = layout.itemAt(i).widget()
                if w and hasattr(w, 'task_data') and w.task_data["id"] == updated_task["id"]:
                    if w.task_data["status"] != updated_task["status"]:
                        self.move_task_card(
                            updated_task["id"],
                            w.task_data["status"],
                            updated_task["status"]
                        )
                    w.update_task_data(updated_task)
                    return

    def remove_task_card(self, task_id: int):
        """Удаляет карточку из UI."""
        for column in self.column_widgets:
            layout = column.tasks_layout
            for i in range(layout.count()):
                w = layout.itemAt(i).widget()
                if w and hasattr(w, 'task_data') and w.task_data["id"] == task_id:
                    w.deleteLater()
                    return

    # =====================================================
    # Действия с задачами (заглушки)
    # =====================================================

    def move_to_done(self, task_id: int):
        """Перемещает в 'Выполнено'."""
        result = self.service.move_task(task_id, "Выполнен")
        if result:
            old_column, task = result
            self.move_task_card(task_id, old_column, "Выполнен")
            self.update_statistics()
            self.taskUpdated.emit()

    def archive_task(self, task_id: int):
        print(f"Архивирование задачи {task_id}")

    def approve_task(self, task_id: int):
        print(f"Одобрение задачи {task_id}")

    def return_to_work(self, task_id: int):
        print(f"Возврат на доработку задачи {task_id}")

    # =====================================================
    # Статистика и фильтрация
    # =====================================================

    def update_statistics(self):
        """Обновляет статистику."""
        stats = self.service.get_statistics_for_display()

        for column in self.column_widgets:
            count = stats["column_counts"].get(column.column_name, 0)
            column.count_label.setText(str(count))

        if hasattr(self, 'totalTasksLabel'):
            self.totalTasksLabel.setText(f"📊 Всего задач: {stats['total']}")

        if hasattr(self, 'inProgressLabel'):
            self.inProgressLabel.setText(f"🔧 В работе: {stats['in_progress']}")

        if hasattr(self, 'overdueTasksLabel'):
            self.overdueTasksLabel.setText(f"⏰ Просрочено: {stats['overdue']}")

        if hasattr(self, 'overallProgress'):
            self.overallProgress.setValue(self.service.get_progress_percent())

    def filter_tasks(self):
        """Фильтрует задачи."""
        priority = self.priorityFilter.currentText()

        all_tasks = []
        for column in self.column_widgets:
            layout = column.tasks_layout
            for i in range(layout.count()):
                w = layout.itemAt(i).widget()
                if w and hasattr(w, 'task_data'):
                    all_tasks.append(w.task_data)

        filtered = self.service.filter_tasks_by_priority(all_tasks, priority)

        self.clear_all_columns()
        for task in filtered:
            self.add_task_card(task)

    # =====================================================
    # Drag & Drop
    # =====================================================

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        data = self.service.deserialize_task_from_drag(
            event.mimeData().data("application/x-task")
        )
        if not data:
            return

        target = self.get_target_column(event.position().toPoint())
        if not target:
            return

        result = self.service.move_task(data["id"], target.column_name)
        if result:
            old_column, task = result
            self.move_task_card(data["id"], old_column, task["status"])
            self.update_statistics()
            self.taskUpdated.emit()

    def get_target_column(self, pos: QPoint):
        for column in self.column_widgets:
            if column.geometry().contains(pos):
                return column
        return None

    # =====================================================
    # Завершение работы
    # =====================================================

    def closeEvent(self, event):
        self.db_session.close()
        super().closeEvent(event)