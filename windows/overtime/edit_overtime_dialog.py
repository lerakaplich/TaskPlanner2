# windows/overtime/edit_overtime_dialog.py

import os
from typing import Dict, Optional
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import QDate, QTime, QTimer


class EditOvertimeDialog(QDialog):
    """UI-диалог редактирования переработки"""

    def __init__(self, service=None, overtime_data: Optional[Dict] = None, parent=None):
        super().__init__(parent)

        self.service = service
        self.overtime_data = overtime_data
        self.overtime_id = overtime_data.get('id') if overtime_data else None
        self.current_project_id = None
        self.current_task_id = None

        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "overtime")
        uic.loadUi(os.path.join(ui_path, "add_overtime_dialog.ui"), self)

        self.setWindowTitle("Редактирование переработки")
        if hasattr(self, 'titleLabel'):
            self.titleLabel.setText("Редактирование переработки")

        for widget in [self.comboEmployee, self.comboProject, self.comboTask,
                       self.dateEdit, self.timeStart, self.timeEnd, self.btnSave]:
            widget.setFixedHeight(32)

        self._load_employees()
        self._load_projects()

        # Загружаем данные переработки
        self._load_overtime_data()

        self.comboProject.currentIndexChanged.connect(self._on_project_changed)
        self.btnSave.clicked.connect(self._save_overtime)

        self.comboTask.setEnabled(False)
        self.comboTask.clear()
        self.comboTask.addItem("Сначала выберите проект", None)

    def _load_employees(self):
        self.comboEmployee.clear()
        if self.service:
            employees = self.service.get_all_employees()
            for emp in employees:
                self.comboEmployee.addItem(emp['name'], emp['id'])

            if self.overtime_data:
                employee_id = self.overtime_data.get('employee_id')
                for i in range(self.comboEmployee.count()):
                    if self.comboEmployee.itemData(i) == employee_id:
                        self.comboEmployee.setCurrentIndex(i)
                        break

    def _load_projects(self):
        self.comboProject.blockSignals(True)
        self.comboProject.clear()
        self.comboProject.addItem("Выберите проект", None)
        if self.service:
            projects = self.service.get_projects(only_active=True)
            for project in projects:
                self.comboProject.addItem(project['name'], project['id'])
        self.comboProject.addItem("Без проекта", -1)
        self.comboProject.blockSignals(False)

    def _load_overtime_data(self):
        """Загружает данные переработки в поля диалога"""
        if not self.overtime_data:
            return

        print(f"[DEBUG] Загрузка данных переработки: {self.overtime_data}")

        # 1. Дата
        date_str = self.overtime_data.get('date')
        if date_str:
            qdate = QDate.fromString(date_str, "dd.MM.yyyy")
            if qdate.isValid():
                self.dateEdit.setDate(qdate)

        # 2. Время начала
        start_time = self.overtime_data.get('start_time')
        if start_time and ':' in start_time:
            parts = start_time.split(':')
            if len(parts) >= 2:
                self.timeStart.setTime(QTime(int(parts[0]), int(parts[1])))

        # 3. Время окончания
        end_time = self.overtime_data.get('end_time')
        if end_time and ':' in end_time:
            parts = end_time.split(':')
            if len(parts) >= 2:
                self.timeEnd.setTime(QTime(int(parts[0]), int(parts[1])))

        # 4. Описание
        description = self.overtime_data.get('description', '')
        self.textDescription.setPlainText(description)

        # 5. Проект
        project_id = self.overtime_data.get('project_id')
        print(f"[DEBUG] project_id из данных: {project_id}")

        self.comboProject.blockSignals(True)

        if project_id:
            found = False
            for i in range(self.comboProject.count()):
                if self.comboProject.itemData(i) == project_id:
                    self.comboProject.setCurrentIndex(i)
                    self.current_project_id = project_id
                    print(f"[DEBUG] Проект найден: {self.comboProject.itemText(i)}")
                    found = True
                    break

            if not found:
                project_name = self.overtime_data.get('project')
                if project_name:
                    for i in range(self.comboProject.count()):
                        if self.comboProject.itemText(i) == project_name:
                            self.comboProject.setCurrentIndex(i)
                            self.current_project_id = self.comboProject.itemData(i)
                            print(f"[DEBUG] Проект найден по названию: {project_name}")
                            found = True
                            break

        self.comboProject.blockSignals(False)

        # 6. Задача - используем отложенную установку
        task_id = self.overtime_data.get('task_id')
        task_title = self.overtime_data.get('task')
        print(f"[DEBUG] task_id из данных: {task_id}, task_title: {task_title}")

        # Если выбран проект, загружаем задачи и устанавливаем задачу с задержкой
        selected_project_id = self.comboProject.currentData()
        if selected_project_id and selected_project_id != -1:
            # Загружаем задачи
            self.comboTask.blockSignals(True)
            self._load_tasks_internal(selected_project_id)
            self.comboTask.blockSignals(False)

            # Устанавливаем задачу с задержкой, чтобы UI успел обновиться
            if task_id or task_title:
                QTimer.singleShot(50, lambda: self._set_task(task_id, task_title))

    def _set_task(self, task_id: Optional[int], task_title: Optional[str]):
        """Устанавливает задачу в комбобоксе"""
        print(f"[DEBUG] _set_task: task_id={task_id}, task_title={task_title}")

        self.comboTask.blockSignals(True)

        found = False

        # Сначала ищем по ID
        if task_id:
            for i in range(self.comboTask.count()):
                if self.comboTask.itemData(i) == task_id:
                    self.comboTask.setCurrentIndex(i)
                    self.current_task_id = task_id
                    print(f"[DEBUG] Задача найдена по ID: {task_id} (индекс {i})")
                    found = True
                    break

        # Если не найдена по ID, ищем по названию
        if not found and task_title:
            for i in range(self.comboTask.count()):
                if self.comboTask.itemText(i) == task_title:
                    self.comboTask.setCurrentIndex(i)
                    self.current_task_id = self.comboTask.itemData(i)
                    print(f"[DEBUG] Задача найдена по названию: {task_title} (индекс {i})")
                    found = True
                    break

        # Если не найдена - добавляем вручную
        if not found and task_title:
            print(f"[DEBUG] Задача '{task_title}' не найдена, добавляем вручную")
            self.comboTask.addItem(task_title, task_id)
            self.comboTask.setCurrentIndex(self.comboTask.count() - 1)
            self.current_task_id = task_id

        self.comboTask.blockSignals(False)

    def _load_tasks_internal(self, project_id: int):
        """Внутренний метод загрузки задач"""
        self.comboTask.clear()
        self.comboTask.addItem("Выберите задачу", None)

        if self.service:
            tasks = self.service.get_tasks_for_project(project_id)
            for task in tasks:
                self.comboTask.addItem(task['title'], task['id'])

        self.comboTask.addItem("Без задачи", -1)
        self.comboTask.setEnabled(True)

    def _on_project_changed(self, index):
        """Обработчик смены проекта"""
        project_id = self.comboProject.currentData()
        if project_id is None or project_id == -1:
            self.comboTask.setEnabled(False)
            self.comboTask.clear()
            self.comboTask.addItem("Нет задач", None)
            return

        self.comboTask.blockSignals(True)
        self._load_tasks_internal(project_id)
        self.comboTask.blockSignals(False)
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
            'id': self.overtime_id,
            'employee_id': employee_id,
            'date': self.dateEdit.date(),
            'start_time': self.timeStart.time(),
            'end_time': self.timeEnd.time(),
            'description': self.textDescription.toPlainText(),
            'project_id': project_id,
            'task_id': task_id
        }

    def _save_overtime(self):
        if not self.service:
            QMessageBox.warning(self, "Ошибка", "Сервис не инициализирован")
            return

        data = self.get_overtime_data()

        success = self.service.update_overtime(
            overtime_id=data['id'],
            date=data['date'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            description=data['description'],
            employee_id=data['employee_id'],
            project_id=data['project_id'],
            task_id=data['task_id']
        )

        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить изменения")