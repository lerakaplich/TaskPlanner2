# windows/settings/departments/department_card.py

from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QLabel
from PyQt6.QtCore import pyqtSignal
import os


class DepartmentCard(QFrame):
    """Карточка отдела на всю ширину"""

    edit_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)

    def __init__(self, department_data, employee_service, parent=None, read_only=False):
        super().__init__(parent)
        self.department_data = department_data
        self.employee_service = employee_service
        self.department_id = department_data.get('id', 0)
        self.read_only = read_only

        # Загрузка UI
        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "..",
            "ui", "settings", "departments", "department_card.ui"
        )
        uic.loadUi(ui_path, self)

        self.fill_data()
        self.connect_signals()
        self._apply_read_only_state()

    def _apply_read_only_state(self):
        """Применяет состояние только просмотра"""
        if self.read_only:
            # Скрываем кнопку удаления
            if hasattr(self, 'deleteButton'):
                self.deleteButton.setVisible(False)
                self.deleteButton.hide()

            # Переименовываем кнопку редактирования
            if hasattr(self, 'editButton'):
                self.editButton.setText("Подробнее")

    def connect_signals(self):
        """Подключение сигналов"""
        self.editButton.clicked.connect(lambda: self.edit_clicked.emit(self.department_id))
        if not self.read_only:
            self.deleteButton.clicked.connect(lambda: self.delete_clicked.emit(self.department_id))

    def fill_data(self):
        """Заполнение данными через сервис"""
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
        division_name = self.department_data.get('division_name', '—')
        if hasattr(self, 'divisionValueLabel') and hasattr(self, 'divisionSectionLabel'):
            if division_name and division_name != '—':
                self.divisionValueLabel.setText(division_name)
                self.divisionValueLabel.setVisible(True)
                self.divisionSectionLabel.setVisible(True)
            else:
                self.divisionValueLabel.setVisible(False)
                self.divisionSectionLabel.setVisible(False)

        # Руководители
        self.setup_bosses_container()
        boss_names = self.department_data.get('boss_names', [])

        # Скрываем/показываем секцию руководителей
        if hasattr(self, 'bossesSectionLabel'):
            self.bossesSectionLabel.setVisible(len(boss_names) > 0)

        if hasattr(self, 'bossesContainer'):
            # Очищаем контейнер
            layout = self.bossesContainer.layout()
            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()

            if boss_names:
                boss_text = ", ".join(boss_names)
                label = QLabel(boss_text)
                label.setObjectName("bossLabel")
                label.setStyleSheet("""
                    QLabel#bossLabel {
                        background-color: transparent;
                        font-size: 12px;
                        color: #1B232A;
                        word-wrap: break-word;
                        padding: 0px;
                    }
                """)
                layout.addWidget(label)
                self.bossesContainer.setVisible(True)
            else:
                self.bossesContainer.setVisible(False)

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

    def setup_bosses_container(self):
        """Настройка контейнера для руководителей"""
        if hasattr(self, 'bossesContainer'):
            self.bossesContainer.setStyleSheet("""
                QWidget#bossesContainer {
                    background-color: transparent;
                    border: none;
                }
            """)
            if self.bossesContainer.layout():
                self.bossesContainer.layout().setContentsMargins(0, 0, 0, 0)
                self.bossesContainer.layout().setSpacing(4)