# windows/overtime/add_overtime_dialog.py

import os
from typing import Dict, Optional
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import QDate, QTime

from services.overtime_service import OvertimeService


class AddOvertimeDialog(QDialog):
    """UI-диалог добавления переработки"""

    def __init__(self, service: Optional[OvertimeService] = None, parent=None):
        super().__init__(parent)

        # UI
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "overtime")
        uic.loadUi(os.path.join(ui_path, "add_overtime_dialog.ui"), self)

        self.service = service
        self.current_user_id = None

        # Настройки высоты
        for widget in [self.comboEmployee, self.comboProject, self.comboTask,
                       self.dateEdit, self.timeStart, self.timeEnd, self.btnSave]:
            widget.setFixedHeight(32)

        self.titleLabel.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #000000; background-color: #FFFFFF;"
        )

        # Загружаем сотрудников
        self.load_employees()

        # Загружаем проекты
        self.load_projects()

        # Дата и время по умолчанию
        self.dateEdit.setDate(QDate.currentDate())
        self.timeStart.setTime(QTime.currentTime().addSecs(-QTime.currentTime().second()))
        self.timeEnd.setTime(self.timeStart.time().addSecs(3600))

        # Сигналы
        self.comboProject.currentIndexChanged.connect(self.on_project_changed)
        self.btnSave.clicked.connect(self.accept)

        # Изначально задачи отключены
        self.comboTask.setEnabled(False)
        self.comboTask.clear()
        self.comboTask.addItem("Сначала выберите проект", None)

    # windows/overtime/add_overtime_dialog.py

    def load_employees(self):
        """Загружает список сотрудников в комбобокс"""
        self.comboEmployee.clear()
        print("🔄 Загрузка сотрудников в диалог...")

        if self.service:
            employees = self.service.get_all_employees()
            print(f"📊 Получено {len(employees)} сотрудников из сервиса")

            for emp in employees:
                self.comboEmployee.addItem(emp['name'], emp['id'])
                print(f"  + Добавлен: {emp['name']} (ID: {emp['id']})")

            # Если есть текущий пользователь, выбираем его по умолчанию
            if hasattr(self.service, 'current_user_id') and self.service.current_user_id:
                for i in range(self.comboEmployee.count()):
                    if self.comboEmployee.itemData(i) == self.service.current_user_id:
                        self.comboEmployee.setCurrentIndex(i)
                        print(f"✅ Выбран текущий пользователь ID: {self.service.current_user_id}")
                        break
        else:
            print("❌ Сервис не инициализирован")

    def load_projects(self):
        """Загружает список проектов в комбобокс"""
        self.comboProject.clear()
        self.comboProject.addItem("Выберите проект", None)

        if self.service:
            projects = self.service.get_projects()
            for project in projects:
                self.comboProject.addItem(project['name'], project['id'])

        self.comboProject.addItem("Без проекта", -1)
        self.comboProject.setCurrentIndex(0)

    def on_project_changed(self, index):
        """Обработчик изменения выбранного проекта"""
        project_id = self.comboProject.currentData()

        if project_id is None or project_id == -1:
            # Если проект не выбран или "Без проекта"
            self.comboTask.setEnabled(False)
            self.comboTask.clear()
            self.comboTask.addItem("Нет задач", None)
            return

        # Загружаем задачи для выбранного проекта
        self.load_tasks(project_id)

    def load_tasks(self, project_id: int):
        """Загружает задачи для выбранного проекта"""
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
        """Возвращает данные для добавления переработки"""
        employee_id = self.comboEmployee.currentData()
        project_id = self.comboProject.currentData()
        task_id = self.comboTask.currentData() if self.comboTask.isEnabled() else None

        # Если выбрано "Без проекта" или "Без задачи", передаем None
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