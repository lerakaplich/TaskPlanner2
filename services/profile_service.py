# services/profile_service.py
from random import random
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy import select, func, and_
from PyQt6.QtCore import QDate

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

    def get_employee_profile(self, employee_id: int) -> Dict[str, Any]:
        """Получить полный профиль сотрудника с реальными данными"""
        try:
            from models.employees import ExternalEmployee
            from models.tasks import Task
            from models.projects import Project, EmployeeProject

            stmt = select(ExternalEmployee).where(ExternalEmployee.id == employee_id)
            employee = self.db_session.scalar(stmt)

            if not employee:
                print(f"❌ Сотрудник с ID {employee_id} не найден")
                return self._get_empty_profile(employee_id)

            # Получаем проекты сотрудника
            projects_stmt = select(Project).join(
                EmployeeProject, Project.id == EmployeeProject.project_id
            ).where(EmployeeProject.employee_id == employee_id)
            all_projects = list(self.db_session.scalars(projects_stmt))

            # Получаем задачи сотрудника (как исполнитель)
            tasks_stmt = select(Task).where(Task.assigned_to == employee_id)
            all_tasks = list(self.db_session.scalars(tasks_stmt))

            # Статистика
            completed_tasks = sum(1 for t in all_tasks if t.column and t.column.is_done_column)
            active_projects = sum(1 for p in all_projects if not p.is_archived)

            # Аналитика по тегам для навыков
            tag_analytics = self._get_employee_tag_analytics(employee_id, all_tasks)

            # Проекты с прогрессом
            projects_data = []
            for project in all_projects:
                project_tasks = [t for t in all_tasks if t.project_id == project.id]
                completed = sum(1 for t in project_tasks if t.column and t.column.is_done_column)
                total = len(project_tasks)
                progress = int((completed / total) * 100) if total > 0 else 0

                projects_data.append({
                    'id': project.id,
                    'name': project.name,
                    'description': project.description or '',
                    'progress': progress,
                    'tasks_completed': completed,
                    'tasks_total': total,
                    'is_archived': project.is_archived
                })

            # Рассчитываем рейтинг
            rating = min(completed_tasks / 50, 1.0) if completed_tasks > 0 else 0

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
                'completed_tasks': completed_tasks,
                'active_projects': active_projects,
                'rating': rating,
                'skills': tag_analytics,  # Используем реальные данные из тегов
                'projects': projects_data
            }

            print(f"✅ Загружен профиль: {profile['last_name']} {profile['first_name']}")
            print(f"   Задач выполнено: {completed_tasks}, Проектов активных: {active_projects}")
            return profile

        except Exception as e:
            print(f"❌ Ошибка загрузки профиля: {e}")
            import traceback
            traceback.print_exc()
            return self._get_empty_profile(employee_id)

    def _get_employee_tag_analytics(self, employee_id: int, tasks: List) -> List[Dict]:
        """Получить аналитику по тегам для сотрудника (навыки)"""
        from repositories.tag_repo import TagRepo
        tag_repo = TagRepo(self.db_session)

        tag_stats = {}
        for task in tasks:
            task_tags = tag_repo.get_task_tags(task.id)
            for tag in task_tags:
                tag_name = tag.name
                if tag_name not in tag_stats:
                    tag_stats[tag_name] = {
                        'topic': tag_name,
                        'count': 0,
                        'completed': 0,
                        'kpd': 0.0
                    }
                tag_stats[tag_name]['count'] += 1
                if task.column and task.column.is_done_column:
                    tag_stats[tag_name]['completed'] += 1

        # Рассчитываем КПД
        for tag_name, stats in tag_stats.items():
            if stats['count'] > 0:
                stats['kpd'] = round(stats['completed'] / stats['count'], 2)
            stats['tasks_completed'] = stats['count']

        # Сортируем по КПД
        result = sorted(tag_stats.values(), key=lambda x: x['kpd'], reverse=True)

        # Если нет тегов, возвращаем базовые навыки
        if not result:
            return [
                {'topic': 'Аналитика', 'kpd': 0.5, 'tasks_completed': 0},
                {'topic': 'Разработка', 'kpd': 0.5, 'tasks_completed': 0},
                {'topic': 'Тестирование', 'kpd': 0.5, 'tasks_completed': 0},
                {'topic': 'Документация', 'kpd': 0.5, 'tasks_completed': 0},
                {'topic': 'Координация', 'kpd': 0.5, 'tasks_completed': 0}
            ]

        return [{'topic': s['topic'], 'kpd': s['kpd'], 'tasks_completed': s['count']} for s in result]

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

    def _get_department_name(self, department_id: Optional[int]) -> str:
        """Получает название отдела по ID"""
        if not department_id:
            return "Не указан"
        try:
            from models.employees import DepartmentFDW
            dept = self.db_session.get(DepartmentFDW, department_id)
            if dept:
                return dept.name
        except Exception as e:
            print(f"Ошибка получения отдела: {e}")
        return f"Отдел #{department_id}"

    def get_all_employee_projects_with_tasks(self, employee_id: int) -> List[Dict]:
        """Получает все проекты сотрудника с детализацией задач"""
        try:
            from models.projects import Project, EmployeeProject
            from models.tasks import Task

            # Получаем все проекты сотрудника
            stmt = select(Project).join(
                EmployeeProject, Project.id == EmployeeProject.project_id
            ).where(EmployeeProject.employee_id == employee_id)
            projects = list(self.db_session.scalars(stmt))

            result = []
            for project in projects:
                # Получаем задачи проекта, назначенные на этого сотрудника
                tasks_stmt = select(Task).where(
                    and_(
                        Task.project_id == project.id,
                        Task.assigned_to == employee_id
                    )
                )
                user_tasks = list(self.db_session.scalars(tasks_stmt))

                # Группируем задачи по статусам
                grouped_tasks = {
                    "to_do": [],
                    "in_progress": [],
                    "review": [],
                    "completed": [],
                    "archived": []
                }

                for task in user_tasks:
                    status_key = "to_do"
                    if task.column:
                        col_name = task.column.name.lower()
                        if task.column.is_done_column:
                            status_key = "completed"
                        elif "проверк" in col_name:
                            status_key = "review"
                        elif "работ" in col_name:
                            status_key = "in_progress"

                    if task.is_archived:
                        status_key = "archived"

                    task_dict = {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description or "",
                        "priority": task.priority.value if task.priority else "medium",
                        "status": status_key,
                        "created_at": task.created_at.strftime("%d.%m.%Y") if task.created_at else "",
                        "deadline": task.deadline.strftime("%d.%m.%Y") if task.deadline else None,
                        "is_completed": status_key in ("completed", "archived"),
                        "due_date_str": task.deadline.strftime("%d.%m.%Y") if task.deadline else None
                    }
                    grouped_tasks[status_key].append(task_dict)

                total_tasks = len(user_tasks)
                completed_tasks = len(grouped_tasks["completed"]) + len(grouped_tasks["archived"])

                result.append({
                    "id": project.id,
                    "name": project.name,
                    "description": project.description or "",
                    "tasks": user_tasks,
                    "grouped_tasks": grouped_tasks,
                    "tasks_total": total_tasks,
                    "tasks_done": completed_tasks,
                    "is_archived": project.is_archived
                })

            return result

        except Exception as e:
            print(f"❌ Ошибка при загрузке проектов с задачами: {e}")
            import traceback
            traceback.print_exc()
            return []

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
        result = {
            "phone_number": employee_data.get("phone_number", ""),
            "email": employee_data.get("email", "")
        }

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

    def get_kpd_chart_data(self, employee_id: int | None = None):
        """Получение данных графика КПД по темам из реальных навыков"""
        if employee_id:
            employee = self.get_employee_profile(employee_id)
            skills = employee.get('skills', [])
            if skills:
                topics = [s['topic'] for s in skills[:8]]
                kpd_values = [s['kpd'] for s in skills[:8]]
            else:
                # Если нет навыков, возвращаем базовые
                topics = ['Нет данных', 'Нет данных', 'Нет данных', 'Нет данных']
                kpd_values = [0, 0, 0, 0]
        else:
            # Тестовые данные
            topics = ['Программирование', 'Документация', 'Управление', 'Аналитика', 'Тестирование', 'Дизайн']
            kpd_values = [0.85, 0.92, 0.65, 0.58, 0.45, 0.72]

        return topics, kpd_values

    def get_chart_title(self):
        return "📊 КПД по темам"

    def get_chart_updated_title(self):
        return "📊 КПД по темам (обновлено)"

    def calculate_rating_stars(self, kpd_value: float) -> int:
        """Расчёт количества звезд"""
        if kpd_value >= 0.9:
            return 5
        elif kpd_value >= 0.7:
            return 4
        elif kpd_value >= 0.5:
            return 3
        elif kpd_value >= 0.3:
            return 2
        elif kpd_value >= 0.1:
            return 1
        return 0

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

    def generate_random_kpd_data(self):
        """Генерация случайных данных графика (обновление)"""
        topics = [
            'Программирование', 'Документация', 'Оптимизация',
            'Управление', 'Аналитика', 'Тестирование',
            'Дизайн', 'Координация'
        ]
        kpd_values = [round(random.uniform(0.3, 0.95), 2) for _ in topics]
        return topics, kpd_values