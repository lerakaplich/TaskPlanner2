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

    # services/projects_service.py

    def get_projects_for_cards(self, search_query: str = "", status_filter: str = "Все", owner_filter: bool = False) -> \
    List[ProjectCardDTO]:
        """
        Получает список проектов, фильтрует их и возвращает в виде списка DTO для карточек.

        Args:
            search_query: строка поиска по названию
            status_filter: фильтр по статусу ("Все", "Активные", "Архив")
            owner_filter: если True, показывать только проекты где текущий пользователь владелец
        """
        # 1. Получаем все проекты
        all_projects = self.project_repo.get_all()
        result = []

        for proj in all_projects:
            # 2. Фильтрация по владельцу
            if owner_filter and proj.owner != self.current_user_id:
                continue

            # 3. Фильтрация по поисковому запросу
            if search_query and search_query.lower() not in proj.name.lower():
                continue

            # 4. Фильтрация по статусу
            if status_filter == "Активные" and proj.is_archived:
                continue
            if status_filter == "Архив" and not proj.is_archived:
                continue

            # 5. Расчет прогресса (Задачи)
            tasks = self.task_repo.get_by_project(proj.id)
            total_tasks = len(tasks)
            done_tasks = len([t for t in tasks if t.column and t.column.is_done_column])

            # 👇 ПОЛУЧАЕМ КОЛИЧЕСТВО УЧАСТНИКОВ И АДМИНОВ
            member_count = len(proj.members) if hasattr(proj, 'members') else 0
            admin_count = len([m for m in proj.members if m.is_admin]) if hasattr(proj, 'members') else 0

            # 👇 ПОЛУЧАЕМ ИМЯ ВЛАДЕЛЬЦА
            owner_name = "Не назначен"
            if proj.owner:
                owner = self.employee_repo.get_by_id(proj.owner)
                if owner:
                    owner_name = f"{owner.last_name} {owner.first_name[0]}."
                    if owner.middle_name:
                        owner_name += f"{owner.middle_name[0]}."

            # 👇 ФОРМАТИРУЕМ ДАТУ СОЗДАНИЯ
            created_at_str = None
            if proj.created_at:
                created_at_str = proj.created_at.strftime("%d.%m.%Y")

            # 6. Сборка DTO
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
                created_at=created_at_str
            )

            result.append(card_dto)

        return result

    def create_new_project(self, raw_data: dict, creator_id: int) -> Optional[ProjectWithMembersDTO]:
        """
        Создает проект 'под ключ': запись в БД, участников и базовые колонки.
        """
        try:
            # 1. Создаем сам проект
            project = self.project_repo.create(
                name=raw_data['name'],
                description=raw_data.get('description', ''),
                owner=creator_id,
                created_by=creator_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                is_archived=not raw_data.get('is_active', True)
            )

            # Flush чтобы получить ID проекта
            self.session.flush()
            print(f"✅ Проект создан в БД, ID: {project.id}")

            # 2. Обработка участников и администраторов
            def to_id_list(val):
                if isinstance(val, str):
                    return [int(i.strip()) for i in val.split(',') if i.strip().isdigit()]
                return val or []

            # Получаем списки из входных данных
            member_ids = to_id_list(raw_data.get('participants_ids'))
            admin_ids = to_id_list(raw_data.get('admins_ids'))

            print(f"📊 member_ids из формы: {member_ids}")
            print(f"📊 admin_ids из формы: {admin_ids}")
            print(f"👤 creator_id: {creator_id}")

            # 👇 ПРОВЕРЯЕМ СУЩЕСТВОВАНИЕ СОТРУДНИКОВ В БД
            from models.employees import ExternalEmployee
            from sqlalchemy import select

            # Проверяем creator
            stmt = select(ExternalEmployee).where(ExternalEmployee.id == creator_id)
            creator_exists = self.session.scalar(stmt) is not None
            print(f"✅ Creator с ID {creator_id} существует в БД: {creator_exists}")

            # Проверяем всех участников
            for emp_id in member_ids:
                stmt = select(ExternalEmployee).where(ExternalEmployee.id == emp_id)
                exists = self.session.scalar(stmt) is not None
                print(f"✅ Участник с ID {emp_id} существует в БД: {exists}")

            # Проверяем всех админов
            for emp_id in admin_ids:
                stmt = select(ExternalEmployee).where(ExternalEmployee.id == emp_id)
                exists = self.session.scalar(stmt) is not None
                print(f"✅ Админ с ID {emp_id} существует в БД: {exists}")

            # Формируем итоговые наборы
            all_members = set(member_ids) | {creator_id}
            all_admins = set(admin_ids) | {creator_id}

            print(f"📊 all_members: {all_members}")
            print(f"📊 all_admins: {all_admins}")

            for emp_id in all_members:
                # 👇 ПРОВЕРЯЕМ КАЖДОГО ПЕРЕД ДОБАВЛЕНИЕМ
                stmt = select(ExternalEmployee).where(ExternalEmployee.id == emp_id)
                employee = self.session.scalar(stmt)
                if not employee:
                    print(f"⚠️ Сотрудник с ID {emp_id} не найден в БД, пропускаем")
                    continue

                self.project_repo.add_member(
                    project_id=project.id,
                    employee_id=emp_id,
                    is_admin=(emp_id in all_admins)
                )
                print(f"✅ Добавлен участник: {employee.last_name} {employee.first_name} (ID: {emp_id})")

            print(f"✅ Добавлено участников")

            # 3. Создание стандартных колонок Канбан-доски
            default_columns = [
                ("К выполнению", 0, False),
                ("В работе", 1, False),
                ("Проверка", 2, False),
                ("Готово", 3, True)
            ]

            for name, pos, is_done in default_columns:
                column = self.project_repo.add_column(
                    project_id=project.id,
                    name=name,
                    position=pos
                )
                # Устанавливаем флаг завершающей колонки
                if is_done:
                    column.is_done_column = True
                    self.session.flush()
            print(f"✅ Созданы стандартные колонки")

            # Фиксируем все изменения
            self.session.commit()
            print(f"✅ Проект успешно сохранен в БД")

            # Возвращаем полные данные созданного проекта
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

            # 1. Обновляем базовые поля
            project.name = dto.name
            project.description = dto.description
            project.is_archived = dto.is_archived
            project.deadline = dto.deadline
            project.updated_at = datetime.now()

            # 2. Получаем текущее состояние из БД
            current_members = {m.employee_id: bool(m.is_admin) for m in project.members}

            # 3. Новое желаемое состояние
            target_members = {emp_id: (emp_id in dto.admin_ids) for emp_id in dto.member_ids}

            # Определяем наборы ID
            current_ids = set(current_members.keys())
            target_ids = set(target_members.keys())

            print(f"📊 Текущие участники: {current_ids}")
            print(f"📊 Новые участники: {target_ids}")
            print(f"📊 Текущие админы: {[id for id, is_admin in current_members.items() if is_admin]}")
            print(f"📊 Новые админы: {dto.admin_ids}")

            # А. Кого удалить
            for emp_id in (current_ids - target_ids):
                print(f"🗑️ Удаляем участника {emp_id}")
                self.project_repo.remove_member(project_id, emp_id)

            # Б. Кого добавить
            for emp_id in (target_ids - current_ids):
                is_admin = target_members[emp_id]
                print(f"➕ Добавляем участника {emp_id}, админ: {is_admin}")
                self.project_repo.add_member(project_id, emp_id, is_admin=is_admin)

            # В. Кому обновить роль
            for emp_id in (current_ids & target_ids):
                if current_members[emp_id] != target_members[emp_id]:
                    print(f"🔄 Обновляем роль участника {emp_id}, админ: {target_members[emp_id]}")
                    self.project_repo.update_member_role(project_id, emp_id, is_admin=target_members[emp_id])

            self.session.commit()
            print(f"✅ Проект {project_id} успешно обновлен")
            return True

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении проекта: {e}")
            import traceback
            traceback.print_exc()
            return False

    # services/projects_service.py

    def get_project_for_edit(self, project_id: int) -> Optional[ProjectWithMembersDTO]:
        """Получает проект для редактирования"""
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return None

        # Преобразуем в DTO
        dto = ProjectWithMembersDTO.model_validate(project)

        # Добавляем списки участников
        dto.member_ids = [m.employee_id for m in project.members]
        dto.admin_ids = [m.employee_id for m in project.members if m.is_admin]

        print(f"✅ Проект загружен из БД: {dto.name} (ID: {dto.id})")
        print(f"   Участников: {len(dto.member_ids)}, Админов: {len(dto.admin_ids)}")

        return dto

    # services/projects_service.py

    def get_project_board_data(self, project_id: int) -> Optional[ProjectBoardDTO]:
        """Собирает полное DTO доски для UI"""
        # 1. Получаем проект
        project = self.project_repo.get_by_id(project_id)
        if not project:
            return None

        board_columns_dto = []

        # 2. Перебираем колонки проекта
        sorted_columns = sorted(project.columns, key=lambda x: x.position)

        for col in sorted_columns:
            # Получаем задачи в колонке
            tasks = self.task_repo.get_by_column(col.id)

            task_cards = []
            for t in tasks:
                # Получаем имя исполнителя
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

            # Собираем DTO колонки
            col_dto = BoardColumnWithTasksDTO(
                id=col.id,
                name=col.name,
                color=col.color or "#cccccc",
                position=col.position,
                is_done_column=col.is_done_column,
                tasks=task_cards
            )
            board_columns_dto.append(col_dto)

        return ProjectBoardDTO(
            project=ProjectWithMembersDTO.model_validate(project),
            columns=board_columns_dto
        )