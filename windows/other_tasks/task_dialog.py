# windows/other_tasks/task_dialog.py - исправленный

import os
from typing import Dict, Optional, List
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox, QListWidgetItem, QPushButton, QHBoxLayout, QWidget, QLabel, \
    QVBoxLayout, QFrame
from PyQt6.QtCore import QDate, QDateTime, pyqtSignal, Qt
from PyQt6.QtGui import QFont

from services.tasks_service import TasksService


class TagWidget(QWidget):
    """Виджет для отображения отдельного тега с кнопкой удаления"""
    tag_removed = pyqtSignal(str)

    def __init__(self, tag_name: str, color: str = "#ccab6e", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        self.tag_button = QPushButton(f"#{tag_name}")
        self.tag_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}20;
                color: {color};
                border: 1px solid {color};
                border-radius: 10px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}40;
            }}
        """)
        self.tag_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.remove_button = QPushButton("✕")
        self.remove_button.setFixedSize(18, 18)
        self.remove_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {color};
                border: none;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: #D22730;
            }}
        """)
        self.remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_button.clicked.connect(lambda: self.tag_removed.emit(tag_name))

        layout.addWidget(self.tag_button)
        layout.addWidget(self.remove_button)
        layout.addStretch()

        self.tag_name = tag_name


