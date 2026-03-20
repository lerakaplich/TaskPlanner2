from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QFrame,
                             QLabel, QSizePolicy)

from windows.analytics.task_card_analytics import TaskCard


# class ThemeTaskCard(QFrame):
#     """Карточка задачи для вкладки темы."""
#     def __init__(self, task, project_name, parent=None):
#         super().__init__(parent)
#         self.task = task
#         self.project_name = project_name
#         self.setup_ui()
#
#     def parse_date(self, date_str):
#         if not date_str:
#             return None
#         for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
#             try:
#                 return datetime.strptime(date_str, fmt).date()
#             except ValueError:
#                 pass
#         return None
#
#     def format_date(self, date_str):
#         date = self.parse_date(date_str)
#         return date.strftime("%d.%m.%Y") if date else (date_str or "—")
#
#     def setup_ui(self):
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(12, 12, 12, 12)
#         layout.setSpacing(5)
#
#         # Проверка просрочки
#         overdue = False
#         due_str = self.task.get("due_date")
#         status = self.task.get("status", "").lower()
#         if due_str and status not in ("completed", "archived", "выполнено"):
#             due_date = self.parse_date(due_str)
#             if due_date and due_date < datetime.now().date():
#                 overdue = True
#
#         # Стиль: красная граница если просрочена
#         if overdue:
#             self.setStyleSheet("background-color: #ffeeee; border-left: 6px solid #e74c3c; border-radius: 6px;")
#         else:
#             self.setStyleSheet("background-color: white; border-left: 6px solid #cccccc; border-radius: 6px;")
#
#         # Название задачи
#         title = QLabel(f"<b>{self.task.get('title', 'Без названия')}</b>")
#         title.setWordWrap(True)
#         layout.addWidget(title)
#
#         # Проект
#         layout.addWidget(QLabel(f"Проект: {self.project_name}"))
#
#         # Приоритет
#         priority_map = {'low': 'Низкий', 'medium': 'Средний', 'high': 'Высокий', 'critical': 'Критический'}
#         prio = self.task.get('priority', 'medium')
#         prio_text = priority_map.get(prio, prio.capitalize())
#         layout.addWidget(QLabel(f"Приоритет: {prio_text}"))
#
#         # Исполнитель
#         assigned = self.task.get('assigned_to')
#         if isinstance(assigned, int):
#             # для теста преобразуем id в имя
#             names = {1: "Иван Иванов", 2: "Анна Петрова", 3: "Алексей Сидоров"}
#             assigned = names.get(assigned, str(assigned))
#         layout.addWidget(QLabel(f"Исполнитель: {assigned or 'не назначен'}"))
#
#         # Дата создания
#         layout.addWidget(QLabel(f"Создана: {self.format_date(self.task.get('created_at'))}"))
#
#         # Дедлайн
#         due_display = self.format_date(due_str) or "Нет"
#         due_text = f"Дедлайн: {due_display}"
#         if overdue:
#             due_text += " (просрочена)"
#         due_label = QLabel(due_text)
#         if overdue:
#             due_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
#         layout.addWidget(due_label)
#
#         # Статус
#         status_map = {
#             'to_do': 'К выполнению', 'in_progress': 'В работе',
#             'review': 'На проверке', 'completed': 'Выполнено',
#             'archived': 'Архивировано'
#         }
#         status_text = status_map.get(status, status.capitalize())
#         layout.addWidget(QLabel(f"Статус: {status_text}"))
#
#         # Создатель
#         creator = self.task.get('creator') or self.task.get('creator_id')
#         if isinstance(creator, int):
#             names = {1: "Иван Иванов", 2: "Анна Петрова", 3: "Алексей Сидоров"}
#             creator = names.get(creator, str(creator))
#         layout.addWidget(QLabel(f"Создатель: {creator or 'неизвестен'}"))
#
#         self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
#

