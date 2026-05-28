# windows/gantt/gantt_widget.py

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidgetItem,
    QDialog, QMessageBox, QPushButton, QComboBox, QFrame, QGroupBox, QSizePolicy, QScrollArea
)
from PyQt6 import uic

from sqlalchemy.orm import Session


class GanttWidget(QWidget):
    """Основной виджет диаграммы Ганта с реальными данными из БД"""

    def __init__(self, session: Session, current_user_id: int = None, project_service=None, parent=None):
        super().__init__(parent)

        self.session = session
        self.current_user_id = current_user_id
        self.project_service = project_service

        # Импортируем сервис и холст
        from services.gantt_service import GanttService
        from windows.gantt.gantt_canvas import GanttCanvas

        self._service = GanttService(session, current_user_id, project_service)
        self._dont_show_link_dialog = False
        self._current_project_filter = "all"  # all или project_{id}
        self._current_executor_filter = "all"

        self._setup_ui()
        self._connect_signals()
        self._populate_data()

    def _setup_ui(self) -> None:
        """Загрузка UI из файла"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        ui_path = os.path.join(project_root, "ui", "gantt", "gantt_widget.ui")

        if not os.path.exists(ui_path):
            self._create_ui_programmatically()
        else:
            uic.loadUi(ui_path, self)
            self._setup_loaded_ui()
            # Вызываем настройку приоритетов после полной загрузки UI
            # Используем QTimer.singleShot чтобы дать UI время на инициализацию
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self._setup_priorities)

    def _create_ui_programmatically(self) -> None:
        """Создает UI программно если UI файл не найден"""
        from PyQt6.QtWidgets import QFrame, QScrollArea

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Левая панель
        left_panel = QFrame()
        left_panel.setFixedWidth(300)
        left_panel.setStyleSheet("background-color: #F8F9FA; border-right: 1px solid #E8E8E8;")
        left_layout = QVBoxLayout(left_panel)

        # Заголовок
        title_label = QLabel("📊 Диаграмма Ганта")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 15px;")
        left_layout.addWidget(title_label)

        # Фильтры
        filters_group = QFrame()
        filters_group.setStyleSheet("background-color: white; border-radius: 10px; margin: 10px;")
        filters_layout = QVBoxLayout(filters_group)

        # Проекты
        filters_layout.addWidget(QLabel("📁 Проект:"))
        self.projectFilter = QComboBox()
        self.projectFilter.addItem("Все проекты", "all")
        filters_layout.addWidget(self.projectFilter)

        # Исполнитель
        filters_layout.addWidget(QLabel("👤 Исполнитель:"))
        self.executorFilter = QComboBox()
        self.executorFilter.addItem("Все исполнители", "all")
        filters_layout.addWidget(self.executorFilter)

        # Кнопки
        self.addTaskButton = QPushButton("➕ Добавить задачу")
        self.createLinkButton = QPushButton("🔗 Создать связь")
        filters_layout.addWidget(self.addTaskButton)
        filters_layout.addWidget(self.createLinkButton)

        left_layout.addWidget(filters_group)

        # Легенда приоритетов
        legend_group = QFrame()
        legend_group.setStyleSheet("background-color: white; border-radius: 10px; margin: 10px;")
        legend_layout = QVBoxLayout(legend_group)
        legend_layout.addWidget(QLabel("🎨 Приоритеты:"))

        self.prioritiesLayout = QVBoxLayout()  # <-- СОХРАНЯЕМ ССЫЛКУ
        legend_layout.addLayout(self.prioritiesLayout)

        left_layout.addWidget(legend_group)

        # Дерево проектов
        from PyQt6.QtWidgets import QTreeWidget
        self.projectsTree = QTreeWidget()
        self.projectsTree.setHeaderLabel("Задачи")
        self.projectsTree.setStyleSheet("""
            QTreeWidget {
                border: none;
                background-color: transparent;
            }
            QTreeWidget::item {
                padding: 5px;
            }
        """)
        left_layout.addWidget(self.projectsTree)

        left_layout.addStretch()

        # Правая панель - холст
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)

        # Верхняя панель с фильтром периода
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Период:"))
        self.periodFilter = QComboBox()
        self.periodFilter.addItems(["Неделя", "Месяц", "Квартал", "Год", "Выбрать период"])
        top_bar.addWidget(self.periodFilter)
        top_bar.addStretch()
        right_layout.addLayout(top_bar)

        # Холст
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        right_layout.addWidget(scroll_area)

        # Создаем холст после инициализации сервиса
        from windows.gantt.gantt_canvas import GanttCanvas
        self.gantt_canvas = GanttCanvas(self._service)
        scroll_area.setWidget(self.gantt_canvas)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

        # Сохраняем виджеты как атрибуты
        self.projectsTree = self.projectsTree
        self.projectFilter = self.projectFilter
        self.executorFilter = self.executorFilter
        self.periodFilter = self.periodFilter
        self.addTaskButton = self.addTaskButton
        self.createLinkButton = self.createLinkButton
        self.gantt_canvas = self.gantt_canvas

        # Настройка приоритетов
        self._setup_priorities()

    def _setup_loaded_ui(self) -> None:
        """Настройка загруженного UI"""
        from windows.gantt.gantt_canvas import GanttCanvas

        # Создаем холст
        self.gantt_canvas = GanttCanvas(self._service)

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

        # НЕ СОЗДАЁМ prioritiesLayout, он уже есть в UI
        print("✅ UI загружен, prioritiesGroup существует в файле")

    def _setup_priorities(self) -> None:
        """Настройка отображения приоритетов в UI из файла"""
        print("\n🎨 _setup_priorities вызван")

        priorities = [
            ("Критический", "#D22730"),
            ("Высокий", "#ccab6e"),
            ("Средний", "#1B232A"),
            ("Низкий", "#998664"),
        ]

        # Ищем prioritiesGroup
        container = self.findChild(QGroupBox, "prioritiesGroup")

        if not container:
            print("❌ prioritiesGroup не найден")
            return

        print(f"✅ Найден prioritiesGroup: {container.objectName()}")

        # Убеждаемся, что группа видна
        container.setVisible(True)
        container.setMinimumHeight(80)
        container.setMaximumHeight(120)

        # Получаем существующий layout или создаем новый
        layout = container.layout()
        if layout is None:
            # Создаем новый горизонтальный layout для компактного отображения
            layout = QHBoxLayout(container)
            layout.setContentsMargins(10, 5, 10, 5)
            layout.setSpacing(20)
            container.setLayout(layout)
            print("✅ Создан новый QHBoxLayout")
        else:
            # Очищаем существующий layout
            print(f"✅ Используем существующий layout: {type(layout).__name__}")
            # Удаляем все виджеты из layout
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        # Добавляем приоритеты в одну строку
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        for name, color in priorities:
            # Создаем контейнер для одного приоритета
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(5)

            # Цветной кружок
            indicator = QLabel()
            indicator.setFixedSize(12, 12)
            indicator.setStyleSheet(f"""
                background-color: {color}; 
                border-radius: 6px;
                border: 1px solid rgba(0,0,0,0.1);
            """)
            item_layout.addWidget(indicator)

            # Название
            name_label = QLabel(name)
            name_label.setStyleSheet("font-size: 12px; color: #1B232A; font-weight: normal;")
            item_layout.addWidget(name_label)

            layout.addWidget(item_widget)

        # Добавляем растяжку в конец
        layout.addStretch()

        # Принудительно обновляем
        container.updateGeometry()
        container.update()

        # Обновляем родителя
        if container.parent():
            container.parent().updateGeometry()

        print(f"✅ Приоритеты добавлены, layout.count() = {layout.count()}")
        print(f"   - container.isVisible(): {container.isVisible()}")
        print(f"   - container.height(): {container.height()}")

    def _connect_signals(self) -> None:
        """Подключение сигналов"""
        self.addTaskButton.clicked.connect(self._on_add_task)
        self.createLinkButton.clicked.connect(self._on_create_link)
        self.periodFilter.currentTextChanged.connect(self._on_period_changed)
        self.projectFilter.currentTextChanged.connect(self._on_project_filter_changed)
        self.executorFilter.currentTextChanged.connect(self._on_executor_filter_changed)

        # Сигнал перемещения задачи
        if hasattr(self, 'gantt_canvas'):
            self.gantt_canvas.task_moved.connect(self._on_task_moved)

        # Клик по дереву проектов
        self.projectsTree.itemClicked.connect(self._on_project_item_clicked)

    def _populate_data(self) -> None:
        """Заполнение данными из БД"""
        print("📊 GanttWidget: загрузка данных...")
        self._service.load_data()
        self._populate_projects_tree()
        self._populate_filters()
        self._apply_filters()  # Применяем фильтры после загрузки
        self._update_canvas_date_range()

    def refresh(self) -> None:
        """Обновление данных - полная перезагрузка"""
        print("🔄 GanttWidget.refresh() - полное обновление")

        # Очищаем кэш сервиса
        self._service._cached_tasks = []
        self._service._cached_projects = []

        # Полная перезагрузка данных
        self._service.load_data()

        # Обновляем дерево проектов
        self._populate_projects_tree()

        # Обновляем фильтры
        self._populate_filters()

        # Применяем фильтры (это обновит холст)
        self._apply_filters()

        # Обновляем диапазон дат на холсте
        self._update_canvas_date_range()

        # Обновляем связи на холсте
        if hasattr(self, 'gantt_canvas'):
            self.gantt_canvas.set_links(self._service.get_all_links())
            self.gantt_canvas.update()

    def _populate_projects_tree(self) -> None:
        """Заполнение дерева проектов"""
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

            # Добавляем задачи проекта
            tasks = self._service.get_tasks_for_project(project.id)
            for task in tasks:
                task_item = QTreeWidgetItem(project_item)
                task_item.setText(0, f"{task.name} ({task.executor_name or 'Не назначен'})")
                task_item.setData(0, Qt.ItemDataRole.UserRole, f"task_{task.id}")
                task_item.setForeground(0, QColor(task.color))
                task_font = task_item.font(0)
                task_font.setPointSize(11)
                task_item.setFont(0, task_font)

            project_item.setExpanded(True)

        print(f"   ✅ Дерево заполнено: {len(projects)} проектов, всего задач: {len(self._service.get_all_tasks())}")

    def _populate_filters(self) -> None:
        """Заполнение фильтров"""
        self.projectFilter.blockSignals(True)
        self.executorFilter.blockSignals(True)

        # Заполняем проекты
        self.projectFilter.clear()
        self.projectFilter.addItem("Все проекты", "all")
        for project in self._service.get_projects():
            self.projectFilter.addItem(project.name, f"project_{project.id}")

        # Заполняем исполнителей
        self.executorFilter.clear()
        self.executorFilter.addItem("Все исполнители", "all")
        executors_set = set()
        for task in self._service.get_all_tasks():
            if task.executor_name:
                executors_set.add(task.executor_name)
        for executor in sorted(executors_set):
            self.executorFilter.addItem(executor, executor)

        self.projectFilter.blockSignals(False)
        self.executorFilter.blockSignals(False)

        # Настраиваем отображение текста в editable режиме
        self._setup_filters_placeholder()

    def _on_project_filter_changed(self, text: str) -> None:
        """Обработка изменения фильтра проектов"""
        # Получаем текущие данные
        current_data = self.projectFilter.currentData()

        # Если текст введен вручную (не из списка), current_data может быть None
        if current_data is None or current_data == "all":
            # Пользователь ввел свой текст или выбрал "Все проекты"
            if text == "Все проекты" or text == "":
                self._current_project_filter = "all"
            else:
                # Ищем проект по введенному тексту
                for i in range(self.projectFilter.count()):
                    if self.projectFilter.itemText(i) == text:
                        self._current_project_filter = self.projectFilter.itemData(i)
                        break
                else:
                    # Если не нашли, оставляем текущий фильтр
                    pass
        else:
            self._current_project_filter = current_data

        self._apply_filters()

    def _on_executor_filter_changed(self, text: str) -> None:
        """Обработка изменения фильтра исполнителей"""
        # Получаем текущие данные
        current_data = self.executorFilter.currentData()

        # Если текст введен вручную (не из списка), current_data может быть None
        if current_data is None or current_data == "all":
            # Пользователь ввел свой текст или выбрал "Все исполнители"
            if text == "Все исполнители" or text == "":
                self._current_executor_filter = "all"
            else:
                # Ищем исполнителя по введенному тексту
                for i in range(self.executorFilter.count()):
                    if self.executorFilter.itemText(i) == text:
                        self._current_executor_filter = self.executorFilter.itemData(i)
                        break
                else:
                    # Если не нашли, оставляем текущий фильтр
                    pass
        else:
            self._current_executor_filter = current_data

        self._apply_filters()

    def _apply_filters(self) -> None:
        """Применяет фильтры к отображаемым задачам"""
        # Получаем все задачи
        all_tasks = self._service.get_all_tasks()

        # Применяем фильтр по проекту
        if self._current_project_filter != "all":
            project_id = int(self._current_project_filter.split("_")[1])
            filtered_tasks = [t for t in all_tasks if t.project_id == project_id]
        else:
            filtered_tasks = all_tasks.copy()

        # Применяем фильтр по исполнителю
        if self._current_executor_filter != "all":
            filtered_tasks = [t for t in filtered_tasks if t.executor_name == self._current_executor_filter]

        # Обновляем холст с отфильтрованными задачами
        if hasattr(self, 'gantt_canvas'):
            self.gantt_canvas.set_filtered_tasks(filtered_tasks)

        # Обновляем видимость в дереве проектов
        self._update_tree_visibility()

    def _setup_filters_placeholder(self) -> None:
        """Настройка плейсхолдеров для фильтров"""
        # Для projectFilter
        if hasattr(self, 'projectFilter'):
            # Устанавливаем текущий текст как "Все проекты"
            self.projectFilter.setEditText("Все проекты")
            # Настраиваем, чтобы при клике текст не выделялся полностью
            line_edit = self.projectFilter.lineEdit()
            if line_edit:
                line_edit.setPlaceholderText("Все проекты")
                line_edit.setReadOnly(False)
                # При фокусе не выделять весь текст
                line_edit.setSelection(0, 0)

        # Для executorFilter
        if hasattr(self, 'executorFilter'):
            # Устанавливаем текущий текст как "Все исполнители"
            self.executorFilter.setEditText("Все исполнители")
            # Настраиваем, чтобы при клике текст не выделялся полностью
            line_edit = self.executorFilter.lineEdit()
            if line_edit:
                line_edit.setPlaceholderText("Все исполнители")
                line_edit.setReadOnly(False)
                # При фокусе не выделять весь текст
                line_edit.setSelection(0, 0)

    def _update_tree_visibility(self) -> None:
        """Обновляет видимость элементов в дереве проектов на основе фильтров"""
        for i in range(self.projectsTree.topLevelItemCount()):
            project_item = self.projectsTree.topLevelItem(i)
            project_data = project_item.data(0, Qt.ItemDataRole.UserRole)

            # Проверяем фильтр по проекту
            project_visible = (
                    self._current_project_filter == "all" or
                    project_data == self._current_project_filter
            )

            visible_tasks = 0
            for j in range(project_item.childCount()):
                task_item = project_item.child(j)
                task_data = task_item.data(0, Qt.ItemDataRole.UserRole)
                if task_data and task_data.startswith("task_"):
                    task_id = int(task_data.split("_")[1])
                    task = next(
                        (t for t in self._service.get_all_tasks() if t.id == task_id),
                        None
                    )
                    if task:
                        # Фильтр по исполнителю
                        executor_visible = (
                                self._current_executor_filter == "all" or
                                self._current_executor_filter == task.executor_name
                        )
                        task_visible = project_visible and executor_visible
                        task_item.setHidden(not task_visible)
                        if task_visible:
                            visible_tasks += 1

            project_item.setHidden(not project_visible or visible_tasks == 0)
            if project_visible and visible_tasks > 0:
                project_item.setExpanded(True)

    def _update_canvas_date_range(self) -> None:
        """Обновляет диапазон дат на холсте на основе отфильтрованных задач"""
        tasks = self._service.get_all_tasks()

        # Если есть фильтр по проекту, используем отфильтрованные задачи для дат
        if self._current_project_filter != "all":
            project_id = int(self._current_project_filter.split("_")[1])
            tasks = [t for t in tasks if t.project_id == project_id]

        if tasks:
            start = min(t.start_date for t in tasks)
            end = max(t.end_date for t in tasks)

            # Добавляем отступ
            start = start - timedelta(days=7)
            end = end + timedelta(days=7)

            if hasattr(self, 'gantt_canvas'):
                self.gantt_canvas.set_date_range(start, end)

    def _on_add_task(self) -> None:
        """Обработка кнопки добавления задачи"""
        # Проверяем, выбран ли проект
        if self._current_project_filter == "all":
            QMessageBox.warning(
                self, "Выберите проект",
                "Пожалуйста, сначала выберите проект из списка проектов,\n"
                "чтобы создать задачу в конкретном проекте."
            )
            return

        # Получаем ID выбранного проекта
        project_id = int(self._current_project_filter.split("_")[1])

        # Находим название проекта
        project_name = ""
        for project in self._service.get_projects():
            if project.id == project_id:
                project_name = project.name
                break

        # Создаем диалог создания задачи
        from windows.other_tasks.task_dialog import TaskDialog
        from services.tasks_service.tasks_service import TasksService
        from services.employee_service.column_service import ColumnService

        # ИСПРАВЛЕНО: передаём корректный db_session
        task_service = TasksService(
            db_session=self.session,  # <-- ИСПРАВЛЕНО! Используем self.session
            current_user={"id": self.current_user_id, "last_name": "", "first_name": ""},
            mode="others",
            column_service=ColumnService(self.session)  # Передаём column_service
        )

        # Подготавливаем данные задачи с предустановленным проектом
        task_data = {
            "project_id": project_id,
            "project_name": project_name
        }

        dialog = TaskDialog(
            parent=None,
            task_data=task_data,
            mode="create",
            current_user={"id": self.current_user_id, "last_name": "", "first_name": ""}
        )
        dialog.set_service(task_service)
        dialog.task_saved.connect(lambda task_id, form_data: self._on_task_created(project_id, form_data))
        dialog.exec()

    def _on_task_created(self, project_id: int, form_data: dict) -> None:
        """Обработчик создания задачи"""
        print(f"✅ Задача создана в проекте {project_id}: {form_data}")

        # СОЗДАЁМ ЗАДАЧУ ЧЕРЕЗ СЕРВИС
        from services.tasks_service.tasks_service import TasksService
        from services.employee_service.column_service import ColumnService

        task_service = TasksService(
            db_session=self.session,
            current_user={"id": self.current_user_id, "last_name": "", "first_name": ""},
            mode="others",
            column_service=ColumnService(self.session)
        )

        try:
            # Добавляем project_id в form_data если его нет
            if "project_id" not in form_data:
                form_data["project_id"] = project_id

            # Создаём задачу
            new_task = task_service.create_task(form_data)
            print(f"✅ Задача успешно создана! ID: {new_task.get('id')}")

            # Полная перезагрузка данных
            self.refresh()

            QMessageBox.information(self, "Успех", "Задача успешно создана!")

        except Exception as e:
            print(f"❌ Ошибка при создании задачи: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать задачу:\n{str(e)}")

    def _on_create_link(self) -> None:
        """Обработка кнопки создания связи"""
        if not self._dont_show_link_dialog:
            from windows.gantt.link_dialog import LinkDialog
            dialog = LinkDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if dialog.dont_show_checkbox.isChecked():
                    self._dont_show_link_dialog = True

        QMessageBox.information(
            self, "Создание связи",
            "Чтобы создать связь между задачами:\n"
            "1. Нажмите Ctrl+клик на первой задаче (предшественник)\n"
            "2. Затем Ctrl+клик на второй задаче (последователь)\n"
            "3. Подтвердите создание связи"
        )

    def _on_period_changed(self, text: str) -> None:
        """Обработка изменения периода"""
        if text == "Выбрать период":
            from windows.gantt.period_dialog import PeriodDialog
            dialog = PeriodDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                start, end = dialog.get_dates()
                self.gantt_canvas.set_date_range(start, end)
        else:
            start, end = self._service.get_date_range(text)
            self.gantt_canvas.set_date_range(start, end)
        self.gantt_canvas.update()

    def _on_project_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Обработка клика по элементу дерева"""
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())

        # Если это задача, можно показать информацию
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.startswith("task_"):
            task_id = int(data.split("_")[1])
            task = next((t for t in self._service.get_all_tasks() if t.id == task_id), None)
            if task:
                self._show_task_info(task)

    def _show_task_info(self, task) -> None:
        """Показывает информацию о задаче"""
        QMessageBox.information(
            self,
            f"Задача: {task.name}",
            f"Проект: {task.project_name}\n"
            f"Исполнитель: {task.executor_name or 'Не назначен'}\n"
            f"Приоритет: {task.priority}\n"
            f"Прогресс: {task.progress}%\n"
            f"Даты: {task.start_date.date()} - {task.end_date.date()}\n"
            f"Длительность: {task.duration_days} дней"
        )

    def _on_task_moved(self, task_id: int, new_start: datetime, new_end: datetime) -> None:
        """Обработка перемещения задачи"""
        if self._service.update_task_dates(task_id, new_start, new_end):
            # Обновляем связи на холсте
            self.gantt_canvas.set_links(self._service.get_all_links())
            print(f"✅ Задача {task_id} перемещена: {new_start.date()} - {new_end.date()}")