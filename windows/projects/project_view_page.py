import os
from PyQt6 import uic
from PyQt6.QtWidgets import (QListWidgetItem, QFrame, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QListWidget, QProgressBar,
                             QLineEdit, QWidget)
from PyQt6.QtCore import Qt, QDate, pyqtSignal

from windows.other_tasks.others_tasks_page import OthersTasksPage
from windows.other_tasks.others_task_card import OthersTaskCard
from windows.other_tasks.task_dialog import TaskDialog


class ProjectViewPage(OthersTasksPage):
    """Страница просмотра проекта с задачами и информацией о команде"""

    projectUpdated = pyqtSignal()  # Сигнал при обновлении проекта

    def __init__(self, project_data=None, parent=None):
        """
        Инициализация страницы проекта

        Args:
            project_data: dict с данными проекта {
                'id': int,
                'name': str,
                'description': str,
                'status': str,
                'start_date': str,
                'end_date': str,
                'progress': int,
                'admins': list,
                'participants': list,
                'tasks': list (опционально)
            }
        """
        # Сохраняем данные проекта ДО вызова родительского конструктора
        self.project_data = project_data or self.get_default_project_data()

        # Вызываем родительский конструктор
        super().__init__(parent)

        # Инициализируем состояние
        self.members_visible = True

        # Настраиваем информацию о проекте
        self.setup_project_info()
        self.setup_members_lists()

        # Подключаем сигналы
        if hasattr(self, 'btnToggleMembers') and self.btnToggleMembers:
            self.btnToggleMembers.clicked.connect(self.toggle_members_visibility)

        # Переопределяем задачи для этого проекта
        if 'tasks' in self.project_data and self.project_data['tasks']:
            self.sample_tasks = self.project_data['tasks']
        else:
            # Создаем тестовые задачи для проекта
            self.sample_tasks = self.create_project_tasks()

        # Обновляем канбан-доску
        self.refresh_tasks_board()

    def get_default_project_data(self):
        """Возвращает данные проекта по умолчанию"""
        return {
            'id': 1,
            'name': 'Разработка новой CRM системы',
            'description': 'Проект по созданию современной CRM системы для отдела продаж с интеграцией существующих сервисов и аналитикой в реальном времени.',
            'status': 'Активен',
            'start_date': '01.02.2024',
            'end_date': '30.06.2024',
            'progress': 45,
            'admins': [
                'Иванов Иван Иванович (Руководитель проекта)',
                'Петрова Анна Сергеевна (Технический директор)',
                'Сидоров Алексей Владимирович (Ведущий разработчик)'
            ],
            'participants': [
                'Кузнецова Елена Павловна (Аналитик)',
                'Васильев Дмитрий Николаевич (Backend-разработчик)',
                'Михайлова Ольга Андреевна (Frontend-разработчик)',
                'Новиков Павел Игоревич (Тестировщик)',
                'Соколова Татьяна Валерьевна (Дизайнер)',
                'Морозов Артем Викторович (DevOps)',
                'Волкова Наталья Сергеевна (Project Manager)',
                'Козлов Максим Денисович (Аналитик данных)'
            ]
        }

    def create_project_tasks(self):
        """Создает тестовые задачи для проекта"""
        return [
            {
                "id": 1,
                "title": "Анализ требований к CRM",
                "description": "Провести встречи с отделом продаж, собрать и задокументировать требования к системе",
                "project": self.project_data['name'],
                "creator": "Вы",
                "assignee": "Кузнецова Елена Павловна",
                "priority": "high",
                "deadline": "15.02.2024",
                "status": "done",
                "created_at": "01.02.2024",
                "updated_at": "10.02.2024",
                "tags": [
                    {"text": "Анализ", "type": "analysis"},
                    {"text": "Документация", "type": "docs"}
                ],
                "completed": True
            },
            {
                "id": 2,
                "title": "Проектирование архитектуры БД",
                "description": "Спроектировать структуру базы данных для CRM",
                "project": self.project_data['name'],
                "creator": "Вы",
                "assignee": "Васильев Дмитрий Николаевич",
                "priority": "high",
                "deadline": "20.02.2024",
                "status": "progress",
                "created_at": "05.02.2024",
                "updated_at": "15.02.2024",
                "tags": [
                    {"text": "Архитектура", "type": "architecture"},
                    {"text": "База данных", "type": "database"}
                ],
                "completed": False
            },
            {
                "id": 3,
                "title": "Разработка макетов интерфейса",
                "description": "Создать прототипы основных экранов CRM",
                "project": self.project_data['name'],
                "creator": "Вы",
                "assignee": "Соколова Татьяна Валерьевна",
                "priority": "medium",
                "deadline": "25.02.2024",
                "status": "review",
                "created_at": "08.02.2024",
                "updated_at": "18.02.2024",
                "tags": [
                    {"text": "Дизайн", "type": "design"},
                    {"text": "UI/UX", "type": "uiux"}
                ],
                "completed": False
            },
            {
                "id": 4,
                "title": "Настройка CI/CD пайплайна",
                "description": "Настроить автоматическую сборку и деплой",
                "project": self.project_data['name'],
                "creator": "Вы",
                "assignee": "Морозов Артем Викторович",
                "priority": "medium",
                "deadline": "10.03.2024",
                "status": "todo",
                "created_at": "12.02.2024",
                "updated_at": "12.02.2024",
                "tags": [
                    {"text": "DevOps", "type": "devops"},
                    {"text": "Инфраструктура", "type": "infrastructure"}
                ],
                "completed": False
            },
            {
                "id": 5,
                "title": "Разработка API для интеграции",
                "description": "Создать REST API для внешних сервисов",
                "project": self.project_data['name'],
                "creator": "Вы",
                "assignee": "Сидоров Алексей Владимирович",
                "priority": "critical",
                "deadline": "15.03.2024",
                "status": "progress",
                "created_at": "10.02.2024",
                "updated_at": "18.02.2024",
                "tags": [
                    {"text": "API", "type": "api"},
                    {"text": "Разработка", "type": "development"}
                ],
                "completed": False
            }
        ]

    def setup_project_info(self):
        """Настройка информации о проекте"""
        if not hasattr(self, 'projectTitle') or not self.projectTitle:
            return

        # Заголовок и описание
        self.projectTitle.setText(self.project_data['name'])
        self.projectDescription.setText(self.project_data['description'])

        # Статус проекта
        status = self.project_data.get('status', 'Активен')
        self.projectStatus.setText(status)

        # Настройка цвета статуса
        status_colors = {
            'Активен': '#4CAF50',
            'Завершен': '#9C27B0',
            'На паузе': '#FF9800',
            'Архив': '#666666'
        }
        color = status_colors.get(status, '#4CAF50')
        self.projectStatus.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                font-weight: bold;
                color: white;
                background-color: {color};
                border-radius: 12px;
                padding: 4px 12px;
                min-width: 80px;
            }}
        """)

        # Даты
        self.startDateLabel.setText(f"📅 Начало: {self.project_data.get('start_date', 'Не указана')}")

    def setup_members_lists(self):
        """Настройка списков участников"""
        if not hasattr(self, 'membersList') or not self.membersList:
            return

        # Очищаем список
        self.membersList.clear()

        # Добавляем администраторов
        admins = self.project_data.get('admins', [])
        participants = self.project_data.get('participants', [])

        # Добавляем всех участников в один список
        for admin in admins:
            item = QListWidgetItem(f"👑 {admin}")
            self.membersList.addItem(item)

        for participant in participants:
            item = QListWidgetItem(f"👤 {participant}")
            self.membersList.addItem(item)

        # Обновляем заголовок
        if hasattr(self, 'membersTitle') and self.membersTitle:
            total_members = len(admins) + len(participants)
            self.membersTitle.setText(f"👥 Участники: {total_members} (админов: {len(admins)})")

    def toggle_members_visibility(self):
        """Скрыть/показать список участников"""
        if not hasattr(self, 'membersList') or not self.membersList:
            return

        self.members_visible = not self.members_visible

        if self.members_visible:
            self.membersList.show()
            self.btnToggleMembers.setText("⌄")
        else:
            self.membersList.hide()
            self.btnToggleMembers.setText("›")

    def refresh_tasks_board(self):
        """Обновление канбан-доски с задачами проекта"""
        # Очищаем существующие задачи из колонок
        for column_key, column in self.columns.items():
            layout = column.tasks_layout
            # Удаляем все виджеты, кроме спейсера в конце
            while layout.count() > 1:
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        # Очищаем список всех задач
        self.all_tasks = []

        # Создаем новые карточки задач
        for task_data in self.sample_tasks:
            task_card = OthersTaskCard(task_data, is_creator=True)
            task_card.editRequested.connect(self.edit_task)
            task_card.deleteRequested.connect(self.delete_task)
            task_card.archiveRequested.connect(self.archive_task)
            task_card.approveRequested.connect(self.approve_task)
            task_card.returnToWorkRequested.connect(self.return_to_work)
            self.all_tasks.append(task_card)

            # Добавляем в соответствующую колонку
            status = task_data["status"]
            if status == "todo":
                self.columns["todo"].tasks_layout.insertWidget(
                    self.columns["todo"].tasks_layout.count() - 1, task_card
                )
            elif status == "progress":
                self.columns["progress"].tasks_layout.insertWidget(
                    self.columns["progress"].tasks_layout.count() - 1, task_card
                )
            elif status == "review":
                self.columns["review"].tasks_layout.insertWidget(
                    self.columns["review"].tasks_layout.count() - 1, task_card
                )
            elif status == "done":
                self.columns["done"].tasks_layout.insertWidget(
                    self.columns["done"].tasks_layout.count() - 1, task_card
                )

        # Обновляем статистику
        self.update_statistics()

        # Обновляем фильтр проектов
        if hasattr(self, 'projectFilter'):
            self.projectFilter.clear()
            self.projectFilter.addItem("Все проекты")
            self.projectFilter.addItem(self.project_data['name'])
            self.projectFilter.setCurrentText(self.project_data['name'])

    def create_new_task(self):
        """Переопределяем создание задачи для привязки к текущему проекту"""
        dialog = TaskDialog(self, mode='create')
        if dialog.exec():
            new_task_data = dialog.get_task_data()
            new_task_data["id"] = len(self.sample_tasks) + 1
            new_task_data["creator"] = "Вы"
            new_task_data["project"] = self.project_data['name']  # Привязываем к текущему проекту
            new_task_data["created_at"] = QDate.currentDate().toString("dd.MM.yyyy")
            new_task_data["updated_at"] = QDate.currentDate().toString("dd.MM.yyyy")
            new_task_data["completed"] = False
            self.sample_tasks.append(new_task_data)

            # Создаем карточку задачи
            task_card = OthersTaskCard(new_task_data, is_creator=True)
            task_card.editRequested.connect(self.edit_task)
            task_card.deleteRequested.connect(self.delete_task)
            task_card.archiveRequested.connect(self.archive_task)
            task_card.approveRequested.connect(self.approve_task)
            task_card.returnToWorkRequested.connect(self.return_to_work)
            self.all_tasks.append(task_card)

            # Добавляем в соответствующую колонку
            status = new_task_data["status"]
            if status == "todo":
                self.columns["todo"].tasks_layout.insertWidget(
                    self.columns["todo"].tasks_layout.count() - 1, task_card
                )
            elif status == "progress":
                self.columns["progress"].tasks_layout.insertWidget(
                    self.columns["progress"].tasks_layout.count() - 1, task_card
                )
            elif status == "review":
                self.columns["review"].tasks_layout.insertWidget(
                    self.columns["review"].tasks_layout.count() - 1, task_card
                )
            elif status == "done":
                self.columns["done"].tasks_layout.insertWidget(
                    self.columns["done"].tasks_layout.count() - 1, task_card
                )

            self.update_statistics()
            self.taskUpdated.emit()
            self.projectUpdated.emit()

    def update_project_progress(self):
        """Обновление прогресса проекта на основе выполненных задач"""
        if not hasattr(self, 'project_data') or not self.sample_tasks:
            return

        completed_tasks = len([t for t in self.sample_tasks if t.get("completed", False)])
        total_tasks = len(self.sample_tasks)

        if total_tasks > 0:
            progress = int((completed_tasks / total_tasks) * 100)
            self.project_data['progress'] = progress

    def update_statistics(self):
        """Переопределяем обновление статистики для обновления прогресса проекта"""
        # Сначала вызываем родительский метод
        super().update_statistics()
        # Затем обновляем прогресс проекта
        self.update_project_progress()