# main.py
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from windows.login.login_window import LoginWindow
from windows.projects.main_window import MainWindow
from database import get_tasks_session
from utils.error_handler import setup_exception_hook
from utils.socket_manager import get_socket_client
from services.auth_service import AuthService


def create_main_window(user_id: int, socket_client):
    """Создает и возвращает главное окно"""
    session = get_tasks_session()
    socket_client.authenticate(user_id)
    return MainWindow(session=session, user_id=user_id, socket_client=socket_client)


def main():
    """Главная функция приложения"""
    setup_exception_hook()

    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QToolTip {
            background-color: white;
        }
    """)

    socket_client = get_socket_client()
    socket_client.connect_to_server("http://localhost:8081")

    auth_service = AuthService()
    saved_user = auth_service.load_session()

    if saved_user and saved_user.get('id'):
        print(f"\n✅ Автологин: {saved_user.get('last_name', '')} {saved_user.get('first_name', '')}")
        print(f"   ID пользователя: {saved_user.get('id')}")

        auth_service.set_current_user(saved_user)
        main_window = create_main_window(saved_user['id'], socket_client)
        main_window.show()
    else:
        login_window = LoginWindow()

        def on_login_success(user_data):
            print(f"✅ Вход выполнен для {user_data.get('phone_number')}")
            main_window = create_main_window(user_data['id'], socket_client)
            main_window.show()
            login_window.close()

        login_window.login_success.connect(on_login_success)
        login_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()