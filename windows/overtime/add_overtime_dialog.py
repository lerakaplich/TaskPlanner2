import os
import sys
from datetime import datetime

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import QDate, QTime
from PyQt6.uic import loadUi


class AddOvertimeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/analytics/employees/
            "..", "..",  # поднимаемся до корня проекта
            "ui", "overtime"  # спускаемся в нужную подпапку ui
        )
        uic.loadUi(os.path.join(ui_path, "add_overtime_dialog.ui"), self)


        # Фиксируем высоту 32 px
        self.comboProject.setFixedHeight(32)
        self.comboTask.setFixedHeight(32)
        self.dateEdit.setFixedHeight(32)
        self.timeStart.setFixedHeight(32)
        self.timeEnd.setFixedHeight(32)
        self.btnSave.setFixedHeight(32)

        # Заголовок
        self.titleLabel.setStyleSheet("font-size: 22px; font-weight: bold; color: #000000; background-color: #FFFFFF;")

        # Заполняем проекты
        self.projects = {
            "CRM-система для отдела продаж": [
                "Разработка модуля лидов",
                "Интеграция с 1С",
                "Дизайн дашборда",
                "Тестирование API"
            ],
            "Мобильное приложение доставки еды": [
                "Карта и геолокация",
                "Корзина и оплата",
                "Профиль курьера",
                "Push-уведомления"
            ],
            "Внутренний портал сотрудников": [
                "Модуль отпусков и больничных",
                "Таблица переработок",
                "Личный кабинет",
                "Отчёты по зарплате"
            ],
            "Админка интернет-магазина": [
                "Управление товарами",
                "Обработка заказов",
                "Аналитика продаж",
                "Импорт каталога"
            ]
        }

        self.comboProject.addItem("Выберите проект", None)
        for project in self.projects:
            self.comboProject.addItem(project, project)
        self.comboProject.addItem("Без проекта", "Без проекта")

        # По умолчанию — текущая дата и время (округлённое)
        self.dateEdit.setDate(QDate.currentDate())
        self.timeStart.setTime(QTime.currentTime().addSecs(-QTime.currentTime().second()))  # без секунд
        self.timeEnd.setTime(self.timeStart.time().addSecs(3600))  # +1 час

        # Сигналы
        self.comboProject.currentIndexChanged.connect(self.update_tasks)
        self.btnSave.clicked.connect(self.accept)

        # Изначально задачи отключены
        self.comboTask.setEnabled(False)
        self.comboTask.addItem("Сначала выберите проект", None)

    def update_tasks(self):
        self.comboTask.clear()
        selected = self.comboProject.currentData()

        if selected is None or selected == "Без проекта":
            self.comboTask.setEnabled(False)
            self.comboTask.addItem("Задачи недоступны", None)
            return

        self.comboTask.setEnabled(True)
        self.comboTask.addItem("Выберите задачу", None)
        for task in self.projects.get(selected, []):
            self.comboTask.addItem(task, task)

    def get_overtime_data(self):
        """Возвращает данные для сохранения в основной программе"""
        project = self.comboProject.currentText()
        if project == "Без проекта" or project == "Выберите проект":
            project = None

        task = self.comboTask.currentText() if self.comboTask.isEnabled() else None
        if task == "Выберите задачу":
            task = None

        return {
            'project': project,
            'task': task,
            'date': self.dateEdit.date().toString("dd.MM.yyyy"),
            'start_time': self.timeStart.time().toString("hh:mm"),
            'end_time': self.timeEnd.time().toString("hh:mm"),
            'duration': self.calculate_duration(),
            'description': self.textDescription.toPlainText().strip()
        }

    def calculate_duration(self):
        """Вычисляет продолжительность в часах (например, 2.5)"""
        start = self.timeStart.time()
        end = self.timeEnd.time()
        secs = start.secsTo(end)
        if secs < 0:
            secs += 86400  # если конец на следующий день
        hours = secs / 3600
        return f"{hours:.1f}".replace(".", ",")


# Тест отдельно
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    dialog = AddOvertimeDialog()
    if dialog.exec():
        data = dialog.get_overtime_data()
        print("Сохранённые данные:")
        for k, v in data.items():
            print(f"  {k}: {v}")
    else:
        print("Диалог закрыт без сохранения")