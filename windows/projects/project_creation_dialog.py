import os
import sys
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QApplication
from PyQt6.QtCore import QDate


class ProjectCreationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)


        ui_path = os.path.join(
            os.path.dirname(__file__),  # windows/analytics/employees/
            "..", "..",  # поднимаемся до корня проекта
            "ui", "projects"  # спускаемся в нужную подпапку ui
        )
        uic.loadUi(os.path.join(ui_path, "project_creation_dialog.ui"), self)



        # Устанавливаем текущую дату
        current_date = QDate.currentDate().toString("dd.MM.yyyy")
        self.dateLabel.setText(f"Создан: {current_date}")

        # Подключаем сигналы
        self.participantsBtn.clicked.connect(self.select_participants)
        self.adminsBtn.clicked.connect(self.select_admins)
        self.createBtn.clicked.connect(self.accept)

    def select_participants(self):
        """Открыть диалог выбора участников"""
        # Здесь можно открыть диалог с выбором участников
        print("Выбор участников проекта")

    def select_admins(self):
        """Открыть диалог выбора администраторов"""
        # Здесь можно открыть диалог с выбором администраторов
        print("Выбор администраторов проекта")

    def get_project_data(self):
        """Получить данные проекта"""
        return {
            'name': self.nameInput.text(),
            'description': self.descInput.toPlainText(),
            'is_active': self.activeCheckbox.isChecked(),
            'created_date': QDate.currentDate().toString("dd.MM.yyyy")
        }


# Для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    dialog = ProjectCreationDialog()

    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = dialog.get_project_data()
        print("Проект создан:", data)

    sys.exit(app.exec())