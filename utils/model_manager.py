# utils/model_manager.py
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from services.tasks_service.task_data_collector import get_task_data_collector
from ml.task_time_predictor import get_task_predictor


class ModelManager:
    """Утилита для управления моделью машинного обучения"""

    @staticmethod
    def train():
        """Принудительное обучение модели"""
        collector = get_task_data_collector()
        return collector.train_model_on_all_data()

    @staticmethod
    def retrain():
        """Переобучение модели"""
        return ModelManager.train()

    @staticmethod
    def get_stats() -> Dict:
        """Получить статистику модели"""
        predictor = get_task_predictor()
        return predictor.get_stats()

    @staticmethod
    def export_data(output_path: str = "data/export/training_data.json") -> int:
        """Экспортировать все данные для обучения"""
        collector = get_task_data_collector()
        data = collector.get_training_data()

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return len(data)

    @staticmethod
    def import_data(file_path: str) -> int:
        """Импортировать данные для обучения"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Сохраняем в коллектор
        collector = get_task_data_collector()
        for item in data:
            collector._cache.append(item)

        collector.flush_cache()
        return len(data)

    @staticmethod
    def predict_on_task(task_data: Dict) -> Dict:
        """Прогнозировать время для задачи"""
        predictor = get_task_predictor()
        return predictor.predict(task_data)

    @staticmethod
    def evaluate() -> Dict:
        """Оценить качество модели"""
        predictor = get_task_predictor()
        collector = get_task_data_collector()
        data = collector.get_training_data()

        valid_data = [
            d for d in data
            if d.get('completed', False) and d.get('effective_hours', 0) > 0
        ]

        if len(valid_data) < 10:
            return {'error': 'Недостаточно данных'}

        predictions = []
        actuals = []

        for item in valid_data:
            pred = predictor.predict(item)
            actual = item.get('effective_hours', 0)
            predictions.append(pred.get('predicted_hours', 0))
            actuals.append(actual)

        from sklearn.metrics import mean_absolute_error, r2_score
        mae = mean_absolute_error(actuals, predictions)
        r2 = r2_score(actuals, predictions)

        return {
            'samples': len(valid_data),
            'mae': round(mae, 2),
            'r2': round(r2, 3),
            'predictions': predictions[:10],
            'actuals': actuals[:10]
        }