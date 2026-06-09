# windows/projects/project_view_page.py

import os
from typing import Dict
from PyQt6.QtWidgets import QWidget, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6 import uic

from windows.other_tasks.others_task_card import OthersTaskCard
from windows.archive.archived_task_card import ArchivedTaskCard
from windows.widgets.kanban_column import KanbanColumn
from services.tasks_service.tasks_service import TasksService
from database import get_tasks_session


class ProjectViewPage(QWidget):
    """Страница просмотра проекта с задачами - только UI, логика в сервисе"""

    projectUpdated = pyqtSignal()

    def __init__(self, session=None, project_id=None, service=None, parent=None):
        super().__init__(parent)

        self.project_id = project_id
        self.project_service = service
        self.columns = {}
        self.column_widgets = []
        self.all_tasks = []

        # Загружаем UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "projects")
        uic.loadUi(os.path.join(ui_path, "project_page.ui"), self)



        # Получаем данные проекта через сервис
        if service and project_id:
            self.project_data = service.get_project_for_edit(project_id)
            if not self.project_data:
                self.project_data = self._get_default_project_data()
        else:
            self.project_data = self._get_default_project_data()

        # Проверяем, архивирован ли проект
        self.is_archived_project = self.project_data.is_archived if hasattr(self.project_data, 'is_archived') else False

        # Создаем сервис задач
        self.db_session = session or get_tasks_session()

        # Получаем текущего пользователя из parent (MainWindow)
        self.current_user = None
        self.current_user_id = None
        if parent and hasattr(parent, 'current_user'):
            self.current_user = parent.current_user
            self.current_user_id = parent.current_user_id
        else:
            self.current_user = {"id": 1, "last_name": "Копейкина", "first_name": "Виктория"}
            self.current_user_id = 1

        self.tasks_service = TasksService(
            db_session=self.db_session,
            current_user=self.current_user,
            mode="all"
        )

        # Получаем колонки проекта через сервис
        self.project_columns = []
        if service and project_id:
            self.project_columns = service.get_project_columns(project_id)

        # Настройка UI
        self.setup_kanban()

        # Загружаем задачи
        self.load_tasks()

    def showEvent(self, event):
        """Срабатывает при каждом показе страницы"""
        super().showEvent(event)
        QTimer.singleShot(100, self.load_tasks)

    def _get_default_project_data(self):
        """Возвращает данные проекта по умолчанию"""
        class ProjectData:
            def __init__(self, id, name):
                self.id = id
                self.name = name
                self.is_archived = False

        return ProjectData(self.project_id or 1, f'Проект #{self.project_id or 1}')

    def get_column_data(self):
        """Возвращает колонки текущего проекта"""
        return self.project_columns

    def load_tasks(self):
        """Загружает задачи через сервис"""
        if not self.project_service or not self.project_id:
            print("❌ Нет project_service или project_id")
            return

        include_archived = self.is_archived_project
        tasks = self.project_service.get_project_tasks_for_view(self.project_id, include_archived)

        print(f"\n📊 Загрузка задач для проекта {self.project_id}: {len(tasks)} задач")

        # Очищаем все колонки
        self.clear_all_columns()

        # Группируем задачи по именам колонок
        tasks_by_column = {}
        for task in tasks:
            column_name = task.get('status', "К выполнению")
            if column_name not in tasks_by_column:
                tasks_by_column[column_name] = []
            tasks_by_column[column_name].append(task)

        # Добавляем задачи в соответствующие колонки
        for col_data in self.project_columns:
            column_name = col_data['name']
            col_widget = self.columns.get(column_name)
            if col_widget:
                column_tasks = tasks_by_column.get(column_name, [])
                for task_dict in column_tasks:
                    task_card = self.create_task_card(task_dict)
                    col_widget.add_task(task_card)
                print(f"  Колонка '{column_name}': добавлено {len(column_tasks)} задач")

        self.update_statistics()

    def create_task_card(self, task_data: Dict):
        """Создает карточку задачи"""
        is_archived = task_data.get('is_archived', False)

        if is_archived or self.is_archived_project:
            card = ArchivedTaskCard(task_data, self)
            card.restore_requested.connect(self._on_restore_task)
            card.delete_permanently_requested.connect(self._on_delete_task_permanently)
            return card
        else:
            is_creator = (task_data.get('created_by') == self.current_user_id)
            card = OthersTaskCard(task_data, service=self.tasks_service, is_creator=is_creator)
            card.editRequested.connect(self._on_edit_task)
            card.deleteRequested.connect(self._on_delete_task)
            card.archiveRequested.connect(self._on_archive_task)
            card.moveToDoneColumn.connect(self._on_move_to_done)
            return card

    def _on_restore_task(self, task_id: int):
        """Восстановление задачи из архива через сервис"""
        if self.project_service and self.project_service.restore_task(task_id):
            self.load_tasks()
            print(f"✅ Задача {task_id} восстановлена")

    def _on_delete_task_permanently(self, task_id: int):
        """Полное удаление задачи через сервис"""
        reply = QMessageBox.question(
            self,
            "Удаление задачи",
            "Вы уверены, что хотите удалить задачу навсегда?\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.project_service and self.project_service.delete_task_permanently(task_id):
                self.load_tasks()
                print(f"🗑️ Задача {task_id} удалена навсегда")

    def _on_edit_task(self, task_id: int):
        """Обработчик редактирования задачи"""
        print(f"✏️ Редактирование задачи {task_id}")

    def _on_delete_task(self, task_id: int):
        """Обработчик удаления задачи"""
        print(f"🗑️ Удаление задачи {task_id}")

    def _on_archive_task(self, task_id: int):
        """Обработчик архивации задачи"""
        print(f"📦 Архивация задачи {task_id}")

    def _on_move_to_done(self, task_id: int):
        """Обработчик перемещения задачи в колонку Готово"""
        print(f"✅ Задача {task_id} отмечена как выполненная")

    def clear_all_columns(self):
        """Очищает все колонки от карточек"""
        for column in self.column_widgets:
            column.clear_tasks()

    def update_statistics(self):
        """Обновляет статистику"""
        total = 0
        for column in self.column_widgets:
            tasks_count = len(column.get_tasks())
            column.update_count(tasks_count)
            total += tasks_count

        if hasattr(self, 'totalTasksLabel'):
            self.totalTasksLabel.setText(f"📊 Всего задач: {total}")

    def setup_project_ui(self):
        """Настройка UI для страницы проекта"""
        if hasattr(self, 'controlPanel') and hasattr(self, 'controlLayout'):
            project_info = QFrame()
            project_info.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 12px;
                    border: 1px solid #E0E0E0;
                    padding: 10px;
                }
            """)

            layout = QHBoxLayout(project_info)
            layout.setContentsMargins(15, 10, 15, 10)

            # Название проекта
            project_name = self.project_data.name if hasattr(self.project_data, 'name') else ''
            title_label = QLabel(f"📋 Проект: {project_name}")
            title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1B232A;")
            layout.addWidget(title_label)

            # Статус
            if self.is_archived_project:
                status_label = QLabel("В архиве")
                status_label.setStyleSheet("""
                    font-size: 12px;
                    font-weight: bold;
                    color: white;
                    background-color: #999999;
                    border-radius: 10px;
                    padding: 4px 12px;
                """)
            else:
                status_label = QLabel("Активен")
                status_label.setStyleSheet("""
                    font-size: 12px;
                    font-weight: bold;
                    color: white;
                    background-color: #4CAF50;
                    border-radius: 10px;
                    padding: 4px 12px;
                """)
            layout.addWidget(status_label)

            # Кнопка возврата
            back_btn = QPushButton("← К проектам")
            back_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #E0E0E0;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            back_btn.clicked.connect(self.go_back_to_projects)
            layout.addWidget(back_btn)

            layout.addStretch()
            self.controlLayout.insertWidget(0, project_info)

    def go_back_to_projects(self):
        """Возврат к списку проектов"""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'contentStack') and hasattr(parent, 'switch_page'):
                parent.switch_page(0)
                break
            parent = parent.parent()

    def setup_kanban(self):
        """Создает колонки канбан-доски"""
        self.clear_layout(self.kanbanLayout)

        column_data = self.get_column_data()
        if not column_data:
            empty_label = QLabel("Нет настроенных колонок для этого проекта")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #999; font-size: 14px; padding: 40px;")
            self.kanbanLayout.addWidget(empty_label)
            return

        # Основной контейнер с горизонтальным скроллом
        scroll_widget = QWidget()
        main_layout = QHBoxLayout(scroll_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Горизонтальный скролл
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
        """)

        # Контейнер для колонок
        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setSpacing(16)
        columns_layout.setContentsMargins(10, 10, 10, 10)

        self.columns.clear()
        self.column_widgets.clear()

        for col in sorted(column_data, key=lambda x: x['position']):
            column_widget = KanbanColumn(col)
            self.columns[col['name']] = column_widget
            self.column_widgets.append(column_widget)
            columns_layout.addWidget(column_widget)

        columns_layout.addStretch()
        horizontal_scroll.setWidget(columns_container)
        main_layout.addWidget(horizontal_scroll)

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
        vertical_scroll.setWidget(scroll_widget)
        self.kanbanLayout.addWidget(vertical_scroll)

    def clear_layout(self, layout):
        """Очищает layout"""
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                else:
                    if item.layout():
                        self.clear_layout(item.layout())