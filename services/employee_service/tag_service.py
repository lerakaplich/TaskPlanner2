# services/tag_service.py

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from models.tasks import Tag, TaskTag
from database import get_tasks_session


class TagService:
    """Сервис для работы с тегами (темами)"""

    def __init__(self, session: Session = None):
        self.session = session or get_tasks_session()
        self._own_session = session is None

    def close(self):
        if self._own_session and self.session:
            self.session.close()

    def get_all_tags(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Возвращает все теги"""
        try:
            query = self.session.query(Tag).order_by(Tag.name)
            if not include_archived:
                query = query.filter(Tag.is_archived == False)
            tags = query.all()
            return [self._tag_to_dict(tag) for tag in tags]
        except Exception as e:
            print(f"❌ Ошибка загрузки тегов: {e}")
            return []

    def get_tag_by_id(self, tag_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает тег по ID"""
        try:
            tag = self.session.get(Tag, tag_id)
            if tag and not tag.is_archived:
                return self._tag_to_dict(tag)
            return None
        except Exception as e:
            print(f"❌ Ошибка загрузки тега {tag_id}: {e}")
            return None

    def create_tag(self, tag_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создает новый тег"""
        try:
            existing = self.session.query(Tag).filter(Tag.name == tag_data.get('name')).first()
            if existing:
                print(f"⚠️ Тег с именем '{tag_data.get('name')}' уже существует")
                return None

            tag = Tag(
                name=tag_data.get('name'),
                color=tag_data.get('color', '#ccab6e')
            )
            self.session.add(tag)
            self.session.commit()
            self.session.refresh(tag)

            return self._tag_to_dict(tag)
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при создании тега: {e}")
            return None

    def update_tag(self, tag_id: int, tag_data: Dict[str, Any]) -> bool:
        """Обновляет тег"""
        try:
            tag = self.session.get(Tag, tag_id)
            if not tag or tag.is_archived:
                return False

            new_name = tag_data.get('name')
            if new_name and new_name != tag.name:
                existing = self.session.query(Tag).filter(Tag.name == new_name).first()
                if existing:
                    print(f"⚠️ Тег с именем '{new_name}' уже существует")
                    return False
                tag.name = new_name

            if 'color' in tag_data and tag_data['color']:
                tag.color = tag_data['color']

            tag.updated_at = datetime.now()
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при обновлении тега: {e}")
            return False

    def delete_tag(self, tag_id: int) -> bool:
        """Удаляет тег (мягкое удаление - архивирует)"""
        try:
            tag = self.session.get(Tag, tag_id)
            if tag:
                tag.is_archived = True
                tag.archived_at = datetime.now()
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
            tag = self.session.get(Tag, tag_id)
            if tag:
                self.session.delete(tag)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            print(f"❌ Ошибка при полном удалении тега: {e}")
            return False

    def get_tag_usage_count(self, tag_id: int) -> int:
        """Возвращает количество использований тега"""
        try:
            count = self.session.query(TaskTag).filter(TaskTag.tag_id == tag_id).count()
            return count
        except Exception as e:
            print(f"❌ Ошибка подсчета использований тега: {e}")
            return 0

    def add_tag_usage_count(self, tags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Добавляет количество использований к списку тегов"""
        result = []
        for tag in tags:
            tag_copy = tag.copy()
            tag_copy['usage_count'] = self.get_tag_usage_count(tag.get('id'))
            result.append(tag_copy)
        return result

    def _tag_to_dict(self, tag: Tag) -> Dict[str, Any]:
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
            'usage_count': 0
        }