class ThemeProjectsView(QWidget):
    def __init__(self, theme_name, projects_data, parent=None):
        """
        projects_data: уже сгруппированный словарь от сервиса
        """
        super().__init__(parent)
        self.projects_data = projects_data  # { Project: { Status: [DTOs] } }

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.build_ui()

    def build_ui(self):
        # Теперь просто перебираем готовые данные
        for project_name, statuses in self.projects_data.items():
            self.add_project_section(project_name, statuses)

    def build_tree(self):
        # Группировка задач по проектам
        projects_dict = {}
        for task in self.all_tasks:
            proj = task.get("project", "Без проекта")
            if proj not in projects_dict:
                projects_dict[proj] = []
            projects_dict[proj].append(task)

        for project_name, tasks in projects_dict.items():
            self.add_project_section(project_name, tasks)

    def add_project_section(self, project_name, status_groups):
        """
        Отрисовывает секцию проекта.
        status_groups: словарь вида {'to_do': [dto1, dto2], 'in_progress': [], ...}
        """
        # 1. Заголовок проекта
        project_btn = QPushButton(f"▶ {project_name}")
        project_btn.setCheckable(True)
        project_btn.setStyleSheet("""
            QPushButton {
                background-color: #D22730; color: white; border-radius: 6px;
                font-weight: bold; font-size: 14px; border: none; text-align: left;
                padding: 8px 12px;
            }
            QPushButton:hover { background-color: #862633; }
            QPushButton:pressed { background-color: #6a1e29; }
        """)
        self.layout().addWidget(project_btn)

        # 2. Панель проекта (контейнер для статусов)
        project_panel = QFrame()
        project_panel.setVisible(False)
        project_panel.setStyleSheet("background-color: #f5f5f5; border-radius: 4px;")
        panel_layout = QVBoxLayout(project_panel)
        panel_layout.setContentsMargins(10, 10, 10, 10)
        panel_layout.setSpacing(8)

        # Человеческие названия для ключей из сервиса
        display_names = {
            "to_do": "К выполнению",
            "in_progress": "В работе",
            "review": "На проверке",
            "completed": "Выполнено"
        }

        # 3. Отрисовка групп по статусам
        for status_key, tasks in status_groups.items():
            if not tasks:  # Пропускаем пустые статусы
                continue

            status_display = display_names.get(status_key, status_key.capitalize())

            # Кнопка статуса
            status_btn = QPushButton(f"▶ {status_display} ({len(tasks)})")
            status_btn.setCheckable(True)
            status_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1B232A; color: white; border: none;
                    border-radius: 6px; padding: 6px 10px; font-size: 13px;
                    font-weight: bold; text-align: left; margin-left: 5px;
                }
                QPushButton:hover { background-color: #D9D9D6; color: black; }
            """)
            panel_layout.addWidget(status_btn)

            # Панель задач внутри статуса
            tasks_panel = QFrame()
            tasks_panel.setVisible(False)
            tasks_panel.setStyleSheet("background-color: white; border-radius: 4px;")
            tasks_layout = QVBoxLayout(tasks_panel)
            tasks_layout.setContentsMargins(8, 8, 8, 8)
            tasks_layout.setSpacing(6)

            # Добавляем карточки задач (TaskCard теперь принимает готовый DTO)
            for task_dto in tasks:
                card = TaskCard(task_dto, compact=True, show_project=False)
                tasks_layout.addWidget(card)

            panel_layout.addWidget(tasks_panel)

            # Логика сворачивания статуса
            status_btn.toggled.connect(
                lambda checked, p=tasks_panel, b=status_btn: self._update_toggle_state(checked, p, b)
            )

        self.layout().addWidget(project_panel)

        # Логика сворачивания всего проекта
        project_btn.toggled.connect(
            lambda checked, p=project_panel, b=project_btn: self._update_toggle_state(checked, p, b)
        )

    def _update_toggle_state(self, checked, panel, button):
        """Вспомогательный метод для управления стрелочками и видимостью."""
        panel.setVisible(checked)
        current_text = button.text()
        arrow = "▼" if checked else "▶"
        button.setText(arrow + current_text[1:])