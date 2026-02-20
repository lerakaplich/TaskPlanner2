import os
from datetime import datetime
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout
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
    DEFAULT_CREATOR_NAMES = {
        1: "Иван Иванов",
        2: "Анна Петрова",
        3: "Алексей Сидоров"
    }

    def __init__(self, task_data, compact=False, show_theme=False, show_project=False,
                 check_overdue=False, creator_names=None, parent=None):
        super().__init__(parent)
        self.task = task_data
        self.compact = compact
        self.show_theme = show_theme
        self.show_project = show_project      # теперь параметр определён
        self.check_overdue = check_overdue
        self.creator_names = creator_names or self.DEFAULT_CREATOR_NAMES
        self._init_ui()

    # ---------- Вспомогательные методы ----------
    @staticmethod
    def parse_date(date_str):
        if not date_str:
            return None
        for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                pass
        return None

    @staticmethod
    def format_date(date_str):
        date = TaskCard.parse_date(date_str)
        return date.strftime("%d.%m.%Y") if date else (date_str or "—")

    def calculate_kpi(self, created_str, completed_str, due_str):
        created = self.parse_date(created_str)
        completed = self.parse_date(completed_str)
        due = self.parse_date(due_str)
        if not all([created, completed, due]):
            return None
        planned = (due - created).days
        actual = (completed - created).days
        if actual <= 0:
            return float('inf')
        return planned / actual

    def _get_creator_display(self):
        creator_raw = self.task.get("creator") or self.task.get("creator_id")
        if creator_raw is None:
            return "неизвестно"
        if isinstance(creator_raw, int):
            return self.creator_names.get(creator_raw, str(creator_raw))
        return creator_raw

    def _is_overdue(self):
        if not self.check_overdue:
            return False
        due_str = self.task.get("due_date")
        status = self.task.get("status", "").lower()
        completed_statuses = ("completed", "archived", "выполнено", "архивировано")
        if due_str and status not in completed_statuses:
            due_date = self.parse_date(due_str)
            if due_date and due_date < datetime.now().date():
                return True
        return False

    def _init_ui(self):
        overdue = self._is_overdue()
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
                border: none;
            }}
        """)

        layout = QVBoxLayout(self)
        if self.compact:
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(5)
            font_size_title = "14px"
            font_size_normal = "12px"
        else:
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(8)
            font_size_title = "16px"
            font_size_normal = "14px"

        # --- Название задачи ---
        title = QLabel(self.task.get("title", "Без названия"))
        title.setWordWrap(True)
        title.setStyleSheet(f"font-size: {font_size_title}; font-weight: bold; color: #1B232A;")
        layout.addWidget(title)

        # --- Проект (если нужно) ---
        if self.show_project:
            project = self.task.get('project', '—')
            project_label = QLabel(f"Проект: {project}")
            project_label.setStyleSheet(f"color: #555; font-size: {font_size_normal};")
            layout.addWidget(project_label)

        # --- Теги ---
        tags = self.task.get("tags", [])
        tags_str = ", ".join(tags) if tags else "нет"
        tags_label = QLabel(f"Теги: {tags_str}")
        tags_label.setStyleSheet(f"color: #555; font-size: {font_size_normal};")
        layout.addWidget(tags_label)

        # --- Приоритет ---
        prio_text = self.PRIORITY_MAP.get(priority, priority.capitalize())
        prio_color = "#e74c3c" if overdue else self.PRIORITY_COLORS.get(priority, "#000000")
        prio_label = QLabel(f"Приоритет: {prio_text}")
        prio_label.setStyleSheet(f"color: {prio_color}; font-weight: bold; font-size: {font_size_normal};")
        layout.addWidget(prio_label)

        # --- Дата создания ---
        created_label = QLabel(f"Дата создания: {self.format_date(self.task.get('created_at'))}")
        created_label.setStyleSheet(f"font-size: {font_size_normal};")
        layout.addWidget(created_label)

        # --- Дедлайн ---
        due_display = self.format_date(self.task.get("due_date")) or "Нет"
        due_text = f"Дедлайн: {due_display}"
        if overdue:
            due_text += " (просрочена)"
            due_style = f"color: #e74c3c; font-weight: bold; font-size: {font_size_normal};"
        else:
            due_style = f"color: #555; font-size: {font_size_normal};"
        due_label = QLabel(due_text)
        due_label.setStyleSheet(due_style)
        layout.addWidget(due_label)

        # --- Дата выполнения (если есть) ---
        completed_at = self.task.get("completed_at")
        if completed_at:
            completed_label = QLabel(f"Дата выполнения: {self.format_date(completed_at)}")
            completed_label.setStyleSheet(f"font-size: {font_size_normal};")
            layout.addWidget(completed_label)

        # --- Статус ---
        status_text = self.STATUS_MAP.get(status, status.capitalize())
        status_label = QLabel(f"Статус: {status_text}")
        status_label.setStyleSheet(f"font-size: {font_size_normal};")
        layout.addWidget(status_label)

        # --- Создатель ---
        creator_label = QLabel(f"Создатель: {self._get_creator_display()}")
        creator_label.setStyleSheet(f"font-size: {font_size_normal};")
        layout.addWidget(creator_label)

        # --- КПД (только для завершённых задач) ---
        if status in ("completed", "archived"):
            kpi = self.calculate_kpi(
                self.task.get("created_at"),
                self.task.get("completed_at"),
                self.task.get("due_date")
            )
            if kpi is not None:
                kpi_text = "∞" if kpi == float('inf') else f"{kpi:.2f}"
                kpi_label = QLabel(f"КПД: {kpi_text}")
                kpi_label.setStyleSheet(f"font-weight: bold; color: #27ae60; font-size: {font_size_normal};")
                layout.addWidget(kpi_label)