from PyQt6 import uic
from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import pyqtSignal
import os


class DivisionCard(QFrame):
    """Карточка подразделения на всю ширину"""

    edit_clicked = pyqtSignal(int)  # id подразделения
    delete_clicked = pyqtSignal(int)  # id подразделения

    def __init__(self, division_data, parent=None):
        super().__init__(parent)
        self.division_data = division_data
        self.division_id = division_data.get('id', 0)

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "settings", "divisions", "division_card.ui"
        )
        uic.loadUi(ui_path, self)

        self.fill_data()
        self.connect_signals()

    def connect_signals(self):
        """Подключение сигналов"""
        self.editButton.clicked.connect(lambda: self.edit_clicked.emit(self.division_id))
        self.deleteButton.clicked.connect(lambda: self.delete_clicked.emit(self.division_id))

    def fill_data(self):
        """Заполнение данными"""
        # Название
        name = self.division_data.get('name', '—')
        if hasattr(self, 'nameLabel'):
            self.nameLabel.setText(name)

        # Номер
        number = self.division_data.get('number', '')
        if hasattr(self, 'numberLabel'):
            if number:
                self.numberLabel.setText(f"№ {number}")
                self.numberLabel.setVisible(True)
            else:
                self.numberLabel.setVisible(False)

        # Расшифровка (workshop_code) - это текст из textEditDescription
        workshop_code = self.division_data.get('workshop_code', '')
        if hasattr(self, 'codeValue') and hasattr(self, 'codeSectionLabel'):
            if workshop_code and workshop_code.strip():
                self.codeValue.setText(workshop_code)
                self.codeValue.setVisible(True)
                self.codeSectionLabel.setVisible(True)
            else:
                self.codeValue.setVisible(False)
                self.codeSectionLabel.setVisible(False)

        # Руководитель
        boss = self.division_data.get('boss', '')
        if hasattr(self, 'bossValue') and hasattr(self, 'bossSectionLabel'):
            if boss:
                self.bossValue.setText(boss)
                self.bossValue.setVisible(True)
                self.bossSectionLabel.setVisible(True)
            else:
                self.bossValue.setVisible(False)
                self.bossSectionLabel.setVisible(False)

        # Телефон
        phone = self.division_data.get('phone_number', '')
        if hasattr(self, 'phoneValue') and hasattr(self, 'phoneSectionLabel'):
            if phone:
                self.phoneValue.setText(phone)
                self.phoneValue.setVisible(True)
                self.phoneSectionLabel.setVisible(True)
            else:
                self.phoneValue.setVisible(False)
                self.phoneSectionLabel.setVisible(False)