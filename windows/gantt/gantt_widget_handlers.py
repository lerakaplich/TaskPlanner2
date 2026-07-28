# windows/gantt/gantt_widget_handlers.py

from datetime import datetime
from typing import Optional
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import QDialog, QMessageBox, QApplication


class GanttWidgetHandlers:
    """Обработчики событий для GanttWidget"""

    def __init__(self, widget):
        self.widget = widget

    # ==========================================================
    # НАВИГАЦИЯ И ЗАГРУЗКА
    # ==========================================================

    def load_initial_data(self) -> None:
        self.widget._service.load_data()
        self.widget._refresh_ui()

    def full_reload(self) -> None:
        self.widget._service.clear_cache()
        self.widget._service.load_data()
        self.widget._refresh_ui()

    # ==========================================================
    # ФИЛЬТРЫ
    # ==========================================================

    def on_project_filter_changed(self, text: str) -> None:
        current_data = self.widget.projectFilter.currentData()
        if current_data is None or current_data == "all":
            if text == "Все проекты" or text == "":
                self.widget._current_project_filter = "all"
            else:
                for i in range(self.widget.projectFilter.count()):
                    if self.widget.projectFilter.itemText(i) == text:
                        self.widget._current_project_filter = self.widget.projectFilter.itemData(i)
                        break
        else:
            self.widget._current_project_filter = current_data
        self.widget._apply_filters()

    def on_executor_filter_changed(self, text: str) -> None:
        current_data = self.widget.executorFilter.currentData()
        if current_data is None or current_data == "all":
            if text == "Все исполнители" or text == "":
                self.widget._current_executor_filter = "all"
            else:
                for i in range(self.widget.executorFilter.count()):
                    if self.widget.executorFilter.itemText(i) == text:
                        self.widget._current_executor_filter = self.widget.executorFilter.itemData(i)
                        break
        else:
            self.widget._current_executor_filter = current_data
        self.widget._apply_filters()

    def on_period_changed(self, text: str) -> None:
        from windows.gantt.period_dialog import PeriodDialog

        if text == "Выбрать период":
            dialog = PeriodDialog(self.widget)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                start, end = dialog.get_dates()
                self.widget.gantt_canvas.set_date_range(start, end)
        else:
            start, end = self.widget._service.get_date_range(text)
            self.widget.gantt_canvas.set_date_range(start, end)
        self.widget.gantt_canvas.update()

    # windows/gantt/gantt_widget_handlers.py

    def on_add_task(self) -> None:
        """Создание новой задачи"""
        if not self.widget._service.can_create_task():
            QMessageBox.warning(self.widget, "Доступ запрещён", "У вас нет прав на создание задач.")
            return

        # ✅ Получаем проекты, где пользователь может управлять задачами
        manageable_projects = self.widget._service.get_manageable_projects()

        if not manageable_projects:
            QMessageBox.warning(
                self.widget,
                "Нет доступных проектов",
                "У вас нет проектов, где вы являетесь администратором или куратором.\n"
                "Для создания задач в проекте вам нужна роль 'Руководитель проекта' или 'Куратор'."
            )
            return

        # Проверяем, есть ли проекты для выбранного фильтра
        if self.widget._current_project_filter != "all":
            project_id = None
            if isinstance(self.widget._current_project_filter, str) and self.widget._current_project_filter.startswith(
                    "project_"):
                project_id = int(self.widget._current_project_filter.split("_")[1])

            if project_id:
                # Проверяем, есть ли выбранный проект в списке доступных
                project_exists = any(p["id"] == project_id for p in manageable_projects)
                if not project_exists:
                    QMessageBox.warning(
                        self.widget,
                        "Доступ запрещён",
                        "У вас нет прав на создание задач в выбранном проекте.\n"
                        "Выберите проект, где вы являетесь администратором или куратором."
                    )
                    return

        from windows.other_tasks.task_dialog import TaskDialog
        from services.tasks_service.tasks_service import TasksService
        from services.employee_service.column_service import ColumnService

        task_service = TasksService(
            db_session=self.widget.session,
            current_user={"id": self.widget.current_user_id, "last_name": "", "first_name": ""},
            mode="others",
            column_service=ColumnService(self.widget.session)
        )

        # Открываем диалог с предустановленным проектом (если выбран)
        task_data = {}
        if self.widget._current_project_filter != "all":
            project_id = None
            if isinstance(self.widget._current_project_filter, str) and self.widget._current_project_filter.startswith(
                    "project_"):
                project_id = int(self.widget._current_project_filter.split("_")[1])
            if project_id:
                project_name = self.widget._service.get_project_name(project_id)
                # Проверяем, доступен ли проект
                if any(p["id"] == project_id for p in manageable_projects):
                    task_data = {"project_id": project_id, "project_name": project_name}
                else:
                    task_data = {"project_id": manageable_projects[0]["id"],
                                 "project_name": manageable_projects[0]["name"]}

        dialog = TaskDialog(
            parent=self.widget,
            task_data=task_data,
            mode="create",
            current_user={"id": self.widget.current_user_id, "last_name": "", "first_name": ""}
        )

        dialog.set_service(task_service)

        # ✅ Фильтруем комбобокс проектов в диалоге
        if hasattr(dialog, 'comboBoxProject'):
            dialog.comboBoxProject.blockSignals(True)
            dialog.comboBoxProject.clear()
            dialog.comboBoxProject.addItem("Выберите проект", None)
            for project in manageable_projects:
                dialog.comboBoxProject.addItem(project["name"], project["id"])

            # Если есть предустановленный проект - выбираем его
            if task_data.get("project_id"):
                for i in range(dialog.comboBoxProject.count()):
                    if dialog.comboBoxProject.itemData(i) == task_data["project_id"]:
                        dialog.comboBoxProject.setCurrentIndex(i)
                        break

            dialog.comboBoxProject.blockSignals(False)

        dialog.task_saved.connect(lambda tid, data: self.on_task_created(task_data.get("project_id"), data))
        dialog.exec()

    def on_task_created(self, project_id: int, form_data: dict) -> None:
        if "project_id" not in form_data:
            form_data["project_id"] = project_id

        new_task = self.widget._service.create_task_via_service(form_data)

        if new_task:
            self.widget._service.refresh_all_data()
            self.widget._refresh_ui()

            if self.widget._current_project_filter != f"project_{project_id}":
                reply = QMessageBox.question(
                    self.widget, "Переключить фильтр?",
                    f"Задача создана в проекте. Показать этот проект на диаграмме?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    for i in range(self.widget.projectFilter.count()):
                        if self.widget.projectFilter.itemData(i) == f"project_{project_id}":
                            self.widget.projectFilter.setCurrentIndex(i)
                            break

            QMessageBox.information(self.widget, "Успех", "Задача успешно создана!")
        else:
            QMessageBox.critical(self.widget, "Ошибка", "Не удалось создать задачу")

    def on_create_link(self) -> None:
        if not self.widget._service.can_create_link():
            QMessageBox.warning(self.widget, "Доступ запрещён", "У вас нет прав на создание связей между задачами.")
            return

        if not self.widget._dont_show_link_dialog:
            from windows.gantt.link_dialog import LinkDialog
            dialog = LinkDialog(self.widget)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if dialog.dont_show_checkbox.isChecked():
                    self.widget._dont_show_link_dialog = True

        QMessageBox.information(
            self.widget, "Создание связи",
            "Чтобы создать связь между задачами:\n"
            "1. Нажмите Ctrl+клик на первой задаче (предшественник)\n"
            "2. Затем Ctrl+клик на второй задаче (последователь)\n"
            "3. Подтвердите создание связи"
        )

    def on_link_created(self, predecessor_id: int, successor_id: int) -> None:
        if not self.widget._service.can_create_link():
            QMessageBox.warning(self.widget, "Доступ запрещён", "У вас нет прав на создание связей.")
            return

        reply = QMessageBox.question(
            self.widget, "Создание связи",
            f"Создать связь между задачами?\nПредшественник ID: {predecessor_id}\nПоследователь ID: {successor_id}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.widget._service.add_dependency(predecessor_id, successor_id):
                QMessageBox.information(self.widget, "Успех", "Связь успешно создана!")
                if hasattr(self.widget, 'gantt_canvas'):
                    self.widget.gantt_canvas.set_links(self.widget._service.get_all_links())
                    self.widget.gantt_canvas.update()
            else:
                QMessageBox.warning(self.widget, "Ошибка", "Не удалось создать связь")

    def on_task_moved(self, task_id: int, new_start: datetime, new_end: datetime) -> None:
        if self.widget._service.update_task_dates_with_linked(task_id, new_start, new_end):
            if hasattr(self.widget, 'gantt_canvas'):
                self.widget.gantt_canvas.set_links(self.widget._service.get_all_links())
            print(f"✅ Задача {task_id} перемещена: {new_start.date()} - {new_end.date()}")

    # ==========================================================
    # ВЗАИМОДЕЙСТВИЕ С UI
    # ==========================================================

    def on_project_item_clicked(self, item, column: int) -> None:
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.startswith("task_"):
            task_id = int(data.split("_")[1])
            task = self.widget._service.get_task_by_id(task_id)
            if task:
                self.show_task_info(task)

    def show_task_info(self, task) -> None:
        info_text = self.widget._service.get_task_info_text(task)
        QMessageBox.information(self.widget, f"Задача: {task.name}", info_text)

    def on_calendar_task_clicked(self, task_id: int) -> None:
        task = self.widget._service.get_task_by_id(task_id)
        if task:
            self.show_task_info(task)

    # ==========================================================
    # ЭКСПОРТ
    # ==========================================================

    def on_export_clicked(self) -> None:
        from windows.gantt.export_dialog import ExportDialog
        from windows.gantt.period_dialog import PeriodDialog

        if not hasattr(self.widget, 'gantt_canvas') or self.widget.gantt_canvas is None:
            QMessageBox.warning(self.widget, "Экспорт", "Нет данных для экспорта")
            return

        all_tasks = self.widget._service.get_filtered_tasks(
            self.widget._current_project_filter,
            self.widget._current_executor_filter
        )

        if not all_tasks:
            QMessageBox.warning(self.widget, "Экспорт", "Нет задач для экспорта")
            return

        dialog = ExportDialog(self.widget)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_format = dialog.get_selected_format()
        period_dialog = PeriodDialog(self.widget)

        start_default, end_default = self.widget._service.get_default_export_period(all_tasks)
        period_dialog.start_edit.setDate(QDate(start_default.year, start_default.month, start_default.day))
        period_dialog.end_edit.setDate(QDate(end_default.year, end_default.month, end_default.day))

        if period_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        start_date, end_date = period_dialog.get_dates()
        filtered_tasks = self.widget._service.get_filtered_tasks_for_export(all_tasks, start_date, end_date)

        if not filtered_tasks:
            QMessageBox.warning(
                self.widget,
                "Экспорт",
                f"Нет задач в выбранном периоде\n{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
            )
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            saved_path = None

            if selected_format == "image":
                saved_path = self.widget._service.export_to_image_with_period(
                    self.widget.gantt_canvas, filtered_tasks, start_date, end_date
                )
            elif selected_format == "excel":
                saved_path = self.widget._service.export_to_excel(filtered_tasks, start_date, end_date)
            elif selected_format == "docx":
                saved_path = self.widget._service.export_to_docx(filtered_tasks, start_date, end_date)

            if saved_path:
                QMessageBox.information(
                    self.widget,
                    "Экспорт завершён",
                    f"Диаграмма Ганта успешно сохранена:\n{saved_path}\n\n"
                    f"Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n"
                    f"Задач: {len(filtered_tasks)}"
                )

        except Exception as e:
            QMessageBox.critical(self.widget, "Ошибка экспорта", f"Не удалось экспортировать диаграмму:\n{str(e)}")

        finally:
            QApplication.restoreOverrideCursor()