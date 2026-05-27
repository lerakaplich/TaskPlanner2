# windows/other_tasks/task_dialog.py

import os
from typing import Dict, Optional, List
from PyQt6 import uic, QtWidgets
from PyQt6.QtWidgets import QDialog, QMessageBox, QVBoxLayout, QWidget, QScrollArea, QLineEdit, QPushButton, QHBoxLayout
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

        # Загружаем UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "other_tasks", "task_dialog.ui")
        uic.loadUi(ui_path, self)

        # Настройка popup для выбора тегов
        self.setup_tags_popup()

        # Настройка звезд рейтинга
        self.setup_stars()

        # Настройка UI
        self.setup_ui()

        if hasattr(self, 'createBtn'):
            self.createBtn.clicked.connect(self.validate_and_save)

    def setup_tags_popup(self):
        """Настройка popup с чекбоксами для выбора тегов"""
        # Используем comboBoxTag (правильное имя из UI файла)
        if not hasattr(self, 'comboBoxTag'):
            print("⚠️ comboBoxTag не найден в UI, пропускаем настройку тегов")
            return

        self.comboTags = self.comboBoxTag  # Создаем алиас для совместимости

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
            cb = QtWidgets.QCheckBox(tag["name"])
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
                # Обновляем список тегов перед показом
                self.load_tags_into_popup()
                self.tag_search_line.clear()
                self.update_tag_checkboxes_visibility()
                pos = self.comboTags.mapToGlobal(QPoint(0, self.comboTags.height()))
                self.tags_popup.move(pos)
                self.tags_popup.setFixedWidth(self.comboTags.width())
                self.tags_popup.show()
                return True
        return super().eventFilter(obj, event)

    def update_tag_checkboxes_visibility(self):
        """Обновляет видимость чекбоксов по поиску"""
        search_text = self.tag_search_line.text().lower().strip()
        for cb in self.tag_checkboxes:
            tag_name = cb.property("tag_name").lower()
            is_visible = not search_text or search_text in tag_name
            cb.setVisible(is_visible)

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

    # windows/other_tasks/task_dialog.py - исправленный метод setup_ui

    def setup_ui(self):
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

            # === ИСПРАВЛЕНИЕ: показываем создателя (текущего пользователя) ===
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

            # Для редактирования показываем создателя из данных задачи
            if hasattr(self, 'createdByLabel'):
                # Будет установлено позже в fill_task_data
                pass

    def format_creator_name(self) -> str:
        last = self.current_user.get('last_name', '')
        first = self.current_user.get('first_name', '')
        middle = self.current_user.get('middle_name', '')

        print(f"🔍 format_creator_name: last={last}, first={first}, middle={middle}")  # Добавьте для отладки

        if last and first:
            first_initial = first[0] + '.' if first else ''
            middle_initial = middle[0] + '.' if middle else ''
            return f"{last} {first_initial}{middle_initial}".strip()
        return "Неизвестен"

    def set_service(self, service: TasksService):
        self.service = service
        self.load_dialog_data()

    def load_dialog_data(self):
        if not self.service:
            return

        dialog_data = self.service.prepare_dialog_data(self.mode, self.task_data)
        print(
            f"📊 Загружено данных: проектов={len(dialog_data.get('projects', []))}, тегов={len(dialog_data.get('tags', []))}")

        # Загружаем проекты
        if hasattr(self, 'comboBoxProject'):
            self.comboBoxProject.clear()
            self.comboBoxProject.addItem("Выберите проект", None)
            for project in dialog_data.get("projects", []):
                self.comboBoxProject.addItem(project["name"], project["id"])

            # Если есть предустановленный проект (из диаграммы Ганта)
            if self.task_data and self.task_data.get("project_id"):
                preset_project_id = self.task_data.get("project_id")
                for i in range(self.comboBoxProject.count()):
                    if self.comboBoxProject.itemData(i) == preset_project_id:
                        self.comboBoxProject.setCurrentIndex(i)
                        # Блокируем изменение проекта
                        self.comboBoxProject.setEnabled(False)
                        break

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

        # Загружаем теги в popup
        self.load_tags_into_popup()

        # Если режим редактирования - заполняем данные
        if self.mode == "edit" and "task_data" in dialog_data:
            self.fill_task_data(dialog_data["task_data"])

    def fill_task_data(self, task_data: Dict):
        if hasattr(self, 'lineEditTitle'):
            self.lineEditTitle.setText(task_data.get("title", ""))

        if hasattr(self, 'textEditDescription'):
            self.textEditDescription.setPlainText(task_data.get("description", ""))

        if hasattr(self, 'comboBoxPriority'):
            priority = task_data.get("priority_text", task_data.get("priority", "Средний"))
            # Приоритет может быть в виде "Низкий", "Средний" и т.д. или в виде "low", "medium"
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
            self.set_selected_tags(task_data["tags"])

        # === ИСПРАВЛЕНИЕ: устанавливаем сложность ===
        difficulty = task_data.get("difficulty", 0)
        if difficulty:
            # Преобразуем в int, если это float или str
            try:
                difficulty_value = int(float(difficulty))
            except (ValueError, TypeError):
                difficulty_value = 0

            # Ограничиваем от 1 до 5
            difficulty_value = max(1, min(5, difficulty_value))
            self.set_difficulty(difficulty_value)

        # === ИСПРАВЛЕНИЕ: показываем создателя задачи (не текущего пользователя) ===
        if hasattr(self, 'createdByLabel'):
            creator_name = task_data.get("created_by_name", "")
            if not creator_name:
                # Если нет имени, пробуем получить через сервис
                created_by_id = task_data.get("created_by")
                if created_by_id and self.service:
                    creator_name = self.service.format_assignee_name(created_by_id)
            self.createdByLabel.setText(f"Создатель: {creator_name if creator_name else 'Неизвестен'}")
            self.createdByLabel.show()

        # Устанавливаем даты создания и обновления для режима редактирования
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

        # Получаем выбранные теги
        data["tags"] = self.get_selected_tags()
        print(f"🏷️ Выбранные теги из диалога: {data['tags']}")

        data["difficulty"] = self.difficulty_value

        # НЕ ДОБАВЛЯЕМ created_by здесь - он будет добавлен в process_form_data
        return data

    def validate_and_save(self):
        print("\n=== ОТЛАДКА: Диалог сохранения задачи ===")

        if not self.service:
            print("❌ Сервис не инициализирован")
            QMessageBox.critical(self, "Ошибка", "Сервис не инициализирован")
            return

        form_data = self.collect_form_data()
        print(f"Собранные данные: {form_data}")

        error = self.service.validate_form_data(form_data)
        if error:
            print(f"❌ Ошибка: {error}")
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

        except Exception as e:
            print(f"❌ ИСКЛЮЧЕНИЕ: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {str(e)}")