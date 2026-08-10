# windows/gantt/gantt_widget_handlers.py

from datetime import datetime
from typing import Optional
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QDialog, QMessageBox, QApplication, QTreeWidgetItem


class GanttWidgetHandlers:
    """Обработчики событий для GanttWidget"""

    def __init__(self, widget):
        self.widget = widget

    def load_initial_data(self) -> None:
        self.widget._service.load_data()
        self.widget._refresh_ui()

    def full_reload(self) -> None:
        self.widget._service.clear_cache()
        self.widget._service.load_data()
        self.widget._refresh_ui()

    def on_project_filter_changed(self, index: int) -> None:
        """Обработчик изменения фильтра по проекту (по индексу)"""
        if index < 0:
            print("❌ on_project_filter_changed: index < 0")
            return

        data = self.widget.projectFilter.itemData(index)
        text = self.widget.projectFilter.itemText(index)

        print(f"📁 on_project_filter_changed: index={index}, text='{text}', data='{data}'")

        if data is None or data == "all":
            self.widget._current_project_filter = "all"
        else:
            self.widget._current_project_filter = data

        print(f"📁 Фильтр проекта установлен: {self.widget._current_project_filter}")

        # ✅ Применяем фильтры
        self.widget._views.apply_filters()

        # ✅ Принудительно обновляем холст
        if hasattr(self.widget, 'gantt_canvas') and self.widget.gantt_canvas:
            self.widget.gantt_canvas.update()
            self.widget.gantt_canvas.repaint()
            self.widget.gantt_canvas.updateGeometry()

    def on_executor_filter_changed(self, index: int) -> None:
        """Обработчик изменения фильтра по исполнителю (по индексу)"""
        if index < 0:
            print("❌ on_executor_filter_changed: index < 0")
            return

        data = self.widget.executorFilter.itemData(index)
        text = self.widget.executorFilter.itemText(index)

        print(f"👤 on_executor_filter_changed: index={index}, text='{text}', data='{data}'")

        if data is None or data == "all":
            self.widget._current_executor_filter = "all"
        else:
            self.widget._current_executor_filter = data

        print(f"👤 Фильтр исполнителя установлен: {self.widget._current_executor_filter}")

        # ✅ Применяем фильтры
        self.widget._views.apply_filters()

        # ✅ Принудительно обновляем холст
        if hasattr(self.widget, 'gantt_canvas') and self.widget.gantt_canvas:
            self.widget.gantt_canvas.update()
            self.widget.gantt_canvas.repaint()
            self.widget.gantt_canvas.updateGeometry()

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

    def on_search_filter(self, query: str):
        """Поиск по диаграмме Ганта"""
        query = query.strip().lower()
        self.widget._current_search_text = query

        if not query:
            self.clear_search_filter()
            return

        self._apply_search(query)

    def clear_search_filter(self):
        """Очищает поиск и восстанавливает все данные"""
        self.widget._current_search_text = ""
        self._restore_all_data()

    def get_filtered_count(self) -> int:
        """Возвращает количество найденных элементов"""
        if not hasattr(self.widget, '_current_search_text') or not self.widget._current_search_text:
            all_tasks = self.widget._service.get_all_tasks()
            return len(all_tasks)

        filtered_tasks = self.widget._service.get_filtered_tasks(
            self.widget._current_project_filter,
            self.widget._current_executor_filter
        )

        search_text = self.widget._current_search_text
        result = []
        for task in filtered_tasks:
            if self._task_matches_search(task, search_text):
                result.append(task)

        return len(result)

    def _apply_search(self, query: str):
        """Применяет поиск к текущим задачам"""
        all_tasks = self.widget._service.get_filtered_tasks(
            self.widget._current_project_filter,
            self.widget._current_executor_filter
        )

        filtered = []
        for task in all_tasks:
            if self._task_matches_search(task, query):
                filtered.append(task)

        if hasattr(self.widget, 'gantt_canvas'):
            self.widget.gantt_canvas.set_tasks(filtered)

        if hasattr(self.widget, 'calendar_widget'):
            self.widget.calendar_widget.set_tasks(filtered)

        self._update_tree_with_search(query)

    def _task_matches_search(self, task, query: str) -> bool:
        """Проверяет, соответствует ли задача поисковому запросу"""
        search_fields = [
            task.name.lower(),
            task.executor_name.lower() if task.executor_name else "",
            task.project_name.lower() if task.project_name else "",
            task.priority.lower() if task.priority else "",
            task.status.lower() if task.status else "",
            str(task.id),
            task.executor_initials.lower() if task.executor_initials else "",
        ]
        return any(query in field for field in search_fields)

    def _update_tree_with_search(self, query: str):
        """Обновляет дерево проектов с учётом поиска"""
        if not hasattr(self.widget, 'projectsTree'):
            return

        self.widget.projectsTree.clear()
        all_tasks = self.widget._service.get_all_tasks()

        if query:
            filtered_tasks = [t for t in all_tasks if self._task_matches_search(t, query)]
        else:
            filtered_tasks = all_tasks

        projects_dict = {}
        for task in filtered_tasks:
            if task.project_id not in projects_dict:
                projects_dict[task.project_id] = {
                    "name": task.project_name,
                    "tasks": []
                }
            projects_dict[task.project_id]["tasks"].append(task)

        for project_id, data in projects_dict.items():
            project_item = QTreeWidgetItem(self.widget.projectsTree)
            project_item.setText(0, f"📁 {data['name']}")
            project_item.setData(0, Qt.ItemDataRole.UserRole, f"project_{project_id}")

            for task in data['tasks']:
                task_item = QTreeWidgetItem(project_item)
                task_item.setText(0, f"{task.name} ({task.executor_name or 'Не назначен'})")
                task_item.setData(0, Qt.ItemDataRole.UserRole, f"task_{task.id}")

                if query and self._task_matches_search(task, query):
                    task_item.setBackground(0, QColor("#FFF3E0"))

            project_item.setExpanded(True)

    def _restore_all_data(self):
        """Восстанавливает все данные после очистки поиска"""
        self.widget._views.refresh_ui()

    def on_add_task(self) -> None:
        """Создание новой задачи"""
        if not self.widget._service.can_create_task():
            QMessageBox.warning(self.widget, "Доступ запрещён", "У вас нет прав на создание задач.")
            return

        manageable_projects = self.widget._service.get_manageable_projects()

        if not manageable_projects:
            QMessageBox.warning(
                self.widget,
                "Нет доступных проектов",
                "У вас нет проектов, где вы являетесь администратором или куратором.\n"
                "Для создания задач в проекте вам нужна роль 'Руководитель проекта' или 'Куратор'."
            )
            return

        if self.widget._current_project_filter != "all":
            project_id = None
            if isinstance(self.widget._current_project_filter, str) and self.widget._current_project_filter.startswith(
                    "project_"):
                project_id = int(self.widget._current_project_filter.split("_")[1])

            if project_id:
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

        task_data = {}
        if self.widget._current_project_filter != "all":
            project_id = None
            if isinstance(self.widget._current_project_filter, str) and self.widget._current_project_filter.startswith(
                    "project_"):
                project_id = int(self.widget._current_project_filter.split("_")[1])
            if project_id:
                project_name = self.widget._service.get_project_name(project_id)
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

        if hasattr(dialog, 'comboBoxProject'):
            dialog.comboBoxProject.blockSignals(True)
            dialog.comboBoxProject.clear()
            dialog.comboBoxProject.addItem("Выберите проект", None)
            for project in manageable_projects:
                dialog.comboBoxProject.addItem(project["name"], project["id"])

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
        """Создание связи между задачами через диалог"""
        if not self.widget._service.can_create_link():
            QMessageBox.warning(self.widget, "Доступ запрещён", "У вас нет прав на создание связей между задачами.")
            return

        # Получаем все задачи для отображения в диалоге
        all_tasks = self.widget._service.get_all_tasks()

        if len(all_tasks) < 2:
            QMessageBox.warning(
                self.widget,
                "Недостаточно задач",
                "Для создания связи необходимо как минимум 2 задачи.\n"
                "Сначала создайте задачи в проектах."
            )
            return

        from windows.gantt.link_dialog import LinkDialog

        # Создаём диалог с выбором задач
        dialog = LinkDialog(
            parent=self.widget,
            tasks=all_tasks,
            link_type=getattr(self.widget, '_default_link_type', 'FS'),
            show_instruction=True
        )

        # Подключаем сигнал создания связи
        dialog.link_created.connect(self._on_link_created_from_dialog)

        # Показываем диалог
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Сохраняем выбор "Не показывать"
            if dialog.get_dont_show():
                self.widget._dont_show_link_dialog = True
                # Обновляем информацию о связи
                link_type = dialog.get_link_type()
                link_type_name = LinkDialog.LINK_TYPES.get(link_type, "").split(" — ")[0]
                QMessageBox.information(
                    self.widget,
                    "Информация",
                    f"Связь типа '{link_type_name}' будет создана.\n"
                    f"В будущем это окно показываться не будет."
                )

    def _on_link_created_from_dialog(self, predecessor_id: int, successor_id: int, link_type: str) -> None:
        """Обработка создания связи из диалога."""
        self._create_link_internal(predecessor_id, successor_id, link_type)

    def on_link_created(self, predecessor_id: int, successor_id: int) -> None:
        """Обработка создания связи через Ctrl+клик (для обратной совместимости)."""
        if not self.widget._service.can_create_link():
            QMessageBox.warning(self.widget, "Доступ запрещён", "У вас нет прав на создание связей.")
            return

        # Используем тип связи по умолчанию
        link_type = getattr(self.widget, '_default_link_type', 'FS')

        # Если есть диалог связи - используем его
        if not self.widget._dont_show_link_dialog:
            all_tasks = self.widget._service.get_all_tasks()
            pred_task = self.widget._service.get_task_by_id(predecessor_id)
            succ_task = self.widget._service.get_task_by_id(successor_id)

            if not pred_task or not succ_task:
                QMessageBox.warning(self.widget, "Ошибка", "Задачи не найдены")
                return

            from windows.gantt.link_dialog import LinkDialog

            dialog = LinkDialog(
                parent=self.widget,
                tasks=all_tasks,
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                link_type=link_type,
                show_instruction=False
            )

            dialog.link_created.connect(self._on_link_created_from_dialog)

            if dialog.exec() != QDialog.DialogCode.Accepted:
                if hasattr(self.widget, 'gantt_canvas'):
                    self.widget.gantt_canvas.clear_selection()
                return

            # Сохраняем выбор "Не показывать"
            if dialog.get_dont_show():
                self.widget._dont_show_link_dialog = True
        else:
            # Создаём связь без диалога
            self._create_link_internal(predecessor_id, successor_id, link_type)

    def _create_link_internal(self, predecessor_id: int, successor_id: int, link_type: str) -> None:
        """Внутренний метод создания связи."""
        pred_task = self.widget._service.get_task_by_id(predecessor_id)
        succ_task = self.widget._service.get_task_by_id(successor_id)

        if not pred_task or not succ_task:
            QMessageBox.warning(self.widget, "Ошибка", "Задачи не найдены")
            return

        pred_name = pred_task.name
        succ_name = succ_task.name

        # Получаем название типа связи
        from windows.gantt.link_dialog import LinkDialog
        link_type_name = LinkDialog.LINK_TYPES.get(link_type, "").split(" — ")[0]

        # Сохраняем старые даты
        old_start = succ_task.start_date
        old_end = succ_task.end_date

        success, message = self.widget._service.add_dependency_with_message(
            predecessor_id, successor_id, 0, link_type
        )

        if success:
            # Перезагружаем данные
            self.widget._service.refresh_all_data()
            updated_task = self.widget._service.get_task_by_id(successor_id)

            date_changed = ""
            if updated_task:
                new_start = updated_task.start_date
                new_end = updated_task.end_date
                if old_start != new_start or old_end != new_end:
                    date_changed = (
                        f"\n\n📅 Даты задачи '{succ_name}' обновлены:\n"
                        f"Было: {old_start.strftime('%d.%m.%Y')} - {old_end.strftime('%d.%m.%Y')}\n"
                        f"Стало: {new_start.strftime('%d.%m.%Y')} - {new_end.strftime('%d.%m.%Y')}\n"
                        f"Тип связи: {link_type_name}"
                    )

            QMessageBox.information(
                self.widget,
                "Успех",
                f"Связь успешно создана!\n"
                f"{pred_name} → {succ_name}"
                f"{date_changed}"
            )

            self.widget._refresh_ui()
        else:
            QMessageBox.warning(self.widget, "Ошибка", f"Не удалось создать связь:\n{message}")

        if hasattr(self.widget, 'gantt_canvas'):
            self.widget.gantt_canvas.clear_selection()

    def on_link_deleted(self, predecessor_id: int, successor_id: int) -> None:
        """Обработка удаления связи."""
        success, message = self.widget._service.delete_dependency(predecessor_id, successor_id)

        if success:
            # Перезагружаем данные
            self.widget._service.refresh_all_data()
            self.widget._refresh_ui()

            QMessageBox.information(
                self.widget,
                "Успех",
                "Связь успешно удалена!"
            )
        else:
            QMessageBox.warning(
                self.widget,
                "Ошибка",
                f"Не удалось удалить связь:\n{message}"
            )

    # windows/gantt/gantt_widget_handlers.py

    def on_task_moved(self, task_id: int, new_start: datetime, new_end: datetime) -> None:
        """Обработка перемещения задачи"""
        print(f"🔄 on_task_moved: задача {task_id}, новые даты: {new_start.date()} - {new_end.date()}")

        # Обновляем даты задачи и всех зависимых
        if self.widget._service.update_task_dates_with_linked(task_id, new_start, new_end):
            # ✅ ВАЖНО: Полностью перезагружаем данные из БД
            self.widget._service.refresh_all_data()

            # ✅ Обновляем холст с новыми данными
            if hasattr(self.widget, 'gantt_canvas'):
                filtered_tasks = self.widget._service.get_filtered_tasks(
                    self.widget._current_project_filter,
                    self.widget._current_executor_filter
                )
                self.widget.gantt_canvas.set_tasks(filtered_tasks)
                self.widget.gantt_canvas.set_links(self.widget._service.get_all_links())
                self.widget.gantt_canvas.update()
                self.widget.gantt_canvas.repaint()

            # ✅ Обновляем календарь
            if hasattr(self.widget, 'calendar_widget'):
                filtered_tasks = self.widget._service.get_filtered_tasks(
                    self.widget._current_project_filter,
                    self.widget._current_executor_filter
                )
                self.widget.calendar_widget.set_tasks(filtered_tasks)

            print(f"✅ Задача {task_id} перемещена и данные обновлены")
        else:
            print(f"❌ Ошибка перемещения задачи {task_id}")

    def on_project_item_clicked(self, item, column: int) -> None:
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.startswith("task_"):
            task_id = int(data.split("_")[1])
            task = self.widget._service.get_task_by_id(task_id)
            if task:
                self.show_task_info(task)

    def show_link_info(self, predecessor_id: int, successor_id: int) -> None:
        """Показывает информацию о связи между задачами."""
        link_info = self.widget._service.get_link_info(predecessor_id, successor_id)
        if link_info:
            QMessageBox.information(
                self.widget,
                "Информация о связи",
                f"Связь между задачами:\n"
                f"Предшественник ID: {predecessor_id}\n"
                f"Последователь ID: {successor_id}\n"
                f"Тип связи: {link_info.get('type_name', 'Неизвестный')}\n"
                f"Описание: {link_info.get('description', '')}"
            )

    def show_task_info(self, task) -> None:
        info_text = self.widget._service.get_task_info_text(task)
        QMessageBox.information(self.widget, f"Задача: {task.name}", info_text)

    def on_calendar_task_clicked(self, task_id: int) -> None:
        task = self.widget._service.get_task_by_id(task_id)
        if task:
            self.show_task_info(task)

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