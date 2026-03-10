# database.py

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
    "options": "-c search_path=foreign_data,public"  # поиск в foreign_data и public
}

def build_db_url(config: dict) -> str:
    base_url = f"postgresql+psycopg2://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    if "options" in config:
        import urllib.parse
        encoded_options = urllib.parse.quote_plus(config['options'])
        base_url += f"?options={encoded_options}"
    return base_url

# ==========================================================
# Engine (только один)
# ==========================================================

tasks_engine = create_engine(
    build_db_url(DB_TASKS),
    echo=False,
    pool_pre_ping=True
)

# ==========================================================
# Session
# ==========================================================

TasksSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=tasks_engine
)

# ==========================================================
# Helpers
# ==========================================================

def get_tasks_session():
    """Получить сессию БД задач (она же для всего)"""
    return TasksSessionLocal()

# ==========================================================
# Проверка соединения
# ==========================================================

def test_connections():
    """Проверка соединения с БД"""
    try:
        with tasks_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✔ Database connection established")
    except Exception as e:
        print("❌ Database connection error:")
        print(e)
        raise