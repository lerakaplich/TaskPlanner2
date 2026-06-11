# services/profile_service.py

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from PyQt6.QtCore import QDate
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from database import get_employees_session, get_tasks_session
from repositories.employee_repo import EmployeeRepo
from repositories.project_repo import ProjectRepo
from models.employees import Employee, EmployeeData
from models.projects import EmployeeProject, BoardColumn
from models.tasks import Task


class ProfileService:
    """Сервис для работы с профилем сотрудника (вся бизнес-логика)"""

    def __init__(self, session: Session = None):
        self.session = session or get_tasks_session()
        self.employees_session = get_employees_session()
        self.employee_repo = EmployeeRepo(self.employees_session)
        self.project_repo = ProjectRepo(self.session)
        self.current_user_id = None

    def get_project_tasks(self, project_id: int, employee_id: int = None) -> List[Dict]:
        """
        Получает задачи проекта для отображения в карточках.

        Args:
            project_id: ID проекта
            employee_id: ID сотрудника (если указан, возвращает задачи этого сотрудника)

        Returns:
            List[Dict]: список задач в формате для TaskCard
        """
        try:
            from models.tasks import Task
            from models.projects import BoardColumn, Project
            from models.schemas.tasks_dto import TaskPriority
            from sqlalchemy import and_

            # Получаем название проекта
            project = self.session.query(Project).filter(Project.id == project_id).first()
            project_name = project.name if project else ""

            # Базовый запрос
            query = self.session.query(Task).filter(
                Task.project_id == project_id,
                Task.is_archived == False
            )

            # Если указан сотрудник, фильтруем по исполнителю
            if employee_id:
                query = query.filter(Task.assigned_to == employee_id)

            # Получаем задачи
            tasks = query.all()

            print(f"🔍 get_project_tasks: project_id={project_id}, найдено задач: {len(tasks)}")

            result = []
            for task in tasks:
                # Получаем имя исполнителя
                assignee_name = None
                if task.assigned_to:
                    from repositories.employee_repo import EmployeeRepo
                    emp_repo = EmployeeRepo(self.employees_session)
                    assignee_name = emp_repo.get_full_name(task.assigned_to)

                # Получаем имя автора
                author_name = None
                if task.created_by:
                    from repositories.employee_repo import EmployeeRepo
                    emp_repo = EmployeeRepo(self.employees_session)
                    author_name = emp_repo.get_full_name(task.created_by)

                # Получаем теги
                tags = []
                try:
                    from models.tasks import Tag, TaskTag
                    # Правильный запрос тегов через связь TaskTag
                    tags = self.session.query(Tag).join(
                        TaskTag, Tag.id == TaskTag.tag_id
                    ).filter(
                        TaskTag.task_id == task.id
                    ).all()
                    tags = [tag.name for tag in tags]
                    print(f"   Задача '{task.title}': теги={tags}")
                except Exception as tag_err:
                    print(f"⚠️ Ошибка загрузки тегов для задачи {task.id}: {tag_err}")

                # Получаем статус
                column_name = task.column.name if task.column else "to_do"

                result.append({
                    "id": task.id,
                    "title": task.title,
                    "description": task.description or "",
                    "status": column_name,
                    "priority": task.priority.value if task.priority else "medium",
                    "deadline": task.deadline.strftime("%Y-%m-%d") if task.deadline else None,
                    "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S") if task.created_at else None,
                    "completed_at": task.completed_at.strftime("%Y-%m-%d %H:%M:%S") if task.completed_at else None,
                    "tags": tags,
                    "project_name": project_name,
                    "creator_name": author_name or "",
                    "assigned_to": task.assigned_to,
                    "assignee_name": assignee_name or "",
                    "kpd_score": task.kpd_score if hasattr(task, 'kpd_score') else 0,
                    "is_archived": task.is_archived if hasattr(task, 'is_archived') else False,
                    "column_id": task.column_id,
                    "column_name": column_name,
                    "is_done": task.column.is_done_column if task.column else False
                })

            print(f"🔍 get_project_tasks: возвращено {len(result)} задач")
            return result
        except Exception as e:
            print(f"❌ Ошибка получения задач проекта {project_id}: {e}")
            import traceback
            traceback.print_exc()
            return []

    def __del__(self):
        try:
            if hasattr(self, 'employees_session') and self.employees_session:
                self.employees_session.close()
        except:
            pass

    def set_current_user_id(self, user_id: int):
        self.current_user_id = user_id

    def get_employee_profile(self, employee_id: int) -> Dict[str, Any]:
        """Получает полный профиль сотрудника"""
        try:
            employee = self.employee_repo.get_by_id(employee_id)
            if not employee:
                return self._get_empty_profile(employee_id)

            employee_data = self.session.query(EmployeeData).filter(
                EmployeeData.employee_id == employee_id
            ).first()

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
            return self._get_empty_profile(employee_id)

    def get_employee_statistics(self, employee_id: int) -> Dict[str, int]:
        """Получает статистику сотрудника (только его задачи)"""
        try:
            # Количество проектов, где сотрудник участвует
            projects_count = self.session.query(EmployeeProject).filter(
                EmployeeProject.employee_id == employee_id
            ).count()

            # Количество задач, назначенных на сотрудника
            tasks_count = self.session.query(Task).filter(
                Task.assigned_to == employee_id,
                Task.is_archived == False
            ).count()

            # Количество выполненных задач сотрудника
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
            return {"projects_count": 0, "tasks_count": 0, "completed_tasks": 0}

    def get_employee_projects(self, employee_id: int) -> List[Dict[str, Any]]:
        """Получает проекты сотрудника с количеством задач, где он исполнитель"""
        try:
            memberships = self.session.query(EmployeeProject).filter(
                EmployeeProject.employee_id == employee_id
            ).all()

            result = []
            for membership in memberships:
                project = self.project_repo.get_by_id(membership.project_id)
                if project:
                    # ВАЖНО: считаем только задачи, где сотрудник является исполнителем
                    tasks = self.session.query(Task).filter(
                        Task.project_id == project.id,
                        Task.assigned_to == employee_id,  # <- ТОЛЬКО задачи сотрудника
                        Task.is_archived == False
                    ).all()

                    # Для завершенных задач считаем также только те, где он исполнитель
                    completed_tasks = self.session.query(Task).filter(
                        Task.project_id == project.id,
                        Task.assigned_to == employee_id,
                        Task.is_archived == False
                    ).join(Task.column).filter(
                        BoardColumn.is_done_column == True
                    ).count()

                    total_tasks = len(tasks)

                    result.append({
                        "id": project.id,
                        "name": project.name,
                        "description": project.description or "",
                        "total_tasks": total_tasks,
                        "completed_tasks": completed_tasks,
                        "progress": int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0,
                        "is_admin": membership.is_admin or False,
                        "created_at": project.created_at.strftime("%d.%m.%Y") if project.created_at else "",
                        "is_archived": project.is_archived
                    })

            return sorted(result, key=lambda x: x['name'])
        except Exception as e:
            print(f"❌ Ошибка загрузки проектов: {e}")
            return []

    def get_kpd_chart_data(self, employee_id: int) -> Tuple[List[str], List[float]]:
        """Получает данные для графика КПД по темам"""
        print(f"\n🔍 [DEBUG] get_kpd_chart_data для сотрудника {employee_id}")

        try:
            from models.tasks import Task, TaskTag, Tag
            from models.projects import BoardColumn

            # Получаем все задачи сотрудника, которые находятся в завершенных колонках
            completed_tasks = self.session.query(Task).filter(
                Task.assigned_to == employee_id,
                Task.is_archived == False
            ).join(Task.column).filter(
                BoardColumn.is_done_column == True
            ).all()

            print(f"   Найдено завершенных задач: {len(completed_tasks)}")

            for task in completed_tasks[:3]:  # Показываем первые 3 для отладки
                print(f"      - Задача: {task.title}, КПД: {task.kpd_score}")

            if not completed_tasks:
                print("   ❌ Нет завершенных задач!")
                return ["Нет данных"], [0]

            # Собираем статистику по тегам
            tag_stats = {}

            print(f"\n   Сбор статистики по тегам:")

            for task in completed_tasks:
                # Получаем теги задачи
                tags = self.session.query(Tag).join(TaskTag).filter(
                    TaskTag.task_id == task.id
                ).all()

                print(f"      Задача '{task.title}': {len(tags)} тегов")

                if not tags:
                    tag_name = "Без темы"
                    if tag_name not in tag_stats:
                        tag_stats[tag_name] = {"total_kpd": 0, "count": 0}
                    tag_stats[tag_name]["total_kpd"] += task.kpd_score
                    tag_stats[tag_name]["count"] += 1
                    print(f"         Добавлен тег 'Без темы', КПД={task.kpd_score}")
                else:
                    for tag in tags:
                        tag_name = tag.name
                        if tag_name not in tag_stats:
                            tag_stats[tag_name] = {"total_kpd": 0, "count": 0}
                        tag_stats[tag_name]["total_kpd"] += task.kpd_score
                        tag_stats[tag_name]["count"] += 1
                        print(f"         Тег '{tag_name}', КПД={task.kpd_score}")

            print(f"\n   Статистика по тегам:")
            for tag_name, stats in tag_stats.items():
                print(f"      {tag_name}: {stats['count']} задач, сумма КПД={stats['total_kpd']:.2f}")

            # Формируем результаты
            topics = []
            kpd_values = []

            for tag_name, stats in tag_stats.items():
                avg_kpd = stats["total_kpd"] / stats["count"] if stats["count"] > 0 else 0
                topics.append(tag_name)
                kpd_values.append(round(avg_kpd, 2))
                print(f"      Итог: {tag_name} -> средний КПД={avg_kpd:.2f}")

            # Сортируем по КПД (по убыванию)
            sorted_data = sorted(zip(topics, kpd_values), key=lambda x: x[1], reverse=True)

            if sorted_data:
                topics, kpd_values = zip(*sorted_data)
                topics = list(topics)
                kpd_values = list(kpd_values)
                print(f"\n   Итоговые данные для графика:")
                for topic, kpd in zip(topics, kpd_values):
                    print(f"      {topic}: {kpd}")
                return topics, kpd_values

            print("   ❌ Нет данных для графика!")
            return ["Нет данных"], [0]

        except Exception as e:
            print(f"❌ Ошибка получения данных для графика: {e}")
            import traceback
            traceback.print_exc()
            return ["Нет данных"], [0]

    def get_chart_title(self) -> str:
        return "Эффективность по темам"

    def get_chart_updated_title(self) -> str:
        return "Данные обновлены"

    def generate_random_kpd_data(self) -> Tuple[List[str], List[float]]:
        """Генерирует тестовые данные для графика"""
        import random
        topics = ["Проектирование", "Разработка", "Тестирование", "Документация", "Аналитика"]
        kpd_values = [round(random.uniform(0.3, 0.95), 2) for _ in range(len(topics))]
        return topics, kpd_values

    def calculate_rating(self, employee_data: Dict[str, Any]) -> float:
        """Вычисляет рейтинг сотрудника"""
        skills = employee_data.get('tag_analytics', [])
        if skills:
            avg_kpd = sum(s.get('kpd', 0) for s in skills) / len(skills)
            return avg_kpd * 100
        return 0

    def calculate_rating_stars(self, rating: float) -> int:
        """Вычисляет количество звёзд для рейтинга (1-5)"""
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
        return 0

    def get_edit_form_data(self, employee_data: Dict[str, Any]) -> Dict[str, Any]:
        """Подготавливает данные для формы редактирования"""
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

    def build_update_data(self, phone: str = None, email: str = None,
                          birth_date: QDate = None) -> Dict[str, Any]:
        """Формирует словарь с обновлениями профиля"""
        updates = {}
        if phone is not None:
            updates['phone_number'] = phone
        if email is not None:
            updates['email'] = email
        if birth_date is not None and birth_date.isValid():
            updates['birth_date'] = birth_date.toString("yyyy-MM-dd")
        return updates

    def update_profile(self, employee_id: int, updates: Dict[str, Any]) -> bool:
        """Обновляет профиль сотрудника"""
        try:
            employee_fields = [
                'last_name', 'first_name', 'middle_name', 'position',
                'phone_number', 'work_number', 'email', 'birth_date',
                'department_id', 'division_id', 'organization_id'
            ]

            update_data = {k: v for k, v in updates.items() if k in employee_fields and v is not None}

            if update_data:
                self.employee_repo.update(employee_id, update_data)
                self.employees_session.commit()

            if 'role' in updates and updates['role']:
                from models.employees import RoleEnum
                role_value = updates['role']
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

    def _get_empty_profile(self, employee_id: int) -> Dict[str, Any]:
        return {
            "id": employee_id,
            "last_name": "", "first_name": "", "middle_name": "",
            "position": "", "phone_number": "", "work_number": "", "email": "",
            "birth_date": "", "department_id": None, "department_name": "—",
            "division_id": None, "division_name": "—", "organization_id": 1,
            "role": "user", "is_active": True, "full_name": "Неизвестен"
        }

    def _format_full_name(self, employee: Employee) -> str:
        parts = [employee.last_name or "", employee.first_name or ""]
        if employee.middle_name:
            parts.append(employee.middle_name)
        return " ".join([p for p in parts if p]) or f"ID:{employee.id}"

    def _get_department_name(self, department_id: Optional[int]) -> str:
        if not department_id:
            return "—"
        try:
            from models.employees import Department
            dept = self.employees_session.get(Department, department_id)
            return dept.name if dept else "—"
        except:
            return "—"

    def _get_division_name(self, division_id: Optional[int]) -> str:
        if not division_id:
            return "—"
        try:
            from models.employees import Division
            div = self.employees_session.get(Division, division_id)
            return div.name if div else "—"
        except:
            return "—"