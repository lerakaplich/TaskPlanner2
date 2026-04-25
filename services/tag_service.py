# services/tag_service.py

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from repositories.tag_repo import TagRepo
from models.tasks import Tag


class TagService:
    """Сервис для работы с глобальными тегами"""

    def __init__(self, session: Session):
        self.session = session
        self.repo = TagRepo(session)

    def get_all_tags(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Получить все теги (глобально)"""
        tags = self.repo.get_all_with_usage() if include_archived else self.repo.get_all_tags_with_usage()
        return tags

    def get_tag_by_id(self, tag_id: int) -> Optional[Dict[str, Any]]:
        tag = self.repo.get_by_id(tag_id)
        if tag:
            return {
                'id': tag.id,
                'name': tag.name,
                'color': tag.color,
                'is_archived': tag.is_archived,
                'usage_count': self.repo.get_tag_usage_count(tag.id),
                'created_at': tag.created_at.isoformat() if tag.created_at else None,
                'updated_at': tag.updated_at.isoformat() if tag.updated_at else None
            }
        return None

    def create_tag(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создать новый тег"""
        try:
            name = data.get('name', '').strip()
            if not name:
                print("❌ Имя тега не может быть пустым")
                return None

            # Проверяем, существует ли уже такой тег
            existing = self.repo.get_by_name(name)
            if existing:
                print(f"⚠️ Тег с именем '{name}' уже существует")
                return None

            color = data.get('color', '#ccab6e')

            tag = self.repo.create(name, color)
            self.session.commit()

            return {
                'id': tag.id,
                'name': tag.name,
                'color': tag.color,
                'is_archived': tag.is_archived,
                'usage_count': 0,
                'created_at': tag.created_at.isoformat() if tag.created_at else None,
                'updated_at': tag.updated_at.isoformat() if tag.updated_at else None
            }

        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании тега: {e}")
            return None

    def update_tag(self, tag_id: int, data: Dict[str, Any]) -> bool:
        try:
            # Если меняем имя, проверяем уникальность
            if 'name' in data:
                existing = self.repo.get_by_name(data['name'])
                if existing and existing.id != tag_id:
                    print(f"⚠️ Тег с именем '{data['name']}' уже существует")
                    return False

            tag = self.repo.update(tag_id, **data)
            if tag:
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении тега: {e}")
            return False

    def delete_tag(self, tag_id: int) -> bool:
        try:
            result = self.repo.delete(tag_id)
            if result:
                self.session.commit()
            return result
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при удалении тега: {e}")
            return False

    def archive_tag(self, tag_id: int, archived: bool = True) -> bool:
        try:
            tag = self.repo.archive(tag_id, archived)
            if tag:
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при архивации тега: {e}")
            return False

    # =========================
    # Работа со связями задач и тегов
    # =========================
    def add_tag_to_task(self, task_id: int, tag_id: int) -> bool:
        try:
            result = self.repo.add_tag_to_task(task_id, tag_id)
            self.session.commit()
            return result
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при добавлении тега к задаче: {e}")
            return False

    def remove_tag_from_task(self, task_id: int, tag_id: int) -> bool:
        try:
            result = self.repo.remove_tag_from_task(task_id, tag_id)
            self.session.commit()
            return result
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при удалении тега из задачи: {e}")
            return False

    def get_task_tags(self, task_id: int) -> List[Dict[str, Any]]:
        tags = self.repo.get_task_tags(task_id)
        return [{
            'id': tag.id,
            'name': tag.name,
            'color': tag.color
        } for tag in tags]

    def set_task_tags(self, task_id: int, tag_ids: List[int]) -> bool:
        try:
            result = self.repo.set_task_tags(task_id, tag_ids)
            self.session.commit()
            return result
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при установке тегов задачи: {e}")
            return False