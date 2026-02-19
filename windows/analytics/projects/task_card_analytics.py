import os
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QSizePolicy


class TaskCard(QFrame):
    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskCard")
        self.setStyleSheet("""
            TaskCard {
                background-color: white;
                border-radius: 6px;
                border: 1px solid #E0E0E0;
                margin: 2px;
            }
            QLabel {
                font-size: 11px;
                color: #333;
            }
            QLabel[cssClass="title"] {
                font-size: 12px;
                font-weight: bold;
                color: #1B232A;
            }
        """)

        self.task_data = task_data
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)

        # Название
        title = QLabel(self.task_data.get("title", ""))
        title.setProperty("cssClass", "title")
        layout.addWidget(title)

        # Тема, приоритет, исполнитель
        theme = self.task_data.get("theme", "")
        priority = self.task_data.get("priority", "")
        assignee_id = self.task_data.get("assigned_to")
        assignee_name = self._get_assignee_name(assignee_id)
        line1 = QLabel(f"Тема: {theme} | Приоритет: {priority} | Исполнитель: {assignee_name}")
        line1.setWordWrap(True)
        layout.addWidget(line1)

        # Дата создания, дедлайн
        created = self.task_data.get("created_at", "")
        due = self.task_data.get("due_date", "")
        overdue = self._is_overdue()
        due_text = due
        if overdue:
            due_text += " (просрочена)"
        line2 = QLabel(f"Создана: {created} | Дедлайн: {due_text}")
        if overdue:
            line2.setStyleSheet("color: red;")
        layout.addWidget(line2)

        # Статус, создатель
        status = self.task_data.get("status", "")
        creator_id = self.task_data.get("creator_id")
        creator_name = self._get_creator_name(creator_id)
        line3 = QLabel(f"Статус: {status} | Создатель: {creator_name}")
        layout.addWidget(line3)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _is_overdue(self):
        due_str = self.task_data.get("due_date")
        status = self.task_data.get("status")
        if not due_str or status in ("completed", "archived"):
            return False
        try:
            due_date = datetime.strptime(due_str, "%Y-%m-%d").date()
            return due_date < datetime.now().date()
        except:
            return False

    def _get_assignee_name(self, assignee_id):
        # В реальном проекте здесь был бы репозиторий сотрудников
        names = {1: "Иван Иванов", 2: "Анна Петрова", 3: "Алексей Сидоров"}
        return names.get(assignee_id, str(assignee_id))

    def _get_creator_name(self, creator_id):
        names = {1: "Иван Иванов", 2: "Анна Петрова", 3: "Алексей Сидоров"}
        return names.get(creator_id, str(creator_id))