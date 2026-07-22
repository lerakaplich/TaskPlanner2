# services/tasks_service/task_data_collector.py

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path


class TaskDataCollector:
    """
    Сбор данных о задачах для обучения нейросети.
    Данные сохраняются в JSON-файл.
    """

    def __init__(self, data_dir: str = "data/training"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache = []
        self._cache_size = 50  # Сохраняем в файл каждые 50 записей

    def collect_task_data(self, task_data: Dict, user_id: int, project_id: int) -> Dict:
        """
        Собирает все необходимые данные о задаче для обучения.
        Возвращает словарь с данными.
        """
        now = datetime.now()

        # === 1. БАЗОВЫЕ ДАННЫЕ О ЗАДАЧЕ ===
        task_info = {
            # Идентификация
            "task_id": task_data.get("id"),
            "project_id": project_id,
            "user_id": user_id,

            # Временные метки
            "created_at": task_data.get("created_at"),
            "started_at": task_data.get("started_at"),
            "completed_at": task_data.get("completed_at"),
            "deadline": task_data.get("deadline"),

            # Характеристики задачи
            "title": task_data.get("title", ""),
            "description_length": len(task_data.get("description", "")),
            "priority": task_data.get("priority", "medium"),
            "difficulty": float(task_data.get("difficulty", 0)),
            "progress_percent": float(task_data.get("progress_percent", 0)),

            # Время выполнения
            "actual_hours": float(task_data.get("actual_hours", 0)),
            "total_paused_seconds": int(task_data.get("total_paused_seconds", 0)),

            # Теги
            "tags": task_data.get("tags", []),

            # Статус
            "status": task_data.get("status"),
            "is_archived": task_data.get("is_archived", False),
            "is_paused": task_data.get("is_paused", False),
            "completed": task_data.get("completed", False),
        }

        # === 2. ВЫЧИСЛЯЕМЫЕ ХАРАКТЕРИСТИКИ ===
        # Длительность работы (эффективное время)
        effective_hours = self._calculate_effective_hours(task_info)
        task_info["effective_hours"] = effective_hours

        # Количество пауз
        task_info["pause_count"] = self._count_pauses(task_data)

        # Наличие дедлайна
        task_info["has_deadline"] = task_info.get("deadline") is not None

        # Дней до дедлайна (если есть)
        if task_info.get("deadline"):
            try:
                deadline = self._parse_date(task_info["deadline"])
                if deadline:
                    days_to_deadline = (deadline - now).days
                    task_info["days_to_deadline"] = days_to_deadline
                else:
                    task_info["days_to_deadline"] = None
            except:
                task_info["days_to_deadline"] = None

        # Просрочена ли задача
        task_info["is_overdue"] = self._check_overdue(task_info)

        # === 3. КОНТЕКСТНАЯ ИНФОРМАЦИЯ ===
        # Количество тегов
        task_info["tags_count"] = len(task_info.get("tags", []))

        # Сложность названия (количество слов)
        task_info["title_word_count"] = len(task_info.get("title", "").split())

        # Наличие описания
        task_info["has_description"] = bool(task_info.get("description_length", 0) > 0)

        return task_info

    def _calculate_effective_hours(self, task_info: Dict) -> float:
        """Рассчитывает эффективное время работы (без пауз)"""
        actual_hours = task_info.get("actual_hours", 0)
        paused_seconds = task_info.get("total_paused_seconds", 0)
        paused_hours = paused_seconds / 3600.0

        # Если есть actual_hours - используем его, но вычитаем паузы
        if actual_hours > 0:
            return max(0, actual_hours - paused_hours)

        # Если нет actual_hours, но есть started_at и completed_at
        started = task_info.get("started_at")
        completed = task_info.get("completed_at")
        if started and completed:
            try:
                start_dt = self._parse_datetime(started)
                end_dt = self._parse_datetime(completed)
                if start_dt and end_dt:
                    total_hours = (end_dt - start_dt).total_seconds() / 3600.0
                    return max(0, total_hours - paused_hours)
            except:
                pass

        return 0.0

    def _count_pauses(self, task_data: Dict) -> int:
        """Подсчитывает количество пауз (по total_paused_seconds и is_paused)"""
        count = 0
        if task_data.get("total_paused_seconds", 0) > 0:
            count += 1
        if task_data.get("is_paused", False):
            count += 1
        return count

    def _parse_datetime(self, value) -> Optional[datetime]:
        """Парсит дату/время из разных форматов"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                # Пробуем разные форматы
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y", "%d.%m.%Y %H:%M"]:
                    try:
                        return datetime.strptime(value, fmt)
                    except:
                        continue
            except:
                pass
        return None

    def _parse_date(self, value) -> Optional[datetime]:
        """Парсит дату (без времени)"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                for fmt in ["%Y-%m-%d", "%d.%m.%Y"]:
                    try:
                        return datetime.strptime(value, fmt)
                    except:
                        continue
            except:
                pass
        return None

    def _check_overdue(self, task_info: Dict) -> bool:
        """Проверяет, просрочена ли задача"""
        if task_info.get("completed", False):
            return False
        deadline = task_info.get("deadline")
        if not deadline:
            return False
        try:
            deadline_dt = self._parse_datetime(deadline)
            if deadline_dt:
                return datetime.now() > deadline_dt
        except:
            pass
        return False

    def save_task_data(self, task_data: Dict, user_id: int, project_id: int):
        """Сохраняет данные о задаче в файл для обучения"""
        # Собираем данные
        data = self.collect_task_data(task_data, user_id, project_id)

        # Добавляем в кэш
        self._cache.append(data)

        # Если кэш заполнен - сохраняем в файл
        if len(self._cache) >= self._cache_size:
            self.flush_cache()

        return data

    def flush_cache(self):
        """Сохраняет кэш в файл и очищает его"""
        if not self._cache:
            return

        # Генерируем имя файла с датой
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.data_dir / f"tasks_data_{date_str}.json"

        # Загружаем существующие данные (если файл есть)
        existing_data = []
        if filename.exists():
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except:
                pass

        # Добавляем новые данные
        all_data = existing_data + self._cache

        # Сохраняем
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2, default=str)

        print(f"📊 Сохранено {len(self._cache)} записей о задачах в {filename}")
        self._cache = []

    def save_on_exit(self):
        """Сохраняет все данные при завершении работы"""
        self.flush_cache()

    def get_training_data(self, limit: int = None) -> List[Dict]:
        """
        Возвращает все собранные данные для обучения.
        """
        all_data = []

        # Читаем все JSON файлы в директории
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_data.extend(data)
                    elif isinstance(data, dict):
                        all_data.append(data)
            except Exception as e:
                print(f"⚠️ Ошибка чтения {file_path}: {e}")

        if limit:
            return all_data[:limit]
        return all_data

    def prepare_for_training(self) -> Dict:
        """
        Подготавливает данные для обучения нейросети.
        Возвращает словарь с признаками и целевыми значениями.
        """
        data = self.get_training_data()

        features = []
        targets = []

        for record in data:
            # Признаки
            feature = {
                "difficulty": record.get("difficulty", 0),
                "priority": self._encode_priority(record.get("priority", "medium")),
                "tags_count": record.get("tags_count", 0),
                "description_length": record.get("description_length", 0),
                "title_word_count": record.get("title_word_count", 0),
                "has_deadline": 1 if record.get("has_deadline") else 0,
                "days_to_deadline": record.get("days_to_deadline", 30),
            }

            # Целевое значение - эффективное время в часах
            target = record.get("effective_hours", 0)

            # Пропускаем записи с нулевым временем
            if target > 0:
                features.append(feature)
                targets.append(target)

        return {
            "features": features,
            "targets": targets,
            "total_records": len(features)
        }


# Глобальный экземпляр для использования во всем приложении
_task_data_collector = None


def get_task_data_collector() -> TaskDataCollector:
    """Возвращает глобальный экземпляр сборщика данных"""
    global _task_data_collector
    if _task_data_collector is None:
        _task_data_collector = TaskDataCollector()
    return _task_data_collector