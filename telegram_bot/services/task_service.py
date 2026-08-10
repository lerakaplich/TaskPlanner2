from typing import Dict, List, Optional
from sqlalchemy import text
from server_app.database import get_tasks_session


class TaskService:
    """Сервис для работы с задачами"""

    async def get_tags_list(self) -> List[Dict]:
        """Получить список тегов"""
        with get_tasks_session() as tasks_session:
            stmt = text("""
                SELECT id, name, color
                FROM public.tags
                WHERE is_archived = false
                ORDER BY name
            """)
            tags = tasks_session.execute(stmt).fetchall()
            return [{"id": t.id, "name": t.name, "color": t.color} for t in tags]

    async def get_statuses_for_project(self, project_id: int) -> List[Dict]:
        """Получить статусы (колонки) для проекта"""
        with get_tasks_session() as tasks_session:
            stmt = text("""
                SELECT id, name, is_done_column
                FROM public.board_columns
                WHERE project_id = :project_id OR (is_template = true AND project_id IS NULL)
                ORDER BY position
            """)
            statuses = tasks_session.execute(stmt, {'project_id': project_id}).fetchall()
            return [{"id": s.id, "name": s.name, "is_done": s.is_done_column} for s in statuses]

    async def get_user_projects(self, user_id: int):
        """Получить проекты где пользователь является создателем или администратором"""
        with get_tasks_session() as tasks_session:
            select_stmt = text("""
                SELECT p.id, p.name, p.created_by
                FROM public.projects p
                WHERE (p.created_by = :user_id 
                   OR p.id IN (
                       SELECT project_id FROM public.employees_projects 
                       WHERE employee_id = :user_id AND is_admin = true
                   ))
                AND p.is_archived = false
                ORDER BY p.name
            """)
            projects = tasks_session.execute(select_stmt, {'user_id': user_id}).fetchall()
            return projects

    async def get_user_tasks_detailed(self, user_id: int) -> List[Dict]:
        """Получить подробный список задач пользователя"""
        with get_tasks_session() as tasks_session:
            stmt = text("""
                SELECT t.id, t.title, t.description, t.priority, 
                       t.deadline, t.progress_percent, t.created_at,
                       p.name as project_name,
                       t.completed_at, t.column_id,
                       bc.name as status_name, bc.is_done_column
                FROM public.tasks t
                JOIN public.projects p ON t.project_id = p.id
                LEFT JOIN public.board_columns bc ON t.column_id = bc.id
                WHERE t.assigned_to = :user_id AND t.is_archived = false
                ORDER BY 
                    CASE WHEN t.deadline IS NULL THEN 1 ELSE 0 END,
                    t.deadline ASC,
                    t.created_at DESC
            """)
            tasks = tasks_session.execute(stmt, {'user_id': user_id}).fetchall()
            return self._format_tasks(tasks)

    def _format_tasks(self, tasks) -> List[Dict]:
        """Форматирование списка задач"""
        from datetime import datetime
        result = []
        for task in tasks:
            deadline_text = ""
            days_left = None
            if task.deadline:
                deadline_date = task.deadline.date() if hasattr(task.deadline, 'date') else task.deadline
                today = datetime.now().date()
                days_left = (deadline_date - today).days

                if days_left < 0:
                    deadline_text = f"⚠️ ПРОСРОЧЕНА на {-days_left} дн."
                elif days_left == 0:
                    deadline_text = "⚠️ СЕГОДНЯ!"
                elif days_left == 1:
                    deadline_text = "📅 ЗАВТРА"
                else:
                    deadline_text = f"📅 {deadline_date.strftime('%d.%m.%Y')} (осталось {days_left} дн.)"

            priority_emoji = {
                'low': '🟢', 'medium': '🟡', 'high': '🟠', 'critical': '🔴'
            }.get(task.priority, '⚪')

            status = task.status_name or "Новая"
            is_completed = (task.progress_percent >= 100) or (task.is_done_column)

            result.append({
                "id": task.id,
                "title": task.title,
                "description": task.description[:100] if task.description else "",
                "project_name": task.project_name,
                "priority": task.priority,
                "priority_emoji": priority_emoji,
                "status": "Выполнено" if is_completed else status,
                "deadline_text": deadline_text,
                "progress": task.progress_percent or 0,
                "completed": is_completed,
                "days_left": days_left
            })
        return result

    async def create_task_full(self, data: Dict) -> Optional[int]:
        """Создать задачу со всеми параметрами"""
        with get_tasks_session() as tasks_session:
            # Получаем колонку по статусу
            column_stmt = text("""
                SELECT id FROM public.board_columns 
                WHERE id = :status_id OR (name = :status_name AND (project_id = :project_id OR is_template = true))
                LIMIT 1
            """)
            column = tasks_session.execute(column_stmt, {
                'status_id': data.get('status_id'),
                'status_name': data.get('status'),
                'project_id': data['project_id']
            }).first()
            column_id = column[0] if column else None

            if not column_id:
                col_stmt = text("""
                    SELECT id FROM public.board_columns 
                    WHERE project_id = :project_id OR (is_template = true AND project_id IS NULL)
                    ORDER BY position LIMIT 1
                """)
                column = tasks_session.execute(col_stmt, {'project_id': data['project_id']}).first()
                column_id = column[0] if column else None

            if not column_id:
                return None

            # Находим максимальную позицию
            max_pos_stmt = text("""
                SELECT COALESCE(MAX(position), 0) FROM public.tasks WHERE column_id = :column_id
            """)
            max_pos = tasks_session.execute(max_pos_stmt, {'column_id': column_id}).scalar()
            new_position = max_pos + 1

            # Маппинг приоритетов
            priority_map = {
                'low': 'low', 'medium': 'medium', 'high': 'high', 'critical': 'critical',
                'Низкий': 'low', 'Средний': 'medium', 'Высокий': 'high', 'Критический': 'critical'
            }
            priority = priority_map.get(data.get('priority', 'medium'), 'medium')

            # Вставка задачи
            insert_stmt = text("""
                INSERT INTO public.tasks (
                    project_id, column_id, title, description, created_by, 
                    assigned_to, created_at, priority, position, difficulty,
                    deadline, progress_percent
                )
                VALUES (
                    :project_id, :column_id, :title, :description, :creator_id,
                    :assigned_to, NOW(), :priority, :position, :difficulty,
                    :deadline, 0
                )
                RETURNING id
            """)

            result = tasks_session.execute(insert_stmt, {
                'project_id': data['project_id'],
                'column_id': column_id,
                'title': data['title'],
                'description': data.get('description', ''),
                'creator_id': data['creator_id'],
                'assigned_to': data.get('assigned_to'),
                'priority': priority,
                'position': new_position,
                'difficulty': float(data.get('difficulty', 0)),
                'deadline': data.get('deadline')
            })
            tasks_session.commit()
            task_id = result.scalar()

            # Добавляем теги
            if data.get('tags'):
                for tag_name in data['tags']:
                    check_tag_stmt = text("SELECT id FROM public.tags WHERE name = :name")
                    existing_tag = tasks_session.execute(check_tag_stmt, {'name': tag_name}).first()

                    if existing_tag:
                        tag_id = existing_tag[0]
                    else:
                        insert_tag_stmt = text("""
                            INSERT INTO public.tags (name, created_at, updated_at)
                            VALUES (:name, NOW(), NOW())
                            RETURNING id
                        """)
                        tag = tasks_session.execute(insert_tag_stmt, {'name': tag_name}).first()
                        tag_id = tag[0] if tag else None

                    if tag_id:
                        link_stmt = text("""
                            INSERT INTO public.task_tags (task_id, tag_id)
                            VALUES (:task_id, :tag_id)
                            ON CONFLICT (task_id, tag_id) DO NOTHING
                        """)
                        tasks_session.execute(link_stmt, {'task_id': task_id, 'tag_id': tag_id})
                tasks_session.commit()

            return task_id