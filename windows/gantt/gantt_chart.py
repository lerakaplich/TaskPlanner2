# windows/gantt/gantt_chart.py

# windows/gantt/gantt_chart.py

import os
from datetime import datetime, timedelta
from typing import List, Dict

from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtGui import (
    QBrush, QPen, QColor, QFont, QPainter, QWheelEvent
)
from PyQt6.QtWidgets import (
    QWidget, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsLineItem, QGraphicsSimpleTextItem,
    QMessageBox, QInputDialog, QTreeWidgetItem, QFileDialog, QDialog, QVBoxLayout, QComboBox, QLabel, QSpinBox,
    QDialogButtonBox
)
from windows.gantt.gantt_constants import (
    PIXELS_PER_DAY,  # 👈 ДОБАВИТЬ ЭТУ СТРОКУ
    TASK_HEIGHT, HEADER_HEIGHT, ROW_HEIGHT,
    COLOR_PRIMARY, COLOR_ACCENT, COLOR_BACKGROUND, COLOR_SECONDARY, COLOR_BORDER,
    COLOR_COMPLETED, COLOR_OVERDUE, COLOR_TEXT, TODAY_COLOR, TODAY
)
from services.gantt_service import GanttService
from windows.gantt.gantt_constants import (
    TASK_HEIGHT, HEADER_HEIGHT, ROW_HEIGHT,
    COLOR_PRIMARY, COLOR_ACCENT, COLOR_BACKGROUND, COLOR_SECONDARY, COLOR_BORDER,
    COLOR_TEXT, TODAY_COLOR, TODAY
)
from windows.other_tasks.task_dialog import TaskDialog


