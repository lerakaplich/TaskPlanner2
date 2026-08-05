# windows/other_tasks/task_dialog.py

import os
from typing import Dict, Optional, List
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox, QVBoxLayout, QWidget, QScrollArea, QLineEdit, QPushButton, \
    QHBoxLayout, QCheckBox, QLabel
from PyQt6.QtCore import QDate, QDateTime, pyqtSignal, Qt, QEvent, QPoint, QTimer

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
        self.current_user = current_user
        self.selected_tag_ids = set()
        self.all_tags = []
        self.selected_assignee_id = None  # один ID

        self._suggestion_shown_for_tags = set()

        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "other_tasks", "task_dialog.ui")
        uic.loadUi(ui_path, self)

        # Настройка popup для выбора тегов
        self.setup_tags_popup()

        # Настройка простого комбобокса исполнителей
        self.setup_assignees_combo()

        # Настройка звезд
        self.setup_stars()
        self.setup_ui()

        if hasattr(self, 'createBtn'):
            self.createBtn.clicked.connect(self.validate_and_save)

    # ==========================================================
    # ИСПОЛНИТЕЛИ (ПРОСТАЯ ВЕРСИЯ)
    # ==========================================================

    def setup_assignees_combo(self):
        """Настройка простого комбобокса для выбора исполнителя"""
        if not hasattr(self, 'comboBoxAssignee'):
            print("⚠️ comboBoxAssignee не найден в UI")
            return

        self.comboBoxAssignee.clear()
        self.comboBoxAssignee.addItem("Не назначен", None)

    def load_assignees_into_combo(self):
        """Загружает исполнителей в комбобокс"""
        if not self.service or not hasattr(self, 'comboBoxAssignee'):
            return

        self.comboBoxAssignee.blockSignals(True)
        self.comboBoxAssignee.clear()
        self.comboBoxAssignee.addItem("Не назначен", None)

        dialog_data = self.service.prepare_dialog_data(self.mode, self.task_data)
        employees = dialog_data.get("employees", [])

        for emp in employees:
            self.comboBoxAssignee.addItem(emp["display_name"], emp["id"])

        if self.selected_assignee_id:
            for i in range(self.comboBoxAssignee.count()):
                if self.comboBoxAssignee.itemData(i) == self.selected_assignee_id:
                    self.comboBoxAssignee.setCurrentIndex(i)
                    break

        self.comboBoxAssignee.blockSignals(False)

    def get_selected_assignee(self) -> Optional[int]:
        """Возвращает ID выбранного исполнителя"""
        if hasattr(self, 'comboBoxAssignee'):
            return self.comboBoxAssignee.currentData()
        return None

    def set_selected_assignee(self, assignee_id: Optional[int]):
        """Устанавливает выбранного исполнителя"""
        self.selected_assignee_id = assignee_id
        if hasattr(self, 'comboBoxAssignee'):
            for i in range(self.comboBoxAssignee.count()):
                if self.comboBoxAssignee.itemData(i) == assignee_id:
                    self.comboBoxAssignee.setCurrentIndex(i)
                    return

    # ==========================================================
    # ТЕГИ
    # ==========================================================

    def setup_tags_popup(self):
        """Настройка popup с чекбоксами для выбора тегов"""
        if not hasattr(self, 'comboBoxTag'):
            print("⚠️ comboBoxTag не найден в UI, пропускаем настройку тегов")
            return

        self.comboTags = self.comboBoxTag
        self.comboTags.setEditable(True)
        line_edit = self.comboTags.lineEdit()
        line_edit.setReadOnly(True)
        line_edit.setCursor(Qt.CursorShape.PointingHandCursor)

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

        self.tag_search_line = QLineEdit()
        self.tag_search_line.setPlaceholderText("Поиск по названию темы...")
        self.tag_search_line.textChanged.connect(self.on_tag_search_changed)
        popup_layout.addWidget(self.tag_search_line)

        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Выбрать всех")
        clear_all_btn = QPushButton("Снять выделение")
        select_all_btn.clicked.connect(self.select_all_tags)
        clear_all_btn.clicked.connect(self.clear_all_tags)
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(clear_all_btn)
        popup_layout.addLayout(btn_layout)

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

        self.comboTags.installEventFilter(self)
        line_edit.installEventFilter(self)

    def load_tags_into_popup(self):
        """Загружает теги в popup"""
        if not self.service:
            return

        for cb in self.tag_checkboxes:
            self.tags_layout.removeWidget(cb)
            cb.deleteLater()
        self.tag_checkboxes.clear()
        self.tag_checkboxes_by_id.clear()

        dialog_data = self.service.prepare_dialog_data(self.mode, self.task_data)
        self.all_tags = dialog_data.get("tags", [])

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

    def on_tag_toggled(self, tag_id: int, checked: bool):
        if checked:
            self.selected_tag_ids.add(tag_id)
        else:
            self.selected_tag_ids.discard(tag_id)
        self.update_tags_button_text()

        # ✅ Всегда пересчитываем при изменении тегов
        self._suggest_executor_after_tag_change()

    # windows/other_tasks/task_dialog.py

    def _suggest_executor_after_tag_change(self):
        """
        Предлагает исполнителя на основе выбранных тегов.
        Пересчитывает при каждом изменении тегов.
        """
        if not self.selected_tag_ids:
            # Если теги сняты, очищаем исполнителя
            self.set_selected_assignee(None)
            # Скрываем уведомление
            if hasattr(self, '_notification') and self._notification:
                try:
                    self._notification.hide()
                    self._notification.deleteLater()
                except:
                    pass
                self._notification = None
            return

        selected_tag_names = []
        for tag_id in self.selected_tag_ids:
            cb = self.tag_checkboxes_by_id.get(tag_id)
            if cb and cb.isChecked():
                tag_name = cb.property("tag_name")
                if tag_name:
                    selected_tag_names.append(tag_name)

        if not selected_tag_names or not self.service:
            return

        # ✅ Сохраняем старый исполнитель для сравнения
        old_assignee_id = self.selected_assignee_id

        try:
            # Получаем предложение от сервиса на основе ВСЕХ текущих тегов
            suggestion = self.service.suggest_executor_for_tags(selected_tag_names)

            if suggestion:
                suggested_id = suggestion.get('employee_id')
                suggested_name = suggestion.get('employee_name', 'Неизвестен')
                avg_difficulty = suggestion.get('avg_difficulty', 0)
                tasks_count = suggestion.get('tasks_count', 0)

                # Обновляем исполнителя (если изменился)
                if suggested_id and suggested_id != old_assignee_id:
                    self.set_selected_assignee(suggested_id)
                    print(
                        f"🔄 Исполнитель обновлён: {suggested_name} (сложность: {avg_difficulty:.1f}⭐, задач: {tasks_count})")

                # ✅ ВСЕГДА показываем уведомление при изменении тегов
                # (даже если исполнитель тот же, пользователь видит актуальную информацию)
                self._show_suggestion_notification(suggestion, force=bool(selected_tag_names))

        except Exception as e:
            print(f"⚠️ Ошибка при предложении исполнителя: {e}")

    # windows/other_tasks/task_dialog.py

    def _show_suggestion_notification(self, suggestion: Dict, force: bool = True):
        """Показывает уведомление о предложенном исполнителе"""
        # Всегда показываем при force=True, даже если исполнитель тот же
        # При force=False показываем только если исполнитель изменился

        # Если уведомление уже есть - удаляем его
        if hasattr(self, '_notification') and self._notification:
            try:
                self._notification.deleteLater()
                self._notification = None
            except:
                pass

        # Если force=False и исполнитель не изменился - не показываем
        # (но force всегда True при изменении тегов)
        if not force:
            return

        notification = QWidget(self)
        notification.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        notification.setStyleSheet("""
            QWidget {
                background-color: #1B232A;
                border-radius: 8px;
                padding: 8px 16px;
                border: 1px solid #333;
            }
            QLabel {
                color: white;
                font-size: 12px;
                border: none;
            }
            QLabel#title {
                font-weight: bold;
                color: #ccab6e;
                font-size: 13px;
            }
            QLabel#subtitle {
                color: #999;
                font-size: 11px;
            }
        """)

        layout = QVBoxLayout(notification)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 6, 8, 6)

        employee_name = suggestion.get('employee_name', 'Неизвестен')
        avg_difficulty = suggestion.get('avg_difficulty', 0)
        tasks_count = suggestion.get('tasks_count', 0)

        # Проверяем, изменился ли исполнитель
        is_new = (self.selected_assignee_id == suggestion.get('employee_id'))

        title_text = f"Рекомендуемый исполнитель на основе компетенций: {employee_name}"
        if is_new:
            title_text = f"✅ {title_text}"
        else:
            title_text = f"🔄 {title_text}"

        title_label = QLabel(title_text)
        title_label.setObjectName("title")
        layout.addWidget(title_label)

        if hasattr(self, 'comboBoxAssignee'):
            pos = self.comboBoxAssignee.mapToGlobal(self.comboBoxAssignee.rect().topLeft())
            notification.move(pos.x(), pos.y() - 70)
        else:
            notification.move(self.width() // 2 - 200, 20)

        notification.show()
        self._notification = notification

        def safe_delete():
            try:
                if hasattr(self, '_notification') and self._notification:
                    self._notification.deleteLater()
                    self._notification = None
            except RuntimeError:
                pass

        QTimer.singleShot(2500, safe_delete)

    def on_tag_search_changed(self, text):
        search_text = self.tag_search_line.text().lower().strip()
        for cb in self.tag_checkboxes:
            tag_name = cb.property("tag_name").lower()
            cb.setVisible(not search_text or search_text in tag_name)

    def select_all_tags(self):
        for cb in self.tag_checkboxes:
            if cb.isVisible():
                cb.setChecked(True)

    def clear_all_tags(self):
        for cb in self.tag_checkboxes:
            cb.setChecked(False)

    def update_tags_button_text(self):
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
        selected_names = []
        for tag_id in self.selected_tag_ids:
            cb = self.tag_checkboxes_by_id.get(tag_id)
            if cb:
                selected_names.append(cb.property("tag_name"))
        return selected_names

    def set_selected_tags(self, tags: List[str]):
        self.selected_tag_ids.clear()
        for cb in self.tag_checkboxes:
            tag_name = cb.property("tag_name")
            if tag_name in tags:
                cb.setChecked(True)
        self.update_tags_button_text()

    def tags_popup_closed(self):
        self.update_tags_button_text()

    def update_tag_checkboxes_visibility(self):
        search_text = self.tag_search_line.text().lower().strip()
        for cb in self.tag_checkboxes:
            tag_name = cb.property("tag_name").lower()
            cb.setVisible(not search_text or search_text in tag_name)

    # ==========================================================
    # ЗВЁЗДЫ
    # ==========================================================

    def setup_stars(self):
        self.stars = [self.star1, self.star2, self.star3, self.star4, self.star5]
        self.difficulty_value = 0

        for i, star in enumerate(self.stars):
            star.mousePressEvent = lambda e, idx=i: self.set_difficulty(idx + 1)
            star.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_difficulty(self, value: int):
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

    # ==========================================================
    # UI
    # ==========================================================

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

            if hasattr(self, 'createdByLabel'):
                creator_name = self.format_creator_name()
                self.createdByLabel.setText(f"Создатель: {creator_name}")
                self.createdByLabel.show()

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

    def format_creator_name(self) -> str:
        last = self.current_user.get('last_name', '')
        first = self.current_user.get('first_name', '')
        middle = self.current_user.get('middle_name', '')

        if last and first:
            first_initial = first[0] + '.' if first else ''
            middle_initial = middle[0] + '.' if middle else ''
            return f"{last} {first_initial}{middle_initial}".strip()
        return "Неизвестен"

    # ==========================================================
    # ЗАГРУЗКА ДАННЫХ
    # ==========================================================

    def set_service(self, service: TasksService):
        self.service = service
        self.load_dialog_data()

    def load_dialog_data(self):
        if not self.service:
            return

        dialog_data = self.service.prepare_dialog_data(self.mode, self.task_data)

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

        if hasattr(self, 'comboBoxStatus'):
            self.comboBoxStatus.clear()
            for status in dialog_data.get("statuses", []):
                self.comboBoxStatus.addItem(status["name"], status["id"])

        self.load_tags_into_popup()
        self.load_assignees_into_combo()

        if self.mode == "edit" and "task_data" in dialog_data:
            self.fill_task_data(dialog_data["task_data"])

    def fill_task_data(self, task_data: Dict):
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

        if task_data.get("tags"):
            self.set_selected_tags(task_data["tags"])

        # Загружаем одного исполнителя
        assignee_id = task_data.get("assigned_to")
        if assignee_id:
            self.set_selected_assignee(assignee_id)

        difficulty = task_data.get("difficulty", 0)
        if difficulty:
            try:
                difficulty_value = int(float(difficulty))
            except (ValueError, TypeError):
                difficulty_value = 0
            difficulty_value = max(1, min(5, difficulty_value))
            self.set_difficulty(difficulty_value)

        if hasattr(self, 'createdByLabel'):
            creator_name = task_data.get("created_by_name", "")
            if not creator_name:
                created_by_id = task_data.get("created_by")
                if created_by_id and self.service:
                    creator_name = self.service.format_assignee_name(created_by_id)
            self.createdByLabel.setText(f"Создатель: {creator_name if creator_name else 'Неизвестен'}")
            self.createdByLabel.show()

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

    # ==========================================================
    # СОХРАНЕНИЕ
    # ==========================================================

    def collect_form_data(self) -> Dict:
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

        data["tags"] = self.get_selected_tags()
        data["assigned_to"] = self.get_selected_assignee()
        data["difficulty"] = self.difficulty_value

        return data

    def validate_and_save(self):
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

    # ==========================================================
    # EVENT FILTER
    # ==========================================================

    def eventFilter(self, obj, event):
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

        elif event.type() == QEvent.Type.WindowDeactivate:
            if obj == self.tags_popup or not self.tags_popup.isVisible():
                self.tags_popup_closed()

        return super().eventFilter(obj, event)