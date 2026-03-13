import sys
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from sqlalchemy import select, text

from windows.projects.main_window import MainWindow
from database import test_connections, get_tasks_session  # 👈 ЗАМЕНЯЕМ get_employees_session на get_tasks_session
from models.employees import ExternalEmployee
from utils.error_handler import setup_exception_hook


class UserSelectDialog(QDialog):
    """Диалог выбора пользователя при входе"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.selected_user = None
        self.users = []

        self.setWindowTitle("Выбор пользователя")
        self.setFixedSize(500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F7;
            }
            QLabel {
                color: #1B232A;
                font-size: 14px;
            }
            QComboBox {
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                background-color: white;
                min-height: 20px;
            }
            QComboBox:hover {
                border: 2px solid #ccab6e;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #666;
                margin-right: 10px;
            }
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #998664;
            }
            QPushButton:pressed {
                background-color: #7a6a50;
            }
            QPushButton#btnCancel {
                background-color: #f0f0f0;
                color: #666;
            }
            QPushButton#btnCancel:hover {
                background-color: #e0e0e0;
            }
        """)

        self.init_ui()
        self.load_users()

    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Заголовок
        title_label = QLabel("Вход в систему")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(18)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #1B232A; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # Иконка пользователя
        icon_label = QLabel("👤")
        icon_font = QFont()
        icon_font.setPointSize(48)
        icon_label.setFont(icon_font)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("color: #ccab6e; margin: 10px;")
        layout.addWidget(icon_label)

        # Подзаголовок
        subtitle_label = QLabel("Выберите пользователя для входа")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #666; margin-bottom: 20px;")
        layout.addWidget(subtitle_label)

        # Выпадающий список пользователей
        self.user_combo = QComboBox()
        self.user_combo.setPlaceholderText("Выберите пользователя...")
        layout.addWidget(self.user_combo)

        # Информация о выбранном пользователе
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("color: #666; font-style: italic; margin: 10px;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton("Войти")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_ok.setEnabled(False)
        buttons_layout.addWidget(self.btn_ok)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

        # Подключаем сигнал изменения выбора
        self.user_combo.currentIndexChanged.connect(self.on_user_selected)

    def load_users(self):
        """Загружает список пользователей из foreign_data.employees"""
        try:
            # 👇 ИСПОЛЬЗУЕМ get_tasks_session() вместо get_employees_session()
            session = get_tasks_session()

            # ДИАГНОСТИКА: проверим текущего пользователя и его права
            current_user = session.execute(text("SELECT current_user")).scalar()
            print(f"Текущий пользователь БД: {current_user}")

            # Проверим, какие схемы доступны
            result = session.execute(text("SHOW search_path")).first()
            print(f"Текущий search_path: {result[0]}")

            # Проверим, видит ли сессия таблицу
            result = session.execute(text("SELECT COUNT(*) FROM foreign_data.employees")).scalar()
            print(f"Количество записей в foreign_data.employees: {result}")

            # Теперь сам запрос через ORM
            stmt = select(ExternalEmployee).order_by(ExternalEmployee.last_name)
            users = session.scalars(stmt).all()

            if users:
                self.users = [
                    {
                        "id": u.id,
                        "last_name": u.last_name,
                        "first_name": u.first_name,
                        "middle_name": u.middle_name,
                        "rights": u.rights or 'user',
                        "position": u.position,
                        "phone_number": u.phone_number,
                        "email": u.email
                    }
                    for u in users
                ]
                print(f"✅ Загружено {len(self.users)} пользователей из foreign_data")
            else:
                print("⚠️ Используются тестовые пользователи")

            session.close()

        except Exception as e:
            print(f"❌ Ошибка загрузки пользователей из foreign_data: {e}")

        # Заполняем комбобокс
        self.user_combo.clear()
        self.user_combo.addItem("-- Выберите пользователя --", None)

        for user in self.users:
            full_name = f"{user['last_name']} {user['first_name']}"
            if user['middle_name']:
                full_name += f" {user['middle_name']}"

            if user.get('position'):
                full_name += f" ({user['position']})"

            role_icon = "👑" if user.get('rights') == 'superadmin' else "👤"
            display_text = f"{role_icon} {full_name}"

            self.user_combo.addItem(display_text, user['id'])

    def on_user_selected(self, index):
        """Обработчик выбора пользователя"""
        if index > 0:
            user_id = self.user_combo.currentData()
            user = next((u for u in self.users if u['id'] == user_id), None)

            if user:
                full_name = f"{user['last_name']} {user['first_name']}"
                if user['middle_name']:
                    full_name += f" {user['middle_name']}"

                role_text = "Администратор" if user.get('rights') == 'superadmin' else "Пользователь"
                info_text = f"Выбран: {full_name}\nРоль: {role_text}"
                if user.get('position'):
                    info_text += f"\nДолжность: {user['position']}"

                self.info_label.setText(info_text)
                self.selected_user = user
                self.btn_ok.setEnabled(True)
        else:
            self.info_label.setText("")
            self.selected_user = None
            self.btn_ok.setEnabled(False)

    def get_selected_user(self):
        """Возвращает выбранного пользователя"""
        return self.selected_user


def main():
    """Главная функция приложения"""
    setup_exception_hook()

    # Проверка БД
    test_connections()

    app = QApplication(sys.argv)

    # Показываем диалог выбора пользователя
    user_dialog = UserSelectDialog()

    if user_dialog.exec() == QDialog.DialogCode.Accepted:
        selected_user = user_dialog.get_selected_user()

        if selected_user:
            print(f"\n✅ Вход выполнен: {selected_user['last_name']} {selected_user['first_name']}")
            print(f"   Роль: {selected_user.get('rights', 'user')}")
            if selected_user.get('position'):
                print(f"   Должность: {selected_user['position']}")

            # Создаем главное окно и передаем выбранного пользователя
            session = get_tasks_session()

            window = MainWindow(
                session=session,
                user_id=selected_user["id"]
            )
            window.show()

            sys.exit(app.exec())
        else:
            print("❌ Пользователь не выбран")
            QMessageBox.warning(None, "Ошибка", "Пользователь не выбран. Приложение будет закрыто.")
            sys.exit(1)
    else:
        print("❌ Вход отменен")
        sys.exit(0)


if __name__ == "__main__":
    main()