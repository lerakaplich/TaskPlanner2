# services/analytics_service/kpd_calculator.py

from typing import Dict, Optional, List
from datetime import datetime, date
from math import exp


class KPDCalculator:
    """Калькулятор КПД задач - использует встроенные поля задачи"""

    # Коэффициенты для разных параметров
    PRIORITY_WEIGHTS = {
        "low": 0.5,
        "medium": 1.0,
        "high": 1.5,
        "critical": 2.0
    }

    DIFFICULTY_WEIGHTS = {
        0: 0.0,  # Не задана
        1: 0.2,  # Очень низкая
        2: 0.4,  # Низкая
        3: 0.6,  # Средняя
        4: 0.8,  # Высокая
        5: 1.0  # Максимальная
    }

    @classmethod
    def calculate_task_kpd(cls, task) -> float:
        """
        Расчет КПД для одной задачи.
        Использует встроенные свойства задачи.

        Args:
            task: объект Task с полями:
                - difficulty (float)
                - priority (TaskPriorityEnum)
                - completed_at (datetime)
                - created_at (datetime)
                - deadline (datetime)
                - progress_percent (float)

        Returns:
            float: КПД задачи (0-100)
        """
        # Если задача не завершена - КПД 0
        if not task.completed:
            return 0.0

        # Используем встроенные свойства задачи
        difficulty_factor = cls.DIFFICULTY_WEIGHTS.get(int(task.difficulty), 1.0)
        priority_factor = task.priority_factor
        efficiency_factor = task.efficiency_factor
        progress_factor = 1.0  # Для завершенных задач = 1

        # Расчет
        raw_score = difficulty_factor * priority_factor * efficiency_factor * progress_factor

        # Нормализация: максимальное значение ~ 1.8-2.0, переводим в 0-100
        normalized = min(100, (raw_score / 2.0) * 100)

        return round(normalized, 1)

    @classmethod
    def calculate_employee_kpd(cls, tasks: List) -> Dict:
        """
        Расчет общего КПД сотрудника по всем его задачам.
        Использует встроенные поля задач.

        Args:
            tasks: список объектов Task

        Returns:
            Dict с ключами:
                - total_kpd: общий КПД
                - completed_tasks_count: количество выполненных задач
                - total_tasks_count: общее количество задач
                - weighted_kpd: взвешенный КПД
        """
        if not tasks:
            return {
                "total_kpd": 0,
                "completed_tasks_count": 0,
                "total_tasks_count": 0,
                "weighted_kpd": 0
            }

        total_weighted_kpd = 0
        completed_count = 0
        total_weight = 0

        for task in tasks:
            if task.completed:
                task_kpd = task.kpd_score / 100  # Переводим в 0-1
                completed_count += 1
            else:
                task_kpd = 0

            # Вес задачи: сложность * приоритет
            difficulty_weight = cls.DIFFICULTY_WEIGHTS.get(int(task.difficulty), 1.0)
            priority_weight = cls.PRIORITY_WEIGHTS.get(task.priority.value, 1.0)
            task_weight = difficulty_weight * priority_weight

            total_weighted_kpd += task_kpd * task_weight
            total_weight += task_weight

        # Средневзвешенное значение
        avg_kpd = (total_weighted_kpd / total_weight) * 100 if total_weight > 0 else 0

        return {
            "total_kpd": round(avg_kpd, 1),
            "completed_tasks_count": completed_count,
            "total_tasks_count": len(tasks),
            "weighted_kpd": round(avg_kpd, 1)
        }

    @classmethod
    def get_task_priority_weight(cls, priority: str) -> float:
        """Получить вес приоритета"""
        return cls.PRIORITY_WEIGHTS.get(priority, 1.0)

    @classmethod
    def get_difficulty_weight(cls, difficulty: int) -> float:
        """Получить вес сложности"""
        return cls.DIFFICULTY_WEIGHTS.get(difficulty, 1.0)