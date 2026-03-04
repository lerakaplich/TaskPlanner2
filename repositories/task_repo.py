from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete

from models.tasks import Task, Tag, TaskTag


class TaskRepo:

    def __init__(self, session: Session):
        self.session = session

    # =========================
    # CRUD
    # =========================
    def get_by_id(self, task_id: int) -> Optional[Task]:
        return self.session.get(Task, task_id)

    def get_by_project(self, project_id: int) -> List[Task]:
        stmt = select(Task).where(Task.project_id == project_id)
        return list(self.session.scalars(stmt))

    def create(self, **kwargs) -> Task:
        task = Task(**kwargs)
        self.session.add(task)
        return task

    def delete(self, task_id: int):
        obj = self.get_by_id(task_id)
        if obj:
            self.session.delete(obj)

    # =========================
    # Position
    # =========================
    def update_position(self, task_id: int, new_position: int):
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(position=new_position)
        )
        self.session.execute(stmt)

    def move_to_column(self, task_id: int, column_id: int):
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(column_id=column_id)
        )
        self.session.execute(stmt)

    # =========================
    # Tags
    # =========================
    def create_tag(self, project_id: int, name: str) -> Tag:
        tag = Tag(project_id=project_id, name=name)
        self.session.add(tag)
        return tag

    def add_tag_to_task(self, task_id: int, tag_id: int):
        rel = TaskTag(task_id=task_id, tag_id=tag_id)
        self.session.add(rel)

    def remove_tag_from_task(self, task_id: int, tag_id: int):
        stmt = delete(TaskTag).where(
            TaskTag.task_id == task_id,
            TaskTag.tag_id == tag_id
        )
        self.session.execute(stmt)