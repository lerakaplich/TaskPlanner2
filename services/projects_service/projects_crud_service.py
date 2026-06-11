# services/projects_service/projects_crud_service.py
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select

from models.schemas.projects_dto import ProjectWithMembersDTO, ProjectCardDTO
from repositories.employee_repo import EmployeeRepo
from repositories.project_repo import ProjectRepo
from telegram_bot.bot import telegram_bot

logger = logging.getLogger(__name__)


def _send_notification_sync(chat_id: int, project_name: str, manager_name: str, description: str, role: str):
    """Синхронная обёртка для отправки уведомления"""
    try:
        # Используем asyncio.run() для создания нового цикла
        asyncio.run(
            telegram_bot.send_project_notification(
                chat_id, project_name, manager_name, description, role
            )
        )
    except RuntimeError as e:
        if "already running" in str(e):
            # Если цикл уже запущен, используем текущий
            loop = asyncio.get_running_loop()
            loop.create_task(
                telegram_bot.send_project_notification(
                    chat_id, project_name, manager_name, description, role
                )
            )
        else:
            logger.error(f"❌ Ошибка при отправке уведомления: {e}")
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке уведомления: {e}")


def _send_update_notification_sync(chat_id: int, project_name: str):
    """Синхронная обёртка для отправки уведомления об обновлении"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(
                telegram_bot.send_project_update_notification(chat_id, project_name)
            )
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке уведомления об обновлении: {e}")


class ProjectsCrudService:
    """CRUD операции с проектами"""

    def __init__(self, session, employees_session, current_user_id=None):
        self.session = session
        self.employees_session = employees_session
        self.current_user_id = current_user_id
        self.project_repo = ProjectRepo(session)
        self.employee_repo = EmployeeRepo(employees_session)

    def set_current_user_id(self, user_id):
        self.current_user_id = user_id

    def get_project_for_edit(self, project_id: int) -> Optional[ProjectWithMembersDTO]:
        """Получить проект для редактирования"""
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return None

        dto = ProjectWithMembersDTO.model_validate(project)
        dto.member_ids = [m.employee_id for m in project.members]
        dto.admin_ids = [m.employee_id for m in project.members if m.is_admin]
        dto.manager_id = project.manager_id

        # Получаем имя куратора
        if project.manager_id:
            manager = self.employee_repo.get_by_id(project.manager_id)
            if manager:
                dto.manager_name = self._get_employee_full_name(manager)

        # Загружаем колонки
        column_ids = self.project_repo.get_selected_column_ids(project_id)
        if column_ids:
            from models.projects import BoardColumn
            stmt = select(BoardColumn).where(BoardColumn.id.in_(column_ids))
            columns = self.session.scalars(stmt).all()

            dto.selected_columns_data = []
            for col in columns:
                dto.selected_columns_data.append({
                    'id': col.id,
                    'name': col.name,
                    'col_key': col.name.lower().replace(' ', '_'),
                    'color': col.color,
                    'position': col.position,
                    'is_done_column': col.is_done_column
                })

        return dto

    def create_project_with_chat(self, project_data: dict, creator_id: int) -> Optional[Dict]:
        """
        Создаёт проект и автоматически создаёт для него чат.

        Args:
            project_data: данные проекта
            creator_id: ID создателя

        Returns:
            Optional[Dict]: данные созданного проекта или None
        """
        from services.chat_service import ChatService
        from database import get_tasks_session

        # Создаём проект
        new_project = self.create_new_project(project_data, creator_id)

        if not new_project:
            print(f"❌ Не удалось создать проект")
            return None

        # Создаём чат для проекта
        try:
            chat_session = get_tasks_session()
            if chat_session:
                chat_service = ChatService(chat_session)

                # Собираем участников
                participants = self._extract_participant_ids(project_data)
                admins = self._extract_admin_ids(project_data)
                manager_id = project_data.get('manager_id')

                chat_id = chat_service.create_project_chat(
                    project_id=new_project.id,
                    project_name=new_project.name,
                    creator_id=creator_id,
                    participant_ids=participants,
                    admin_ids=admins,
                    manager_id=manager_id
                )

                if chat_id:
                    print(f"✅ Чат для проекта {new_project.id} создан (ID: {chat_id})")
                else:
                    print(f"⚠️ Проект создан, но чат не создан")

                chat_session.close()
            else:
                print(f"⚠️ Нет подключения к БД чатов")

        except Exception as e:
            print(f"⚠️ Ошибка при создании чата: {e}")

        return new_project

    def archive_project(self, project_id: int) -> bool:
        """Архивировать проект"""
        try:
            project = self.project_repo.get_by_id(project_id)
            if not project:
                return False

            project.is_archived = True
            project.updated_at = datetime.now()

            # Архивируем все задачи проекта
            from repositories.task_repo import TaskRepo
            task_repo = TaskRepo(self.session)
            tasks = task_repo.get_by_project(project_id)
            for task in tasks:
                if not task.is_archived:
                    task.is_archived = True
                    task.archived_at = datetime.now()

            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при архивации проекта: {e}")
            return False

    def create_new_project(self, raw_data: dict, creator_id: int) -> Optional[ProjectWithMembersDTO]:
        """Создать новый проект"""
        try:
            from repositories.task_repo import TaskRepo

            project = self.project_repo.create(
                name=raw_data['name'],
                description=raw_data.get('description', ''),
                owner=creator_id,
                created_by=creator_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                is_archived=not raw_data.get('is_active', True),
                manager_id=raw_data.get('manager_id')
            )

            self.session.flush()

            # Сохраняем ID выбранных колонок
            selected_columns_data = raw_data.get('selected_columns_data', [])
            column_ids = [col.get('id') for col in selected_columns_data if col.get('id')]
            if column_ids:
                self.project_repo.save_selected_column_ids(project.id, column_ids)
            else:
                default_column_ids = [24, 25, 26, 27]
                self.project_repo.save_selected_column_ids(project.id, default_column_ids)

            self.session.commit()
            # === ОТПРАВКА УВЕДОМЛЕНИЙ В TELEGRAM ===
            self._send_project_notifications(project.id, project.name, raw_data, creator_id)

            return self.get_project_for_edit(project.id)

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании проекта: {e}")
            return None

    def _extract_participant_ids(self, project_data: dict) -> List[int]:
        """Извлекает ID участников из данных проекта"""
        participants = []

        # Из participants_ids
        participants_ids_str = project_data.get('participants_ids', '')
        if participants_ids_str:
            for pid in participants_ids_str.split(','):
                if pid.strip():
                    participants.append(int(pid.strip()))

        # Из participants
        if 'participants' in project_data:
            for p in project_data['participants']:
                if isinstance(p, dict) and p.get('id'):
                    participants.append(p['id'])
                elif isinstance(p, int):
                    participants.append(p)

        return list(set(participants))

    def _extract_admin_ids(self, project_data: dict) -> List[int]:
        """Извлекает ID администраторов из данных проекта"""
        admins = []

        # Из admins_ids
        admins_ids_str = project_data.get('admins_ids', '')
        if admins_ids_str:
            for aid in admins_ids_str.split(','):
                if aid.strip():
                    admins.append(int(aid.strip()))

        # Из admins
        if 'admins' in project_data:
            for a in project_data['admins']:
                if isinstance(a, dict) and a.get('id'):
                    admins.append(a['id'])
                elif isinstance(a, int):
                    admins.append(a)

        return list(set(admins))

    def _send_project_notifications(self, project_id: int, project_name: str,
                                    raw_data: Dict[str, Any], creator_id: int):
        """
        Отправляет уведомления о новом проекте всем участникам, администраторам и куратору
        """
        try:
            from database import get_employees_session
            from models.employees import Employee
            import threading

            # Получаем списки ID
            participants_ids_str = raw_data.get('participants_ids', '')
            admins_ids_str = raw_data.get('admins_ids', '')
            manager_id = raw_data.get('manager_id')

            # Парсим ID участников (все, кто добавлен в проект)
            participant_ids = set()
            if participants_ids_str:
                for pid in participants_ids_str.split(','):
                    if pid and pid.strip():
                        participant_ids.add(int(pid.strip()))

            # Парсим ID администраторов
            admin_ids = set()
            if admins_ids_str:
                for aid in admins_ids_str.split(','):
                    if aid and aid.strip():
                        admin_ids.add(int(aid.strip()))

            # ВАЖНО: Добавляем куратора в список участников для уведомлений
            if manager_id:
                manager_id_int = int(manager_id) if isinstance(manager_id, str) else manager_id
                participant_ids.add(manager_id_int)

            # ВАЖНО: Добавляем создателя в список участников для уведомлений
            participant_ids.add(creator_id)

            # ВАЖНО: Все администраторы также должны получать уведомления
            for admin_id in admin_ids:
                participant_ids.add(admin_id)

            # Получаем имя куратора
            manager_name = raw_data.get('manager_name', 'Не назначен')
            if not manager_name or manager_name == 'Не назначен':
                manager_id_val = raw_data.get('manager_id')
                if manager_id_val:
                    with get_employees_session() as emp_session:
                        emp_id = int(manager_id_val) if isinstance(manager_id_val, str) else manager_id_val
                        employee = emp_session.get(Employee, emp_id)
                        if employee:
                            first_initial = f"{employee.first_name[0]}." if employee.first_name else ""
                            middle_initial = f"{employee.middle_name[0]}." if employee.middle_name else ""
                            manager_name = f"{employee.last_name} {first_initial}{middle_initial}".strip()

            description = raw_data.get('description', '')

            # Отправляем уведомления ВСЕМ участникам
            with get_employees_session() as emp_session:
                for emp_id in participant_ids:
                    employee = emp_session.get(Employee, emp_id)
                    if employee and employee.chat_id:
                        # Определяем роль пользователя
                        role = 'участник'

                        # Куратор имеет высший приоритет
                        if manager_id and emp_id == (int(manager_id) if isinstance(manager_id, str) else manager_id):
                            role = 'куратор'
                        # Затем проверяем, является ли пользователь администратором
                        elif emp_id in admin_ids:
                            role = 'администратор'
                        # Иначе - обычный участник

                        # Запускаем отправку в отдельном потоке
                        thread = threading.Thread(
                            target=_send_notification_sync,
                            args=(employee.chat_id, project_name, manager_name, description, role),
                            daemon=True
                        )
                        thread.start()
                        logger.info(f"📨 Запланировано уведомление для {employee.last_name} (ID={emp_id}, роль: {role})")

            logger.info(
                f"📨 Отправлены уведомления о проекте '{project_name}' для {len(participant_ids)} участников: {participant_ids}")
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке уведомлений о проекте: {e}")
            import traceback
            traceback.print_exc()

    def update_project(self, project_id: int, updated_data: Any) -> bool:
        """Обновляет проект и отправляет уведомления о изменениях"""
        try:
            # Получаем существующий проект
            project = self.project_repo.get_by_id(project_id)
            if not project:
                print(f"❌ Проект {project_id} не найден")
                return False

            # Преобразуем DTO в словарь, если это DTO
            if hasattr(updated_data, 'model_dump'):
                data_dict = updated_data.model_dump()
            elif hasattr(updated_data, 'dict'):
                data_dict = updated_data.dict()
            else:
                data_dict = updated_data

            # Обновляем поля проекта
            if 'name' in data_dict and data_dict['name']:
                project.name = data_dict['name']
            if 'description' in data_dict:
                project.description = data_dict['description']
            if 'is_archived' in data_dict:
                project.is_archived = data_dict['is_archived']
            if 'manager_id' in data_dict:
                project.manager_id = data_dict['manager_id']

            # Обновляем дату
            project.updated_at = datetime.now()

            # Обновляем участников и администраторов
            member_ids = data_dict.get('member_ids', [])
            admin_ids = data_dict.get('admin_ids', [])

            # ВАЖНО: Сначала добавляем отсутствующих сотрудников в employees_data
            self._ensure_employees_exist_in_taskplanner(member_ids)

            # Очищаем существующие связи
            self.project_repo.clear_project_members(project_id)

            # Добавляем новых участников
            for emp_id in member_ids:
                is_admin = emp_id in admin_ids
                self.project_repo.add_project_member(project_id, emp_id, is_admin)

            # Обновляем выбранные колонки
            selected_columns_data = data_dict.get('selected_columns_data', [])
            if selected_columns_data:
                column_ids = [col.get('id') for col in selected_columns_data if col.get('id')]
                if column_ids:
                    self.project_repo.save_selected_column_ids(project_id, column_ids)

            self.session.commit()

            # === ОТПРАВКА УВЕДОМЛЕНИЙ ОБ ИЗМЕНЕНИЯХ ===
            self._send_project_update_notifications(project_id, project.name, data_dict)

            print(f"✅ Проект '{project.name}' обновлён")
            return True

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении проекта: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _ensure_employees_exist_in_taskplanner(self, employee_ids: List[int]):
        """Проверяет наличие записей сотрудников в employees_data и создаёт их при необходимости"""
        try:
            from sqlalchemy import text

            for emp_id in employee_ids:
                # Проверяем, есть ли запись в employees_data
                check_stmt = text("SELECT employee_id FROM public.employees_data WHERE employee_id = :emp_id")
                result = self.session.execute(check_stmt, {'emp_id': emp_id}).first()

                if not result:
                    # Создаём запись
                    insert_stmt = text("""
                        INSERT INTO public.employees_data (employee_id, is_active, role, created_at, updated_at)
                        VALUES (:emp_id, true, 'user', NOW(), NOW())
                    """)
                    self.session.execute(insert_stmt, {'emp_id': emp_id})
                    print(f"✅ Создана запись в employees_data для сотрудника {emp_id}")
        except Exception as e:
            print(f"⚠️ Ошибка при проверке/создании employees_data: {e}")

    def _send_project_update_notifications(self, project_id: int, project_name: str,
                                           updated_data: Dict[str, Any]):
        """
        Отправляет уведомления об изменении проекта
        """
        try:
            from database import get_employees_session
            from models.employees import Employee
            import threading

            # Получаем список ID участников из данных обновления
            member_ids = set()

            participants_ids = updated_data.get('participants_ids', '')
            if participants_ids:
                for pid in participants_ids.split(','):
                    if pid and pid.strip():
                        member_ids.add(int(pid.strip()))

            admins_ids = updated_data.get('admins_ids', '')
            if admins_ids:
                for aid in admins_ids.split(','):
                    if aid and aid.strip():
                        member_ids.add(int(aid.strip()))

            manager_id = updated_data.get('manager_id')
            if manager_id:
                member_ids.add(int(manager_id))

            # Отправляем уведомления в отдельных потоках
            with get_employees_session() as emp_session:
                for emp_id in member_ids:
                    employee = emp_session.get(Employee, emp_id)
                    if employee and employee.chat_id:
                        thread = threading.Thread(
                            target=_send_update_notification_sync,
                            args=(employee.chat_id, project_name),
                            daemon=True
                        )
                        thread.start()

            print(f"📨 Отправлены уведомления об обновлении проекта '{project_name}' для {len(member_ids)} участников")
        except Exception as e:
            print(f"❌ Ошибка при отправке уведомлений об обновлении: {e}")

    def get_projects_for_cards(self, search_query: str = "", status_filter: str = "Все",
                               owner_filter: bool = False) -> List[ProjectCardDTO]:
        """Получить проекты для карточек, отсортированные по дате создания (новые сверху)"""
        try:
            all_projects = self.project_repo.get_all(exclude_archived=True)

            # Фильтруем проекты
            filtered_projects = []
            for proj in all_projects:
                if owner_filter and proj.owner != self.current_user_id:
                    continue
                if search_query and search_query.lower() not in proj.name.lower():
                    continue
                filtered_projects.append(proj)

            # СОРТИРУЕМ ПО ДАТЕ СОЗДАНИЯ (НОВЫЕ СВЕРХУ)
            filtered_projects.sort(key=lambda p: p.created_at, reverse=True)

            result = []
            for proj in filtered_projects:
                from repositories.task_repo import TaskRepo
                task_repo = TaskRepo(self.session)
                tasks = task_repo.get_by_project(proj.id)
                total_tasks = len(tasks)
                done_tasks = len([t for t in tasks if t.column and t.column.is_done_column])

                member_count = len(proj.members) if hasattr(proj, 'members') else 0
                admin_count = len([m for m in proj.members if m.is_admin]) if hasattr(proj, 'members') else 0

                column_ids = self.project_repo.get_selected_column_ids(proj.id)
                columns_count = len(column_ids) if column_ids else 0

                # Получаем имя владельца
                owner_name = "Не назначен"
                if proj.owner:
                    owner = self.employee_repo.get_by_id(proj.owner)
                    if owner:
                        owner_name = f"{owner.last_name} {owner.first_name[0]}."
                        if owner.middle_name:
                            owner_name += f"{owner.middle_name[0]}."

                # Получаем имя куратора
                manager_name = None
                if proj.manager_id:
                    manager = self.employee_repo.get_by_id(proj.manager_id)
                    if manager:
                        manager_name = f"{manager.last_name} {manager.first_name[0]}."
                        if manager.middle_name:
                            manager_name += f"{manager.middle_name[0]}."

                created_at_str = proj.created_at.strftime("%d.%m.%Y") if proj.created_at else None

                card_dto = ProjectCardDTO(
                    id=proj.id,
                    name=proj.name,
                    description=proj.description or "",
                    tasks_total=total_tasks,
                    tasks_done=done_tasks,
                    deadline=proj.deadline,
                    is_archived=proj.is_archived,
                    member_count=member_count,
                    admin_count=admin_count,
                    owner_name=owner_name,
                    owner_id=proj.owner,
                    created_at=created_at_str,
                    columns_count=columns_count,
                    manager_name=manager_name
                )
                result.append(card_dto)

            return result
        except Exception as e:
            print(f"❌ Критическая ошибка в get_projects_for_cards: {e}")
            return []

    def _get_employee_full_name(self, employee) -> str:
        """Возвращает ФИО сотрудника"""
        if not employee:
            return "Неизвестный"
        parts = []
        if hasattr(employee, 'last_name') and employee.last_name:
            parts.append(employee.last_name)
        if hasattr(employee, 'first_name') and employee.first_name:
            parts.append(employee.first_name)
        if hasattr(employee, 'middle_name') and employee.middle_name:
            parts.append(employee.middle_name)
        return " ".join(parts) if parts else f"User {employee.id if hasattr(employee, 'id') else '?'}"