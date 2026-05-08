# services/projects_service/projects_service.py

from typing import List, Optional, Dict, Any
from database import get_tasks_session, get_employees_session

from .projects_crud_service import ProjectsCrudService
from .projects_members_service import ProjectsMembersService
from .projects_columns_service import ProjectsColumnsService
from .projects_tasks_service import ProjectsTasksService
from .projects_statistics_service import ProjectsStatisticsService
from .projects_notification_service import ProjectsNotificationService
from ..employee_service.column_service import ColumnService


class ProjectsService:
    """Главный сервис для работы с проектами (фасад)"""

    def __init__(self, session=None):
        # Сессии
        self.session = session or get_tasks_session()
        self.employees_session = get_employees_session()

        self.current_user_id = None
        self.current_user = None

        # Вспомогательные сервисы
        self.column_service = ColumnService(self.session)

        # Инициализация подсервисов
        self.crud = ProjectsCrudService(self.session, self.employees_session, self.current_user_id)
        self.members = ProjectsMembersService(self.session, self.employees_session, self.crud.employee_repo)
        self.columns = ProjectsColumnsService(self.session)
        self.tasks = ProjectsTasksService(self.session, self.employees_session, self.crud.employee_repo)
        self.stats = ProjectsStatisticsService(self.session, self.crud.employee_repo)
        self.notification = ProjectsNotificationService(self.crud.employee_repo)

    def set_current_user_id(self, user_id):
        self.current_user_id = user_id
        self.crud.set_current_user_id(user_id)
        self.notification.set_current_user_id(user_id)

    def set_current_user(self, user):
        self.current_user = user

    # =====================================================
    # Прокси для CRUD операций
    # =====================================================

    def get_project_for_edit(self, project_id: int):
        return self.crud.get_project_for_edit(project_id)

    def archive_project(self, project_id: int) -> bool:
        return self.crud.archive_project(project_id)

    def create_new_project(self, raw_data: dict, creator_id: int):
        return self.crud.create_new_project(raw_data, creator_id)

    def update_project(self, project_id: int, dto) -> bool:
        return self.crud.update_project(project_id, dto)

    def get_projects_for_cards(self, search_query: str = "", status_filter: str = "Все", owner_filter: bool = False):
        return self.crud.get_projects_for_cards(search_query, status_filter, owner_filter)

    # =====================================================
    # Прокси для работы с участниками
    # =====================================================

    def load_employees_for_selector(self) -> List[Dict]:
        return self.members.load_employees_for_selector()

    def load_employees_for_manager_combo(self) -> List[Dict]:
        return self.members.load_employees_for_manager_combo()

    def load_employees_by_ids(self, employee_ids: List[int]) -> List[Dict]:
        return self.members.load_employees_by_ids(employee_ids)

    def get_employee_display_name(self, employee_id: int) -> str:
        return self.members.get_employee_display_name(employee_id)

    def get_user_by_id(self, user_id: int) -> Dict:
        return self.members.get_user_by_id(user_id)

    def load_employee_selector_data(self) -> Dict:
        return self.members.load_employee_selector_data()

    def filter_employees_by_search(self, employees: List[Dict], search_text: str) -> List[Dict]:
        return self.members._filter_by_search(employees, search_text) if hasattr(self.members, '_filter_by_search') else [e for e in employees if search_text.lower() in e['full_name'].lower()]

    def sort_employees_for_selector(self, employees: List[Dict], selected_ids: set) -> List[Dict]:
        def get_sort_key(emp):
            is_selected = emp['id'] in selected_ids
            return (0 if is_selected else 1, -emp.get('usage_count', 0))
        return sorted(employees, key=get_sort_key)

    # =====================================================
    # Прокси для работы с колонками
    # =====================================================

    def get_template_columns_for_selector(self) -> List[Dict]:
        return self.columns.get_template_columns_for_selector()

    def filter_columns_by_search(self, columns: List[Dict], search_text: str) -> List[Dict]:
        return self.columns.filter_columns_by_search(columns, search_text)

    def get_selected_columns_by_keys(self, all_columns: List[Dict], selected_keys: List[str]) -> List[Dict]:
        return self.columns.get_selected_columns_by_keys(all_columns, selected_keys)

    def load_template_columns(self) -> List[Dict]:
        return self.columns.load_template_columns()

    def get_project_columns(self, project_id: int) -> List[Dict]:
        return self.columns.get_project_columns(project_id, self.crud.project_repo)

    def add_column_to_project(self, project_id: int, template_column_id: int = None, custom_data: Dict = None):
        return self.columns.add_column_to_project(project_id, self.column_service, template_column_id, custom_data)

    # =====================================================
    # Прокси для работы с задачами проекта
    # =====================================================

    def get_project_tasks_for_view(self, project_id: int, include_archived: bool = False) -> List[Dict]:
        return self.tasks.get_project_tasks_for_view(project_id, include_archived, self.get_project_name)

    def get_project_name(self, project_id: int) -> str:
        return self.tasks.get_project_name(project_id, self.crud.project_repo)

    def restore_task(self, task_id: int) -> bool:
        return self.tasks.restore_task(task_id)

    def delete_task_permanently(self, task_id: int) -> bool:
        return self.tasks.delete_task_permanently(task_id)

    # =====================================================
    # Прокси для статистики
    # =====================================================

    def get_project_card_data(self, project_card_dto) -> Dict:
        return self.stats.get_project_card_data(project_card_dto)

    # =====================================================
    # Прокси для уведомлений
    # =====================================================

    def get_user_chats(self, user_id: int) -> List:
        return self.notification.get_user_chats(user_id)

    # =====================================================
    # Вспомогательные методы (оставляем в фасаде)
    # =====================================================

    def validate_project_data(self, data: Dict) -> Optional[str]:
        if not data.get('name', '').strip():
            return "Введите название проекта"
        selected_columns = data.get('selected_columns_data', [])
        if not selected_columns:
            return "Выберите хотя бы одну колонку для отображения в проекте"
        return None

    def prepare_project_data_for_creation(self, raw_data: Dict, creator_id: int) -> Dict:
        prepared = {
            'name': raw_data.get('name', '').strip(),
            'description': raw_data.get('description', ''),
            'is_active': raw_data.get('is_active', True),
            'manager_id': raw_data.get('manager_id'),
            'selected_columns_data': raw_data.get('selected_columns_data', []),
            'selected_columns_keys': raw_data.get('selected_columns', []),
        }

        participants_ids = raw_data.get('participants_ids', '')
        admins_ids = raw_data.get('admins_ids', '')

        if isinstance(participants_ids, list):
            participants_ids = ','.join(str(id) for id in participants_ids)
        if isinstance(admins_ids, list):
            admins_ids = ','.join(str(id) for id in admins_ids)

        prepared['participants_ids'] = participants_ids
        prepared['admins_ids'] = admins_ids

        participant_list = [str(creator_id)]
        if participants_ids:
            participant_list.extend([p for p in participants_ids.split(',') if p and p != str(creator_id)])
        prepared['participants_ids'] = ','.join(participant_list)

        admin_list = [str(creator_id)]
        if admins_ids:
            admin_list.extend([a for a in admins_ids.split(',') if a and a != str(creator_id)])
        prepared['admins_ids'] = ','.join(admin_list)

        return prepared

    def prepare_edit_dialog_data(self, project_dto) -> Dict:
        from models.employees import Employee
        from sqlalchemy import select
        from database import get_employees_session

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

        if result['member_ids']:
            emp_session = get_employees_session()
            if emp_session:
                stmt = select(Employee).where(Employee.id.in_(result['member_ids']))
                employees = emp_session.scalars(stmt).all()
                for emp in employees:
                    result['participants'].append({
                        'id': emp.id, 'last_name': emp.last_name, 'first_name': emp.first_name,
                        'middle_name': emp.middle_name or '', 'position': emp.position or 'Сотрудник',
                        'phone': emp.phone_number or '', 'email': emp.email or ''
                    })
                emp_session.close()

        if result['admin_ids']:
            emp_session = get_employees_session()
            if emp_session:
                stmt = select(Employee).where(Employee.id.in_(result['admin_ids']))
                employees = emp_session.scalars(stmt).all()
                for emp in employees:
                    result['admins'].append({
                        'id': emp.id, 'last_name': emp.last_name, 'first_name': emp.first_name,
                        'middle_name': emp.middle_name or '', 'position': emp.position or 'Сотрудник',
                        'phone': emp.phone_number or '', 'email': emp.email or ''
                    })
                emp_session.close()

        return result

    def compare_project_changes(self, original_data: Dict, current_data: Dict) -> bool:
        if original_data.get('name') != current_data.get('name'): return True
        if original_data.get('description') != current_data.get('description'): return True
        if original_data.get('is_active') != current_data.get('is_active'): return True
        if original_data.get('manager_id') != current_data.get('manager_id'): return True

        original_columns = original_data.get('selected_columns_data', [])
        current_columns = current_data.get('selected_columns_data', [])
        if len(original_columns) != len(current_columns): return True

        original_col_ids = set([col.get('id') for col in original_columns if col.get('id')])
        current_col_ids = set([col.get('id') for col in current_columns if col.get('id')])
        if original_col_ids != current_col_ids: return True

        original_participants = set(self._extract_ids(original_data.get('participants', [])))
        current_participants = set(self._extract_ids(current_data.get('participants', [])))
        if original_participants != current_participants: return True

        original_admins = set(self._extract_ids(original_data.get('admins', [])))
        current_admins = set(self._extract_ids(current_data.get('admins', [])))
        if original_admins != current_admins: return True

        return False

    def _extract_ids(self, data) -> List[int]:
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

    def ensure_admins_in_participants(self, participants: List[Dict], admins: List[Dict]) -> List[Dict]:
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

    def update_project_from_dialog(self, project_id: int, dialog_data: Dict):
        project_dto = self.get_project_for_edit(project_id)
        if not project_dto:
            return None

        project_dto.name = dialog_data.get('name', '')
        project_dto.description = dialog_data.get('description', '')
        project_dto.is_archived = not dialog_data.get('is_active', True)
        project_dto.selected_columns_data = dialog_data.get('selected_columns_data', [])
        project_dto.manager_id = dialog_data.get('manager_id')

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