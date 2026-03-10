# Логика создания проекта (включая авто-создание колонок "To Do", "Done").
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from database import get_tasks_session
from models.projects import Project
from models.schemas.projects_dto import ProjectWithMembersDTO, ProjectCardDTO, ProjectBoardDTO, BoardColumnWithTasksDTO
from models.schemas.tasks_dto import TaskCardDTO, TaskPriority
from repositories.project_repo import ProjectRepo
from repositories.task_repo import TaskRepo
from repositories.external_employee_repo import ExternalEmployeeRepo


class ProjectsService:
    def __init__(self, session=None):
        self.session = session or get_tasks_session()
        self.current_user_id = None  # 👈 ДОБАВЛЯЕМ
        self.project_repo = ProjectRepo(session)
        self.task_repo = TaskRepo(session)
        self.employee_repo = ExternalEmployeeRepo(session)

    def set_current_user_id(self, user_id):  # 👈 ДОБАВЛЯЕМ
        """Устанавливает ID текущего пользователя"""
        self.current_user_id = user_id

    def set_current_user(self, user):
        self.current_user = user


    def get_projects_for_cards(self, search_query: str = "", status_filter: str = "Все") -> List[ProjectCardDTO]:
        """
        Получает список проектов, фильтрует их и возвращает в виде списка DTO для карточек.
        """
        # 1. Получаем все проекты (в идеале фильтрацию по имени и архиву лучше делать на уровне SQL)
        all_projects = self.project_repo.get_all()
        result = []

        for proj in all_projects:
            # 2. Фильтрация по поисковому запросу
            if search_query and search_query.lower() not in proj.name.lower():
                continue

            # 3. Фильтрация по статусу
            if status_filter == "Активные" and proj.is_archived:
                continue
            if status_filter == "Архив" and not proj.is_archived:
                continue

            # 4. Расчет прогресса (Задачи)
            tasks = self.task_repo.get_by_project(proj.id)
            total_tasks = len(tasks)
            # Считаем выполненными задачи, которые находятся в колонках с флагом is_done_column
            done_tasks = len([t for t in tasks if t.column and t.column.is_done_column])

            # 5. Сборка DTO
            # Используем ProjectCardDTO, который мы определили ранее
            card_dto = ProjectCardDTO(
                id=proj.id,
                name=proj.name,
                description=proj.description or "",
                tasks_total=total_tasks,
                tasks_done=done_tasks,
                deadline=proj.deadline,  # Передаем объект time или datetime
                is_archived=proj.is_archived
            )

            result.append(card_dto)

        return result

    def create_new_project(self, raw_data: dict, creator_id: int) -> Optional[ProjectWithMembersDTO]:
        """
        Создает проект 'под ключ': запись в БД, участников и базовые колонки.
        """
        try:
            # 1. Создаем сам проект
            # Используем creator_id для полей владельца и создателя
            project = self.project_repo.create(
                name=raw_data['name'],
                description=raw_data.get('description'),
                owner=creator_id,
                created_by=creator_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                is_archived=not raw_data.get('is_active', True)
            )
            # Flush позволяет БД сгенерировать ID проекта, но не фиксирует транзакцию
            self.session.flush()

            # 2. Обработка участников и администраторов
            def to_id_list(val):
                if isinstance(val, str):
                    return [int(i.strip()) for i in val.split(',') if i.strip().isdigit()]
                return val or []

            # Получаем списки из входных данных
            member_ids = to_id_list(raw_data.get('participants_ids'))
            admin_ids = to_id_list(raw_data.get('admins_ids'))

            # Формируем итоговые наборы (Set убирает дубликаты)
            # Гарантируем, что создатель всегда в обоих списках
            all_members = set(member_ids) | {creator_id}
            all_admins = set(admin_ids) | {creator_id}

            for emp_id in all_members:
                self.project_repo.add_member(
                    project_id=project.id,
                    employee_id=emp_id,
                    is_admin=(emp_id in all_admins)
                )

            # 3. Создание стандартных колонок Канбан-доски
            # Это избавляет пользователя от рутины при каждом создании проекта
            default_columns = [
                ("К выполнению", 0, False),
                ("В работе", 1, False),
                ("Проверка", 2, False),
                ("Готово", 3, True)  # Флаг завершающей колонки
            ]

            for name, pos, is_done in default_columns:
                self.project_repo.add_column(
                    project_id=project.id,
                    name=name,
                    position=pos,
                    # Убедись, что метод в Repo принимает этот аргумент
                    # is_done_column=is_done
                )

            # Фиксируем все изменения в БД одной транзакцией
            self.session.commit()

            # Возвращаем полные данные созданного проекта через DTO
            return self.get_project_for_edit(project.id)

        except Exception as e:
            # Если хоть один шаг (например, добавление колонки) упал —
            # отменяем всё создание проекта целиком
            self.session.rollback()
            print(f"Критическая ошибка сервиса при создании проекта: {e}")
            return None

    def update_project(self, project_id: int, dto: ProjectWithMembersDTO) -> bool:
        try:
            project = self.project_repo.get_by_id(project_id)
            if not project:
                return False

            # 1. Обновляем базовые поля
            project.name = dto.name
            project.description = dto.description
            project.is_archived = dto.is_archived
            project.deadline = dto.deadline

            # 2. Получаем текущее состояние из БД (словарь {id: is_admin})
            current_members = {m.employee_id: bool(m.is_admin) for m in project.members}

            # 3. Новое желаемое состояние из DTO
            target_members = {emp_id: (emp_id in dto.admin_ids) for emp_id in dto.member_ids}

            # Определяем наборы ID
            current_ids = set(current_members.keys())
            target_ids = set(target_members.keys())

            # А. Кого удалить
            for emp_id in (current_ids - target_ids):
                self.project_repo.remove_member(project_id, emp_id)

            # Б. Кого добавить
            for emp_id in (target_ids - current_ids):
                self.project_repo.add_member(project_id, emp_id, is_admin=target_members[emp_id])

            # В. Кому обновить роль
            for emp_id in (current_ids & target_ids):
                if current_members[emp_id] != target_members[emp_id]:
                    self.project_repo.update_member_role(project_id, emp_id, is_admin=target_members[emp_id])

            self.session.commit()
            return True

        except Exception as e:
            self.session.rollback()
            print(f"Error updating project: {e}")
            return False

    def get_project_for_edit(self, project_id: int) -> Optional[ProjectWithMembersDTO]:
        # Обязательно используем joinedload в репозитории для project.members
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return None

        dto = ProjectWithMembersDTO.model_validate(project)
        dto.member_ids = [m.employee_id for m in project.members]
        dto.admin_ids = [m.employee_id for m in project.members if m.is_admin]

        return dto

    def get_project_board_data(self, project_id: int) -> Optional[ProjectBoardDTO]:
        """Собирает полное DTO доски для UI"""
        # 1. Получаем проект (используем существующий метод Repo)
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return None

        board_columns_dto = []

        # 2. Перебираем колонки проекта
        # (project.columns подгружаются автоматически, если в модели прописан relationship)
        sorted_columns = sorted(project.columns, key=lambda x: x.position)

        for col in sorted_columns:
            # Используем НОВЫЙ метод Repo
            tasks = self.task_repo.get_by_column(col.id)

            task_cards = []
            for t in tasks:
                # Используем НОВЫЙ метод Repo для имени
                assigned_name = self.employee_repo.get_full_name(t.assigned_to) if t.assigned_to else "Не назначен"

                is_overdue = (t.deadline < datetime.now()) if t.deadline else False

                task_cards.append(TaskCardDTO(
                    id=t.id,
                    title=t.title,
                    # Приводим значение из БД к строке или объекту нашего Enum
                    priority=TaskPriority(t.priority.value if hasattr(t.priority, 'value') else t.priority),
                    deadline=t.deadline,
                    assigned_to_name=assigned_name,
                    is_overdue=is_overdue
                ))

            # Собираем DTO колонки с вложенными задачами
            col_dto = BoardColumnWithTasksDTO(
                id=col.id,
                name=col.name,
                color="#cccccc",  # Можно добавить поле color в модель Column позже
                position=col.position,
                is_done_column=col.is_done_column,
                tasks=task_cards
            )
            board_columns_dto.append(col_dto)

        return ProjectBoardDTO(
            project=ProjectWithMembersDTO.model_validate(project),
            columns=board_columns_dto
        )