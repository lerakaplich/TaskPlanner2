# windows/overtime/add_overtime_dialog.py

import os
from typing import Dict, Optional
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import QDate, QTime

from services.permissions.app_permissions import AppRole


class AddOvertimeDialog(QDialog):
    """UI-диалог добавления переработки"""

    def __init__(self, service=None, permission_service=None, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "overtime")
        uic.loadUi(os.path.join(ui_path, "add_overtime_dialog.ui"), self)

        self.service = service
        self.permission_service = permission_service

        for widget in [self.comboEmployee, self.comboProject, self.comboTask,
                       self.dateEdit, self.timeStart, self.timeEnd, self.btnSave]:
            widget.setFixedHeight(32)

        self.titleLabel.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #000000; background-color: #FFFFFF;"
        )

        self._load_employees()
        self._load_projects()

        self.dateEdit.setDate(QDate.currentDate())
        self.timeStart.setTime(QTime.currentTime().addSecs(-QTime.currentTime().second()))
        self.timeEnd.setTime(self.timeStart.time().addSecs(3600))

        self.comboProject.currentIndexChanged.connect(self._on_project_changed)
        self.btnSave.clicked.connect(self.accept)

        self.comboTask.setEnabled(False)
        self.comboTask.clear()
        self.comboTask.addItem("Сначала выберите проект", None)

    def _load_employees(self):
        """Загружает сотрудников в зависимости от прав"""
        self.comboEmployee.clear()
        if not self.service:
            return

        employees = self.service.get_all_employees()
        can_edit_all = True

        # Проверяем права
        if self.permission_service:
            role = self.permission_service.app_manager.role
            can_edit_all = role in (AppRole.ADMIN, AppRole.SUPER_ADMIN)
            print(f"[DEBUG] AddOvertimeDialog: role={role.value}, can_edit_all={can_edit_all}")

        if can_edit_all:
            # Админ/суперадмин - показываем всех
            for emp in employees:
                self.comboEmployee.addItem(emp['name'], emp['id'])
            self.comboEmployee.setEnabled(True)
        else:
            # Обычный пользователь - только себя
            current_user_id = self.service.current_user_id
            for emp in employees:
                if emp['id'] == current_user_id:
                    self.comboEmployee.addItem(emp['name'], emp['id'])
                    break
            self.comboEmployee.setEnabled(False)

    def _load_projects(self):
        self.comboProject.clear()
        self.comboProject.addItem("Выберите проект", None)
        if self.service:
            projects = self.service.get_projects(only_active=True)
            for project in projects:
                self.comboProject.addItem(project['name'], project['id'])
        self.comboProject.addItem("Без проекта", -1)
        self.comboProject.setCurrentIndex(0)

    def _on_project_changed(self, index):
        project_id = self.comboProject.currentData()
        if project_id is None or project_id == -1:
            self.comboTask.setEnabled(False)
            self.comboTask.clear()
            self.comboTask.addItem("Нет задач", None)
            return
        self._load_tasks(project_id)

    def _load_tasks(self, project_id: int):
        self.comboTask.clear()
        self.comboTask.addItem("Выберите задачу", None)
        if self.service:
            tasks = self.service.get_tasks_for_project(project_id)
            for task in tasks:
                self.comboTask.addItem(task['title'], task['id'])
        self.comboTask.addItem("Без задачи", -1)
        self.comboTask.setEnabled(True)
        self.comboTask.setCurrentIndex(0)

    def get_overtime_data(self) -> Dict:
        employee_id = self.comboEmployee.currentData()
        project_id = self.comboProject.currentData()
        task_id = self.comboTask.currentData() if self.comboTask.isEnabled() else None

        if project_id == -1:
            project_id = None
        if task_id == -1:
            task_id = None

        return {
            'employee_id': employee_id,
            'date': self.dateEdit.date(),
            'start_time': self.timeStart.time(),
            'end_time': self.timeEnd.time(),
            'description': self.textDescription.toPlainText(),
            'project_id': project_id,
            'task_id': task_id
        }