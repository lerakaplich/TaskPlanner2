# windows/my_tasks/my_tasks_page.py

import os
from typing import Dict, List

from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent
from PyQt6.QtWidgets import QWidget, QScrollArea, QHBoxLayout, QMessageBox
from sqlalchemy import select

from services.tasks_service.tasks_service import TasksService
from windows.my_tasks.task_card import TaskCard
from windows.widgets.kanban_column import KanbanColumn


class MyTasksPage(QWidget):
    """Страница Мои задачи (только UI слой)"""

    task_moved = pyqtSignal()
    open_project_requested = pyqtSignal(int)

    def __init__(self, db_session, current_user, parent=None, column_service=None):
        super().__init__(parent)

        self._is_loading = False
        self._is_refreshing = False
        self._loaded = False
        self._first_show = True
        self._all_projects = []  # Список проектов для фильтра
        self._current_project_id = None  # Текущий выбранный проект

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "my_tasks"
        )
        uic.loadUi(os.path.join(ui_path, "my_tasks_page.ui"), self)

        self.service = TasksService(
            db_session=db_session,
            current_user=current_user,
            mode="my",
            column_service=column_service
        )

        self.columns = {}
        self.column_widgets = []
        self.current_user = current_user

        self.setup_board()
        # Не загружаем задачи при создании, только при первом показе

        # Drag & Drop
        self.setAcceptDrops(True)

        # Фильтры
        self.priorityFilter.currentTextChanged.connect(self._on_filter_changed)
        self.projectFilter.currentTextChanged.connect(self._on_project_filter_changed)

        # Загружаем проекты для фильтра
        self._load_projects_for_filter()

    def _load_projects_for_filter(self):
        """Загружает проекты для выпадающего списка (только где пользователь участник/админ/куратор/создатель)"""
        try:
            from sqlalchemy import select
            from models.projects import Project, EmployeeProject

            user_id = self.current_user.get("id") if self.current_user else None
            if not user_id:
                print("⚠️ Не удалось получить ID пользователя")
                return

            db_session = self.service.crud.db_session

            # Получаем ID проектов, где пользователь является участником (EmployeeProject)
            # или создателем проекта (Project.created_by)
            stmt = select(Project).where(
                (Project.is_archived == False) & (
                        (Project.id.in_(
                            select(EmployeeProject.project_id).where(EmployeeProject.employee_id == user_id)
                        )) |
                        (Project.created_by == user_id)
                )
            ).order_by(Project.name)

            projects = db_session.scalars(stmt).all()

            self._all_projects = [{"id": p.id, "name": p.name} for p in projects]

            # Блокируем сигналы
            self.projectFilter.blockSignals(True)

            # Обновляем combo box
            self.projectFilter.clear()
            self.projectFilter.addItem("Все проекты", None)
            for project in self._all_projects:
                self.projectFilter.addItem(project["name"], project["id"])

            # Восстанавливаем сигналы
            self.projectFilter.blockSignals(False)

            print(f"📁 Загружено проектов для фильтра (Мои задачи): {len(self._all_projects)}")

        except Exception as e:
            print(f"⚠️ Ошибка загрузки проектов для фильтра: {e}")
            import traceback
            traceback.print_exc()

    def _on_project_filter_changed(self):
        """Обработчик изменения фильтра по проекту - перестраиваем доску"""
        project_id = self.projectFilter.currentData()
        self._current_project_id = project_id

        # Перестраиваем колонки под выбранный проект
        self._rebuild_board_for_project(project_id)

        # Загружаем задачи заново (с учётом фильтра по проекту)
        self._load_tasks_for_current_project()

    def _load_tasks_for_current_project(self):
        """Загружает задачи для текущего выбранного проекта"""
        if self._is_loading:
            return

        self._is_loading = True

        try:
            # Очищаем все колонки
            self.clear_all_columns()

            # Получаем все задачи (с учётом mode=my)
            all_tasks = self.service.get_tasks_for_board()

            # Фильтруем по проекту, если выбран конкретный проект
            if self._current_project_id:
                filtered_tasks = [t for t in all_tasks if t.get("project_id") == self._current_project_id]
            else:
                filtered_tasks = all_tasks

            # Отключаем обновления UI
            self.setUpdatesEnabled(False)
            for column in self.column_widgets:
                column.setUpdatesEnabled(False)

            # Добавляем задачи в колонки
            for task in filtered_tasks:
                column_name = task.get("status")
                if column_name and column_name in self.columns:
                    task_card = TaskCard(task)
                    self._connect_task_card_signals(task_card)
                    self.columns[column_name].add_task(task_card)

            # Включаем обновления UI
            for column in self.column_widgets:
                column.setUpdatesEnabled(True)
            self.setUpdatesEnabled(True)

            # Обновляем статистику
            self.update_statistics()

            # Обновляем геометрию
            self.updateGeometry()
            if self.parent():
                self.parent().updateGeometry()

        except Exception as e:
            print(f"❌ Ошибка загрузки задач для проекта: {e}")
            import traceback
            traceback.print_exc()
            self.setUpdatesEnabled(True)
            for column in self.column_widgets:
                column.setUpdatesEnabled(True)
        finally:
            self._is_loading = False

    def _rebuild_board_for_project(self, project_id: int = None):
        """Перестраивает канбан-доску для выбранного проекта"""
        print(f"🔄 Перестроение доски для проекта: {project_id}")

        # Сбрасываем кэш колонок в сервисе
        if hasattr(self.service.crud, '_column_cache'):
            self.service.crud._column_cache = None

        # Получаем колонки для выбранного проекта
        if project_id:
            # Получаем колонки из проекта
            column_ids = self._get_project_column_ids(project_id)
            column_data = self._get_columns_by_ids(column_ids)
        else:
            # Все проекты - показываем шаблонные колонки
            column_data = self.service.get_columns_for_board()

        # Перестраиваем UI колонок
        self._rebuild_columns_ui(column_data)

    def _get_project_column_ids(self, project_id: int) -> List[int]:
        """Получает ID колонок выбранного проекта"""
        try:
            from models.projects import Project
            from sqlalchemy import select

            db_session = self.service.crud.db_session
            stmt = select(Project).where(Project.id == project_id)
            project = db_session.scalar(stmt)

            if project and project.selected_column_ids:
                # Парсим строку с ID колонок
                ids_str = project.selected_column_ids
                if ids_str:
                    return [int(id_str.strip()) for id_str in ids_str.split(',') if id_str.strip()]
        except Exception as e:
            print(f"⚠️ Ошибка получения колонок проекта {project_id}: {e}")

        # Возвращаем ID шаблонных колонок по умолчанию
        return [24, 25, 26, 27]  # К выполнению, В работе, Проверка, Готово

    def _get_columns_by_ids(self, column_ids: List[int]) -> List[Dict]:
        """Получает данные колонок по их ID"""
        try:
            from models.projects import BoardColumn
            from sqlalchemy import select

            db_session = self.service.crud.db_session
            stmt = select(BoardColumn).where(BoardColumn.id.in_(column_ids)).order_by(BoardColumn.position)
            columns = db_session.scalars(stmt).all()

            result = []
            for col in columns:
                result.append({
                    "id": col.id,
                    "name": col.name,
                    "color": col.color,
                    "position": col.position,
                    "is_done": col.is_done_column
                })
            return result
        except Exception as e:
            print(f"⚠️ Ошибка загрузки колонок по ID: {e}")
            return []

    def _rebuild_columns_ui(self, column_data: List[Dict]):
        """Перестраивает UI колонок"""
        # Очищаем существующий layout
        self.clear_layout(self.kanbanLayout)

        if not column_data:
            print("⚠️ Нет колонок для отображения")
            return

        # Горизонтальный скролл
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:horizontal {
                background: #f0f0f0;
                height: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: #c0c0c0;
                border-radius: 5px;
            }
        """)

        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setSpacing(16)
        columns_layout.setContentsMargins(10, 10, 10, 10)
        columns_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.columns.clear()
        self.column_widgets.clear()

        for col in sorted(column_data, key=lambda x: x["position"]):
            column_widget = KanbanColumn(col)
            self.columns[col["name"]] = column_widget
            self.column_widgets.append(column_widget)
            columns_layout.addWidget(column_widget)
            column_widget.task_dropped.connect(self._on_task_dropped)

        scroll_area.setWidget(columns_container)

        vertical_scroll = QScrollArea()
        vertical_scroll.setWidgetResizable(True)
        vertical_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        vertical_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        vertical_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 5px;
            }
        """)

        vertical_scroll.setWidget(scroll_area)
        self.kanbanLayout.addWidget(vertical_scroll)

        print(f"🔧 Перестроено {len(column_data)} колонок")

    def setup_board(self):
        """Создает колонки канбан-доски (стандартные, для всех проектов)"""
        self._rebuild_columns_ui(self.service.get_columns_for_board())

    def showEvent(self, event):
        """Показываем задачи только при первом отображении страницы"""
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            # Откладываем загрузку, чтобы UI успел отрисоваться
            QTimer.singleShot(10, self.load_tasks)

    def clear_layout(self, layout):
        """Очищает layout"""
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    def load_tasks(self):
        if self._is_loading or self._loaded:
            return

        self._is_loading = True

        try:
            self.clear_all_columns()
            tasks = self.service.get_tasks_for_board()

            # ОТКЛЮЧАЕМ ОБНОВЛЕНИЯ UI
            self.setUpdatesEnabled(False)

            for column in self.column_widgets:
                column.setUpdatesEnabled(False)

            for task in tasks:
                column_name = task.get("status")
                if not column_name or column_name not in self.columns:
                    continue

                task_card = TaskCard(task)
                self._connect_task_card_signals(task_card)

                column = self.columns[column_name]
                column.add_task(task_card)

            # ВКЛЮЧАЕМ ОБНОВЛЕНИЯ
            for column in self.column_widgets:
                column.setUpdatesEnabled(True)
            self.setUpdatesEnabled(True)

            self.updateGeometry()
            if self.parent():
                self.parent().updateGeometry()

            self.update_statistics()
            self._loaded = True

        except Exception as e:
            print(f"❌ Ошибка при загрузке задач: {e}")
            self.setUpdatesEnabled(True)
            for column in self.column_widgets:
                column.setUpdatesEnabled(True)
        finally:
            self._is_loading = False

    def clear_all_columns(self):
        """Очищает все колонки от карточек"""
        for column in self.column_widgets:
            column.clear_tasks()

    def _connect_task_card_signals(self, card):
        """Подключает сигналы карточки"""
        card.edit_requested.connect(self._on_edit_task)
        card.delete_requested.connect(self._on_delete_task)
        card.archive_requested.connect(self._on_archive_task)
        card.duplicate_requested.connect(self._on_duplicate_task)
        card.pause_requested.connect(self._on_pause_task)
        card.resume_requested.connect(self._on_resume_task)
        card.drag_started.connect(self._on_drag_started)
        card.progress_changed.connect(self._on_progress_changed)
        card.project_clicked.connect(self._on_project_clicked)

    def _on_project_clicked(self, project_id: int):
        """Обработчик клика по названию проекта"""
        print(f"📁 Запрошено открытие проекта {project_id}")
        self.open_project_requested.emit(project_id)

    def refresh_columns(self):
        """Обновить колонки (перезагрузить доску) с защитой от повторных вызовов"""
        if self._is_refreshing:
            print("⚠️ Обновление колонок уже выполняется, пропускаем")
            return

        self._is_refreshing = True

        try:
            print("🔄 ОБНОВЛЕНИЕ КОЛОНОК на странице Мои задачи")

            if hasattr(self.service.crud, '_column_cache'):
                self.service.crud._column_cache = None

            all_tasks = []
            for column in self.column_widgets:
                for card in column.get_tasks():
                    all_tasks.append(card.task_data)

            print(f"   - Сохранено задач: {len(all_tasks)}")

            self.setup_board()

            for task in all_tasks:
                task_card = TaskCard(task)
                self._connect_task_card_signals(task_card)

                column_name = task.get("status")
                if column_name in self.columns:
                    column = self.columns[column_name]
                    column.add_task(task_card)
                    print(f"   - Восстановлена задача '{task.get('title')}' в колонку '{column_name}'")
                else:
                    print(f"   - ⚠️ Колонка '{column_name}' не найдена для задачи '{task.get('title')}'")

            self.update_statistics()
            self.updateGeometry()
            if self.parent():
                self.parent().updateGeometry()

            print("✅ Обновление колонок на странице Мои задачи завершено")

        except Exception as e:
            print(f"❌ Ошибка при обновлении колонок: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._is_refreshing = False

    def _on_edit_task(self, task_id: int):
        """Редактирование задачи"""
        print(f"✏️ Редактирование задачи {task_id}")
        task = self.service.get_task_by_id(task_id)
        if task:
            from windows.other_tasks.task_dialog import TaskDialog
            dialog = TaskDialog(
                self,
                task_data=task,
                mode="edit",
                current_user=self.current_user
            )
            dialog.set_service(self.service)
            dialog.task_saved.connect(self._on_task_updated_from_edit)
            dialog.exec()

    def _on_task_updated_from_edit(self, task_id, form_data):
        """Обработчик обновления задачи из диалога"""
        print(f"🔄 Обновление задачи {task_id} из диалога")
        print(f"   Новые данные: {form_data}")

        updated_task = self.service.update_task(task_id, form_data)
        if updated_task:
            print(f"   Новый статус: {updated_task.get('status')}")
            self.update_task_card(updated_task)
            self.update_statistics()

    def _on_duplicate_task(self, task_id: int):
        """Дублирование задачи"""
        print(f"📋 Дублирование задачи {task_id}")
        new_task = self.service.duplicate_task(task_id)
        if new_task:
            task_card = TaskCard(new_task)
            self._connect_task_card_signals(task_card)
            column_name = new_task.get("status")
            if column_name in self.columns:
                self.columns[column_name].add_task(task_card)
            self.update_statistics()
            QMessageBox.information(self, "Успех", f"Задача '{new_task.get('title')}' дублирована")

    def _on_pause_task(self, task_id: int):
        """Поставить задачу на паузу"""
        print(f"⏸️ Пауза задачи {task_id}")
        updated_task = self.service.pause_task(task_id)
        if updated_task:
            self._update_task_card_data(task_id, updated_task)
            self.update_statistics()
            QMessageBox.information(self, "Пауза", f"Задача поставлена на паузу")

    def _on_resume_task(self, task_id: int):
        """Возобновить задачу"""
        print(f"▶️ Возобновление задачи {task_id}")
        updated_task = self.service.resume_task(task_id)
        if updated_task:
            self._update_task_card_data(task_id, updated_task)
            self.update_statistics()
            QMessageBox.information(self, "Возобновление", f"Задача возобновлена")

    def _update_task_card_data(self, task_id: int, updated_task: Dict):
        """Обновляет данные карточки без пересоздания виджета"""
        for column in self.column_widgets:
            for card in column.get_tasks():
                if card.task_id == task_id:
                    old_paused = card.task_data.get("is_paused", False)
                    new_paused = updated_task.get("is_paused", False)

                    for key, value in updated_task.items():
                        card.task_data[key] = value

                    if old_paused != new_paused:
                        card._update_pause_indicator()

                    new_progress = updated_task.get("progress_percent", 0)
                    if card.task_data.get("progress_percent") != new_progress:
                        card.overallProgress.blockSignals(True)
                        card.overallProgress.setValue(new_progress)
                        card.overallProgress.setFormat(f"Общий прогресс: {new_progress}%")
                        card.overallProgress.blockSignals(False)

                    print(f"✅ Данные задачи {task_id} обновлены в UI (пауза: {old_paused}->{new_paused})")
                    return

    def _on_archive_task(self, task_id: int):
        """Архивирование задачи"""
        reply = QMessageBox.question(
            self, "Архивирование",
            "Вы уверены, что хотите архивировать задачу?\nОна будет перемещена в архив.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.service.archive_task_by_id(task_id):
                self._remove_task_card_from_ui(task_id)
                self.update_statistics()
                QMessageBox.information(self, "Успех", "Задача архивирована")
                print(f"📦 Задача {task_id} архивирована и удалена из UI")

    def _on_delete_task(self, task_id: int):
        """Удаление задачи"""
        print(f"🗑️ Запрос на удаление задачи {task_id}")
        reply = QMessageBox.question(
            self, "Удаление",
            "Вы уверены, что хотите полностью удалить задачу?\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.service.delete_task_by_id(task_id)
                if success:
                    self._remove_task_card_from_ui(task_id)
                    self.update_statistics()
                    QMessageBox.information(self, "Успех", "Задача удалена")
                    print(f"✅ Задача {task_id} удалена")
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось удалить задачу")
            except Exception as e:
                print(f"❌ Ошибка при удалении: {e}")
                QMessageBox.critical(self, "Ошибка", f"Ошибка при удалении: {str(e)}")

    def _remove_task_card_from_ui(self, task_id: int):
        """Удаляет карточку задачи из UI"""
        for column in self.column_widgets:
            for card in column.get_tasks()[:]:
                if card.task_id == task_id:
                    column.remove_task(card)
                    card.deleteLater()
                    print(f"   ✅ Карточка задачи {task_id} удалена из UI")
                    return
        self.load_tasks()

    def _on_progress_changed(self, task_id: int, progress_percent: int):
        """Обработчик изменения прогресса задачи"""
        print(f"\n🔍 [DEBUG] _on_progress_changed: начало")
        print(f"   - task_id: {task_id}")
        print(f"   - progress_percent: {progress_percent}")

        try:
            updated_task = self.service.update_task_progress(task_id, progress_percent)

            if updated_task:
                for column in self.column_widgets:
                    for card in column.get_tasks():
                        if card.task_id == task_id:
                            card.task_data["progress_percent"] = progress_percent
                            card.overallProgress.blockSignals(True)
                            card.overallProgress.setValue(progress_percent)
                            card.overallProgress.setFormat(f"Общий прогресс: {progress_percent}%")
                            card.overallProgress.blockSignals(False)
                            print(f"✅ Прогресс задачи {task_id} обновлен до {progress_percent}% в UI")
                            break
                    else:
                        continue
                    break

                self.update_statistics()
                self.task_moved.emit()
            else:
                print(f"❌ Не удалось обновить прогресс задачи {task_id}")

        except Exception as e:
            print(f"❌ Ошибка при обновлении прогресса: {e}")
            import traceback
            traceback.print_exc()

        print(f"🔍 [DEBUG] _on_progress_changed: конец\n")

    def update_task_card(self, updated_task: Dict):
        """Обновляет карточку задачи в UI после перемещения"""
        task_id = updated_task.get("id")
        new_status = updated_task.get("status")

        print(f"\n🔍 [DEBUG] update_task_card: начало")
        print(f"   - task_id: {task_id}")
        print(f"   - new_status: {new_status}")

        found = False
        for column in self.column_widgets:
            for card in column.get_tasks()[:]:
                card_id = getattr(card, 'task_id', None)
                if card_id == task_id:
                    found = True
                    old_status = card.task_data.get("status")

                    if old_status != new_status:
                        print(f"     - статус изменился {old_status} -> {new_status}, перемещаем")
                        column.remove_task(card)
                        new_column = self.columns.get(new_status)
                        if new_column:
                            card.update_task_data(updated_task)
                            new_column.add_task(card)
                            print(f"     - перемещена в колонку '{new_status}'")
                        else:
                            print(f"     - ⚠️ колонка '{new_status}' не найдена")
                            card.update_task_data(updated_task)
                    else:
                        card.update_task_data(updated_task)
                    break
            if found:
                break

        if not found:
            print(f"   - ⚠️ карточка НЕ найдена в UI")
            self.load_tasks()

        self.updateGeometry()
        if self.parent():
            self.parent().updateGeometry()

    def update_statistics(self):
        """Обновляет статистику (Всего, В работе, Просрочено, Прогресс)"""
        all_tasks = []
        for column in self.column_widgets:
            for card in column.get_tasks():
                all_tasks.append(card.task_data)

        total = len(all_tasks)

        # Подсчёт "В работе" - задачи не в Done колонке
        in_progress = 0
        for task in all_tasks:
            status = task.get("status", "")
            # Считаем "В работе" все задачи, кроме тех, что в колонке "Готово"/"Done"
            # Можно также исключать завершённые задачи
            if status not in ["Готово", "Done", "Выполнено"] and not task.get("completed", False):
                in_progress += 1

        # Подсчёт просроченных задач (deadline < сегодня, не завершены)
        from datetime import datetime
        overdue = 0
        today = datetime.now().date()
        for task in all_tasks:
            deadline_str = task.get("deadline")
            completed = task.get("completed", False)
            if deadline_str and not completed:
                try:
                    deadline_date = datetime.strptime(deadline_str, "%d.%m.%Y").date()
                    if deadline_date < today:
                        overdue += 1
                except (ValueError, TypeError):
                    pass

        # Общий прогресс
        progress = self.service.get_progress_percent()

        # Обновляем UI
        if hasattr(self, 'totalTasksLabel'):
            self.totalTasksLabel.setText(f"📊 Всего задач: {total}")

        if hasattr(self, 'inProgressLabel'):
            self.inProgressLabel.setText(f"🔧 В работе: {in_progress}")

        if hasattr(self, 'overdueTasksLabel'):
            self.overdueTasksLabel.setText(f"⏰ Просрочено: {overdue}")

        if hasattr(self, 'overallProgress'):
            self.overallProgress.setValue(progress)

        # Обновляем счетчики в колонках
        for column in self.column_widgets:
            tasks_count = len(column.get_tasks())
            column.update_count(tasks_count)

    def _on_drag_started(self, task_data: dict):
        """Начало перетаскивания задачи"""
        print(f"🖱️ Начато перетаскивание задачи {task_data.get('id')}")

    def _on_filter_changed(self):
        """Изменение фильтра по приоритету"""
        self.filter_tasks()

    def filter_tasks(self):
        """Фильтрация задач по приоритету и проекту"""
        priority = self.priorityFilter.currentText()
        project_id = self.projectFilter.currentData()  # Получаем ID проекта

        # Собираем все задачи из колонок
        all_tasks = []
        for column in self.column_widgets:
            for card in column.get_tasks():
                all_tasks.append(card.task_data)

        filtered = all_tasks

        # Фильтр по приоритету
        if priority != "Все приоритеты":
            filtered = self.service.filter_tasks_by_priority(filtered, priority)

        # Фильтр по проекту
        if project_id:
            filtered = self.service.filter_tasks_by_project(filtered, project_id)

        filtered_ids = {t["id"] for t in filtered}

        # Применяем фильтр к карточкам
        for column in self.column_widgets:
            for card in column.get_tasks():
                if card.task_id in filtered_ids:
                    card.show()
                else:
                    card.hide()

    def _on_task_dropped(self, task_id: int, target_column_id: int):
        """Обработчик drop из KanbanColumn"""
        print(f"🔄 Получен drop: задача {task_id} → колонка ID={target_column_id}")

        target_column = None
        for col in self.column_widgets:
            if col.column_id == target_column_id:
                target_column = col
                break

        if not target_column:
            print("❌ Колонка не найдена по ID")
            return

        new_status = target_column.column_name
        print(f"🎯 Целевая колонка: '{new_status}' (ID={target_column_id})")

        task = self.service.get_task_by_id(task_id)
        if not task:
            print("❌ Задача не найдена в БД")
            return

        old_status = task.get("status")
        if old_status == new_status:
            print("ℹ️ Уже в этой колонке")
            return

        result = self.service.move_task_to_column(task_id, target_column_id)

        if result:
            self.update_task_card(result)
            self.update_statistics()
            self.task_moved.emit()

            from PyQt6.QtCore import QTimer
            QTimer.singleShot(150, self.load_tasks)

            print("✅ Задача успешно перемещена")
        else:
            print("❌ Не удалось переместить задачу")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        mime_data = event.mimeData()
        if not mime_data.hasFormat("application/x-task"):
            event.ignore()
            return

        data = self.service.deserialize_task_from_drag(
            mime_data.data("application/x-task")
        )
        if not data:
            event.ignore()
            return

        task_id = data.get("id")
        if not task_id:
            event.ignore()
            return

        global_pos = self.mapToGlobal(event.position().toPoint())

        target_column = None
        for column in self.column_widgets:
            column_pos = column.mapFromGlobal(global_pos)
            if column.rect().contains(column_pos):
                target_column = column
                break

        if not target_column:
            for column in self.column_widgets:
                if column.isVisible():
                    try:
                        if column.geometry().contains(
                                column.mapFromGlobal(global_pos)
                        ):
                            target_column = column
                            break
                    except:
                        continue

        if not target_column:
            print("⚠️ Не удалось определить целевую колонку")
            event.ignore()
            return

        new_status = target_column.column_name
        old_status = data.get("status")

        if old_status == new_status:
            event.ignore()
            return

        print(f"🔄 Перемещение задачи {task_id}: {old_status} -> {new_status}")

        result = self.service.move_task(task_id, new_status)
        if result:
            old_column_name, updated_task = result
            self.update_task_card(updated_task)
            self.update_statistics()
            self.task_moved.emit()
            event.acceptProposedAction()
        else:
            print("❌ Сервис не смог переместить задачу")
            event.ignore()