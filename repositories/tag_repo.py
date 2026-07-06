# repositories/tag_repo.py
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, func

from models.tasks import Tag, TaskTag


class TagRepo:
    """Репозиторий для работы с тегами"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, tag_id: int) -> Optional[Tag]:
        return self.session.get(Tag, tag_id)

    def get_by_name(self, name: str) -> Optional[Tag]:
        stmt = select(Tag).where(Tag.name == name)
        return self.session.scalar(stmt)

    def get_all(self) -> List[Tag]:
        """Получить все теги (архивации нет)"""
        stmt = select(Tag).order_by(Tag.name)
        return list(self.session.scalars(stmt))

    def create(self, name: str, color: str = "#ccab6e") -> Tag:
        """Создать новый тег"""
        tag = Tag(
            name=name.strip(),
            color=color,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.session.add(tag)
        self.session.flush()
        return tag

    def update(self, tag_id: int, **kwargs) -> Optional[Tag]:
        tag = self.get_by_id(tag_id)
        if tag:
            for key, value in kwargs.items():
                if hasattr(tag, key):
                    setattr(tag, key, value)
            tag.updated_at = datetime.now()
            self.session.flush()
        return tag

    def delete(self, tag_id: int) -> bool:
        """Удалить тег (полное удаление)"""
        tag = self.get_by_id(tag_id)
        if tag:
            self.session.delete(tag)
            self.session.flush()
            return True
        return False

    def get_tag_usage_count(self, tag_id: int) -> int:
        stmt = select(func.count()).where(TaskTag.tag_id == tag_id)
        return self.session.scalar(stmt) or 0

    def get_all_tags_with_usage(self) -> List[dict]:
        """Получить все теги с количеством использований"""
        tags = self.get_all()
        result = []
        for tag in tags:
            result.append({
                'id': tag.id,
                'name': tag.name,
                'color': tag.color,
                'usage_count': self.get_tag_usage_count(tag.id),
                'created_at': tag.created_at,
                'updated_at': tag.updated_at
            })
        return result

    def add_tag_to_task(self, task_id: int, tag_id: int) -> bool:
        existing = self.session.query(TaskTag).filter(
            TaskTag.task_id == task_id,
            TaskTag.tag_id == tag_id
        ).first()
        if existing:
            return False

        task_tag = TaskTag(task_id=task_id, tag_id=tag_id)
        self.session.add(task_tag)
        self.session.flush()
        return True

    def remove_tag_from_task(self, task_id: int, tag_id: int) -> bool:
        stmt = delete(TaskTag).where(
            TaskTag.task_id == task_id,
            TaskTag.tag_id == tag_id
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount > 0

    def get_task_tags(self, task_id: int) -> List[Tag]:
        stmt = select(Tag).join(TaskTag).where(TaskTag.task_id == task_id)
        return list(self.session.scalars(stmt))

    def set_task_tags(self, task_id: int, tag_ids: List[int]) -> bool:
        """Установить теги задачи (полная замена)"""
        try:
            # Удаляем все старые связи
            stmt = delete(TaskTag).where(TaskTag.task_id == task_id)
            self.session.execute(stmt)

            # Добавляем новые
            for tag_id in tag_ids:
                self.session.add(TaskTag(task_id=task_id, tag_id=tag_id))

            self.session.flush()
            return True
        except Exception as e:
            print(f"❌ Ошибка при установке тегов: {e}")
            self.session.rollback()
            return False

    def get_tasks_by_tag(self, tag_id: int) -> List[int]:
        """Получить ID всех задач с данным тегом"""
        stmt = select(TaskTag.task_id).where(TaskTag.tag_id == tag_id)
        return list(self.session.scalars(stmt))