# main.py
import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QTimer

from windows.login.login_window import LoginWindow
from windows.projects.main_window import MainWindow
from database import test_connections, get_tasks_session
from utils.error_handler import setup_exception_hook
from utils.socket_manager import get_socket_client
from services.auth_service import AuthService


def main():
    """Главная функция приложения"""
    setup_exception_hook()

    # Проверка БД
    test_connections()

    app = QApplication(sys.argv)

    app.setStyleSheet("""
            QToolTip {
                background-color: white;
            }
        """)

    # Запускаем подключение к сокет-серверу
    socket_client = get_socket_client()
    socket_client.connect_to_server("http://localhost:8081")

    # Проверяем наличие сохранённой сессии ПЕРЕД созданием окна входа
    auth_service = AuthService()
    saved_user = auth_service.load_session()

    # Глобальная переменная для хранения главного окна
    main_window = None

    if saved_user and saved_user.get('id'):
        # === АВТОЛОГИН: сразу открываем главное окно ===
        print(f"\n✅ Автологин: {saved_user.get('last_name', '')} {saved_user.get('first_name', '')}")
        print(f"   ID пользователя: {saved_user.get('id')}")

        # Устанавливаем текущего пользователя
        auth_service.set_current_user(saved_user)

        user_id = saved_user.get('id')

        # Получаем сессию БД
        session = get_tasks_session()

        # Аутентификация на сокет-сервере
        socket_client.authenticate(user_id)

        # Создаем и показываем главное окно
        main_window = MainWindow(
            session=session,
            user_id=user_id,
            socket_client=socket_client
        )
        main_window.show()

    else:
        # === НЕТ СОХРАНЁННОЙ СЕССИИ: показываем окно входа ===
        login_window = LoginWindow()

        # Функция для обработки успешного входа
        def on_login_success(user_data):
            nonlocal main_window
            print(f"✅ Сигнал login_success получен для {user_data.get('phone_number')}")

            user_id = user_data.get('id')

            # Получаем сессию БД
            session = get_tasks_session()

            # Аутентификация на сокет-сервере
            socket_client.authenticate(user_id)

            # Создаем главное окно
            main_window = MainWindow(
                session=session,
                user_id=user_id,
                socket_client=socket_client
            )
            main_window.show()

        # Подключаем сигнал
        login_window.login_success.connect(on_login_success)

        # Показываем окно входа (не блокируя)
        login_window.show()

        # Ждём закрытия окна входа
        def on_login_window_closed():
            if main_window is None:
                print("❌ Вход отменен")
                app.quit()

        login_window.finished.connect(on_login_window_closed)

    # Запускаем событийный цикл
    sys.exit(app.exec())


if __name__ == "__main__":
    main()