class TaskDialog(QDialog):
    task_saved = pyqtSignal(int, dict)

    def __init__(
            self,
            parent=None,
            task_data: Optional[Dict] = None,
            mode="create",
            current_user=None
    ):
        super().__init__(parent)

        self.service: Optional[TasksService] = None
        self.task_data = task_data
        self.mode = mode
        self.current_user = current_user or {"id": 1, "last_name": "Копейкина", "first_name": "Виктория",
                                             "middle_name": "Анатольевна"}
        self.selected_tags = []

        # Загружаем UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "other_tasks", "task_dialog.ui")
        uic.loadUi(ui_path, self)

        # Настройка UI
        self.setup_ui()

        if hasattr(self, 'createBtn'):
            self.createBtn.clicked.connect(self.validate_and_save)

        # Настройка работы с тегами
        self.setup_tags_ui()

    def setup_tags_ui(self):
        """Настраивает UI для работы с тегами"""
        # Создаем контейнер для тегов, если его нет
        if not hasattr(self, 'tags_container'):
            # Создаем фрейм для тегов
            self.tags_frame = QFrame(self)
            self.tags_frame.setFrameShape(QFrame.Shape.StyledPanel)
            self.tags_frame.setStyleSheet("""
                QFrame {
                    background-color: #f0f0f0;
                    border-radius: 8px;
                    border: 1px solid #e0e0e0;
                    min-height: 50px;
                }
            """)
            self.tags_container = QVBoxLayout(self.tags_frame)
            self.tags_container.setContentsMargins(10, 10, 10, 10)
            self.tags_container.setSpacing(8)

            # Вставляем фрейм с тегами после comboBoxTag
            if hasattr(self, 'verticalLayout'):
                # Находим индекс comboBoxTag
                for i in range(self.verticalLayout.count()):
                    item = self.verticalLayout.itemAt(i)
                    if item and item.widget() == self.comboBoxTag:
                        self.verticalLayout.insertWidget(i + 1, self.tags_frame)
                        break

        # Очищаем контейнер
        self.clear_tags_container()

        # Настройка comboBox для выбора тегов - ИСПРАВЛЕНО ИМЯ
        if hasattr(self, 'comboBoxTag'):
            self.comboBoxTag.setEditable(True)
            self.comboBoxTag.lineEdit().setPlaceholderText("Введите название темы или выберите из списка...")
            self.comboBoxTag.lineEdit().returnPressed.connect(self.add_tag_from_input)
            self.comboBoxTag.activated.connect(self.on_tag_selected)
            print("✅ Настройка comboBoxTag завершена")

    def clear_tags_container(self):
        """Очищает контейнер с тегами"""
        if hasattr(self, 'tags_container'):
            while self.tags_container.count():
                item = self.tags_container.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

    def update_tags_display(self):
        """Обновляет отображение выбранных тегов"""
        self.clear_tags_container()

        if not self.selected_tags:
            label = QLabel("Темы не выбраны")
            label.setStyleSheet("color: #999; font-style: italic;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tags_container.addWidget(label)
            return

        for tag_name in self.selected_tags:
            tag_color = "#ccab6e"
            if self.service:
                all_tags = self.service.get_all_tags()
                for tag in all_tags:
                    if tag["name"] == tag_name:
                        tag_color = tag.get("color", "#ccab6e")
                        break

            tag_widget = TagWidget(tag_name, tag_color)
            tag_widget.tag_removed.connect(self.remove_tag)
            self.tags_container.addWidget(tag_widget)

        self.tags_container.addStretch()

    def add_tag_from_input(self):
        """Добавляет тег из поля ввода"""
        if not hasattr(self, 'comboBoxTag'):
            return

        tag_text = self.comboBoxTag.lineEdit().text().strip()
        if not tag_text:
            return

        if tag_text in self.selected_tags:
            self.comboBoxTag.lineEdit().clear()
            return

        self.selected_tags.append(tag_text)
        self.update_tags_display()
        self.comboBoxTag.lineEdit().clear()

    def on_tag_selected(self, index):
        """Обрабатывает выбор тега из выпадающего списка"""
        if not hasattr(self, 'comboBoxTag'):
            return

        if index < 0:
            return

        tag_name = self.comboBoxTag.itemText(index)
        if not tag_name or tag_name == "Выберите тему или введите новую...":
            return

        if tag_name not in self.selected_tags:
            self.selected_tags.append(tag_name)
            self.update_tags_display()

        self.comboBoxTag.setCurrentIndex(0)

    def remove_tag(self, tag_name: str):
        """Удаляет тег из списка выбранных"""
        if tag_name in self.selected_tags:
            self.selected_tags.remove(tag_name)
            self.update_tags_display()

    def get_selected_tags(self) -> List[str]:
        return self.selected_tags

    def format_creator_name(self) -> str:
        last = self.current_user.get('last_name', '')
        first = self.current_user.get('first_name', '')
        middle = self.current_user.get('middle_name', '')

        if last and first:
            first_initial = first[0] + '.' if first else ''
            middle_initial = middle[0] + '.' if middle else ''
            return f"{last} {first_initial}{middle_initial}"
        return "Неизвестен"

    def get_current_datetime_str(self) -> str:
        now = QDateTime.currentDateTime()
        return now.toString("dd.MM.yyyy hh:mm")

    def setup_ui(self):
        if self.mode == "create":
            self.setWindowTitle("Создание задачи")
            if hasattr(self, 'createBtn'):
                self.createBtn.setText("Создать")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Создание новой задачи")

            if hasattr(self, 'createdAtLabel'):
                current_datetime = self.get_current_datetime_str()
                self.createdAtLabel.setText(f"Создано: {current_datetime}")
                self.createdAtLabel.show()

            if hasattr(self, 'updatedAtLabel'):
                self.updatedAtLabel.hide()

        else:
            self.setWindowTitle("Редактирование задачи")
            if hasattr(self, 'createBtn'):
                self.createBtn.setText("Сохранить")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Редактирование задачи")

            if hasattr(self, 'createdAtLabel'):
                self.createdAtLabel.show()
            if hasattr(self, 'updatedAtLabel'):
                self.updatedAtLabel.show()

        if hasattr(self, 'createdByLabel'):
            creator_name = self.format_creator_name()
            self.createdByLabel.setText(f"Создатель: {creator_name}")

    def update_dates_info(self, task_data: Dict):
        if hasattr(self, 'createdAtLabel') and task_data.get('created_at'):
            self.createdAtLabel.setText(f"Создано: {task_data['created_at']}")

        if hasattr(self, 'updatedAtLabel') and task_data.get('updated_at'):
            self.updatedAtLabel.setText(f"Изменено: {task_data['updated_at']}")

    def set_service(self, service: TasksService):
        self.service = service
        self.load_dialog_data()

    def load_dialog_data(self):
        if not self.service:
            return

        dialog_data = self.service.prepare_dialog_data(self.mode, self.task_data)
        print(
            f"📊 Загружено данных для диалога: проектов={len(dialog_data.get('projects', []))}, тегов={len(dialog_data.get('tags', []))}")

        # Загружаем проекты
        if hasattr(self, 'comboBoxProject'):
            self.comboBoxProject.clear()
            self.comboBoxProject.addItem("Выберите проект", None)
            for project in dialog_data.get("projects", []):
                self.comboBoxProject.addItem(project["name"], project["id"])

        # Загружаем статусы
        if hasattr(self, 'comboBoxStatus'):
            self.comboBoxStatus.clear()
            for status in dialog_data.get("statuses", []):
                self.comboBoxStatus.addItem(status["name"], status["id"])

        # Загружаем исполнителей
        if hasattr(self, 'comboBoxAssignee'):
            self.comboBoxAssignee.clear()
            self.comboBoxAssignee.addItem("Не назначен", None)
            for emp in dialog_data.get("employees", []):
                self.comboBoxAssignee.addItem(emp["display_name"], emp["id"])

        # Загружаем приоритеты
        if hasattr(self, 'comboBoxPriority'):
            # Оставляем как есть, они уже есть в UI
            pass

        # Загружаем теги в выпадающий список - ИСПРАВЛЕНО ИМЯ
        if hasattr(self, 'comboBoxTag'):
            self.comboBoxTag.clear()
            self.comboBoxTag.addItem("Выберите тему или введите новую...", None)
            for tag in dialog_data.get("tags", []):
                self.comboBoxTag.addItem(tag["name"], tag["id"])
            print(f"✅ Загружено {len(dialog_data.get('tags', []))} тегов в comboBoxTag")

        # Если режим редактирования - заполняем данные
        if self.mode == "edit" and "task_data" in dialog_data:
            self.fill_task_data(dialog_data["task_data"])

    def fill_task_data(self, task_data: Dict):
        if hasattr(self, 'lineEditTitle'):
            self.lineEditTitle.setText(task_data.get("title", ""))

        if hasattr(self, 'textEditDescription'):
            self.textEditDescription.setPlainText(task_data.get("description", ""))

        if hasattr(self, 'comboBoxPriority'):
            priority = task_data.get("priority", "Средний")
            index = self.comboBoxPriority.findText(priority)
            if index >= 0:
                self.comboBoxPriority.setCurrentIndex(index)

        if hasattr(self, 'comboBoxStatus'):
            status = task_data.get("status", "")
            for i in range(self.comboBoxStatus.count()):
                if self.comboBoxStatus.itemText(i) == status:
                    self.comboBoxStatus.setCurrentIndex(i)
                    break

        if hasattr(self, 'comboBoxAssignee'):
            assigned_to = task_data.get("assigned_to")
            if assigned_to:
                for i in range(self.comboBoxAssignee.count()):
                    if self.comboBoxAssignee.itemData(i) == assigned_to:
                        self.comboBoxAssignee.setCurrentIndex(i)
                        break

        if hasattr(self, 'dateEditDeadline') and task_data.get("deadline"):
            deadline = task_data["deadline"]
            if isinstance(deadline, str) and deadline:
                try:
                    date_parts = deadline.split('.')
                    if len(date_parts) == 3:
                        qdate = QDate(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
                        self.dateEditDeadline.setDate(qdate)
                except:
                    pass

        # Загружаем теги
        if task_data.get("tags"):
            self.selected_tags = task_data["tags"].copy()
            self.update_tags_display()

        self.update_dates_info(task_data)

    def collect_form_data(self) -> Dict:
        data = {}

        if hasattr(self, 'lineEditTitle'):
            data["title"] = self.lineEditTitle.text().strip()

        if hasattr(self, 'textEditDescription'):
            data["description"] = self.textEditDescription.toPlainText().strip()

        if hasattr(self, 'comboBoxProject'):
            data["project_id"] = self.comboBoxProject.currentData()

        if hasattr(self, 'comboBoxAssignee'):
            data["assigned_to"] = self.comboBoxAssignee.currentData()

        if hasattr(self, 'comboBoxPriority'):
            data["priority"] = self.comboBoxPriority.currentText()

        if hasattr(self, 'comboBoxStatus'):
            data["status"] = self.comboBoxStatus.currentText()

        if hasattr(self, 'dateEditDeadline'):
            data["due_date"] = self.dateEditDeadline.date().toString("yyyy-MM-dd")

        data["tags"] = self.selected_tags.copy()

        return data

    def validate_and_save(self):
        print("\n=== ОТЛАДКА: Диалог сохранения задачи ===")

        if not self.service:
            print("❌ Сервис не инициализирован")
            QMessageBox.critical(self, "Ошибка", "Сервис не инициализирован")
            return

        form_data = self.collect_form_data()
        print(f"Собранные данные из формы: {form_data}")

        error = self.service.validate_form_data(form_data)
        if error:
            print(f"❌ Ошибка валидации: {error}")
            QMessageBox.warning(self, "Ошибка", error)
            return

        print("✅ Валидация пройдена")

        try:
            task_data = self.service.process_form_data(form_data, self.current_user)
            print(f"Подготовленные данные: {task_data}")

            if self.mode == "edit" and self.task_data:
                task_id = self.task_data.get("id")
                print(f"📤 Отправка сигнала task_saved с ID: {task_id}")
                self.task_saved.emit(task_id, task_data)
            else:
                print("📤 Отправка сигнала task_saved для создания")
                self.task_saved.emit(None, task_data)

            print("✅ Сигнал отправлен")
            self.accept()
            print("✅ Диалог закрыт")

        except Exception as e:
            print(f"❌ ИСКЛЮЧЕНИЕ: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {str(e)}")