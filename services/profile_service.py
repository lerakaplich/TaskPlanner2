# services/profile_service.py

from typing import Dict, List, Optional, Any
from datetime import datetime
from PyQt6.QtCore import QDate
import random

# Импортируем репозитории
from repositories.task_repo import TaskRepo
from database import get_tasks_session  # 👈 ТОЛЬКО ОДНА СЕССИЯ


class ProfileService:
    """Сервис профиля сотрудника с реальными данными из БД"""

    def __init__(self, db_session=None):
        self.db_session = db_session or get_tasks_session()  # только одна сессия для всего
        self.task_repo = TaskRepo(self.db_session)
        # Убираем employee_repo, так как работаем только через foreign_data
        self.current_user = None

    def set_current_user(self, user_data: Dict):
        """Устанавливает текущего пользователя"""
        self.current_user = user_data

    # =====================================================
    # Получение данных сотрудника
    # =====================================================

    def get_employee_profile(self, employee_id: int) -> Dict:
        """
        Получение данных профиля сотрудника из БД
        """
        try:
            # Получаем данные сотрудника из внешней таблицы
            from models.employees import ExternalEmployee
            from sqlalchemy import select

            stmt = select(ExternalEmployee).where(ExternalEmployee.id == employee_id)
            employee = self.db_session.scalar(stmt)

            if not employee:
                print(f"⚠️ Сотрудник с ID {employee_id} не найден, возвращаю тестовые данные")
                return self._get_test_profile(employee_id)

            # Вся информация о сотруднике уже есть в ExternalEmployee
            # Убираем обращение к employee_repo.get_by_id()

            # Получаем статистику по задачам
            tasks = self.task_repo.get_tasks_for_kanban(2)  # project_id=2
            user_tasks = [t for t in tasks if t.assigned_to == employee_id]

            completed_tasks = len([t for t in user_tasks if t.completed])
            active_tasks = len([t for t in user_tasks if not t.completed])

            # Рассчитываем KPD (упрощенно)
            rating = 0.5
            if user_tasks:
                rating = completed_tasks / len(user_tasks)

            # Формируем данные для профиля
            profile = {
                'id': employee.id,
                'last_name': employee.last_name,
                'first_name': employee.first_name,
                'middle_name': employee.middle_name or '',
                'position': employee.position or 'Сотрудник',
                'department': self._get_department_name(employee.department_id),
                'phone_number': employee.phone_number or '',
                'email': employee.email or '',
                'birth_date': employee.birth_date.isoformat() if employee.birth_date else None,
                'photo_path': None,
                'completed_tasks': completed_tasks,
                'active_projects': self._get_active_projects_count(employee_id),
                'rating': rating,
                'rights': employee.rights or 'user',
                'settings': employee.settings or {}
            }

            # Добавляем навыки (из настроек или генерируем)
            profile['skills'] = self._get_employee_skills(employee_id, user_tasks)

            # Добавляем проекты
            profile['projects'] = self._get_employee_projects(employee_id)

            return profile

        except Exception as e:
            print(f"❌ Ошибка загрузки профиля: {e}")
            import traceback
            traceback.print_exc()
            return self._get_test_profile(employee_id)

    def _get_test_profile(self, employee_id: int) -> Dict:
        """Возвращает тестовые данные для профиля"""
        return {
            'id': employee_id,
            'last_name': 'Иванов',
            'first_name': 'Иван',
            'middle_name': 'Иванович',
            'position': 'Старший инженер-программист',
            'department': 'Отдел разработки ПО',
            'phone_number': '+7 (123) 456-78-90',
            'email': 'ivanov@maz.by',
            'birth_date': '1990-05-15',
            'photo_path': None,
            'completed_tasks': 156,
            'active_projects': 10,
            'rating': 0.75,
            'rights': 'user',
            'settings': {},
            'skills': [
                {'topic': 'Программирование', 'kpd': 0.8, 'tasks_completed': 45},
                {'topic': 'Дизайн', 'kpd': 0.2, 'tasks_completed': 18},
                {'topic': 'Аналитика', 'kpd': 0.5, 'tasks_completed': 22},
                {'topic': 'Тестирование', 'kpd': 0.1, 'tasks_completed': 32},
                {'topic': 'Документация', 'kpd': 0.9, 'tasks_completed': 12},
                {'topic': 'Координация', 'kpd': 0.3, 'tasks_completed': 15},
                {'topic': 'Оптимизация', 'kpd': 0.7, 'tasks_completed': 8},
                {'topic': 'Управление', 'kpd': 0.6, 'tasks_completed': 20},
                {'topic': 'Исследование', 'kpd': 0.4, 'tasks_completed': 10},
                {'topic': 'Внедрение', 'kpd': 0.55, 'tasks_completed': 14},
            ],
            'projects': self._get_test_projects()
        }

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
            },
            {
                'name': 'Автоматизация складского учета',
                'progress': 30,
                'tasks_completed': 6,
                'tasks_total': 20
            },
            {
                'name': 'Разработка мобильного приложения',
                'progress': 60,
                'tasks_completed': 15,
                'tasks_total': 25
            },
            {
                'name': 'Обновление серверного оборудования',
                'progress': 85,
                'tasks_completed': 17,
                'tasks_total': 20
            },
            {
                'name': 'Внедрение системы контроля качества',
                'progress': 25,
                'tasks_completed': 5,
                'tasks_total': 20
            },
            {
                'name': 'Оптимизация производственных процессов',
                'progress': 55,
                'tasks_completed': 11,
                'tasks_total': 20
            },
            {
                'name': 'Разработка документации',
                'progress': 95,
                'tasks_completed': 19,
                'tasks_total': 20
            },
            {
                'name': 'Обучение персонала',
                'progress': 40,
                'tasks_completed': 8,
                'tasks_total': 20
            }
        ]

    def _get_department_name(self, department_id: Optional[int]) -> str:
        """Получает название отдела по ID"""
        if not department_id:
            return "Не указан"
        # TODO: получить из БД departments
        departments = {
            1: "Отдел разработки ПО",
            2: "Отдел тестирования",
            3: "Отдел аналитики",
            4: "Отдел управления проектами"
        }
        return departments.get(department_id, f"Отдел #{department_id}")

    def _get_active_projects_count(self, employee_id: int) -> int:
        """Получает количество активных проектов сотрудника"""
        # TODO: реализовать подсчет проектов
        return random.randint(5, 15)

    def _get_employee_skills(self, employee_id: int, tasks: List) -> List[Dict]:
        """Получает или генерирует навыки сотрудника"""
        # TODO: получать из реальных данных
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

    def _get_employee_projects(self, employee_id: int) -> List[Dict]:
        """Получает проекты сотрудника"""
        # TODO: получать из реальных данных
        return self._get_test_projects()

    # =====================================================
    # Обновление профиля
    # =====================================================

    def update_employee_profile(self, employee_id: int, updates: Dict) -> bool:
        """
        Обновляет данные сотрудника в БД
        """
        try:
            from models.employees import ExternalEmployee
            from sqlalchemy import update

            # Обновляем данные во внешней таблице
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
                date = QDate.fromString(birth, "yyyy-MM-dd")
                result["birth_date"] = date if date.isValid() else None
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
            "birth_date": birth_date.toString("yyyy-MM-dd") if birth_date.isValid() else None
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
    # Проекты и задачи
    # =====================================================

    STATUS_ORDER = ["to_do", "in_progress", "review", "completed", "archived"]

    def get_employee_projects_with_tasks(self, employee_id: int):
        """Получение проектов сотрудника с задачами"""
        # TODO: получать из реальных данных
        return [
            {
                "name": "Task Planner",
                "tasks": [
                    {
                        "title": "Сверстать экран задач",
                        "priority": "high",
                        "due_date": "10.02.2026",
                        "created_at": "20.01.2026",
                        "completed_at": "08.02.2026",
                        "status": "completed",
                        "tags": ["UI", "срочно"],
                        "creator": "Иван Иванов"
                    },
                    {
                        "title": "Реализовать профиль сотрудника",
                        "priority": "medium",
                        "due_date": "01.02.2026",
                        "created_at": "10.01.2026",
                        "completed_at": None,
                        "status": "in_progress",
                        "tags": ["backend"],
                        "creator": "Иван Иванов"
                    }
                ]
            },
            {
                "name": "Модернизация системы учета 2024",
                "tasks": [
                    {
                        "title": "Перенос данных в новую БД",
                        "priority": "critical",
                        "due_date": None,
                        "created_at": "15.11.2024",
                        "completed_at": "20.11.2024",
                        "status": "archived",
                        "tags": ["база данных"],
                        "creator": "Анна Петрова"
                    }
                ]
            }
        ]

    def filter_projects_by_mode(self, projects, mode):
        """Фильтрация проектов по режиму"""
        if mode == "completed":
            filtered_projects = []
            for project in projects:
                tasks = [
                    t for t in project["tasks"]
                    if t.get("status", "").lower() in ("completed", "archived")
                ]
                if tasks:
                    filtered_projects.append({
                        "name": project["name"],
                        "tasks": tasks
                    })
            return filtered_projects, "Нет выполненных проектов"

        projects = [p for p in projects if p.get("tasks")]
        return projects, "Нет активных проектов"

    def group_tasks_by_status(self, tasks):
        """Группировка задач по статусам"""
        groups = {s: [] for s in self.STATUS_ORDER}
        for task in tasks:
            status = task.get("status", "").lower()
            if status in groups:
                groups[status].append(task)
            else:
                groups["to_do"].append(task)
        return groups

    def get_status_order(self):
        return self.STATUS_ORDER

    # =====================================================
    # Рейтинг
    # =====================================================

    def calculate_rating_stars(self, kpd_value: float) -> int:
        """Расчёт количества звезд"""
        if kpd_value >= 1.0:
            return 5
        return int(kpd_value * 5)