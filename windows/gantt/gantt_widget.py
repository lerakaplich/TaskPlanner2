# windows/gantt/gantt_widget.py

import os
from datetime import datetime, timedelta
from typing import Optional, List
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidgetItem,
    QDialog, QMessageBox, QPushButton, QComboBox, QFrame, QGroupBox, QScrollArea, QApplication, QTabWidget
)
from PyQt6 import uic

from sqlalchemy.orm import Session

from services.permissions.app_permissions import AppRole


class GanttWidget(QWidget):
    """Основной виджет диаграммы Ганта - с поддержкой прав доступа"""

    def __init__(self, session: Session, current_user_id: int = None, project_service=None, permission_service=None,
                 parent=None):
        super().__init__(parent)

        self.session = session
        self.current_user_id = current_user_id
        self.project_service = project_service
        self.permission_service = permission_service  # <-- ПРЯМОЕ ПРИСВАИВАНИЕ
        self._first_show = True

        from services.gantt_service import GanttService
        from windows.gantt.gantt_canvas import GanttCanvas

        self._service = GanttService(session, current_user_id, project_service, self.permission_service)
        self._dont_show_link_dialog = False
        self._current_project_filter = "all"
        self._current_executor_filter = "all"

        self._setup_ui()
        self._connect_signals()

        # Настройка UI в зависимости от прав
        self._setup_permission_ui()

    def _can_export(self) -> bool:
        """Проверяет, может ли пользователь экспортировать диаграмму"""
        if not self.permission_service:
            return False  # Без сервиса - НЕ РАЗРЕШАЕМ

        # Экспорт доступен суперадмину и админу
        app_role = self.permission_service.app_manager.role
        return app_role in (AppRole.SUPER_ADMIN, AppRole.ADMIN)

    def _setup_permission_ui(self):
        """Настраивает UI в зависимости от прав пользователя"""
        # Кнопка добавления задачи
        if hasattr(self, 'addTaskButton'):
            can_create = self._can_create_task()
            self.addTaskButton.setVisible(can_create)
            print(f"   addTaskButton visible (Гант): {can_create}")

        # Кнопка создания связи
        if hasattr(self, 'createLinkButton'):
            can_create_link = self._can_create_link()
            self.createLinkButton.setVisible(can_create_link)
            print(f"   createLinkButton visible (Гант): {can_create_link}")

        # Кнопка экспорта
        if hasattr(self, 'btnExport'):
            can_export = self._can_export()
            self.btnExport.setVisible(can_export)
            print(f"   btnExport visible (Гант): {can_export}")

    def _can_create_task(self) -> bool:
        """Проверяет, может ли пользователь создавать задачи"""
        if not self.permission_service:
            return False  # Без сервиса - НЕ РАЗРЕШАЕМ

        # Только суперадмин может создавать задачи на диаграмме Ганта
        app_role = self.permission_service.app_manager.role
        return app_role == AppRole.SUPER_ADMIN

    def _can_create_link(self) -> bool:
        """Проверяет, может ли пользователь создавать связи между задачами"""
        if not self.permission_service:
            return False  # Без сервиса - НЕ РАЗРЕШАЕМ

        # Только суперадмин может создавать связи
        app_role = self.permission_service.app_manager.role
        return app_role == AppRole.SUPER_ADMIN

    def showEvent(self, event):
        """Срабатывает при каждом показе страницы"""
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            QTimer.singleShot(10, self._load_initial_data)
        else:
            print("🔄 Повторный показ страницы Гант - перезагружаем")
            QTimer.singleShot(10, self._full_reload)

    def _full_reload(self):
        """Полная перезагрузка страницы Гант"""
        print("🔄 Полная перезагрузка страницы Гант")
        self._service.clear_cache()
        self._service.load_data()
        self._refresh_ui()

    def _setup_ui(self) -> None:
        """Загрузка UI из файла или создание программно"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        ui_path = os.path.join(project_root, "ui", "gantt", "gantt_widget.ui")

        if not os.path.exists(ui_path):
            self._create_ui_programmatically()
        else:
            uic.loadUi(ui_path, self)
            self._setup_loaded_ui()
            QTimer.singleShot(100, self._setup_priorities)

    def _create_ui_programmatically(self) -> None:
        """Создает UI программно если UI файл не найден"""
        from PyQt6.QtWidgets import QTreeWidget

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

        filters_layout.addWidget(QLabel("📁 Проект:"))
        self.projectFilter = QComboBox()
        self.projectFilter.addItem("Все проекты", "all")
        filters_layout.addWidget(self.projectFilter)

        filters_layout.addWidget(QLabel("👤 Исполнитель:"))
        self.executorFilter = QComboBox()
        self.executorFilter.addItem("Все исполнители", "all")
        filters_layout.addWidget(self.executorFilter)

        self.addTaskButton = QPushButton("➕ Добавить задачу")
        self.createLinkButton = QPushButton("🔗 Создать связь")
        self.btnExport = QPushButton("📎 Экспорт")
        filters_layout.addWidget(self.addTaskButton)
        filters_layout.addWidget(self.createLinkButton)
        filters_layout.addWidget(self.btnExport)

        left_layout.addWidget(filters_group)

        # Легенда приоритетов
        legend_group = QFrame()
        legend_group.setStyleSheet("background-color: white; border-radius: 10px; margin: 10px;")
        legend_layout = QVBoxLayout(legend_group)
        legend_layout.addWidget(QLabel("🎨 Приоритеты:"))
        self.prioritiesLayout = QVBoxLayout()
        legend_layout.addLayout(self.prioritiesLayout)
        left_layout.addWidget(legend_group)

        # Дерево проектов
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

        # Правая панель
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Период:"))
        self.periodFilter = QComboBox()
        self.periodFilter.addItems(["Неделя", "Месяц", "Квартал", "Год", "Выбрать период"])
        top_bar.addWidget(self.periodFilter)
        top_bar.addStretch()
        right_layout.addLayout(top_bar)

        # Вкладки
        self.tabWidget = QTabWidget()
        self.tabWidget.addTab(QWidget(), "Диаграмма Ганта")
        # self.tabWidget.addTab(QWidget(), "Календарь")
        right_layout.addWidget(self.tabWidget)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.tabWidget.widget(0).setLayout(QVBoxLayout())
        self.tabWidget.widget(0).layout().addWidget(scroll_area)

        from windows.gantt.gantt_canvas import GanttCanvas
        self.gantt_canvas = GanttCanvas(self._service)
        scroll_area.setWidget(self.gantt_canvas)

        # Настройка календаря
        from windows.gantt.calendar_widget import CalendarWidget
        self.calendar_widget = CalendarWidget(self._service)
        self.tabWidget.widget(1).setLayout(QVBoxLayout())
        self.tabWidget.widget(1).layout().addWidget(self.calendar_widget)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

        self._setup_priorities()

    def _setup_loaded_ui(self) -> None:
        """Настройка загруженного UI"""
        from windows.gantt.gantt_canvas import GanttCanvas
        from windows.gantt.calendar_widget import CalendarWidget

        # Настройка диаграммы Ганта
        self.gantt_canvas = GanttCanvas(self._service)

        if hasattr(self, 'ganttScrollArea'):
            gantt_layout = self.ganttScrollArea.layout()
            if gantt_layout is None:
                gantt_layout = QVBoxLayout(self.ganttScrollArea)
                self.ganttScrollArea.setLayout(gantt_layout)

            old_widget = self.ganttScrollArea.widget()
            if old_widget and old_widget != self.gantt_canvas:
                gantt_layout.removeWidget(old_widget)
                old_widget.deleteLater()

            gantt_layout.addWidget(self.gantt_canvas)
            self.ganttScrollArea.setWidget(self.gantt_canvas)

        # Настройка календаря
        self.calendar_widget = CalendarWidget(self._service)

        calendar_tab = self.findChild(QWidget, "calendarTab")
        if calendar_tab:
            tab_layout = calendar_tab.layout()
            if tab_layout is None:
                tab_layout = QVBoxLayout(calendar_tab)
                tab_layout.setContentsMargins(0, 0, 0, 0)
                tab_layout.setSpacing(0)
                calendar_tab.setLayout(tab_layout)
            else:
                while tab_layout.count():
                    item = tab_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()

            tab_layout.addWidget(self.calendar_widget)

        placeholder = self.findChild(QLabel, "calendarPlaceholder")
        if placeholder:
            placeholder.hide()
            placeholder.deleteLater()

        print("✅ UI загружен")

    def _setup_priorities(self) -> None:
        """Настройка отображения приоритетов"""
        priorities = [
            ("Критический", "#D22730"),
            ("Высокий", "#ccab6e"),
            ("Средний", "#1B232A"),
            ("Низкий", "#998664"),
        ]

        container = self.findChild(QGroupBox, "prioritiesGroup")
        if not container:
            return

        container.setVisible(True)
        container.setMinimumHeight(80)
        container.setMaximumHeight(120)

        layout = container.layout()
        if layout is None:
            layout = QHBoxLayout(container)
            layout.setContentsMargins(10, 5, 10, 5)
            layout.setSpacing(20)
            container.setLayout(layout)
        else:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        for name, color in priorities:
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(5)

            indicator = QLabel()
            indicator.setFixedSize(12, 12)
            indicator.setStyleSheet(f"""
                background-color: {color}; 
                border-radius: 6px;
                border: 1px solid rgba(0,0,0,0.1);
            """)
            item_layout.addWidget(indicator)

            name_label = QLabel(name)
            name_label.setStyleSheet("font-size: 12px; color: #1B232A; font-weight: normal;")
            item_layout.addWidget(name_label)

            layout.addWidget(item_widget)

        layout.addStretch()
        container.updateGeometry()

    def _connect_signals(self) -> None:
        """Подключение сигналов UI к методам"""
        if hasattr(self, 'addTaskButton'):
            self.addTaskButton.clicked.connect(self._on_add_task)
        if hasattr(self, 'createLinkButton'):
            self.createLinkButton.clicked.connect(self._on_create_link)
        if hasattr(self, 'periodFilter'):
            self.periodFilter.currentTextChanged.connect(self._on_period_changed)
        if hasattr(self, 'projectFilter'):
            self.projectFilter.currentTextChanged.connect(self._on_project_filter_changed)
        if hasattr(self, 'executorFilter'):
            self.executorFilter.currentTextChanged.connect(self._on_executor_filter_changed)
        if hasattr(self, 'projectsTree'):
            self.projectsTree.itemClicked.connect(self._on_project_item_clicked)
        if hasattr(self, 'btnExport'):
            self.btnExport.clicked.connect(self._on_export_clicked)

        if hasattr(self, 'gantt_canvas'):
            self.gantt_canvas.task_moved_signal.connect(self._on_task_moved)
            self.gantt_canvas.link_created_signal.connect(self._on_link_created)

        if hasattr(self, 'calendar_widget'):
            self.calendar_widget.task_clicked.connect(self._on_calendar_task_clicked)

    def _on_calendar_task_clicked(self, task_id: int) -> None:
        """Обработчик клика по задаче в календаре"""
        task = self._service.get_task_by_id(task_id)
        if task:
            self._show_task_info(task)

    def _on_export_clicked(self) -> None:
        """Обработчик нажатия кнопки экспорта"""
        from windows.gantt.export_dialog import ExportDialog
        from windows.gantt.period_dialog import PeriodDialog

        if not hasattr(self, 'gantt_canvas') or self.gantt_canvas is None:
            QMessageBox.warning(self, "Экспорт", "Нет данных для экспорта")
            return

        all_tasks = self._service.get_filtered_tasks(
            self._current_project_filter,
            self._current_executor_filter
        )
        if not all_tasks:
            QMessageBox.warning(self, "Экспорт", "Нет задач для экспорта")
            return

        dialog = ExportDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_format = dialog.get_selected_format()

        period_dialog = PeriodDialog(self)
        period_dialog.setWindowTitle("Выбор периода для экспорта")

        start_default, end_default = self._service.get_date_range_for_tasks(all_tasks, padding_days=0)
        period_dialog.start_edit.setDate(QDate(start_default.year, start_default.month, start_default.day))
        period_dialog.end_edit.setDate(QDate(end_default.year, end_default.month, end_default.day))

        if period_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        start_date, end_date = period_dialog.get_dates()

        filtered_tasks = []
        for task in all_tasks:
            if (task.start_date <= end_date and task.end_date >= start_date):
                filtered_tasks.append(task)

        if not filtered_tasks:
            QMessageBox.warning(
                self,
                "Экспорт",
                f"Нет задач в выбранном периоде\n{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
            )
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            saved_path = None

            if selected_format == "image":
                saved_path = self._export_to_image_with_period(filtered_tasks, start_date, end_date)
            elif selected_format == "excel":
                saved_path = self._service.export_to_excel(filtered_tasks, start_date, end_date)
            elif selected_format == "docx":
                saved_path = self._service.export_to_docx(filtered_tasks, start_date, end_date)

            if saved_path:
                QMessageBox.information(
                    self,
                    "Экспорт завершён",
                    f"Диаграмма Ганта успешно сохранена:\n{saved_path}\n\n"
                    f"Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n"
                    f"Задач: {len(filtered_tasks)}"
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка экспорта",
                f"Не удалось экспортировать диаграмму:\n{str(e)}"
            )
            print(f"❌ Ошибка экспорта: {e}")
            import traceback
            traceback.print_exc()

        finally:
            QApplication.restoreOverrideCursor()

    def _export_to_image_with_period(self, tasks: List, start_date: datetime, end_date: datetime) -> Optional[str]:
        """Экспортирует диаграмму Ганта в PNG с заданным периодом."""
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtGui import QPixmap
        from datetime import datetime

        original_tasks = self.gantt_canvas._tasks.copy()
        original_start = self.gantt_canvas._start_date
        original_end = self.gantt_canvas._end_date
        original_links = self.gantt_canvas._links.copy()

        try:
            self.gantt_canvas.set_tasks(tasks)
            self.gantt_canvas.set_date_range(start_date, end_date)

            task_ids = {t.id for t in tasks}
            filtered_links = {}
            all_links = self._service.get_all_links()
            for from_id, to_ids in all_links.items():
                if from_id in task_ids:
                    filtered_to_ids = [tid for tid in to_ids if tid in task_ids]
                    if filtered_to_ids:
                        filtered_links[from_id] = filtered_to_ids
            self.gantt_canvas.set_links(filtered_links)

            self.gantt_canvas.updateGeometry()
            self.gantt_canvas.update()

            for _ in range(10):
                QApplication.processEvents()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"gantt_chart_{timestamp}.png"

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить диаграмму Ганта",
                default_name,
                "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;All Files (*.*)"
            )

            if not file_path:
                return None

            pixmap = self.gantt_canvas.grab()
            success = pixmap.save(file_path)

            if success:
                print(f"✅ PNG экспортирован с периодом: {start_date.date()} - {end_date.date()}")
                return file_path
            else:
                print(f"❌ Ошибка сохранения PNG")
                return None

        except Exception as e:
            print(f"❌ Ошибка экспорта PNG: {e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            self.gantt_canvas.set_tasks(original_tasks)
            self.gantt_canvas.set_date_range(original_start, original_end)
            self.gantt_canvas.set_links(original_links)
            self.gantt_canvas.update()
            QApplication.processEvents()

    def _load_initial_data(self) -> None:
        """Начальная загрузка данных"""
        print("📊 GanttWidget: загрузка данных...")
        self._service.load_data()
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        """Обновление всего UI после изменения данных"""
        self._update_projects_tree()
        self._update_filters()
        self._apply_filters()
        self._update_canvas_date_range()

        if hasattr(self, 'gantt_canvas'):
            self.gantt_canvas.set_links(self._service.get_all_links())
            self.gantt_canvas.update()

        if hasattr(self, 'calendar_widget'):
            self.calendar_widget.update()
            self.calendar_widget.repaint()

    def _update_projects_tree(self) -> None:
        """Обновление дерева проектов"""
        if not hasattr(self, 'projectsTree'):
            return
        self.projectsTree.clear()

        for project, tasks in self._service.get_tasks_for_tree():
            project_item = QTreeWidgetItem(self.projectsTree)
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

    def _update_filters(self) -> None:
        """Обновление фильтров"""
        if not hasattr(self, 'projectFilter') or not hasattr(self, 'executorFilter'):
            return

        self.projectFilter.blockSignals(True)
        self.executorFilter.blockSignals(True)

        self.projectFilter.clear()
        self.projectFilter.addItem("Все проекты", "all")
        for project in self._service.get_projects():
            self.projectFilter.addItem(project.name, f"project_{project.id}")

        self.executorFilter.clear()
        self.executorFilter.addItem("Все исполнители", "all")
        for executor in self._service.get_unique_executors():
            self.executorFilter.addItem(executor, executor)

        self.projectFilter.blockSignals(False)
        self.executorFilter.blockSignals(False)

        self._restore_filter_selection()

    def _restore_filter_selection(self) -> None:
        """Восстанавливает выбранные фильтры после обновления"""
        if not hasattr(self, 'projectFilter') or not hasattr(self, 'executorFilter'):
            return

        for i in range(self.projectFilter.count()):
            if self.projectFilter.itemData(i) == self._current_project_filter:
                self.projectFilter.setCurrentIndex(i)
                break

        for i in range(self.executorFilter.count()):
            if self.executorFilter.itemData(i) == self._current_executor_filter:
                self.executorFilter.setCurrentIndex(i)
                break

    def _update_canvas_date_range(self) -> None:
        """Обновление диапазона дат на холсте"""
        if not hasattr(self, 'gantt_canvas'):
            return

        if self._current_project_filter != "all":
            tasks = self._service.get_filtered_tasks(self._current_project_filter, "all")
        else:
            tasks = self._service.get_all_tasks()

        if not tasks:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start = today.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
        else:
            start, end = self._service.get_date_range_for_tasks(tasks, padding_days=5)

        self.gantt_canvas.set_date_range(start, end)

    def _update_tree_visibility(self) -> None:
        """Обновление видимости элементов в дереве проектов"""
        if not hasattr(self, 'projectsTree'):
            return

        all_tasks = self._service.get_all_tasks()
        task_dict = {t.id: t for t in all_tasks}

        for i in range(self.projectsTree.topLevelItemCount()):
            project_item = self.projectsTree.topLevelItem(i)
            project_data = project_item.data(0, Qt.ItemDataRole.UserRole)

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
                    task = task_dict.get(task_id)

                    if task:
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

    def _on_project_filter_changed(self, text: str) -> None:
        """Обработка изменения фильтра проектов"""
        current_data = self.projectFilter.currentData()

        if current_data is None or current_data == "all":
            if text == "Все проекты" or text == "":
                self._current_project_filter = "all"
            else:
                for i in range(self.projectFilter.count()):
                    if self.projectFilter.itemText(i) == text:
                        self._current_project_filter = self.projectFilter.itemData(i)
                        break
        else:
            self._current_project_filter = current_data

        self._apply_filters()

    def _on_executor_filter_changed(self, text: str) -> None:
        """Обработка изменения фильтра исполнителей"""
        current_data = self.executorFilter.currentData()

        if current_data is None or current_data == "all":
            if text == "Все исполнители" or text == "":
                self._current_executor_filter = "all"
            else:
                for i in range(self.executorFilter.count()):
                    if self.executorFilter.itemText(i) == text:
                        self._current_executor_filter = self.executorFilter.itemData(i)
                        break
        else:
            self._current_executor_filter = current_data

        self._apply_filters()

    def _apply_filters(self) -> None:
        """Применяет фильтры к отображаемым задачам"""
        filtered_tasks = self._service.get_filtered_tasks(
            self._current_project_filter,
            self._current_executor_filter
        )

        if hasattr(self, 'gantt_canvas'):
            self.gantt_canvas.set_tasks(filtered_tasks)

        if hasattr(self, 'calendar_widget'):
            self.calendar_widget.set_tasks(filtered_tasks)
            self.calendar_widget.update()
            self.calendar_widget.repaint()

        self._update_tree_visibility()

    def _on_add_task(self) -> None:
        """Обработка кнопки добавления задачи"""
        if not self._can_create_task():
            QMessageBox.warning(self, "Доступ запрещён", "У вас нет прав на создание задач.")
            return

        is_valid, project_id, error = self._service.validate_project_selected(self._current_project_filter)

        if not is_valid:
            QMessageBox.warning(self, "Выберите проект", error)
            return

        project_name = self._service.get_project_name(project_id)

        from windows.other_tasks.task_dialog import TaskDialog
        from services.tasks_service.tasks_service import TasksService
        from services.employee_service.column_service import ColumnService

        task_service = TasksService(
            db_session=self.session,
            current_user={"id": self.current_user_id, "last_name": "", "first_name": ""},
            mode="others",
            column_service=ColumnService(self.session)
        )

        task_data = {"project_id": project_id, "project_name": project_name}

        dialog = TaskDialog(
            parent=self,
            task_data=task_data,
            mode="create",
            current_user={"id": self.current_user_id, "last_name": "", "first_name": ""}
        )
        dialog.set_service(task_service)
        dialog.task_saved.connect(lambda tid, data: self._on_task_created(project_id, data))
        dialog.exec()

    def _on_task_created(self, project_id: int, form_data: dict) -> None:
        """Обработчик создания задачи"""
        if "project_id" not in form_data:
            form_data["project_id"] = project_id

        new_task = self._service.create_task_via_service(form_data)

        if new_task:
            self._service.refresh_all_data()
            self._refresh_ui()

            if self._current_project_filter != f"project_{project_id}":
                reply = QMessageBox.question(
                    self, "Переключить фильтр?",
                    f"Задача создана в проекте. Показать этот проект на диаграмме?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    for i in range(self.projectFilter.count()):
                        if self.projectFilter.itemData(i) == f"project_{project_id}":
                            self.projectFilter.setCurrentIndex(i)
                            break

            QMessageBox.information(self, "Успех", "Задача успешно создана!")
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось создать задачу")

    def _on_create_link(self) -> None:
        """Обработка кнопки создания связи"""
        if not self._can_create_link():
            QMessageBox.warning(self, "Доступ запрещён", "У вас нет прав на создание связей между задачами.")
            return

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

    def _on_link_created(self, predecessor_id: int, successor_id: int) -> None:
        """Обработчик создания связи от холста"""
        if not self._can_create_link():
            QMessageBox.warning(self, "Доступ запрещён", "У вас нет прав на создание связей.")
            return

        reply = QMessageBox.question(
            self, "Создание связи",
            f"Создать связь между задачами?\n"
            f"Предшественник ID: {predecessor_id}\n"
            f"Последователь ID: {successor_id}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self._service.add_dependency(predecessor_id, successor_id):
                QMessageBox.information(self, "Успех", "Связь успешно создана!")
                if hasattr(self, 'gantt_canvas'):
                    self.gantt_canvas.set_links(self._service.get_all_links())
                    self.gantt_canvas.update()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось создать связь")

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

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.startswith("task_"):
            task_id = int(data.split("_")[1])
            task = self._service.get_task_by_id(task_id)
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
        if self._service.update_task_dates_with_linked(task_id, new_start, new_end):
            if hasattr(self, 'gantt_canvas'):
                self.gantt_canvas.set_links(self._service.get_all_links())
            print(f"✅ Задача {task_id} перемещена: {new_start.date()} - {new_end.date()}")