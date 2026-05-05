# services/projects_service.py
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import text, select
from database import get_tasks_session, get_employees_session
from models.projects import BoardColumn
from models.schemas.projects_dto import ProjectWithMembersDTO, ProjectCardDTO, ProjectBoardDTO, BoardColumnWithTasksDTO
from models.schemas.tasks_dto import TaskCardDTO, TaskPriority
from repositories.employee_repo import EmployeeRepo  # ← ИСПРАВЛЕНО (было external_employee_repo)
from repositories.project_repo import ProjectRepo
from repositories.task_repo import TaskRepo
from services.column_service import ColumnService
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
                        owner = self.employee_repo.get_by_id(proj.owner)
                        if owner:
                            owner_name = f"{owner.last_name} {owner.first_name[0]}."
                            if owner.middle_name:
                                owner_name += f"{owner.middle_name[0]}."

                    # ← ДОБАВЛЯЕМ ПОЛУЧЕНИЕ ИМЕНИ КУРАТОРА
                    manager_name = None
                    if proj.manager_id:
                        manager = self.employee_repo.get_by_id(proj.manager_id)
                        if manager:
                            manager_name = f"{manager.last_name} {manager.first_name[0]}."
                            if manager.middle_name:
                                manager_name += f"{manager.middle_name[0]}."

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
                        columns_count=columns_count,
                        manager_name=manager_name  # ← ДОБАВЛЯЕМ
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

    def load_employee_selector_data(self) -> Dict:
        """
        Загружает все данные для диалога выбора сотрудников:
        - список сотрудников
        - подразделения
        - отделы
        """
        from models.employees import Employee, Division, Department
        from sqlalchemy import select

        result = {
            'employees': [],
            'divisions': [],
            'departments': [],
            'roles': {},  # останется пустым, так как данные в другой БД
            'usage_count': {}  # останется пустым
        }

        # 1. Загружаем подразделения
        try:
            stmt = select(Division.name).where(Division.name.isnot(None)).order_by(Division.name)
            divisions = self.employees_session.scalars(stmt).all()
            result['divisions'] = list(divisions)
            print(f"✅ Загружено подразделений: {len(result['divisions'])}")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки подразделений: {e}")

        # 2. Загружаем отделы
        try:
            stmt = select(Department.name).where(Department.name.isnot(None)).order_by(Department.name)
            departments = self.employees_session.scalars(stmt).all()
            result['departments'] = list(departments)
            print(f"✅ Загружено отделов: {len(result['departments'])}")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки отделов: {e}")

        # 3. Загружаем сотрудников (просто всех, без фильтрации)
        try:
            stmt = select(Employee).order_by(Employee.last_name)
            employees = self.employees_session.scalars(stmt).all()

            for emp in employees:
                full_name = self._get_employee_full_name(emp)
                if full_name:
                    result['employees'].append({
                        'id': emp.id,
                        'full_name': full_name,
                        'last_name': emp.last_name or '',
                        'first_name': emp.first_name or '',
                        'middle_name': emp.middle_name or '',
                        'position': emp.position or '',
                        'phone': emp.phone_number or '',
                        'email': emp.email or '',
                        'is_admin': False,  # не можем определить
                        'usage_count': 0,
                        'department_id': emp.department_id,
                        'division_id': emp.division_id,
                        'role': 'user'  # по умолчанию
                    })
            print(f"✅ Загружено сотрудников: {len(result['employees'])}")
        except Exception as e:
            print(f"❌ Ошибка загрузки сотрудников: {e}")

        return result

    def filter_employees_by_search(self, employees: List[Dict], search_text: str) -> List[Dict]:
        """Фильтрует сотрудников по поисковому запросу"""
        if not search_text:
            return employees.copy()

        search_lower = search_text.lower().strip()
        filtered = []
        for emp in employees:
            if search_lower in emp['full_name'].lower():
                filtered.append(emp)
        return filtered

    def sort_employees_for_selector(self, employees: List[Dict], selected_ids: set) -> List[Dict]:
        """
        Сортирует сотрудников для селектора:
        1. Выбранные сотрудники (всегда вверху)
        2. Остальные сортируются по частоте использования
        """

        def get_sort_key(emp):
            is_selected = emp['id'] in selected_ids
            return (0 if is_selected else 1, -emp.get('usage_count', 0))

        return sorted(employees, key=get_sort_key)

    def archive_project(self, project_id: int) -> bool:
        try:
            project = self.project_repo.get_by_id(project_id)
            if not project:
                return False

            # Архивируем проект
            project.is_archived = True
            project.updated_at = datetime.now()

            # Архивируем все задачи проекта
            tasks = self.task_repo.get_by_project(project_id)
            archived_tasks_count = 0
            for task in tasks:
                if not task.is_archived:
                    task.is_archived = True
                    task.archived_at = datetime.now()
                    archived_tasks_count += 1

            self.session.commit()
            print(f"✅ Проект {project_id} архивирован вместе с {archived_tasks_count} задачами")
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
                is_archived=not raw_data.get('is_active', True),
                manager_id=raw_data.get('manager_id')
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
        dto.manager_id = project.manager_id

        # Получаем имя куратора
        if project.manager_id:
            manager = self.employee_repo.get_by_id(project.manager_id)
            if manager:
                dto.manager_name = self._get_employee_full_name(manager)

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
            project.manager_id = dto.manager_id

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

    def get_template_columns_for_selector(self) -> List[Dict]:
        """Возвращает шаблонные колонки для диалога выбора с дополнительными полями"""
        try:
            stmt = select(BoardColumn).where(
                BoardColumn.is_template == True
            ).order_by(BoardColumn.template_order)
            columns = self.session.scalars(stmt).all()

            result = []
            for col in columns:
                result.append({
                    'id': col.id,
                    'name': col.name,
                    'col_key': col.name.lower().replace(' ', '_'),
                    'color': col.color,
                    'position': col.template_order or col.position,
                    'is_done_column': col.is_done_column,
                    'is_template': True,
                    'description': getattr(col, 'description', '')
                })
            return result
        except Exception as e:
            print(f"❌ Ошибка при загрузке колонок для селектора: {e}")
            return []

    def filter_columns_by_search(self, columns: List[Dict], search_text: str) -> List[Dict]:
        """Фильтрует колонки по поисковому запросу"""
        if not search_text:
            return columns.copy()

        search_lower = search_text.lower().strip()
        filtered = []
        for col in columns:
            col_name = col.get('name', '').lower()
            col_key = col.get('col_key', '').lower()
            if search_lower in col_name or search_lower in col_key:
                filtered.append(col)
        return filtered

    def get_selected_columns_by_keys(self, all_columns: List[Dict], selected_keys: List[str]) -> List[Dict]:
        """Возвращает данные выбранных колонок по ключам"""
        selected = []
        for col in all_columns:
            col_key = col.get('col_key', col.get('name', '').lower().replace(' ', '_'))
            if col_key in selected_keys:
                col_copy = col.copy()
                if 'col_key' not in col_copy:
                    col_copy['col_key'] = col_key
                selected.append(col_copy)
        return selected

    def load_template_columns(self) -> List[Dict]:
        """Загружает шаблонные колонки из БД"""
        try:
            stmt = select(BoardColumn).where(
                BoardColumn.is_template == True
            ).order_by(BoardColumn.template_order)
            columns = self.session.scalars(stmt).all()

            return [{
                'id': col.id,
                'name': col.name,
                'col_key': col.name.lower().replace(' ', '_'),
                'color': col.color,
                'position': col.template_order or col.position,
                'is_done_column': col.is_done_column,
                'is_template': True
            } for col in columns]
        except Exception as e:
            print(f"❌ Ошибка при загрузке колонок: {e}")
            return []

    def get_default_project_data(self, creator_id: int) -> Dict:
        """
        Возвращает данные для нового проекта по умолчанию
        """
        return {
            'id': None,
            'name': '',
            'description': '',
            'is_active': True,
            'creator_id': creator_id,
            'owner_id': creator_id,
            'created_date': datetime.now().strftime("%d.%m.%Y"),
            'selected_columns_data': [],
            'selected_columns_keys': [],
            'participants_ids': str(creator_id),
            'admins_ids': str(creator_id),
            'member_ids': [creator_id],
            'admin_ids': [creator_id],
            'manager_id': None
        }

    def validate_project_data(self, data: Dict) -> Optional[str]:
        """
        Валидация данных проекта
        Возвращает строку с ошибкой или None если всё ок
        """
        if not data.get('name', '').strip():
            return "Введите название проекта"

        selected_columns = data.get('selected_columns_data', [])
        if not selected_columns:
            return "Выберите хотя бы одну колонку для отображения в проекте"

        return None

    def get_project_columns(self, project_id: int) -> List[Dict]:
        """
        Возвращает колонки проекта по сохраненным ID
        """
        from sqlalchemy import select
        from models.projects import BoardColumn

        column_ids = self.project_repo.get_selected_column_ids(project_id)
        result = []

        if column_ids:
            stmt = select(BoardColumn).where(BoardColumn.id.in_(column_ids))
            columns = self.session.scalars(stmt).all()

            for col in columns:
                result.append({
                    'id': col.id,
                    'name': col.name,
                    'color': col.color,
                    'position': col.template_order if col.template_order is not None else col.position,
                    'is_done': col.is_done_column
                })
            print(f"📋 Загружено колонок проекта: {len(result)}")
        else:
            # Если нет сохраненных, берем все шаблонные
            stmt = select(BoardColumn).where(BoardColumn.is_template == True)
            columns = self.session.scalars(stmt).all()
            for col in columns:
                result.append({
                    'id': col.id,
                    'name': col.name,
                    'color': col.color,
                    'position': col.template_order if col.template_order is not None else col.position,
                    'is_done': col.is_done_column
                })

        return result

    def get_project_tasks_for_view(self, project_id: int, include_archived: bool = False) -> List[Dict]:
        """
        Возвращает задачи проекта в виде словарей с полной информацией для отображения
        """
        from repositories.task_repo import TaskRepo
        from database import get_employees_session
        from repositories.employee_repo import EmployeeRepo
        from models.schemas.tasks_dto import TaskPriority
        from datetime import datetime

        task_repo = TaskRepo(self.session)
        tasks = task_repo.get_by_project(project_id, load_column=True, include_archived=include_archived)

        result = []
        for task in tasks:
            # Получаем имя исполнителя
            assignee_name = None
            if task.assigned_to:
                emp_session = get_employees_session()
                if emp_session:
                    emp_repo = EmployeeRepo(emp_session)
                    assignee_name = emp_repo.get_full_name(task.assigned_to)
                    emp_session.close()

            # Получаем имя автора
            author_name = None
            if task.created_by:
                emp_session = get_employees_session()
                if emp_session:
                    emp_repo = EmployeeRepo(emp_session)
                    author_name = emp_repo.get_full_name(task.created_by)
                    emp_session.close()

            priority_map = {
                TaskPriority.low: ("Низкий", "#4CAF50"),
                TaskPriority.medium: ("Средний", "#FFA726"),
                TaskPriority.high: ("Высокий", "#D22730"),
                TaskPriority.critical: ("Критический", "#D22730")
            }

            priority_text, priority_color = priority_map.get(
                task.priority,
                ("Средний", "#FFA726")
            )

            deadline_text = ""
            deadline_color = "#666"
            deadline_obj = None
            if task.deadline:
                deadline_text = task.deadline.strftime("%d.%m.%Y")
                deadline_obj = task.deadline
                if task.deadline.date() < datetime.now().date():
                    deadline_color = "#D22730"

            created_text = task.created_at.strftime("%d.%m.%Y") if task.created_at else ""
            updated_text = task.updated_at.strftime("%d.%m.%Y") if task.updated_at else ""

            tags = []
            if hasattr(task, 'tags') and task.tags:
                for tag_obj in task.tags:
                    if hasattr(tag_obj, 'name'):
                        tags.append(tag_obj.name)
                    elif isinstance(tag_obj, str):
                        tags.append(tag_obj)
                    else:
                        tags.append(str(tag_obj))

            archived_at = ""
            if task.is_archived and task.archived_at:
                archived_at = task.archived_at.strftime("%d.%m.%Y")

            result.append({
                "id": task.id,
                "title": task.title,
                "description": task.description or "",
                "status": task.column.name if task.column else None,
                "column_id": task.column_id,
                "priority": task.priority.value,
                "priority_text": priority_text,
                "priority_color": priority_color,
                "deadline": deadline_text,
                "deadline_obj": deadline_obj,
                "deadline_color": deadline_color,
                "assignee_name": assignee_name or "Не назначен",
                "assigned_to": task.assigned_to,
                "created_by": task.created_by,
                "author_text": author_name or "Неизвестен",
                "created_text": created_text,
                "updated_text": updated_text,
                "executor_text": assignee_name or "Не назначен",
                "completed": task.is_archived if hasattr(task, 'is_archived') else False,
                "difficulty": task.difficulty if hasattr(task, 'difficulty') else 0,
                "tags": tags,
                "project_id": task.project_id,
                "project_name": self.get_project_name(project_id),
                "is_archived": task.is_archived if hasattr(task, 'is_archived') else False,
                "archived_at": archived_at
            })

        return result

    def get_project_name(self, project_id: int) -> str:
        """Возвращает название проекта по ID"""
        project = self.project_repo.get_by_id(project_id)
        return project.name if project else f"Проект #{project_id}"

    def restore_task(self, task_id: int) -> bool:
        """Восстанавливает задачу из архива"""
        from repositories.task_repo import TaskRepo

        task_repo = TaskRepo(self.session)
        task = task_repo.get_by_id(task_id)
        if task:
            task.is_archived = False
            task.archived_at = None
            self.session.commit()
            return True
        return False

    def delete_task_permanently(self, task_id: int) -> bool:
        """Полное удаление задачи"""
        from repositories.task_repo import TaskRepo

        task_repo = TaskRepo(self.session)
        result = task_repo.hard_delete(task_id)
        self.session.commit()
        return result

    def prepare_project_data_for_creation(self, raw_data: Dict, creator_id: int) -> Dict:
        """
        Подготавливает данные проекта для создания
        """
        prepared = {
            'name': raw_data.get('name', '').strip(),
            'description': raw_data.get('description', ''),
            'is_active': raw_data.get('is_active', True),
            'manager_id': raw_data.get('manager_id'),
            'selected_columns_data': raw_data.get('selected_columns_data', []),
            'selected_columns_keys': raw_data.get('selected_columns', []),
        }

        # Обработка участников и администраторов
        participants_ids = raw_data.get('participants_ids', '')
        admins_ids = raw_data.get('admins_ids', '')

        if isinstance(participants_ids, list):
            participants_ids = ','.join(str(id) for id in participants_ids)
        if isinstance(admins_ids, list):
            admins_ids = ','.join(str(id) for id in admins_ids)

        prepared['participants_ids'] = participants_ids
        prepared['admins_ids'] = admins_ids

        # Добавляем создателя как участника
        participant_list = [str(creator_id)]
        if participants_ids:
            participant_list.extend([p for p in participants_ids.split(',') if p and p != str(creator_id)])
        prepared['participants_ids'] = ','.join(participant_list)

        # Добавляем создателя как администратора
        admin_list = [str(creator_id)]
        if admins_ids:
            admin_list.extend([a for a in admins_ids.split(',') if a and a != str(creator_id)])
        prepared['admins_ids'] = ','.join(admin_list)

        return prepared

    def prepare_edit_dialog_data(self, project_dto: ProjectWithMembersDTO) -> Dict:
        """
        Подготавливает данные для диалога редактирования проекта
        """
        from database import get_employees_session
        from models.employees import Employee
        from sqlalchemy import select

        result = {
            'id': project_dto.id,
            'name': project_dto.name,
            'description': project_dto.description,
            'is_active': not project_dto.is_archived,
            'created_date': project_dto.created_at.strftime('%d.%m.%Y') if project_dto.created_at else '',
            'member_ids': project_dto.member_ids or [],
            'admin_ids': project_dto.admin_ids or [],
            'selected_columns_data': project_dto.selected_columns_data or [],
            'selected_columns_keys': [col.get('col_key', '') for col in (project_dto.selected_columns_data or [])],
            'manager_id': project_dto.manager_id,
            'manager_name': project_dto.manager_name,
            'participants': [],
            'admins': []
        }

        # Загружаем полные данные участников
        if result['member_ids']:
            emp_session = get_employees_session()
            if emp_session:
                stmt = select(Employee).where(Employee.id.in_(result['member_ids']))
                employees = emp_session.scalars(stmt).all()
                for emp in employees:
                    result['participants'].append({
                        'id': emp.id,
                        'last_name': emp.last_name,
                        'first_name': emp.first_name,
                        'middle_name': emp.middle_name or '',
                        'position': emp.position or 'Сотрудник',
                        'phone': emp.phone_number or '',
                        'email': emp.email or ''
                    })
                emp_session.close()

        # Загружаем полные данные администраторов
        if result['admin_ids']:
            emp_session = get_employees_session()
            if emp_session:
                stmt = select(Employee).where(Employee.id.in_(result['admin_ids']))
                employees = emp_session.scalars(stmt).all()
                for emp in employees:
                    result['admins'].append({
                        'id': emp.id,
                        'last_name': emp.last_name,
                        'first_name': emp.first_name,
                        'middle_name': emp.middle_name or '',
                        'position': emp.position or 'Сотрудник',
                        'phone': emp.phone_number or '',
                        'email': emp.email or ''
                    })
                emp_session.close()

        return result

    def compare_project_changes(self, original_data: Dict, current_data: Dict) -> bool:
        """
        Сравнивает исходные и текущие данные проекта
        Возвращает True если есть изменения
        """
        # Сравниваем основные поля
        if original_data.get('name') != current_data.get('name'):
            return True
        if original_data.get('description') != current_data.get('description'):
            return True
        if original_data.get('is_active') != current_data.get('is_active'):
            return True
        if original_data.get('manager_id') != current_data.get('manager_id'):
            return True

        # Сравниваем выбранные колонки
        original_columns = original_data.get('selected_columns_data', [])
        current_columns = current_data.get('selected_columns_data', [])

        if len(original_columns) != len(current_columns):
            return True

        original_col_ids = set([col.get('id') for col in original_columns if col.get('id')])
        current_col_ids = set([col.get('id') for col in current_columns if col.get('id')])
        if original_col_ids != current_col_ids:
            return True

        # Сравниваем участников
        original_participants = self._extract_employee_ids(original_data.get('participants', []))
        current_participants = self._extract_employee_ids(current_data.get('participants', []))
        if set(original_participants) != set(current_participants):
            return True

        # Сравниваем администраторов
        original_admins = self._extract_employee_ids(original_data.get('admins', []))
        current_admins = self._extract_employee_ids(current_data.get('admins', []))
        if set(original_admins) != set(current_admins):
            return True

        return False

    def _extract_employee_ids(self, data) -> List[int]:
        """Извлекает ID сотрудников из данных"""
        if isinstance(data, str):
            return [int(id.strip()) for id in data.split(',') if id.strip()]
        elif isinstance(data, list):
            ids = []
            for item in data:
                if isinstance(item, dict):
                    ids.append(item.get('id'))
                elif isinstance(item, int):
                    ids.append(item)
            return [id for id in ids if id]
        return []

    def get_user_chats(self, user_id: int) -> List:
        """Получает чаты пользователя"""
        from services.chat_service import ChatService
        from database import get_tasks_session

        chat_session = get_tasks_session()
        if chat_session is None:
            print("⚠️ Нет подключения к БД чатов")
            return []

        try:
            chat_service = ChatService(chat_session)
            return chat_service.get_user_chats(user_id)
        finally:
            chat_session.close()

    def ensure_admins_in_participants(self, participants: List[Dict], admins: List[Dict]) -> List[Dict]:
        """
        Убеждается, что администраторы также являются участниками
        Возвращает обновленный список участников
        """
        admin_ids = set()
        for admin in admins:
            if isinstance(admin, dict):
                admin_ids.add(admin.get('id'))
            else:
                admin_ids.add(admin)

        participant_ids = set()
        for participant in participants:
            if isinstance(participant, dict):
                participant_ids.add(participant.get('id'))
            else:
                participant_ids.add(participant)

        # Добавляем администраторов в участники, если их там нет
        result = list(participants)
        for admin_id in admin_ids:
            if admin_id not in participant_ids:
                result.append({
                    'id': admin_id,
                    'last_name': f"User{admin_id}",
                    'first_name': f"User{admin_id}",
                    'position': 'Сотрудник'
                })

        return result

    def update_project_from_dialog(self, project_id: int, dialog_data: Dict) -> ProjectWithMembersDTO:
        """
        Обновляет DTO проекта данными из диалога
        """
        # Получаем существующий DTO
        project_dto = self.get_project_for_edit(project_id)
        if not project_dto:
            return None

        # Обновляем поля
        project_dto.name = dialog_data.get('name', '')
        project_dto.description = dialog_data.get('description', '')
        project_dto.is_archived = not dialog_data.get('is_active', True)
        project_dto.selected_columns_data = dialog_data.get('selected_columns_data', [])
        project_dto.manager_id = dialog_data.get('manager_id')

        # Обновляем участников
        def extract_ids(data):
            if isinstance(data, str):
                return [int(i.strip()) for i in data.split(',') if i.strip().isdigit()]
            elif isinstance(data, list):
                ids = []
                for item in data:
                    if isinstance(item, dict):
                        ids.append(item.get('id'))
                    elif isinstance(item, int):
                        ids.append(item)
                return [id for id in ids if id]
            return []

        project_dto.member_ids = extract_ids(dialog_data.get('participants_ids', []))
        project_dto.admin_ids = extract_ids(dialog_data.get('admins_ids', []))

        return project_dto

    def load_employees_for_selector(self) -> List[Dict]:
        """Загружает список сотрудников для выбора"""
        from models.employees import Employee
        from sqlalchemy import select

        # Просто загружаем всех сотрудников
        stmt = select(Employee).order_by(Employee.last_name)
        employees = self.employees_session.scalars(stmt).all()

        result = []
        for emp in employees:
            result.append({
                'id': emp.id,
                'last_name': emp.last_name,
                'first_name': emp.first_name,
                'middle_name': emp.middle_name or '',
                'position': emp.position or 'Сотрудник',
                'phone': emp.phone_number or '',
                'department_id': emp.department_id,
                'division_id': emp.division_id
            })
        return result

    def load_employees_for_manager_combo(self) -> List[Dict]:
        """Загружает сотрудников для комбобокса куратора"""
        from models.employees import Employee
        from sqlalchemy import select

        # Просто загружаем всех сотрудников из employees БД
        # Без JOIN с employees_data, так как она в другой базе
        stmt = select(Employee).order_by(Employee.last_name)
        employees = self.employees_session.scalars(stmt).all()

        result = []
        for emp in employees:
            full_name = f"{emp.last_name} {emp.first_name}"
            if emp.middle_name:
                full_name += f" {emp.middle_name}"
            result.append({
                'id': emp.id,
                'display_name': full_name
            })
        return result

    def get_user_by_id(self, user_id: int) -> Dict:
        """Получает данные пользователя по ID"""
        from models.employees import Employee, EmployeeData
        from sqlalchemy import select
        from database import get_employees_session, get_tasks_session

        emp_session = get_employees_session()
        if emp_session is None:
            return {
                'id': user_id,
                'last_name': 'Неизвестен',
                'first_name': '',
                'middle_name': '',
                'rights': 'user'
            }

        try:
            stmt = select(Employee).where(Employee.id == user_id)
            user = emp_session.scalar(stmt)

            if not user:
                return {
                    'id': user_id,
                    'last_name': 'Неизвестен',
                    'first_name': '',
                    'middle_name': '',
                    'rights': 'user'
                }

            # Получаем роль из EmployeeData
            role = 'user'
            tasks_session = get_tasks_session()
            if tasks_session:
                try:
                    from models.employees import EmployeeData
                    from sqlalchemy import select
                    stmt = select(EmployeeData.role).where(EmployeeData.employee_id == user_id)
                    emp_data_role = tasks_session.scalar(stmt)
                    if emp_data_role:
                        role = emp_data_role.value if hasattr(emp_data_role, 'value') else str(emp_data_role)
                except Exception as e:
                    print(f"⚠️ Ошибка получения роли: {e}")
                finally:
                    tasks_session.close()

            return {
                'id': user.id,
                'last_name': user.last_name,
                'first_name': user.first_name,
                'middle_name': user.middle_name or '',
                'rights': role,
                'position': user.position or '',
                'phone_number': user.phone_number or '',
                'email': user.email or ''
            }
        finally:
            emp_session.close()

    def load_employees_by_ids(self, employee_ids: List[int]) -> List[Dict]:
        """Загружает сотрудников по списку ID"""
        if not employee_ids:
            return []

        from models.employees import Employee
        from sqlalchemy import select

        stmt = select(Employee).where(Employee.id.in_(employee_ids))
        employees = self.employees_session.scalars(stmt).all()

        result = []
        for emp in employees:
            result.append({
                'id': emp.id,
                'last_name': emp.last_name,
                'first_name': emp.first_name,
                'middle_name': emp.middle_name or '',
                'position': emp.position or 'Сотрудник',
                'phone': emp.phone_number or ''
            })
        return result

    def get_project_card_data(self, project_card_dto) -> Dict:
        """
        Преобразует ProjectCardDTO в данные для отображения в карточке
        Возвращает словарь с готовыми строками для UI
        """
        # Прогресс
        if project_card_dto.tasks_total > 0:
            progress = int((project_card_dto.tasks_done / project_card_dto.tasks_total) * 100)
        else:
            progress = 0

        # Информационная строка (владелец и куратор)
        owner_name = getattr(project_card_dto, 'owner_name', 'Не назначен')
        manager_name = getattr(project_card_dto, 'manager_name', None)

        if manager_name:
            info_text = f"Владелец: {owner_name} | Куратор: {manager_name}"
        else:
            info_text = f"Владелец: {owner_name}"

        # Дата создания
        created_at = getattr(project_card_dto, 'created_at', None)
        start_date_text = f"Создан: {created_at}" if created_at else ""

        # Участники
        member_count = getattr(project_card_dto, 'member_count', 0)
        participants_text = f"Участники: {member_count} чел."

        # Администраторы
        admin_count = getattr(project_card_dto, 'admin_count', 0)
        admins_text = f"Админы: {admin_count} чел."

        # Задачи
        tasks_total = getattr(project_card_dto, 'tasks_total', 0)
        tasks_done = getattr(project_card_dto, 'tasks_done', 0)

        if tasks_total > 0:
            tasks_text = f"Задачи: {tasks_done} / {tasks_total} выполнено"
        else:
            tasks_text = "Задачи: 0"

        # Цвет для задач (зеленый если все выполнены)
        tasks_style = "color: #4CAF50;" if (tasks_total > 0 and tasks_done == tasks_total) else "color: #1B232A;"

        # Колонки
        columns_count = getattr(project_card_dto, 'columns_count', 0)
        columns_text = f"Колонок: {columns_count}"

        return {
            'name': project_card_dto.name if project_card_dto.name else '',
            'progress': progress,
            'info_text': info_text,
            'start_date_text': start_date_text,
            'participants_text': participants_text,
            'admins_text': admins_text,
            'tasks_text': tasks_text,
            'tasks_style': tasks_style,
            'columns_text': columns_text
        }

    def get_employee_display_name(self, employee_id: int) -> str:
        """Возвращает короткое ФИО для отображения"""
        employee = self.employee_repo.get_by_id(employee_id)
        if not employee:
            return f"ID: {employee_id}"

        first_initial = f"{employee.first_name[0]}." if employee.first_name else ""
        middle_initial = f"{employee.middle_name[0]}." if employee.middle_name else ""
        return f"{employee.last_name} {first_initial}{middle_initial}".strip()

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