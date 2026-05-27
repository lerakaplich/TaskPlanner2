# windows/other_tasks/others_tasks_page.py

import os
from typing import Dict

from PyQt6 import uic
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (QWidget, QScrollArea,
                             QMessageBox, QSizePolicy, QHBoxLayout)

from database import get_tasks_session
from services.tasks_service.tasks_service import TasksService
from windows.other_tasks.others_task_card import OthersTaskCard
from windows.other_tasks.task_dialog import TaskDialog
from windows.widgets.kanban_column import KanbanColumn


class OthersTasksPage(QWidget):
    taskUpdated = pyqtSignal()
    open_project_requested = pyqtSignal(int)

    def __init__(self, parent=None, current_user=None, project_id=None, column_service=None):
        super().__init__(parent)

        self._is_loading = False
        self._is_refreshing = False

        self.current_user = current_user or {"id": 1, "last_name": "Копейкина", "first_name": "Виктория",
                                             "middle_name": "Анатольевна"}

        # Загружаем UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "other_tasks")
        uic.loadUi(os.path.join(ui_path, "others_tasks_page.ui"), self)

        self.columns = {}  # name -> widget
        self.column_widgets = []

        # Инициализация сервиса - РЕЖИМ "others" (чужие задачи)
        self.db_session = get_tasks_session()
        self.service = TasksService(
            db_session=self.db_session,
            current_user=self.current_user,
            mode="others",
            column_service=column_service  # <-- ПЕРЕДАЁМ
        )

        # Настройка UI
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.setup_kanban()
        self.load_tasks()
        self.connect_signals()

    def connect_signals(self):
        """Подключает сигналы UI."""
        self.priorityFilter.currentTextChanged.connect(self.filter_tasks)
        self.projectFilter.currentTextChanged.connect(self.filter_tasks)
        self.btnCreateTask.clicked.connect(self.create_new_task)

    def setup_kanban(self):
        """Создает колонки канбан-доски с горизонтальной и вертикальной прокруткой"""
        self.clear_layout(self.kanbanLayout)

        column_data = self.service.get_column_data()
        print(f"🔧 setup_kanban: получено {len(column_data)} колонок из сервиса")
        for col in column_data:
            print(f"   - {col['name']} (id={col.get('id')}, позиция={col.get('position')})")

        if not column_data:
            print("⚠️ Нет колонок для отображения")
            return

        # 👇 ВЕРТИКАЛЬНЫЙ СКРОЛЛ ДЛЯ ВСЕГО КОНТЕНТА
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        main_scroll.setStyleSheet("""
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
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
        """)

        # 👇 ГОРИЗОНТАЛЬНЫЙ СКРОЛЛ ДЛЯ КОЛОНОК
        horizontal_scroll = QScrollArea()
        horizontal_scroll.setWidgetResizable(True)
        horizontal_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        horizontal_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        horizontal_scroll.setStyleSheet("""
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
            QScrollBar::handle:horizontal:hover {
                background: #a0a0a0;
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
            print(f"📦 Создаем колонку: {col['name']}")
            column_widget = KanbanColumn(col)
            # НЕ УСТАНАВЛИВАЕМ политику размера
            self.columns[col["name"]] = column_widget
            self.column_widgets.append(column_widget)
            columns_layout.addWidget(column_widget)

        horizontal_scroll.setWidget(columns_container)
        main_scroll.setWidget(horizontal_scroll)
        self.kanbanLayout.addWidget(main_scroll)

        print(f"✅ Создано {len(self.column_widgets)} колонок")

    def clear_layout(self, layout):
        """Очищает layout."""
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    def load_tasks(self):
        """Загружает задачи (только чужие) с защитой от повторных вызовов"""
        if self._is_loading:
            print("⚠️ Загрузка чужих задач уже выполняется, пропускаем")
            return

        self._is_loading = True

        try:
            self.clear_all_columns()

            tasks = self.service.load_tasks()

            print(f"\n📊 Загрузка чужих задач: {len(tasks)}")
            for task in tasks:
                print(
                    f"  - {task.get('title')} (проект: {task.get('project_name')}, статус: {task.get('status')}, автор: {task.get('created_by_name')})")

            for task in tasks:
                self.add_task_card(task)

            self.update_statistics()

        except Exception as e:
            print(f"❌ Ошибка при загрузке задач: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._is_loading = False

    def add_task_card(self, task_data: Dict):
        """Добавляет карточку задачи в колонку."""
        print(f"📋 Добавляем задачу в колонку: {task_data.get('title')} -> {task_data.get('status')}")

        card = self.create_task_card(task_data)
        self.connect_task_card_signals(card)

        column_name = task_data.get("status")
        if column_name in self.columns:
            column = self.columns[column_name]
            column.add_task(card)

            # 👇 ПРИНУДИТЕЛЬНО ОБНОВЛЯЕМ ГЕОМЕТРИЮ КОЛОНКИ
            column.updateGeometry()
            # Обновляем геометрию родителя, чтобы пересчитать размеры
            if column.parent():
                column.parent().updateGeometry()

            print(f"  ✅ Добавлено в колонку '{column_name}'")
        else:
            print(f"  ❌ Колонка '{column_name}' не найдена!")

    def create_task_card(self, task_data: Dict) -> QWidget:
        """Создает карточку задачи."""
        # Определяем, является ли текущий пользователь создателем
        is_creator = (task_data.get('created_by') == self.current_user.get('id'))
        return OthersTaskCard(task_data, service=self.service, is_creator=is_creator)

    def connect_task_card_signals(self, card):
        """Подключает сигналы карточки."""
        card.editRequested.connect(self.edit_task)
        card.deleteRequested.connect(self.delete_task)
        card.archiveRequested.connect(self.archive_task)
        card.approveRequested.connect(self.approve_task)
        card.returnToWorkRequested.connect(self.return_to_work)
        card.moveToDoneColumn.connect(self.move_to_done)
        card.project_clicked.connect(self._on_project_clicked)  # <-- ДОБАВИТЬ

    def _on_project_clicked(self, project_id: int):
        """Обработчик клика по названию проекта"""
        print(f"📁 Запрошено открытие проекта {project_id} из чужих задач")
        self.open_project_requested.emit(project_id)

    def clear_all_columns(self):
        """Очищает все колонки от карточек."""
        for column in self.column_widgets:
            column.clear_tasks()

    def refresh_columns(self):
        """Обновляет колонки (после добавления/удаления) с защитой от повторных вызовов"""
        if self._is_refreshing:
            print("⚠️ Обновление колонок уже выполняется, пропускаем")
            return

        self._is_refreshing = True

        try:
            print("🔄 ОБНОВЛЕНИЕ КОЛОНОК на странице Чужие задачи")

            # ВАЖНО: Принудительно очищаем кэш колонок в сервисе
            if hasattr(self.service.crud, '_column_cache'):
                self.service.crud._column_cache = None

            # Пересоздаем доску с НОВЫМИ колонками
            self.setup_kanban()

            # ОЧИЩАЕМ ВСЕ КОЛОНКИ перед добавлением задач
            self.clear_all_columns()

            # ПЕРЕЗАГРУЖАЕМ ЗАДАЧИ заново из сервиса
            tasks = self.service.load_tasks()

            print(f"   - Загружено задач из БД: {len(tasks)}")

            for task in tasks:
                card = self.create_task_card(task)
                self.connect_task_card_signals(card)

                column_name = task.get("status")
                if column_name in self.columns:
                    column = self.columns[column_name]
                    column.add_task(card)
                    column.updateGeometry()
                    if column.parent():
                        column.parent().updateGeometry()
                    print(f"   - Добавлена задача '{task.get('title')}' в колонку '{column_name}'")
                else:
                    print(f"   - ⚠️ Колонка '{column_name}' не найдена для задачи '{task.get('title')}'")

            self.update_statistics()

            # Принудительно обновляем геометрию
            self.updateGeometry()
            if self.parent():
                self.parent().updateGeometry()

            print("✅ Обновление колонок на странице Чужие задачи завершено")

        except Exception as e:
            print(f"❌ Ошибка при обновлении колонок: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._is_refreshing = False

    def create_new_task(self):
        """Создает новую задачу."""
        print("\n=== ОТЛАДКА: Создание новой задачи ===")

        dialog = TaskDialog(self, mode="create", current_user=self.current_user)
        dialog.set_service(self.service)
        dialog.task_saved.connect(self.on_task_saved)

        dialog.exec()

    def edit_task(self, task_id: int):
        """Редактирует задачу."""
        task = self.service.get_task_by_id(task_id)
        if not task:
            return

        dialog = TaskDialog(self, task_data=task, mode="edit", current_user=self.current_user)
        dialog.set_service(self.service)
        dialog.task_saved.connect(self.on_task_updated)

        dialog.exec()

    def on_task_saved(self, task_id, form_data):
        """Обработчик создания задачи."""
        print("\n=== ОТЛАДКА: Создание задачи ===")
        print(f"Данные из диалога: {form_data}")

        try:
            new_task = self.service.create_task(form_data)
            print(f"✅ Задача создана: {new_task}")

            self.add_task_card(new_task)
            self.update_statistics()
            self.taskUpdated.emit()
            print("✅ Задача добавлена в UI")

        except Exception as e:
            print(f"❌ ОШИБКА при создании задачи: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать задачу: {str(e)}")

    def on_task_updated(self, task_id, form_data):
        """Обработчик обновления задачи."""
        print("\n=== ОТЛАДКА: Обновление задачи ===")
        print(f"ID задачи: {task_id}")
        print(f"Данные из диалога: {form_data}")

        try:
            updated_task = self.service.update_task(task_id, form_data)
            if updated_task:
                print(f"✅ Задача обновлена: {updated_task}")

                self.update_task_card(updated_task)
                self.update_statistics()
                self.taskUpdated.emit()
                print("✅ Задача обновлена в UI")
            else:
                print("❌ Задача не найдена")

        except Exception as e:
            print(f"❌ ОШИБКА при обновлении задачи: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить задачу: {str(e)}")

    def delete_task(self, task_id: int):
        """Удаляет задачу."""
        reply = QMessageBox.question(
            self, "Удаление",
            "Вы уверены, что хотите удалить задачу?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.service.delete_task(task_id)
            self.remove_task_card(task_id)
            self.update_statistics()
            self.taskUpdated.emit()

    def update_task_card(self, updated_task: Dict):
        """Обновляет карточку задачи."""
        for column in self.column_widgets:
            for card in column.get_tasks():
                if hasattr(card, 'task_data') and card.task_data["id"] == updated_task["id"]:
                    if card.task_data["status"] != updated_task["status"]:
                        # Перемещаем в другую колонку
                        column.remove_task(card)
                        new_column = self.columns.get(updated_task["status"])
                        if new_column:
                            new_column.add_task(card)
                    card.update_task_data(updated_task)
                    return

    def remove_task_card(self, task_id: int):
        """Удаляет карточку из UI."""
        for column in self.column_widgets:
            for card in column.get_tasks():
                if hasattr(card, 'task_data') and card.task_data["id"] == task_id:
                    column.remove_task(card)
                    return

    def move_to_done(self, task_id: int):
        """Перемещает в 'Выполнено'."""
        result = self.service.move_task(task_id, "Готово")
        if result:
            old_column, task = result
            self.update_task_card(task)
            self.update_statistics()
            self.taskUpdated.emit()

    def archive_task(self, task_id: int):
        print(f"Архивирование задачи {task_id}")

    def approve_task(self, task_id: int):
        print(f"Одобрение задачи {task_id}")

    def return_to_work(self, task_id: int):
        print(f"Возврат на доработку задачи {task_id}")

    def update_statistics(self):
        """Обновляет статистику."""
        stats = self.service.get_statistics_for_display()

        # Обновляем счетчики в колонках
        for column in self.column_widgets:
            tasks_count = len(column.get_tasks())
            column.update_count(tasks_count)

        if hasattr(self, 'totalTasksLabel'):
            self.totalTasksLabel.setText(f"📊 Всего задач: {stats['total']}")

        if hasattr(self, 'inProgressLabel'):
            self.inProgressLabel.setText(f"🔧 В работе: {stats['in_progress']}")

        if hasattr(self, 'overdueTasksLabel'):
            self.overdueTasksLabel.setText(f"⏰ Просрочено: {stats['overdue']}")

        if hasattr(self, 'overallProgress'):
            self.overallProgress.setValue(self.service.get_progress_percent())

    def filter_tasks(self):
        """Фильтрует задачи."""
        priority = self.priorityFilter.currentText()

        all_tasks = []
        for column in self.column_widgets:
            for card in column.get_tasks():
                all_tasks.append(card.task_data)

        filtered = self.service.filter_tasks_by_priority(all_tasks, priority)

        filtered_ids = {t["id"] for t in filtered}
        for column in self.column_widgets:
            for card in column.get_tasks():
                if card.task_data["id"] in filtered_ids:
                    card.show()
                else:
                    card.hide()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-task"):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        data = self.service.deserialize_task_from_drag(
            event.mimeData().data("application/x-task")
        )
        if not data:
            return

        target = self.get_target_column(event.position().toPoint())
        if not target:
            return

        result = self.service.move_task(data["id"], target.column_name)
        if result:
            old_column, task = result
            self.update_task_card(task)
            self.update_statistics()
            self.taskUpdated.emit()

    def get_target_column(self, pos: QPoint):
        for column in self.column_widgets:
            if column.geometry().contains(pos):
                return column
        return None

    def closeEvent(self, event):
        self.db_session.close()
        super().closeEvent(event)

    def move_task_card(self, task_id: int, from_column: str, to_column: str):
        """Перемещает карточку между колонками."""
        card = None
        source_column = None

        for col in self.column_widgets:
            layout = col.tasks_layout
            for i in range(layout.count()):
                w = layout.itemAt(i).widget()
                if w and hasattr(w, 'task_data') and w.task_data["id"] == task_id:
                    card = w
                    source_column = col
                    layout.takeAt(i)
                    break
            if card:
                break

        target_column = None
        for col in self.column_widgets:
            if col.column_name == to_column:
                target_column = col
                break

        if card and target_column:
            target_column.tasks_layout.insertWidget(
                target_column.tasks_layout.count() - 1,
                card
            )