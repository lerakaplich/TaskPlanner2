import os

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import QDate, Qt
from PyQt6.uic import loadUi


class TaskDialog(QDialog):
    """Универсальный диалог для создания и редактирования задачи"""

    def __init__(self, parent=None, task_data=None, mode='create'):
        """
        Инициализация диалога

        Args:
            parent: Родительский виджет
            task_data: Данные задачи для редактирования (None для создания)
            mode: 'create' для создания, 'edit' для редактирования
        """
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/analytics/employees/
            "..", "..",   # поднимаемся до корня проекта
            "ui", "other_tasks"  # спускаемся в нужную подпапку ui
        )
        uic.loadUi(os.path.join(ui_path, "task_dialog.ui"), self)

        self.mode = mode
        self.task_data = task_data or {}

        # Устанавливаем флаг для сохранения геометрии
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        # Настраиваем интерфейс в зависимости от режима
        self.setup_dialog()

        # Подключаем сигналы
        self.buttonBox.accepted.connect(self.validate_and_accept)
        self.buttonBox.rejected.connect(self.reject)

        # Настраиваем кнопки
        self.setup_buttons()

    def setup_dialog(self):
        """Настройка диалога в зависимости от режима"""
        if self.mode == 'create':
            self.setWindowTitle("Создание новой задачи")
            self.titleLabel.setText("📝 Создание задачи")

            # Устанавливаем дату дедлайна на 7 дней вперед
            self.dateEditDeadline.setDate(QDate.currentDate().addDays(7))

        elif self.mode == 'edit':
            self.setWindowTitle("Редактирование задачи")
            self.titleLabel.setText("✏️ Редактирование задачи")

            # Заполняем поля данными задачи
            self.load_task_data()

    def setup_buttons(self):
        """Настройка стилей кнопок"""
        # Кнопка OK
        ok_button = self.buttonBox.button(self.buttonBox.StandardButton.Ok)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 10px 20px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #998664;
            }
            QPushButton:pressed {
                background-color: #7a6a50;
            }
        """)

        if self.mode == 'create':
            ok_button.setText("Создать")
        else:
            ok_button.setText("Сохранить")

        # Кнопка Cancel
        cancel_button = self.buttonBox.button(self.buttonBox.StandardButton.Cancel)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #1B232A;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 10px 20px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #D9D9D6;
                color: black;
            }
            QPushButton:pressed {
                background-color: #B8B8B5;
            }
        """)

    def load_task_data(self):
        """Загрузка данных задачи для редактирования"""
        if not self.task_data:
            return

        # Название задачи
        self.lineEditTitle.setText(self.task_data.get('title', ''))

        # Описание
        self.textEditDescription.setPlainText(self.task_data.get('description', ''))

        # Исполнитель
        self.lineEditAssignee.setText(self.task_data.get('assignee', ''))

        # Проект
        self.lineEditProject.setText(self.task_data.get('project', ''))

        # Приоритет
        priority = self.task_data.get('priority', 'medium')
        priority_map = {
            'low': 'Низкий',
            'medium': 'Средний',
            'high': 'Высокий',
            'critical': 'Критический'
        }
        priority_text = priority_map.get(priority, 'Средний')

        # Ищем индекс приоритета в комбобоксе
        for i in range(self.comboBoxPriority.count()):
            if self.comboBoxPriority.itemText(i) == priority_text:
                self.comboBoxPriority.setCurrentIndex(i)
                break

        # Дедлайн
        deadline = self.task_data.get('deadline', '')
        if deadline:
            try:
                deadline_date = QDate.fromString(deadline, 'dd.MM.yyyy')
                if deadline_date.isValid():
                    self.dateEditDeadline.setDate(deadline_date)
            except:
                # Если не удалось распарсить, устанавливаем текущую дату + 7 дней
                self.dateEditDeadline.setDate(QDate.currentDate().addDays(7))

        # Статус
        status = self.task_data.get('status', 'todo')
        status_map = {
            'todo': 'К выполнению',
            'progress': 'В работе',
            'review': 'На проверке',
            'done': 'Выполнено'
        }
        status_text = status_map.get(status, 'К выполнению')

        # Ищем индекс статуса в комбобоксе
        for i in range(self.comboBoxStatus.count()):
            if self.comboBoxStatus.itemText(i) == status_text:
                self.comboBoxStatus.setCurrentIndex(i)
                break

    def validate_and_accept(self):
        """Валидация данных и принятие диалога"""
        # Проверяем обязательные поля
        if not self.lineEditTitle.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите название задачи!")
            self.lineEditTitle.setFocus()
            return

        if not self.lineEditAssignee.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите исполнителя задачи!")
            self.lineEditAssignee.setFocus()
            return

        if not self.lineEditProject.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите название проекта!")
            self.lineEditProject.setFocus()
            return

        # Проверяем дату дедлайна
        deadline_date = self.dateEditDeadline.date()
        if not deadline_date.isValid():
            QMessageBox.warning(self, "Ошибка", "Введите корректную дату дедлайна!")
            self.dateEditDeadline.setFocus()
            return

        # Проверяем, что дедлайн не в прошлом (кроме случаев, когда задача уже выполнена)
        current_date = QDate.currentDate()
        if deadline_date < current_date:
            reply = QMessageBox.question(
                self, "Подтверждение",
                "Дата дедлайна уже прошла. Вы уверены, что хотите установить прошедшую дату?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self.dateEditDeadline.setFocus()
                return

        # Все проверки пройдены
        self.accept()

    def get_task_data(self):
        """Получение данных задачи из диалога"""
        # Маппинг приоритетов
        priority_map = {
            'Низкий': 'low',
            'Средний': 'medium',
            'Высокий': 'high',
            'Критический': 'critical'
        }

        # Маппинг статусов
        status_map = {
            'К выполнению': 'todo',
            'В работе': 'progress',
            'На проверке': 'review',
            'Выполнено': 'done'
        }

        # Формируем данные задачи
        task_data = {
            'title': self.lineEditTitle.text().strip(),
            'description': self.textEditDescription.toPlainText().strip(),
            'assignee': self.lineEditAssignee.text().strip(),
            'project': self.lineEditProject.text().strip(),
            'priority': priority_map.get(self.comboBoxPriority.currentText(), 'medium'),
            'deadline': self.dateEditDeadline.date().toString('dd.MM.yyyy'),
            'status': status_map.get(self.comboBoxStatus.currentText(), 'todo'),
            'tags': self.task_data.get('tags', [])  # Сохраняем существующие теги
        }

        # Сохраняем ID если редактируем
        if 'id' in self.task_data:
            task_data['id'] = self.task_data['id']

        # Сохраняем создателя если редактируем
        if 'creator' in self.task_data:
            task_data['creator'] = self.task_data['creator']

        return task_data