# windows/chat/employee_selection_dialog.py
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton


class EmployeeSelectionDialog(QDialog):
    def __init__(self, exclude_ids, emp_repo, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выберите сотрудников")
        self.setMinimumSize(300, 400)
        self.emp_repo = emp_repo
        self.exclude_ids = exclude_ids
        self.selected_ids = []

        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        # Загружаем всех сотрудников
        all_emps = self.emp_repo.get_all()  # Метод вашего репозитория сотрудников
        for emp in all_emps:
            if emp.id not in exclude_ids:
                item = QListWidgetItem(f"{emp.last_name} {emp.first_name}")
                item.setData(Qt.ItemDataRole.UserRole, emp.id)
                self.list_widget.addItem(item)

        layout.addWidget(self.list_widget)

        btn = QPushButton("Добавить выбранных")
        btn.clicked.connect(self.handle_accept)
        layout.addWidget(btn)

    def handle_accept(self):
        for item in self.list_widget.selectedItems():
            self.selected_ids.append(item.data(Qt.ItemDataRole.UserRole))
        self.accept()

    def get_selected_employees(self):
        return self.selected_ids