# windows/shared/kanban_column.py

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QScrollArea, QSizePolicy
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont


class KanbanColumn(QFrame):
    """Универсальная колонка канбан-доски"""

    def __init__(self, column_data: dict, parent=None):
        super().__init__(parent)

        self.column_id = column_data["id"]
        self.column_name = column_data["name"]
        self.column_color = column_data.get("color", "#2196F3")
        self.is_done_column = column_data.get("is_done", False)

        print(f"📌 Создаем колонку: id={self.column_id}, name='{self.column_name}'")

        self.setup_ui()
        self.setAcceptDrops(True)
        self.show()

    def get_tasks(self):
        """Возвращает список всех карточек в колонке."""
        tasks = []
        for i in range(self.tasks_layout.count()):
            widget = self.tasks_layout.itemAt(i).widget()
            if widget and hasattr(widget, 'task_data'):
                tasks.append(widget)
        return tasks

    def clear_tasks(self):
        """Очищает все карточки из колонки."""
        while self.tasks_layout.count() > 0:
            item = self.tasks_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def add_task(self, task_card):
        """Добавляет карточку задачи в колонку с выравниванием по верху."""
        # 👇 КЛЮЧЕВОЕ: добавляем с выравниванием по верху
        self.tasks_layout.addWidget(task_card, 0, Qt.AlignmentFlag.AlignTop)

    def remove_task(self, task_card):
        """Удаляет карточку задачи из колонки."""
        self.tasks_layout.removeWidget(task_card)
        task_card.deleteLater()

    def update_count(self, count):
        """Обновляет счетчик задач."""
        if hasattr(self, 'count_label'):
            self.count_label.setText(str(count))

    def setup_ui(self):
        """Настройка UI колонки"""
        self.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border-radius: 8px;
                border: 1px solid #ddd;
            }
        """)

        self.setFixedWidth(350)  # Немного шире для комфорта

        # Главный layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ========== ЗАГОЛОВОК ==========
        header_widget = QWidget()
        header_widget.setFixedHeight(30)
        header_widget.setStyleSheet("background-color: transparent;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(self.column_name)
        self.title_label.setStyleSheet("""
            QLabel {
                color: black;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial;
                padding: 5px;
            }
        """)
        header_layout.addWidget(self.title_label)

        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("""
            QLabel {
                background-color: #ccab6e;
                color: white;
                border-radius: 12px;
                padding: 2px 8px;
                font-size: 12px;
                font-weight: bold;
                min-width: 30px;
            }
        """)
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.count_label)
        header_layout.addStretch()

        main_layout.addWidget(header_widget)

        # Разделитель
        line = QFrame()
        line.setFixedHeight(2)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #e0e0e0; max-height: 1px;")
        main_layout.addWidget(line)

        # ========== ОБЛАСТЬ ЗАДАЧ С ПРОКРУТКОЙ ==========
        self.tasks_container = QWidget()
        self.tasks_container.setStyleSheet("background-color: transparent;")

        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setSpacing(8)
        self.tasks_layout.setContentsMargins(2, 2, 2, 2)
        self.tasks_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Прижимаем к верху
        # 👇 Убираем растяжение у карточек
        self.tasks_layout.setStretch(0, 0)

        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setWidget(self.tasks_container)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
        """)

        main_layout.addWidget(scroll_area)

        self.setLayout(main_layout)

        # Для совместимости
        self.tasksLayout = self.tasks_layout
        self.countLabel = self.count_label
        self.titleLabel = self.title_label
        self.tasks_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        print(f"  ✅ Колонка '{self.column_name}' готова")

    def sizeHint(self):
        return QSize(350, 500)