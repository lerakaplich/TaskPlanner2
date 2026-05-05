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
        self.stretch = None  # Будем хранить ссылку на растяжение

        print(f"📌 Создаем колонку: id={self.column_id}, name='{self.column_name}'")

        self.setup_ui()
        self.setAcceptDrops(True)
        self.show()

    def get_tasks(self):
        """Возвращает список всех карточек в колонке."""
        tasks = []
        for i in range(self.tasks_layout.count()):
            widget = self.tasks_layout.itemAt(i).widget()
            if widget:
                tasks.append(widget)
        return tasks

    def clear_tasks(self):
        """Очищает все карточки из колонки."""
        print(f"🗑️ Очистка колонки '{self.column_name}'")

        # Удаляем все виджеты, кроме растяжения
        while self.tasks_layout.count() > 0:
            item = self.tasks_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                # Не удаляем растяжение
                if widget != self.stretch:
                    print(f"   Удаляем виджет: {widget}")
                    widget.deleteLater()

        # Убеждаемся, что растяжение есть в конце
        if self.stretch is None or self.stretch not in [self.tasks_layout.itemAt(i) for i in
                                                        range(self.tasks_layout.count())]:
            self.stretch = self.tasks_layout.addStretch()

    def add_task(self, task_card):
        """Добавляет карточку задачи в колонку."""
        if task_card is None:
            print(f"⚠️ Попытка добавить None в колонку '{self.column_name}'")
            return

        # Убеждаемся, что карточка видима
        task_card.setVisible(True)

        # Устанавливаем правильный размер policy для карточки
        task_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        # Получаем индекс растяжения (оно всегда последнее)
        stretch_index = -1
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            if item and item.widget() == self.stretch:
                stretch_index = i
                break

        # Вставляем карточку перед растяжением
        if stretch_index >= 0:
            self.tasks_layout.insertWidget(stretch_index, task_card)
        else:
            # Если растяжения нет, добавляем в конец и затем добавляем растяжение
            self.tasks_layout.addWidget(task_card)
            self.stretch = self.tasks_layout.addStretch()

        # Принудительно обновляем layout
        task_card.updateGeometry()
        self.tasks_container.updateGeometry()

        print(f"   ✅ Добавлена карточка в колонку '{self.column_name}', теперь задач: {self.get_tasks_count()}")

    def get_tasks_count(self):
        """Возвращает количество карточек в колонке (без учета растяжения)."""
        count = 0
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            if item and item.widget() and item.widget() != self.stretch:
                count += 1
        return count

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

        self.setFixedWidth(350)
        self.setMinimumHeight(400)

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
        self.tasks_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setSpacing(8)
        self.tasks_layout.setContentsMargins(2, 2, 2, 10)
        self.tasks_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Добавляем растяжение в конец (сохраняем ссылку)
        self.stretch = self.tasks_layout.addStretch()

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

        print(f"  ✅ Колонка '{self.column_name}' готова")

    def sizeHint(self):
        return QSize(350, 500)