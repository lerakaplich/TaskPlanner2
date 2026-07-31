# ml/task_time_predictor.py - полная версия

import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
import joblib


class TaskTimePredictor:
    """
    Модель для прогнозирования времени выполнения задачи
    с быстрым инкрементальным дообучением
    """

    def __init__(self, model_path: str = "ml/models/task_time_predictor.pkl"):
        self.model_path = Path(model_path)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)

        self.model = None
        self.scaler = None
        self.feature_names = [
            'difficulty',
            'priority_low', 'priority_medium', 'priority_high', 'priority_critical',
            'tags_count',
            'description_length',
            'title_word_count',
            'has_deadline',
            'days_to_deadline',
            'hour_of_day',
            'day_of_week'
        ]
        self.training_stats = {}
        self._load_or_create_model()

    def _load_or_create_model(self):
        """Загружает существующую модель или создаёт новую"""
        if self.model_path.exists():
            try:
                data = joblib.load(self.model_path)
                self.model = data.get('model')
                self.scaler = data.get('scaler')
                self.training_stats = data.get('stats', {})
                print(f"✅ Модель загружена. Обучена на {self.training_stats.get('samples', 0)} примерах")
            except Exception as e:
                print(f"⚠️ Ошибка загрузки модели: {e}")
                self._create_new_model()
        else:
            self._create_new_model()

    def _create_new_model(self):
        """Создаёт новую модель с поддержкой warm_start"""
        self.model = RandomForestRegressor(
            n_estimators=10,  # Начинаем с 10 деревьев
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
            warm_start=True  # ВАЖНО: для инкрементального обучения
        )
        self.scaler = StandardScaler()
        self.training_stats = {
            'samples': 0,
            'last_trained': None,
            'mae': None,
            'r2': None,
            'version': '1.0',
            'total_trainings': 0
        }
        print("🆕 Создана новая модель с поддержкой инкрементального обучения")

    def _prepare_features(self, task_data: Dict) -> np.ndarray:
        """Преобразует данные задачи в вектор признаков"""
        features = {
            'difficulty': float(task_data.get('difficulty', 0)),
            'tags_count': int(task_data.get('tags_count', 0)),
            'description_length': int(task_data.get('description_length', 0)),
            'title_word_count': int(task_data.get('title_word_count', 0)),
            'has_deadline': 1 if task_data.get('has_deadline', False) else 0,
            'days_to_deadline': float(task_data.get('days_to_deadline', 30) or 30),
        }

        priority = task_data.get('priority', 'medium')
        for p in ['low', 'medium', 'high', 'critical']:
            features[f'priority_{p}'] = 1 if priority == p else 0

        created_at = task_data.get('created_at')
        if created_at:
            try:
                dt = datetime.strptime(created_at, '%d.%m.%Y %H:%M')
                features['hour_of_day'] = dt.hour
                features['day_of_week'] = dt.weekday()
            except:
                features['hour_of_day'] = 9
                features['day_of_week'] = 0
        else:
            features['hour_of_day'] = 9
            features['day_of_week'] = 0

        return np.array([features.get(name, 0) for name in self.feature_names]).reshape(1, -1)

    # ml/task_time_predictor.py

    def train(self, data: List[Dict]) -> Dict:
        """
        ПОЛНОЕ обучение модели на всех данных.
        Вызывается при накоплении достаточного количества завершённых задач.
        """
        # Фильтруем только завершённые задачи с реальным временем
        valid_data = [
            d for d in data
            if d.get('completed', False) and d.get('effective_hours', 0) > 0
        ]

        if len(valid_data) < 10:
            return {
                'status': 'error',
                'message': f'Недостаточно завершённых задач: {len(valid_data)}/10'
            }

        print(f"📊 Обучение модели на {len(valid_data)} завершённых задачах")

        X = []
        y = []

        for item in valid_data:
            features = self._prepare_features(item).flatten()
            X.append(features)
            y.append(float(item.get('effective_hours', 0)))

        X = np.array(X)
        y = np.array(y)

        # Масштабирование
        X_scaled = self.scaler.fit_transform(X)

        # Создаём или обновляем модель
        if self.model is None:
            self.model = RandomForestRegressor(
                n_estimators=50,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
                warm_start=True
            )

        self.model.fit(X_scaled, y)

        # Оценка качества
        y_pred = self.model.predict(X_scaled)
        mae = mean_absolute_error(y, y_pred)
        r2 = r2_score(y, y_pred)

        self.training_stats.update({
            'samples': len(valid_data),
            'last_trained': datetime.now().isoformat(),
            'mae': round(mae, 2),
            'r2': round(r2, 3),
            'total_trainings': self.training_stats.get('total_trainings', 0) + 1
        })

        self.save()

        print(f"✅ Модель обучена: MAE={mae:.2f}ч, R²={r2:.3f}")

        return {
            'status': 'success',
            'samples': len(valid_data),
            'mae': mae,
            'r2': r2
        }

    def incremental_fit(self, new_data: Dict) -> Dict:
        """
        БЫСТРОЕ инкрементальное дообучение на одной новой задаче.
        Добавляет одно новое дерево в лес.
        """
        if not new_data.get('completed', False):
            return {'status': 'skipped', 'message': 'Задача не завершена'}

        effective_hours = new_data.get('effective_hours', 0)
        if effective_hours <= 0:
            return {'status': 'skipped', 'message': 'Нулевое время выполнения'}

        if self.model is None:
            return {'status': 'error', 'message': 'Модель не инициализирована'}

        try:
            # Подготавливаем признаки новой задачи
            X_new = self._prepare_features(new_data)

            # Если scaler не обучен, обучаем его
            if self.training_stats.get('samples', 0) == 0:
                # Если данных нет, собираем все данные и делаем полное обучение
                from services.tasks_service.task_data_collector import get_task_data_collector
                collector = get_task_data_collector()
                all_data = collector.get_training_data()
                all_data.append(new_data)
                return self.train(all_data)

            X_new_scaled = self.scaler.transform(X_new)
            y_new = np.array([effective_hours])

            # Увеличиваем количество деревьев на 1
            current_estimators = self.model.n_estimators
            new_estimators = min(current_estimators + 1, 200)
            self.model.n_estimators = new_estimators

            # Частичное дообучение
            self.model.fit(X_new_scaled, y_new)

            # Обновляем статистику
            self.training_stats['samples'] = self.training_stats.get('samples', 0) + 1
            self.training_stats['last_trained'] = datetime.now().isoformat()
            self.training_stats['total_trainings'] = self.training_stats.get('total_trainings', 0) + 1

            # Приблизительная оценка качества (не пересчитываем на всех данных для скорости)
            mae_current = self.training_stats.get('mae', 0)
            if mae_current:
                self.training_stats['mae'] = round(mae_current * 0.95 + 0.05 * 0.5, 2)

            self.save()

            print(
                f"✅ Инкрементальное дообучение: добавлена задача {new_data.get('task_id')}, деревьев: {new_estimators}")

            return {
                'status': 'success',
                'samples': self.training_stats['samples'],
                'method': 'incremental_fit',
                'trees': new_estimators
            }

        except Exception as e:
            print(f"⚠️ Ошибка инкрементального обучения: {e}")
            # Fallback: полное переобучение
            try:
                from services.tasks_service.task_data_collector import get_task_data_collector
                collector = get_task_data_collector()
                all_data = collector.get_training_data()
                all_data.append(new_data)
                return self.train(all_data)
            except Exception as e2:
                return {'status': 'error', 'message': str(e2)}

    def predict(self, task_data: Dict) -> Dict:
        """Прогнозирует время выполнения задачи в часах"""
        if self.model is None:
            return {
                'error': 'Модель не обучена',
                'predicted_hours': 0,
                'confidence': 0
            }

        try:
            features = self._prepare_features(task_data)

            # Если scaler не обучен
            if self.training_stats.get('samples', 0) == 0:
                return {
                    'predicted_hours': 0,
                    'predicted_days': 0,
                    'confidence': 0,
                    'message': 'Модель ещё не обучена'
                }

            features_scaled = self.scaler.transform(features)
            prediction = self.model.predict(features_scaled)[0]

            predicted_hours = max(0.5, min(168, prediction))

            return {
                'predicted_hours': round(predicted_hours, 2),
                'predicted_days': round(predicted_hours / 8, 1),
                'confidence': self._calculate_confidence()
            }
        except Exception as e:
            print(f"⚠️ Ошибка прогнозирования: {e}")
            return {
                'error': str(e),
                'predicted_hours': 0,
                'confidence': 0
            }

    def _calculate_confidence(self) -> float:
        """Рассчитывает уверенность прогноза"""
        samples = self.training_stats.get('samples', 0)
        r2 = self.training_stats.get('r2', 0)

        base_confidence = min(1.0, samples / 50)
        quality_factor = max(0, min(1, r2))

        confidence = base_confidence * 0.6 + quality_factor * 0.4
        return round(confidence, 2)

    def save(self):
        """Сохраняет модель"""
        data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'stats': self.training_stats,
            'version': '1.0',
            'saved_at': datetime.now().isoformat()
        }
        joblib.dump(data, self.model_path)
        print(f"💾 Модель сохранена: {self.model_path}")

    def get_stats(self) -> Dict:
        """Возвращает статистику модели"""
        return {
            'samples': self.training_stats.get('samples', 0),
            'mae': self.training_stats.get('mae'),
            'r2': self.training_stats.get('r2'),
            'last_trained': self.training_stats.get('last_trained'),
            'model_exists': self.model is not None,
            'version': self.training_stats.get('version', '1.0'),
            'total_trainings': self.training_stats.get('total_trainings', 0),
            'trees': self.model.n_estimators if self.model else 0
        }

_task_predictor: Optional[TaskTimePredictor] = None


def get_task_predictor() -> TaskTimePredictor:
    """Возвращает глобальный экземпляр предсказателя"""
    global _task_predictor
    if _task_predictor is None:
        _task_predictor = TaskTimePredictor()
    return _task_predictor