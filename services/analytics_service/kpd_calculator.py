# services/analytics_service/kpd_calculator.py

from typing import Dict, Optional
from datetime import datetime, date
from math import exp


class KPDCalculator:
    """Калькулятор КПД задач"""

    # Коэффициенты для разных параметров
    PRIORITY_WEIGHTS = {
        "low": 0.5,
        "medium": 1.0,
        "high": 1.5,
        "critical": 2.0
    }

    DIFFICULTY_WEIGHTS = {
        0: 0.5,  # Не задана
        1: 0.6,  # Очень низкая
        2: 0.8,  # Низкая
        3: 1.0,  # Средняя
        4: 1.2,  # Высокая
        5: 1.5  # Максимальная
    }

    @classmethod
    def calculate_task_kpd(cls, task_data: Dict) -> float:
        """
        Расчет КПД для одной задачи по формуле:
        KPD = (deadline_factor) * priority_weight * progress_factor * difficulty_weight

        где:
        - deadline_factor: коэффициент соблюдения дедлайна
        - priority_weight: вес приоритета
        - progress_factor: коэффициент прогресса выполнения
        - difficulty_weight: вес сложности
        """

        # 1. Фактор соблюдения дедлайна
        deadline_factor = cls._calculate_deadline_factor(task_data)

        # 2. Вес приоритета
        priority = task_data.get('priority', 'medium')
        priority_weight = cls.PRIORITY_WEIGHTS.get(priority, 1.0)

        # 3. Фактор прогресса
        progress_percent = task_data.get('progress_percent', 0)
        progress_factor = cls._calculate_progress_factor(progress_percent)

        # 4. Вес сложности
        difficulty = task_data.get('difficulty', 0)
        difficulty_weight = cls.DIFFICULTY_WEIGHTS.get(difficulty, 1.0)

        # Итоговый КПД задачи (нормализован от 0 до 100)
        raw_kpd = deadline_factor * priority_weight * progress_factor * difficulty_weight

        # Нормализация: максимальное значение около 2.0, поэтому делим на 2 и умножаем на 100
        normalized_kpd = min(100, (raw_kpd / 2.0) * 100)

        return round(normalized_kpd, 1)

    @classmethod
    def _calculate_deadline_factor(cls, task_data: Dict) -> float:
        """
        Расчет фактора соблюдения дедлайна.

        Если задача выполнена:
        - Раньше срока: 1.2-1.5
        - В срок: 1.0
        - С небольшим опозданием: 0.5-0.9
        - С большим опозданием: 0-0.4

        Если задача не выполнена:
        - Дедлайн не наступил: 0.5 (базовый)
        - Дедлайн наступил: 0
        """
        due_date_str = task_data.get('due_date_str')
        is_completed = task_data.get('is_completed', False)
        completed_at_str = task_data.get('completed_at_str')

        if not due_date_str or due_date_str == "Нет":
            # Нет дедлайна - базовый коэффициент
            return 0.8

        try:
            due_date = datetime.strptime(due_date_str, "%d.%m.%Y").date()
            today = date.today()

            if is_completed and completed_at_str:
                completed_date = datetime.strptime(completed_at_str, "%d.%m.%Y").date()
                days_diff = (due_date - completed_date).days

                if days_diff > 0:
                    # Выполнено раньше срока
                    if days_diff >= 7:
                        return 1.5  # На неделю раньше
                    elif days_diff >= 3:
                        return 1.3
                    else:
                        return 1.1
                elif days_diff == 0:
                    # В срок
                    return 1.0
                else:
                    # Просрочено
                    days_late = abs(days_diff)
                    if days_late <= 3:
                        return 0.7
                    elif days_late <= 7:
                        return 0.4
                    else:
                        return 0.1
            else:
                # Задача не выполнена
                days_remaining = (due_date - today).days
                if days_remaining >= 0:
                    # Дедлайн не наступил
                    return 0.5
                else:
                    # Дедлайн наступил, задача не выполнена
                    return 0.0

        except Exception as e:
            print(f"Ошибка расчета дедлайн фактора: {e}")
            return 0.5

    @classmethod
    def _calculate_progress_factor(cls, progress_percent: float) -> float:
        """
        Расчет фактора прогресса на основе процента выполнения.

        Формула: прогресс дает квадратичный рост КПД
        progress_factor = (progress_percent / 100) ^ 1.5 * 1.2
        """
        if progress_percent >= 100:
            return 1.2  # Полностью выполнена - бонус
        elif progress_percent <= 0:
            return 0.0
        else:
            # Квадратичный рост
            normalized = progress_percent / 100
            return normalized ** 1.5 * 1.2

    @classmethod
    def calculate_employee_kpd(cls, tasks: list, overtime_hours: float = 0) -> Dict:
        """
        Расчет общего КПД сотрудника по всем его задачам.

        Возвращает словарь с:
        - total_kpd: общий КПД
        - completed_tasks_count: количество выполненных задач
        - total_tasks_count: общее количество задач
        - weighted_kpd: взвешенный КПД с учетом прогресса
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
            task_kpd = cls.calculate_task_kpd(task)
            # Вес задачи - сложность + приоритет
            difficulty_weight = cls.DIFFICULTY_WEIGHTS.get(task.get('difficulty', 0), 1.0)
            priority_weight = cls.PRIORITY_WEIGHTS.get(task.get('priority', 'medium'), 1.0)
            task_weight = difficulty_weight * priority_weight

            total_weighted_kpd += task_kpd * task_weight
            total_weight += task_weight

            if task.get('is_completed', False):
                completed_count += 1

        # Средневзвешенное значение
        avg_kpd = (total_weighted_kpd / total_weight) if total_weight > 0 else 0

        # Штраф за переработки (если часов много)
        overtime_penalty = 1.0
        if overtime_hours > 20:
            overtime_penalty = 0.95
        elif overtime_hours > 40:
            overtime_penalty = 0.9
        elif overtime_hours > 60:
            overtime_penalty = 0.85

        final_kpd = avg_kpd * overtime_penalty

        return {
            "total_kpd": round(final_kpd, 1),
            "completed_tasks_count": completed_count,
            "total_tasks_count": len(tasks),
            "weighted_kpd": round(avg_kpd, 1),
            "overtime_hours": overtime_hours
        }