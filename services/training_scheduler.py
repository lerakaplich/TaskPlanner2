# services/training_scheduler.py
import threading
import time
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TrainingScheduler:
    """
    Планировщик периодического дообучения модели прогнозирования времени.
    Запускается в фоновом потоке.
    """

    def __init__(self, check_interval_seconds: int = 3600, min_samples: int = 10):
        """
        Args:
            check_interval_seconds: Интервал проверки новых данных (сек)
            min_samples: Минимальное количество новых задач для дообучения
        """
        self.check_interval = check_interval_seconds
        self.min_samples = min_samples
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_training: Optional[str] = None
        self._pending_tasks = []
        self._lock = threading.Lock()
        self._stats = {
            'total_trainings': 0,
            'last_result': None,
            'last_error': None
        }

    def start(self):
        """Запускает фоновый поток для периодического дообучения"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"🧠 Планировщик обучения запущен (интервал: {self.check_interval}с)")

    def stop(self):
        """Останавливает планировщик"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("🧠 Планировщик обучения остановлен")

    def _run(self):
        """Основной цикл планировщика"""
        while self._running:
            try:
                self._check_and_train()
            except Exception as e:
                logger.error(f"⚠️ Ошибка в планировщике обучения: {e}")
                self._stats['last_error'] = str(e)

            # Ждём до следующей проверки (с возможностью прерывания)
            for _ in range(int(self.check_interval)):
                if not self._running:
                    break
                time.sleep(1)

    def _check_and_train(self) -> Dict:
        """Проверяет накопленные данные и запускает обучение при необходимости"""
        from services.tasks_service.task_data_collector import get_task_data_collector

        collector = get_task_data_collector()
        all_data = collector.get_training_data()

        # Фильтруем завершённые задачи с временем
        completed_tasks = [
            d for d in all_data
            if d.get("completed", False) and d.get("effective_hours", 0) > 0
        ]

        # Проверяем, сколько новых задач с момента последнего обучения
        new_tasks = 0
        if self._last_training:
            new_tasks = len([
                d for d in completed_tasks
                if d.get("completed_at") and d.get("completed_at") > self._last_training
            ])
        else:
            new_tasks = len(completed_tasks)

        if new_tasks >= self.min_samples:
            logger.info(f"🧠 Дообучение: {new_tasks} новых задач")
            result = collector.train_model_on_all_data()
            self._last_training = datetime.now().isoformat()
            self._stats['total_trainings'] += 1
            self._stats['last_result'] = result

            with self._lock:
                self._pending_tasks.clear()

            return result

        return {'status': 'skipped', 'new_tasks': new_tasks}

    def force_retrain(self) -> Dict:
        """Принудительное переобучение модели на всех данных"""
        from services.tasks_service.task_data_collector import get_task_data_collector

        collector = get_task_data_collector()
        result = collector.train_model_on_all_data()
        self._last_training = datetime.now().isoformat()
        self._stats['total_trainings'] += 1
        self._stats['last_result'] = result
        return result

    def add_pending_task(self, task_data: Dict):
        """Добавляет задачу в очередь для обучения (вызывается при завершении задачи)"""
        with self._lock:
            self._pending_tasks.append(task_data)

    def get_stats(self) -> Dict:
        """Возвращает статистику работы планировщика"""
        return {
            'is_running': self._running,
            'last_training': self._last_training,
            'total_trainings': self._stats['total_trainings'],
            'last_result': self._stats['last_result'],
            'last_error': self._stats['last_error'],
            'pending_tasks': len(self._pending_tasks),
            'check_interval': self.check_interval,
            'min_samples': self.min_samples
        }


# Глобальный экземпляр
_training_scheduler: Optional[TrainingScheduler] = None


def get_training_scheduler() -> TrainingScheduler:
    """Возвращает глобальный экземпляр планировщика обучения"""
    global _training_scheduler
    if _training_scheduler is None:
        _training_scheduler = TrainingScheduler()
    return _training_scheduler