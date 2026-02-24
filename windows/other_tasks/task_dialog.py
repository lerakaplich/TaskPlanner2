import os
import sys
import traceback
from datetime import datetime
from typing import Dict, Optional

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QApplication, QMessageBox
from PyQt6.QtCore import Qt, QDate, pyqtSignal


# ГЛОБАЛЬНЫЙ ЛОВЕЦ ОШИБОК
def global_excepthook(exc_type, exc_value, exc_tb):
    print("\n" + "="*90)
    print("=== КРИТИЧЕСКАЯ ОШИБКА В ПРИЛОЖЕНИИ ===")
    traceback.print_exception(exc_type, exc_value, exc_tb)
    print("="*90)
    QMessageBox.critical(None, "Краш приложения",
                         f"Произошла ошибка:\n{exc_value}\n\nСмотри консоль!")

sys.excepthook = global_excepthook


class TaskDialog(QDialog):
    task_saved = pyqtSignal(dict)

    def __init__(self,
                 parent=None,
                 task_data=None,
                 current_user=None,
                 mode: str = "create"):   # ← ВОТ ЭТО ДОБАВИЛИ
        super().__init__(parent)
        print(f"=== TaskDialog: __init__ START (mode={mode}) ===")

        self.task_data = task_data
        self.mode = mode
        self.current_user = current_user or self.get_test_user()
        print(f"  current_user = {self.current_user}")

        # Загрузка UI
        try:
            ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "other_tasks")
            ui_file = os.path.join(ui_path, "task_dialog.ui")
            print(f"  Загружаю UI: {ui_file}")
            uic.loadUi(ui_file, self)
            print("  ✓ UI загружен успешно")
        except Exception as e:
            print("  ❌ ОШИБКА загрузки UI:", e)
            traceback.print_exc()
            raise

        # Настройка заголовка и кнопки в зависимости от режима
        if self.mode == "edit" or self.task_data is not None:
            self.titleLabel.setText("Редактирование задачи")
            self.createBtn.setText("Сохранить изменения")
        else:
            self.titleLabel.setText("Создание новой задачи")
            self.createBtn.setText("Создать задачу")

        self.createBtn.clicked.connect(self.validate_and_save)
        print("  ✓ Кнопка подключена")

        # Загрузка данных
        self.load_test_projects()
        self.load_test_employees()
        self.update_creation_info()

        if self.task_data:
            self.load_task_data()

        print("=== TaskDialog: __init__ END ===\n")

    # ==================== ОСТАЛЬНЫЕ МЕТОДЫ (без изменений) ====================
    def get_test_user(self):
        return {
            'id': 1,
            'last_name': 'Иванов',
            'first_name': 'Иван',
            'middle_name': 'Иванович',
            'position': 'Генеральный директор'
        }

    def load_test_projects(self):
        self.test_projects = [
            {'id': 1, 'name': 'Task Planner', 'description': 'Планировщик задач'},
            {'id': 2, 'name': 'CRM System', 'description': 'Система управления клиентами'},
            {'id': 3, 'name': 'Mobile App', 'description': 'Разработка мобильного приложения'},
            {'id': 4, 'name': 'Website Redesign', 'description': 'Редизайн корпоративного сайта'},
            {'id': 5, 'name': 'Analytics Dashboard', 'description': 'Дашборд аналитики'}
        ]
        self.comboBoxProject.clear()
        self.comboBoxProject.addItem("Выберите проект", None)
        for project in self.test_projects:
            self.comboBoxProject.addItem(project['name'], project['id'])

    def load_test_employees(self):
        self.test_employees = [
            {'id': 1, 'last_name': 'Иванов', 'first_name': 'Иван', 'middle_name': 'Иванович', 'position': 'Генеральный директор'},
            {'id': 2, 'last_name': 'Петрова', 'first_name': 'Анна', 'middle_name': 'Сергеевна', 'position': 'Ведущий разработчик'},
            {'id': 3, 'last_name': 'Сидоров', 'first_name': 'Петр', 'middle_name': 'Петрович', 'position': 'Технический директор'},
            {'id': 4, 'last_name': 'Козлова', 'first_name': 'Елена', 'middle_name': 'Владимировна', 'position': 'Тестировщик'},
            {'id': 5, 'last_name': 'Морозов', 'first_name': 'Дмитрий', 'middle_name': 'Алексеевич', 'position': 'Аналитик'},
            {'id': 6, 'last_name': 'Волкова', 'first_name': 'Мария', 'middle_name': 'Дмитриевна', 'position': 'Дизайнер'},
            {'id': 7, 'last_name': 'Соколов', 'first_name': 'Александр', 'middle_name': 'Игоревич', 'position': 'Менеджер проектов'}
        ]
        self.comboBoxAssignee.clear()
        self.comboBoxAssignee.addItem("Не назначен", None)
        for emp in self.test_employees:
            full_name = f"{emp['last_name']} {emp['first_name']} {emp['middle_name']}"
            display_text = f"{full_name} — {emp['position']}"
            self.comboBoxAssignee.addItem(display_text, emp['id'])

    def _safe_name(self, person: dict) -> str:
        if not person:
            return "Неизвестно"
        last = person.get('last_name', '') or ''
        first = (person.get('first_name') or '')[:1]
        middle = (person.get('middle_name') or '')[:1]
        f = first + '.' if first else ''
        m = middle + '.' if middle else ''
        return f"{last} {f}{m}".strip()

    def update_creation_info(self):
        now = datetime.now()
        self.createdByLabel.setText(f"Создал: {self._safe_name(self.current_user)}")

        def fmt(dt):
            if isinstance(dt, datetime):
                return dt.strftime('%d.%m.%Y %H:%M')
            return str(dt)

        created = self.task_data.get('created_at', now) if self.task_data else now
        updated = self.task_data.get('updated_at', now) if self.task_data else now
        self.createdAtLabel.setText(f"Создано: {fmt(created)}")
        self.updatedAtLabel.setText(f"Изменено: {fmt(updated)}")

    def load_task_data(self):
        if not self.task_data:
            return
        self.lineEditTitle.setText(self.task_data.get('title', ''))
        self.textEditDescription.setPlainText(self.task_data.get('description', ''))

        project_id = self.task_data.get('project_id')
        if project_id is not None:
            index = self.comboBoxProject.findData(project_id)
            if index >= 0:
                self.comboBoxProject.setCurrentIndex(index)

        assignee_id = self.task_data.get('assigned_to')
        if assignee_id is not None:
            index = self.comboBoxAssignee.findData(assignee_id)
            if index >= 0:
                self.comboBoxAssignee.setCurrentIndex(index)

        priority = self.task_data.get('priority', 'medium')
        priority_map = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        self.comboBoxPriority.setCurrentIndex(priority_map.get(priority, 1))

        status = self.task_data.get('status', 'to_do')
        status_map = {'to_do': 0, 'in_progress': 1, 'review': 2, 'done': 3}
        self.comboBoxStatus.setCurrentIndex(status_map.get(status, 0))

        if self.task_data.get('due_date'):
            try:
                due_date = QDate.fromString(self.task_data['due_date'], "yyyy-MM-dd")
                self.dateEditDeadline.setDate(due_date)
            except:
                pass

    def get_task_data(self) -> Dict:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        task_data = {
            'id': self.task_data.get('id') if self.task_data else None,
            'title': self.lineEditTitle.text().strip(),
            'description': self.textEditDescription.toPlainText().strip(),
            'project_id': self.comboBoxProject.currentData(),
            'project_name': self.comboBoxProject.currentText(),
            'assigned_to': self.comboBoxAssignee.currentData(),
            'priority': {'Низкий': 'low', 'Средний': 'medium', 'Высокий': 'high', 'Критический': 'critical'}
                        .get(self.comboBoxPriority.currentText(), 'medium'),
            'status': {'К выполнению': 'to_do', 'В работе': 'in_progress', 'На проверке': 'review', 'Выполнено': 'done'}
                      .get(self.comboBoxStatus.currentText(), 'to_do'),
            'due_date': self.dateEditDeadline.date().toString("yyyy-MM-dd"),
            'created_by': self.current_user.get('id'),
            'created_by_name': self._safe_name(self.current_user),
            'created_at': now_str,
            'updated_at': now_str,
            'assignee_name': 'Не назначен'
        }

        assignee_id = task_data['assigned_to']
        if assignee_id:
            for emp in self.test_employees:
                if emp['id'] == assignee_id:
                    task_data['assignee_name'] = self._safe_name(emp)
                    break

        return task_data

    def validate_and_save(self):
        print("=== validate_and_save() START ===")
        try:
            title = self.lineEditTitle.text().strip()
            if not title:
                QMessageBox.warning(self, "Предупреждение", "Введите название задачи")
                return

            if self.comboBoxProject.currentData() is None:
                QMessageBox.warning(self, "Предупреждение", "Выберите проект")
                return

            task_data = self.get_task_data()
            print("  → ЭМИТ сигнала task_saved")
            self.task_saved.emit(task_data)
            self.accept()

        except Exception as e:
            print("  ❌ ИСКЛЮЧЕНИЕ:")
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n{str(e)}\n\nСмотри консоль!")


# ====================== ТЕСТ ======================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    dialog = TaskDialog(mode="create")   # теперь работает и так
    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = dialog.get_task_data()
        print("\n" + "="*70)
        print("ЗАДАЧА УСПЕШНО СОХРАНЕНА:")
        print("="*70)
        for k, v in sorted(data.items()):
            print(f"{k:18} : {v}")
        print("="*70)
    sys.exit(app.exec())