# windows/profile/edit_profile.py

import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox


class EditProfileDialog(QDialog):
    """Диалог редактирования профиля (только UI)"""

    def __init__(self, parent=None, employee_data=None, profile_service=None):
        super().__init__(parent)

        self.employee_data = employee_data or {}
        self.profile_service = profile_service
        self.employee_id = self.employee_data.get('id')

        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "profile")
        uic.loadUi(os.path.join(ui_path, "edit_profile.ui"), self)

        self._fill_fields()
        self._connect_signals()

    def _fill_fields(self):
        """Заполняет поля формы данными через сервис"""
        if not self.profile_service:
            return

        data = self.profile_service.get_edit_form_data(self.employee_data)

        if hasattr(self, 'lineEditPhone'):
            self.lineEditPhone.setText(data["phone_number"])
        if hasattr(self, 'lineEditEmail'):
            self.lineEditEmail.setText(data["email"])
        if hasattr(self, 'dateEditBirth') and data["birth_date"]:
            self.dateEditBirth.setDate(data["birth_date"])

    def _connect_signals(self):
        if hasattr(self, 'btnSave'):
            self.btnSave.clicked.connect(self._save_profile)
        if hasattr(self, 'btnCancel'):
            self.btnCancel.clicked.connect(self.reject)
        if hasattr(self, 'btnEditPhoto'):
            self.btnEditPhoto.clicked.connect(self._edit_photo)

    def _save_profile(self):
        """Сохраняет изменения через сервис"""
        if not self.profile_service:
            QMessageBox.critical(self, "Ошибка", "Сервис не инициализирован")
            return

        updates = self.profile_service.build_update_data(
            phone=self.lineEditPhone.text() if hasattr(self, 'lineEditPhone') else None,
            email=self.lineEditEmail.text() if hasattr(self, 'lineEditEmail') else None,
            birth_date=self.dateEditBirth.date() if hasattr(self, 'dateEditBirth') else None
        )

        success = self.profile_service.update_profile(self.employee_id, updates)

        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить изменения в базе данных")

    def _edit_photo(self):
        QMessageBox.information(self, "Изменение фото", "Функция изменения фото будет доступна в следующей версии.")