# services/tag_service.py

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from repositories.tag_repo import TagRepo
from database import get_tasks_session


class TagService:
    """Сервис для работы с тегами (использует TagRepo)"""

    def __init__(self, session: Session = None):
        self.session = session or get_tasks_session()
        self._own_session = session is None
        self.repo = TagRepo(self.session)

    def close(self):
        if self._own_session and self.session:
            self.session.close()

    def get_all_tags(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Возвращает все теги"""
        try:
            if include_archived:
                tags = self.repo.get_all(include_archived=True)
            else:
                tags = self.repo.get_all(include_archived=False)

            result = []
            for tag in tags:
                tag_dict = self._tag_to_dict(tag)
                tag_dict['usage_count'] = self.repo.get_tag_usage_count(tag.id)
                result.append(tag_dict)
            return result
        except Exception as e:
            print(f"❌ Ошибка загрузки тегов: {e}")
            return []

    def get_tag_by_id(self, tag_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает тег по ID"""
        try:
            tag = self.repo.get_by_id(tag_id)
            if tag and not tag.is_archived:
                return self._tag_to_dict(tag)
            return None
        except Exception as e:
            print(f"❌ Ошибка загрузки тега {tag_id}: {e}")
            return None

    def create_tag(self, tag_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создает новый тег"""
        try:
            existing = self.repo.get_by_name(tag_data.get('name'))
            if existing:
                print(f"⚠️ Тег с именем '{tag_data.get('name')}' уже существует")
                return None

            tag = self.repo.create(
                name=tag_data.get('name'),
                color=tag_data.get('color', '#ccab6e')
            )
            self.session.commit()
            return self._tag_to_dict(tag)
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании тега: {e}")
            return None

    def update_tag(self, tag_id: int, tag_data: Dict[str, Any]) -> bool:
        """Обновляет тег"""
        try:
            new_name = tag_data.get('name')
            if new_name:
                existing = self.repo.get_by_name(new_name)
                if existing and existing.id != tag_id:
                    print(f"⚠️ Тег с именем '{new_name}' уже существует")
                    return False

            tag = self.repo.update(tag_id, **tag_data)
            if tag:
                tag.updated_at = datetime.now()
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении тега: {e}")
            return False

    def delete_tag(self, tag_id: int) -> bool:
        """Удаляет тег (мягкое удаление - архивирует)"""
        try:
            tag = self.repo.archive(tag_id, archived=True)
            if tag:
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при удалении тега: {e}")
            return False

    def hard_delete_tag(self, tag_id: int) -> bool:
        """Полное удаление тега из БД"""
        try:
            success = self.repo.delete(tag_id)
            if success:
                self.session.commit()
            return success
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при полном удалении тега: {e}")
            return False

    def _tag_to_dict(self, tag) -> Dict[str, Any]:
        """Преобразует модель тега в словарь"""
        if tag is None:
            return {}
        return {
            'id': tag.id,
            'name': tag.name,
            'color': tag.color,
            'is_archived': tag.is_archived,
            'created_at': tag.created_at.isoformat() if tag.created_at else None,
            'updated_at': tag.updated_at.isoformat() if tag.updated_at else None,
        }