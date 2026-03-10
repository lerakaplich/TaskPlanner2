# windows/profile/edit_profile.py

import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import QDate

from services.profile_service import ProfileService


class EditProfileDialog(QDialog):
    """Диалог редактирования профиля"""

    def __init__(self, parent=None, employee_data=None, profile_service=None):
        super().__init__(parent)

        self.employee_data = employee_data or {}
        self.profile_service = profile_service or ProfileService()
        self.employee_id = self.employee_data.get('id')

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "profile"
        )

        uic.loadUi(os.path.join(ui_path, "edit_profile.ui"), self)

        self.fill_fields()
        self.connect_signals()

    # ---------- UI ----------

    def fill_fields(self):
        """Заполняет поля формы данными"""
        data = self.profile_service.prepare_profile_form_data(self.employee_data)

        if hasattr(self, 'lineEditPhone'):
            self.lineEditPhone.setText(data["phone_number"])

        if hasattr(self, 'lineEditEmail'):
            self.lineEditEmail.setText(data["email"])

        if hasattr(self, 'dateEditBirth') and data["birth_date"]:
            self.dateEditBirth.setDate(data["birth_date"])

    def connect_signals(self):
        """Подключает сигналы"""
        if hasattr(self, 'btnSave'):
            self.btnSave.clicked.connect(self.save_profile)

        if hasattr(self, 'btnCancel'):
            self.btnCancel.clicked.connect(self.reject)

        if hasattr(self, 'btnEditPhoto'):
            self.btnEditPhoto.clicked.connect(self.edit_photo)

    # ---------- ACTIONS ----------

    def save_profile(self):
        """Сохраняет изменения профиля"""
        try:
            # Собираем данные из формы
            updates = self.profile_service.build_profile_update_data(
                phone=self.lineEditPhone.text(),
                email=self.lineEditEmail.text(),
                birth_date=self.dateEditBirth.date()
            )

            # Сохраняем в БД
            success = self.profile_service.update_employee_profile(
                self.employee_id,
                updates
            )

            if success:
                # Обновляем локальные данные
                self.employee_data = self.profile_service.apply_profile_updates(
                    self.employee_data,
                    updates
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    "Не удалось сохранить изменения в базе данных"
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Ошибка при сохранении: {str(e)}"
            )

    def edit_photo(self):
        """Изменение фото (заглушка)"""
        QMessageBox.information(
            self,
            "Изменение фото",
            "Функция изменения фото будет доступна в следующей версии."
        )