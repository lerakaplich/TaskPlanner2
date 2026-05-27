# services/tasks_service/tasks_tag_service.py

from typing import Dict, List, Optional
from sqlalchemy import select, delete

from models.tasks import Tag, TaskTag
from repositories.tag_repo import TagRepo


class TasksTagService:
    """Сервис для работы с тегами задач"""

    def __init__(self, db_session, repo, current_user=None, mode="all"):
        self.db_session = db_session
        self.repo = repo
        self.tag_repo = TagRepo(db_session)
        self.current_user = current_user
        self.mode = mode

    def get_all_tags(self, include_archived: bool = False) -> List[Dict]:
        """Получить все глобальные теги"""
        stmt = select(Tag)
        if not include_archived:
            stmt = stmt.where(Tag.is_archived == False)
        stmt = stmt.order_by(Tag.name)

        tags = list(self.db_session.scalars(stmt))
        return [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in tags]

    def get_all_tags_with_usage(self) -> List[Dict]:
        """Получить теги с количеством использований"""
        return self.tag_repo.get_all_tags_with_usage()

    def create_tag(self, name: str, color: str = "#ccab6e") -> Optional[Dict]:
        """Создать новый тег"""
        existing = self.tag_repo.get_by_name(name)
        if existing:
            return {"id": existing.id, "name": existing.name, "color": existing.color}

        try:
            tag = self.tag_repo.create(name, color)
            self.db_session.commit()
            return {"id": tag.id, "name": tag.name, "color": tag.color}
        except Exception as e:
            self.db_session.rollback()
            print(f"❌ Ошибка при создании тега: {e}")
            return None

    def get_task_tags(self, task_id: int) -> List[Dict]:
        """Получить теги задачи"""
        tags = self.tag_repo.get_task_tags(task_id)
        return [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in tags]

    def set_task_tags(self, task_id: int, tag_names: List[str]) -> bool:
        """Установить теги задачи по названиям"""
        if not tag_names:
            # Если нет тегов, удаляем все
            return self.tag_repo.set_task_tags(task_id, [])

        tag_ids = []
        for tag_name in tag_names:
            tag = self.tag_repo.get_by_name(tag_name)
            if not tag:
                # Создаём новый тег, если не существует
                tag = self.tag_repo.create(tag_name, "#ccab6e")
                self.db_session.flush()
            tag_ids.append(tag.id)

        result = self.tag_repo.set_task_tags(task_id, tag_ids)
        self.db_session.flush()
        return result

    def add_tag_to_task(self, task_id: int, tag_id: int) -> bool:
        """Добавить тег к задаче"""
        result = self.tag_repo.add_tag_to_task(task_id, tag_id)
        self.db_session.commit()
        return result

    def remove_tag_from_task(self, task_id: int, tag_id: int) -> bool:
        """Удалить тег из задачи"""
        result = self.tag_repo.remove_tag_from_task(task_id, tag_id)
        self.db_session.commit()
        return result

    def add_tags_to_task(self, task_id: int, tag_names: List[str]) -> List[str]:
        """Добавить теги к задаче (создавая новые при необходимости)"""
        task = self.repo.get_by_id(task_id)
        if not task:
            return []

        added_tags = []
        for tag_name in tag_names:
            tag = self.db_session.scalar(
                select(Tag).where(
                    Tag.project_id == task.project_id,
                    Tag.name == tag_name
                )
            )

            if not tag:
                tag = Tag(project_id=task.project_id, name=tag_name)
                self.db_session.add(tag)
                self.db_session.flush()

            existing = self.db_session.scalar(
                select(TaskTag).where(
                    TaskTag.task_id == task_id,
                    TaskTag.tag_id == tag.id
                )
            )

            if not existing:
                task_tag = TaskTag(task_id=task_id, tag_id=tag.id)
                self.db_session.add(task_tag)
                added_tags.append(tag_name)

        self.db_session.commit()
        return added_tags