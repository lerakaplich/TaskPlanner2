# main.py
import atexit
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from services.tasks_service.task_data_collector import get_task_data_collector
from services.training_scheduler import get_training_scheduler
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


# main.py

def setup_training_system():
    """Настраивает систему машинного обучения"""
    print("\n🧠 Настройка системы прогнозирования...")

    try:
        scheduler = get_training_scheduler()
        scheduler.start()
        print("   ✅ Планировщик дообучения запущен")

        def initial_training():
            try:
                from ml.task_time_predictor import get_task_predictor
                from services.tasks_service.task_data_collector import get_task_data_collector

                collector = get_task_data_collector()
                all_data = collector.get_training_data()

                # Проверяем, есть ли завершённые задачи
                completed = [d for d in all_data if d.get('completed', False) and d.get('effective_hours', 0) > 0]

                if len(completed) >= 10:
                    print(f"   📊 Найдено {len(completed)} завершённых задач, обучаем модель...")
                    predictor = get_task_predictor()
                    result = predictor.train(all_data)
                    print(f"   📊 Результат: {result}")
                else:
                    print(f"   ⏳ Недостаточно завершённых задач: {len(completed)}/10")

            except Exception as e:
                print(f"   ⚠️ Ошибка первоначального обучения: {e}")

        QTimer.singleShot(5000, initial_training)
        return scheduler

    except Exception as e:
        print(f"   ❌ Ошибка настройки системы обучения: {e}")
        return None


def shutdown_training_system(scheduler):
    """Корректно завершает работу системы обучения"""
    if scheduler:
        try:
            scheduler.stop()
            print("🧠 Планировщик обучения остановлен")
        except Exception as e:
            print(f"⚠️ Ошибка остановки планировщика: {e}")


def main():
    """Главная функция приложения"""
    setup_exception_hook()

    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QToolTip {
            background-color: white;
        }
    """)

    # ============================================================
    # 1. ПОДКЛЮЧЕНИЕ К СОКЕТ-СЕРВЕРУ
    # ============================================================
    socket_client = get_socket_client()
    socket_client.connect_to_server("http://localhost:8081")

    # ============================================================
    # 2. АВТОРИЗАЦИЯ
    # ============================================================
    auth_service = AuthService()
    saved_user = auth_service.load_session()

    if saved_user and saved_user.get('id'):
        print(f"\n✅ Автологин: {saved_user.get('last_name', '')} {saved_user.get('first_name', '')}")
        print(f"   ID пользователя: {saved_user.get('id')}")

        auth_service.set_current_user(saved_user)

        # Создаём главное окно
        main_window = create_main_window(saved_user['id'], socket_client)
        main_window.show()

        # Настраиваем систему обучения ПОСЛЕ создания окна
        scheduler = setup_training_system()
    else:
        login_window = LoginWindow()

        def on_login_success(user_data):
            print(f"✅ Вход выполнен для {user_data.get('phone_number')}")
            main_window = create_main_window(user_data['id'], socket_client)
            main_window.show()
            login_window.close()

            # Настраиваем систему обучения ПОСЛЕ входа
            scheduler = setup_training_system()
            # Сохраняем scheduler в глобальной переменной для корректного завершения
            app.scheduler = scheduler

        login_window.login_success.connect(on_login_success)
        login_window.show()

        # Инициализируем scheduler как None для случая без входа
        app.scheduler = None

    # ============================================================
    # 3. РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ЗАВЕРШЕНИЯ
    # ============================================================

    def on_exit():
        """Обработчик завершения приложения"""
        print("\n🔄 Завершение работы приложения...")

        # Сохраняем собранные данные
        try:
            collector = get_task_data_collector()
            collector.flush_cache()
            print("📊 Данные для обучения сохранены")
        except Exception as e:
            print(f"⚠️ Ошибка сохранения данных: {e}")

        # Останавливаем планировщик обучения
        try:
            if hasattr(app, 'scheduler') and app.scheduler:
                shutdown_training_system(app.scheduler)
        except Exception as e:
            print(f"⚠️ Ошибка остановки планировщика: {e}")

    atexit.register(on_exit)

    # Также обрабатываем сигнал приложения о завершении
    app.aboutToQuit.connect(lambda: on_exit())

    # ============================================================
    # 4. ЗАПУСК ПРИЛОЖЕНИЯ
    # ============================================================
    sys.exit(app.exec())


if __name__ == "__main__":
    main()