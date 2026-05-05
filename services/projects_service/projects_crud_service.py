# services/projects_service/projects_crud_service.py

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from database import get_employees_session
from models.schemas.projects_dto import ProjectWithMembersDTO, ProjectCardDTO
from repositories.project_repo import ProjectRepo
from repositories.employee_repo import EmployeeRepo


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
            return self.get_project_for_edit(project.id)

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании проекта: {e}")
            return None

    def update_project(self, project_id: int, dto: ProjectWithMembersDTO) -> bool:
        """Обновить проект"""
        try:
            project = self.project_repo.get_by_id(project_id)
            if not project:
                return False

            project.name = dto.name
            project.description = dto.description
            project.is_archived = dto.is_archived
            project.deadline = dto.deadline
            project.updated_at = datetime.now()
            project.manager_id = dto.manager_id

            if hasattr(dto, 'selected_columns_data') and dto.selected_columns_data:
                column_ids = [col.get('id') for col in dto.selected_columns_data if col.get('id')]
                if column_ids:
                    self.project_repo.save_selected_column_ids(project_id, column_ids)

            self.session.commit()
            return True

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении проекта: {e}")
            return False

    def get_projects_for_cards(self, search_query: str = "", status_filter: str = "Все",
                               owner_filter: bool = False) -> List[ProjectCardDTO]:
        """Получить проекты для карточек"""
        try:
            all_projects = self.project_repo.get_all(exclude_archived=True)
            result = []

            for proj in all_projects:
                if owner_filter and proj.owner != self.current_user_id:
                    continue
                if search_query and search_query.lower() not in proj.name.lower():
                    continue

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