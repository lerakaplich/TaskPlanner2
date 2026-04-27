# windows/analytics/task_card_analytics.py

import os
from datetime import datetime
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt


class TaskCard(QFrame):
    """Виджет для отображения карточки задачи."""

    PRIORITY_MAP = {
        'low': 'Низкий',
        'medium': 'Средний',
        'high': 'Высокий',
        'critical': 'Критический'
    }
    PRIORITY_COLORS = {
        'low': '#2ecc71',
        'medium': '#f1c40f',
        'high': '#e67e22',
        'critical': '#e74c3c'
    }
    STATUS_MAP = {
        'to_do': 'К выполнению',
        'in_progress': 'В работе',
        'review': 'На проверке',
        'completed': 'Выполнено',
        'archived': 'Архивировано',
        'overdue': 'Просрочена'
    }

    def __init__(self, task_data, compact=False, show_theme=False, show_project=False, parent=None):
        super().__init__(parent)
        self.task = task_data
        self.compact = compact
        self.show_theme = show_theme
        self.show_project = show_project
        self._init_ui()

    def _init_ui(self):
        overdue = self.task.get("is_overdue", False)
        priority = self.task.get("priority", "medium")
        status = self.task.get("status", "").lower()

        # Цвета фона и границы
        if overdue:
            bg_color = "#ffeeee"
            border_color = "#e74c3c"
        else:
            bg_color = "white"
            border_color = self.PRIORITY_COLORS.get(priority, "#cccccc")

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 8px;
                border-left: 6px solid {border_color};
                border-right: 1px solid #e0e0e0;
                border-top: 1px solid #e0e0e0;
                border-bottom: 1px solid #e0e0e0;
                margin: 4px;
            }}
            QLabel {{
                color: #1B232A;
            }}
        """)

        layout = QVBoxLayout(self)
        if self.compact:
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(4)
            font_size_title = "13px"
            font_size_normal = "11px"
            font_size_small = "10px"
        else:
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(8)
            font_size_title = "16px"
            font_size_normal = "14px"
            font_size_small = "12px"

        # ========== НАЗВАНИЕ ЗАДАЧИ ==========
        title = self.task.get("title", "Без названия")
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"font-size: {font_size_title}; font-weight: bold; color: #1B232A;")
        layout.addWidget(title_label)

        # ========== ОПИСАНИЕ (если есть) ==========
        description = self.task.get("description", "")
        if description and description.strip():
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"color: #666; font-size: {font_size_normal};")
            desc_label.setMaximumHeight(60 if self.compact else 80)
            layout.addWidget(desc_label)

        # ========== ИНФОРМАЦИОННАЯ СТРОКА (приоритет + дедлайн) ==========
        info_layout = QHBoxLayout()
        info_layout.setSpacing(10)

        # Приоритет
        prio_text = self.PRIORITY_MAP.get(priority, priority.capitalize())
        prio_color = "#e74c3c" if overdue else self.PRIORITY_COLORS.get(priority, "#000000")
        prio_label = QLabel(f"⚡ {prio_text}")
        prio_label.setStyleSheet(f"color: {prio_color}; font-weight: bold; font-size: {font_size_normal};")
        info_layout.addWidget(prio_label)

        # Дедлайн
        due_display = self.task.get("due_date_str", "Нет")
        if due_display and due_display != "Нет":
            due_text = f"📅 {due_display}"
            if overdue:
                due_text += " (просрочена)"
                due_style = f"color: #e74c3c; font-size: {font_size_normal};"
            else:
                due_style = f"color: #555; font-size: {font_size_normal};"
            due_label = QLabel(due_text)
            due_label.setStyleSheet(due_style)
            info_layout.addWidget(due_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)

        # ========== СТАТУС ==========
        status_text = self.STATUS_MAP.get(status, status.capitalize() if status else "Неизвестно")
        status_label = QLabel(f"📌 {status_text}")
        status_label.setStyleSheet(f"color: #555; font-size: {font_size_normal};")
        layout.addWidget(status_label)

        # ========== СОЗДАТЕЛЬ ==========
        creator = self.task.get("creator_name", "")
        if creator and creator != "Неизвестен":
            creator_label = QLabel(f"👤 Создал: {creator}")
            creator_label.setStyleSheet(f"color: #888; font-size: {font_size_small};")
            layout.addWidget(creator_label)

        # ========== ПРОЕКТ (если нужно показывать) ==========
        if self.show_project:
            project_name = self.task.get("project_name", "")
            if project_name:
                project_label = QLabel(f"📁 {project_name}")
                project_label.setStyleSheet(f"color: #888; font-size: {font_size_small};")
                layout.addWidget(project_label)

        # ========== ТЕГИ (если есть) ==========
        tags_list = self.task.get("tags_list", [])
        if tags_list:
            tags_layout = QHBoxLayout()
            tags_layout.setSpacing(5)
            tags_layout.setContentsMargins(0, 0, 0, 0)

            for tag in tags_list[:3]:  # Показываем максимум 3 тега
                tag_label = QLabel(f"#{tag}")
                tag_label.setStyleSheet("""
                    background-color: #F0F0F0;
                    color: #666;
                    font-size: 10px;
                    padding: 2px 6px;
                    border-radius: 10px;
                """)
                tags_layout.addWidget(tag_label)

            if len(tags_list) > 3:
                more_label = QLabel(f"+{len(tags_list) - 3}")
                more_label.setStyleSheet("color: #999; font-size: 10px;")
                tags_layout.addWidget(more_label)

            tags_layout.addStretch()
            layout.addLayout(tags_layout)

        # Задаем минимальную высоту для карточки
        self.setMinimumHeight(100 if self.compact else 120)