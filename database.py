"""
Глобальная настройка SQLAlchemy.

Архитектура вызовов:

UI (Windows)
    ↓
Service
    ↓
Repository
    ↓
Database
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# ==========================================================
# Параметры подключения
# ==========================================================

DB_TASKS = {
    "user": "postgres",
    "password": "admin",
    "database": "taskplanner",
    "host": "localhost",
    "port": 5433,
}

DB_EMPLOYEES = {
    "user": "postgres",
    "password": "admin",
    "database": "employees",
    "host": "localhost",
    "port": 5433,
}


# ==========================================================
# Функция формирования URL
# ==========================================================

def build_db_url(config: dict) -> str:
    return (
        f"postgresql+psycopg2://{config['user']}:{config['password']}"
        f"@{config['host']}:{config['port']}/{config['database']}"
    )


# ==========================================================
# Engines
# ==========================================================

employees_engine = create_engine(
    build_db_url(DB_EMPLOYEES),
    echo=False,
    pool_pre_ping=True
)

tasks_engine = create_engine(
    build_db_url(DB_TASKS),
    echo=False,
    pool_pre_ping=True
)


# ==========================================================
# Sessions
# ==========================================================

EmployeesSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=employees_engine
)

TasksSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=tasks_engine
)


# ==========================================================
# Helpers
# ==========================================================

def get_employees_session():
    """Получить сессию БД сотрудников"""
    return EmployeesSessionLocal()


def get_tasks_session():
    """Получить сессию БД задач"""
    return TasksSessionLocal()


# ==========================================================
# Проверка соединения
# ==========================================================

def test_connections():
    """Проверка соединения с БД"""
    try:
        with employees_engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        with tasks_engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        print("✔ Database connections established")

    except Exception as e:
        print("❌ Database connection error:")
        print(e)
        raise