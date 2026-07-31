# windows/settings/base_tab.py

import os

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox, QPushButton,
    QMessageBox, QDialog, QVBoxLayout,
    QLabel
)

from windows.permissions.ui_permission_mixin import UIPermissionMixin


class BaseTab(QWidget, UIPermissionMixin):
    """Базовый класс для всех вкладок настроек - ТОЛЬКО UI логика"""

    item_deleted = pyqtSignal(str, int)
    item_edited = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = []
        self.employee_service = None
        self.user_id = None
        self._search_query = ""  # <-- ДОБАВЛЯЕМ

        # Загрузка UI
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
        ui_path = os.path.join(project_root, "ui", "settings", "base_tab.ui")

        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"base_tab.ui не найден: {ui_path}")

        uic.loadUi(ui_path, self)

        self.tools_frame = self.findChild(QWidget, "toolsFrame")
        self.btnAdd = self.findChild(QPushButton, "btnAdd")
        self.filterDepartment = self.findChild(QComboBox, "filterDepartment")
        self.filterSubDepartment = self.findChild(QComboBox, "filterSubDepartment")

        if self.tools_frame:
            self.tools_frame.setFixedHeight(72)

        FIXED_HEIGHT = 35

        if self.btnAdd:
            self.btnAdd.setFixedHeight(FIXED_HEIGHT)
            self.btnAdd.setMinimumHeight(FIXED_HEIGHT)
            self.btnAdd.setMaximumHeight(FIXED_HEIGHT)

        for combo in (self.filterDepartment, self.filterSubDepartment):
            if combo:
                combo.setFixedHeight(FIXED_HEIGHT)
                combo.setMinimumHeight(FIXED_HEIGHT)
                combo.setMaximumHeight(FIXED_HEIGHT)

        if hasattr(self, 'toolsLayout'):
            self.toolsLayout.setContentsMargins(24, 18, 24, 18)
            self.toolsLayout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

    # ==========================================================
    # МЕТОДЫ ПОИСКА (ДОБАВЛЕНЫ)
    # ==========================================================

    def apply_search_filter(self, query: str):
        """
        Применяет фильтр поиска ко всем элементам вкладки.
        Должен быть переопределён в дочерних классах, если там есть своя логика.
        """
        self._search_query = query
        self._apply_search_to_items()

    def _apply_search_to_items(self):
        """
        Внутренний метод применения поиска.
        По умолчанию фильтрует карточки по названию.
        Может быть переопределён в дочерних классах.
        """
        query = self._search_query.lower().strip() if hasattr(self, '_search_query') else ""

        for card in self.cards:
            if query:
                card_name = self._get_card_search_text(card)
                card.setVisible(query in card_name.lower())
            else:
                card.setVisible(True)

    def _get_card_search_text(self, card) -> str:
        """
        Возвращает текст для поиска из карточки.
        Должен быть переопределён в дочерних классах.
        """
        if hasattr(card, 'nameLabel'):
            return card.nameLabel.text()
        return ""

    def clear_search_filter(self):
        """Очищает фильтр поиска"""
        self._search_query = ""
        self._apply_search_to_items()

    def get_filtered_count(self) -> int:
        """Возвращает количество видимых элементов"""
        count = 0
        for card in self.cards:
            if card.isVisible():
                count += 1
        return count

    def showEvent(self, event):
        """Обновляет данные при показе вкладки"""
        super().showEvent(event)
        if hasattr(self, 'load_divisions') and self.employee_service:
            QTimer.singleShot(50, self.load_divisions)

    def set_employee_service(self, service):
        self.employee_service = service

    def set_permission_service(self, permission_service):
        self._permission_service = permission_service
        if permission_service:
            self.user_id = permission_service.user_id
        self.setup_permission_ui()

    def hide_filters(self):
        if self.filterDepartment:
            self.filterDepartment.hide()
        if self.filterSubDepartment:
            self.filterSubDepartment.hide()

    def show_filters(self):
        if self.filterDepartment:
            self.filterDepartment.show()
        if self.filterSubDepartment:
            self.filterSubDepartment.show()
        if self.tools_frame:
            self.tools_frame.updateGeometry()

    def setup_permission_ui(self):
        self._apply_read_only_state()

    def _apply_read_only_state(self):
        """Применяет состояние только просмотра — скрывает кнопку добавления"""
        if self.btnAdd:
            self.btnAdd.setVisible(self._should_show_add_buttons())

    def confirm_delete(self, title: str, message: str, item_type: str, item_id: int):
        if self._read_only_mode:
            QMessageBox.information(self, "Информация", "В режиме просмотра удаление недоступно")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setFixedSize(420, 180)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(20)

        label = QLabel(message)
        label.setWordWrap(True)
        label.setStyleSheet("""
            font-size: 15px;
            color: #2c3e50;
            font-weight: 500;
        """)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        btn_no = QPushButton("Нет")
        btn_no.setFixedHeight(28)
        btn_no.setStyleSheet("""
            QPushButton {
                background-color: #D22730;
                color: white;
                border-radius: 6px;
                font-weight: bold;
                font-size: 15px;
                border: none;
            }
            QPushButton:hover {
                background-color: #862633;
            }
        """)

        btn_yes = QPushButton("Да")
        btn_yes.setFixedHeight(28)
        btn_yes.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border-radius: 6px;
                font-weight: bold;
                font-size: 15px;
                border: none;
            }
            QPushButton:hover {
                background-color: #998664;
            }
        """)

        btn_layout.addWidget(btn_no)
        btn_layout.addWidget(btn_yes)
        layout.addLayout(btn_layout)

        btn_no.clicked.connect(dialog.reject)
        btn_yes.clicked.connect(dialog.accept)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.item_deleted.emit(item_type, item_id)

    def clear_cards(self):
        for card in self.cards:
            self.cardsGridLayout.removeWidget(card)
            card.deleteLater()
        self.cards.clear()

    def add_card_to_grid(self, card, index: int):
        row = index // 2
        col = index % 2
        self.cardsGridLayout.addWidget(card, row, col)
        self.cards.append(card)

    def set_last_row_stretch(self):
        if self.cards:
            last_row = (len(self.cards) - 1) // 2
            self.cardsGridLayout.setRowStretch(last_row + 1, 1)

    def _rename_edit_buttons(self):
        """Переименовывает кнопки редактирования на 'Подробнее'"""
        for card in self.cards:
            if hasattr(card, 'editButton'):
                card.editButton.setText("Подробнее")