# server_app/services/tasks_service/task_data_collector.py

"""
Сбор данных о задачах для обучения модели на СЕРВЕРЕ.
Данные сохраняются в БД и JSON-файлы.
Обучение происходит на сервере, модель общая для всех клиентов.
"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import select, func

from server_app.database import get_tasks_session, get_employees_session
from models.tasks import Task, TaskTag, Tag
from models.projects import BoardColumn


class TaskDataCollector:
    """
    Сбор данных о задачах для обучения модели на сервере.
    Работает с БД taskplanner и employees.
    Модель обучается на сервере и доступна всем клиентам.
    """

    def __init__(self, data_dir: str = "server_app/data/training"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._cache = []
        self._cache_size = 50  # Сохраняем в файл каждые 50 записей

        self._training_lock = threading.Lock()
        self._last_training_time: Optional[datetime] = None
        self._min_samples_for_training = 10  # Минимум завершённых задач для обучения

        # Статистика обучения
        self._stats = {
            'total_collected': 0,
            'total_trained': 0,
            'last_result': None,
            'last_error': None
        }

    # ==========================================================
    # ОСНОВНЫЕ МЕТОДЫ
    # ==========================================================

    def collect_and_save_task(self, task_id: int) -> Optional[Dict]:
        """
        Собирает данные о задаче и сохраняет их.
        Вызывается при завершении задачи, изменении статуса.
        """
        session = get_tasks_session()
        try:
            task = session.get(Task, task_id)
            if not task:
                print(f"❌ Задача {task_id} не найдена")
                return None

            # Собираем данные
            task_info = self._collect_task_data(task, session)

            # Сохраняем в кэш и файл
            self._cache.append(task_info)
            self._stats['total_collected'] += 1

            # Проверяем, нужно ли обучать модель
            if task.completed and task.actual_hours > 0:
                self._try_train_model(session)

            # Если кэш переполнен - сохраняем
            if len(self._cache) >= self._cache_size:
                self.flush_cache()

            return task_info

        except Exception as e:
            print(f"❌ Ошибка сбора данных задачи {task_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            session.close()

    def collect_all_completed_tasks(self) -> List[Dict]:
        """
        Собирает все завершённые задачи из БД.
        Используется для первоначального обучения.
        """
        session = get_tasks_session()
        try:
            stmt = select(Task).where(
                Task.completed == True,
                Task.actual_hours > 0
            )
            tasks = session.scalars(stmt).all()

            collected = []
            for task in tasks:
                task_info = self._collect_task_data(task, session)
                collected.append(task_info)
                self._cache.append(task_info)

            self._stats['total_collected'] += len(collected)
            print(f"📊 Собрано {len(collected)} завершённых задач")
            return collected

        except Exception as e:
            print(f"❌ Ошибка сбора завершённых задач: {e}")
            return []
        finally:
            session.close()

    def _try_train_model(self, session):
        """
        Проверяет, достаточно ли данных, и запускает обучение.
        """
        # Считаем завершённые задачи в БД
        stmt = select(func.count(Task.id)).where(
            Task.completed == True,
            Task.actual_hours > 0
        )
        completed_count = session.scalar(stmt) or 0

        # Считаем завершённые задачи в кэше
        cached_completed = len([
            d for d in self._cache
            if d.get('completed', False) and d.get('effective_hours', 0) > 0
        ])

        total_completed = completed_count + cached_completed

        print(f"📊 Всего завершённых задач: {total_completed} (БД: {completed_count}, кэш: {cached_completed})")

        if total_completed >= self._min_samples_for_training:
            self._train_model_on_all_data()
        else:
            print(f"⏳ Ждём ещё данных: {total_completed}/{self._min_samples_for_training}")

    # ==========================================================
    # СБОР ДАННЫХ
    # ==========================================================

    def _collect_task_data(self, task: Task, session) -> Dict:
        """
        Собирает все данные о задаче.
        """
        now = datetime.now()

        # Получаем информацию о создателе и исполнителе
        creator_info = self._get_employee_info(task.created_by)
        assignee_info = self._get_employee_info(task.assigned_to)

        # Получаем теги
        tag_names = []
        if task.tags:
            for task_tag in task.tags:
                if task_tag.tag:
                    tag_names.append(task_tag.tag.name)

        # Получаем колонку
        column_name = None
        if task.column:
            column_name = task.column.name
            is_done = task.column.is_done_column
        else:
            is_done = task.completed

        # Базовые данные
        task_info = {
            # Идентификация
            "task_id": task.id,
            "project_id": task.project_id,
            "user_id": task.created_by,

            # Временные метки
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "deadline": task.deadline.isoformat() if task.deadline else None,

            # Характеристики задачи
            "title": task.title or "",
            "description_length": len(task.description) if task.description else 0,
            "priority": task.priority.value if task.priority else "medium",
            "difficulty": float(task.difficulty) if task.difficulty else 0,
            "progress_percent": float(task.progress_percent) if task.progress_percent else 0,

            # Время выполнения
            "actual_hours": float(task.actual_hours) if task.actual_hours else 0,
            "planned_hours": float(task.planned_hours) if task.planned_hours else 0,
            "total_paused_seconds": int(task.total_paused_seconds) if task.total_paused_seconds else 0,

            # Теги
            "tags": tag_names,

            # Статус
            "status": column_name,
            "is_archived": task.is_archived,
            "is_paused": task.is_paused,
            "completed": task.completed,

            # Создатель и исполнитель
            "created_by_name": creator_info.get('name') if creator_info else None,
            "assigned_to_name": assignee_info.get('name') if assignee_info else None,
            "assigned_to_position": assignee_info.get('position') if assignee_info else None,
        }

        # Вычисляемые характеристики
        task_info["effective_hours"] = self._calculate_effective_hours(task_info)
        task_info["pause_count"] = 1 if task.total_paused_seconds > 0 else 0

        task_info["has_deadline"] = task.deadline is not None
        if task.deadline:
            days_to_deadline = (task.deadline - now).days
            task_info["days_to_deadline"] = days_to_deadline
        else:
            task_info["days_to_deadline"] = None

        task_info["is_overdue"] = self._check_overdue(task, now)
        task_info["tags_count"] = len(tag_names)
        task_info["title_word_count"] = len(task_info["title"].split())
        task_info["has_description"] = task_info["description_length"] > 0

        return task_info

    def _get_employee_info(self, employee_id: Optional[int]) -> Optional[Dict]:
        """
        Получает информацию о сотруднике из БД employees.
        """
        if not employee_id:
            return None

        try:
            session = get_employees_session()
            from models.employees import Employee

            employee = session.get(Employee, employee_id)
            if employee:
                first_initial = f"{employee.first_name[0]}." if employee.first_name else ""
                middle_initial = f"{employee.middle_name[0]}." if employee.middle_name else ""
                return {
                    "id": employee.id,
                    "name": f"{employee.last_name} {first_initial}{middle_initial}".strip(),
                    "last_name": employee.last_name,
                    "first_name": employee.first_name,
                    "middle_name": employee.middle_name,
                    "position": employee.position
                }
            session.close()
        except Exception as e:
            print(f"⚠️ Ошибка получения информации о сотруднике {employee_id}: {e}")

        return None

    def _calculate_effective_hours(self, task_info: Dict) -> float:
        """
        Рассчитывает эффективное время работы (без пауз).
        """
        actual_hours = task_info.get("actual_hours", 0)
        paused_seconds = task_info.get("total_paused_seconds", 0)
        paused_hours = paused_seconds / 3600.0

        if actual_hours > 0:
            effective = max(0, actual_hours - paused_hours)
            if effective == 0 and task_info.get("completed", False):
                return 0.1
            return effective

        # Если нет actual_hours, но есть started_at и completed_at
        started = task_info.get("started_at")
        completed = task_info.get("completed_at")
        if started and completed:
            try:
                start_dt = datetime.fromisoformat(started)
                end_dt = datetime.fromisoformat(completed)
                total_hours = (end_dt - start_dt).total_seconds() / 3600.0
                effective = max(0, total_hours - paused_hours)
                if effective == 0 and task_info.get("completed", False):
                    return 0.1
                return effective
            except Exception:
                pass

        if task_info.get("completed", False):
            return 0.1

        return 0.0

    def _check_overdue(self, task: Task, now: datetime) -> bool:
        """Проверяет, просрочена ли задача."""
        if task.completed:
            return False
        if not task.deadline:
            return False
        return now > task.deadline

    # ==========================================================
    # ОБУЧЕНИЕ МОДЕЛИ
    # ==========================================================

    def _train_model_on_all_data(self):
        """
        Обучает модель на всех собранных данных.
        Вызывается при накоплении достаточного количества завершённых задач.
        """
        with self._training_lock:
            try:
                print("🧠 Запуск обучения модели на сервере...")

                # Получаем все данные
                all_data = self.get_training_data()

                # Проверяем количество завершённых задач
                completed = [
                    d for d in all_data
                    if d.get('completed', False) and d.get('effective_hours', 0) > 0
                ]

                if len(completed) < self._min_samples_for_training:
                    print(f"⏳ Недостаточно завершённых задач: {len(completed)}/{self._min_samples_for_training}")
                    return

                # Импортируем предсказатель
                from server_app.ml.task_time_predictor import get_task_predictor
                predictor = get_task_predictor()

                # Обучаем модель
                result = predictor.train(all_data)

                self._stats['total_trained'] += 1
                self._stats['last_result'] = result
                self._last_training_time = datetime.now()

                print(f"✅ Обучение завершено: {result}")

                # Сохраняем статистику в файл
                self._save_training_stats()

            except Exception as e:
                error_msg = str(e)
                print(f"❌ Ошибка обучения: {error_msg}")
                import traceback
                traceback.print_exc()
                self._stats['last_error'] = error_msg

    def force_train(self) -> Dict:
        """
        Принудительное обучение модели на всех данных.
        Вызывается вручную или по расписанию.
        """
        with self._training_lock:
            try:
                all_data = self.get_training_data()
                from server_app.ml.task_time_predictor import get_task_predictor
                predictor = get_task_predictor()
                result = predictor.train(all_data)
                self._stats['total_trained'] += 1
                self._stats['last_result'] = result
                self._last_training_time = datetime.now()
                return result
            except Exception as e:
                return {'status': 'error', 'message': str(e)}

    # ==========================================================
    # РАБОТА С ДАННЫМИ
    # ==========================================================

    def get_training_data(self, limit: int = None) -> List[Dict]:
        """
        Возвращает все собранные данные для обучения.
        Читает из JSON-файлов.
        """
        all_data = []

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

    def get_completed_tasks(self) -> List[Dict]:
        """Возвращает только завершённые задачи с временем."""
        all_data = self.get_training_data()
        return [
            d for d in all_data
            if d.get('completed', False) and d.get('effective_hours', 0) > 0
        ]

    def get_training_stats(self) -> Dict:
        """Возвращает статистику обучения."""
        all_data = self.get_training_data()
        completed = self.get_completed_tasks()

        return {
            'total_records': len(all_data),
            'completed_tasks': len(completed),
            'min_samples': self._min_samples_for_training,
            'last_training': self._last_training_time.isoformat() if self._last_training_time else None,
            'total_trainings': self._stats['total_trained'],
            'last_result': self._stats['last_result'],
            'last_error': self._stats['last_error'],
            'cache_size': len(self._cache),
            'can_train': len(completed) >= self._min_samples_for_training
        }

    def flush_cache(self):
        """Сохраняет кэш в файл и очищает его."""
        if not self._cache:
            return

        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.data_dir / f"tasks_data_{date_str}.json"

        try:
            # Читаем существующие данные
            existing_data = []
            if filename.exists():
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except:
                    pass

            # Объединяем с новыми данными
            all_data = existing_data + self._cache

            # Сохраняем
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2, default=str)

            print(f"📊 Сохранено {len(self._cache)} записей о задачах в {filename}")
            self._cache = []

        except Exception as e:
            print(f"❌ Ошибка сохранения кэша: {e}")

    def _save_training_stats(self):
        """Сохраняет статистику обучения."""
        stats_file = self.data_dir / "training_stats.json"
        try:
            stats = self.get_training_stats()
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Ошибка сохранения статистики: {e}")

    # ==========================================================
    # ПОЛУЧЕНИЕ ДАННЫХ ИЗ БД ПО ЗАПРОСУ
    # ==========================================================

    def get_tasks_for_training(self, limit: int = None) -> List[Dict]:
        """
        Получает задачи из БД для обучения.
        Используется когда нужно собрать данные из БД напрямую.
        """
        session = get_tasks_session()
        try:
            stmt = select(Task).where(
                Task.completed == True,
                Task.actual_hours > 0
            ).order_by(Task.completed_at.desc())

            if limit:
                stmt = stmt.limit(limit)

            tasks = session.scalars(stmt).all()
            result = []

            for task in tasks:
                task_info = self._collect_task_data(task, session)
                result.append(task_info)

            return result

        except Exception as e:
            print(f"❌ Ошибка получения задач для обучения: {e}")
            return []
        finally:
            session.close()

    def get_recent_completed_tasks(self, hours: int = 24) -> List[Dict]:
        """
        Получает задачи, завершённые за последние N часов.
        Используется для инкрементального обучения.
        """
        session = get_tasks_session()
        try:
            cutoff = datetime.now() - timedelta(hours=hours)

            stmt = select(Task).where(
                Task.completed == True,
                Task.actual_hours > 0,
                Task.completed_at > cutoff
            ).order_by(Task.completed_at.desc())

            tasks = session.scalars(stmt).all()
            result = []

            for task in tasks:
                task_info = self._collect_task_data(task, session)
                result.append(task_info)

            return result

        except Exception as e:
            print(f"❌ Ошибка получения новых задач: {e}")
            return []
        finally:
            session.close()


# ==========================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ==========================================================

_task_data_collector: Optional[TaskDataCollector] = None


def get_task_data_collector() -> TaskDataCollector:
    """Возвращает глобальный экземпляр сборщика данных."""
    global _task_data_collector
    if _task_data_collector is None:
        _task_data_collector = TaskDataCollector()
    return _task_data_collector