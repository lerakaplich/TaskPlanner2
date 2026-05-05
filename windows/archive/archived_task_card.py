# windows/archive/archived_task_card.py

import os
from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal, QPoint, Qt
from PyQt6.QtWidgets import QMenu, QLabel, QFrame, QPushButton, QSizePolicy, QApplication


class ArchivedTaskCard(QFrame):
    """Карточка архивированной задачи - только UI"""

    restore_requested = pyqtSignal(int)
    delete_permanently_requested = pyqtSignal(int)
    data_updated = pyqtSignal(dict)

    def __init__(self, task_data: dict, parent=None, service=None):
        super().__init__(parent)
        self.task_data = task_data
        self.task_id = task_data["id"]
        self.service = service

        # Загружаем UI
        ui_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "ui", "archive", "archived_task_card.ui"
        )
        uic.loadUi(ui_path, self)

        # Настройка размеров
        self.setMinimumWidth(320)
        self.setMaximumWidth(350)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        # Настройка переноса слов
        self.title_label.setWordWrap(True)
        self.description_label.setWordWrap(True)
        self.project_label.setWordWrap(True)
        self.deadline_label.setWordWrap(True)
        self.assignee_label.setWordWrap(True)

        # Убираем ограничение высоты
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)

        self._apply_styles()
        self.fill_data()
        self.setup_menu()

    def _apply_styles(self):
        """Применяет стили к элементам"""
        # Стиль для карточки
        self.setStyleSheet("""
            ArchivedTaskCard {
                background-color: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
            }
            ArchivedTaskCard:hover {
                border: 2px solid #ccab6e;
                background-color: #ffffff;
            }
        """)

        # Стили меток
        normal_style = """
            QLabel {
                color: #555555;
                font-size: 12px;
                background-color: transparent;
            }
        """

        self.project_label.setStyleSheet(normal_style)
        self.deadline_label.setStyleSheet(normal_style)
        self.assignee_label.setStyleSheet(normal_style)

        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: bold;
                color: #1B232A;
                background-color: transparent;
            }
        """)

        self.description_label.setStyleSheet("""
            QLabel {
                color: #777777;
                font-size: 12px;
                background-color: transparent;
            }
        """)

    def fill_data(self):
        """Заполнение карточки данными"""
        # Название
        self.title_label.setText(self.task_data.get("title", "Без названия"))

        # Описание
        description = self.task_data.get("description", "")
        if description:
            self.description_label.setText(description[:150] + ("..." if len(description) > 150 else ""))
            self.description_label.setVisible(True)
        else:
            self.description_label.setVisible(False)

        # Проект
        project_name = self.task_data.get("project_name", "")
        if project_name:
            self.project_label.setText(f"Проект: {project_name}")
            self.project_label.setVisible(True)
        else:
            self.project_label.setVisible(False)

        # Приоритет
        priority = self.task_data.get("priority", "Средний")
        priority_colors = {
            "Низкий": "#4CAF50",
            "Средний": "#FFA726",
            "Высокий": "#E74C3C",
            "Критический": "#C0392B"
        }
        priority_color = priority_colors.get(priority, "#FFA726")

        self.priority_label.setText(priority)
        self.priority_label.setStyleSheet(f"""
            QLabel {{
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
                background-color: {priority_color};
                color: white;
            }}
        """)

        # Дедлайн
        deadline = self.task_data.get("deadline", "")
        if deadline:
            self.deadline_label.setText(f"Дедлайн: {deadline}")
        else:
            self.deadline_label.setText("Дедлайн: не указан")

        # Исполнитель
        assignee = self.task_data.get("assignee_name", "")
        if assignee:
            self.assignee_label.setText(f"Исполнитель: {assignee}")
        else:
            self.assignee_label.setText("Исполнитель: не назначен")

        # Теги
        tags = self.task_data.get("tags", [])
        self.clear_tags()
        if tags:
            for tag in tags[:3]:
                self.add_tag(tag)
            if len(tags) > 3:
                self.add_tag(f"+{len(tags) - 3}")

        # Бейдж архивации
        self._add_archive_badge()

        # Обновляем размер
        self.adjustSize()
        self.updateGeometry()

    def _add_archive_badge(self):
        """Добавляет бейдж архивации"""
        for i in range(self.footer_layout.count()):
            widget = self.footer_layout.itemAt(i).widget()
            if widget and isinstance(widget, QLabel) and hasattr(widget, 'is_archive_badge'):
                widget.deleteLater()
                break

        archived_at = self.task_data.get("archived_at", "")
        badge_text = f"Архивирована{f' {archived_at}' if archived_at else ''}"

        archive_badge = QLabel(badge_text)
        archive_badge.is_archive_badge = True
        archive_badge.setWordWrap(True)
        archive_badge.setStyleSheet("""
            QLabel {
                color: #999999;
                font-size: 10px;
                padding: 2px 6px;
                background-color: transparent;
            }
        """)
        self.footer_layout.insertWidget(0, archive_badge)

    def clear_tags(self):
        """Очищает контейнер с тегами"""
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def add_tag(self, tag_name: str):
        """Добавляет тег"""
        tag_btn = QPushButton(tag_name)
        tag_btn.setStyleSheet("""
            QPushButton {
                font-size: 10px;
                padding: 4px 10px;
                border-radius: 12px;
                background-color: #EEEEEE;
                color: #555555;
                border: none;
            }
            QPushButton:hover {
                background-color: #DDDDDD;
            }
        """)
        tag_btn.setCursor(tag_btn.cursor().PointingHandCursor)
        tag_btn.setFixedHeight(26)
        self.tags_layout.addWidget(tag_btn)

    def setup_menu(self):
        """Настройка контекстного меню"""
        self.menuButton.clicked.connect(self._show_context_menu)

    def _show_context_menu(self):
        """Показывает контекстное меню"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 4px 0;
                font-size: 13px;
            }
            QMenu::item {
                padding: 8px 25px 8px 15px;
                color: #333333;
            }
            QMenu::item:selected {
                background-color: #ccab6e;
                color: white;
                border-radius: 4px;
                margin: 2px 6px;
            }
        """)

        restore_action = menu.addAction("Восстановить")
        restore_action.triggered.connect(lambda: self.restore_requested.emit(self.task_id))

        delete_action = menu.addAction("Удалить навсегда")
        delete_action.triggered.connect(lambda: self.delete_permanently_requested.emit(self.task_id))

        menu.exec(self.menuButton.mapToGlobal(QPoint(0, self.menuButton.height())))

    def update_data(self, task_data: dict):
        """Обновляет данные карточки"""
        self.task_data = task_data
        self.task_id = task_data["id"]
        self.fill_data()
        self.data_updated.emit(task_data)

    def set_loading(self, loading: bool):
        """Устанавливает состояние загрузки"""
        if loading:
            self.menuButton.setEnabled(False)
            QApplication.processEvents()
        else:
            self.menuButton.setEnabled(True)

    def enterEvent(self, event):
        """При наведении курсора"""
        super().enterEvent(event)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def leaveEvent(self, event):
        """При уходе курсора"""
        super().leaveEvent(event)
        self.setCursor(Qt.CursorShape.ArrowCursor)