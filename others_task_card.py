from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
                             QPushButton, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QAction, QColor, QPalette


class OthersTaskCard(QWidget):
    """Карточка задачи для Создателя (с возможностями редактирования)"""

    editRequested = pyqtSignal(int)
    deleteRequested = pyqtSignal(int)
    archiveRequested = pyqtSignal(int)
    approveRequested = pyqtSignal(int)
    returnToWorkRequested = pyqtSignal(int)

    def __init__(self, task_data, is_creator=False):
        super().__init__()
        self.task_data = task_data
        self.is_creator = is_creator
        self.setup_ui()
        self.setup_context_menu()

    def setup_ui(self):
        """Настройка интерфейса карточки"""
        self.setMinimumHeight(120)
        self.setMaximumWidth(350)

        # Основной контейнер
        main_layout = QVBoxLayout()
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # Верхняя строка: заголовок и приоритет
        header_layout = QHBoxLayout()

        # Заголовок
        title_label = QLabel(self.task_data.get("title", "Без названия"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        title_label.setWordWrap(True)
        header_layout.addWidget(title_label)

        # Метка приоритета
        priority = self.task_data.get("priority", "medium")
        priority_colors = {
            "critical": "#F44336",
            "high": "#FF9800",
            "medium": "#2196F3",
            "low": "#4CAF50"
        }
        priority_text = {
            "critical": "Крит",
            "high": "Высок",
            "medium": "Средн",
            "low": "Низк"
        }

        priority_label = QLabel(priority_text.get(priority, "Средн"))
        priority_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                background-color: {priority_colors.get(priority, "#2196F3")};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)
        header_layout.addWidget(priority_label)

        main_layout.addLayout(header_layout)

        # Описание
        description = self.task_data.get("description", "")
        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #666; font-size: 10px;")
            main_layout.addWidget(desc_label)

        # Теги
        tags = self.task_data.get("tags", [])
        if tags:
            tags_layout = QHBoxLayout()
            tags_layout.setSpacing(4)

            for tag in tags:
                tag_label = QLabel(tag.get("text", ""))
                tag_type = tag.get("type", "default")
                tag_styles = {
                    "design": "background-color: #E3F2FD; color: #1565C0;",
                    "urgent": "background-color: #FFEBEE; color: #C62828; font-weight: bold;",
                    "bug": "background-color: #FFF3E0; color: #EF6C00;",
                    "security": "background-color: #E8F5E9; color: #2E7D32;",
                    "docs": "background-color: #F3E5F5; color: #7B1FA2;",
                    "development": "background-color: #E0F7FA; color: #006064;",
                    "testing": "background-color: #FFF8E1; color: #FF8F00;",
                    "data": "background-color: #F5F5F5; color: #424242;",
                    "update": "background-color: #E8EAF6; color: #3949AB;",
                    "report": "background-color: #F1F8E9; color: #558B2F;",
                    "finance": "background-color: #FFF3E0; color: #F57C00;",
                    "default": "background-color: #F5F5F5; color: #666;"
                }

                tag_label.setStyleSheet(f"""
                    QLabel {{
                        {tag_styles.get(tag_type, tag_styles["default"])}
                        border-radius: 3px;
                        padding: 1px 5px;
                        font-size: 9px;
                    }}
                """)
                tags_layout.addWidget(tag_label)

            tags_layout.addStretch()
            main_layout.addLayout(tags_layout)

        # Нижняя строка: метаданные и действия
        footer_layout = QHBoxLayout()

        # Метаданные
        meta_layout = QVBoxLayout()

        # Проект и исполнитель
        project = self.task_data.get("project", "")
        assignee = self.task_data.get("assignee", "")

        if project:
            project_label = QLabel(f"📁 {project}")
            project_label.setStyleSheet("color: #666; font-size: 9px;")
            meta_layout.addWidget(project_label)

        if assignee:
            assignee_label = QLabel(f"👤 {assignee}")
            assignee_label.setStyleSheet("color: #666; font-size: 9px;")
            meta_layout.addWidget(assignee_label)

        # Срок выполнения
        deadline = self.task_data.get("deadline", "")
        if deadline:
            deadline_label = QLabel(f"📅 {deadline}")

            # Проверка на просрочку
            from PyQt6.QtCore import QDate
            current_date = QDate.currentDate()
            deadline_date = QDate.fromString(deadline, "dd.MM.yyyy")
            if deadline_date and deadline_date < current_date and not self.task_data.get("completed", False):
                deadline_label.setStyleSheet("color: #F44336; font-size: 9px; font-weight: bold;")
            else:
                deadline_label.setStyleSheet("color: #666; font-size: 9px;")

            meta_layout.addWidget(deadline_label)

        footer_layout.addLayout(meta_layout)
        footer_layout.addStretch()

        # Кнопка меню действий (только для создателя)
        if self.is_creator:
            self.menu_btn = QPushButton("⋮")
            self.menu_btn.setFixedSize(24, 24)
            self.menu_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F5F5F5;
                    border: 1px solid #DDD;
                    border-radius: 4px;
                    color: #666;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #E0E0E0;
                }
            """)
            self.menu_btn.clicked.connect(self.show_context_menu)
            footer_layout.addWidget(self.menu_btn)

        main_layout.addLayout(footer_layout)

        # Настройка стиля карточки
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #E0E0E0;
            }
            QWidget:hover {
                border-color: #BDBDBD;
                background-color: #FAFAFA;
            }
        """)

        self.setLayout(main_layout)

        # Устанавливаем курсор
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def setup_context_menu(self):
        """Настройка контекстного меню"""
        self.context_menu = QMenu(self)

        # Разные действия в зависимости от статуса задачи
        status = self.task_data.get("status", "todo")

        # Общие действия
        edit_action = QAction("✏️ Редактировать", self)
        edit_action.triggered.connect(lambda: self.editRequested.emit(self.task_data["id"]))
        self.context_menu.addAction(edit_action)

        delete_action = QAction("🗑️ Удалить", self)
        delete_action.triggered.connect(lambda: self.deleteRequested.emit(self.task_data["id"]))
        self.context_menu.addAction(delete_action)

        self.context_menu.addSeparator()

        # Действия для задач "На проверке"
        if status == "review":
            approve_action = QAction("✅ Одобрить выполнение", self)
            approve_action.triggered.connect(lambda: self.approveRequested.emit(self.task_data["id"]))
            self.context_menu.addAction(approve_action)

            return_action = QAction("↩️ Вернуть на доработку", self)
            return_action.triggered.connect(lambda: self.returnToWorkRequested.emit(self.task_data["id"]))
            self.context_menu.addAction(return_action)

        # Действия для выполненных задач
        elif status == "done":
            archive_action = QAction("📁 Архивировать", self)
            archive_action.triggered.connect(lambda: self.archiveRequested.emit(self.task_data["id"]))
            self.context_menu.addAction(archive_action)

        # Действия для других статусов
        else:
            mark_done_action = QAction("✓ Отметить выполненной", self)
            mark_done_action.triggered.connect(lambda: self.mark_as_done())
            self.context_menu.addAction(mark_done_action)

    def show_context_menu(self):
        """Показ контекстного меню"""
        self.context_menu.exec(self.mapToGlobal(self.menu_btn.pos()))

    def mark_as_done(self):
        """Отметить задачу как выполненную"""
        self.task_data["status"] = "done"
        self.task_data["completed"] = True
        # Сигнал будет обработан в OthersTasksPage

    def update_task_data(self, new_data):
        """Обновление данных задачи"""
        self.task_data.update(new_data)

        # Пересоздаем UI с новыми данными
        self.clear()
        self.setup_ui()

    def clear(self):
        """Очистка виджета"""
        layout = self.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            layout.deleteLater()

    def mousePressEvent(self, event):
        """Обработка клика по карточке"""
        if event.button() == Qt.MouseButton.RightButton and self.is_creator:
            self.show_context_menu()
        super().mousePressEvent(event)