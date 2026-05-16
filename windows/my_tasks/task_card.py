# windows/my_tasks/task_card.py

import json
import os

from PyQt6 import uic
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QPoint
from PyQt6.QtGui import QDrag, QPixmap, QPainter
from PyQt6.QtWidgets import QFrame, QPushButton, QMenu, QApplication, QSizePolicy, QLabel


class TaskCard(QFrame):
    """UI карточки задачи - только отображение и сигналы"""

    edit_requested = pyqtSignal(int)  # task_id
    delete_requested = pyqtSignal(int)  # task_id
    archive_requested = pyqtSignal(int)  # task_id
    duplicate_requested = pyqtSignal(int)  # task_id
    pause_requested = pyqtSignal(int)  # task_id
    resume_requested = pyqtSignal(int)  # task_id
    move_requested = pyqtSignal(int, str)  # task_id, new_status
    drag_started = pyqtSignal(dict)  # task_data
    progress_changed = pyqtSignal(int, int)  # task_id, new_progress_percent

    def __init__(self, task_data, parent=None):
        super().__init__(parent)

        self.task_data = task_data
        self.task_id = task_data.get("id")
        self.drag_start_position = None
        self._updating_progress = False

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "my_tasks"
        )

        uic.loadUi(os.path.join(ui_path, "task_card.ui"), self)

        self.setObjectName("TaskCard")
        self.setAcceptDrops(True)

        # Настройка размеров
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.setMaximumWidth(330)
        self.setMinimumWidth(300)
        self.setMinimumHeight(0)
        self.setContentsMargins(0, 0, 0, 0)

        # Делаем прогресс-бар кликабельным через установку обработчика
        self.overallProgress.mousePressEvent = self._on_progress_click

        self.fill_ui()
        self.menuButton.clicked.connect(self._show_context_menu)

    def _on_progress_click(self, event):
        """Обработчик клика по прогресс-бару для изменения значения"""
        print(f"\n🔍 [DEBUG] _on_progress_click: начало")
        print(f"   - task_id: {self.task_id}")
        print(f"   - widget: {self}")
        print(f"   - parent: {self.parent()}")
        print(f"   - isVisible: {self.isVisible()}")

        # Вычисляем процент по позиции клика
        width = self.overallProgress.width()
        pos_x = event.position().x()
        percent = int((pos_x / width) * 100)
        percent = max(0, min(100, percent))

        print(f"   - ширина: {width}, позиция: {pos_x}, процент: {percent}")
        print(f"   - старый прогресс: {self.task_data.get('progress_percent', 0)}%")

        # Обновляем отображение
        self._updating_progress = True
        self.overallProgress.setValue(percent)
        self.overallProgress.setFormat(f"Общий прогресс: {percent}%")
        self._updating_progress = False

        # Сохраняем в данные
        self.task_data["progress_percent"] = percent

        print(f"   - отправляем сигнал progress_changed")
        # Отправляем сигнал для сохранения в БД
        self.progress_changed.emit(self.task_id, percent)

        print(f"🔍 [DEBUG] _on_progress_click: конец, карточка должна остаться")
        print(f"   - self.isVisible(): {self.isVisible()}\n")

    def hideEvent(self, event):
        """Отслеживаем, когда карточка скрывается"""
        print(f"\n⚠️ [DEBUG] hideEvent для задачи {self.task_id}")
        print(f"   - widget: {self}")
        print(f"   - parent: {self.parent()}")
        print(f"   - reason: {event}")
        super().hideEvent(event)

    def deleteLater(self):
        """Отслеживаем удаление карточки"""
        print(f"\n⚠️ [DEBUG] deleteLater для задачи {self.task_id}")
        super().deleteLater()

    def fill_ui(self):
        """Заполнение карточки данными из task_data"""
        # Название задачи
        title = self.task_data.get("title", "")
        self.taskTitleLabel.setText(title if title else "Без названия")

        # Проект
        project_name = self.task_data.get("project_name", "")
        if project_name:
            self.projectButton.setText(f"📁 {project_name}")
            self.projectButton.show()
            self.projectLabel.show()
        else:
            self.projectButton.hide()
            self.projectLabel.hide()

        # Приоритет
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

        # Описание
        description = self.task_data.get("description", "")
        if description and description.strip():
            self.descriptionText.setPlainText(description[:100] + ("..." if len(description) > 100 else ""))
            self.descriptionText.show()
            doc_height = self.descriptionText.document().size().height()
            self.descriptionText.setFixedHeight(min(int(doc_height) + 10, 80))
        else:
            self.descriptionText.hide()
            self.descriptionText.setFixedHeight(0)

        # ===== ПРОГРЕСС-БАР (обновляем значение) =====
        progress = self.task_data.get("progress_percent", 0)
        # Убираем блокировку по completed
        # completed = self.task_data.get("completed", False)

        self.overallProgress.setValue(int(progress))
        self.overallProgress.setFormat(f"Общий прогресс: {int(progress)}%")

        # Простой стиль для всех задач (без блокировки)
        self.overallProgress.setStyleSheet("""
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
            """)

        # Дата создания
        created_text = self.task_data.get("created_text", "")
        if created_text:
            self.createdLabel.setText(f"📅 Создана: {created_text}")
            self.createdLabel.show()
        else:
            self.createdLabel.hide()

        # Дата обновления
        updated_text = self.task_data.get("updated_text", "")
        created_text_simple = self.task_data.get("created_text", "")
        if updated_text and updated_text != created_text_simple:
            self.updatedLabel.setText(f"🔄 Обновление: {updated_text}")
            self.updatedLabel.show()
        else:
            self.updatedLabel.hide()

        # Автор
        author = self.task_data.get("author_text", "")
        if author:
            self.authorLabel.setText(f"👤 Автор: {author}")
            self.authorLabel.show()
        else:
            self.authorLabel.hide()

        # Исполнитель
        executor = self.task_data.get("executor_text", "")
        if executor:
            self.executorLabel.setText(f"👥 Исполнитель: {executor}")
            self.executorLabel.show()
        else:
            self.executorLabel.hide()

        # Дедлайн
        deadline_text = self.task_data.get("deadline_text", "")
        if deadline_text:
            self.deadlineLabel.setText(f"⏰ {deadline_text}")
            deadline_color = self.task_data.get('deadline_color', '#666')
            self.deadlineLabel.setStyleSheet(
                f"font-size: 11px; color: {deadline_color}; font-weight: bold;"
            )
            self.deadlineLabel.show()
        else:
            self.deadlineLabel.hide()

        # Сложность
        difficulty = self.task_data.get("difficulty", 0)
        self._set_difficulty_display(difficulty)

        # Теги
        self._setup_tags()

        self._setup_pause_indicator()

        # Обновляем размер
        self.adjustSize()
        self.updateGeometry()

    def _set_difficulty_display(self, difficulty):
        """Устанавливает отображение сложности"""
        if not hasattr(self, 'difficultyValueLabel'):
            return

        try:
            value = float(difficulty) if difficulty else 0
        except (ValueError, TypeError):
            value = 0

        value = max(0, min(5, value))

        if value == int(value):
            display_value = int(value)
        else:
            display_value = value

        self.difficultyValueLabel.setText(f"{display_value}⭐")

        if value >= 4:
            color = "#D22730"
            bg_color = "#FFEBEE"
        elif value >= 3:
            color = "#FF9800"
            bg_color = "#FFF3E0"
        elif value >= 1:
            color = "#4CAF50"
            bg_color = "#E8F5E9"
        else:
            color = "#9E9E9E"
            bg_color = "#F5F5F5"

        self.difficultyValueLabel.setStyleSheet(f"""
            font-size: 12px;
            font-weight: bold;
            color: {color};
            background-color: {bg_color};
            border-radius: 10px;
            padding: 2px 8px;
        """)

        difficulty_widget = self.difficultyLayout.parentWidget()
        if difficulty_widget:
            difficulty_widget.setVisible(value > 0)

    def _setup_tags(self):
        """Настройка отображения тегов"""
        for i in reversed(range(self.tagsLayout.count())):
            w = self.tagsLayout.itemAt(i).widget()
            if w:
                w.deleteLater()

        tags = self.task_data.get("tags", [])

        tags_widget = self.tagsLayout.parentWidget()
        if tags:
            for tag in tags[:3]:
                tag_str = tag.name if hasattr(tag, 'name') else str(tag)
                tag_button = QPushButton(tag_str)
                tag_button.setStyleSheet("""
                    QPushButton{
                        font-size: 10px;
                        padding: 2px 8px;
                        border-radius: 10px;
                        background: #E8F5E9;
                        color: #2E7D32;
                        border: 1px solid #C8E6C9;
                    }
                """)
                tag_button.setCursor(Qt.CursorShape.PointingHandCursor)
                tag_button.setFixedHeight(22)
                self.tagsLayout.addWidget(tag_button)

            if len(tags) > 3:
                more_btn = QPushButton(f"+{len(tags) - 3}")
                more_btn.setStyleSheet("""
                    QPushButton{
                        font-size: 10px;
                        padding: 2px 8px;
                        border-radius: 10px;
                        background: #EEEEEE;
                        color: #555555;
                        border: none;
                    }
                """)
                self.tagsLayout.addWidget(more_btn)

            if tags_widget:
                tags_widget.show()
        else:
            if tags_widget:
                tags_widget.hide()

        self.tagsLayout.addStretch()

    def _show_context_menu(self):
        """Показывает контекстное меню"""
        menu = QMenu(self)
        menu.setStyleSheet("""
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
        """)

        # Дублировать
        duplicate_action = menu.addAction("📋 Дублировать")

        menu.addSeparator()

        # Пауза/Возобновление (только для активных задач)
        is_paused = self.task_data.get("is_paused", False)
        is_completed = self.task_data.get("completed", False)

        pause_action = None
        if not is_completed:
            if is_paused:
                pause_action = menu.addAction("▶️ Возобновить")
            else:
                pause_action = menu.addAction("⏸️ Пауза")
            menu.addSeparator()

        # Архивировать
        archive_action = menu.addAction("📦 Архивировать")

        # Удалить
        delete_action = menu.addAction("🗑️ Удалить")

        action = menu.exec(self.menuButton.mapToGlobal(QPoint(0, self.menuButton.height())))

        if action == duplicate_action:
            self.duplicate_requested.emit(self.task_id)
        elif pause_action and action == pause_action:
            if is_paused:
                self.resume_requested.emit(self.task_id)
            else:
                self.pause_requested.emit(self.task_id)
        elif action == archive_action:
            self.archive_requested.emit(self.task_id)
        elif action == delete_action:
            self.delete_requested.emit(self.task_id)

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

        # Сигнал о начале перетаскивания
        self.drag_started.emit(self.task_data)

        drag = QDrag(self)
        mime = QMimeData()

        task_json = json.dumps(self.task_data, ensure_ascii=False, default=str)
        mime.setData("application/x-task", task_json.encode("utf-8"))

        drag.setMimeData(mime)

        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setOpacity(0.7)
        self.render(painter)
        painter.end()

        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())

        drag.exec(Qt.DropAction.MoveAction)

    def _update_pause_indicator(self):
        """Обновляет индикатор паузы в карточке"""
        is_paused = self.task_data.get("is_paused", False)

        # Ищем существующий индикатор паузы в titleLayout
        pause_indicator = None
        for i in range(self.titleLayout.count()):
            widget = self.titleLayout.itemAt(i).widget()
            if widget and hasattr(widget, 'is_pause_indicator') and widget.is_pause_indicator:
                pause_indicator = widget
                break

        if is_paused:
            if not pause_indicator:
                # Создаём новый индикатор
                from PyQt6.QtWidgets import QLabel
                pause_indicator = QLabel("⏸️ ПАУЗА")
                pause_indicator.is_pause_indicator = True
                pause_indicator.setStyleSheet("""
                    background-color: #FF9800;
                    color: white;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 2px 8px;
                    border-radius: 10px;
                """)
                # Вставляем в начало titleLayout
                self.titleLayout.insertWidget(0, pause_indicator)
        else:
            if pause_indicator:
                pause_indicator.deleteLater()

    def _setup_pause_indicator(self):
        """Настраивает индикатор паузы при инициализации"""
        is_paused = self.task_data.get("is_paused", False)
        if is_paused:
            from PyQt6.QtWidgets import QLabel
            pause_indicator = QLabel("⏸️ ПАУЗА")
            pause_indicator.is_pause_indicator = True
            pause_indicator.setStyleSheet("""
                background-color: #FF9800;
                color: white;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 8px;
                border-radius: 10px;
            """)
            # Вставляем в начало titleLayout
            self.titleLayout.insertWidget(0, pause_indicator)

    def update_task_data(self, new_data):
        """Обновляет данные карточки"""
        self.task_data.update(new_data)
        self.task_id = self.task_data.get("id")
        self.fill_ui()