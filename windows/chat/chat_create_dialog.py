from PyQt6.QtWidgets import QListWidgetItem
from PyQt6.QtCore import Qt
from windows.chat.chat_create_view import ChatCreateView


class ChatCreateDialog(ChatCreateView):
    def __init__(self, emp_repo, current_user_id, parent=None):
        super().__init__(parent)
        self.emp_repo = emp_repo  # Теперь это EmployeeRepo
        self.current_user_id = current_user_id

        # Подключаем события
        self.type_combo.currentIndexChanged.connect(self.toggle_type)
        self.search_input.textChanged.connect(self.filter_users)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_create.clicked.connect(self.validate_and_accept)

        self.load_users()

    def toggle_type(self, index):
        is_private = index == 1  # 1 - Личная переписка
        self.title_input.setVisible(not is_private)
        self.title_label.setVisible(not is_private)

        # Сбрасываем выделение при смене типа, чтобы не было путаницы
        for i in range(self.user_list.count()):
            self.user_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def load_users(self):
        """Загрузка списка сотрудников для выбора"""
        try:
            self.user_list.clear()

            # Используем метод get_all() из EmployeeRepo
            users = self.emp_repo.get_all()

            if not users:
                print("⚠️ Список сотрудников пуст")
                return

            for u in users:
                # Пропускаем себя
                if u.id == self.current_user_id:
                    continue

                # Формируем текст для списка
                display_text = f"{u.last_name} {u.first_name}"
                if u.middle_name:
                    display_text += f" {u.middle_name}"
                if u.position:
                    display_text += f" ({u.position})"

                item = QListWidgetItem(display_text)
                # Сохраняем ID сотрудника
                item.setData(Qt.ItemDataRole.UserRole, u.id)
                # Добавляем чекбокс
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)

                self.user_list.addItem(item)

            print(f"✅ В диалог загружено {self.user_list.count()} сотрудников")

        except Exception as e:
            print(f"❌ Критическая ошибка при загрузке пользователей в диалог: {e}")

    def filter_users(self, text):
        for i in range(self.user_list.count()):
            item = self.user_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def get_data(self):
        selected_ids = []
        for i in range(self.user_list.count()):
            item = self.user_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_ids.append(item.data(Qt.ItemDataRole.UserRole))

        chat_type = "group" if self.type_combo.currentIndex() == 0 else "private"

        return {
            "type": chat_type,
            "title": self.title_input.text() if chat_type == "group" else None,
            "participants": selected_ids
        }

    def validate_and_accept(self):
        data = self.get_data()
        if data["type"] == "group" and not data["title"]:
            return  # Можно добавить QMessageBox
        if not data["participants"]:
            return
        self.accept()