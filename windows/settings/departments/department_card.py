from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QLabel
from PyQt6.QtCore import pyqtSignal
import os


class DepartmentCard(QFrame):
    """Карточка отдела на всю ширину"""

    edit_clicked = pyqtSignal(int)  # id отдела
    delete_clicked = pyqtSignal(int)  # id отдела

    def __init__(self, department_data, parent=None):
        super().__init__(parent)
        self.department_data = department_data
        self.department_id = department_data.get('id', 0)

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "settings", "departments", "department_card.ui"
        )
        uic.loadUi(ui_path, self)

        self.boss_labels = []  # для хранения созданных label руководителей
        self.fill_data()
        self.connect_signals()

    def connect_signals(self):
        """Подключение сигналов"""
        self.editButton.clicked.connect(lambda: self.edit_clicked.emit(self.department_id))
        self.deleteButton.clicked.connect(lambda: self.delete_clicked.emit(self.department_id))

    def clear_bosses_container(self):
        """Очистка контейнера с руководителями"""
        if hasattr(self, 'bossesContainer'):
            layout = self.bossesContainer.layout()
            if layout:
                # Удаляем все виджеты из layout
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
        if hasattr(self, 'divisionValue') and hasattr(self, 'divisionSectionLabel'):
            if division and division != '—':
                if isinstance(division, dict):
                    division = division.get('name', '—')
                self.divisionValue.setText(division)
                self.divisionValue.setVisible(True)
                self.divisionSectionLabel.setVisible(True)
            else:
                self.divisionValue.setVisible(False)
                self.divisionSectionLabel.setVisible(False)

        # Руководители
        self.clear_bosses_container()

        bosses = []
        # Проверяем разные возможные форматы хранения руководителей
        if 'bosses' in self.department_data and self.department_data['bosses']:
            bosses = self.department_data['bosses']
        elif 'boss' in self.department_data and self.department_data['boss']:
            bosses = [self.department_data['boss']]

        if hasattr(self, 'bossesSectionLabel') and hasattr(self, 'bossesContainer'):
            if bosses:
                self.bossesSectionLabel.setVisible(True)
                self.bossesContainer.setVisible(True)
                for boss in bosses:
                    self.add_boss_label(boss)
            else:
                self.bossesSectionLabel.setVisible(False)
                self.bossesContainer.setVisible(False)

        # Телефон
        phone = self.department_data.get('phone_number', '')
        if hasattr(self, 'phoneValue') and hasattr(self, 'phoneSectionLabel'):
            if phone:
                self.phoneValue.setText(phone)
                self.phoneValue.setVisible(True)
                self.phoneSectionLabel.setVisible(True)
            else:
                self.phoneValue.setVisible(False)
                self.phoneSectionLabel.setVisible(False)

    def get_bosses(self):
        """Получить список руководителей"""
        return [label.text() for label in self.boss_labels]