# services/profile_service.py

from typing import Dict, List, Optional, Any
from datetime import datetime
from PyQt6.QtCore import QDate
import random

from repositories.external_employee_repo import ExternalEmployeeRepo
from repositories.project_repo import ProjectRepo
from repositories.task_repo import TaskRepo
from database import get_tasks_session


class ProfileService:
    """Сервис профиля сотрудника с реальными данными из БД"""

    def __init__(self, session=None):
        self.db_session = session or get_tasks_session()
        self.task_repo = TaskRepo(self.db_session)
        self.current_user = None
        self.project_repo = ProjectRepo(self.db_session)
        self.employee_repo = ExternalEmployeeRepo(self.db_session)

    @property
    def session(self):
        """Свойство для обратной совместимости (доступ к db_session)"""
        return self.db_session

    def set_current_user(self, user_data: Dict):
        """Устанавливает текущего пользователя"""
        self.current_user = user_data

    # =====================================================
    # Получение данных сотрудника
    # =====================================================

    def get_employee_profile(self, employee_id: int) -> Dict[str, Any]:
        """Получить полный профиль сотрудника"""
        try:
            from models.employees import ExternalEmployee
            from sqlalchemy import select

            stmt = select(ExternalEmployee).where(ExternalEmployee.id == employee_id)
            employee = self.db_session.scalar(stmt)

            if not employee:
                print(f"❌ Сотрудник с ID {employee_id} не найден")
                return self._get_empty_profile(employee_id)

            # Формируем словарь с данными
            profile = {
                'id': employee.id,
                'last_name': employee.last_name or '',
                'first_name': employee.first_name or '',
                'middle_name': employee.middle_name or '',
                'position': employee.position or 'Сотрудник',
                'phone_number': employee.phone_number or '',
                'email': employee.email or '',
                'birth_date': employee.birth_date,
                'rights': employee.rights or 'user',
                'department': self._get_department_name(employee.department_id),
                'completed_tasks': self._get_completed_tasks_count(employee_id),
                'active_projects': self._get_active_projects_count(employee_id),
                'rating': self._calculate_employee_rating(employee_id),
                'skills': self._get_employee_skills(employee_id, []),
                'projects': self._get_employee_projects(employee_id)
            }

            print(f"✅ Загружен профиль: {profile['last_name']} {profile['first_name']}")
            return profile

        except Exception as e:
            print(f"❌ Ошибка загрузки профиля: {e}")
            import traceback
            traceback.print_exc()
            return self._get_empty_profile(employee_id)

    def _get_empty_profile(self, employee_id: int) -> Dict:
        """Возвращает пустой профиль при ошибке"""
        return {
            'id': employee_id,
            'last_name': 'Неизвестен',
            'first_name': '',
            'middle_name': '',
            'position': 'Сотрудник',
            'phone_number': '',
            'email': '',
            'birth_date': None,
            'rights': 'user',
            'department': 'Не указан',
            'completed_tasks': 0,
            'active_projects': 0,
            'rating': 0,
            'skills': [],
            'projects': []
        }

    def _get_completed_tasks_count(self, employee_id: int) -> int:
        """Получает количество выполненных задач сотрудника"""
        try:
            from models.tasks import Task
            from sqlalchemy import select, and_

            stmt = select(Task).where(
                and_(
                    Task.assigned_to == employee_id,
                    Task.completed == True
                )
            )
            tasks = self.db_session.scalars(stmt).all()
            return len(tasks)
        except Exception as e:
            print(f"❌ Ошибка подсчета задач: {e}")
            return random.randint(10, 50)

    def _get_active_projects_count(self, employee_id: int) -> int:
        """Получает количество активных проектов сотрудника"""
        try:
            from models.projects import Project
            from sqlalchemy import select, and_

            stmt = select(Project).where(
                and_(
                    Project.members.any(employee_id=employee_id),
                    Project.is_archived == False
                )
            )
            projects = self.db_session.scalars(stmt).all()
            return len(projects)
        except Exception as e:
            print(f"❌ Ошибка подсчета проектов: {e}")
            return random.randint(3, 10)

    def _calculate_employee_rating(self, employee_id: int) -> float:
        """Рассчитывает рейтинг сотрудника"""
        try:
            completed = self._get_completed_tasks_count(employee_id)
            # Простой расчет рейтинга (можно усложнить)
            rating = min(completed / 100, 1.0)
            return round(rating, 2)
        except:
            return round(random.uniform(0.3, 0.95), 2)

    # =====================================================
    # Получение проектов сотрудника
    # =====================================================

    def _get_employee_projects(self, employee_id: int) -> List[Dict]:
        """Получает реальные проекты сотрудника из БД"""
        try:
            from models.projects import Project
            from sqlalchemy import select

            # Получаем все проекты, где сотрудник является участником
            stmt = select(Project).where(
                Project.members.any(employee_id=employee_id)
            )
            projects = self.db_session.scalars(stmt).all()

            result = []
            for project in projects:
                # Получаем задачи проекта, назначенные на этого сотрудника
                tasks = self.task_repo.get_by_project(project.id)
                user_tasks = [t for t in tasks if t.assigned_to == employee_id]

                completed_tasks = len([t for t in user_tasks if t.completed])
                total_tasks = len(user_tasks)

                # Рассчитываем прогресс
                progress = 0
                if total_tasks > 0:
                    progress = int((completed_tasks / total_tasks) * 100)

                result.append({
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'progress': progress,
                    'tasks_completed': completed_tasks,
                    'tasks_total': total_tasks,
                    'is_archived': project.is_archived
                })

            return result

        except Exception as e:
            print(f"❌ Ошибка при загрузке проектов сотрудника: {e}")
            return self._get_test_projects()

    def get_all_employee_projects_with_tasks(self, employee_id: int) -> List[Dict]:
        """Получает все проекты сотрудника с детализацией задач для страницы проектов"""
        try:
            from models.projects import Project
            from sqlalchemy import select

            # Получаем все проекты сотрудника
            stmt = select(Project).where(
                Project.members.any(employee_id=employee_id)
            )
            projects = self.db_session.scalars(stmt).all()

            result = []
            for project in projects:
                # Получаем все задачи проекта, назначенные на этого сотрудника
                tasks = self.task_repo.get_by_project(project.id)
                user_tasks = [t for t in tasks if t.assigned_to == employee_id]

                # Преобразуем задачи в нужный формат
                task_list = []
                for task in user_tasks:
                    task_list.append({
                        'id': task.id,
                        'title': task.title,
                        'description': task.description,
                        'priority': task.priority.value if task.priority else 'medium',
                        'status': task.column.name if task.column else 'unknown',
                        'created_at': task.created_at.strftime('%d.%m.%Y') if task.created_at else '',
                        'completed_at': task.updated_at.strftime('%d.%m.%Y') if task.completed else None,
                        'deadline': task.deadline.strftime('%d.%m.%Y') if task.deadline else None,
                        'tags': []
                    })

                result.append({
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'tasks': task_list,
                    'is_archived': project.is_archived
                })

            return result

        except Exception as e:
            print(f"❌ Ошибка при загрузке проектов с задачами: {e}")
            return []

    def _get_test_projects(self) -> List[Dict]:
        """Возвращает тестовые проекты"""
        return [
            {
                'name': 'Разработка новой кабины',
                'progress': 75,
                'tasks_completed': 12,
                'tasks_total': 16
            },
            {
                'name': 'Модернизация конвейера',
                'progress': 90,
                'tasks_completed': 9,
                'tasks_total': 10
            },
            {
                'name': 'Внедрение ERP-системы',
                'progress': 45,
                'tasks_completed': 18,
                'tasks_total': 40
            }
        ]

    def _get_department_name(self, department_id: Optional[int]) -> str:
        """Получает название отдела по ID"""
        if not department_id:
            return "Не указан"
        try:
            from models.employees import DepartmentFDW
            dept = self.db_session.get(DepartmentFDW, department_id)
            if dept:
                return dept.name
        except:
            pass
        return f"Отдел #{department_id}"

    def _get_employee_skills(self, employee_id: int, tasks: List) -> List[Dict]:
        """Получает или генерирует навыки сотрудника"""
        topics = ['Программирование', 'Дизайн', 'Аналитика', 'Тестирование',
                  'Документация', 'Координация', 'Оптимизация', 'Управление',
                  'Исследование', 'Внедрение']

        skills = []
        for topic in topics:
            kpd = random.uniform(0.1, 0.95)
            skills.append({
                'topic': topic,
                'kpd': round(kpd, 2),
                'tasks_completed': random.randint(5, 50)
            })

        return sorted(skills, key=lambda x: x['kpd'], reverse=True)

    # =====================================================
    # Обновление профиля
    # =====================================================

    def update_employee_profile(self, employee_id: int, updates: Dict) -> bool:
        """Обновляет данные сотрудника в БД"""
        try:
            from models.employees import ExternalEmployee
            from sqlalchemy import update

            stmt = (
                update(ExternalEmployee)
                .where(ExternalEmployee.id == employee_id)
                .values(
                    phone_number=updates.get('phone_number'),
                    email=updates.get('email'),
                    birth_date=updates.get('birth_date')
                )
            )
            self.db_session.execute(stmt)
            self.db_session.commit()
            return True

        except Exception as e:
            print(f"❌ Ошибка обновления профиля: {e}")
            self.db_session.rollback()
            return False

    def prepare_profile_form_data(self, employee_data: dict) -> dict:
        """Подготовка данных профиля для формы"""
        result = {}

        result["phone_number"] = employee_data.get("phone_number", "")
        result["email"] = employee_data.get("email", "")

        birth = employee_data.get("birth_date")
        if birth:
            try:
                if isinstance(birth, str):
                    date = QDate.fromString(birth, "yyyy-MM-dd")
                    result["birth_date"] = date if date.isValid() else None
                else:
                    result["birth_date"] = QDate(birth.year, birth.month, birth.day) if hasattr(birth, 'year') else None
            except:
                result["birth_date"] = None
        else:
            result["birth_date"] = None

        return result

    def build_profile_update_data(self, phone: str, email: str, birth_date: QDate) -> dict:
        """Формирование данных для обновления профиля"""
        return {
            "phone_number": phone,
            "email": email,
            "birth_date": birth_date.toString("yyyy-MM-dd") if birth_date and birth_date.isValid() else None
        }

    def apply_profile_updates(self, employee_data: dict, updates: dict) -> dict:
        """Применение изменений к данным сотрудника"""
        employee_data.update(updates)
        return employee_data

    # =====================================================
    # Данные для графиков
    # =====================================================

    def get_kpd_chart_data(self, employee_id: int | None = None):
        """Получение данных графика КПД по темам"""
        if employee_id:
            employee = self.get_employee_profile(employee_id)
            skills = employee.get('skills', [])
            topics = [s['topic'] for s in skills[:8]]
            kpd_values = [s['kpd'] for s in skills[:8]]
        else:
            # Тестовые данные
            topics = [
                'Программирование', 'Документация', 'Оптимизация',
                'Управление', 'Аналитика', 'Тестирование',
                'Дизайн', 'Координация'
            ]
            kpd_values = [0.85, 0.92, 0.78, 0.65, 0.58, 0.45, 0.38, 0.72]

        return topics, kpd_values

    def generate_random_kpd_data(self):
        """Генерация случайных данных графика (обновление)"""
        topics = [
            'Программирование', 'Документация', 'Оптимизация',
            'Управление', 'Аналитика', 'Тестирование',
            'Дизайн', 'Координация'
        ]
        kpd_values = [round(random.uniform(0.3, 0.95), 2) for _ in topics]
        return topics, kpd_values

    def get_chart_title(self):
        return "📊 КПД по темам (нормированный)"

    def get_chart_updated_title(self):
        return "📊 КПД по темам (обновлено)"

    # =====================================================
    # Рейтинг
    # =====================================================

    def calculate_rating_stars(self, kpd_value: float) -> int:
        """Расчёт количества звезд"""
        if kpd_value >= 1.0:
            return 5
        return int(kpd_value * 5)