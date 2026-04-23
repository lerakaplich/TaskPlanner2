# database.py

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ==========================================================
# Параметры подключения к taskplanner
# ==========================================================

DB_TASKS = {
    "user": "postgres",
    "password": "admin",
    "database": "taskplanner",
    "host": "192.168.84.150",
    "port": 5432,
    "options": "-c search_path=foreign_data,public"
}

# ==========================================================
# Параметры подключения к employees (прямое подключение)
# ==========================================================

DB_EMPLOYEES = {
    "user": "postgres",
    "password": "admin",
    "database": "employees",
    "host": "192.168.84.150",  # тот же хост, но другая БД
    "port": 5432,
}


def build_db_url(config: dict) -> str:
    base_url = f"postgresql+psycopg2://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    if "options" in config:
        import urllib.parse
        encoded_options = urllib.parse.quote_plus(config['options'])
        base_url += f"?options={encoded_options}"
    return base_url


# ==========================================================
# Engine для taskplanner
# ==========================================================

tasks_engine = create_engine(
    build_db_url(DB_TASKS),
    echo=False,
    pool_pre_ping=True
)

# ==========================================================
# Engine для employees (прямое подключение)
# ==========================================================

employees_engine = create_engine(
    build_db_url(DB_EMPLOYEES),
    echo=False,
    pool_pre_ping=True
)

# ==========================================================
# Session для taskplanner
# ==========================================================

TasksSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=tasks_engine
)

# ==========================================================
# Session для employees (прямое подключение)
# ==========================================================

EmployeesSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=employees_engine
)


# ==========================================================
# Helpers
# ==========================================================

def get_tasks_session():
    """Получить сессию БД задач (taskplanner)"""
    return TasksSessionLocal()


def get_employees_session():
    """Получить сессию БД сотрудников (employees) для записи"""
    return EmployeesSessionLocal()


# ==========================================================
# Проверка соединения
# ==========================================================

def test_connections():
    """Проверка соединения с БД"""
    try:
        with tasks_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✔ Database connection established (taskplanner)")
    except Exception as e:
        print("❌ Database connection error (taskplanner):")
        print(e)
        raise

    try:
        with employees_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✔ Database connection established (employees)")
    except Exception as e:
        print("❌ Database connection error (employees):")
        print(e)
        raise