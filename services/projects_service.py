# Логика создания проекта (включая авто-создание колонок "To Do", "Done").
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from database import get_tasks_session
from models.projects import Project
from models.schemas.projects_dto import ProjectWithMembersDTO, ProjectCardDTO, ProjectBoardDTO, BoardColumnWithTasksDTO
from models.schemas.tasks_dto import TaskCardDTO, TaskPriority
from repositories.chat_repo import ChatRepo
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
        # 👇 Добавляем репозиторий чатов
        self.chat_repo = ChatRepo(self.session)

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
        Создает проект 'под ключ': запись в БД, участников, колонки и связанный чат.
        """
        try:
            # 1. Создание базовой записи проекта
            project = self.project_repo.create(
                name=raw_data['name'],
                description=raw_data.get('description', ''),
                owner=creator_id,
                created_by=creator_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                is_archived=not raw_data.get('is_active', True)
            )
            self.session.flush()  # Получаем ID проекта

            # 2. Обработка участников (логика вынесена в отдельный метод)
            all_members, all_admins = self._prepare_participant_sets(raw_data, creator_id)
            self._add_project_members(project.id, all_members, all_admins)

            # 3. Создание стандартных колонок Канбан-доски
            self._create_default_columns(project.id)

            # 4. Создание связанного чата через ChatRepo
            self._create_project_chat(project, all_members)

            # Финальная фиксация всей транзакции
            self.session.commit()
            print(f"✅ Проект '{project.name}' (ID: {project.id}) успешно создан со всеми связями.")

            return self.get_project_for_edit(project.id)

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании проекта: {e}")
            import traceback
            traceback.print_exc()
            return None

    # --- Вспомогательные методы для разбиения логики ---

    def _prepare_participant_sets(self, raw_data, creator_id):
        """Парсит входящие данные и формирует наборы участников и админов"""

        def to_id_list(val):
            if isinstance(val, str):
                return [int(i.strip()) for i in val.split(',') if i.strip().isdigit()]
            return val or []

        member_ids = to_id_list(raw_data.get('participants_ids'))
        admin_ids = to_id_list(raw_data.get('admins_ids'))

        # Объединяем с создателем (он всегда участник и админ)
        all_members = set(member_ids) | {creator_id}
        all_admins = set(admin_ids) | {creator_id}
        return all_members, all_admins

    def _add_project_members(self, project_id, all_members, all_admins):
        """Проверяет существование сотрудников и добавляет их в проект"""
        from models.employees import ExternalEmployee
        from sqlalchemy import select

        for emp_id in all_members:
            stmt = select(ExternalEmployee).where(ExternalEmployee.id == emp_id)
            employee = self.session.scalar(stmt)

            if employee:
                self.project_repo.add_member(
                    project_id=project_id,
                    employee_id=emp_id,
                    is_admin=(emp_id in all_admins)
                )
            else:
                print(f"⚠️ Сотрудник ID {emp_id} не найден, пропущен.")

    def _create_default_columns(self, project_id):
        """Генерирует стандартный набор колонок для нового проекта"""
        default_columns = [
            ("К выполнению", 0, False),
            ("В работе", 1, False),
            ("Проверка", 2, False),
            ("Готово", 3, True)
        ]
        for name, pos, is_done in default_columns:
            column = self.project_repo.add_column(project_id, name, pos)
            if is_done:
                column.is_done_column = True
                self.session.flush()

    def _create_project_chat(self, project, participants):
        """Создает чат проекта и добавляет в него всех участников через ChatRepo"""
        try:
            # Создаем сам чат
            new_chat = self.chat_repo.create_chat(
                title=f"Проект: {project.name}",
                chat_type="project",
                project_id=project.id
            )

            # Добавляем участников в чат
            for emp_id in participants:
                self.chat_repo.add_participant(new_chat.id, emp_id)

            print(f"💬 Чат проекта создан (ID чата: {new_chat.id})")
        except Exception as e:
            # Ошибка в чате не должна отменять создание проекта,
            # но в данном случае всё в одной транзакции
            print(f"⚠️ Не удалось создать чат для проекта: {e}")
            raise e

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