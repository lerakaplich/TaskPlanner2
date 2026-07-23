# windows/settings/departments/department_card.py

from PyQt6 import uic
from PyQt6.QtWidgets import QFrame, QLabel
from PyQt6.QtCore import pyqtSignal
import os


class DepartmentCard(QFrame):
    """Карточка отдела на всю ширину"""

    edit_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)

    def __init__(self, department_data, employee_service, parent=None, read_only=False, permission_service=None):
        super().__init__(parent)
        self.department_data = department_data
        self.employee_service = employee_service
        self.department_id = department_data.get('id', 0)
        self.read_only = read_only
        self.permission_service = permission_service

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

    def _can_edit_this_department(self) -> bool:
        """Проверяет, может ли пользователь редактировать этот отдел"""
        if not self.permission_service:
            return not self.read_only

        user_id = self.permission_service.user_id

        # Если пользователь - начальник отдела, он может редактировать ТОЛЬКО свой отдел
        combined = self.permission_service.get_combined_role()

        if combined.is_department_head:
            # Проверяем, является ли пользователь начальником ЭТОГО отдела
            boss_ids = self.department_data.get('boss_ids', [])
            return user_id in boss_ids

        # Для суперадмина и админа - можно редактировать всё
        if combined.is_super_admin or combined.is_admin:
            return True

        # Для начальника подразделения - можно редактировать отделы в своём подразделении
        if combined.is_division_head:
            # Проверяем, принадлежит ли отдел подразделению пользователя
            # Для этого нужно получить подразделения, где пользователь - начальник
            divisions = self.employee_service.get_all_divisions() if self.employee_service else []
            user_division_ids = []
            for div in divisions:
                boss_ids = div.get('boss_ids', [])
                if user_id in boss_ids:
                    user_division_ids.append(div.get('id'))

            department_division_id = self.department_data.get('division_id')
            return department_division_id in user_division_ids

        return False

    def _apply_read_only_state(self):
        """Применяет состояние только просмотра"""
        # Если read_only = True, значит пользователь не может редактировать этот отдел
        if self.read_only:
            if hasattr(self, 'deleteButton'):
                self.deleteButton.setVisible(False)
                self.deleteButton.hide()
            if hasattr(self, 'editButton'):
                self.editButton.setText("Подробнее")
        else:
            if hasattr(self, 'editButton'):
                self.editButton.setText("Редактировать")

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