# windows/other_tasks/task_dialog.py

import os
from typing import Dict, Optional
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import QDate, pyqtSignal

from services.other_tasks_service import OtherTasksService


class TaskDialog(QDialog):
    task_saved = pyqtSignal(dict)

    def __init__(
            self,
            parent=None,
            task_data: Optional[Dict] = None,
            mode="create"
    ):
        super().__init__(parent)

        self.service: Optional[OtherTasksService] = None
        self.task_data = task_data
        self.mode = mode
        self.current_user = {"id": 1, "name": "Текущий пользователь"}

        # Загружаем UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "other_tasks")
        uic.loadUi(os.path.join(ui_path, "task_dialog.ui"), self)

        # Настройка UI
        self.setup_ui()

        if hasattr(self, 'createBtn'):
            self.createBtn.clicked.connect(self.validate_and_save)

    def setup_ui(self):
        """Настраивает UI диалога."""
        if self.mode == "create":
            self.setWindowTitle("Создание задачи")
            if hasattr(self, 'createBtn'):
                self.createBtn.setText("Создать")
        else:
            self.setWindowTitle("Редактирование задачи")
            if hasattr(self, 'createBtn'):
                self.createBtn.setText("Сохранить")

    def set_service(self, service: OtherTasksService):
        """Устанавливает сервис и загружает данные."""
        self.service = service
        self.load_dialog_data()

    def load_dialog_data(self):
        """Загружает данные для диалога через сервис."""
        if not self.service:
            return

        dialog_data = self.service.prepare_dialog_data(self.mode, self.task_data)

        # Загружаем проекты
        if hasattr(self, 'comboBoxProject'):
            self.comboBoxProject.clear()
            self.comboBoxProject.addItem("Выберите проект", None)
            for project in dialog_data["projects"]:
                self.comboBoxProject.addItem(project["name"], project["id"])

        # Загружаем статусы
        if hasattr(self, 'comboBoxStatus'):
            self.comboBoxStatus.clear()
            for status in dialog_data["statuses"]:
                self.comboBoxStatus.addItem(status["name"], status["id"])

        # Загружаем исполнителей
        if hasattr(self, 'comboBoxAssignee'):
            self.comboBoxAssignee.clear()
            self.comboBoxAssignee.addItem("Не назначен", None)
            for emp in dialog_data["employees"]:
                self.comboBoxAssignee.addItem(emp["display_name"], emp["id"])

        # Загружаем приоритеты
        if hasattr(self, 'comboBoxPriority'):
            self.comboBoxPriority.clear()
            for priority in dialog_data["priorities"]:
                self.comboBoxPriority.addItem(priority["text"])

        # Если режим редактирования - заполняем данные
        if self.mode == "edit" and "task_data" in dialog_data:
            self.fill_task_data(dialog_data["task_data"])

    def fill_task_data(self, task_data: Dict):
        """Заполняет поля формы данными задачи."""
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
            # Ищем статус по тексту
            for i in range(self.comboBoxStatus.count()):
                if self.comboBoxStatus.itemText(i) == status:
                    self.comboBoxStatus.setCurrentIndex(i)
                    break

        if hasattr(self, 'comboBoxAssignee'):
            assigned_to = task_data.get("assigned_to")
            if assigned_to:
                # Ищем по данным (ID)
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

    def collect_form_data(self) -> Dict:
        """Собирает данные из полей формы."""
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

        return data

    # windows/other_tasks/task_dialog.py

    def validate_and_save(self):
        """Валидирует и сохраняет задачу."""
        print("\n=== ОТЛАДКА: Диалог сохранения задачи ===")

        if not self.service:
            print("❌ Сервис не инициализирован")
            QMessageBox.critical(self, "Ошибка", "Сервис не инициализирован")
            return

        form_data = self.collect_form_data()
        print(f"Собранные данные из формы: {form_data}")

        # Валидация через сервис
        error = self.service.validate_form_data(form_data)
        if error:
            print(f"❌ Ошибка валидации: {error}")
            QMessageBox.warning(self, "Ошибка", error)
            return

        print("✅ Валидация пройдена")

        try:
            # Подготовка данных через сервис
            task_data = self.service.process_form_data(form_data, self.current_user)
            print(f"Подготовленные данные: {task_data}")

            # Сигнал с данными
            print("📤 Отправка сигнала task_saved")
            self.task_saved.emit(task_data)
            print("✅ Сигнал отправлен")

            self.accept()
            print("✅ Диалог закрыт")

        except Exception as e:
            print(f"❌ ИСКЛЮЧЕНИЕ: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {str(e)}")