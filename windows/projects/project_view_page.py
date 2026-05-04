# windows/projects/project_view_page.py

import os
from typing import Dict
from PyQt6.QtWidgets import QWidget, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6 import uic

from windows.other_tasks.others_task_card import OthersTaskCard
from windows.shared.kanban_column import KanbanColumn
from services.tasks_service import TasksService
from database import get_tasks_session


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

        # Создаем сервис задач в режиме "all" (показываем все задачи проекта)
        self.db_session = session or get_tasks_session()
        temp_user = {"id": 1, "last_name": "Копейкина", "first_name": "Виктория"}
        self.service = TasksService(
            db_session=self.db_session,
            current_user=temp_user,
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
        self.load_tasks()
        self.setup_project_ui()

    def _get_default_project_data(self):
        """Возвращает данные проекта по умолчанию"""
        return {
            'id': self.project_id or 1,
            'name': f'Проект #{self.project_id or 1}',
            'description': 'Описание проекта'
        }

    def get_column_data(self):
        """Возвращает колонки текущего проекта"""
        return self.project_columns

    def load_tasks(self):
        """Загружает задачи ТОЛЬКО текущего проекта"""
        if not self.project_service or not self.project_id:
            return

        # Получаем все задачи проекта через TaskRepo
        from repositories.task_repo import TaskRepo
        task_repo = TaskRepo(self.db_session)
        project_tasks = task_repo.get_by_project(self.project_id, load_column=True)

        print(f"\n📊 Загрузка задач для проекта {self.project_id}: {len(project_tasks)} задач")
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
                    task_card = self.create_task_card(task_dict)
                    self.connect_task_card_signals(task_card)
                    col_widget.add_task(task_card)
                print(f"  Колонка '{column_name}': добавлено {len(tasks)} задач")

        self.update_statistics()

    def _task_to_dict(self, task):
        """Преобразует задачу в словарь для карточки"""
        from models.schemas.tasks_dto import TaskPriority
        from repositories.employee_repo import EmployeeRepo
        from database import get_employees_session  # ← ДОБАВИТЬ

        # Получаем имя исполнителя - используем ОТДЕЛЬНУЮ сессию для employees
        assignee_name = None
        if task.assigned_to:
            emp_session = get_employees_session()  # ← ПРАВИЛЬНАЯ СЕССИЯ ДЛЯ EMPLOYEES
            if emp_session:
                emp_repo = EmployeeRepo(emp_session)
                assignee_name = emp_repo.get_full_name(task.assigned_to)
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
        if task.deadline:
            deadline_text = task.deadline.strftime("%d.%m.%Y")
            from datetime import datetime
            if task.deadline.date() < datetime.now().date():
                deadline_color = "#D22730"

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
            "deadline_color": deadline_color,
            "assignee_name": assignee_name or "Не назначен",
            "created_by": task.created_by,
            "completed": task.is_archived if hasattr(task, 'is_archived') else False,
            "tags": []
        }

    def create_task_card(self, task_data: Dict) -> QWidget:
        """Создает карточку задачи"""
        # Проверяем, является ли текущий пользователь создателем
        is_creator = (task_data.get('created_by') == self.current_user.get('id')) if hasattr(self,
                                                                                             'current_user') else False
        return OthersTaskCard(task_data, service=self.service, is_creator=is_creator)

    def connect_task_card_signals(self, card):
        """Подключает сигналы карточки"""
        # Можно добавить обработчики при необходимости
        pass

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
            title_label = QLabel(
                f"📋 Проект: {self.project_data.name if hasattr(self.project_data, 'name') else self.project_data.get('name', '')}"
            )
            title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1B232A;")
            layout.addWidget(title_label)

            # Статус
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
        self.clear_layout(self.kanbanLayout)

        column_data = self.get_column_data()
        if not column_data:
            print(f"⚠️ Нет колонок для проекта {self.project_id}")
            empty_label = QLabel("Нет настроенных колонок для этого проекта")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #999; font-size: 14px; padding: 40px;")
            self.kanbanLayout.addWidget(empty_label)
            return

        # Вертикальный скролл
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
        """)

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
            print(f"📦 Создаем колонку: {col['name']}")
            column_widget = KanbanColumn(col)
            self.columns[col['name']] = column_widget
            self.column_widgets.append(column_widget)
            columns_layout.addWidget(column_widget)

        columns_layout.addStretch()
        horizontal_scroll.setWidget(columns_container)
        main_scroll.setWidget(horizontal_scroll)
        self.kanbanLayout.addWidget(main_scroll)

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
                    self.clear_layout(item.layout())