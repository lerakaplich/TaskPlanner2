from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import (
    Qt, QRect, QPoint, QDate, pyqtSignal
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, QFontMetrics,
    QPainterPath, QMouseEvent, QPaintEvent
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTreeWidget, QTreeWidgetItem, QDialog, QVBoxLayout as QVBoxDialog,
    QCheckBox, QPushButton, QDateEdit, QMessageBox, QApplication,
    QComboBox
)
from PyQt6 import uic

from services.gantt_service import GanttService, TaskGanttData, ProjectGanttData, Priority
from windows.gantt.gantt_canvas import GanttCanvas
from windows.gantt.link_dialog import LinkDialog
from windows.gantt.period_dialog import PeriodDialog


class GanttWidget(QWidget):
    """
    Основной виджет диаграммы Ганта.
    Содержит фильтры, дерево проектов, приоритеты и холст диаграммы.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._service = GanttService()
        self._service.load_test_data()
        self._dont_show_link_dialog = False
        self._setup_ui()
        self._connect_signals()
        self._populate_data()

    def _setup_ui(self) -> None:
        """Загрузка UI из файла."""
        # Правильный путь: поднимаемся на 2 уровня вверх от windows/gantt/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))  # Было 3 dirname, стало 2
        ui_path = os.path.join(project_root, "ui", "gantt", "gantt_widget.ui")

        print(f"Текущая директория: {current_dir}")
        print(f"Project root: {project_root}")
        print(f"UI путь: {ui_path}")
        print(f"UI файл существует: {os.path.exists(ui_path)}")

        if not os.path.exists(ui_path):
            raise FileNotFoundError(
                f"UI файл не найден: {ui_path}\n"
                f"Проверьте структуру проекта. Ожидается: {project_root}\\ui\\gantt\\gantt_widget.ui"
            )

        # Загружаем UI
        uic.loadUi(ui_path, self)
        print("UI успешно загружен!")

        # Дальше ваш код...

        # Настройка холста Ганта (только если UI загрузился успешно)
        self.gantt_canvas = GanttCanvas(self._service)
        self.gantt_canvas.set_links(self._service.get_all_links())

        # Заменяем заглушку на холст
        if hasattr(self, 'ganttScrollArea'):
            gantt_layout = self.ganttScrollArea.layout()
            if gantt_layout is None:
                gantt_layout = QVBoxLayout(self.ganttScrollArea)
                self.ganttScrollArea.setLayout(gantt_layout)

            # Удаляем старый виджет если есть
            old_widget = self.ganttScrollArea.widget()
            if old_widget and old_widget != self.gantt_canvas:
                gantt_layout.removeWidget(old_widget)
                old_widget.deleteLater()

            gantt_layout.addWidget(self.gantt_canvas)
            self.ganttScrollArea.setWidget(self.gantt_canvas)

        # Настройка приоритетов
        if hasattr(self, 'prioritiesLayout'):
            self._setup_priorities()

    def _setup_priorities(self) -> None:
        """Настройка отображения приоритетов."""
        priorities = [
            ("critical", "Критический", "#D22730"),
            ("high", "Высокий", "#ccab6e"),
            ("medium", "Средний", "#1B232A"),
            ("low", "Низкий", "#998664"),
        ]

        for _, name, color in priorities:
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 2, 5, 2)
            item_layout.setSpacing(10)

            # Цветовой индикатор
            indicator = QLabel()
            indicator.setFixedSize(16, 16)
            indicator.setStyleSheet(
                f"background-color: {color}; border-radius: 8px;"
            )
            item_layout.addWidget(indicator)

            # Название приоритета
            name_label = QLabel(name)
            name_label.setStyleSheet("font-size: 13px; color: #1B232A;")
            item_layout.addWidget(name_label)

            item_layout.addStretch()
            self.prioritiesLayout.addWidget(item_widget)

    def _connect_signals(self) -> None:
        """Подключение сигналов."""
        self.addTaskButton.clicked.connect(self._on_add_task)
        self.createLinkButton.clicked.connect(self._on_create_link)
        self.periodFilter.currentTextChanged.connect(self._on_period_changed)
        self.projectFilter.currentTextChanged.connect(self._on_filter_changed)
        self.executorFilter.currentTextChanged.connect(self._on_filter_changed)

        # Сигнал перемещения задачи
        self.gantt_canvas.task_moved.connect(self._on_task_moved)

        # Клик по дереву проектов
        self.projectsTree.itemClicked.connect(self._on_project_item_clicked)

    def _populate_data(self) -> None:
        """Заполнение данных."""
        self._populate_projects_tree()
        self._populate_filters()

    def _populate_projects_tree(self) -> None:
        """Заполнение дерева проектов."""
        self.projectsTree.clear()
        projects = self._service.get_projects()

        for project in projects:
            project_item = QTreeWidgetItem(self.projectsTree)
            project_item.setText(0, f"📁 {project.name}")
            project_item.setData(0, Qt.ItemDataRole.UserRole, f"project_{project.id}")

            # Стиль для проекта
            project_item.setForeground(0, QColor("#1B232A"))
            font = project_item.font(0)
            font.setBold(True)
            font.setPointSize(12)
            project_item.setFont(0, font)

            for task in project.tasks:
                task_item = QTreeWidgetItem(project_item)
                task_item.setText(
                    0, f"{task.name} ({task.executor_name})"
                )
                task_item.setData(0, Qt.ItemDataRole.UserRole, f"task_{task.id}")
                task_item.setForeground(0, QColor(task.color))
                task_font = task_item.font(0)
                task_font.setPointSize(11)
                task_item.setFont(0, task_font)

            # Раскрываем проект
            project_item.setExpanded(True)

    def _populate_filters(self) -> None:
        """Заполнение фильтров."""
        # Блокируем сигналы на время заполнения
        self.projectFilter.blockSignals(True)
        self.executorFilter.blockSignals(True)

        # Заполняем проекты
        self.projectFilter.clear()
        self.projectFilter.addItem("Все проекты", "all")
        projects = self._service.get_projects()
        for project in projects:
            self.projectFilter.addItem(project.name, f"project_{project.id}")

        # Заполняем исполнителей
        self.executorFilter.clear()
        self.executorFilter.addItem("Все исполнители", "all")
        executors_set = set()
        for task in self._service.get_all_tasks():
            executors_set.add(task.executor_name)
        for executor in sorted(executors_set):
            self.executorFilter.addItem(executor, executor)

        self.projectFilter.blockSignals(False)
        self.executorFilter.blockSignals(False)

    def _on_add_task(self) -> None:
        """Обработка кнопки добавления задачи."""
        # Здесь будет открытие существующего TaskDialog
        QMessageBox.information(
            self, "Добавить задачу",
            "Открытие диалога TaskDialog (существующий диалог из TaskPlanner2)"
        )

    def _on_create_link(self) -> None:
        """Обработка кнопки создания связи."""
        if not self._dont_show_link_dialog:
            dialog = LinkDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if dialog.dont_show_checkbox.isChecked():
                    self._dont_show_link_dialog = True

        QMessageBox.information(
            self, "Создание связи",
            "Используйте Ctrl+клик на двух задачах для создания связи между ними.\n"
            "Первая выбранная задача будет предшественником, вторая - последователем."
        )

    def _on_period_changed(self, text: str) -> None:
        """Обработка изменения периода."""
        if text == "Выбрать период":
            dialog = PeriodDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                start, end = dialog.get_dates()
                self.gantt_canvas.set_date_range(start, end)
        else:
            start, end = self._service.get_date_range(text)
            self.gantt_canvas.set_date_range(start, end)
        self.gantt_canvas.update()

    def _on_filter_changed(self) -> None:
        """Обработка изменения фильтров."""
        project_filter = self.projectFilter.currentData()
        executor_filter = self.executorFilter.currentData()

        # Обновляем видимость в дереве проектов
        for i in range(self.projectsTree.topLevelItemCount()):
            project_item = self.projectsTree.topLevelItem(i)
            project_data = project_item.data(0, Qt.ItemDataRole.UserRole)

            # Фильтр по проекту
            project_visible = (
                project_filter == "all" or project_data == project_filter
            )

            visible_tasks = 0
            for j in range(project_item.childCount()):
                task_item = project_item.child(j)
                task_id_str = task_item.data(0, Qt.ItemDataRole.UserRole)
                if task_id_str and task_id_str.startswith("task_"):
                    task_id = int(task_id_str.split("_")[1])
                    task = next(
                        (t for t in self._service.get_all_tasks() if t.id == task_id),
                        None
                    )
                    if task:
                        # Фильтр по исполнителю
                        executor_visible = (
                            executor_filter == "all"
                            or executor_filter == task.executor_name
                        )
                        task_visible = project_visible and executor_visible
                        task_item.setHidden(not task_visible)
                        if task_visible:
                            visible_tasks += 1

            project_item.setHidden(not project_visible or visible_tasks == 0)
            if project_visible and visible_tasks > 0:
                project_item.setExpanded(True)

    def _on_project_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Обработка клика по элементу дерева проектов."""
        # Переключение раскрытия/скрытия проекта
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())

    def _on_task_moved(self, task_id: int, new_start: datetime, new_end: datetime) -> None:
        """Обработка перемещения задачи."""
        print(
            f"Задача {task_id} перемещена: "
            f"{new_start.strftime('%d.%m.%Y')} - {new_end.strftime('%d.%m.%Y')}"
        )
        # Обновляем связи на холсте
        self.gantt_canvas.set_links(self._service.get_all_links())


if __name__ == "__main__":
    import sys
    import os

    # Правильный путь
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))  # 2 уровня, не 3!

    print(f"Current dir: {current_dir}")
    print(f"Project root: {project_root}")

    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from PyQt6.QtWidgets import QApplication, QMainWindow


    class TestWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("TaskPlanner2 - Диаграмма Ганта")
            self.setMinimumSize(1200, 800)
            self.setStyleSheet("QMainWindow { background-color: #F5F5F5; }")

            try:
                self.gantt_widget = GanttWidget(self)
                self.setCentralWidget(self.gantt_widget)
                print("Виджет успешно создан и отображен!")
            except Exception as e:
                print(f"Ошибка: {e}")
                import traceback
                traceback.print_exc()


    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = TestWindow()
    window.show()
    sys.exit(app.exec())