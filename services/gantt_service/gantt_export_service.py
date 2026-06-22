# services/gantt_service/gantt_export_service.py

from datetime import datetime
from typing import List, Optional, Tuple

from .gantt_base_service import GanttBaseService, TaskGanttData


class GanttExportService(GanttBaseService):
    """Сервис для экспорта диаграммы Ганта"""

    def __init__(self, permission_service=None):
        self.permission_service = permission_service

    def can_export(self) -> bool:
        """Проверяет права на экспорт"""
        if not self.permission_service:
            return False
        from services.permissions.app_permissions import AppRole
        return self.permission_service.app_manager.role in (AppRole.SUPER_ADMIN, AppRole.ADMIN)

    def export_to_image_with_period(
        self,
        canvas_widget,
        tasks: List[TaskGanttData],
        start_date: datetime,
        end_date: datetime
    ) -> Optional[str]:
        """Экспортирует диаграмму в PNG"""
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtWidgets import QApplication

        if not canvas_widget or not tasks:
            return None

        original_tasks = canvas_widget._tasks.copy()
        original_start = canvas_widget._start_date
        original_end = canvas_widget._end_date
        original_links = canvas_widget._links.copy()

        try:
            canvas_widget.set_tasks(tasks)
            canvas_widget.set_date_range(start_date, end_date)

            # Фильтруем связи для видимых задач
            from .gantt_dependency_service import GanttDependencyService
            dep_service = GanttDependencyService(None, None)
            # ... логика фильтрации связей

            canvas_widget.updateGeometry()
            canvas_widget.update()

            for _ in range(10):
                QApplication.processEvents()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"gantt_chart_{timestamp}.png"

            file_path, _ = QFileDialog.getSaveFileName(
                canvas_widget,
                "Сохранить диаграмму Ганта",
                default_name,
                "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;All Files (*.*)"
            )

            if not file_path:
                return None

            pixmap = canvas_widget.grab()
            if pixmap.save(file_path):
                return file_path
            return None

        except Exception as e:
            print(f"❌ Ошибка экспорта PNG: {e}")
            return None

        finally:
            canvas_widget.set_tasks(original_tasks)
            canvas_widget.set_date_range(original_start, original_end)
            canvas_widget.set_links(original_links)
            canvas_widget.update()
            QApplication.processEvents()

    def export_to_excel(self, tasks: List[TaskGanttData], start_date: datetime = None, end_date: datetime = None) -> Optional[str]:
        """Экспортирует в Excel"""
        # ... логика экспорта в Excel
        pass

    def export_to_docx(self, tasks: List[TaskGanttData], start_date: datetime = None, end_date: datetime = None) -> Optional[str]:
        """Экспортирует в Word"""
        # ... логика экспорта в Word
        pass

    def get_task_info_text(self, task: TaskGanttData) -> str:
        """Возвращает информацию о задаче"""
        return (
            f"Проект: {task.project_name}\n"
            f"Исполнитель: {task.executor_name or 'Не назначен'}\n"
            f"Приоритет: {task.priority}\n"
            f"Прогресс: {task.progress}%\n"
            f"Даты: {task.start_date.date()} - {task.end_date.date()}\n"
            f"Длительность: {task.duration_days} дней"
        )