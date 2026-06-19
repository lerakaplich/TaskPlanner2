# windows/overtime/overtime_card.py

import os
from PyQt6.QtWidgets import QFrame
from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal

from services.overtime_service.overtime_base_service import OvertimeBaseService


class OvertimeCard(QFrame):
    """UI карточка переработки. Только отображение, без логики"""

    edit_clicked = pyqtSignal(int)
    add_details_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)

    def __init__(self, overtime_data, parent=None, can_edit=True, can_delete=False):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "ui", "overtime"
        )
        uic.loadUi(os.path.join(ui_path, "overtime_card.ui"), self)

        self.overtime_data = overtime_data
        self.overtime_id = overtime_data.get('id', 0)
        self.base = OvertimeBaseService()
        self.can_edit = can_edit
        self.can_delete = can_delete

        self.setObjectName("OvertimeCard")
        self.setup_data()
        self.connect_signals()
        self._apply_permissions()

    def _apply_permissions(self):
        """Применяет права доступа к кнопкам"""
        # Определяем, есть ли описание у переработки
        has_description = self.base.has_description(self.overtime_data)

        # Кнопка "Добавить" - показываем если НЕТ описания
        if hasattr(self, 'btnAdd'):
            self.btnAdd.setVisible(not has_description and self.can_edit)
            self.btnAdd.setEnabled(not has_description and self.can_edit)
            # Обновляем текст кнопки для ясности
            if not has_description and self.can_edit:
                self.btnAdd.setText("Добавить")
            else:
                self.btnAdd.setText("Добавить")

        # Кнопка "Редактировать" - показываем если ЕСТЬ описание
        if hasattr(self, 'btnEdit'):
            self.btnEdit.setVisible(has_description and self.can_edit)
            self.btnEdit.setEnabled(has_description and self.can_edit)

        # Кнопка "Удалить" - только для админа и суперадмина
        if hasattr(self, 'btnDelete'):
            self.btnDelete.setVisible(self.can_delete)
            self.btnDelete.setEnabled(self.can_delete)

    def connect_signals(self):
        if hasattr(self, 'btnEdit'):
            self.btnEdit.clicked.connect(lambda: self.edit_clicked.emit(self.overtime_id))
        if hasattr(self, 'btnAdd'):
            self.btnAdd.clicked.connect(lambda: self.add_details_clicked.emit(self.overtime_id))
        if hasattr(self, 'btnDelete'):
            self.btnDelete.clicked.connect(lambda: self.delete_clicked.emit(self.overtime_id))

    def setup_data(self):
        data = self.overtime_data

        has_description = self.base.has_description(data)

        self.descriptionLabel.setText(self.base.get_display_description(data))
        self.dateLabel.setText(data.get('date', '-'))
        self.timeLabel.setText(data.get('time_period', '-'))
        self.durationLabel.setText(f"{data.get('duration', '-')} ч.")

        project_name = data.get('project')
        task_title = data.get('task')

        if project_name:
            self.projectLabel.setText(f"🏢 Проект: {project_name}")
            self.projectLabel.setVisible(True)
        else:
            self.projectLabel.setVisible(False)

        if task_title:
            self.taskLabel.setText(f"📝 Задача: {task_title}")
            self.taskLabel.setVisible(True)
        else:
            self.taskLabel.setVisible(False)

        self.userLabel.setText(data.get('user', 'Неизвестный'))