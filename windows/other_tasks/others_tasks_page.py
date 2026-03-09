# windows/other_tasks/others_tasks_page.py

import os
from typing import Dict, Optional
from PyQt6 import uic
from PyQt6.QtWidgets import (QWidget, QFrame, QLabel, QScrollArea,
                             QMessageBox, QSizePolicy, QSplitter,
                             QVBoxLayout, QHBoxLayout)  # Добавлены QVBoxLayout и QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent

from database import get_tasks_session
from services.other_tasks_service import OtherTasksService
from windows.other_tasks.others_task_card import OthersTaskCard
from windows.other_tasks.task_dialog import TaskDialog


class OthersTasksPage(QWidget):
    taskUpdated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Загружаем UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "other_tasks")
        uic.loadUi(os.path.join(ui_path, "others_tasks_page.ui"), self)

        self.columns = {}  # id -> widget
        self.column_widgets = []  # список виджетов колонок

        # Инициализация сервиса
        self.db_session = get_tasks_session()
        self.service = OtherTasksService(self.db_session, project_id=2)

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
            column_widget = self.create_column_widget(col)
            self.columns[col["id"]] = column_widget
            self.column_widgets.append(column_widget)
            splitter.addWidget(column_widget)

        # Устанавливаем начальные размеры
        sizes = self.service.get_initial_sizes(len(column_data), self.width() - 50)
        if sizes:
            splitter.setSizes(sizes)

        self.kanbanLayout.addWidget(splitter)

    def create_column_widget(self, column_data: Dict) -> QFrame:
        """Создает виджет колонки."""
        column = QFrame()
        column.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border: 1px solid #E0E0E0;
            }}
        """)

        column.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        column.setMinimumWidth(250)
        column.setMinimumHeight(400)
        column.setProperty("column_name", column_data["name"])
        column.setProperty("column_id", column_data["id"])
        column.setAcceptDrops(True)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Заголовок
        header = QHBoxLayout()

        title_label = QLabel(column_data["name"])
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {column_data['color']};")
        header.addWidget(title_label)

        count_label = QLabel("0")
        count_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: white;
                background-color: #666;
                border-radius: 10px;
                padding: 2px 8px;
                font-weight: bold;
            }
        """)
        header.addWidget(count_label)
        header.addStretch()
        layout.addLayout(header)

        # Область задач
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #F5F5F5;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #C1C1C1;
                border-radius: 4px;
                min-height: 20px;
            }
        """)

        tasks_container = QWidget()
        tasks_container.setStyleSheet("background-color: transparent;")
        tasks_container.setAcceptDrops(True)

        tasks_layout = QVBoxLayout()
        tasks_layout.setSpacing(8)
        tasks_layout.setContentsMargins(2, 2, 2, 2)
        tasks_layout.addStretch()
        tasks_container.setLayout(tasks_layout)

        scroll_area.setWidget(tasks_container)
        layout.addWidget(scroll_area)
        column.setLayout(layout)

        # Сохраняем ссылки
        column.tasks_layout = tasks_layout
        column.count_label = count_label
        column.column_name = column_data["name"]
        column.column_id = column_data["id"]

        return column

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
        card = OthersTaskCard(task_data, service=self.service, is_creator=True)

        # Подключаем сигналы
        card.editRequested.connect(self.edit_task)
        card.deleteRequested.connect(self.delete_task)
        card.archiveRequested.connect(self.archive_task)
        card.approveRequested.connect(self.approve_task)
        card.returnToWorkRequested.connect(self.return_to_work)
        card.moveToDoneColumn.connect(self.move_to_done)

        column_id = task_data.get("column_id")
        if column_id in self.columns:
            column = self.columns[column_id]
            column.tasks_layout.insertWidget(
                column.tasks_layout.count() - 1,
                card
            )

    def move_task_card(self, task_id: int, from_column: str, to_column: str):
        """Перемещает карточку между колонками."""
        # Ищем карточку
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

        # Ищем целевую колонку
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

    # windows/other_tasks/others_tasks_page.py

    def create_new_task(self):
        """Создает новую задачу."""
        print("\n=== ОТЛАДКА: Создание новой задачи ===")

        dialog = TaskDialog(self, mode="create")
        dialog.set_service(self.service)

        # Подключаемся к сигналу для отладки
        dialog.task_saved.connect(self.on_task_saved)

        result = dialog.exec()
        print(f"Результат диалога: {result}")

        if result:
            print("✅ Диалог завершен успешно, задача будет создана")
        else:
            print("❌ Диалог отменен или закрыт")

    def on_task_saved(self, form_data):
        """Обработчик сигнала сохранения задачи."""
        print("\n=== ОТЛАДКА: Получен сигнал task_saved ===")
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

    def edit_task(self, task_id: int):
        """Редактирует задачу."""
        task = self.service.get_task_by_id(task_id)
        if not task:
            return

        dialog = TaskDialog(self, task_data=task, mode="edit")
        dialog.set_service(self.service)

        if dialog.exec():
            form_data = dialog.get_task_data()
            updated_task = self.service.update_task(task_id, form_data)
            if updated_task:
                self.update_task_card(updated_task)
                self.update_statistics()
                self.taskUpdated.emit()

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
    # Действия с задачами
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
        """Архивирует задачу."""
        print(f"Архивирование задачи {task_id}")

    def approve_task(self, task_id: int):
        """Одобряет задачу."""
        print(f"Одобрение задачи {task_id}")

    def return_to_work(self, task_id: int):
        """Возвращает на доработку."""
        print(f"Возврат на доработку задачи {task_id}")

    # =====================================================
    # Статистика и фильтрация
    # =====================================================

    def update_statistics(self):
        """Обновляет статистику."""
        stats = self.service.get_statistics_for_display()

        # Обновляем счетчики колонок
        for column in self.column_widgets:
            count = stats["column_counts"].get(column.column_name, 0)
            column.count_label.setText(str(count))

        # Обновляем общую статистику
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

        # Собираем все задачи
        all_tasks = []
        for column in self.column_widgets:
            layout = column.tasks_layout
            for i in range(layout.count()):
                w = layout.itemAt(i).widget()
                if w and hasattr(w, 'task_data'):
                    all_tasks.append(w.task_data)

        # Фильтруем
        filtered = self.service.filter_tasks_by_priority(all_tasks, priority)

        # Перестраиваем отображение
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
        """Определяет целевую колонку."""
        for column in self.column_widgets:
            if column.geometry().contains(pos):
                return column
        return None

    # =====================================================
    # Вспомогательные методы
    # =====================================================

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

    def resizeEvent(self, event):
        """Обработка изменения размера."""
        super().resizeEvent(event)
        # Здесь можно сохранять пропорции колонок

    def closeEvent(self, event):
        """Закрытие страницы."""
        self.db_session.close()
        super().closeEvent(event)