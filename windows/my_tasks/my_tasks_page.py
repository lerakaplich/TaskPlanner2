# windows/my_tasks/my_tasks_page.py

import os
from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QSplitter, QScrollArea, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal

from windows.my_tasks.task_card import TaskCard
from windows.shared.kanban_column import KanbanColumn
from services.tasks_service import TasksService


class MyTasksPage(QWidget):
    """Страница Мои задачи (UI слой)"""

    task_moved = pyqtSignal()

    def __init__(self, db_session, current_user, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "my_tasks"
        )

        uic.loadUi(os.path.join(ui_path, "my_tasks_page.ui"), self)

        # Сервис теперь работает со ВСЕМИ проектами, режим "my"
        self.service = TasksService(
            db_session=db_session,
            current_user=current_user,
            mode="my"
        )

        self.columns = {}  # name -> widget
        self.column_widgets = []

        # Сохраняем текущего пользователя
        self.current_user = current_user

        self.setup_board()
        self.load_tasks()

        # фильтры
        self.priorityFilter.currentTextChanged.connect(self.filter_tasks)
        self.projectFilter.currentTextChanged.connect(self.filter_tasks)

    # windows/my_tasks/my_tasks_page.py

    def setup_board(self):
        """Создает колонки канбан-доски с горизонтальной прокруткой"""
        self.clear_layout(self.kanbanLayout)

        column_data = self.service.get_column_data()
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
            QScrollBar::handle:horizontal:hover {
                background: #a0a0a0;
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

        # Вертикальный скролл для всего контента
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
        """Очищает layout."""
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    def load_tasks(self):
        """Загрузка задач (только мои)"""
        tasks = self.service.load_tasks()

        print(f"\n📊 Загрузка моих задач: {len(tasks)}")
        for task in tasks:
            print(f"  - {task.get('title')} (проект: {task.get('project_name')}, статус: {task.get('status')})")

        # Очищаем все колонки
        self.clear_all_columns()

        # Добавляем задачи в соответствующие колонки
        for task in tasks:
            task_card = TaskCard(task)

            column_name = task.get("status")
            if column_name in self.columns:
                column = self.columns[column_name]
                column.add_task(task_card)
                print(f"  ✅ Добавлена задача '{task.get('title')}' в колонку '{column_name}'")
            else:
                print(f"  ⚠️ Колонка '{column_name}' не найдена для задачи '{task.get('title')}'")
                print(f"     Доступные колонки: {list(self.columns.keys())}")

        self.update_statistics()

    def clear_all_columns(self):
        """Очищает все колонки от карточек."""
        for column in self.column_widgets:
            column.clear_tasks()

    def filter_tasks(self):
        priority = self.priorityFilter.currentText()

        all_tasks = []
        for column in self.column_widgets:
            for card in column.get_tasks():
                all_tasks.append(card.task_data)

        filtered = self.service.filter_tasks_by_priority(all_tasks, priority)

        # Показываем/скрываем карточки
        filtered_ids = {t["id"] for t in filtered}
        for column in self.column_widgets:
            for card in column.get_tasks():
                if card.task_data["id"] in filtered_ids:
                    card.show()
                else:
                    card.hide()

    def update_statistics(self):
        stats = self.service.get_statistics_for_display()

        # Обновляем счетчики в колонках
        for column in self.column_widgets:
            tasks_in_column = column.get_tasks()
            column.update_count(len(tasks_in_column))

        # Обновляем статистику в UI
        if hasattr(self, 'totalTasksLabel'):
            self.totalTasksLabel.setText(f"📊 Всего задач: {stats['total']}")

        if hasattr(self, 'completedTasksLabel'):
            self.completedTasksLabel.setText(f"✅ Выполнено: {stats['done']}")

        if hasattr(self, 'overdueTasksLabel'):
            self.overdueTasksLabel.setText(f"⏰ Просрочено: {stats['overdue']}")

        if hasattr(self, 'overallProgress'):
            self.overallProgress.setValue(self.service.get_progress_percent())