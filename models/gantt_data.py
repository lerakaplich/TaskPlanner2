# models/gantt_data.py

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from models.schemas.tasks_dto import TaskDTO, TaskPriority


class GanttTaskData:
    """Адаптер задачи для диаграммы Ганта."""

    def __init__(
        self,
        task_dto: TaskDTO,
        get_employee_name: Optional[Callable[[int], str]] = None
    ):
        self.task_dto = task_dto
        self._get_employee_name = get_employee_name or (lambda x: f"ID:{x}")
        self._start_date = None
        self._end_date = None
        self._init_dates()

    def _init_dates(self):
        """Инициализация дат из DTO."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if hasattr(self.task_dto, 'start_date') and self.task_dto.start_date:
            self._start_date = datetime.combine(
                self.task_dto.start_date,
                datetime.min.time()
            )
        elif self.task_dto.deadline:
            self._start_date = datetime.combine(
                self.task_dto.deadline.date() - timedelta(days=7),
                datetime.min.time()
            )
        else:
            self._start_date = today

        if hasattr(self.task_dto, 'end_date') and self.task_dto.end_date:
            self._end_date = datetime.combine(
                self.task_dto.end_date,
                datetime.min.time()
            )
        elif self.task_dto.deadline:
            self._end_date = datetime.combine(
                self.task_dto.deadline.date(),
                datetime.min.time()
            )
        else:
            self._end_date = today + timedelta(days=7)

        if self._end_date <= self._start_date:
            self._end_date = self._start_date + timedelta(days=1)

    @property
    def id(self) -> int:
        return self.task_dto.id

    @property
    def title(self) -> str:
        return self.task_dto.title

    @property
    def priority(self) -> TaskPriority:
        return self.task_dto.priority

    @property
    def start_date(self) -> datetime:
        return self._start_date

    @property
    def end_date(self) -> datetime:
        return self._end_date

    @property
    def progress(self) -> int:
        return int(self.task_dto.progress_percent or 0)

    @property
    def assigned_to(self) -> str:
        """Возвращает имя сотрудника."""
        if self.task_dto.assigned_to:
            return self._get_employee_name(self.task_dto.assigned_to)
        return "Не назначен"

    @property
    def assigned_to_id(self) -> Optional[int]:
        return self.task_dto.assigned_to

    @property
    def project_id(self) -> int:
        return self.task_dto.project_id

    @property
    def duration_days(self) -> int:
        return max(1, (self._end_date - self._start_date).days)

    @property
    def is_completed(self) -> bool:
        return self.task_dto.completed_at is not None or self.progress == 100

    @property
    def is_overdue(self) -> bool:
        if self.is_completed or not self.task_dto.deadline:
            return False
        return datetime.now() > self.task_dto.deadline

    def update_dates(self, start_date: datetime, end_date: datetime):
        """Обновление дат задачи."""
        self._start_date = start_date
        self._end_date = end_date


def get_gantt_tasks_from_dto(
    tasks_dto: List[TaskDTO],
    get_employee_name: Optional[Callable[[int], str]] = None
) -> List[GanttTaskData]:
    """Преобразование списка TaskDTO в GanttTaskData."""
    return [GanttTaskData(task, get_employee_name) for task in tasks_dto]