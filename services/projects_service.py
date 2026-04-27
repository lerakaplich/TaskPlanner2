# services/projects_service.py

import json  # 👈 ДОБАВИТЬ
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from database import get_tasks_session
from models.projects import Project
from models.schemas.projects_dto import ProjectWithMembersDTO, ProjectCardDTO, ProjectBoardDTO, BoardColumnWithTasksDTO
from models.schemas.tasks_dto import TaskCardDTO, TaskPriority
from repositories.project_repo import ProjectRepo
from repositories.task_repo import TaskRepo
from repositories.external_employee_repo import ExternalEmployeeRepo
from services.column_service import ColumnService


class ProjectsService:
    def __init__(self, session=None):
        self.session = session or get_tasks_session()
        self.current_user_id = None
        self.project_repo = ProjectRepo(session)
        self.task_repo = TaskRepo(session)
        self.employee_repo = ExternalEmployeeRepo(session)
        self.column_service = ColumnService(session)

    def set_current_user_id(self, user_id):
        self.current_user_id = user_id

    def set_current_user(self, user):
        self.current_user = user

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

                    # Исправленный вызов - с try/except
                    try:
                        columns_count = self.project_repo.get_project_columns_count(proj.id)
                    except Exception as e:
                        print(f"⚠️ Ошибка подсчета колонок для проекта {proj.id}: {e}")
                        columns_count = 0

                    owner_name = "Не назначен"
                    if proj.owner:
                        owner = self.employee_repo.get_by_id(proj.owner)
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

            # 2. Создаем колонки для канбан-доски и сохраняем их ID
            selected_columns_data = raw_data.get('selected_columns_data', [])
            created_columns = []
            column_ids = []

            if selected_columns_data:
                created_columns = self.column_service.create_project_columns_batch(
                    project_id=project.id,
                    columns_data=selected_columns_data
                )
                # Сохраняем ID созданных колонок
                column_ids = [col['id'] for col in created_columns]
                self.project_repo.save_selected_column_ids(project.id, column_ids)
                print(f"✅ Создано {len(created_columns)} колонок, ID: {column_ids}")
            else:
                default_columns = [
                    {'name': 'Название проекта', 'color': '#1B232A', 'position': 0, 'is_done_column': False},
                    {'name': 'Статус', 'color': '#ccab6e', 'position': 1, 'is_done_column': False},
                    {'name': 'Прогресс', 'color': '#9b59b6', 'position': 2, 'is_done_column': False}
                ]
                created_columns = self.column_service.create_project_columns_batch(
                    project_id=project.id,
                    columns_data=default_columns
                )
                column_ids = [col['id'] for col in created_columns]
                self.project_repo.save_selected_column_ids(project.id, column_ids)
                print(f"✅ Создано {len(created_columns)} стандартных колонок, ID: {column_ids}")

            # 3. Обработка участников
            def to_id_list(val):
                if isinstance(val, str):
                    return [int(i.strip()) for i in val.split(',') if i.strip().isdigit()]
                return val or []

            member_ids = to_id_list(raw_data.get('participants_ids'))
            admin_ids = to_id_list(raw_data.get('admins_ids'))

            all_members = set(member_ids) | {creator_id}
            all_admins = set(admin_ids) | {creator_id}

            for emp_id in all_members:
                self.project_repo.add_member(
                    project_id=project.id,
                    employee_id=emp_id,
                    is_admin=(emp_id in all_admins)
                )
                print(f"✅ Добавлен участник ID: {emp_id}")

            self.session.commit()
            return self.get_project_for_edit(project.id)

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании проекта: {e}")
            import traceback
            traceback.print_exc()
            return None

    def update_project(self, project_id: int, dto: ProjectWithMembersDTO) -> bool:
        try:
            project = self.project_repo.get_by_id(project_id)
            if not project:
                return False

            project.name = dto.name
            project.description = dto.description
            project.is_archived = dto.is_archived
            project.deadline = dto.deadline
            project.updated_at = datetime.now()

            # Сохраняем ID колонок, если они изменились
            if hasattr(dto, 'selected_columns_data') and dto.selected_columns_data:
                # Нужно обновить колонки в проекте
                # Для простоты: удаляем старые и создаем новые
                # Или можно обновлять существующие
                pass

            # Обновление участников...
            current_members = {m.employee_id: bool(m.is_admin) for m in project.members}
            target_members = {emp_id: (emp_id in dto.admin_ids) for emp_id in dto.member_ids}

            current_ids = set(current_members.keys())
            target_ids = set(target_members.keys())

            for emp_id in (current_ids - target_ids):
                self.project_repo.remove_member(project_id, emp_id)

            for emp_id in (target_ids - current_ids):
                is_admin = target_members[emp_id]
                self.project_repo.add_member(project_id, emp_id, is_admin=is_admin)

            for emp_id in (current_ids & target_ids):
                if current_members[emp_id] != target_members[emp_id]:
                    self.project_repo.update_member_role(project_id, emp_id, is_admin=target_members[emp_id])

            self.session.commit()
            return True

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении проекта: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_project_for_edit(self, project_id: int) -> Optional[ProjectWithMembersDTO]:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return None

        dto = ProjectWithMembersDTO.model_validate(project)
        dto.member_ids = [m.employee_id for m in project.members]
        dto.admin_ids = [m.employee_id for m in project.members if m.is_admin]

        # Загружаем данные колонок по сохраненным ID
        column_ids = self.project_repo.get_selected_column_ids(project_id)
        if column_ids:
            # Получаем полные данные колонок из БД
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
        print(f"   ID колонок: {column_ids}")

        return dto

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

    def get_project_board_data(self, project_id: int) -> Optional[ProjectBoardDTO]:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return None

        # Получаем колонки проекта из БД (те, которые уже созданы)
        all_project_columns = self.column_service.get_project_columns(project_id)

        # Если есть созданные колонки - используем их
        if all_project_columns:
            board_columns_dto = []
            for col in sorted(all_project_columns, key=lambda x: x['position']):
                tasks = self.task_repo.get_by_column(col['id'])

                task_cards = []
                for t in tasks:
                    assigned_name = self.employee_repo.get_full_name(t.assigned_to) if t.assigned_to else "Не назначен"
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
                    id=col['id'],
                    name=col['name'],
                    color=col['color'] or "#cccccc",
                    position=col['position'],
                    is_done_column=col['is_done_column'],
                    tasks=task_cards
                )
                board_columns_dto.append(col_dto)
        else:
            # Если нет колонок, создаем из сохраненных ID или шаблонов
            column_ids = self.project_repo.get_selected_column_ids(project_id)
            if column_ids:
                from sqlalchemy import select
                from models.projects import BoardColumn

                stmt = select(BoardColumn).where(BoardColumn.id.in_(column_ids))
                columns = self.session.scalars(stmt).all()

                board_columns_dto = []
                for col in columns:
                    col_dto = BoardColumnWithTasksDTO(
                        id=col.id,
                        name=col.name,
                        color=col.color or "#cccccc",
                        position=col.position,
                        is_done_column=col.is_done_column,
                        tasks=[]
                    )
                    board_columns_dto.append(col_dto)
            else:
                # Если ничего нет, используем шаблонные колонки
                board_columns_dto = []

        # Загружаем сохраненные колонки в DTO проекта
        project_dto = ProjectWithMembersDTO.model_validate(project)
        project_dto.selected_columns_data = self.project_repo.get_selected_columns(project_id)

        return ProjectBoardDTO(
            project=project_dto,
            columns=board_columns_dto
        )