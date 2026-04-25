import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from windows.login.login_window import LoginWindow
from windows.projects.main_window import MainWindow
from database import test_connections, get_tasks_session
from utils.error_handler import setup_exception_hook
from utils.socket_manager import get_socket_client


def main():
    """Главная функция приложения"""
    setup_exception_hook()

    # Проверка БД
    test_connections()

    app = QApplication(sys.argv)

    # Запускаем подключение к сокет-серверу
    socket_client = get_socket_client()
    socket_client.connect_to_server("http://localhost:8082")

    # Показываем окно авторизации
    login_window = LoginWindow()

    if login_window.exec() == LoginWindow.DialogCode.Accepted:
        # 👇 ПОЛУЧАЕМ РЕАЛЬНОГО ПОЛЬЗОВАТЕЛЯ ИЗ ОКНА ВХОДА
        authenticated_user = login_window.get_authenticated_user()

        if not authenticated_user:
            QMessageBox.critical(None, "Ошибка", "Не удалось получить данные пользователя")
            sys.exit(1)

        user_id = authenticated_user.get('id')  # 👈 Берем ID из результата входа
        user_name = f"{authenticated_user.get('last_name', '')} {authenticated_user.get('first_name', '')}"

        print(f"\n✅ Вход выполнен: {user_name}")
        print(f"   ID пользователя: {user_id}")
        print(f"   Роль: {authenticated_user.get('rights', 'user')}")
        if authenticated_user.get('position'):
            print(f"   Должность: {authenticated_user.get('position')}")

        # Получаем сессию БД
        session = get_tasks_session()

        # Аутентификация на сокет-сервере
        socket_client.authenticate(user_id)

        # Создаем главное окно с правильным user_id
        window = MainWindow(
            session=session,
            user_id=user_id,  # 👈 Передаем правильный ID
            socket_client=socket_client
        )
        window.show()

        sys.exit(app.exec())
    else:
        print("❌ Вход отменен")
        sys.exit(0)

if __name__ == "__main__":
    main()