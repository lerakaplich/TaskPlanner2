# windows/projects/project_creation_dialog.py
from windows.projects.base_project_dialog import BaseProjectDialog


class ProjectCreationDialog(BaseProjectDialog):
    """Диалог создания проекта"""

    def __init__(self, parent=None, service=None, creator_id=None):
        super().__init__(parent, title="Создание проекта", service=service, creator_id=creator_id)

        self.setWindowTitle("Создание проекта")
        self.titleLabel.setText("Создание проекта")
        self.createBtn.setText("Создать проект")
        self.activeCheckbox.setChecked(True)

        self.createBtn.clicked.connect(self._on_create)

    def _on_create(self):
        """Обработчик создания проекта"""
        if self.validate_input():
            self.accept()

    def get_project_data(self):
        """Возвращает подготовленные данные для создания"""
        raw_data = super().get_project_data()
        return self.dialog_service.prepare_creation_data(raw_data)