from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QLabel
from PyQt6.QtCore import pyqtSignal
import os


class DepartmentCard(QFrame):
    """Карточка отдела на всю ширину"""

    edit_clicked = pyqtSignal(int)  # id отдела
    delete_clicked = pyqtSignal(int)  # id отдела

    def __init__(self, department_data, employee_resolver=None, parent=None):
        super().__init__(parent)
        self.department_data = department_data
        self.department_id = department_data.get('id', 0)
        self._get_employee_name = employee_resolver or (lambda x: str(x))

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "settings", "departments", "department_card.ui"
        )
        uic.loadUi(ui_path, self)

        self.boss_labels = []
        self.fill_data()
        self.connect_signals()

    def connect_signals(self):
        """Подключение сигналов"""
        self.editButton.clicked.connect(lambda: self.edit_clicked.emit(self.department_id))
        self.deleteButton.clicked.connect(lambda: self.delete_clicked.emit(self.department_id))

    def _parse_boss_ids(self, boss_field) -> list:
        """Парсит поле boss и возвращает список ID сотрудников"""
        if not boss_field:
            return []

        if isinstance(boss_field, str):
            # Проверяем, содержит ли строка только цифры и запятые
            if all(c.isdigit() or c == ',' or c.isspace() for c in boss_field):
                ids = []
                for part in boss_field.split(','):
                    part = part.strip()
                    if part and part.isdigit():
                        ids.append(int(part))
                return ids
            else:
                return []
        elif isinstance(boss_field, (int, float)):
            return [int(boss_field)]
        elif isinstance(boss_field, list):
            return boss_field
        return []

    def clear_bosses_container(self):
        """Очистка контейнера с руководителями"""
        if hasattr(self, 'bossesContainer'):
            layout = self.bossesContainer.layout()
            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
            self.boss_labels = []

    def add_boss_label(self, boss_name):
        """Добавление label с именем руководителя"""
        label = QLabel(boss_name)
        label.setObjectName("bossLabel")
        label.setStyleSheet("""
            QLabel#bossLabel {
                background-color: #F0F0F0;
                padding: 3px 12px;
                border-radius: 12px;
                font-size: 12px;
                color: #1B232A;
            }
        """)
        if hasattr(self, 'bossesContainer'):
            self.bossesContainer.layout().addWidget(label)
            self.boss_labels.append(label)

    def fill_data(self):
        """Заполнение данными"""
        # Название отдела
        name = self.department_data.get('name', '—')
        if hasattr(self, 'nameLabel'):
            self.nameLabel.setText(name)

        # Номер отдела
        number = self.department_data.get('number', '')
        if hasattr(self, 'numberLabel'):
            if number:
                self.numberLabel.setText(f"№ {number}")
                self.numberLabel.setVisible(True)
            else:
                self.numberLabel.setVisible(False)

        # Подразделение
        division = self.department_data.get('division', '—')
        if hasattr(self, 'divisionValueLabel') and hasattr(self, 'divisionSectionLabel'):
            if division and division != '—':
                if isinstance(division, dict):
                    division = division.get('name', '—')
                self.divisionValueLabel.setText(division)
                self.divisionValueLabel.setVisible(True)
                self.divisionSectionLabel.setVisible(True)
            else:
                self.divisionValueLabel.setVisible(False)
                self.divisionSectionLabel.setVisible(False)

        # Руководители - преобразуем ID в ФИО
        self.clear_bosses_container()

        boss_field = self.department_data.get('boss', '')
        boss_ids = self._parse_boss_ids(boss_field)

        boss_names = []
        for emp_id in boss_ids:
            emp_name = self._get_employee_name(emp_id)
            if emp_name and emp_name != str(emp_id):
                boss_names.append(emp_name)

        # Скрываем/показываем секцию руководителей
        if hasattr(self, 'bossesSectionLabel'):
            self.bossesSectionLabel.setVisible(len(boss_names) > 0)

        if hasattr(self, 'bossesContainer'):
            self.bossesContainer.setVisible(len(boss_names) > 0)
            for boss in boss_names:
                self.add_boss_label(boss)

        # Телефон
        phone = self.department_data.get('phone_number', '')
        if hasattr(self, 'phoneValueLabel') and hasattr(self, 'phoneSectionLabel'):
            if phone:
                self.phoneValueLabel.setText(phone)
                self.phoneValueLabel.setVisible(True)
                self.phoneSectionLabel.setVisible(True)
            else:
                self.phoneValueLabel.setVisible(False)
                self.phoneSectionLabel.setVisible(False)

    def get_bosses(self):
        """Получить список руководителей"""
        return [label.text() for label in self.boss_labels]