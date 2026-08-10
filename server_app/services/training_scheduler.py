# server_app/services/training_scheduler.py

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging
from pathlib import Path

from server_app.database import get_tasks_session
from server_app.services.tasks_service.task_data_collector import get_task_data_collector

logger = logging.getLogger(__name__)


class TrainingScheduler:
    """Планировщик обучения на СЕРВЕРЕ"""

    def __init__(self, check_interval_seconds: int = 300):  # 5 минут
        self.check_interval = check_interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_training: Optional[str] = None
        self._min_samples = 10

        # Путь к модели на сервере
        self.model_path = Path("ml/models/task_time_predictor.pkl")
        self.model_path.parent.mkdir(parents=True, exist_ok=True)

        self._stats = {
            'total_trainings': 0,
            'last_result': None,
            'last_error': None
        }

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("🧠 Планировщик обучения на сервере запущен")

    def stop(self):
        """Останавливает планировщик"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("🧠 Планировщик обучения остановлен")

    def _run(self):
        while self._running:
            try:
                self._check_and_train()
            except Exception as e:
                logger.error(f"⚠️ Ошибка обучения: {e}")
                self._stats['last_error'] = str(e)

            for _ in range(int(self.check_interval)):
                if not self._running:
                    break
                time.sleep(1)

    def _check_and_train(self):
        """Проверка новых завершённых задач"""
        from models.tasks import Task
        from sqlalchemy import select

        session = get_tasks_session()
        try:
            # Считаем завершённые задачи за последний час
            one_hour_ago = datetime.now() - timedelta(hours=1)

            # Получаем все завершённые задачи
            stmt = select(Task).where(
                Task.completed == True,
                Task.completed_at > one_hour_ago,
                Task.actual_hours > 0
            )
            new_tasks = session.scalars(stmt).all()

            if len(new_tasks) >= self._min_samples:
                logger.info(f"🧠 Найдено {len(new_tasks)} новых завершённых задач")

                collector = get_task_data_collector()

                # Добавляем новые задачи в кэш
                for task in new_tasks:
                    collector.collect_and_save_task(task.id)

                # Обучаем модель
                result = collector.force_train()
                self._stats['total_trainings'] += 1
                self._stats['last_result'] = result
                logger.info(f"✅ Результат обучения: {result}")

        except Exception as e:
            logger.error(f"❌ Ошибка проверки задач: {e}")
        finally:
            session.close()

    def force_retrain(self) -> Dict:
        """Принудительное переобучение модели на всех данных"""
        try:
            collector = get_task_data_collector()
            result = collector.force_train()
            self._stats['total_trainings'] += 1
            self._stats['last_result'] = result
            self._last_training = datetime.now().isoformat()
            return result
        except Exception as e:
            error_msg = str(e)
            self._stats['last_error'] = error_msg
            return {'status': 'error', 'message': error_msg}

    def get_stats(self) -> Dict:
        """Возвращает статистику работы планировщика"""
        return {
            'is_running': self._running,
            'last_training': self._last_training,
            'total_trainings': self._stats['total_trainings'],
            'last_result': self._stats['last_result'],
            'last_error': self._stats['last_error'],
            'check_interval': self.check_interval,
            'min_samples': self._min_samples
        }


# ==========================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# ==========================================================

_training_scheduler: Optional[TrainingScheduler] = None


def get_training_scheduler() -> TrainingScheduler:
    """Возвращает глобальный экземпляр планировщика обучения"""
    global _training_scheduler
    if _training_scheduler is None:
        _training_scheduler = TrainingScheduler()
    return _training_scheduler