class DependencyDialog(QDialog):
    def __init__(self, parent=None, tasks=None, current_task_id=None):
        super().__init__(parent)
        self.setWindowTitle("Создание связи")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Выбор задачи-предшественника
        layout.addWidget(QLabel("Выберите задачу-предшественник:"))
        self.task_combo = QComboBox()
        for task in tasks:
            if task.id != current_task_id:
                self.task_combo.addItem(f"{task.title} ({task.start_date} - {task.end_date})", task.id)
        layout.addWidget(self.task_combo)

        # Задержка (лаг)
        layout.addWidget(QLabel("Задержка (дней):"))
        self.lag_spin = QSpinBox()
        self.lag_spin.setRange(0, 365)
        self.lag_spin.setValue(0)
        layout.addWidget(self.lag_spin)

        # Тип связи
        layout.addWidget(QLabel("Тип связи:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("Финиш-Старт (FS)", "FS")
        self.type_combo.addItem("Финиш-Финиш (FF)", "FF")
        self.type_combo.addItem("Старт-Старт (SS)", "SS")
        self.type_combo.addItem("Старт-Финиш (SF)", "SF")
        layout.addWidget(self.type_combo)

        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_dependency(self):
        return {
            "predecessor_id": self.task_combo.currentData(),
            "lag": self.lag_spin.value(),
            "type": self.type_combo.currentData()
        }

class GanttTask:
    """Модель задачи для Ганта"""
    def __init__(self, task_data: dict):
        self.id = task_data["id"]
        self.title = task_data["title"]
        self.description = task_data.get("description", "")
        self.start_date = task_data["start_date"]
        self.end_date = task_data["end_date"]
        self.assignee = task_data.get("assignee", "")
        self.assignee_id = task_data.get("assignee_id")
        self.is_critical = task_data.get("is_critical", False)
        self.dependencies = task_data.get("dependencies", [])
        self.children = task_data.get("children", [])
        self.color = COLOR_PRIMARY
        self.project_id = task_data.get("project_id")
        self.status = task_data.get("status", "")
        self._is_completed = task_data.get("is_completed", False)  # Это из БД (is_done_column)
        self.priority = task_data.get("priority", "medium")

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    @property
    def is_overdue(self) -> bool:
        """Просрочена ли задача (дедлайн меньше сегодня, но не завершена)"""
        return self.end_date < TODAY and not self.is_completed

    @property
    def is_completed(self) -> bool:
        """
        Задача считается завершенной если:
        1. В БД колонка is_done_column = True, ИЛИ
        2. Статус из колонки содержит "Готово" или "Done"
        """
        # Если из БД пришел флаг завершения
        if self._is_completed:
            return True
        # Проверяем статус колонки
        if self.status and ("Готово" in self.status or "Done" in self.status or "completed" in self.status.lower()):
            return True
        # Если дата окончания меньше сегодня, но это не значит что завершено!
        # Поэтому убираем условие self.end_date < TODAY
        return False

    @property
    def is_in_progress(self) -> bool:
        """В работе - не завершена и не просрочена"""
        return not self.is_completed and not self.is_overdue


class GanttHeaderItem(QGraphicsRectItem):
    def __init__(self, project_start: datetime.date, total_days: int):
        super().__init__(0, 0, total_days * PIXELS_PER_DAY, HEADER_HEIGHT)
        self.setBrush(QBrush(QColor(COLOR_SECONDARY)))
        self.setPen(QPen(QColor(COLOR_BORDER), 1))
        self._add_date_labels(project_start, total_days)

    def _add_date_labels(self, project_start: datetime.date, total_days: int):
        for i in range(total_days):
            current_date = project_start + timedelta(days=i)
            x = i * PIXELS_PER_DAY
            if i > 0:
                line = QGraphicsLineItem(x, 0, x, HEADER_HEIGHT, self)
                line.setPen(QPen(QColor(COLOR_BORDER), 1, Qt.PenStyle.DotLine))
            if i % 5 == 0 or i == total_days - 1:
                date_text = QGraphicsSimpleTextItem(current_date.strftime("%d.%m"), self)
                date_text.setPos(x + 2, 5)
                date_text.setFont(QFont("Segoe UI", 8))
                date_text.setBrush(QBrush(QColor(COLOR_TEXT)))
                day_text = QGraphicsSimpleTextItem(current_date.strftime("%a"), self)
                day_text.setPos(x + 2, 25)
                day_text.setFont(QFont("Segoe UI", 7))
                day_text.setBrush(QBrush(QColor(COLOR_ACCENT)))


class GanttDependencyItem(QGraphicsLineItem):
    def __init__(self, from_item, to_item, lag: int):
        super().__init__()
        self.from_item = from_item
        self.to_item = to_item
        self.lag = lag
        self.original_pen = QPen(QColor(COLOR_ACCENT), 2, Qt.PenStyle.DashLine)
        self.original_pen.setDashPattern([5, 3])
        self.setPen(self.original_pen)
        self.update_position()

    def update_position(self):
        if not self.from_item or not self.to_item:
            return
        start_x = self.from_item.pos().x() + self.from_item.rect_item.rect().width()
        start_y = self.from_item.pos().y() + TASK_HEIGHT / 2
        end_x = self.to_item.pos().x()
        end_y = self.to_item.pos().y() + TASK_HEIGHT / 2
        self.setLine(start_x, start_y, end_x, end_y)


class GanttScene(QGraphicsScene):
    task_changed = pyqtSignal(int)

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.project_start = TODAY
        self.project_end = TODAY + timedelta(days=30)
        self.tasks: List[GanttTask] = []
        self.task_items: Dict[int, 'GanttTaskItem'] = {}
        self.dependency_items: List[GanttDependencyItem] = []
        self.setBackgroundBrush(QBrush(QColor(COLOR_BACKGROUND)))

    def _on_task_updated(self, task_id: int):
        if self.widget:
            self.widget.update_task_in_tree(task_id)

    def update_scene(self):
        self.clear()
        self.task_items.clear()
        self.dependency_items.clear()

        total_days = (self.project_end - self.project_start).days + 1
        header = GanttHeaderItem(self.project_start, total_days)
        self.addItem(header)

        y = HEADER_HEIGHT
        for task in self.tasks:
            from windows.gantt.gantt_task_item import GanttTaskItem
            # ✅ ПЕРЕДАЕМ parent_widget (self.widget)
            item = GanttTaskItem(task, self.project_start, y, self.widget)  # <-- ВАЖНО!

            self.addItem(item)
            self.task_items[task.id] = item
            y += ROW_HEIGHT

        if self.project_start <= TODAY <= self.project_end:
            days = (TODAY - self.project_start).days
            x = days * PIXELS_PER_DAY
            line = QGraphicsLineItem(x, 0, x, y)
            line.setPen(QPen(QColor(TODAY_COLOR), 2, Qt.PenStyle.DashLine))
            line.setZValue(10)
            self.addItem(line)
            text = QGraphicsSimpleTextItem("Сегодня")
            text.setPos(x + 5, 5)
            text.setBrush(QBrush(QColor(TODAY_COLOR)))
            text.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            text.setZValue(10)
            self.addItem(text)

        self.setSceneRect(0, 0, total_days * PIXELS_PER_DAY + 500, y + 100)

    def _on_task_moved(self, task_id: int, old_start, new_start):
        """Обработчик перемещения задачи"""
        if self.widget and hasattr(self.widget, 'gantt_service'):
            task = next((t for t in self.tasks if t.id == task_id), None)
            if task:
                # Обновляем задачу в БД
                self.widget.gantt_service.update_task_dates(
                    task_id,
                    task.start_date,
                    task.end_date
                )

    def _on_task_resized(self, task_id: int, old_end, new_end):
        """Обработчик изменения размера задачи"""
        if self.widget and hasattr(self.widget, 'gantt_service'):
            task = next((t for t in self.tasks if t.id == task_id), None)
            if task:
                self.widget.gantt_service.update_task_dates(
                    task_id,
                    task.start_date,
                    task.end_date
                )

    def scroll_to_today(self, view):
        days = (TODAY - self.project_start).days
        if 0 <= days <= (self.project_end - self.project_start).days:
            x = days * PIXELS_PER_DAY
            view.centerOn(x, view.height() / 2)


class GanttChartWidget(QWidget):
    def __init__(self, service: GanttService = None, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "gantt", "gantt_chart.ui")
        uic.loadUi(ui_path, self)

        self.gantt_service = service
        self.current_project_id = None
        self.linking_mode = False
        self.pending_pred = None

        self.scene = GanttScene(self)
        self.ganttView.setScene(self.scene)
        self.ganttView.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.ganttView.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.ganttView.viewport().installEventFilter(self)

        self._connect_signals()
        self._load_projects()

    def _connect_signals(self):
        self.btnZoomIn.clicked.connect(self.zoom_in)
        self.btnZoomOut.clicked.connect(self.zoom_out)
        self.btnRefresh.clicked.connect(self.refresh_chart)
        self.btnToday.clicked.connect(self.center_on_today)
        self.btnExport.clicked.connect(self.export_chart)
        self.btnAddTask.clicked.connect(self.add_task_dialog)
        self.btnCreateLink.clicked.connect(self.toggle_linking_mode)
        self.autoPlanningCheck.toggled.connect(self.on_auto_plan_toggled)
        self.projectCombo.currentIndexChanged.connect(self.on_project_changed)
        self.searchTasks.textChanged.connect(self.on_search)
        self.filterMyTasks.toggled.connect(self.on_filter_changed)
        self.filterOverdue.toggled.connect(self.on_filter_changed)
        self.filterInProgress.toggled.connect(self.on_filter_changed)
        self.filterCompleted.toggled.connect(self.on_filter_changed)

    def on_auto_plan_toggled(self, checked):
        """Обработчик включения/выключения автопланирования"""
        if checked:
            # Выключаем чекбокс, чтобы он не оставался включенным
            self.autoPlanningCheck.setChecked(False)
            # Запускаем автопланирование
            self.auto_plan()

    def auto_plan(self):
        """Автоматическое планирование задач"""
        if not self.current_project_id:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите проект")
            return

        # Запрашиваем дату начала планирования
        from PyQt6.QtWidgets import QDateEdit
        from PyQt6.QtCore import QDate

        dialog = QDialog(self)
        dialog.setWindowTitle("Автопланирование")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Дата начала проекта:"))
        date_edit = QDateEdit()
        date_edit.setDate(QDate.currentDate())
        date_edit.setCalendarPopup(True)
        layout.addWidget(date_edit)

        # Опционально: добавить выбор метода планирования
        layout.addWidget(QLabel("Метод планирования:"))
        method_combo = QComboBox()
        method_combo.addItem("По дате начала", "start_date")
        method_combo.addItem("По дате окончания", "end_date")
        layout.addWidget(method_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        start_date = date_edit.date().toPyDate()
        method = method_combo.currentData()

        # Показываем прогресс
        QMessageBox.information(self, "Автопланирование", "Выполняется автоматическое планирование...")

        # Выполняем автопланирование
        result = self.gantt_service.auto_plan_tasks(self.current_project_id, start_date)

        if result["tasks"]:
            # Обновляем отображение
            self.refresh_chart()
            QMessageBox.information(
                self,
                "Автопланирование завершено",
                f"Обновлено {len(result['tasks'])} задач\n\n{result['message']}"
            )
        else:
            QMessageBox.information(self, "Автопланирование", result["message"])

    def show_critical_path(self):
        """Показать критический путь"""
        if not self.current_project_id:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите проект")
            return

        critical_path = self.gantt_service.calculate_critical_path(self.current_project_id)

        if critical_path:
            # Подсвечиваем задачи на критическом пути
            for task_item in self.scene.task_items.values():
                if task_item.task.id in [t["id"] for t in critical_path]:
                    # Подсвечиваем красным
                    task_item.rect_item.setPen(QPen(QColor("#FF4444"), 3))
                else:
                    task_item.rect_item.setPen(QPen(QColor(COLOR_BORDER), 1))

            # Показываем список
            message = "Критический путь:\n" + "\n".join([
                f"  • {t['title']} ({t['start_date']} - {t['end_date']})"
                for t in critical_path
            ])
            QMessageBox.information(self, "Критический путь", message)
        else:
            QMessageBox.information(self, "Критический путь", "Не удалось рассчитать критический путь")

    def update_task_in_tree(self, task_id: int):
        """Обновляет задачу в дереве задач"""
        # Ищем элемент в дереве
        for i in range(self.taskList.topLevelItemCount()):
            item = self.taskList.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == task_id:
                # Находим задачу в scene.tasks
                task = next((t for t in self.scene.tasks if t.id == task_id), None)
                if task:
                    status_emoji = "✅" if task.is_completed else "⚠️" if task.is_overdue else "🔄"
                    date_str = f"{task.start_date.strftime('%d.%m')}–{task.end_date.strftime('%d.%m')}"
                    item.setText(0, f"{status_emoji} {task.title} | {date_str} | {task.assignee}")
                break

    def _load_projects(self):
        if not self.gantt_service:
            return
        projects = self.gantt_service.get_projects_for_gantt()
        self.projectCombo.clear()
        self.projectCombo.addItem("-- Выберите проект --", None)
        for proj in projects:
            self.projectCombo.addItem(proj["name"], proj["id"])

    def on_project_changed(self, index):
        if index <= 0:
            return
        self.current_project_id = self.projectCombo.currentData()
        self.load_real_data()

    def on_search(self, text):
        self.load_real_data()

    def on_filter_changed(self):
        self.load_real_data()

    def load_real_data(self):
        if not self.gantt_service or not self.current_project_id:
            return

        filters = {
            'my_tasks': self.filterMyTasks.isChecked(),
            'overdue': self.filterOverdue.isChecked(),
            'in_progress': self.filterInProgress.isChecked(),
            'completed': self.filterCompleted.isChecked(),
            'search': self.searchTasks.text()
        }

        try:
            result = self.gantt_service.get_project_tasks_for_gantt(self.current_project_id, filters)

            # ✅ ОТЛАДКА
            print(f"🔍 DEBUG: Получено задач: {len(result['tasks'])}")
            for t in result['tasks'][:5]:  # первые 5 задач
                print(f"   - {t['title']} | start: {t['start_date']} | end: {t['end_date']} | status: {t['status']}")

            if not result["tasks"]:
                self._show_empty_message(result["project_name"])
                return

            self.scene.tasks = [GanttTask(task_data) for task_data in result["tasks"]]
            self.scene.project_start = result["project_start"]
            self.scene.project_end = result["project_end"]

            self.dateRangeLabel.setText(
                f"{result['project_start'].strftime('%d.%m.%Y')} - {result['project_end'].strftime('%d.%m.%Y')}"
            )
            self.statusLabel.setText(
                f"✅ Завершено: {result['completed_tasks']} | "
                f"🔄 В работе: {result['in_progress_tasks']} | "
                f"⚠️ Просрочено: {result['overdue_tasks']} | "
                f"📊 Всего: {result['total_tasks']}"
            )

            self._update_task_tree()
            self.scene.update_scene()
            print(f"✅ Загружено {len(result['tasks'])} задач")

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            self._show_empty_message()

    def _update_task_tree(self):
        self.taskList.blockSignals(True)
        self.taskList.clear()

        def add_task_to_tree(task, parent_item=None):
            status_emoji = "✅" if task.is_completed else "⚠️" if task.is_overdue else "🔄"
            date_str = f"{task.start_date.strftime('%d.%m')}–{task.end_date.strftime('%d.%m')}"
            item = QTreeWidgetItem()
            item.setText(0, f"{status_emoji} {task.title} | {date_str} | {task.assignee}")
            item.setData(0, Qt.ItemDataRole.UserRole, task.id)
            if parent_item is None:
                self.taskList.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
            item.setExpanded(True)
            for child in task.children:
                add_task_to_tree(child, item)

        for task in self.scene.tasks:
            add_task_to_tree(task)

        self.taskList.blockSignals(False)

    def _show_empty_message(self, project_name=""):
        self.dateRangeLabel.setText("Нет данных")
        if project_name:
            self.statusLabel.setText(f"В проекте '{project_name}' нет задач")
        else:
            self.statusLabel.setText("Задачи не найдены")
        self.scene.tasks = []
        self.scene.update_scene()

    def refresh_chart(self):
        self.load_real_data()

    def zoom_in(self):
        global PIXELS_PER_DAY
        PIXELS_PER_DAY = min(80, PIXELS_PER_DAY + 10)
        self.refresh_chart()

    def zoom_out(self):
        global PIXELS_PER_DAY
        PIXELS_PER_DAY = max(15, PIXELS_PER_DAY - 10)
        self.refresh_chart()

    def center_on_today(self):
        days = (TODAY - self.scene.project_start).days
        if 0 <= days <= (self.scene.project_end - self.scene.project_start).days:
            x = days * PIXELS_PER_DAY
            self.ganttView.centerOn(x, self.ganttView.height() / 2)

    def export_chart(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Экспорт диаграммы Ганта", "", "PNG Image (*.png);;JPEG Image (*.jpg)"
        )
        if filepath:
            if self.gantt_service.export_to_image(self.scene, filepath):
                QMessageBox.information(self, "Успех", f"Диаграмма экспортирована в {filepath}")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось экспортировать диаграмму")

    # Замените метод add_task_dialog на этот:
    def add_task_dialog(self):
        """Открывает диалог создания задачи (как в OthersTasksPage)"""
        if not self.current_project_id:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите проект")
            return

        # Создаем диалог создания задачи
        dialog = TaskDialog(
            self,
            task_data=None,
            mode="create",
            current_user={"id": self.gantt_service.current_user_id} if self.gantt_service else None
        )

        # Устанавливаем сервис задач
        from services.tasks_service.tasks_service import TasksService
        from database import get_tasks_session

        tasks_session = get_tasks_session()
        tasks_service = TasksService(
            db_session=tasks_session,
            current_user={"id": self.gantt_service.current_user_id} if self.gantt_service else None,
            mode="all"  # Режим для работы со всеми задачами
        )
        dialog.set_service(tasks_service)

        # Подключаем сигнал сохранения
        dialog.task_saved.connect(self.on_task_created)

        dialog.exec()

    def on_task_created(self, task_id, form_data):
        """Обработчик создания задачи"""
        print(f"📝 Создана задача: {form_data}")
        # Обновляем диаграмму
        self.refresh_chart()

        # Показываем уведомление
        QMessageBox.information(self, "Успех", f"Задача '{form_data.get('title', '')}' создана")

    def toggle_linking_mode(self):
        """Включение/выключение режима создания связей"""
        self.linking_mode = not self.linking_mode
        if self.linking_mode:
            self.btnCreateLink.setText("Отмена")
            self.btnCreateLink.setStyleSheet("background-color: #8B0000;")
            self.statusLabel.setText("🔗 Режим создания связей: нажмите на первую задачу, затем на вторую")
        else:
            self.btnCreateLink.setText("Создать связь")
            self.btnCreateLink.setStyleSheet("")
            self.pending_pred = None
            self.statusLabel.setText(
                f"✅ Завершено: {self.statusLabel.text().split('|')[0] if '|' in self.statusLabel.text() else ''} | "
                f"🔄 В работе: ... | ⚠️ Просрочено: ... | 📊 Всего: ..."
            )
        cursor = Qt.CursorShape.PointingHandCursor if self.linking_mode else Qt.CursorShape.ArrowCursor
        self.ganttView.viewport().setCursor(cursor)

    def create_dependency(self, predecessor_id: int, successor_id: int):
        """Создает связь между задачами через диалог"""
        # Находим задачи
        pred_task = next((t for t in self.scene.tasks if t.id == predecessor_id), None)
        succ_task = next((t for t in self.scene.tasks if t.id == successor_id), None)

        if not pred_task or not succ_task:
            QMessageBox.warning(self, "Ошибка", "Задачи не найдены")
            return

        if predecessor_id == successor_id:
            QMessageBox.warning(self, "Ошибка", "Нельзя создать связь с самой собой")
            return

        # Открываем диалог для задания параметров связи
        dialog = DependencyDialog(self, self.scene.tasks, predecessor_id)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dep_data = dialog.get_dependency()

            # Сохраняем связь в БД через сервис
            if self.gantt_service:
                success = self.gantt_service.add_dependency(
                    predecessor_id=predecessor_id,
                    successor_id=successor_id,
                    lag=dep_data["lag"],
                    dep_type=dep_data["type"]
                )
                if success:
                    # Добавляем связь в модель
                    pred_task.dependencies.append({
                        "successor_id": successor_id,
                        "lag": dep_data["lag"],
                        "type": dep_data["type"]
                    })
                    # Обновляем визуальное отображение связей
                    self.update_dependencies_visual()
                    QMessageBox.information(self, "Успех",
                                            f"Связь создана: '{pred_task.title}' → '{succ_task.title}' (лаг: {dep_data['lag']} дн.)")
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось сохранить связь")

    def update_dependencies_visual(self):
        """Обновляет визуальное отображение связей на диаграмме"""
        # Удаляем существующие линии связей
        for dep_item in self.scene.dependency_items:
            self.scene.removeItem(dep_item)
        self.scene.dependency_items.clear()

        # Создаем новые линии для каждой связи
        for task in self.scene.tasks:
            for dep in task.dependencies:
                pred_item = self.scene.task_items.get(task.id)
                succ_item = self.scene.task_items.get(dep.get("successor_id"))
                if pred_item and succ_item:
                    dep_item = GanttDependencyItem(pred_item, succ_item, dep.get("lag", 0))
                    self.scene.addItem(dep_item)
                    self.scene.dependency_items.append(dep_item)

    def eventFilter(self, obj, event):
        if obj == self.ganttView.viewport() and event.type() == QEvent.Type.MouseButtonPress and self.linking_mode:
            pos = self.ganttView.mapToScene(event.pos())
            item = self.scene.itemAt(pos, self.ganttView.transform())
            while item and not hasattr(item, 'task'):
                item = item.parentItem()
            if hasattr(item, 'task'):
                if self.pending_pred is None:
                    self.pending_pred = item.task.id
                    self.statusLabel.setText(f"🔗 Выбрана задача-предшественник: {item.task.title}")
                    # Подсветим выбранную задачу
                    if item in self.scene.task_items.values():
                        item.rect_item.setOpacity(0.7)
                else:
                    # Создаем связь между задачами
                    self.create_dependency(self.pending_pred, item.task.id)
                    # Снимаем подсветку
                    for task_item in self.scene.task_items.values():
                        task_item.rect_item.setOpacity(1.0)
                    self.pending_pred = None
                    self.toggle_linking_mode()
                return True
        return super().eventFilter(obj, event)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_in() if event.angleDelta().y() > 0 else self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

