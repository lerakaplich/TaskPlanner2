# services/tasks_service/tasks_executor_suggestion_service.py

from typing import Dict, List, Optional, Tuple
from sqlalchemy import select, func, and_

from models.projects import BoardColumn
from models.tasks import Task, Tag, TaskTag
from datetime import datetime, timedelta


class TasksExecutorSuggestionService:
    """Сервис для автоматического предложения исполнителя на основе анализа тегов"""

    def __init__(self, db_session, employee_db_session_func):
        self.db_session = db_session  # taskplanner сессия (не фабрика!)
        self.employee_db_session_func = employee_db_session_func  # фабрика для employees

    def get_top_executors_for_tags(self, tag_names: List[str], limit: int = 3) -> List[Dict]:
        if not tag_names:
            return []

        print(f"\n🔍 Поиск лучших исполнителей для тегов: {tag_names}")

        tasks_session = self.db_session

        tag_ids_result = tasks_session.execute(
            select(Tag.id).where(Tag.name.in_(tag_names))
        ).fetchall()
        tag_ids = [row[0] for row in tag_ids_result]

        print(f"   🏷️ ID тегов: {tag_ids}")

        if not tag_ids:
            print(f"⚠️ Теги не найдены: {tag_names}")
            return []

        # Проверка наличия задач
        check_stmt = select(
            Task.id, Task.assigned_to, Task.difficulty, BoardColumn.name
        ).join(
            TaskTag, Task.id == TaskTag.task_id
        ).join(
            BoardColumn, Task.column_id == BoardColumn.id
        ).where(
            TaskTag.tag_id.in_(tag_ids),
            BoardColumn.is_done_column == True,
            Task.assigned_to.isnot(None)
        ).limit(10)

        check_results = tasks_session.execute(check_stmt).fetchall()
        print(f"   📊 Найдено подходящих задач (проверка): {len(check_results)}")
        for row in check_results:
            print(
                f"      - Задача {row.id}: исполнитель={row.assigned_to}, сложность={row.difficulty}, колонка={row.name}")

        if not check_results:
            print("   ⚠️ Нет выполненных задач с выбранными тегами!")
            return []

        # УБИРАЕМ ОГРАНИЧЕНИЕ ПО ВРЕМЕНИ или увеличиваем период
        stmt = select(
            Task.assigned_to,
            func.avg(Task.difficulty).label('avg_difficulty'),
            func.count(Task.id.distinct()).label('tasks_count')
        ).join(
            TaskTag, Task.id == TaskTag.task_id
        ).join(
            BoardColumn, Task.column_id == BoardColumn.id
        ).where(
            TaskTag.tag_id.in_(tag_ids),
            BoardColumn.is_done_column == True,
            Task.assigned_to.isnot(None)
            # Убираем: Task.created_at > datetime.now() - timedelta(days=90)
        ).group_by(
            Task.assigned_to
        ).order_by(
            func.avg(Task.difficulty).desc()
        ).limit(limit)

        results = tasks_session.execute(stmt).fetchall()

        print(f"   📊 Результаты группировки: {len(results)}")

        suggestions = []
        for row in results:
            employee_info = self._get_employee_info(row.assigned_to)
            if employee_info:
                suggestions.append({
                    "employee_id": row.assigned_to,
                    "employee_name": employee_info.get("name", "Неизвестен"),
                    "avg_difficulty": round(row.avg_difficulty, 2) if row.avg_difficulty else 0,
                    "tasks_count": row.tasks_count,
                    "tag_match_count": self._get_tag_match_count(row.assigned_to, tag_ids, tasks_session)
                })
                print(
                    f"      - {employee_info.get('name')}: средняя сложность={row.avg_difficulty}, задач={row.tasks_count}")

        print(f"✅ Найдено {len(suggestions)} кандидатов")
        return suggestions

    def get_top_executor_for_tags(self, tag_names: List[str]) -> Optional[Dict]:
        """Возвращает лучшего исполнителя для заданных тегов"""
        suggestions = self.get_top_executors_for_tags(tag_names, limit=1)
        return suggestions[0] if suggestions else None

    def get_employee_performance_by_tag(self, employee_id: int, tag_name: str = None) -> Dict:
        """
        Получает производительность сотрудника по конкретному тегу или по всем тегам
        """
        tasks_session = self.db_session

        query = select(
            Tag.name,
            func.avg(Task.difficulty).label('avg_difficulty'),
            func.count(Task.id).label('tasks_count')
        ).join(
            TaskTag, Task.id == TaskTag.task_id
        ).join(
            Tag, TaskTag.tag_id == Tag.id
        ).join(
            BoardColumn, Task.column_id == BoardColumn.id
        ).where(
            Task.assigned_to == employee_id,
            BoardColumn.is_done_column == True  # Завершённые задачи
        )

        if tag_name:
            query = query.where(Tag.name == tag_name)

        query = query.group_by(Tag.name).order_by(func.avg(Task.difficulty).desc())

        results = tasks_session.execute(query).fetchall()

        performance = {}
        for row in results:
            performance[row.name] = {
                "avg_difficulty": round(row.avg_difficulty, 2) if row.avg_difficulty else 0,
                "tasks_count": row.tasks_count
            }

        return performance

    def _get_employee_info(self, employee_id: int) -> Optional[Dict]:
        """Получает информацию о сотруднике из БД employees"""
        try:
            with self.employee_db_session_func() as emp_session:
                from models.employees import Employee
                employee = emp_session.get(Employee, employee_id)
                if employee:
                    first_initial = f"{employee.first_name[0]}." if employee.first_name else ""
                    middle_initial = f"{employee.middle_name[0]}." if employee.middle_name else ""
                    return {
                        "id": employee.id,
                        "name": f"{employee.last_name} {first_initial}{middle_initial}".strip(),
                        "last_name": employee.last_name,
                        "first_name": employee.first_name,
                        "middle_name": employee.middle_name,
                        "position": employee.position
                    }
        except Exception as e:
            print(f"⚠️ Ошибка получения информации о сотруднике {employee_id}: {e}")
        return None

    def _get_tag_match_count(self, employee_id: int, tag_ids: List[int], tasks_session) -> int:
        """Подсчитывает количество тегов, по которым у сотрудника есть опыт"""
        stmt = select(
            func.count(Tag.id.distinct())
        ).join(
            TaskTag, Tag.id == TaskTag.tag_id
        ).join(
            Task, TaskTag.task_id == Task.id
        ).join(
            BoardColumn, Task.column_id == BoardColumn.id  # ДОБАВИТЬ
        ).where(
            Task.assigned_to == employee_id,
            BoardColumn.is_done_column == True,  # Вместо Task.completed
            Tag.id.in_(tag_ids)
        )
        result = tasks_session.execute(stmt).scalar()
        return result or 0

    def suggest_executor_for_new_task(self, tag_names: List[str], creator_id: int = None) -> Optional[Dict]:
        """
        Предлагает исполнителя для новой задачи на основе тегов.
        Возвращает словарь с информацией о лучшем кандидате.
        """
        if not tag_names:
            return None

        suggestions = self.get_top_executors_for_tags(tag_names, limit=3)

        if not suggestions:
            return None

        best = suggestions[0]

        # Преобразуем сложность в понятное описание
        difficulty_desc = "средней"
        if best['avg_difficulty'] >= 4:
            difficulty_desc = "высокой"
        elif best['avg_difficulty'] >= 3:
            difficulty_desc = "средней"
        else:
            difficulty_desc = "базовой"

        explanation = (
            f"🎯 Рекомендация исполнителя\n\n"
            f"На основе анализа тем '{', '.join(tag_names)}' "
            f"рекомендуется назначить {best['employee_name']}.\n\n"
            f"📊 Статистика:\n"
            f"   • Средняя сложность выполненных задач по теме: {best['avg_difficulty']} ⭐ ({difficulty_desc})\n"
            f"   • Выполнено задач по теме(-ам): {best['tasks_count']}\n"
        )

        return {
            "employee_id": best["employee_id"],
            "employee_name": best["employee_name"],
            "avg_difficulty": best["avg_difficulty"],
            "tasks_count": best["tasks_count"],
            "explanation": explanation,
            "all_suggestions": suggestions
        }