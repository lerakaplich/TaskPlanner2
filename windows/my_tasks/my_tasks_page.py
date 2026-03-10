import os

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QSplitter
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

        self.service = TasksService(
            db_session=db_session,
            project_id=2,
            current_user=current_user,
            mode="my"
        )

        self.columns = {}  # name -> widget
        self.column_widgets = []  # список для обратной совместимости

        self.setup_board()
        self.load_tasks()

        # фильтры
        self.priorityFilter.currentTextChanged.connect(self.filter_tasks)
        self.projectFilter.currentTextChanged.connect(self.filter_tasks)

    # =====================================================
    # BOARD
    # =====================================================

    def setup_board(self):
        """Создает колонки канбан-доски"""

        # Очищаем существующий layout
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
            column_widget = KanbanColumn(col)
            self.columns[col["name"]] = column_widget
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
    # TASKS
    # =====================================================

    def load_tasks(self):
        """Загрузка задач"""
        tasks = self.service.load_tasks()

        # Очищаем колонки
        self.clear_all_columns()

        self.task_cards = []

        for task in tasks:
            task_card = TaskCard(task)
            self.task_cards.append(task_card)

            column_name = task.get("status")
            column = self.columns.get(column_name)

            if column:
                column.add_task(task_card)

        self.update_statistics()

    def clear_all_columns(self):
        """Очищает все колонки от карточек."""
        for column in self.column_widgets:
            column.clear_tasks()

    # =====================================================
    # FILTER
    # =====================================================

    def filter_tasks(self):
        priority = self.priorityFilter.currentText()

        tasks = self.service.filter_tasks_by_priority(
            [t.task_data for t in self.task_cards],
            priority
        )

        visible_ids = {t["id"] for t in tasks}

        for card in self.task_cards:
            if card.task_data["id"] in visible_ids:
                card.show()
            else:
                card.hide()

    # =====================================================
    # STATISTICS
    # =====================================================

    def update_statistics(self):
        stats = self.service.get_statistics_for_display()

        # Обновляем счетчики в колонках
        for column in self.column_widgets:
            count = stats["column_counts"].get(column.column_name, 0)
            column.update_count(count)

        # Обновляем статистику в UI
        if hasattr(self, 'totalTasksLabel'):
            self.totalTasksLabel.setText(f"📊 Всего задач: {stats['total']}")

        if hasattr(self, 'completedTasksLabel'):
            self.completedTasksLabel.setText(f"✅ Выполнено: {stats['done']}")

        if hasattr(self, 'overdueTasksLabel'):
            self.overdueTasksLabel.setText(f"⏰ Просрочено: {stats['overdue']}")

        if hasattr(self, 'overallProgress'):
            progress = self.service.get_progress_percent()
            self.overallProgress.setValue(progress)