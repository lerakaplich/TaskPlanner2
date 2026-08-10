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
        print("🔄 refresh_ui - обновление UI")

        self.update_filters()
        self.apply_filters()
        self.update_canvas_date_range()

        # ✅ Получаем свежие данные из сервиса
        filtered_tasks = self.widget._service.get_filtered_tasks(
            self.widget._current_project_filter,
            self.widget._current_executor_filter
        )
        links = self.widget._service.get_all_links()

        if hasattr(self.widget, 'gantt_canvas') and self.widget.gantt_canvas:
            self.widget.gantt_canvas.set_tasks(filtered_tasks)
            self.widget.gantt_canvas.set_links(links)
            self.widget.gantt_canvas.update()
            self.widget.gantt_canvas.repaint()
            self.widget.gantt_canvas.updateGeometry()

        if hasattr(self.widget, 'calendar_widget') and self.widget.calendar_widget:
            self.widget.calendar_widget.set_tasks(filtered_tasks)
            self.widget.calendar_widget.update()
            self.widget.calendar_widget.repaint()

        # ✅ Обновляем дерево проектов
        self.update_projects_tree()

    def update_projects_tree(self) -> None:
        """Обновление дерева проектов с учётом фильтров"""
        if not hasattr(self.widget, 'projectsTree') or not self.widget.projectsTree:
            return

        print(f"🌳 Обновление дерева проектов")
        print(f"   Текущий фильтр проекта: {self.widget._current_project_filter}")
        print(f"   Текущий фильтр исполнителя: {self.widget._current_executor_filter}")

        # Получаем отфильтрованные задачи
        filtered_tasks = self.widget._service.get_filtered_tasks(
            self.widget._current_project_filter,
            self.widget._current_executor_filter
        )

        print(f"   Отфильтровано задач: {len(filtered_tasks)}")

        # ✅ Если есть фильтр по проекту - показываем только задачи этого проекта
        if self.widget._current_project_filter != "all":
            project_id = None
            if isinstance(self.widget._current_project_filter, str) and self.widget._current_project_filter.startswith(
                    "project_"):
                try:
                    project_id = int(self.widget._current_project_filter.split("_")[1])
                    filtered_tasks = [t for t in filtered_tasks if t.project_id == project_id]
                    print(f"   Фильтр по проекту {project_id}: осталось {len(filtered_tasks)} задач")
                except (ValueError, IndexError):
                    pass

        # Группируем задачи по проектам
        projects_dict = {}
        for task in filtered_tasks:
            if task.project_id not in projects_dict:
                projects_dict[task.project_id] = {
                    "name": task.project_name,
                    "tasks": []
                }
            projects_dict[task.project_id]["tasks"].append(task)

        # Очищаем дерево
        self.widget.projectsTree.clear()

        # Если задач нет - показываем сообщение
        if not projects_dict:
            item = QTreeWidgetItem(self.widget.projectsTree)
            item.setText(0, "Нет задач для отображения")
            item.setForeground(0, QColor("#999999"))
            print("🌳 Дерево проектов: нет задач")
            return

        # Сортируем проекты по названию
        for project_id, data in sorted(projects_dict.items(), key=lambda x: x[1]["name"]):
            project_item = QTreeWidgetItem(self.widget.projectsTree)
            project_item.setText(0, f"📁 {data['name']} ({len(data['tasks'])} задач)")
            project_item.setData(0, Qt.ItemDataRole.UserRole, f"project_{project_id}")
            project_item.setForeground(0, QColor("#1B232A"))
            font = project_item.font(0)
            font.setBold(True)
            font.setPointSize(12)
            project_item.setFont(0, font)

            # Сортируем задачи по имени
            for task in sorted(data['tasks'], key=lambda x: x.name):
                task_item = QTreeWidgetItem(project_item)
                task_item.setText(0, f"{task.name} ({task.executor_name or 'Не назначен'})")
                task_item.setData(0, Qt.ItemDataRole.UserRole, f"task_{task.id}")
                task_item.setForeground(0, QColor(task.color))
                task_font = task_item.font(0)
                task_font.setPointSize(11)
                task_item.setFont(0, task_font)

            project_item.setExpanded(True)

        print(f"🌳 Дерево проектов обновлено: {len(projects_dict)} проектов, {len(filtered_tasks)} задач")

    def update_filters(self) -> None:
        """Обновление фильтров"""
        if not hasattr(self.widget, 'projectFilter') or not hasattr(self.widget, 'executorFilter'):
            print("⚠️ update_filters: projectFilter или executorFilter не найдены")
            return

        print("🔄 update_filters: заполнение комбобоксов")

        self.widget.projectFilter.blockSignals(True)
        self.widget.executorFilter.blockSignals(True)

        self.widget.projectFilter.clear()
        self.widget.projectFilter.addItem("Все проекты", "all")
        projects = self.widget._service.get_projects()
        print(f"   Проектов для фильтра: {len(projects)}")
        for project in projects:
            self.widget.projectFilter.addItem(project.name, f"project_{project.id}")
            print(f"      Добавлен: {project.name} -> project_{project.id}")

        self.widget.executorFilter.clear()
        self.widget.executorFilter.addItem("Все исполнители", "all")
        executors = self.widget._service.get_unique_executors()
        print(f"   Исполнителей для фильтра: {len(executors)}")
        for executor in executors:
            self.widget.executorFilter.addItem(executor, executor)
            print(f"      Добавлен: {executor} -> {executor}")

        self.widget.projectFilter.blockSignals(False)
        self.widget.executorFilter.blockSignals(False)

        self._restore_filter_selection()
        print("✅ update_filters завершён")
        print(f"   Текущий фильтр проекта: {self.widget._current_project_filter}")
        print(f"   Текущий фильтр исполнителя: {self.widget._current_executor_filter}")

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
        print("=" * 60)
        print(f"🔍 ПРИМЕНЕНИЕ ФИЛЬТРОВ")
        print(
            f"   Проект: {self.widget._current_project_filter} (тип: {type(self.widget._current_project_filter).__name__})")
        print(
            f"   Исполнитель: {self.widget._current_executor_filter} (тип: {type(self.widget._current_executor_filter).__name__})")
        print("=" * 60)

        filtered_tasks = self.widget._service.get_filtered_tasks(
            self.widget._current_project_filter,
            self.widget._current_executor_filter
        )

        print(f"   Найдено задач: {len(filtered_tasks)}")

        # ✅ Обновляем холст Ганта
        if hasattr(self.widget, 'gantt_canvas') and self.widget.gantt_canvas:
            self.widget.gantt_canvas.set_tasks(filtered_tasks)
            links = self.widget._service.get_all_links()
            self.widget.gantt_canvas.set_links(links)
            self.widget.gantt_canvas.update()
            self.widget.gantt_canvas.repaint()
            self.widget.gantt_canvas.updateGeometry()

        # ✅ Обновляем календарь
        if hasattr(self.widget, 'calendar_widget') and self.widget.calendar_widget:
            self.widget.calendar_widget.set_tasks(filtered_tasks)
            self.widget.calendar_widget.update()
            self.widget.calendar_widget.repaint()

        # ✅ Обновляем видимость кнопок
        self._update_permission_ui()

        # ✅ Перестраиваем дерево проектов
        self.update_projects_tree()

        # ✅ Обновляем диапазон дат
        self.update_canvas_date_range()

        print(f"✅ Фильтры применены, отображено {len(filtered_tasks)} задач")
        print("=" * 60)

    def _update_permission_ui(self):
        """Обновляет видимость кнопок в зависимости от прав"""
        if hasattr(self.widget, 'addTaskButton') and self.widget.addTaskButton:
            can_create = self.widget._service.can_create_task()
            self.widget.addTaskButton.setVisible(can_create)

    def update_canvas_date_range(self) -> None:
        """Обновление диапазона дат на холсте"""
        if not hasattr(self.widget, 'gantt_canvas'):
            return

        tasks = self.widget._service.get_filtered_tasks(
            self.widget._current_project_filter,
            self.widget._current_executor_filter
        )

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