# windows/my_tasks/task_card.py

import json
import os

from PyQt6 import uic
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QDrag, QPixmap, QPainter
from PyQt6.QtWidgets import (
    QFrame, QPushButton, QMenu, QApplication, QSizePolicy,
    QLabel, QHBoxLayout, QWidget, QGridLayout
)


class TaskCardStyles:
    """Стили для TaskCard - вынесены в отдельный класс"""

    DIFFICULTY_STYLES = {
        4: {"color": "#D22730", "bg": "#FFEBEE"},
        3: {"color": "#FF9800", "bg": "#FFF3E0"},
        1: {"color": "#4CAF50", "bg": "#E8F5E9"},
        0: {"color": "#9E9E9E", "bg": "#F5F5F5"},
    }

    TAG_STYLE = """
        QPushButton {
            font-size: 10px;
            padding: 4px 10px;
            border-radius: 10px;
            background: #E8F5E9;
            color: #2E7D32;
            border: 1px solid #C8E6C9;
        }
        QPushButton:hover {
            background: #C8E6C9;
        }
    """

    PAUSE_STYLE = """
        background-color: #FF9800;
        color: white;
        font-size: 10px;
        font-weight: bold;
        padding: 2px 8px;
        border-radius: 10px;
    """

    MENU_STYLE = """
        QMenu {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 6px 0;
            font-size: 14px;
        }
        QMenu::item {
            padding: 10px 30px 10px 15px;
            color: #1B232A;
        }
        QMenu::item:selected {
            background-color: #ccab6e;
            color: white;
            border-radius: 6px;
            margin: 2px 6px;
        }
    """

    PROGRESS_STYLE = """
        QProgressBar {
            border: 2px solid #E0E0E0;
            border-radius: 8px;
            text-align: center;
            background-color: white;
            font-size: 13px;
        }
        QProgressBar:hover {
            border: 2px solid #ccab6e;
        }
        QProgressBar::chunk {
            background-color: #D22730;
            border-radius: 8px;
        }
    """


