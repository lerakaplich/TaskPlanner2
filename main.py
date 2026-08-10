# main.py
import atexit
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from server_app.services.training_scheduler import get_training_scheduler
from server_app.services.tasks_service.task_data_collector import get_task_data_collector

from windows.login.login_window import LoginWindow
from windows.projects.main_window import MainWindow
from server_app.database import get_tasks_session
from utils.error_handler import setup_exception_hook
from utils.socket_manager import get_socket_client
from services.auth_service import AuthService


def create_main_window(user_id: int, socket_client):
    """Создает и возвращает главное окно"""
    session = get_tasks_session()
    socket_client.authenticate(user_id)
    return MainWindow(session=session, user_id=user_id, socket_client=socket_client)


def setup_training_system():
    """
    Настраивает систему машинного обучения.
    Теперь обучение происходит на сервере, клиент только инициализирует.
    """
    print("\n🧠 Настройка системы прогнозирования...")

    try:
        # Получаем планировщик (на сервере)
        scheduler = get_training_scheduler()
        scheduler.start()
        print("   ✅ Планировщик дообучения запущен")

        # Проверяем текущее состояние модели на сервере
        def check_model_status():
            try:
                collector = get_task_data_collector()
                stats = collector.get_training_stats()

                print(f"   📊 Статистика данных:")
                print(f"      - Всего записей: {stats.get('total_records', 0)}")
                print(f"      - Завершённых задач: {stats.get('completed_tasks', 0)}")
                print(f"      - Минимум для обучения: {stats.get('min_samples', 10)}")
                print(f"      - Можно обучать: {stats.get('can_train', False)}")

                if stats.get('can_train', False):
                    print(f"   🧠 Достаточно данных, запускаем обучение...")
                    collector.force_train()
                else:
                    print(f"   ⏳ Ждём ещё данных: {stats.get('completed_tasks', 0)}/{stats.get('min_samples', 10)}")

            except Exception as e:
                print(f"   ⚠️ Ошибка проверки модели: {e}")

        # Запускаем через 3 секунды после старта приложения
        QTimer.singleShot(3000, check_model_status)

        return scheduler

    except Exception as e:
        print(f"   ❌ Ошибка настройки системы обучения: {e}")
        import traceback
        traceback.print_exc()
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
        app.scheduler = scheduler  # Сохраняем для завершения
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

    def on_exit():
        """Обработчик завершения приложения"""
        print("\n🔄 Завершение работы приложения...")

        # Сохраняем собранные данные (если есть локальный кэш)
        try:
            collector = get_task_data_collector()
            collector.flush_cache()
            print("📊 Данные для обучения сохранены")
        except Exception as e:
            print(f"⚠️ Ошибка сохранения данных: {e}")

        # Останавливаем планировщик обучения (на сервере)
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