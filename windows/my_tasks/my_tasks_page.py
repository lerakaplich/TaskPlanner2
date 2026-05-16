# windows/my_tasks/my_tasks_page.py

import os
from typing import Dict

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QScrollArea, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent

from services.tasks_service.tasks_service import TasksService
from windows.my_tasks.task_card import TaskCard
from windows.widgets.kanban_column import KanbanColumn

class MyTasksPage(QWidget):
    """Страница Мои задачи (только UI слой)"""

    task_moved = pyqtSignal()

    def __init__(self, db_session, current_user, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "my_tasks"
        )
        uic.loadUi(os.path.join(ui_path, "my_tasks_page.ui"), self)

        # Сервис - режим "my" (только мои задачи)
        self.service = TasksService(
            db_session=db_session,
            current_user=current_user,
            mode="my"
        )

        self.columns = {}
        self.column_widgets = []
        self.current_user = current_user

        self.setup_board()
        self.load_tasks()

        # Drag & Drop
        self.setAcceptDrops(True)

        # Фильтры
        self.priorityFilter.currentTextChanged.connect(self._on_filter_changed)

    # ==========================================================
    # Настройка UI
    # ==========================================================

    def setup_board(self):
        """Создает колонки канбан-доски"""
        self.clear_layout(self.kanbanLayout)

        column_data = self.service.get_columns_for_board()
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

        self.columns.clear()
        self.column_widgets.clear()

        for col in sorted(column_data, key=lambda x: x["position"]):
            print(f"📦 Создаем колонку: {col['name']}")
            column_widget = KanbanColumn(col)
            self.columns[col["name"]] = column_widget
            self.column_widgets.append(column_widget)
            columns_layout.addWidget(column_widget)

            # === ПОДКЛЮЧЕНИЕ СИГНАЛА ===
            column_widget.task_dropped.connect(self._on_task_dropped)

        columns_layout.addStretch()
        scroll_area.setWidget(columns_container)

        # Вертикальный скролл
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

        print(f"✅ Создано {len(self.column_widgets)} колонок")

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

    # ==========================================================
    # Загрузка и отображение задач
    # ==========================================================

    def load_tasks(self):
        """Загружает и отображает задачи"""
        tasks = self.service.get_tasks_for_board()

        print(f"\n📊 Загрузка моих задач: {len(tasks)}")
        for task in tasks:
            print(f"  - {task.get('title')} (проект: {task.get('project_name')}, статус: {task.get('status')})")

        self.clear_all_columns()

        for task in tasks:
            task_card = TaskCard(task)
            self._connect_task_card_signals(task_card)

            column_name = task.get("status")
            if column_name in self.columns:
                column = self.columns[column_name]
                column.add_task(task_card)
                print(f"  ✅ Добавлена задача '{task.get('title')}' в колонку '{column_name}'")
            else:
                print(f"  ⚠️ Колонка '{column_name}' не найдена")

        self.update_statistics()

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
        card.drag_started.connect(self._on_drag_started)
        # Добавляем сигнал изменения прогресса
        card.progress_changed.connect(self._on_progress_changed)

    def _on_progress_changed(self, task_id: int, progress_percent: int):
        """Обработчик изменения прогресса задачи"""
        print(f"\n🔍 [DEBUG] _on_progress_changed: начало")
        print(f"   - task_id: {task_id}")
        print(f"   - progress_percent: {progress_percent}")

        try:
            # Обновляем прогресс через сервис
            updated_task = self.service.update_task_progress(task_id, progress_percent)

            if updated_task:
                # НЕ обновляем карточку - просто обновляем данные в task_data карточки
                # ищем карточку и обновляем её данные без перерисовки
                for column in self.column_widgets:
                    for card in column.get_tasks():
                        if card.task_id == task_id:
                            # Обновляем только прогресс в данных, без вызова fill_ui
                            card.task_data["progress_percent"] = progress_percent
                            # Обновляем отображение прогресс-бара
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

        # Ищем карточку во всех колонках
        found = False
        for column in self.column_widgets:
            print(f"   - проверяем колонку: {column.column_name}")
            for card in column.get_tasks()[:]:  # копия списка
                card_id = getattr(card, 'task_id', None)
                print(f"     - карточка в колонке: task_id={card_id}, card={card}")
                if card_id == task_id:
                    found = True
                    old_status = card.task_data.get("status")
                    print(f"     - НАЙДЕНА! old_status={old_status}")

                    if old_status != new_status:
                        print(f"     - статус изменился, перемещаем")
                        column.remove_task(card)
                        new_column = self.columns.get(new_status)
                        if new_column:
                            new_column.add_task(card)
                            print(f"     - перемещена в колонку '{new_status}'")
                        else:
                            print(f"     - ⚠️ колонка '{new_status}' не найдена")

                    print(f"     - обновляем данные карточки")
                    card.update_task_data(updated_task)
                    print(f"     - карточка обновлена, isVisible={card.isVisible()}")
                    break
            if found:
                break

        if not found:
            print(f"   - ⚠️ карточка НЕ найдена в UI")
            print(f"   - перезагружаем все задачи")
            self.load_tasks()
        else:
            print(f"   - карточка найдена и обновлена")

        print(f"🔍 [DEBUG] update_task_card: конец\n")

    def update_statistics(self):
        """Обновляет статистику"""
        stats = self.service.get_statistics_for_display()

        for column in self.column_widgets:
            tasks_in_column = len(column.get_tasks())
            column.update_count(tasks_in_column)

        if hasattr(self, 'totalTasksLabel'):
            self.totalTasksLabel.setText(f"📊 Всего задач: {stats['total']}")

        if hasattr(self, 'completedTasksLabel'):
            self.completedTasksLabel.setText(f"✅ Выполнено: {stats['done']}")

        if hasattr(self, 'overdueTasksLabel'):
            self.overdueTasksLabel.setText(f"⏰ Просрочено: {stats['overdue']}")

        if hasattr(self, 'overallProgress'):
            self.overallProgress.setValue(self.service.get_progress_percent())

    # ==========================================================
    # Обработчики действий (вызывают сервис)
    # ==========================================================

    def _on_edit_task(self, task_id: int):
        """Редактирование задачи"""
        print(f"✏️ Редактирование задачи {task_id}")
        # TODO: открыть диалог редактирования

    def _on_delete_task(self, task_id: int):
        """Удаление задачи"""
        reply = QMessageBox.question(
            self, "Удаление",
            "Вы уверены, что хотите удалить задачу?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.service.delete_task_by_id(task_id):
                self.load_tasks()
                QMessageBox.information(self, "Успех", "Задача удалена")

    def _on_archive_task(self, task_id: int):
        """Архивирование задачи"""
        if self.service.archive_task_by_id(task_id):
            self.load_tasks()
            QMessageBox.information(self, "Успех", "Задача архивирована")

    def _on_duplicate_task(self, task_id: int):
        """Дублирование задачи"""
        new_task = self.service.duplicate_task(task_id)
        if new_task:
            self.load_tasks()
            QMessageBox.information(self, "Успех", "Задача дублирована")

    def _on_drag_started(self, task_data: dict):
        """Начало перетаскивания задачи"""
        print(f"🖱️ Начато перетаскивание задачи {task_data.get('id')}")

    def _on_filter_changed(self):
        """Изменение фильтра"""
        self.filter_tasks()

    def filter_tasks(self):
        """Фильтрация задач по приоритету"""
        priority = self.priorityFilter.currentText()

        all_tasks = []
        for column in self.column_widgets:
            for card in column.get_tasks():
                all_tasks.append(card.task_data)

        filtered = self.service.filter_tasks_by_priority(all_tasks, priority)

        filtered_ids = {t["id"] for t in filtered}
        for column in self.column_widgets:
            for card in column.get_tasks():
                if card.task_id in filtered_ids:
                    card.show()
                else:
                    card.hide()

    # ==========================================================
    # Drag & Drop — ИСПРАВЛЕННАЯ ВЕРСИЯ
    # ==========================================================

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

            # === КРИТИЧНАЯ СТРАХОВКА ===
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(150, self.load_tasks)  # перезагружаем UI через 150мс

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

        # === КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: используем global позицию ===
        global_pos = self.mapToGlobal(event.position().toPoint())

        target_column = None
        for column in self.column_widgets:
            # Преобразуем глобальную позицию в координаты колонки
            column_pos = column.mapFromGlobal(global_pos)
            if column.rect().contains(column_pos):
                target_column = column
                break

        if not target_column:
            # Попробуем найти через viewport scroll area (дополнительная страховка)
            for column in self.column_widgets:
                if column.isVisible():
                    # Проверяем через parent hierarchy
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