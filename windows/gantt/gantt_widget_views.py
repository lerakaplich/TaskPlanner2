# windows/gantt/gantt_widget_views.py

from datetime import datetime, timedelta
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTreeWidgetItem


class GanttWidgetViews:
    """Отображение данных для GanttWidget"""

    def __init__(self, widget):
        self.widget = widget

    def refresh_ui(self) -> None:
        """Обновление всего UI после изменения данных"""
        self.update_projects_tree()
        self.update_filters()
        self.apply_filters()
        self.update_canvas_date_range()

        if hasattr(self.widget, 'gantt_canvas'):
            # Получаем связи с типами
            links = self.widget._service.get_all_links()
            self.widget.gantt_canvas.set_links(links)
            self.widget.gantt_canvas.update()

        if hasattr(self.widget, 'calendar_widget'):
            self.widget.calendar_widget.set_tasks(self.widget._service.get_all_tasks())
            self.widget.calendar_widget.update()
            self.widget.calendar_widget.repaint()

    def update_projects_tree(self) -> None:
        """Обновление дерева проектов"""
        if not hasattr(self.widget, 'projectsTree'):
            return

        self.widget.projectsTree.clear()

        for project, tasks in self.widget._service.get_tasks_for_tree():
            project_item = QTreeWidgetItem(self.widget.projectsTree)
            project_item.setText(0, f"📁 {project.name}")
            project_item.setData(0, Qt.ItemDataRole.UserRole, f"project_{project.id}")
            project_item.setForeground(0, QColor("#1B232A"))
            font = project_item.font(0)
            font.setBold(True)
            font.setPointSize(12)
            project_item.setFont(0, font)

            for task in tasks:
                task_item = QTreeWidgetItem(project_item)
                task_item.setText(0, f"{task.name} ({task.executor_name or 'Не назначен'})")
                task_item.setData(0, Qt.ItemDataRole.UserRole, f"task_{task.id}")
                task_item.setForeground(0, QColor(task.color))
                task_font = task_item.font(0)
                task_font.setPointSize(11)
                task_item.setFont(0, task_font)

            project_item.setExpanded(True)

    def update_filters(self) -> None:
        """Обновление фильтров"""
        if not hasattr(self.widget, 'projectFilter') or not hasattr(self.widget, 'executorFilter'):
            return

        self.widget.projectFilter.blockSignals(True)
        self.widget.executorFilter.blockSignals(True)

        self.widget.projectFilter.clear()
        self.widget.projectFilter.addItem("Все проекты", "all")
        for project in self.widget._service.get_projects():
            self.widget.projectFilter.addItem(project.name, f"project_{project.id}")

        self.widget.executorFilter.clear()
        self.widget.executorFilter.addItem("Все исполнители", "all")
        for executor in self.widget._service.get_unique_executors():
            self.widget.executorFilter.addItem(executor, executor)

        self.widget.projectFilter.blockSignals(False)
        self.widget.executorFilter.blockSignals(False)

        self._restore_filter_selection()

    def _restore_filter_selection(self) -> None:
        """Восстанавливает выбранные фильтры"""
        if not hasattr(self.widget, 'projectFilter') or not hasattr(self.widget, 'executorFilter'):
            return

        for i in range(self.widget.projectFilter.count()):
            if self.widget.projectFilter.itemData(i) == self.widget._current_project_filter:
                self.widget.projectFilter.setCurrentIndex(i)
                break

        for i in range(self.widget.executorFilter.count()):
            if self.widget.executorFilter.itemData(i) == self.widget._current_executor_filter:
                self.widget.executorFilter.setCurrentIndex(i)
                break

    def apply_filters(self) -> None:
        """Применяет фильтры к отображаемым задачам"""
        filtered_tasks = self.widget._service.get_filtered_tasks(
            self.widget._current_project_filter,
            self.widget._current_executor_filter
        )

        if hasattr(self.widget, 'gantt_canvas'):
            self.widget.gantt_canvas.set_tasks(filtered_tasks)

        if hasattr(self.widget, 'calendar_widget'):
            self.widget.calendar_widget.set_tasks(filtered_tasks)
            self.widget.calendar_widget.update()
            self.widget.calendar_widget.repaint()

        self.update_tree_visibility()

    def update_canvas_date_range(self) -> None:
        """Обновление диапазона дат на холсте"""
        if not hasattr(self.widget, 'gantt_canvas'):
            return

        if self.widget._current_project_filter != "all":
            tasks = self.widget._service.get_filtered_tasks(self.widget._current_project_filter, "all")
        else:
            tasks = self.widget._service.get_all_tasks()

        if not tasks:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start = today.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
        else:
            start, end = self.widget._service.get_date_range_for_tasks(tasks, padding_days=5)

        self.widget.gantt_canvas.set_date_range(start, end)

    def update_tree_visibility(self) -> None:
        """Обновление видимости элементов в дереве проектов"""
        if not hasattr(self.widget, 'projectsTree'):
            return

        all_tasks = self.widget._service.get_all_tasks()
        task_dict = {t.id: t for t in all_tasks}

        for i in range(self.widget.projectsTree.topLevelItemCount()):
            project_item = self.widget.projectsTree.topLevelItem(i)
            project_data = project_item.data(0, Qt.ItemDataRole.UserRole)

            project_visible = (
                self.widget._current_project_filter == "all" or
                project_data == self.widget._current_project_filter
            )

            visible_tasks = 0
            for j in range(project_item.childCount()):
                task_item = project_item.child(j)
                task_data = task_item.data(0, Qt.ItemDataRole.UserRole)

                if task_data and task_data.startswith("task_"):
                    task_id = int(task_data.split("_")[1])
                    task = task_dict.get(task_id)

                    if task:
                        executor_visible = (
                            self.widget._current_executor_filter == "all" or
                            self.widget._current_executor_filter == task.executor_name
                        )
                        task_visible = project_visible and executor_visible
                        task_item.setHidden(not task_visible)
                        if task_visible:
                            visible_tasks += 1

            project_item.setHidden(not project_visible or visible_tasks == 0)
            if project_visible and visible_tasks > 0:
                project_item.setExpanded(True)