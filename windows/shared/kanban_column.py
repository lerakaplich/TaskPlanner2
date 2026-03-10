# windows/shared/kanban_column.py

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont


class KanbanColumn(QFrame):
    """Универсальная колонка канбан-доски"""

    def __init__(self, column_data: dict, parent=None):
        super().__init__(parent)

        self.column_id = column_data["id"]
        self.column_name = column_data["name"]
        self.column_color = column_data.get("color", "#2196F3")

        self.setup_ui()
        self.setAcceptDrops(True)

    def setup_ui(self):
        """Настройка UI колонки"""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border: 1px solid #E0E0E0;
            }}
        """)

        self.setSizePolicy(self.sizePolicy().Policy.Preferred,
                           self.sizePolicy().Policy.Expanding)
        self.setMinimumWidth(250)
        self.setMinimumHeight(400)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Заголовок
        header = QHBoxLayout()

        self.title_label = QLabel(self.column_name)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {self.column_color};")
        header.addWidget(self.title_label)

        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: white;
                background-color: #666;
                border-radius: 10px;
                padding: 2px 8px;
                font-weight: bold;
            }
        """)
        header.addWidget(self.count_label)
        header.addStretch()
        layout.addLayout(header)

        # Область задач
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #F5F5F5;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #C1C1C1;
                border-radius: 4px;
                min-height: 20px;
            }
        """)

        self.tasks_container = QWidget()
        self.tasks_container.setStyleSheet("background-color: transparent;")
        self.tasks_container.setAcceptDrops(True)

        self.tasks_layout = QVBoxLayout()
        self.tasks_layout.setSpacing(8)
        self.tasks_layout.setContentsMargins(2, 2, 2, 2)
        self.tasks_layout.addStretch()
        self.tasks_container.setLayout(self.tasks_layout)

        scroll_area.setWidget(self.tasks_container)
        layout.addWidget(scroll_area)

        self.setLayout(layout)

        # Для совместимости со старым кодом
        self.tasksLayout = self.tasks_layout
        self.countLabel = self.count_label
        self.titleLabel = self.title_label

    def add_task(self, task_card):
        """Добавляет карточку задачи в колонку"""
        self.tasks_layout.insertWidget(self.tasks_layout.count() - 1, task_card)

    def remove_task(self, task_card):
        """Удаляет карточку задачи из колонки"""
        for i in range(self.tasks_layout.count()):
            w = self.tasks_layout.itemAt(i).widget()
            if w == task_card:
                self.tasks_layout.takeAt(i)
                return True
        return False

    def clear_tasks(self):
        """Очищает колонку от всех задач"""
        while self.tasks_layout.count() > 1:
            item = self.tasks_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def update_count(self, count: int):
        """Обновляет счетчик задач"""
        self.count_label.setText(str(count))

    def sizeHint(self):
        """Рекомендуемый размер"""
        return QSize(300, 500)