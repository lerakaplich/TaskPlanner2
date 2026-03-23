# utils/sync_employees.py

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_tasks_session
from models.employees import ExternalEmployee, EmployeeData
from sqlalchemy import select, text


def sync_employees():
    """Синхронизация сотрудников из foreign_data.employees в employees_data"""
    session = get_tasks_session()

    try:
        print("=" * 60)
        print("🔄 СИНХРОНИЗАЦИЯ СОТРУДНИКОВ")
        print("=" * 60)

        # Получаем всех сотрудников из внешней таблицы
        stmt = select(ExternalEmployee)
        external_employees = session.scalars(stmt).all()

        print(f"📊 Найдено сотрудников в foreign_data.employees: {len(external_employees)}")

        # Получаем существующие ID в employees_data
        existing_ids = set()
        # 👇 ИСПРАВЛЕНО: используем правильное имя столбца employee_id
        result = session.execute(text("SELECT employee_id FROM employees_data"))
        for row in result:
            existing_ids.add(row[0])

        print(f"📊 Существующие ID в employees_data: {sorted(existing_ids)}")

        # Синхронизируем
        added = 0
        for emp in external_employees:
            if emp.id not in existing_ids:
                print(f"  ➕ Добавляем сотрудника ID={emp.id}: {emp.last_name} {emp.first_name}")

                # Создаем запись в employees_data
                # 👇 ИСПРАВЛЕНО: используем правильные поля таблицы
                employee_data = EmployeeData(
                    employee_id=emp.id,  # employee_id вместо id
                    last_login=None,
                    is_active=True,
                    role='user'  # можно определить на основе emp.rights
                )
                session.add(employee_data)
                added += 1

        if added > 0:
            session.commit()
            print(f"✅ Добавлено {added} сотрудников в employees_data")
        else:
            print("✅ Все сотрудники уже синхронизированы")

        # Проверяем результат
        result = session.execute(text("SELECT COUNT(*) FROM employees_data"))
        count = result.scalar()
        print(f"📊 Всего в employees_data: {count} записей")

    except Exception as e:
        session.rollback()
        print(f"❌ Ошибка синхронизации: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


def check_employee_exists(employee_id):
    """Проверка существования сотрудника в employees_data"""
    session = get_tasks_session()
    try:
        # 👇 ИСПРАВЛЕНО: используем employee_id
        stmt = text("SELECT employee_id FROM employees_data WHERE employee_id = :id")
        result = session.execute(stmt, {"id": employee_id}).first()
        return result is not None
    finally:
        session.close()


def fix_missing_employee(employee_id):
    """Добавление конкретного отсутствующего сотрудника"""
    session = get_tasks_session()
    try:
        # Получаем данные из внешней таблицы
        stmt = select(ExternalEmployee).where(ExternalEmployee.id == employee_id)
        emp = session.scalar(stmt)

        if not emp:
            print(f"❌ Сотрудник с ID={employee_id} не найден в foreign_data.employees")
            return False

        # Проверяем, может уже существует
        exists = check_employee_exists(employee_id)
        if exists:
            print(f"⚠️ Сотрудник ID={employee_id} уже существует в employees_data")
            return True

        # Создаем запись в employees_data
        # 👇 ИСПРАВЛЕНО: используем правильные поля
        employee_data = EmployeeData(
            employee_id=emp.id,
            last_login=None,
            is_active=True,
            role='admin' if emp.rights == 'superadmin' else 'user'
        )
        session.add(employee_data)
        session.commit()
        print(f"✅ Добавлен сотрудник ID={emp.id}: {emp.last_name} {emp.first_name}")
        return True

    except Exception as e:
        session.rollback()
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


def create_employees_data_table():
    """Создание таблицы employees_data если её нет"""
    session = get_tasks_session()
    try:
        # Проверяем существование таблицы
        result = session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'employees_data'
            )
        """))
        exists = result.scalar()

        if not exists:
            print("📦 Создание таблицы employees_data...")
            session.execute(text("""
                CREATE TABLE public.employees_data (
                    employee_id INTEGER PRIMARY KEY,
                    last_login TIMESTAMP WITH TIME ZONE,
                    is_active BOOLEAN DEFAULT true,
                    role VARCHAR(50) DEFAULT 'user'
                )
            """))
            session.commit()
            print("✅ Таблица employees_data создана")
        else:
            print("✅ Таблица employees_data уже существует")

    except Exception as e:
        print(f"❌ Ошибка при создании таблицы: {e}")
        session.rollback()
    finally:
        session.close()


def add_test_employees():
    """Добавление тестовых сотрудников напрямую"""
    session = get_tasks_session()
    try:
        test_employees = [
            (2, True, 'admin'),
            (6, True, 'user'),
            (8, True, 'user'),
            (9, True, 'user')
        ]

        added = 0
        for emp_id, is_active, role in test_employees:
            # Проверяем, существует ли уже
            stmt = text("SELECT employee_id FROM employees_data WHERE employee_id = :id")
            exists = session.execute(stmt, {"id": emp_id}).first()

            if not exists:
                session.execute(
                    text("INSERT INTO employees_data (employee_id, is_active, role) VALUES (:id, :active, :role)"),
                    {"id": emp_id, "active": is_active, "role": role}
                )
                added += 1
                print(f"  ➕ Добавлен сотрудник ID={emp_id}")

        if added > 0:
            session.commit()
            print(f"✅ Добавлено {added} тестовых сотрудников")
        else:
            print("✅ Все тестовые сотрудники уже существуют")

    except Exception as e:
        session.rollback()
        print(f"❌ Ошибка: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    # Сначала убедимся, что таблица существует
    create_employees_data_table()

    # Запускаем синхронизацию
    sync_employees()

    # Если какие-то ID все еще отсутствуют, добавляем их принудительно
    print("\n" + "=" * 60)
    print("🔍 ПРОВЕРКА КОНКРЕТНЫХ СОТРУДНИКОВ")
    print("=" * 60)

    missing = []
    for emp_id in [2, 6, 8, 9]:
        exists = check_employee_exists(emp_id)
        status = "✅" if exists else "❌"
        print(f"{status} Сотрудник ID={emp_id}: {'существует' if exists else 'ОТСУТСТВУЕТ'}")
        if not exists:
            missing.append(emp_id)

    # Добавляем отсутствующих
    if missing:
        print(f"\n⚠️ Найдены отсутствующие сотрудники: {missing}")
        print("🔄 Добавляем их принудительно...")
        add_test_employees()

        # Проверяем еще раз
        print("\n🔍 ПОВТОРНАЯ ПРОВЕРКА:")
        for emp_id in missing:
            exists = check_employee_exists(emp_id)
            status = "✅" if exists else "❌"
            print(f"{status} Сотрудник ID={emp_id}")