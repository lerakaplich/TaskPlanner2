# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_TASKS = {
    "user": "postgres",
    "password": "admin",
    "database": "taskplanner",
    "host": "10.126.231.152",
    "port": 5432,
}

DB_EMPLOYEES = {
    "user": "postgres",
    "password": "admin",
    "database": "employees",
    "host": "10.126.231.152",
    "port": 5432,
}

def build_db_url(config: dict) -> str:
    """Создает URL подключения к PostgreSQL"""
    return f"postgresql+psycopg2://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

tasks_engine = create_engine(
    build_db_url(DB_TASKS),
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600
)

employees_engine = create_engine(
    build_db_url(DB_EMPLOYEES),
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600
)

TasksSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=tasks_engine)
EmployeesSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=employees_engine)

def get_tasks_session():
    """Получить сессию БД задач (taskplanner)"""
    return TasksSessionLocal()

def get_employees_session():
    """Получить сессию БД сотрудников (employees)"""
    return EmployeesSessionLocal()