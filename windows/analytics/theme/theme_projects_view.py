# windows/analytics/theme/theme_projects_view.py

from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QFrame,
                             QLabel, QSizePolicy)

# Исправлен импорт
from windows.analytics.task_card_analytics import TaskCard


class ThemeProjectsView(QWidget):
    def __init__(self, theme_name, projects_data, parent=None):
        super().__init__(parent)
        self.theme_name = theme_name
        self.projects_data = projects_data

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.build_ui()

    def build_ui(self):
        """Построение интерфейса"""
        # Очищаем layout
        while self.layout().count():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.projects_data:
            label = QLabel("Нет данных по проектам")
            label.setStyleSheet("color: #999; padding: 10px;")
            self.layout().addWidget(label)
            return

        for project_item in self.projects_data:
            if isinstance(project_item, dict):
                project_name = project_item.get("project_name", "Без названия")
                task_count = project_item.get("task_count", 0)
                completed_count = project_item.get("completed_count", 0)

                # Заголовок проекта
                project_btn = QPushButton(f"▶ {project_name} ({task_count} задач)")
                project_btn.setCheckable(True)
                project_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #D22730;
                        color: white;
                        border-radius: 6px;
                        font-weight: bold;
                        font-size: 14px;
                        border: none;
                        text-align: left;
                        padding: 8px 12px;
                    }
                    QPushButton:hover {
                        background-color: #862633;
                    }
                """)
                self.layout().addWidget(project_btn)

                # Панель проекта
                project_panel = QFrame()
                project_panel.setVisible(False)
                project_panel.setStyleSheet("background-color: #f5f5f5; border-radius: 4px;")
                panel_layout = QVBoxLayout(project_panel)
                panel_layout.setContentsMargins(10, 10, 10, 10)
                panel_layout.setSpacing(8)

                # Информация о проекте
                info_label = QLabel(f"📊 Задач: {task_count} | ✅ Выполнено: {completed_count}")
                info_label.setStyleSheet("color: #555; font-size: 12px;")
                panel_layout.addWidget(info_label)

                self.layout().addWidget(project_panel)

                # Логика сворачивания
                project_btn.toggled.connect(
                    lambda checked, p=project_panel, b=project_btn: self._update_toggle_state(checked, p, b)
                )

    def _update_toggle_state(self, checked, panel, button):
        panel.setVisible(checked)
        current_text = button.text()
        arrow = "▼" if checked else "▶"
        if len(current_text) > 1:
            button.setText(arrow + current_text[1:])
        else:
            button.setText(arrow)