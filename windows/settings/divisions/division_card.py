from PyQt6 import uic
from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import pyqtSignal
import os


class DivisionCard(QFrame):
    """Карточка подразделения на всю ширину"""

    edit_clicked = pyqtSignal(int)  # id подразделения
    delete_clicked = pyqtSignal(int)  # id подразделения

    def __init__(self, division_data, employee_resolver=None, parent=None):
        super().__init__(parent)
        self.division_data = division_data
        self.division_id = division_data.get('id', 0)
        self._get_employee_name = employee_resolver or (lambda x: str(x))  # ← резолвер имён

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

    def _parse_boss_ids(self, boss_field) -> list:
        """Парсит поле boss и возвращает список ID сотрудников"""
        if not boss_field:
            return []

        if isinstance(boss_field, str):
            # Проверяем, содержит ли строка только цифры и запятые
            if all(c.isdigit() or c == ',' or c.isspace() for c in boss_field):
                # Парсим строку с ID через запятую
                ids = []
                for part in boss_field.split(','):
                    part = part.strip()
                    if part and part.isdigit():
                        ids.append(int(part))
                return ids
            else:
                # Это текстовые имена (старый формат) - возвращаем пустой список
                return []
        elif isinstance(boss_field, (int, float)):
            return [int(boss_field)]
        elif isinstance(boss_field, list):
            return boss_field
        return []

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

        # === ИСПРАВЛЕНИЕ: Руководители - преобразуем ID в ФИО ===
        boss_field = self.division_data.get('boss', '')
        boss_ids = self._parse_boss_ids(boss_field)

        boss_names = []
        for emp_id in boss_ids:
            name = self._get_employee_name(emp_id)
            if name and name != str(emp_id):
                boss_names.append(name)

        boss_text = ', '.join(boss_names) if boss_names else ''

        if hasattr(self, 'bossValue') and hasattr(self, 'bossSectionLabel'):
            if boss_text:
                self.bossValue.setText(boss_text)
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