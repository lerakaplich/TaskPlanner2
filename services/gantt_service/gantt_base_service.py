# services/gantt_service/gantt_base_service.py

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class TaskGanttData:
    """Данные задачи для отображения на диаграмме Ганта"""
    id: int
    name: str
    start_date: datetime
    end_date: datetime
    executor_name: str
    executor_initials: str
    executor_id: Optional[int]
    color: str
    priority: str
    progress: float
    project_id: int
    project_name: str
    status: str
    dependencies: List[Dict] = None  # <-- используем None вместо field

    def __post_init__(self):
        """Инициализация после создания"""
        if self.dependencies is None:
            self.dependencies = []

    @property
    def duration_days(self) -> int:
        return max(1, (self.end_date - self.start_date).days + 1)


class GanttBaseService:
    """Базовый сервис с константами и утилитами"""

    # Константы для отрисовки
    DAY_WIDTH = 30
    ROW_HEIGHT = 50
    HEADER_HEIGHT = 55
    LEFT_PADDING = 0

    # Цвета для приоритетов
    PRIORITY_COLORS = {
        "critical": "#D22730",
        "high": "#ccab6e",
        "medium": "#1B232A",
        "low": "#998664"
    }

    PRIORITY_NAMES = {
        "critical": "Критический",
        "high": "Высокий",
        "medium": "Средний",
        "low": "Низкий"
    }

    @classmethod
    def translate_priority(cls, priority: str) -> str:
        """Переводит код приоритета в читаемое название"""
        return cls.PRIORITY_NAMES.get(priority, priority)

    @classmethod
    def get_priority_color(cls, priority: str) -> str:
        """Возвращает цвет для приоритета"""
        return cls.PRIORITY_COLORS.get(priority, cls.PRIORITY_COLORS["medium"])

    @classmethod
    def get_initials(cls, user: Dict) -> str:
        """Получает инициалы пользователя"""
        first = user.get('first_name', '')
        last = user.get('last_name', '')
        if last and first:
            return f"{last[0]}{first[0]}".upper()
        return "??"