"""
Модель данных для диаграммы Ганта.
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Optional

from models.schemas.tasks_dto import TaskDTO, TaskPriority


class GanttTaskData:
    """Адаптер задачи для диаграммы Ганта."""

    # Словарь для соответствия ID сотрудника -> имени (временно для тестов)
    # В реальном приложении нужно получать из сервиса сотрудников
    _EMPLOYEES_NAMES: Dict[int, str] = {
        101: "Иванов А.А.",
        102: "Петрова М.С.",
        103: "Сидоров К.В.",
        104: "Козлова Е.Д.",
        105: "Морозова А.В.",
        106: "Волков Д.С.",
        107: "Соколов П.Н.",
        108: "Белова И.К.",
    }

    def __init__(self, task_dto: TaskDTO):
        self.task_dto = task_dto
        self._start_date = None
        self._end_date = None
        self._init_dates()

    def _init_dates(self):
        """Инициализация дат из DTO."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if self.task_dto.start_date:
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

        if self.task_dto.end_date:
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
        return self.task_dto.progress

    @property
    def assigned_to(self) -> str:
        """Возвращает имя сотрудника, а не ID."""
        if self.task_dto.assigned_to:
            return self._EMPLOYEES_NAMES.get(self.task_dto.assigned_to, f"ID:{self.task_dto.assigned_to}")
        return "Не назначен"

    @property
    def assigned_to_id(self) -> Optional[int]:
        """Возвращает ID сотрудника."""
        return self.task_dto.assigned_to

    @property
    def project_id(self) -> int:
        return self.task_dto.project_id

    @property
    def duration_days(self) -> int:
        return max(1, (self._end_date - self._start_date).days)

    def update_dates(self, start_date: datetime, end_date: datetime):
        """Обновление дат задачи."""
        self._start_date = start_date
        self._end_date = end_date


def get_gantt_tasks_from_dto(tasks_dto: List[TaskDTO]) -> List[GanttTaskData]:
    """Преобразование списка TaskDTO в GanttTaskData."""
    return [GanttTaskData(task) for task in tasks_dto]