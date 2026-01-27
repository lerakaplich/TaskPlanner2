from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import QTime, QDate, pyqtSignal, Qt
from PyQt6.uic import loadUi
from datetime import datetime, time, date


class CreateOvertimeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi("create_overtime.ui", self)

        # Устанавливаем флаг для сохранения геометрии
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.setup_ui()
        self.connect_signals()

        # Устанавливаем текущую дату и время
        self.dateEdit.setDate(QDate.currentDate())
        self.timeStart.setTime(QTime(18, 0))
        self.timeEnd.setTime(QTime(21, 0))

        # Загружаем тестовые данные
        self.load_test_data()

    def setup_ui(self):
        """Настройка интерфейса"""
        # Стили для кнопок
        self.buttonBox.button(self.buttonBox.StandardButton.Ok).setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #998664;
            }
            QPushButton:pressed {
                background-color: #7a6a50;
            }
        """)

        self.buttonBox.button(self.buttonBox.StandardButton.Cancel).setStyleSheet("""
            QPushButton {
                background-color: #D22730;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #862633;
            }
            QPushButton:pressed {
                background-color: #6a1e29;
            }
        """)

    def load_test_data(self):
        """Загрузка тестовых данных"""
        projects = [
            "Разработка новой кабины",
            "Внедрение ERP-системы",
            "Модернизация конвейера",
            "Разработка сайта"
        ]

        self.comboProject.addItems(projects)

    def connect_signals(self):
        """Подключение сигналов"""
        self.comboProject.currentIndexChanged.connect(self.on_project_changed)
        self.timeStart.timeChanged.connect(self.calculate_hours)
        self.timeEnd.timeChanged.connect(self.calculate_hours)
        self.buttonBox.accepted.connect(self.validate_and_accept)
        self.buttonBox.rejected.connect(self.reject)

    def on_project_changed(self):
        """Обработка изменения проекта"""
        project = self.comboProject.currentText()
        self.comboTask.setEnabled(bool(project))

        if project:
            # Загружаем задачи для выбранного проекта
            tasks = {
                "Разработка новой кабины": ["Дизайн интерфейса", "Разработка API", "Тестирование"],
                "Внедрение ERP-системы": ["Анализ требований", "Настройка серверов", "Миграция данных"],
                "Модернизация конвейера": ["Закупка оборудования", "Монтаж", "Пуско-наладочные работы"],
                "Разработка сайта": ["Верстка", "Бэкенд", "Деплой"]
            }.get(project, [])

            self.comboTask.clear()
            self.comboTask.addItems(tasks)

    def calculate_hours(self):
        """Расчет количества часов"""
        start = self.timeStart.time()
        end = self.timeEnd.time()

        if start.isValid() and end.isValid():
            hours = start.secsTo(end) / 3600.0
            if hours < 0:
                hours = 0
            self.labelHours.setText(f"Часов: {hours:.1f}")

    def validate_and_accept(self):
        """Валидация и принятие данных"""
        # Проверяем обязательные поля
        if not self.comboProject.currentText():
            QMessageBox.warning(self, "Ошибка", "Выберите проект!")
            return

        if not self.comboTask.currentText():
            QMessageBox.warning(self, "Ошибка", "Выберите задачу!")
            return

        # Проверяем время
        start = self.timeStart.time()
        end = self.timeEnd.time()

        if not start.isValid() or not end.isValid():
            QMessageBox.warning(self, "Ошибка", "Введите корректное время!")
            return

        if start >= end:
            QMessageBox.warning(self, "Ошибка", "Время окончания должно быть позже времени начала!")
            return

        hours = start.secsTo(end) / 3600.0
        if hours <= 0:
            QMessageBox.warning(self, "Ошибка", "Длительность должна быть положительной!")
            return

        # Проверяем максимальную длительность (например, 12 часов)
        if hours > 12:
            QMessageBox.warning(self, "Ошибка", "Слишком большая длительность! Максимум 12 часов.")
            return

        self.accept()

    def get_overtime_data(self):
        """Получение данных о переработке"""
        start_time = self.timeStart.time().toPyTime()
        end_time = self.timeEnd.time().toPyTime()
        hours = start_time.hour + start_time.minute / 60.0
        hours_end = end_time.hour + end_time.minute / 60.0
        duration = hours_end - hours

        return {
            "date": self.dateEdit.date().toPyDate(),
            "project": self.comboProject.currentText(),
            "task": self.comboTask.currentText(),
            "start": start_time,
            "end": end_time,
            "hours": duration,
            "note": self.textNote.toPlainText()
        }