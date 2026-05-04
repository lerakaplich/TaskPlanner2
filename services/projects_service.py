# services/projects_service.py

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_tasks_session, get_employees_session
from models.projects import Project
from models.schemas.projects_dto import ProjectWithMembersDTO, ProjectCardDTO, ProjectBoardDTO, BoardColumnWithTasksDTO
from models.schemas.tasks_dto import TaskCardDTO, TaskPriority
from repositories.project_repo import ProjectRepo
from repositories.task_repo import TaskRepo
from repositories.employee_repo import EmployeeRepo  # ← ИСПРАВЛЕНО (было external_employee_repo)
from services.column_service import ColumnService
from models.employees import Employee  # ← ДОБАВЛЕНО

# Импортируем бота для отправки уведомлений
import asyncio
from telegram_bot import telegram_bot


class ProjectsService:
    def __init__(self, session=None):
        # Сессия для taskplanner БД (проекты, задачи)
        self.session = session or get_tasks_session()
        # Отдельная сессия для employees БД (сотрудники)
        self.employees_session = get_employees_session()

        self.current_user_id = None
        self.current_user = None
        self.project_repo = ProjectRepo(self.session)
        self.task_repo = TaskRepo(self.session)
        # Используем ОТДЕЛЬНУЮ сессию для EmployeeRepo
        self.employee_repo = EmployeeRepo(self.employees_session)  # ← ИСПРАВЛЕНО
        self.column_service = ColumnService(self.session)

    def __del__(self):
        """Закрываем сессии при удалении объекта"""
        try:
            if hasattr(self, 'employees_session') and self.employees_session:
                self.employees_session.close()
            if hasattr(self, 'session') and self.session:
                self.session.close()
        except:
            pass

    def set_current_user_id(self, user_id):
        self.current_user_id = user_id

    def set_current_user(self, user):
        self.current_user = user

    def _ensure_local_employee(self, external_employee_id: int) -> Optional[int]:
        """
        Проверяет наличие записи сотрудника в БД taskplanner.public.employees_data
        """
        try:
            # Проверяем и создаем запись в taskplanner.employee_data (НЕ в employees!)
            check_data_stmt = text("""
                SELECT employee_id FROM public.employees_data WHERE employee_id = :emp_id
            """)
            data_exists = self.session.execute(check_data_stmt, {'emp_id': external_employee_id}).first()

            if not data_exists:
                insert_data_stmt = text("""
                    INSERT INTO public.employees_data (employee_id, is_active, role)
                    VALUES (:emp_id, :is_active, :role)
                """)
                self.session.execute(insert_data_stmt, {
                    'emp_id': external_employee_id,
                    'is_active': True,
                    'role': 'user'
                })
                print(f"✅ Создана запись в public.employees_data для сотрудника {external_employee_id}")
                self.session.flush()

            return external_employee_id

        except Exception as e:
            print(f"⚠️ Ошибка при создании локальной записи сотрудника: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _send_telegram_notification(self, chat_id: int, message: str):
        """Отправляет уведомление через Telegram бота"""
        if not chat_id:
            return
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                telegram_bot.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
            )
            loop.close()
            print(f"✅ Уведомление отправлено в Telegram (chat_id={chat_id})")
        except Exception as e:
            print(f"⚠️ Ошибка отправки Telegram уведомления: {e}")

    def _get_employee_full_name(self, employee) -> str:
        """Возвращает ФИО сотрудника из employees БД"""
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

    def _get_employee_chat_id(self, employee_id: int) -> Optional[int]:
        """Получает chat_id сотрудника из БД employees"""
        try:
            # Используем employee_repo для получения сотрудника
            employee = self.employee_repo.get_by_id(employee_id)  # ← ИСПРАВЛЕНО
            if employee:
                return employee.chat_id
        except Exception as e:
            print(f"⚠️ Ошибка получения chat_id для сотрудника {employee_id}: {e}")
        return None

    def _send_project_notification(self, project_name: str, project_description: str,
                                   creator_name: str, participants: List[dict],
                                   is_new: bool = True, project_id: int = None):
        """Отправляет уведомление всем участникам проекта"""
        if is_new:
            title = "🆕 **НОВЫЙ ПРОЕКТ**"
            action = "добавлены в проект"
            footer = "Вы можете просмотреть проект в приложении TaskPlanner."
        else:
            title = "✏️ **ПРОЕКТ ОБНОВЛЕН**"
            action = "проект обновлен"
            footer = "Обновленную информацию можно посмотреть в приложении TaskPlanner."

        message = f"""{title}

📋 **Название:** {project_name}
👤 **Создатель проекта:** {creator_name}
📝 **Описание:** {project_description[:200]}{'...' if len(project_description) > 200 else ''}

Вы были {action} «{project_name}».

{footer}"""

        for participant in participants:
            emp_id = participant.get('id') if isinstance(participant, dict) else participant

            if self.current_user_id and emp_id == self.current_user_id:
                continue

            chat_id = self._get_employee_chat_id(emp_id)
            if chat_id:
                self._send_telegram_notification(chat_id, message)
                print(f"📨 Уведомление отправлено участнику ID={emp_id}")

    def get_projects_for_cards(self, search_query: str = "", status_filter: str = "Все", owner_filter: bool = False) -> \
    List[ProjectCardDTO]:
        try:
            all_projects = self.project_repo.get_all(exclude_archived=True)
            result = []

            for proj in all_projects:
                try:
                    if owner_filter and proj.owner != self.current_user_id:
                        continue

                    if search_query and search_query.lower() not in proj.name.lower():
                        continue

                    tasks = self.task_repo.get_by_project(proj.id)
                    total_tasks = len(tasks)
                    done_tasks = len([t for t in tasks if t.column and t.column.is_done_column])

                    member_count = len(proj.members) if hasattr(proj, 'members') else 0
                    admin_count = len([m for m in proj.members if m.is_admin]) if hasattr(proj, 'members') else 0

                    column_ids = self.project_repo.get_selected_column_ids(proj.id)
                    columns_count = len(column_ids) if column_ids else 0

                    owner_name = "Не назначен"
                    if proj.owner:
                        owner = self.employee_repo.get_by_id(proj.owner)  # ← ИСПРАВЛЕНО
                        if owner:
                            owner_name = f"{owner.last_name} {owner.first_name[0]}."
                            if owner.middle_name:
                                owner_name += f"{owner.middle_name[0]}."

                    created_at_str = None
                    if proj.created_at:
                        created_at_str = proj.created_at.strftime("%d.%m.%Y")

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
                        columns_count=columns_count
                    )

                    result.append(card_dto)
                except Exception as e:
                    print(f"⚠️ Ошибка при обработке проекта {proj.id if hasattr(proj, 'id') else 'unknown'}: {e}")
                    continue

            return result
        except Exception as e:
            print(f"❌ Критическая ошибка в get_projects_for_cards: {e}")
            import traceback
            traceback.print_exc()
            return []

    def archive_project(self, project_id: int) -> bool:
        try:
            project = self.project_repo.get_by_id(project_id)
            if not project:
                return False

            project.is_archived = True
            project.updated_at = datetime.now()
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при архивации проекта: {e}")
            return False

    def create_new_project(self, raw_data: dict, creator_id: int) -> Optional[ProjectWithMembersDTO]:
        try:
            # 1. Создаем проект
            project = self.project_repo.create(
                name=raw_data['name'],
                description=raw_data.get('description', ''),
                owner=creator_id,
                created_by=creator_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                is_archived=not raw_data.get('is_active', True)
            )

            self.session.flush()
            print(f"✅ Проект создан в БД, ID: {project.id}")

            # 2. Сохраняем ID выбранных шаблонных колонок
            selected_columns_data = raw_data.get('selected_columns_data', [])
            column_ids = [col.get('id') for col in selected_columns_data if col.get('id')]

            if column_ids:
                self.project_repo.save_selected_column_ids(project.id, column_ids)
                print(f"✅ Сохранены ID шаблонных колонок: {column_ids}")
            else:
                default_column_ids = [24, 25, 26, 27]
                self.project_repo.save_selected_column_ids(project.id, default_column_ids)
                print(f"✅ Сохранены ID колонок по умолчанию: {default_column_ids}")

            # 3. Обработка участников
            def to_id_list(val):
                if isinstance(val, str):
                    return [int(i.strip()) for i in val.split(',') if i.strip().isdigit()]
                return val or []

            member_ids = to_id_list(raw_data.get('participants_ids'))
            admin_ids = to_id_list(raw_data.get('admins_ids'))

            all_members = set(member_ids) | {creator_id}
            all_admins = set(admin_ids) | {creator_id}

            participants_list = []
            for emp_id in all_members:
                # Убеждаемся, что для сотрудника есть локальная запись в БД employees
                local_id = self._ensure_local_employee(emp_id)
                if not local_id:
                    print(f"⚠️ Не удалось создать локальную запись для сотрудника {emp_id}, пропускаем")
                    continue

                self.project_repo.add_member(
                    project_id=project.id,
                    employee_id=local_id,
                    is_admin=(emp_id in all_admins)
                )
                print(f"✅ Добавлен участник ID: {emp_id} (локальный ID: {local_id})")

                employee = self.employee_repo.get_by_id(emp_id)  # ← ИСПРАВЛЕНО
                if employee:
                    participants_list.append({
                        'id': emp_id,
                        'full_name': self._get_employee_full_name(employee)
                    })

            self.session.commit()

            # 4. Отправляем уведомления участникам
            creator_employee = self.employee_repo.get_by_id(creator_id)  # ← ИСПРАВЛЕНО
            creator_name = self._get_employee_full_name(creator_employee) if creator_employee else "Создатель проекта"

            if participants_list:
                self._send_project_notification(
                    project_name=raw_data['name'],
                    project_description=raw_data.get('description', ''),
                    creator_name=creator_name,
                    participants=participants_list,
                    is_new=True,
                    project_id=project.id
                )

            return self.get_project_for_edit(project.id)

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании проекта: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_project_for_edit(self, project_id: int) -> Optional[ProjectWithMembersDTO]:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return None

        dto = ProjectWithMembersDTO.model_validate(project)
        dto.member_ids = [m.employee_id for m in project.members]
        dto.admin_ids = [m.employee_id for m in project.members if m.is_admin]

        column_ids = self.project_repo.get_selected_column_ids(project_id)
        if column_ids:
            from sqlalchemy import select
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

        print(f"✅ Проект загружен из БД: {dto.name} (ID: {dto.id})")
        print(f"   Участников: {len(dto.member_ids)}, Админов: {len(dto.admin_ids)}")
        print(f"   ID шаблонных колонок: {column_ids}")

        return dto

    def update_project(self, project_id: int, dto: ProjectWithMembersDTO) -> bool:
        try:
            project = self.project_repo.get_by_id(project_id)
            if not project:
                return False

            old_member_ids = {m.employee_id for m in project.members}

            project.name = dto.name
            project.description = dto.description
            project.is_archived = dto.is_archived
            project.deadline = dto.deadline
            project.updated_at = datetime.now()

            if hasattr(dto, 'selected_columns_data') and dto.selected_columns_data:
                column_ids = [col.get('id') for col in dto.selected_columns_data if col.get('id')]
                if column_ids:
                    self.project_repo.save_selected_column_ids(project_id, column_ids)
                    print(f"✅ Обновлены ID колонок проекта: {column_ids}")

            current_members = {m.employee_id: bool(m.is_admin) for m in project.members}
            target_members = {emp_id: (emp_id in dto.admin_ids) for emp_id in dto.member_ids}

            current_ids = set(current_members.keys())
            target_ids = set(target_members.keys())

            new_member_ids = target_ids - current_ids
            removed_member_ids = current_ids - target_ids

            for emp_id in removed_member_ids:
                self.project_repo.remove_member(project_id, emp_id)

            participants_list = []
            for emp_id in new_member_ids:
                local_id = self._ensure_local_employee(emp_id)
                if not local_id:
                    print(f"⚠️ Не удалось создать локальную запись для сотрудника {emp_id}, пропускаем")
                    continue

                is_admin = target_members[emp_id]
                self.project_repo.add_member(project_id, local_id, is_admin=is_admin)

                employee = self.employee_repo.get_by_id(emp_id)  # ← ИСПРАВЛЕНО
                if employee:
                    participants_list.append({
                        'id': emp_id,
                        'full_name': self._get_employee_full_name(employee)
                    })

            for emp_id in (current_ids & target_ids):
                if current_members[emp_id] != target_members[emp_id]:
                    self.project_repo.update_member_role(project_id, emp_id, is_admin=target_members[emp_id])

            self.session.commit()

            if participants_list:
                creator_employee = self.employee_repo.get_by_id(project.owner)  # ← ИСПРАВЛЕНО
                creator_name = self._get_employee_full_name(
                    creator_employee) if creator_employee else "Создатель проекта"

                self._send_project_notification(
                    project_name=project.name,
                    project_description=project.description or '',
                    creator_name=creator_name,
                    participants=participants_list,
                    is_new=False,
                    project_id=project_id
                )

            return True

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении проекта: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_project_board_data(self, project_id: int) -> Optional[ProjectBoardDTO]:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return None

        column_ids = self.project_repo.get_selected_column_ids(project_id)

        from sqlalchemy import select
        from models.projects import BoardColumn

        if column_ids:
            stmt = select(BoardColumn).where(BoardColumn.id.in_(column_ids)).order_by(BoardColumn.template_order)
            template_columns = self.session.scalars(stmt).all()
        else:
            stmt = select(BoardColumn).where(BoardColumn.is_template == True).order_by(BoardColumn.template_order)
            template_columns = self.session.scalars(stmt).all()

        tasks = self.task_repo.get_by_project(project_id)

        tasks_by_column = {}
        for task in tasks:
            column_name = task.column.name if task.column else "К выполнению"
            if column_name not in tasks_by_column:
                tasks_by_column[column_name] = []
            tasks_by_column[column_name].append(task)

        board_columns_dto = []
        for template_col in template_columns:
            column_tasks = tasks_by_column.get(template_col.name, [])

            task_cards = []
            for t in column_tasks:
                # Получаем имя назначенного сотрудника
                assigned_name = "Не назначен"
                if t.assigned_to:
                    employee = self.employee_repo.get_by_id(t.assigned_to)  # ← ИСПРАВЛЕНО
                    if employee:
                        assigned_name = self._get_employee_full_name(employee)

                is_overdue = (t.deadline < datetime.now()) if t.deadline else False

                task_cards.append(TaskCardDTO(
                    id=t.id,
                    title=t.title,
                    priority=TaskPriority(t.priority.value if hasattr(t.priority, 'value') else t.priority),
                    deadline=t.deadline,
                    assigned_to_name=assigned_name,
                    is_overdue=is_overdue
                ))

            col_dto = BoardColumnWithTasksDTO(
                id=template_col.id,
                name=template_col.name,
                color=template_col.color or "#cccccc",
                position=template_col.template_order or 0,
                is_done_column=template_col.is_done_column,
                tasks=task_cards
            )
            board_columns_dto.append(col_dto)

        project_dto = ProjectWithMembersDTO.model_validate(project)
        project_dto.selected_columns_data = [
            {'id': col.id, 'name': col.name, 'col_key': col.name.lower().replace(' ', '_')}
            for col in template_columns
        ]

        return ProjectBoardDTO(
            project=project_dto,
            columns=board_columns_dto
        )

    def add_column_to_project(self, project_id: int, template_column_id: int = None, custom_data: Dict = None) -> \
    Optional[Dict[str, Any]]:
        try:
            column = self.column_service.create_project_column(
                project_id=project_id,
                template_column_id=template_column_id,
                custom_data=custom_data
            )

            if column:
                self.session.commit()
                print(f"✅ Колонка '{column['name']}' добавлена в проект {project_id}")

            return column

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при добавлении колонки в проект: {e}")
            return None