class TaskCard(QFrame):
    """UI карточки задачи - только отображение и сигналы"""

    # Сигналы для внешней обработки
    edit_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)
    archive_requested = pyqtSignal(int)
    duplicate_requested = pyqtSignal(int)
    pause_requested = pyqtSignal(int)
    resume_requested = pyqtSignal(int)
    move_requested = pyqtSignal(int, str)
    drag_started = pyqtSignal(dict)
    progress_changed = pyqtSignal(int, int)
    project_clicked = pyqtSignal(int)

    def __init__(self, task_data, parent=None):
        super().__init__(parent)

        self.task_data = task_data
        self.task_id = task_data.get("id")
        self.drag_start_position = None
        self._updating_progress = False
        self._delete_enabled = True
        self._archive_enabled = True

        self._setup_widget_flags()
        self._load_ui()
        self._setup_ui_components()
        self.fill_ui()
        self._connect_signals()

    # ==========================================================
    # НАСТРОЙКА UI
    # ==========================================================

    def _setup_widget_flags(self):
        """Настройка флагов виджета"""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setVisible(False)

    def _load_ui(self):
        """Загрузка UI из файла"""
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "my_tasks", "task_card.ui"
        )
        uic.loadUi(ui_path, self)

        self.setObjectName("TaskCard")
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        self.setFixedWidth(300)
        self.setMinimumHeight(0)
        self.setContentsMargins(0, 0, 0, 0)

    def _setup_ui_components(self):
        """Настройка компонентов UI"""
        self._setup_difficulty_widget()
        self.overallProgress.mousePressEvent = self._on_progress_click

    def _setup_difficulty_widget(self):
        """Создает виджет для отображения сложности"""
        self.difficulty_widget = QWidget()
        self.difficulty_layout = QHBoxLayout(self.difficulty_widget)
        self.difficulty_layout.setContentsMargins(0, 0, 0, 0)
        self.difficulty_layout.setSpacing(5)

        self.difficulty_label = QLabel("Сложность:")
        self.difficulty_label.setStyleSheet("font-size: 11px; color: #666; border: none;")

        self.difficulty_value_label = QLabel("0⭐")
        self.difficulty_value_label.setStyleSheet("""
            font-size: 11px;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 8px;
            border: none;
        """)

        self.difficulty_layout.addWidget(self.difficulty_label)
        self.difficulty_layout.addWidget(self.difficulty_value_label)
        self.difficulty_layout.addStretch()

        self._insert_difficulty_widget()

    def _insert_difficulty_widget(self):
        """Вставляет виджет сложности в layout"""
        layout = self.layout()
        if layout:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget() == self.overallProgress:
                    layout.insertWidget(i, self.difficulty_widget)
                    break

    def _connect_signals(self):
        """Подключение сигналов"""
        self.menuButton.clicked.connect(self._show_context_menu)
        self.projectButton.clicked.connect(self._on_project_clicked)

    # ==========================================================
    # УПРАВЛЕНИЕ ВИДИМОСТЬЮ КНОПОК
    # ==========================================================

    def set_delete_button_visible(self, visible: bool):
        self._delete_enabled = visible

    def set_archive_button_visible(self, visible: bool):
        self._archive_enabled = visible

    # ==========================================================
    # ЗАПОЛНЕНИЕ ДАННЫМИ
    # ==========================================================

    def fill_ui(self):
        """Заполнение карточки данными"""
        self._fill_title()
        self._fill_project()
        self._fill_priority()
        self._fill_description()
        self._fill_progress()
        self._fill_difficulty()
        self._fill_dates()
        self._fill_author_executor()
        self._fill_deadline()
        self._setup_tags()
        self._setup_pause_indicator()

    def _fill_title(self):
        title = self.task_data.get("title", "")
        self.taskTitleLabel.setText(title if title else "Без названия")
        self.taskTitleLabel.setWordWrap(True)
        self.taskTitleLabel.setMinimumHeight(30)

    def _fill_project(self):
        project_name = self.task_data.get("project_name", "")
        if project_name:
            self.projectButton.setText(f"📁 {project_name}")
            self.projectButton.show()
            self.projectLabel.show()
        else:
            self.projectButton.hide()
            self.projectLabel.hide()

    def _fill_priority(self):
        priority_text = self.task_data.get("priority_text", "")
        priority_color = self.task_data.get("priority_color", "#FFA726")

        if priority_text:
            self.priorityValueLabel.setText(priority_text)
            self.priorityValueLabel.setStyleSheet(
                f"background-color:{priority_color};"
                "color:white;border-radius:6px;padding:6px 12px;font-weight:bold;"
            )
            self.priorityValueLabel.show()
            self.priorityLabel.show()
        else:
            self.priorityValueLabel.hide()
            self.priorityLabel.hide()

    def _fill_description(self):
        description = self.task_data.get("description", "")
        if description and description.strip():
            import re
            clean_description = re.sub(r'<[^>]+>', '', description)
            clean_description = clean_description.strip()
            if not clean_description:
                clean_description = description[:100]
            if len(clean_description) > 100:
                clean_description = clean_description[:100] + "..."

            self.descriptionText.setPlainText(clean_description)
            self.descriptionText.show()

            self.descriptionText.document().adjustSize()
            doc_height = self.descriptionText.document().size().height()
            new_height = min(max(int(doc_height) + 10, 40), 80)
            self.descriptionText.setFixedHeight(new_height)
        else:
            self.descriptionText.hide()
            self.descriptionText.setFixedHeight(0)

    def _fill_progress(self):
        progress = self.task_data.get("progress_percent", 0)
        self.overallProgress.setValue(int(progress))
        self.overallProgress.setFormat(f"Общий прогресс: {int(progress)}%")
        self.overallProgress.setStyleSheet(TaskCardStyles.PROGRESS_STYLE)

    def _fill_difficulty(self):
        difficulty = self.task_data.get("difficulty", 0)
        self._set_difficulty_display(difficulty)

    def _fill_dates(self):
        created_text = self.task_data.get("created_text", "")
        if created_text:
            self.createdLabel.setText(f"Создана: {created_text}")
            self.createdLabel.show()
        else:
            self.createdLabel.hide()

        updated_text = self.task_data.get("updated_text", "")
        created_text_simple = self.task_data.get("created_text", "")
        if updated_text and updated_text != created_text_simple:
            self.updatedLabel.setText(f"Обновление: {updated_text}")
            self.updatedLabel.show()
        else:
            self.updatedLabel.hide()

    def _fill_author_executor(self):
        author = self.task_data.get("author_text", "")
        if author:
            self.authorLabel.setText(f"Автор: {author}")
            self.authorLabel.show()
        else:
            self.authorLabel.hide()

        executor = self.task_data.get("executor_text", "")
        if executor:
            self.executorLabel.setText(f"Исполнитель: {executor}")
            self.executorLabel.show()
        else:
            self.executorLabel.hide()

    def _fill_deadline(self):
        deadline_text = self.task_data.get("deadline_text", "")
        if deadline_text:
            self.deadlineLabel.setText(f"Срок выполнения: {deadline_text}")
            deadline_color = self.task_data.get('deadline_color', '#666')
            self.deadlineLabel.setStyleSheet(
                f"font-size: 11px; color: {deadline_color}; font-weight: bold; border: none;"
            )
            self.deadlineLabel.show()
        else:
            self.deadlineLabel.hide()

    # ==========================================================
    # ОТОБРАЖЕНИЕ СЛОЖНОСТИ
    # ==========================================================

    def _set_difficulty_display(self, difficulty):
        try:
            value = float(difficulty) if difficulty else 0
        except (ValueError, TypeError):
            value = 0

        value = max(0, min(5, value))
        display_value = int(value) if value == int(value) else value

        self.difficulty_value_label.setText(f"{display_value}⭐")

        # Получаем стиль для значения сложности
        style = self._get_difficulty_style(value)
        self.difficulty_value_label.setStyleSheet(f"""
            font-size: 11px;
            font-weight: bold;
            color: {style['color']};
            background-color: {style['bg']};
            border-radius: 10px;
            padding: 2px 8px;
        """)

        self.difficulty_widget.setVisible(value > 0)

    def _get_difficulty_style(self, value: float) -> dict:
        """Возвращает стиль для сложности"""
        if value >= 4:
            return {"color": "#D22730", "bg": "#FFEBEE"}
        elif value >= 3:
            return {"color": "#FF9800", "bg": "#FFF3E0"}
        elif value >= 1:
            return {"color": "#4CAF50", "bg": "#E8F5E9"}
        else:
            return {"color": "#9E9E9E", "bg": "#F5F5F5"}

    # ==========================================================
    # ОТОБРАЖЕНИЕ ТЕГОВ
    # ==========================================================

    def _setup_tags(self):
        """Настраивает отображение тегов"""
        self._clear_tags()
        tags = self.task_data.get("tags", [])

        if not tags:
            self._hide_tags_container()
            return

        grid_layout = self._create_tag_grid(tags)
        self.tagsLayout.addLayout(grid_layout)
        self._show_tags_container()
        self.updateGeometry()

    def _clear_tags(self):
        """Очищает существующие теги"""
        while self.tagsLayout.count():
            item = self.tagsLayout.takeAt(0)

    def _create_tag_grid(self, tags: list) -> QGridLayout:
        """Создает сетку тегов"""
        grid = QGridLayout()
        grid.setSpacing(4)
        grid.setContentsMargins(0, 0, 0, 0)

        row, col = 0, 0
        max_cols = 3

        for tag_name in tags:
            tag_button = self._create_tag_button(tag_name)
            grid.addWidget(tag_button, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        return grid

    def _create_tag_button(self, tag_name: str) -> QPushButton:
        """Создает кнопку тега"""
        tag_button = QPushButton(tag_name)
        tag_button.setStyleSheet(TaskCardStyles.TAG_STYLE)
        tag_button.setCursor(Qt.CursorShape.PointingHandCursor)
        tag_button.setFixedHeight(24)
        tag_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        return tag_button

    def _hide_tags_container(self):
        tags_widget = self.tagsLayout.parentWidget()
        if tags_widget:
            tags_widget.hide()

    def _show_tags_container(self):
        tags_widget = self.tagsLayout.parentWidget()
        if tags_widget:
            tags_widget.show()

    # ==========================================================
    # ПАУЗА
    # ==========================================================

    def _setup_pause_indicator(self):
        """Настраивает индикатор паузы"""
        self._remove_pause_indicator()
        if self.task_data.get("is_paused", False):
            self._add_pause_indicator()

    def _add_pause_indicator(self):
        pause_indicator = QLabel("ПАУЗА")
        pause_indicator.is_pause_indicator = True
        pause_indicator.setStyleSheet(TaskCardStyles.PAUSE_STYLE)
        self.titleLayout.insertWidget(0, pause_indicator)

    def _remove_pause_indicator(self):
        for i in range(self.titleLayout.count()):
            widget = self.titleLayout.itemAt(i).widget()
            if widget and hasattr(widget, 'is_pause_indicator') and widget.is_pause_indicator:
                widget.deleteLater()
                break

    def _update_pause_indicator(self):
        """Обновляет индикатор паузы (вызывается извне)"""
        self._setup_pause_indicator()

    # ==========================================================
    # КОНТЕКСТНОЕ МЕНЮ
    # ==========================================================

    def _show_context_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(TaskCardStyles.MENU_STYLE)

        duplicate_action = menu.addAction("Дублировать")

        is_paused = self.task_data.get("is_paused", False)
        is_completed = self.task_data.get("completed", False)

        pause_action = None
        if not is_completed:
            pause_action = menu.addAction("Возобновить" if is_paused else "Пауза")

        archive_action = menu.addAction("Архивировать") if self._archive_enabled else None
        delete_action = menu.addAction("Удалить") if self._delete_enabled else None

        action = menu.exec(self.menuButton.mapToGlobal(QPoint(0, self.menuButton.height())))

        if action == duplicate_action:
            self.duplicate_requested.emit(self.task_id)
        elif pause_action and action == pause_action:
            if is_paused:
                self.resume_requested.emit(self.task_id)
            else:
                self.pause_requested.emit(self.task_id)
        elif archive_action and action == archive_action:
            self.archive_requested.emit(self.task_id)
        elif delete_action and action == delete_action:
            self.delete_requested.emit(self.task_id)

    # ==========================================================
    # ОБНОВЛЕНИЕ ДАННЫХ
    # ==========================================================

    def update_task_data(self, new_data):
        self.task_data.update(new_data)
        self.task_id = self.task_data.get("id")
        self.fill_ui()

    # ==========================================================
    # ОБРАБОТКА СОБЫТИЙ
    # ==========================================================

    def _on_progress_click(self, event):
        width = self.overallProgress.width()
        pos_x = event.position().x()
        percent = int((pos_x / width) * 100)
        percent = max(0, min(100, percent))

        self._updating_progress = True
        self.overallProgress.setValue(percent)
        self.overallProgress.setFormat(f"Общий прогресс: {percent}%")
        self._updating_progress = False

        self.task_data["progress_percent"] = percent
        self.progress_changed.emit(self.task_id, percent)

    def _on_project_clicked(self):
        project_id = self.task_data.get("project_id")
        if project_id:
            self.project_clicked.emit(project_id)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        if not self.drag_start_position:
            return

        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        self._start_drag()

    def _start_drag(self):
        self.drag_started.emit(self.task_data)

        drag = QDrag(self)
        mime = QMimeData()

        task_json = json.dumps(self.task_data, ensure_ascii=False, default=str)
        mime.setData("application/x-task", task_json.encode("utf-8"))

        drag.setMimeData(mime)

        pixmap = self._create_drag_pixmap()
        drag.setPixmap(pixmap)
        drag.setHotSpot(self.drag_start_position)

        drag.exec(Qt.DropAction.MoveAction)

    def _create_drag_pixmap(self) -> QPixmap:
        pixmap = QPixmap(self.size())
        painter = QPainter(pixmap)
        painter.setOpacity(0.7)
        self.render(painter)
        painter.end()
        return pixmap

    # ==========================================================
    # РАЗМЕРЫ
    # ==========================================================

    def sizeHint(self):
        return QSize(300, super().sizeHint().height())

    def minimumSizeHint(self):
        return QSize(280, 100)