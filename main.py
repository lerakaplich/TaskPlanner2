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
    socket_client.connect_to_server("http://localhost:8081")

    # Показываем окно авторизации
    login_window = LoginWindow()

    if login_window.exec() == LoginWindow.DialogCode.Accepted:
        # Здесь нужно получить данные авторизованного пользователя
        # Пока используем тестового пользователя (ID=2)
        # В будущем нужно будет получать реального пользователя из LoginWindow
        user_id = 2  # ВРЕМЕННО! Нужно будет заменить на реального пользователя

        # Получаем данные пользователя из БД
        session = get_tasks_session()
        from models.employees import ExternalEmployee
        from sqlalchemy import select

        stmt = select(ExternalEmployee).where(ExternalEmployee.id == user_id)
        user = session.scalar(stmt)

        if user:
            # Аутентификация на сокет-сервере
            socket_client.authenticate(user_id)

            print(f"\n✅ Вход выполнен: {user.last_name} {user.first_name}")
            print(f"   Роль: {user.rights or 'user'}")
            if user.position:
                print(f"   Должность: {user.position}")

            # Создаем главное окно
            window = MainWindow(
                session=session,
                user_id=user_id,
                socket_client=socket_client
            )
            window.show()

            sys.exit(app.exec())
        else:
            QMessageBox.critical(None, "Ошибка", "Пользователь не найден в базе данных")
            sys.exit(1)
    else:
        print("❌ Вход отменен")
        sys.exit(0)


if __name__ == "__main__":
    main()