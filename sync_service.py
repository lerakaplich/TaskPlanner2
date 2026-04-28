# services/sync_service.py

import asyncio
import threading
from datetime import datetime
from sqlalchemy import select, text
from database import get_tasks_session, get_employees_session
from models.employees import ExternalEmployee, LocalEmployee
import logging

logger = logging.getLogger(__name__)


class SyncService:
    """Сервис для синхронизации сотрудников между FDW и локальной БД"""

    def __init__(self):
        self.running = False
        self.sync_thread = None
        self.sync_interval = 30  # секунд

    def sync_employees(self):
        """Синхронизирует foreign_data.employees с public.employees"""
        tasks_session = None
        employees_session = None

        try:
            tasks_session = get_tasks_session()
            employees_session = get_employees_session()

            # Получаем всех сотрудников из FDW
            fdw_employees = tasks_session.query(ExternalEmployee).all()

            # Получаем всех сотрудников из локальной БД
            local_employees = employees_session.query(LocalEmployee).all()
            local_ids = {emp.id for emp in local_employees}
            fdw_ids = {emp.id for emp in fdw_employees}

            # 1. Обновляем существующих и добавляем новых
            for fdw_emp in fdw_employees:
                local_emp = employees_session.get(LocalEmployee, fdw_emp.id)

                if local_emp:
                    # Обновляем существующего
                    local_emp.number = fdw_emp.number
                    local_emp.last_name = fdw_emp.last_name
                    local_emp.first_name = fdw_emp.first_name
                    local_emp.middle_name = fdw_emp.middle_name
                    local_emp.position = fdw_emp.position
                    local_emp.rights = fdw_emp.rights
                    local_emp.phone_number = fdw_emp.phone_number
                    local_emp.email = fdw_emp.email
                    local_emp.chat_id = fdw_emp.chat_id
                    local_emp.birth_date = fdw_emp.birth_date
                    local_emp.department_id = fdw_emp.department_id
                    local_emp.division_id = fdw_emp.division_id
                    local_emp.organization_id = fdw_emp.organization_id
                    local_emp.session_token = fdw_emp.session_token
                    local_emp.settings = fdw_emp.settings
                    if hasattr(fdw_emp, 'password_hash'):
                        local_emp.password_hash = fdw_emp.password_hash
                else:
                    # Добавляем нового
                    new_emp = LocalEmployee(
                        id=fdw_emp.id,
                        number=fdw_emp.number,
                        last_name=fdw_emp.last_name,
                        first_name=fdw_emp.first_name,
                        middle_name=fdw_emp.middle_name,
                        position=fdw_emp.position,
                        rights=fdw_emp.rights,
                        phone_number=fdw_emp.phone_number,
                        email=fdw_emp.email,
                        chat_id=fdw_emp.chat_id,
                        birth_date=fdw_emp.birth_date,
                        department_id=fdw_emp.department_id,
                        division_id=fdw_emp.division_id,
                        organization_id=fdw_emp.organization_id,
                        session_token=fdw_emp.session_token,
                        settings=fdw_emp.settings,
                        password_hash=getattr(fdw_emp, 'password_hash', None)
                    )
                    employees_session.add(new_emp)

            # 2. Удаляем тех, кого нет в FDW (но только тех, кто не был добавлен через регистрацию)
            # Для этого нужно отслеживать source (FDW или регистрация)
            # Пока просто удаляем только если нет в FDW
            for local_id in local_ids:
                if local_id not in fdw_ids:
                    # Проверяем, не был ли этот сотрудник создан через регистрацию
                    # Для этого можно добавить флаг is_from_fdw
                    emp = employees_session.get(LocalEmployee, local_id)
                    if emp and hasattr(emp, 'is_from_fdw') and emp.is_from_fdw:
                        employees_session.delete(emp)

            employees_session.commit()
            logger.info(
                f"✅ Синхронизация завершена. FDW: {len(fdw_employees)}, Local: {len(employees_session.query(LocalEmployee).all())}")

        except Exception as e:
            if employees_session:
                employees_session.rollback()
            logger.error(f"❌ Ошибка синхронизации: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if tasks_session:
                tasks_session.close()
            if employees_session:
                employees_session.close()

    def sync_employee_from_local_to_fdw(self, employee_data: dict) -> bool:
        """Синхронизирует нового сотрудника из локальной БД в FDW"""
        try:
            # Здесь нужно выполнить вставку в foreign_data.employees
            # Но так как FDW только для чтения, нужно писать в исходную БД
            from database import get_employees_session
            from models.employees import LocalEmployee

            # Получаем прямую сессию к employees БД
            emp_session = get_employees_session()

            # Создаем прямую вставку в public.employees (исходная таблица)
            # Используем сырой SQL или ORM для исходной БД
            from models.employees import Employee as SourceEmployee

            new_emp = SourceEmployee(
                number=employee_data.get('number'),
                last_name=employee_data.get('last_name'),
                first_name=employee_data.get('first_name'),
                middle_name=employee_data.get('middle_name'),
                position=employee_data.get('position'),
                rights=employee_data.get('rights', 'user'),
                phone_number=employee_data.get('phone_number'),
                email=employee_data.get('email'),
                chat_id=employee_data.get('chat_id'),
                birth_date=employee_data.get('birth_date'),
                department_id=employee_data.get('department_id'),
                division_id=employee_data.get('division_id'),
                organization_id=1,
                password_hash=employee_data.get('password_hash')
            )
            emp_session.add(new_emp)
            emp_session.commit()

            # Теперь FDW автоматом подтянет эту запись
            logger.info(f"✅ Сотрудник {employee_data.get('last_name')} синхронизирован в исходную БД")
            emp_session.close()
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации в FDW: {e}")
            return False

    def start_background_sync(self):
        """Запускает фоновую синхронизацию"""
        if self.running:
            return

        self.running = True

        def sync_loop():
            while self.running:
                try:
                    self.sync_employees()
                except Exception as e:
                    logger.error(f"Ошибка в цикле синхронизации: {e}")
                import time
                time.sleep(self.sync_interval)

        self.sync_thread = threading.Thread(target=sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info(f"🔄 Фоновая синхронизация запущена (интервал: {self.sync_interval} сек)")

    def stop_background_sync(self):
        """Останавливает фоновую синхронизацию"""
        self.running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        logger.info("🔄 Фоновая синхронизация остановлена")


# Глобальный экземпляр
sync_service = SyncService()