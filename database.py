# database.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import urllib.parse
import time
import traceback

# ==========================================================
# Параметры подключения к taskplanner
# ==========================================================

DB_TASKS = {
    "user": "postgres",
    "password": "admin",
    "database": "taskplanner",
    "host": "192.168.43.32",
    "port": 5432,
}

# ==========================================================
# Параметры подключения к employees
# ==========================================================

DB_EMPLOYEES = {
    "user": "postgres",
    "password": "admin",
    "database": "employees",
    "host": "192.168.43.32",
    "port": 5432,
}


def build_db_url(config: dict) -> str:
    """Создает URL подключения к PostgreSQL"""
    return f"postgresql+psycopg2://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"


def test_connection_direct(config: dict, name: str) -> bool:
    """Проверяет подключение напрямую через psycopg2 с детальной диагностикой"""
    try:
        import psycopg2
        import socket

        print(f"\n🔍 Проверка подключения к {name}...")
        print(f"   Хост: {config['host']}:{config['port']}")
        print(f"   База: {config['database']}")
        print(f"   Пользователь: {config['user']}")

        # Сначала проверяем, доступен ли хост и порт
        print(f"\n📡 Проверка сетевой доступности {config['host']}:{config['port']}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((config['host'], config['port']))
        sock.close()

        if result != 0:
            print(f"❌ Хост {config['host']}:{config['port']} НЕ ДОСТУПЕН (ошибка: {result})")
            print(f"\nВозможные причины:")
            print(f"   • PostgreSQL не запущен на сервере")
            print(f"   • Брандмауэр блокирует порт 5432")
            print(f"   • Неправильный IP адрес")
            return False
        else:
            print(f"✅ Хост {config['host']}:{config['port']} доступен")

        # Пытаемся подключиться к PostgreSQL
        print(f"\n🔐 Попытка подключения к PostgreSQL...")
        conn = psycopg2.connect(
            user=config['user'],
            password=config['password'],
            database=config['database'],
            host=config['host'],
            port=config['port'],
            connect_timeout=5
        )
        conn.close()
        print(f"✅ Подключение к {name} успешно!")
        return True

    except psycopg2.OperationalError as e:
        error_msg = str(e)
        print(f"❌ Ошибка подключения к {name}:")
        print(f"   {error_msg}")

        # Анализируем ошибку
        if "Connection refused" in error_msg:
            print(f"\n🔍 Диагностика: Соединение отвергнуто")
            print(f"   • PostgreSQL не запущен на {config['host']}:{config['port']}")
            print(f"   • Или PostgreSQL слушает только localhost")
        elif "password authentication failed" in error_msg:
            print(f"\n🔍 Диагностика: Неверный пароль")
            print(f"   • Проверьте пароль для пользователя {config['user']}")
        elif "database" in error_msg and "does not exist" in error_msg:
            print(f"\n🔍 Диагностика: База данных не существует")
            print(f"   • База '{config['database']}' не найдена")
        elif "timeout" in error_msg.lower():
            print(f"\n🔍 Диагностика: Таймаут подключения")
            print(f"   • Проверьте сетевые настройки")
            print(f"   • Возможно, брандмауэр блокирует порт")
        else:
            print(f"\n🔍 Неизвестная ошибка: {error_msg}")

        return False
    except Exception as e:
        print(f"❌ Неизвестная ошибка при подключении к {name}: {e}")
        print(traceback.format_exc())
        return False


# ==========================================================
# Проверка подключений перед созданием engine
# ==========================================================

print("\n" + "=" * 60)
print("ПРОВЕРКА ПОДКЛЮЧЕНИЙ К БАЗАМ ДАННЫХ")
print("=" * 60)

# Проверяем taskplanner
taskplanner_ok = test_connection_direct(DB_TASKS, "taskplanner")

# Проверяем employees
employees_ok = test_connection_direct(DB_EMPLOYEES, "employees")

if not taskplanner_ok:
    print("\n⚠️ ВНИМАНИЕ: Нет подключения к taskplanner!")
    print("   Чаты и сообщения не будут работать.")

if not employees_ok:
    print("\n⚠️ ВНИМАНИЕ: Нет подключения к employees!")
    print("   Сотрудники, отделы и подразделения не будут доступны.")

print("=" * 60 + "\n")

# ==========================================================
# Создаем engine (даже если подключение не удалось)
# ==========================================================

# Engine для taskplanner
if taskplanner_ok:
    tasks_engine = create_engine(
        build_db_url(DB_TASKS),
        echo=False,
        pool_pre_ping=True,
        pool_recycle=3600
    )
else:
    tasks_engine = None
    print("⚠️ Engine для taskplanner не создан из-за ошибки подключения")

# Engine для employees
if employees_ok:
    employees_engine = create_engine(
        build_db_url(DB_EMPLOYEES),
        echo=False,
        pool_pre_ping=True,
        pool_recycle=3600
    )
else:
    employees_engine = None
    print("⚠️ Engine для employees не создан из-за ошибки подключения")

# ==========================================================
# Session makers
# ==========================================================

TasksSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=tasks_engine
) if tasks_engine else None

EmployeesSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=employees_engine
) if employees_engine else None


# ==========================================================
# Helpers with error handling
# ==========================================================

def get_tasks_session():
    """Получить сессию БД задач (taskplanner)"""
    if TasksSessionLocal is None:
        print("❌ Нет подключения к базе taskplanner")
        return None
    return TasksSessionLocal()


def get_employees_session():
    """Получить сессию БД сотрудников (employees)"""
    if EmployeesSessionLocal is None:
        print("❌ Нет подключения к базе employees")
        return None
    return EmployeesSessionLocal()


def test_connections():
    """Проверка соединения с БД (используя созданные engine)"""
    results = {}

    if tasks_engine:
        try:
            with tasks_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            results['taskplanner'] = "✅ OK"
            print("✔ Database connection established (taskplanner)")
        except Exception as e:
            results['taskplanner'] = f"❌ {e}"
            print(f"❌ Database connection error (taskplanner): {e}")
    else:
        results['taskplanner'] = "❌ Engine not created"
        print("❌ Database connection error (taskplanner): Engine not created")

    if employees_engine:
        try:
            with employees_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            results['employees'] = "✅ OK"
            print("✔ Database connection established (employees)")
        except Exception as e:
            results['employees'] = f"❌ {e}"
            print(f"❌ Database connection error (employees): {e}")
    else:
        results['employees'] = "❌ Engine not created"
        print("❌ Database connection error (employees): Engine not created")

    return results