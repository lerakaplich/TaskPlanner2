import os
from PyQt6.QtWidgets import QDialog
from PyQt6.uic import loadUi
from PyQt6.QtCore import QDate


class EditProfileDialog(QDialog):
    def __init__(self, parent=None, employee_data=None):
        super().__init__(parent)

        self.employee_data = employee_data or {}

        # Путь к папке ui (как ты просила)
        self.ui_path = os.path.join(os.path.dirname(__file__), "..", "ui")

        # Загружаем UI из файла
        loadUi(os.path.join(self.ui_path, "edit_profile.ui"), self)

        # Если есть данные — заполняем поля
        self.fill_fields()

        # Подключаем кнопки
        self.btnSave.clicked.connect(self.save_profile)
        self.btnEditPhoto.clicked.connect(self.edit_photo)

    def fill_fields(self):
        if "phone_number" in self.employee_data:
            self.lineEditPhone.setText(self.employee_data["phone_number"])

        if "email" in self.employee_data:
            self.lineEditEmail.setText(self.employee_data["email"])

        if "birth_date" in self.employee_data and self.employee_data["birth_date"]:
            self.dateEditBirth.setDate(
                QDate.fromString(self.employee_data["birth_date"], "yyyy-MM-dd")
            )

    def save_profile(self):
        self.employee_data["phone_number"] = self.lineEditPhone.text()
        self.employee_data["email"] = self.lineEditEmail.text()
        self.employee_data["birth_date"] = (
            self.dateEditBirth.date().toString("yyyy-MM-dd")
        )

        self.accept()  # важно, а не close()

    def edit_photo(self):
        print("Изменение фото")
