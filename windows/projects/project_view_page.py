# windows/projects/project_view_page.py

import os
from typing import Dict

from PyQt6 import uic
from PyQt6.QtWidgets import (QListWidgetItem, QFrame, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QListWidget, QProgressBar,
                             QLineEdit, QWidget, QMessageBox)
from PyQt6.QtCore import Qt, QDate, pyqtSignal

from windows.other_tasks.others_tasks_page import OthersTasksPage
from windows.other_tasks.others_task_card import OthersTaskCard
from windows.other_tasks.task_dialog import TaskDialog


class ProjectViewPage(OthersTasksPage):
    """Страница просмотра проекта с задачами и информацией о команде"""

    projectUpdated = pyqtSignal()  # Сигнал при обновлении проекта

    def __init__(self, session=None, project_id=None, service=None, parent=None):
        """
        Инициализация страницы проекта

        Args:
            session: сессия БД
            project_id: ID проекта
            service: сервис проектов
            parent: родительский виджет
        """
        self.project_id = project_id
        self.project_service = service

        # Получаем данные проекта из сервиса
        if service and project_id:
            self.project_data = service.get_project_for_edit(project_id)
            if not self.project_data:
                self.project_data = self.get_default_project_data()
        else:
            self.project_data = self.get_default_project_data()

        # Создаем временного пользователя для OthersTasksPage
        temp_user = {"id": 1, "last_name": "", "first_name": ""}

        # Вызываем родительский конструктор
        super().__init__(parent=parent, current_user=temp_user, project_id=project_id or 2)

        # Перенастраиваем UI для проекта
        self.setup_project_ui()

        # Загружаем задачи проекта
        self.load_project_tasks()

    def get_default_project_data(self):
        """Возвращает данные проекта по умолчанию"""
        return {
            'id': self.project_id or 1,
            'name': f'Проект #{self.project_id or 1}',
            'description': 'Описание проекта',
            'status': 'Активен',
            'start_date': '01.01.2026',
            'progress': 0
        }

    def setup_project_ui(self):
        """Настройка UI для страницы проекта"""
        # Скрываем стандартные элементы OthersTasksPage
        if hasattr(self, 'btnCreateTask'):
            self.btnCreateTask.hide()

        # Добавляем информацию о проекте в верхнюю панель
        if hasattr(self, 'controlPanel'):
            # Создаем виджет с информацией о проекте
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
            title_label = QLabel(f"📋 Проект: {self.project_data.name}")
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
        # Ищем MainWindow в родителях
        parent = self.parent()
        while parent:
            if hasattr(parent, 'contentStack') and hasattr(parent, 'switch_page'):
                parent.switch_page(0)  # Переключаемся на главную страницу
                break
            parent = parent.parent()

    def load_project_tasks(self):
        """Загрузка задач проекта"""
        if self.project_service and self.project_id:
            # Получаем данные доски проекта
            board_data = self.project_service.get_project_board_data(self.project_id)
            if board_data:
                # Преобразуем задачи в формат для карточек
                all_tasks = []
                for column in board_data.columns:
                    for task in column.tasks:
                        task_dict = {
                            'id': task.id,
                            'title': task.title,
                            'description': '',
                            'priority': task.priority.value if hasattr(task.priority, 'value') else task.priority,
                            'deadline': task.deadline.strftime('%d.%m.%Y') if task.deadline else '',
                            'status': column.name,
                            'column_id': column.id,
                            'assignee_name': task.assigned_to_name,
                            'completed': task.is_overdue,  # или другой признак
                        }
                        all_tasks.append(task_dict)

                # Очищаем текущие задачи и добавляем новые
                self.clear_all_columns()
                for task_dict in all_tasks:
                    self.add_task_card(task_dict)

                self.update_statistics()

    def create_task_card(self, task_data: Dict) -> QWidget:
        """Создает карточку задачи (переопределяем для проекта)"""
        # Определяем, является ли текущий пользователь создателем
        is_creator = (task_data.get('created_by') == self.current_user.get('id'))

        return OthersTaskCard(
            task_data,
            service=self.service,
            is_creator=is_creator
        )

    def update_statistics(self):
        """Обновление статистики с учетом прогресса проекта"""
        super().update_statistics()

        # Обновляем прогресс проекта
        if hasattr(self, 'project_data') and self.project_data:
            total = len(self.all_tasks) if hasattr(self, 'all_tasks') else 0
            completed = len([t for t in self.all_tasks if t.task_data.get('completed')]) if hasattr(self,
                                                                                                    'all_tasks') else 0

            if total > 0:
                progress = int((completed / total) * 100)
                if hasattr(self, 'project_data'):
                    self.project_data.progress = progress