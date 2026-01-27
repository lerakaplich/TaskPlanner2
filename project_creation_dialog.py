from PyQt6.QtWidgets import QDialog, QMessageBox, QListWidgetItem
from PyQt6.QtCore import QDate
from PyQt6.uic import loadUi


class ProjectCreationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Загружаем UI
        loadUi("project_creation_dialog.ui", self)

        # Начальные значения
        self.startDateEdit.setDate(QDate.currentDate())
        self.endDateEdit.setDate(QDate.currentDate().addMonths(1))

        # Пример списка сотрудников (потом заменишь на БД)
        self.available_users = [
            "Иванов И.И.",
            "Петров А.В.",
            "Сидорова Е.П.",
            "Кузнецов С.П."
        ]
        self.participantsList.addItems(self.available_users)

        # Подключение кнопок
        self.btnCancel.clicked.connect(self.reject)
        self.btnCreate.clicked.connect(self.on_create_clicked)
        self.btnAddParticipant.clicked.connect(self.add_participant)

        # Здесь будут данные созданного проекта
        self.project_data = None

    def add_participant(self):
        """
        Назначение роли выбранным участникам
        (пока просто пример логики)
        """
        selected_items = self.participantsList.selectedItems()
        role = self.roleCombo.currentText()

        for item in selected_items:
            item.setText(f"{item.text().split(' (')[0]} ({role})")

    def on_create_clicked(self):
        """
        Проверка данных и создание проекта
        """
        name = self.projectNameInput.text().strip()

        if not name:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Название проекта обязательно для заполнения"
            )
            return

        if self.endDateEdit.date() < self.startDateEdit.date():
            QMessageBox.warning(
                self,
                "Ошибка",
                "Дата окончания не может быть раньше даты начала"
            )
            return

        # Сбор данных проекта
        self.project_data = {
            "name": name,
            "description": self.projectDescriptionInput.toPlainText(),
            "start_date": self.startDateEdit.date().toString("dd.MM.yyyy"),
            "end_date": self.endDateEdit.date().toString("dd.MM.yyyy"),
            "participants": [
                self.participantsList.item(i).text()
                for i in range(self.participantsList.count())
            ],
            "template": self.templateCombo.currentText()
        }

        # Закрываем диалог others_tasks_page.ui результатом Accepted
        self.accept()

    def get_project_data(self):
        """
        Возвращает данные созданного проекта
        """
        return self.project_data
