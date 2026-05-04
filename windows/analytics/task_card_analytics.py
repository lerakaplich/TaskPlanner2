# windows/analytics/task_card_analytics.py

from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt


class TaskCard(QFrame):
    """Виджет для отображения карточки задачи - только UI"""

    def __init__(self, task_data, compact=False, show_theme=False, show_project=False, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self.compact = compact
        self.show_theme = show_theme
        self.show_project = show_project
        self._init_ui()

    def _init_ui(self):
        # Получаем данные из словаря
        title = self.task_data.get("title", "Без названия")
        description = self.task_data.get("description", "")
        priority_text = self.task_data.get("priority_text", "Средний")
        priority_color = self.task_data.get("priority_color", "#f1c40f")
        status_text = self.task_data.get("status_text", "Неизвестно")
        is_overdue = self.task_data.get("is_overdue", False)
        due_date_str = self.task_data.get("due_date_str", "Нет")
        creator_name = self.task_data.get("creator_name", "")
        project_name = self.task_data.get("project_name", "")
        tags_list = self.task_data.get("tags_list", [])
        tags_extra_count = self.task_data.get("tags_extra_count", 0)

        # Цвета
        bg_color = "#ffeeee" if is_overdue else "white"

        # Определяем цвет границы
        if is_overdue:
            border_color = "#e74c3c"
        else:
            border_color = priority_color

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

        # Настройка размеров
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

        # Название задачи
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"font-size: {font_size_title}; font-weight: bold; color: #1B232A;")
        layout.addWidget(title_label)

        # Описание
        if description and description.strip():
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"color: #666; font-size: {font_size_normal};")
            desc_label.setMaximumHeight(60 if self.compact else 80)
            layout.addWidget(desc_label)

        # Информационная строка (приоритет + дедлайн)
        info_layout = QHBoxLayout()
        info_layout.setSpacing(10)

        # Приоритет
        prio_label = QLabel(f"⚡ {priority_text}")
        prio_label.setStyleSheet(f"color: {priority_color}; font-weight: bold; font-size: {font_size_normal};")
        info_layout.addWidget(prio_label)

        # Дедлайн
        if due_date_str and due_date_str != "Нет":
            due_text = f"📅 {due_date_str}"
            if is_overdue:
                due_text += " (просрочена)"
                due_style = f"color: #e74c3c; font-size: {font_size_normal};"
            else:
                due_style = f"color: #555; font-size: {font_size_normal};"
            due_label = QLabel(due_text)
            due_label.setStyleSheet(due_style)
            info_layout.addWidget(due_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Статус
        status_label = QLabel(f"📌 {status_text}")
        status_label.setStyleSheet(f"color: #555; font-size: {font_size_normal};")
        layout.addWidget(status_label)

        # Создатель
        if creator_name and creator_name != "Неизвестен":
            creator_label = QLabel(f"👤 Создал: {creator_name}")
            creator_label.setStyleSheet(f"color: #888; font-size: {font_size_small};")
            layout.addWidget(creator_label)

        # Проект
        if self.show_project and project_name:
            project_label = QLabel(f"📁 {project_name}")
            project_label.setStyleSheet(f"color: #888; font-size: {font_size_small};")
            layout.addWidget(project_label)

        # Теги
        if tags_list:
            tags_layout = QHBoxLayout()
            tags_layout.setSpacing(5)
            tags_layout.setContentsMargins(0, 0, 0, 0)

            for tag in tags_list:
                tag_label = QLabel(f"#{tag}")
                tag_label.setStyleSheet("""
                    background-color: #F0F0F0;
                    color: #666;
                    font-size: 10px;
                    padding: 2px 6px;
                    border-radius: 10px;
                """)
                tags_layout.addWidget(tag_label)

            if tags_extra_count > 0:
                more_label = QLabel(f"+{tags_extra_count}")
                more_label.setStyleSheet("color: #999; font-size: 10px;")
                tags_layout.addWidget(more_label)

            tags_layout.addStretch()
            layout.addLayout(tags_layout)

        self.setMinimumHeight(100 if self.compact else 120)