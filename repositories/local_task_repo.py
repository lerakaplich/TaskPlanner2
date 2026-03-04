from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from models.tasks import Task


class LocalTaskRepo:

    def __init__(self, session: Session):
        self.session = session

    def get_overdue_tasks(self) -> List[Task]:
        stmt = select(Task).where(
            Task.deadline.is_not(None),
            Task.deadline < func.now()
        )
        return list(self.session.scalars(stmt))

    def count_by_project(self, project_id: int) -> int:
        stmt = select(func.count()).where(Task.project_id == project_id)
        return self.session.scalar(stmt)

    def count_done_tasks(self, project_id: int, done_column_ids: List[int]) -> int:
        stmt = select(func.count()).where(
            Task.project_id == project_id,
            Task.column_id.in_(done_column_ids)
        )
        return self.session.scalar(stmt)