# windows/projects/project_view_page.py

import os
from typing import Dict
from PyQt6.QtWidgets import QWidget, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6 import uic

from windows.other_tasks.others_task_card import OthersTaskCard
from windows.archive.archived_task_card import ArchivedTaskCard
from windows.shared.kanban_column import KanbanColumn
from services.tasks_service import TasksService
from database import get_tasks_session
from repositories.employee_repo import EmployeeRepo
from database import get_employees_session


class ProjectViewPage(QWidget):
    """Страница просмотра проекта с задачами и информацией о команде"""

    projectUpdated = pyqtSignal()

    def __init__(self, session=None, project_id=None, service=None, parent=None):
        super().__init__(parent)

        self.project_id = project_id
        self.project_service = service
        self.columns = {}
        self.column_widgets = []
        self.all_tasks = []

        # Загружаем UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "other_tasks")
        uic.loadUi(os.path.join(ui_path, "others_tasks_page.ui"), self)

        # Скрываем кнопку создания задачи
        if hasattr(self, 'btnCreateTask'):
            self.btnCreateTask.hide()

        # Получаем данные проекта
        if service and project_id:
            self.project_data = service.get_project_for_edit(project_id)
            if not self.project_data:
                self.project_data = self._get_default_project_data()
        else:
            self.project_data = self._get_default_project_data()

        # Проверяем, архивирован ли проект
        self.is_archived_project = self.project_data.is_archived if hasattr(self.project_data, 'is_archived') else False
        print(f"📋 Проект {self.project_id}, архивирован: {self.is_archived_project}")

        # Создаем сервис задач в режиме "all" (показываем все задачи проекта)
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

        self.service = TasksService(
            db_session=self.db_session,
            current_user=self.current_user,
            mode="all"
        )

        # Получаем колонки проекта из сохраненных ID
        self.project_columns = []
        if service and project_id:
            # Получаем ID сохраненных колонок
            column_ids = service.project_repo.get_selected_column_ids(project_id)
            if column_ids:
                from sqlalchemy import select
                from models.projects import BoardColumn

                stmt = select(BoardColumn).where(BoardColumn.id.in_(column_ids))
                columns = self.db_session.scalars(stmt).all()

                for col in columns:
                    self.project_columns.append({
                        'id': col.id,
                        'name': col.name,
                        'color': col.color,
                        'position': col.template_order if col.template_order is not None else col.position,
                        'is_done': col.is_done_column
                    })
                print(f"📋 Загружено колонок проекта: {len(self.project_columns)}")
            else:
                # Если нет сохраненных, берем все шаблонные
                from sqlalchemy import select
                from models.projects import BoardColumn

                stmt = select(BoardColumn).where(BoardColumn.is_template == True)
                columns = self.db_session.scalars(stmt).all()
                for col in columns:
                    self.project_columns.append({
                        'id': col.id,
                        'name': col.name,
                        'color': col.color,
                        'position': col.template_order if col.template_order is not None else col.position,
                        'is_done': col.is_done_column
                    })

        # Настройка UI
        self.setup_kanban()
        self.setup_project_ui()

        # Загружаем задачи ПОСЛЕ создания колонок
        self.load_tasks()

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
        """Загружает задачи ТОЛЬКО текущего проекта (включая архивированные для архивного проекта)"""
        if not self.project_service or not self.project_id:
            print("❌ Нет project_service или project_id")
            return

        # Получаем все задачи проекта через TaskRepo
        from repositories.task_repo import TaskRepo
        task_repo = TaskRepo(self.db_session)

        # Если проект архивирован - загружаем ВСЕ задачи (включая архивированные)
        # Если проект активен - загружаем только активные задачи
        include_archived = self.is_archived_project
        project_tasks = task_repo.get_by_project(
            self.project_id,
            load_column=True,
            include_archived=include_archived
        )

        print(
            f"\n📊 Загрузка задач для проекта {self.project_id} (архивирован={self.is_archived_project}): {len(project_tasks)} задач")
        print(f"Колонки проекта: {[c['name'] for c in self.project_columns]}")

        # Очищаем все колонки
        self.clear_all_columns()

        # Группируем задачи по именам колонок
        tasks_by_column = {}
        for task in project_tasks:
            column_name = task.column.name if task.column else "К выполнению"
            if column_name not in tasks_by_column:
                tasks_by_column[column_name] = []
            tasks_by_column[column_name].append(task)
            print(f"  - Задача: {task.title} -> колонка: {column_name}")

        # Добавляем задачи в соответствующие колонки
        for col_data in self.project_columns:
            column_name = col_data['name']
            col_widget = self.columns.get(column_name)
            if col_widget:
                tasks = tasks_by_column.get(column_name, [])
                for task in tasks:
                    task_dict = self._task_to_dict(task)
                    task_card = self.create_task_card(task_dict, task)
                    col_widget.add_task(task_card)
                    print(f"    ✅ Добавлена карточка задачи '{task.title}' в колонку '{column_name}'"
                          f" (архивирована={task.is_archived})")
                print(f"  Колонка '{column_name}': добавлено {len(tasks)} задач")

        self.update_statistics()

    def _task_to_dict(self, task):
        """Преобразует задачу в словарь для карточки с полным набором данных"""
        from models.schemas.tasks_dto import TaskPriority
        from datetime import datetime

        # Получаем имя исполнителя
        assignee_name = None
        if task.assigned_to:
            emp_session = get_employees_session()
            if emp_session:
                emp_repo = EmployeeRepo(emp_session)
                assignee_name = emp_repo.get_full_name(task.assigned_to)
                emp_session.close()

        # Получаем имя автора
        author_name = None
        if task.created_by:
            emp_session = get_employees_session()
            if emp_session:
                emp_repo = EmployeeRepo(emp_session)
                author_name = emp_repo.get_full_name(task.created_by)
                emp_session.close()

        priority_map = {
            TaskPriority.low: ("Низкий", "#4CAF50"),
            TaskPriority.medium: ("Средний", "#FFA726"),
            TaskPriority.high: ("Высокий", "#D22730"),
            TaskPriority.critical: ("Критический", "#D22730")
        }

        priority_text, priority_color = priority_map.get(
            task.priority,
            ("Средний", "#FFA726")
        )

        deadline_text = ""
        deadline_color = "#666"
        deadline_obj = None
        if task.deadline:
            deadline_text = task.deadline.strftime("%d.%m.%Y")
            deadline_obj = task.deadline
            if task.deadline.date() < datetime.now().date():
                deadline_color = "#D22730"

        # Форматируем даты
        created_text = task.created_at.strftime("%d.%m.%Y") if task.created_at else ""
        updated_text = task.updated_at.strftime("%d.%m.%Y") if task.updated_at else ""

        # Преобразуем теги в строки
        tags = []
        if hasattr(task, 'tags') and task.tags:
            for tag_obj in task.tags:
                if hasattr(tag_obj, 'name'):
                    tags.append(tag_obj.name)
                elif isinstance(tag_obj, str):
                    tags.append(tag_obj)
                else:
                    tags.append(str(tag_obj))

        # Получаем дату архивации
        archived_at = ""
        if task.is_archived and task.archived_at:
            archived_at = task.archived_at.strftime("%d.%m.%Y")

        return {
            "id": task.id,
            "title": task.title,
            "description": task.description or "",
            "status": task.column.name if task.column else None,
            "column_id": task.column_id,
            "priority": task.priority.value,
            "priority_text": priority_text,
            "priority_color": priority_color,
            "deadline": deadline_text,
            "deadline_obj": deadline_obj,
            "deadline_color": deadline_color,
            "assignee_name": assignee_name or "Не назначен",
            "assigned_to": task.assigned_to,
            "created_by": task.created_by,
            "author_text": author_name or "Неизвестен",
            "created_text": created_text,
            "updated_text": updated_text,
            "executor_text": assignee_name or "Не назначен",
            "completed": task.is_archived if hasattr(task, 'is_archived') else False,
            "difficulty": task.difficulty if hasattr(task, 'difficulty') else 0,
            "tags": tags,
            "project_id": task.project_id,
            "project_name": self.project_data.name if hasattr(self.project_data, 'name') else str(self.project_id),
            "is_archived": task.is_archived if hasattr(task, 'is_archived') else False,
            "archived_at": archived_at
        }

    def create_task_card(self, task_data: Dict, task=None) -> QWidget:
        """Создает карточку задачи"""
        is_archived = task_data.get('is_archived', False)

        # Если задача архивирована или проект архивирован - используем ArchivedTaskCard
        if is_archived or self.is_archived_project:
            card = ArchivedTaskCard(task_data, self)
            # Подключаем сигналы для архивированной карточки
            card.restore_requested.connect(self._on_restore_task)
            card.delete_permanently_requested.connect(self._on_delete_task_permanently)
            return card
        else:
            # Обычная карточка для активных задач
            is_creator = (task_data.get('created_by') == self.current_user_id)
            card = OthersTaskCard(task_data, service=self.service, is_creator=is_creator)
            card.editRequested.connect(self._on_edit_task)
            card.deleteRequested.connect(self._on_delete_task)
            card.archiveRequested.connect(self._on_archive_task)
            card.moveToDoneColumn.connect(self._on_move_to_done)
            return card

    def _on_restore_task(self, task_id: int):
        """Восстановление задачи из архива"""
        if self.project_service:
            # Восстанавливаем задачу через сервис
            from repositories.task_repo import TaskRepo
            task_repo = TaskRepo(self.db_session)
            task = task_repo.get_by_id(task_id)
            if task:
                task.is_archived = False
                task.archived_at = None
                self.db_session.commit()
                # Перезагружаем страницу
                self.load_tasks()
                print(f"✅ Задача {task_id} восстановлена")

    def _on_delete_task_permanently(self, task_id: int):
        """Полное удаление задачи"""
        reply = QMessageBox.question(
            self,
            "Удаление задачи",
            "Вы уверены, что хотите удалить задачу навсегда?\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            from repositories.task_repo import TaskRepo
            task_repo = TaskRepo(self.db_session)
            task_repo.hard_delete(task_id)
            self.db_session.commit()
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
        # Добавляем информацию о проекте в верхнюю панель
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
            project_name = self.project_data.name if hasattr(self.project_data, 'name') else self.project_data.get(
                'name', '')
            title_label = QLabel(f"📋 Проект: {project_name}")
            title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1B232A;")
            layout.addWidget(title_label)

            # Статус (если проект архивирован, показываем архивный статус)
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

            # Кнопка возврата к проектам
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

            # Вставляем в начало controlPanel
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
        # Очищаем существующий kanbanLayout
        self.clear_layout(self.kanbanLayout)

        column_data = self.get_column_data()
        if not column_data:
            print(f"⚠️ Нет колонок для проекта {self.project_id}")
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

        # Создаем горизонтальный скролл
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
            print(f"📦 Создаем колонку: {col['name']}")
            column_widget = KanbanColumn(col)
            self.columns[col['name']] = column_widget
            self.column_widgets.append(column_widget)
            columns_layout.addWidget(column_widget)

        columns_layout.addStretch()
        horizontal_scroll.setWidget(columns_container)

        # Добавляем в основной layout с вертикальным скроллом
        main_layout.addWidget(horizontal_scroll)

        # Вертикальный скролл для всего
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

        print(f"✅ Создано {len(self.column_widgets)} колонок для проекта {self.project_id}")

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