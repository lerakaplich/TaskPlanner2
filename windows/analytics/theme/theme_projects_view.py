# windows/analytics/theme/theme_projects_view.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QFrame,
                             QLabel, QSizePolicy)
from PyQt6.QtCore import Qt


class ThemeProjectsView(QWidget):
    """Виджет для отображения проектов по теме - только UI"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._projects_data = []
        self._project_widgets = {}  # {project_name: (button, panel)}

        # ← ВАЖНО: создаем layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(10)

    def display_data(self, projects_data: list):
        """
        Отображает данные проектов.
        projects_data - список словарей с ключами:
        - project_name, task_count, completed_count
        """
        self._projects_data = projects_data
        self._build_ui()

    def _build_ui(self):
        """Построение интерфейса - все проекты скрыты по умолчанию"""
        # Очищаем layout
        self._clear_layout()

        if not self._projects_data:
            label = QLabel("Нет данных по проектам")
            label.setStyleSheet("color: #999; padding: 10px;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._layout.addWidget(label)
            return

        for project_item in self._projects_data:
            project_name = project_item.get("project_name", "Без названия")
            task_count = project_item.get("task_count", 0)
            completed_count = project_item.get("completed_count", 0)
            completion_percent = project_item.get("completion_percent", 0)

            # Заголовок проекта
            project_btn = QPushButton(f"▶ {project_name} ({task_count} задач)", self)
            project_btn.setCheckable(True)
            project_btn.setChecked(False)
            project_btn.setStyleSheet("""
                QPushButton {
                    background-color: #D22730;
                    color: white;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 13px;
                    border: none;
                    text-align: left;
                    padding: 6px 10px;
                    margin: 2px;
                }
                QPushButton:hover {
                    background-color: #862633;
                }
            """)
            self._layout.addWidget(project_btn)

            # Панель проекта
            project_panel = QFrame()
            project_panel.setVisible(False)
            project_panel.setStyleSheet("background-color: #f5f5f5; border-radius: 4px;")
            panel_layout = QVBoxLayout(project_panel)
            panel_layout.setContentsMargins(10, 10, 10, 10)
            panel_layout.setSpacing(8)

            # Информация о проекте
            info_label = QLabel(
                f"📊 Задач: {task_count} | ✅ Выполнено: {completed_count} | "
                f"📈 Выполнено: {completion_percent:.1f}%"
            )
            info_label.setStyleSheet("color: #555; font-size: 11px;")
            panel_layout.addWidget(info_label)

            self._layout.addWidget(project_panel)

            # Сохраняем ссылки
            self._project_widgets[project_name] = (project_btn, project_panel)

            # Логика сворачивания
            project_btn.toggled.connect(
                lambda checked, p=project_panel, b=project_btn: self._toggle_panel(checked, p, b)
            )

    def _clear_layout(self):
        """Очищает layout от всех виджетов"""
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._project_widgets.clear()

    def _toggle_panel(self, checked, panel, button):
        """Переключает видимость панели и текст кнопки"""
        panel.setVisible(checked)
        current_text = button.text()
        arrow = "▼" if checked else "▶"
        if len(current_text) > 1:
            button.setText(arrow + current_text[1:])
        else:
            button.setText(arrow)