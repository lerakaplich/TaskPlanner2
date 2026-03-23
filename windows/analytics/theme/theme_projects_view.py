# windows/analytics/theme/theme_projects_view.py

from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QFrame,
                             QLabel, QSizePolicy)

from windows.analytics.task_card_analytics import TaskCard


class ThemeProjectsView(QWidget):
    def __init__(self, theme_name, projects_data, parent=None):
        """
        projects_data: список проектов или словарь с проектами
        """
        super().__init__(parent)
        self.theme_name = theme_name
        self.projects_data = projects_data  # Может быть списком или словарем

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.build_ui()

    def build_ui(self):
        """Построение интерфейса с проверкой типа данных"""

        # Очищаем layout
        while self.layout().count():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Проверяем тип projects_data
        if isinstance(self.projects_data, dict):
            # Если словарь {project_name: status_groups}
            for project_name, status_groups in self.projects_data.items():
                self.add_project_section(project_name, status_groups)
        elif isinstance(self.projects_data, list):
            # Если список проектов
            for project_item in self.projects_data:
                if isinstance(project_item, dict):
                    project_name = project_item.get("project_name", "Без названия")
                    # Создаем простую структуру статусов
                    status_groups = {
                        "tasks": project_item.get("tasks", [])
                    }
                    self.add_simple_project_section(project_name, status_groups)
        else:
            print(f"⚠️ ThemeProjectsView: projects_data имеет неподдерживаемый тип {type(self.projects_data)}")
            # Добавляем заглушку
            label = QLabel("Нет данных по проектам")
            label.setStyleSheet("color: #999; padding: 10px;")
            self.layout().addWidget(label)

    def add_simple_project_section(self, project_name, data):
        """Простая секция проекта без группировки по статусам"""
        # Заголовок проекта
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

        # Панель проекта
        project_panel = QFrame()
        project_panel.setVisible(False)
        project_panel.setStyleSheet("background-color: #f5f5f5; border-radius: 4px;")
        panel_layout = QVBoxLayout(project_panel)
        panel_layout.setContentsMargins(10, 10, 10, 10)
        panel_layout.setSpacing(8)

        # Добавляем задачи
        tasks = data.get("tasks", [])
        if tasks:
            for task_dto in tasks:
                try:
                    card = TaskCard(task_dto, compact=True, show_project=False)
                    panel_layout.addWidget(card)
                except Exception as e:
                    print(f"❌ Ошибка создания карточки задачи: {e}")
        else:
            no_tasks_label = QLabel("Нет задач")
            no_tasks_label.setStyleSheet("color: #999; padding: 5px;")
            panel_layout.addWidget(no_tasks_label)

        self.layout().addWidget(project_panel)

        # Логика сворачивания
        project_btn.toggled.connect(
            lambda checked, p=project_panel, b=project_btn: self._update_toggle_state(checked, p, b)
        )

    def add_project_section(self, project_name, status_groups):
        """
        Отрисовывает секцию проекта с группировкой по статусам
        """
        # Заголовок проекта
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

        # Панель проекта (контейнер для статусов)
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

        # Отрисовка групп по статусам
        has_tasks = False

        for status_key, tasks in status_groups.items():
            if status_key == "tasks":  # Пропускаем, если это не статус
                continue

            if not tasks:  # Пропускаем пустые статусы
                continue

            has_tasks = True
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

            # Добавляем карточки задач
            for task_dto in tasks:
                try:
                    card = TaskCard(task_dto, compact=True, show_project=False)
                    tasks_layout.addWidget(card)
                except Exception as e:
                    print(f"❌ Ошибка создания карточки задачи: {e}")

            panel_layout.addWidget(tasks_panel)

            # Логика сворачивания статуса
            status_btn.toggled.connect(
                lambda checked, p=tasks_panel, b=status_btn: self._update_toggle_state(checked, p, b)
            )

        if not has_tasks:
            no_tasks_label = QLabel("Нет задач в этом проекте")
            no_tasks_label.setStyleSheet("color: #999; padding: 5px;")
            panel_layout.addWidget(no_tasks_label)

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
        # Заменяем первый символ (стрелку)
        if len(current_text) > 1:
            button.setText(arrow + current_text[1:])
        else:
            button.setText(arrow)