# windows/other_tasks/task_dialog.py

import os
from typing import Dict, Optional, List
from PyQt6 import uic, QtWidgets
from PyQt6.QtWidgets import QDialog, QMessageBox, QVBoxLayout, QWidget, QScrollArea, QLineEdit, QPushButton, QHBoxLayout, QCheckBox
from PyQt6.QtCore import QDate, QDateTime, pyqtSignal, Qt, QEvent, QPoint

from services.tasks_service.tasks_service import TasksService


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
        self.selected_tag_ids = set()
        self.all_tags = []
        self.selected_assignee_ids = []  # Список ID выбранных исполнителей

        # Загружаем UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "other_tasks", "task_dialog.ui")
        uic.loadUi(ui_path, self)

        # Настройка popup для выбора тегов
        self.setup_tags_popup()

        # Настройка popup для выбора исполнителей
        self.setup_assignees_popup()

        # Настройка звезд рейтинга
        self.setup_stars()

        # Настройка UI
        self.setup_ui()

        if hasattr(self, 'createBtn'):
            self.createBtn.clicked.connect(self.validate_and_save)

    def setup_assignees_popup(self):
        """Настройка popup с чекбоксами для выбора исполнителей"""
        if not hasattr(self, 'comboBoxAssignee'):
            print("⚠️ comboBoxAssignee не найден в UI, пропускаем настройку исполнителей")
            return

        self.comboAssignees = self.comboBoxAssignee

        # Настройка комбобокса
        self.comboAssignees.setEditable(True)
        line_edit = self.comboAssignees.lineEdit()
        line_edit.setReadOnly(True)
        line_edit.setCursor(Qt.CursorShape.PointingHandCursor)

        # Создаем popup для исполнителей
        self.assignees_popup = QWidget()
        self.assignees_popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.assignees_popup.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
            QLineEdit {
                border: 2px solid #e9ecef;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #D22730;
            }
            QCheckBox {
                font-size: 13px;
                color: #2c3e50;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #D9D9D6;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #D22730;
                border-color: #D22730;
            }
            QPushButton {
                background-color: #1B232A;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #09131B;
            }
            QScrollArea {
                border: none;
            }
        """)

        popup_layout = QVBoxLayout(self.assignees_popup)
        popup_layout.setContentsMargins(10, 10, 10, 10)
        popup_layout.setSpacing(10)

        # Строка поиска
        self.assignee_search_line = QLineEdit()
        self.assignee_search_line.setPlaceholderText("Поиск исполнителя...")
        self.assignee_search_line.textChanged.connect(self.on_assignee_search_changed)
        popup_layout.addWidget(self.assignee_search_line)

        # Кнопки Выбрать всех / Снять всех
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Выбрать всех")
        clear_all_btn = QPushButton("Снять выделение")
        select_all_btn.clicked.connect(self.select_all_assignees)
        clear_all_btn.clicked.connect(self.clear_all_assignees)
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(clear_all_btn)
        popup_layout.addLayout(btn_layout)

        # Контейнер для чекбоксов с прокруткой
        self.assignees_container = QWidget()
        self.assignees_layout = QVBoxLayout(self.assignees_container)
        self.assignees_layout.setSpacing(8)
        self.assignees_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.assignees_container)
        scroll_area.setMinimumHeight(200)
        scroll_area.setMaximumHeight(300)
        popup_layout.addWidget(scroll_area)

        self.assignee_checkboxes = []
        self.assignee_checkboxes_by_id = {}

        # Устанавливаем event filter для комбобокса
        self.comboAssignees.installEventFilter(self)
        line_edit.installEventFilter(self)

    def load_assignees_into_popup(self):
        """Загружает исполнителей в popup"""
        if not self.service:
            return

        # Очищаем существующие чекбоксы
        for cb in self.assignee_checkboxes:
            self.assignees_layout.removeWidget(cb)
            cb.deleteLater()
        self.assignee_checkboxes.clear()
        self.assignee_checkboxes_by_id.clear()

        # Получаем данные из сервиса
        dialog_data = self.service.prepare_dialog_data(self.mode, self.task_data)
        employees = dialog_data.get("employees", [])

        # Создаем чекбоксы для каждого сотрудника
        for emp in employees:
            cb = QCheckBox(emp["display_name"])
            cb.setProperty("employee_id", emp["id"])
            cb.setProperty("employee_name", emp["display_name"])
            cb.setProperty("search_text", emp["display_name"].lower())
            cb.toggled.connect(lambda checked, eid=emp["id"]: self.on_assignee_toggled(eid, checked))
            cb.setChecked(emp["id"] in self.selected_assignee_ids)
            self.assignee_checkboxes.append(cb)
            self.assignee_checkboxes_by_id[emp["id"]] = cb
            self.assignees_layout.addWidget(cb)

        self.assignees_layout.addStretch()
        self.update_assignees_button_text()

    def on_assignee_search_changed(self, text):
        """Фильтрация чекбоксов по поиску"""
        search_text = self.assignee_search_line.text().lower().strip()
        for cb in self.assignee_checkboxes:
            emp_name = cb.property("employee_name").lower()
            is_visible = not search_text or search_text in emp_name
            cb.setVisible(is_visible)

    def on_assignee_toggled(self, employee_id: int, checked: bool):
        """Обработчик изменения состояния чекбокса исполнителя"""
        if checked:
            if employee_id not in self.selected_assignee_ids:
                self.selected_assignee_ids.append(employee_id)
        else:
            if employee_id in self.selected_assignee_ids:
                self.selected_assignee_ids.remove(employee_id)
        self.update_assignees_button_text()

    def select_all_assignees(self):
        """Выбрать всех видимых исполнителей"""
        for cb in self.assignee_checkboxes:
            if cb.isVisible():
                cb.setChecked(True)

    def clear_all_assignees(self):
        """Снять выделение со всех исполнителей"""
        for cb in self.assignee_checkboxes:
            cb.setChecked(False)

    def update_assignees_button_text(self):
        """Обновляет текст в комбобоксе с выбранными исполнителями"""
        selected_names = []
        for emp_id in self.selected_assignee_ids:
            cb = self.assignee_checkboxes_by_id.get(emp_id)
            if cb:
                name = cb.property("employee_name")
                if name:
                    selected_names.append(name)

        if selected_names:
            text = f"✓ Выбрано ({len(selected_names)}): {', '.join(selected_names[:2])}"
            if len(selected_names) > 2:
                text += f" и ещё {len(selected_names) - 2}"
            self.comboAssignees.lineEdit().setText(text)
        else:
            self.comboAssignees.lineEdit().setText("▼ Выберите исполнителей")

    def get_selected_assignees(self) -> List[int]:
        """Возвращает список ID выбранных исполнителей"""
        return self.selected_assignee_ids.copy()

    def set_selected_assignees(self, assignee_ids: List[int]):
        """Устанавливает выбранных исполнителей"""
        self.selected_assignee_ids = assignee_ids.copy() if assignee_ids else []
        for cb in self.assignee_checkboxes:
            emp_id = cb.property("employee_id")
            cb.setChecked(emp_id in self.selected_assignee_ids)
        self.update_assignees_button_text()

    def setup_tags_popup(self):
        """Настройка popup с чекбоксами для выбора тегов"""
        if not hasattr(self, 'comboBoxTag'):
            print("⚠️ comboBoxTag не найден в UI, пропускаем настройку тегов")
            return

        self.comboTags = self.comboBoxTag

        # Настройка комбобокса
        self.comboTags.setEditable(True)
        line_edit = self.comboTags.lineEdit()
        line_edit.setReadOnly(True)
        line_edit.setCursor(Qt.CursorShape.PointingHandCursor)

        # Создаем popup
        self.tags_popup = QWidget()
        self.tags_popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.tags_popup.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
            QLineEdit {
                border: 2px solid #e9ecef;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #D22730;
            }
            QCheckBox {
                font-size: 13px;
                color: #2c3e50;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #D9D9D6;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #D22730;
                border-color: #D22730;
            }
            QPushButton {
                background-color: #1B232A;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #09131B;
            }
            QScrollArea {
                border: none;
            }
        """)

        popup_layout = QVBoxLayout(self.tags_popup)
        popup_layout.setContentsMargins(10, 10, 10, 10)
        popup_layout.setSpacing(10)

        # Строка поиска
        self.tag_search_line = QLineEdit()
        self.tag_search_line.setPlaceholderText("Поиск по названию темы...")
        self.tag_search_line.textChanged.connect(self.on_tag_search_changed)
        popup_layout.addWidget(self.tag_search_line)

        # Кнопки Выбрать всех / Снять всех
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Выбрать всех")
        clear_all_btn = QPushButton("Снять выделение")
        select_all_btn.clicked.connect(self.select_all_tags)
        clear_all_btn.clicked.connect(self.clear_all_tags)
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(clear_all_btn)
        popup_layout.addLayout(btn_layout)

        # Контейнер для чекбоксов с прокруткой
        self.tags_container = QWidget()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setSpacing(8)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.tags_container)
        scroll_area.setMinimumHeight(200)
        scroll_area.setMaximumHeight(300)
        popup_layout.addWidget(scroll_area)

        self.tag_checkboxes = []
        self.tag_checkboxes_by_id = {}

        # Устанавливаем event filter для комбобокса
        self.comboTags.installEventFilter(self)
        line_edit.installEventFilter(self)

    def load_tags_into_popup(self):
        """Загружает теги в popup"""
        if not self.service:
            return

        # Очищаем существующие чекбоксы
        for cb in self.tag_checkboxes:
            self.tags_layout.removeWidget(cb)
            cb.deleteLater()
        self.tag_checkboxes.clear()
        self.tag_checkboxes_by_id.clear()

        # Получаем теги из сервиса
        dialog_data = self.service.prepare_dialog_data(self.mode, self.task_data)
        self.all_tags = dialog_data.get("tags", [])

        # Создаем чекбоксы
        for tag in self.all_tags:
            cb = QCheckBox(tag["name"])
            cb.setProperty("tag_id", tag["id"])
            cb.setProperty("tag_name", tag["name"])
            cb.setProperty("search_text", tag["name"].lower())
            cb.toggled.connect(lambda checked, tid=tag["id"]: self.on_tag_toggled(tid, checked))
            cb.setChecked(tag["id"] in self.selected_tag_ids)
            self.tag_checkboxes.append(cb)
            self.tag_checkboxes_by_id[tag["id"]] = cb
            self.tags_layout.addWidget(cb)

        self.tags_layout.addStretch()
        self.update_tags_button_text()

    def on_tag_search_changed(self, text):
        """Фильтрация чекбоксов по поиску"""
        search_text = self.tag_search_line.text().lower().strip()
        for cb in self.tag_checkboxes:
            tag_name = cb.property("tag_name").lower()
            is_visible = not search_text or search_text in tag_name
            cb.setVisible(is_visible)

    def on_tag_toggled(self, tag_id: int, checked: bool):
        """Обработчик изменения состояния чекбокса тега"""
        if checked:
            self.selected_tag_ids.add(tag_id)
        else:
            self.selected_tag_ids.discard(tag_id)
        self.update_tags_button_text()

    def select_all_tags(self):
        """Выбрать все видимые теги"""
        for cb in self.tag_checkboxes:
            if cb.isVisible():
                cb.setChecked(True)

    def clear_all_tags(self):
        """Снять выделение со всех тегов"""
        for cb in self.tag_checkboxes:
            cb.setChecked(False)

    def update_tags_button_text(self):
        """Обновляет текст в комбобоксе с выбранными тегами"""
        selected_names = []
        for tag_id in self.selected_tag_ids:
            cb = self.tag_checkboxes_by_id.get(tag_id)
            if cb:
                name = cb.property("tag_name")
                if name:
                    selected_names.append(name)

        if selected_names:
            text = f"✓ Выбрано ({len(selected_names)}): {', '.join(selected_names[:2])}"
            if len(selected_names) > 2:
                text += f" и ещё {len(selected_names) - 2}"
            self.comboTags.lineEdit().setText(text)
        else:
            self.comboTags.lineEdit().setText("▼ Выберите темы")

    def get_selected_tags(self) -> List[str]:
        """Возвращает список выбранных тегов"""
        selected_names = []
        for tag_id in self.selected_tag_ids:
            cb = self.tag_checkboxes_by_id.get(tag_id)
            if cb:
                selected_names.append(cb.property("tag_name"))
        return selected_names

    def set_selected_tags(self, tags: List[str]):
        """Устанавливает выбранные теги"""
        self.selected_tag_ids.clear()
        for cb in self.tag_checkboxes:
            tag_name = cb.property("tag_name")
            if tag_name in tags:
                cb.setChecked(True)
        self.update_tags_button_text()

    def eventFilter(self, obj, event):
        """Обработчик событий для показа popup при клике на комбобокс"""
        if event.type() == QEvent.Type.MouseButtonPress:
            if obj == self.comboTags or obj == self.comboTags.lineEdit():
                self.load_tags_into_popup()
                self.tag_search_line.clear()
                self.update_tag_checkboxes_visibility()
                pos = self.comboTags.mapToGlobal(QPoint(0, self.comboTags.height()))
                self.tags_popup.move(pos)
                self.tags_popup.setFixedWidth(self.comboTags.width())
                self.tags_popup.show()
                return True

            if obj == self.comboAssignees or obj == self.comboAssignees.lineEdit():
                self.load_assignees_into_popup()
                self.assignee_search_line.clear()
                self.update_assignee_checkboxes_visibility()
                pos = self.comboAssignees.mapToGlobal(QPoint(0, self.comboAssignees.height()))
                self.assignees_popup.move(pos)
                self.assignees_popup.setFixedWidth(self.comboAssignees.width())
                self.assignees_popup.show()
                return True

        elif event.type() == QEvent.Type.WindowDeactivate:
            if obj == self.tags_popup or (hasattr(self.tags_popup, 'isVisible') and not self.tags_popup.isVisible()):
                self.tags_popup_closed()
            if obj == self.assignees_popup or (hasattr(self.assignees_popup, 'isVisible') and not self.assignees_popup.isVisible()):
                self.assignees_popup_closed()

        return super().eventFilter(obj, event)

    def update_tag_checkboxes_visibility(self):
        """Обновляет видимость чекбоксов по поиску"""
        search_text = self.tag_search_line.text().lower().strip()
        for cb in self.tag_checkboxes:
            tag_name = cb.property("tag_name").lower()
            is_visible = not search_text or search_text in tag_name
            cb.setVisible(is_visible)

    def update_assignee_checkboxes_visibility(self):
        """Обновляет видимость чекбоксов исполнителей по поиску"""
        search_text = self.assignee_search_line.text().lower().strip()
        for cb in self.assignee_checkboxes:
            emp_name = cb.property("employee_name").lower()
            is_visible = not search_text or search_text in emp_name
            cb.setVisible(is_visible)

    def tags_popup_closed(self):
        """Вызывается, когда popup с тегами закрыт"""
        self.update_tags_button_text()
        if self.mode == "create":
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self.auto_fill_executor)

    def assignees_popup_closed(self):
        """Вызывается, когда popup с исполнителями закрыт"""
        self.update_assignees_button_text()

    def setup_stars(self):
        """Настройка звезд рейтинга"""
        self.stars = [self.star1, self.star2, self.star3, self.star4, self.star5]
        self.difficulty_value = 0

        for i, star in enumerate(self.stars):
            star.mousePressEvent = lambda e, idx=i: self.set_difficulty(idx + 1)
            star.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_difficulty(self, value: int):
        """Устанавливает сложность задачи по звездам"""
        self.difficulty_value = value
        for i, star in enumerate(self.stars):
            if i < value:
                star.setText("★")
                star.setStyleSheet("font-size: 28px; color: #FFD700;")
            else:
                star.setText("☆")
                star.setStyleSheet("font-size: 28px; color: #D3D3D3;")

        if hasattr(self, 'labelDifficultyValue'):
            difficulty_names = ["", "Очень низкая", "Низкая", "Средняя", "Высокая", "Максимальная"]
            self.labelDifficultyValue.setText(difficulty_names[value] if value <= 5 else "")

    def setup_ui(self):
        """Настройка UI"""
        if self.mode == "create":
            self.setWindowTitle("Создание задачи")
            if hasattr(self, 'createBtn'):
                self.createBtn.setText("Создать")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Создание новой задачи")

            if hasattr(self, 'createdAtLabel'):
                current_datetime = QDateTime.currentDateTime().toString("dd.MM.yyyy hh:mm")
                self.createdAtLabel.setText(f"Создано: {current_datetime}")
                self.createdAtLabel.show()

            if hasattr(self, 'updatedAtLabel'):
                self.updatedAtLabel.hide()

            if hasattr(self, 'createdByLabel'):
                creator_name = self.format_creator_name()
                self.createdByLabel.setText(f"Создатель: {creator_name}")
                self.createdByLabel.show()

        else:  # mode == "edit"
            self.setWindowTitle("Редактирование задачи")
            if hasattr(self, 'createBtn'):
                self.createBtn.setText("Сохранить")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Редактирование задачи")

            if hasattr(self, 'createdAtLabel'):
                self.createdAtLabel.show()
            if hasattr(self, 'updatedAtLabel'):
                self.updatedAtLabel.show()

    def format_creator_name(self) -> str:
        """Форматирует имя создателя"""
        last = self.current_user.get('last_name', '')
        first = self.current_user.get('first_name', '')
        middle = self.current_user.get('middle_name', '')

        if last and first:
            first_initial = first[0] + '.' if first else ''
            middle_initial = middle[0] + '.' if middle else ''
            return f"{last} {first_initial}{middle_initial}".strip()
        return "Неизвестен"

    def set_service(self, service: TasksService):
        """Устанавливает сервис и загружает данные"""
        self.service = service
        self.load_dialog_data()

    def load_dialog_data(self):
        """Загружает данные для диалога"""
        if not self.service:
            return

        dialog_data = self.service.prepare_dialog_data(self.mode, self.task_data)

        # Загружаем проекты
        if hasattr(self, 'comboBoxProject'):
            self.comboBoxProject.clear()
            self.comboBoxProject.addItem("Выберите проект", None)
            for project in dialog_data.get("projects", []):
                self.comboBoxProject.addItem(project["name"], project["id"])

            if self.task_data and self.task_data.get("project_id"):
                preset_project_id = self.task_data.get("project_id")
                for i in range(self.comboBoxProject.count()):
                    if self.comboBoxProject.itemData(i) == preset_project_id:
                        self.comboBoxProject.setCurrentIndex(i)
                        self.comboBoxProject.setEnabled(False)
                        break

        # Загружаем статусы
        if hasattr(self, 'comboBoxStatus'):
            self.comboBoxStatus.clear()
            for status in dialog_data.get("statuses", []):
                self.comboBoxStatus.addItem(status["name"], status["id"])

        # Загружаем теги в popup
        self.load_tags_into_popup()

        # Загружаем исполнителей в popup
        self.load_assignees_into_popup()

        # Если режим редактирования - заполняем данные
        if self.mode == "edit" and "task_data" in dialog_data:
            self.fill_task_data(dialog_data["task_data"])

    def fill_task_data(self, task_data: Dict):
        """Заполняет поля данными задачи"""
        if hasattr(self, 'lineEditTitle'):
            self.lineEditTitle.setText(task_data.get("title", ""))

        if hasattr(self, 'textEditDescription'):
            self.textEditDescription.setPlainText(task_data.get("description", ""))

        if hasattr(self, 'comboBoxPriority'):
            priority = task_data.get("priority_text", task_data.get("priority", "Средний"))
            if priority in ["low", "medium", "high", "critical"]:
                priority_map = {"low": "Низкий", "medium": "Средний", "high": "Высокий", "critical": "Критический"}
                priority = priority_map.get(priority, "Средний")
            index = self.comboBoxPriority.findText(priority)
            if index >= 0:
                self.comboBoxPriority.setCurrentIndex(index)

        if hasattr(self, 'comboBoxStatus'):
            status = task_data.get("status", "")
            for i in range(self.comboBoxStatus.count()):
                if self.comboBoxStatus.itemText(i) == status:
                    self.comboBoxStatus.setCurrentIndex(i)
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
            self.set_selected_tags(task_data["tags"])

        # Загружаем исполнителей (множественный выбор)
        assignee_ids = task_data.get("assignee_ids", [])
        if task_data.get("assigned_to") and task_data["assigned_to"] not in assignee_ids:
            assignee_ids.append(task_data["assigned_to"])
        if assignee_ids:
            self.set_selected_assignees(assignee_ids)

        # Устанавливаем сложность
        difficulty = task_data.get("difficulty", 0)
        if difficulty:
            try:
                difficulty_value = int(float(difficulty))
            except (ValueError, TypeError):
                difficulty_value = 0
            difficulty_value = max(1, min(5, difficulty_value))
            self.set_difficulty(difficulty_value)

        # Показываем создателя задачи
        if hasattr(self, 'createdByLabel'):
            creator_name = task_data.get("created_by_name", "")
            if not creator_name:
                created_by_id = task_data.get("created_by")
                if created_by_id and self.service:
                    creator_name = self.service.format_assignee_name(created_by_id)
            self.createdByLabel.setText(f"Создатель: {creator_name if creator_name else 'Неизвестен'}")
            self.createdByLabel.show()

        # Устанавливаем даты создания и обновления
        if self.mode == "edit":
            if hasattr(self, 'createdAtLabel'):
                created_at = task_data.get("created_at", "")
                if created_at:
                    self.createdAtLabel.setText(f"Создано: {created_at}")
                    self.createdAtLabel.show()

            if hasattr(self, 'updatedAtLabel'):
                updated_at = task_data.get("updated_at", "")
                if updated_at:
                    self.updatedAtLabel.setText(f"Обновлено: {updated_at}")
                    self.updatedAtLabel.show()

    def collect_form_data(self) -> Dict:
        """Собирает данные из формы"""
        data = {}

        if hasattr(self, 'lineEditTitle'):
            data["title"] = self.lineEditTitle.text().strip()

        if hasattr(self, 'textEditDescription'):
            data["description"] = self.textEditDescription.toPlainText().strip()

        if hasattr(self, 'comboBoxProject'):
            data["project_id"] = self.comboBoxProject.currentData()

        if hasattr(self, 'comboBoxPriority'):
            data["priority"] = self.comboBoxPriority.currentText()

        if hasattr(self, 'comboBoxStatus'):
            data["status"] = self.comboBoxStatus.currentText()

        if hasattr(self, 'dateEditDeadline'):
            data["due_date"] = self.dateEditDeadline.date().toString("yyyy-MM-dd")

        # Получаем выбранные теги
        data["tags"] = self.get_selected_tags()

        # Получаем выбранных исполнителей
        data["assignee_ids"] = self.get_selected_assignees()
        if data["assignee_ids"]:
            data["assigned_to"] = data["assignee_ids"][0]  # для обратной совместимости

        data["difficulty"] = self.difficulty_value

        return data

    def suggest_executor(self):
        """Предлагает исполнителя на основе выбранных тегов"""
        selected_tags = self.get_selected_tags()

        if not selected_tags or not self.service:
            return None

        try:
            suggestion = self.service.suggest_executor_for_tags(selected_tags)
            if suggestion:
                return suggestion
        except Exception as e:
            print(f"⚠️ Ошибка при предложении исполнителя: {e}")
        return None

    def auto_fill_executor(self):
        """Автоматически заполняет поле исполнителя на основе тегов"""
        suggestion = self.suggest_executor()

        if suggestion and hasattr(self, 'comboAssignees'):
            suggested_id = suggestion['employee_id']
            # Если исполнитель ещё не выбран - добавляем
            if suggested_id not in self.selected_assignee_ids:
                self.selected_assignee_ids.append(suggested_id)
                for cb in self.assignee_checkboxes:
                    emp_id = cb.property("employee_id")
                    if emp_id == suggested_id:
                        cb.setChecked(True)
                        break
                self.update_assignees_button_text()

                QMessageBox.information(
                    self,
                    "Рекомендация исполнителя",
                    f"{suggestion['explanation']}\n\n"
                    f"Исполнитель автоматически назначен. Вы можете изменить его при необходимости."
                )
                return True
        return False

    def validate_and_save(self):
        """Валидация и сохранение задачи"""
        if not self.service:
            QMessageBox.critical(self, "Ошибка", "Сервис не инициализирован")
            return

        form_data = self.collect_form_data()

        error = self.service.validate_form_data(form_data)
        if error:
            QMessageBox.warning(self, "Ошибка", error)
            return

        try:
            task_data = self.service.process_form_data(form_data, self.current_user)

            if self.mode == "edit" and self.task_data:
                task_id = self.task_data.get("id")
                self.task_saved.emit(task_id, task_data)
            else:
                self.task_saved.emit(None, task_data)

            self.accept()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {str(e)}")