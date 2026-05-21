"""
Сервис для работы с диаграммой Ганта.
Отвечает за расчёт позиций полос задач и связей между ними.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum


class Priority(str, Enum):
    """Приоритеты задач."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TaskGanttData:
    """DTO для отображения задачи на диаграмме Ганта."""
    id: int
    name: str
    executor_name: str
    executor_initials: str  # Фамилия И.О.
    start_date: datetime
    end_date: datetime
    priority: Priority
    project_id: int
    project_name: str
    color: str  # Цвет полосы в HEX


@dataclass
class TaskLink:
    """Связь между задачами."""
    from_task_id: int
    to_task_id: int


@dataclass
class ProjectGanttData:
    """DTO для проекта на диаграмме Ганта."""
    id: int
    name: str
    tasks: List[TaskGanttData]


class GanttService:
    """
    Сервис для расчёта позиций элементов на диаграмме Ганта.
    Отвечает за бизнес-логику отображения задач и связей.
    """

    # Цвета приоритетов
    PRIORITY_COLORS: Dict[Priority, str] = {
        Priority.CRITICAL: "#D22730",  # красный
        Priority.HIGH: "#ccab6e",      # золотой
        Priority.MEDIUM: "#1B232A",    # серый
        Priority.LOW: "#998664",       # светло-серый/золотистый
    }

    # Ширина одного дня в пикселях
    DAY_WIDTH: int = 30
    # Высота строки задачи
    ROW_HEIGHT: int = 40
    # Отступы
    HEADER_HEIGHT: int = 60
    LEFT_PADDING: int = 10

    def __init__(self) -> None:
        """Инициализация сервиса."""
        self._links: Dict[int, List[int]] = {}  # task_id -> [связанные task_id]
        self._projects: List[ProjectGanttData] = []
        self._all_tasks: List[TaskGanttData] = []

    def load_test_data(self) -> None:
        """
        Загрузка тестовых данных.
        Создаёт 2 проекта с задачами для демонстрации.
        """
        # Очистка предыдущих данных
        self._projects.clear()
        self._all_tasks.clear()
        self._links.clear()

        # Проект "Редизайн сайта" (id=1)
        project1_tasks = [
            TaskGanttData(
                id=1, name="Анализ конкурентов",
                executor_name="Иванов И.И.", executor_initials="И",
                start_date=datetime(2026, 5, 1),
                end_date=datetime(2026, 5, 10),
                priority=Priority.HIGH,
                project_id=1, project_name="Редизайн сайта",
                color=self.PRIORITY_COLORS[Priority.HIGH]
            ),
            TaskGanttData(
                id=2, name="Прототипирование",
                executor_name="Петрова А.С.", executor_initials="П",
                start_date=datetime(2026, 5, 11),
                end_date=datetime(2026, 5, 20),
                priority=Priority.CRITICAL,
                project_id=1, project_name="Редизайн сайта",
                color=self.PRIORITY_COLORS[Priority.CRITICAL]
            ),
            TaskGanttData(
                id=3, name="Дизайн макетов",
                executor_name="Сидоров Д.М.", executor_initials="С",
                start_date=datetime(2026, 5, 15),
                end_date=datetime(2026, 5, 25),
                priority=Priority.MEDIUM,
                project_id=1, project_name="Редизайн сайта",
                color=self.PRIORITY_COLORS[Priority.MEDIUM]
            ),
            TaskGanttData(
                id=4, name="Вёрстка",
                executor_name="Иванов И.И.", executor_initials="И",
                start_date=datetime(2026, 5, 21),
                end_date=datetime(2026, 6, 1),
                priority=Priority.HIGH,
                project_id=1, project_name="Редизайн сайта",
                color=self.PRIORITY_COLORS[Priority.HIGH]
            ),
        ]

        # Связи: 1→2, 2→3, 3→4
        self._links[1] = [2]
        self._links[2] = [3]
        self._links[3] = [4]

        project1 = ProjectGanttData(id=1, name="Редизайн сайта", tasks=project1_tasks)
        self._projects.append(project1)
        self._all_tasks.extend(project1_tasks)

        # Проект "Мобильное приложение" (id=2)
        project2_tasks = [
            TaskGanttData(
                id=5, name="ТЗ и аналитика",
                executor_name="Козлова Е.Н.", executor_initials="К",
                start_date=datetime(2026, 5, 1),
                end_date=datetime(2026, 5, 8),
                priority=Priority.CRITICAL,
                project_id=2, project_name="Мобильное приложение",
                color=self.PRIORITY_COLORS[Priority.CRITICAL]
            ),
            TaskGanttData(
                id=6, name="UI/UX дизайн",
                executor_name="Смирнова О.В.", executor_initials="С",
                start_date=datetime(2026, 5, 9),
                end_date=datetime(2026, 5, 22),
                priority=Priority.HIGH,
                project_id=2, project_name="Мобильное приложение",
                color=self.PRIORITY_COLORS[Priority.HIGH]
            ),
            TaskGanttData(
                id=7, name="Разработка API",
                executor_name="Новиков А.А.", executor_initials="Н",
                start_date=datetime(2026, 5, 12),
                end_date=datetime(2026, 5, 30),
                priority=Priority.HIGH,
                project_id=2, project_name="Мобильное приложение",
                color=self.PRIORITY_COLORS[Priority.HIGH]
            ),
            TaskGanttData(
                id=8, name="Тестирование",
                executor_name="Михайлов П.Р.", executor_initials="М",
                start_date=datetime(2026, 5, 25),
                end_date=datetime(2026, 6, 5),
                priority=Priority.MEDIUM,
                project_id=2, project_name="Мобильное приложение",
                color=self.PRIORITY_COLORS[Priority.MEDIUM]
            ),
        ]

        # Нет связей в этом проекте
        project2 = ProjectGanttData(id=2, name="Мобильное приложение", tasks=project2_tasks)
        self._projects.append(project2)
        self._all_tasks.extend(project2_tasks)

    def get_projects(self) -> List[ProjectGanttData]:
        """Получить все проекты."""
        return self._projects

    def get_all_tasks(self) -> List[TaskGanttData]:
        """Получить все задачи."""
        return self._all_tasks

    def get_task_links(self, task_id: int) -> List[int]:
        """Получить список ID задач, с которыми связана данная задача."""
        return self._links.get(task_id, [])

    def get_all_links(self) -> Dict[int, List[int]]:
        """Получить все связи."""
        return self._links

    def calculate_bar_position(
        self, task: TaskGanttData, start_date: datetime
    ) -> Tuple[int, int, int]:
        """
        Рассчитать позицию и размер полосы задачи.

        Args:
            task: Данные задачи.
            start_date: Начальная дата отображения диаграммы.

        Returns:
            Tuple[int, int, int]: (x-позиция, y-позиция, ширина в пикселях).
        """
        # Вычисляем количество дней от начала отображения
        days_from_start = (task.start_date - start_date).days
        task_duration = (task.end_date - task.start_date).days + 1

        x = self.LEFT_PADDING + days_from_start * self.DAY_WIDTH
        width = task_duration * self.DAY_WIDTH

        return x, width

    def get_day_position(self, date: datetime, start_date: datetime) -> int:
        """
        Получить x-координату для конкретной даты.

        Args:
            date: Дата.
            start_date: Начальная дата диаграммы.

        Returns:
            int: X-координата в пикселях.
        """
        days_from_start = (date - start_date).days
        return self.LEFT_PADDING + days_from_start * self.DAY_WIDTH

    def get_date_range(self, period: str) -> Tuple[datetime, datetime]:
        """
        Получить диапазон дат для выбранного периода.

        Args:
            period: Строка периода ("Неделя", "Месяц", "Полгода", "Год").

        Returns:
            Tuple[datetime, datetime]: (начало, конец).
        """
        today = datetime.now().replace(day=1)

        if period == "Неделя":
            start = today
            end = today + timedelta(days=7)
        elif period == "Месяц":
            start = today
            # Определяем конец месяца
            if today.month == 12:
                end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        elif period == "Полгода":
            start = today
            end = today + timedelta(days=180)
        elif period == "Год":
            start = today
            end = today + timedelta(days=365)
        else:
            # По умолчанию - месяц
            start = today
            end = today + timedelta(days=30)

        return start, end

    def add_link(self, from_task_id: int, to_task_id: int) -> None:
        """
        Добавить связь между задачами.

        Args:
            from_task_id: ID задачи-предшественника.
            to_task_id: ID задачи-последователя.
        """
        if from_task_id not in self._links:
            self._links[from_task_id] = []
        if to_task_id not in self._links[from_task_id]:
            self._links[from_task_id].append(to_task_id)

    def update_task_dates(
        self, task_id: int, new_start: datetime, new_end: datetime
    ) -> None:
        """
        Обновить даты задачи.

        Args:
            task_id: ID задачи.
            new_start: Новая дата начала.
            new_end: Новая дата окончания.
        """
        for task in self._all_tasks:
            if task.id == task_id:
                task.start_date = new_start
                task.end_date = new_end
                break

    def get_linked_tasks_for_update(
        self, task_id: int
    ) -> List[int]:
        """
        Получить список задач, которые должны двигаться вместе с данной.

        Args:
            task_id: ID перемещаемой задачи.

        Returns:
            List[int]: Список ID связанных задач.
        """
        linked = []
        # Задачи, которые зависят от этой
        if task_id in self._links:
            linked.extend(self._links[task_id])
        # Задачи, от которых зависит эта
        for tid, deps in self._links.items():
            if task_id in deps and tid not in linked:
                linked.append(tid)
        return linked