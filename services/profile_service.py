# services/profile_service.py

from datetime import datetime
from typing import Dict, List, Optional

from PyQt6.QtCore import QDate
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from database import get_employees_session, get_tasks_session
from repositories.employee_repo import EmployeeRepo
from repositories.project_repo import ProjectRepo
from models.employees import Employee, EmployeeData
from models.projects import EmployeeProject, BoardColumn


class ProfileService:
    """Сервис для работы с профилем сотрудника"""

    def __init__(self, session: Session = None):
        # Сессия для taskplanner БД (проекты, задачи)
        self.session = session or get_tasks_session()
        # Отдельная сессия для employees БД (сотрудники)
        self.employees_session = get_employees_session()

        # Используем employees_session для EmployeeRepo
        self.employee_repo = EmployeeRepo(self.employees_session)
        self.project_repo = ProjectRepo(self.session)
        self.current_user_id = None

    def __del__(self):
        """Закрываем сессию employees при удалении"""
        try:
            if hasattr(self, 'employees_session') and self.employees_session:
                self.employees_session.close()
        except:
            pass

    def set_current_user_id(self, user_id: int):
        self.current_user_id = user_id

    def calculate_rating_stars(self, rating: float) -> int:
        """Вычисляет количество звезд для рейтинга (от 1 до 5)"""
        if rating >= 90:
            return 5
        elif rating >= 70:
            return 4
        elif rating >= 50:
            return 3
        elif rating >= 30:
            return 2
        elif rating >= 10:
            return 1
        else:
            return 0

    def get_kpd_chart_data(self, employee_id: int) -> tuple:
        """
        Получает данные для графика КПД по темам.
        Возвращает (список_тем, список_КПД)
        """
        try:
            from services.analytics_service import AnalyticsService

            analytics = AnalyticsService(self.session)
            employee_data = analytics.get_employee_card_data(employee_id)

            tag_analytics = employee_data.get("tag_analytics", [])

            if not tag_analytics:
                # Возвращаем тестовые данные, если нет реальных
                return ["Нет данных"], [0]

            topics = [item.get("tag", "Без темы") for item in tag_analytics]
            kpd_values = [item.get("kpd", 0) for item in tag_analytics]

            return topics, kpd_values

        except Exception as e:
            print(f"❌ Ошибка получения данных для графика: {e}")
            return ["Нет данных"], [0]

    def get_chart_title(self) -> str:
        """Возвращает заголовок графика"""
        return "Эффективность по темам"

    def get_chart_updated_title(self) -> str:
        """Возвращает заголовок после обновления"""
        return "Данные обновлены"

    def generate_random_kpd_data(self) -> tuple:
        """
        Генерирует тестовые данные для графика (для демонстрации)
        """
        topics = ["Проектирование", "Разработка", "Тестирование", "Документация", "Аналитика"]
        import random
        kpd_values = [round(random.uniform(0.3, 0.95), 2) for _ in range(len(topics))]
        return topics, kpd_values

    def prepare_profile_form_data(self, employee_data: Dict) -> Dict:
        """
        Подготавливает данные для формы редактирования профиля
        """
        birth_date = None
        if employee_data.get('birth_date'):
            try:
                birth_date = QDate.fromString(employee_data['birth_date'], "yyyy-MM-dd")
            except:
                pass

        return {
            "phone_number": employee_data.get('phone_number', ''),
            "work_number": employee_data.get('work_number', ''),
            "email": employee_data.get('email', ''),
            "birth_date": birth_date
        }

    def build_profile_update_data(self, phone: str = None, email: str = None,
                                  birth_date: QDate = None) -> Dict:
        """
        Формирует словарь с обновлениями профиля
        """
        updates = {}
        if phone is not None:
            updates['phone_number'] = phone
        if email is not None:
            updates['email'] = email
        if birth_date is not None and birth_date.isValid():
            updates['birth_date'] = birth_date.toString("yyyy-MM-dd")
        return updates

    def update_employee_profile(self, employee_id: int, updates: Dict) -> bool:
        """
        Обновляет профиль сотрудника
        """
        return self.update_profile(employee_id, updates)

    def apply_profile_updates(self, employee_data: Dict, updates: Dict) -> Dict:
        """
        Применяет обновления к словарю данных сотрудника
        """
        result = employee_data.copy()
        result.update(updates)
        return result

    def get_employee_profile(self, employee_id: int) -> Dict:
        """
        Получает профиль сотрудника с данными из БД employees
        Возвращает словарь с полями:
        - id, last_name, first_name, middle_name
        - position, phone_number, work_number, email, birth_date
        - department_name, division_name, organization_name
        - role, is_active
        """
        try:
            # Получаем сотрудника из БД employees
            employee = self.employee_repo.get_by_id(employee_id)
            if not employee:
                return self._get_empty_profile(employee_id)

            # Получаем дополнительные данные из EmployeeData (БД taskplanner)
            employee_data = self.session.query(EmployeeData).filter(
                EmployeeData.employee_id == employee_id
            ).first()

            # Получаем названия отдела и подразделения
            department_name = self._get_department_name(employee.department_id)
            division_name = self._get_division_name(employee.division_id)

            return {
                "id": employee.id,
                "last_name": employee.last_name or "",
                "first_name": employee.first_name or "",
                "middle_name": employee.middle_name or "",
                "position": employee.position or "",
                "phone_number": employee.phone_number or "",
                "work_number": employee.work_number or "",
                "email": employee.email or "",
                "birth_date": employee.birth_date.isoformat() if employee.birth_date else "",
                "department_id": employee.department_id,
                "department_name": department_name or "—",
                "division_id": employee.division_id,
                "division_name": division_name or "—",
                "organization_id": employee.organization_id or 1,
                "role": employee_data.role.value if employee_data and employee_data.role else "user",
                "is_active": employee_data.is_active if employee_data else True,
                "full_name": self._format_full_name(employee)
            }

        except Exception as e:
            print(f"❌ Ошибка загрузки профиля: {e}")
            import traceback
            traceback.print_exc()
            return self._get_empty_profile(employee_id)

    def _get_empty_profile(self, employee_id: int) -> Dict:
        """Возвращает пустой профиль"""
        return {
            "id": employee_id,
            "last_name": "",
            "first_name": "",
            "middle_name": "",
            "position": "",
            "phone_number": "",
            "work_number": "",
            "email": "",
            "birth_date": "",
            "department_id": None,
            "department_name": "—",
            "division_id": None,
            "division_name": "—",
            "organization_id": 1,
            "role": "user",
            "is_active": True,
            "full_name": "Неизвестен"
        }

    def _format_full_name(self, employee: Employee) -> str:
        """Форматирует ФИО сотрудника"""
        parts = [employee.last_name or "", employee.first_name or ""]
        if employee.middle_name:
            parts.append(employee.middle_name)
        return " ".join([p for p in parts if p]) or f"ID:{employee.id}"

    def _get_department_name(self, department_id: Optional[int]) -> str:
        """Получает название отдела по ID (из БД employees)"""
        if not department_id:
            return "—"
        try:
            from models.employees import Department
            dept = self.employees_session.get(Department, department_id)
            return dept.name if dept else "—"
        except Exception as e:
            print(f"⚠️ Ошибка получения отдела: {e}")
            return "—"

    def _get_division_name(self, division_id: Optional[int]) -> str:
        """Получает название подразделения по ID (из БД employees)"""
        if not division_id:
            return "—"
        try:
            from models.employees import Division
            div = self.employees_session.get(Division, division_id)
            return div.name if div else "—"
        except Exception as e:
            print(f"⚠️ Ошибка получения подразделения: {e}")
            return "—"

    def get_user_projects(self, user_id: int) -> List[Dict]:
        """
        Получает проекты пользователя (из БД taskplanner)
        """
        try:
            # Получаем проекты, где пользователь участник
            stmt = select(EmployeeProject).where(EmployeeProject.employee_id == user_id)
            memberships = self.session.scalars(stmt).all()

            result = []
            for membership in memberships:
                project = self.project_repo.get_by_id(membership.project_id)
                if project and not project.is_archived:
                    result.append({
                        "id": project.id,
                        "name": project.name,
                        "description": project.description or "",
                        "is_admin": membership.is_admin or False,
                        "created_at": project.created_at.strftime("%d.%m.%Y") if project.created_at else ""
                    })

            # Сортируем по названию
            return sorted(result, key=lambda x: x['name'])
        except Exception as e:
            print(f"❌ Ошибка загрузки проектов пользователя: {e}")
            return []

    def update_profile(self, employee_id: int, data: Dict) -> bool:
        """
        Обновляет профиль сотрудника
        data может содержать: last_name, first_name, middle_name, position,
        phone_number, work_number, email, birth_date, department_id, division_id
        """
        try:
            # Обновляем только поля Employee
            employee_fields = [
                'last_name', 'first_name', 'middle_name', 'position',
                'phone_number', 'work_number', 'email', 'birth_date',
                'department_id', 'division_id', 'organization_id'
            ]

            update_data = {k: v for k, v in data.items() if k in employee_fields and v is not None}

            if update_data:
                self.employee_repo.update(employee_id, update_data)
                self.employees_session.commit()

            # Обновляем роль если передана
            if 'role' in data and data['role']:
                from models.employees import RoleEnum
                role_value = data['role']
                if isinstance(role_value, str):
                    try:
                        role_value = RoleEnum(role_value)
                    except ValueError:
                        role_value = RoleEnum.user
                self.employee_repo.update_role(employee_id, role_value)
                self.session.commit()

            return True
        except Exception as e:
            self.employees_session.rollback()
            self.session.rollback()
            print(f"❌ Ошибка обновления профиля: {e}")
            return False

    def get_all_employee_projects_with_tasks(self, employee_id: int) -> List[Dict]:
        """
        Получает все проекты сотрудника с задачами (для окна проектов)
        """
        try:
            from models.tasks import Task
            from models.projects import Project

            # Получаем проекты, где сотрудник участник
            stmt = select(EmployeeProject).where(EmployeeProject.employee_id == employee_id)
            memberships = self.session.scalars(stmt).all()

            result = []
            for membership in memberships:
                project = self.project_repo.get_by_id(membership.project_id)
                if project:
                    # Получаем задачи проекта
                    tasks = self.session.query(Task).filter(
                        Task.project_id == project.id,
                        Task.is_archived == False
                    ).all()

                    total_tasks = len(tasks)
                    completed_tasks = sum(1 for t in tasks if t.column and t.column.is_done_column)
                    progress = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0

                    result.append({
                        "id": project.id,
                        "name": project.name,
                        "description": project.description or "",
                        "total_tasks": total_tasks,
                        "completed_tasks": completed_tasks,
                        "progress": progress,
                        "is_admin": membership.is_admin or False,
                        "created_at": project.created_at.strftime("%d.%m.%Y") if project.created_at else ""
                    })

            return sorted(result, key=lambda x: x['name'])
        except Exception as e:
            print(f"❌ Ошибка загрузки проектов сотрудника: {e}")
            return []

    def get_employee_statistics(self, employee_id: int) -> Dict:
        """
        Получает статистику сотрудника по задачам и проектам
        """
        try:
            from models.tasks import Task
            from models.projects import Project

            # Количество проектов
            projects_count = self.session.query(EmployeeProject).filter(
                EmployeeProject.employee_id == employee_id
            ).count()

            # Количество задач (как исполнитель)
            tasks_count = self.session.query(Task).filter(
                Task.assigned_to == employee_id,
                Task.is_archived == False
            ).count()

            # Количество выполненных задач
            completed_tasks = self.session.query(Task).filter(
                Task.assigned_to == employee_id,
                Task.is_archived == False
            ).join(Task.column).filter(
                BoardColumn.is_done_column == True
            ).count()

            return {
                "projects_count": projects_count,
                "tasks_count": tasks_count,
                "completed_tasks": completed_tasks
            }
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
            return {
                "projects_count": 0,
                "tasks_count": 0,
                "completed_tasks": 0
            }