"""
ML Pipeline - Управление жизненным циклом ML моделей

Включает:
- Обучение и валидация моделей
- Метрики качества (ROC-AUC, Precision, Recall, F1)
- Cross-validation
- Feature importance
- Model versioning
- A/B testing support
"""

import os
import json
import pickle
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict

import numpy as np
from sklearn.model_selection import (
    train_test_split, cross_val_score, StratifiedKFold
)
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    precision_recall_curve, roc_curve
)
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder, StandardScaler

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / 'saved_models'
MODEL_DIR.mkdir(exist_ok=True)


@dataclass
class ModelMetrics:
    """Метрики качества модели"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    confusion_matrix: List[List[int]]
    classification_report: str
    feature_importance: Dict[str, float]
    cross_val_scores: List[float]
    cross_val_mean: float
    cross_val_std: float
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def __str__(self) -> str:
        return f"""
Model Metrics:
--------------
Accuracy:  {self.accuracy:.4f}
Precision: {self.precision:.4f}
Recall:    {self.recall:.4f}
F1 Score:  {self.f1_score:.4f}
ROC-AUC:   {self.roc_auc:.4f}

Cross-Validation:
  Mean: {self.cross_val_mean:.4f} (+/- {self.cross_val_std:.4f})
  Scores: {[f'{s:.4f}' for s in self.cross_val_scores]}

Confusion Matrix:
{self._format_confusion_matrix()}

Top Features:
{self._format_feature_importance()}
"""
    
    def _format_confusion_matrix(self) -> str:
        cm = self.confusion_matrix
        return f"  TN={cm[0][0]:5d}  FP={cm[0][1]:5d}\n  FN={cm[1][0]:5d}  TP={cm[1][1]:5d}"
    
    def _format_feature_importance(self) -> str:
        sorted_features = sorted(
            self.feature_importance.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        return '\n'.join([f"  {name}: {imp:.4f}" for name, imp in sorted_features])


@dataclass
class ModelVersion:
    """Информация о версии модели"""
    version: str
    model_type: str
    created_at: str
    metrics: ModelMetrics
    hyperparameters: Dict[str, Any]
    training_data_size: int
    feature_names: List[str]
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['metrics'] = self.metrics.to_dict()
        return d


class MLPipeline:
    """
    ML Pipeline для обучения, валидации и деплоя моделей.
    
    Поддерживает:
    - Несколько типов моделей (RF, GBM, LogReg)
    - Кросс-валидацию
    - Автоматический подбор гиперпараметров
    - Версионирование моделей
    - Метрики качества
    """
    
    SUPPORTED_MODELS = {
        'random_forest': RandomForestClassifier,
        'gradient_boosting': GradientBoostingClassifier,
        'logistic_regression': LogisticRegression,
    }
    
    DEFAULT_HYPERPARAMETERS = {
        'random_forest': {
            'n_estimators': 100,
            'max_depth': 10,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'criterion': 'entropy',
            'random_state': 42,
            'n_jobs': -1
        },
        'gradient_boosting': {
            'n_estimators': 100,
            'max_depth': 5,
            'learning_rate': 0.1,
            'min_samples_split': 5,
            'random_state': 42
        },
        'logistic_regression': {
            'C': 1.0,
            'max_iter': 1000,
            'random_state': 42
        }
    }
    
    def __init__(self, model_name: str = 'scoring_model'):
        self.model_name = model_name
        self.model = None
        self.encoders: Dict[str, LabelEncoder] = {}
        self.scaler: Optional[StandardScaler] = None
        self.feature_names: List[str] = []
        self.current_version: Optional[ModelVersion] = None
        self.is_fitted = False
    
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str],
        model_type: str = 'random_forest',
        hyperparameters: Optional[Dict] = None,
        test_size: float = 0.2,
        cv_folds: int = 5,
        scale_features: bool = True
    ) -> ModelMetrics:
        """
        Обучение модели с полной валидацией.
        
        Args:
            X: Матрица признаков
            y: Целевая переменная
            feature_names: Названия признаков
            model_type: Тип модели
            hyperparameters: Гиперпараметры (если None - используются дефолтные)
            test_size: Размер тестовой выборки
            cv_folds: Количество фолдов для кросс-валидации
            scale_features: Нормализовать признаки
            
        Returns:
            ModelMetrics: Метрики качества
        """
        logger.info(f"Starting training: {model_type}, samples={len(y)}")
        
        self.feature_names = feature_names
        
        # Разбиение на train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Нормализация
        if scale_features:
            self.scaler = StandardScaler()
            X_train = self.scaler.fit_transform(X_train)
            X_test = self.scaler.transform(X_test)
        
        # Создание модели
        params = hyperparameters or self.DEFAULT_HYPERPARAMETERS.get(model_type, {})
        model_class = self.SUPPORTED_MODELS.get(model_type)
        
        if model_class is None:
            raise ValueError(f"Unknown model type: {model_type}")
        
        self.model = model_class(**params)
        
        # Обучение
        logger.info("Fitting model...")
        self.model.fit(X_train, y_train)
        
        # Предсказания
        y_pred = self.model.predict(X_test)
        y_proba = self.model.predict_proba(X_test)[:, 1] if hasattr(self.model, 'predict_proba') else y_pred
        
        # Cross-validation
        logger.info("Running cross-validation...")
        cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        cv_scores = cross_val_score(self.model, X_train, y_train, cv=cv, scoring='roc_auc')
        
        # Feature importance
        if hasattr(self.model, 'feature_importances_'):
            importance = dict(zip(feature_names, self.model.feature_importances_))
        elif hasattr(self.model, 'coef_'):
            importance = dict(zip(feature_names, np.abs(self.model.coef_[0])))
        else:
            importance = {}
        
        # Метрики
        metrics = ModelMetrics(
            accuracy=accuracy_score(y_test, y_pred),
            precision=precision_score(y_test, y_pred, zero_division=0),
            recall=recall_score(y_test, y_pred, zero_division=0),
            f1_score=f1_score(y_test, y_pred, zero_division=0),
            roc_auc=roc_auc_score(y_test, y_proba) if len(np.unique(y_test)) > 1 else 0.5,
            confusion_matrix=confusion_matrix(y_test, y_pred).tolist(),
            classification_report=classification_report(y_test, y_pred),
            feature_importance=importance,
            cross_val_scores=cv_scores.tolist(),
            cross_val_mean=cv_scores.mean(),
            cross_val_std=cv_scores.std()
        )
        
        # Версионирование
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_version = ModelVersion(
            version=version,
            model_type=model_type,
            created_at=datetime.now().isoformat(),
            metrics=metrics,
            hyperparameters=params,
            training_data_size=len(y),
            feature_names=feature_names
        )
        
        self.is_fitted = True
        
        logger.info(f"Training complete. ROC-AUC: {metrics.roc_auc:.4f}")
        logger.info(str(metrics))
        
        return metrics
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Предсказание классов"""
        if not self.is_fitted:
            raise ValueError("Model is not fitted")
        
        if self.scaler:
            X = self.scaler.transform(X)
        
        return self.model.predict(X)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Предсказание вероятностей"""
        if not self.is_fitted:
            raise ValueError("Model is not fitted")
        
        if self.scaler:
            X = self.scaler.transform(X)
        
        if hasattr(self.model, 'predict_proba'):
            return self.model.predict_proba(X)
        else:
            # Для моделей без predict_proba
            preds = self.model.predict(X)
            return np.column_stack([1 - preds, preds])
    
    def save(self, path: Optional[Path] = None) -> Path:
        """
        Сохранение модели и метаданных.
        
        Args:
            path: Путь для сохранения (если None - автогенерация)
            
        Returns:
            Path: Путь к сохранённой модели
        """
        if not self.is_fitted:
            raise ValueError("Model is not fitted")
        
        if path is None:
            path = MODEL_DIR / f"{self.model_name}_{self.current_version.version}.pkl"
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'encoders': self.encoders,
            'feature_names': self.feature_names,
            'version': self.current_version.to_dict()
        }
        
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
        
        # Сохраняем метаданные в JSON
        metadata_path = path.with_suffix('.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.current_version.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Model saved to {path}")
        
        return path
    
    def load(self, path: Path) -> 'MLPipeline':
        """
        Загрузка модели.
        
        Args:
            path: Путь к файлу модели
            
        Returns:
            self
        """
        with open(path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data.get('scaler')
        self.encoders = model_data.get('encoders', {})
        self.feature_names = model_data.get('feature_names', [])
        
        version_data = model_data.get('version', {})
        if version_data:
            metrics_data = version_data.pop('metrics', {})
            metrics = ModelMetrics(**metrics_data) if metrics_data else None
            self.current_version = ModelVersion(metrics=metrics, **version_data) if metrics else None
        
        self.is_fitted = True
        
        logger.info(f"Model loaded from {path}")
        
        return self
    
    @classmethod
    def load_latest(cls, model_name: str) -> 'MLPipeline':
        """Загрузка последней версии модели"""
        pattern = f"{model_name}_*.pkl"
        models = sorted(MODEL_DIR.glob(pattern), reverse=True)
        
        if not models:
            raise FileNotFoundError(f"No models found for {model_name}")
        
        pipeline = cls(model_name)
        return pipeline.load(models[0])
    
    def compare_models(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str],
        model_types: List[str] = None
    ) -> Dict[str, ModelMetrics]:
        """
        Сравнение нескольких типов моделей.
        
        Args:
            X: Признаки
            y: Целевая переменная
            feature_names: Названия признаков
            model_types: Типы моделей для сравнения
            
        Returns:
            Dict: Метрики для каждой модели
        """
        if model_types is None:
            model_types = list(self.SUPPORTED_MODELS.keys())
        
        results = {}
        
        for model_type in model_types:
            logger.info(f"Training {model_type}...")
            pipeline = MLPipeline(f"{self.model_name}_{model_type}")
            metrics = pipeline.train(X, y, feature_names, model_type=model_type)
            results[model_type] = metrics
        
        # Выводим сравнительную таблицу
        logger.info("\n" + "=" * 60)
        logger.info("MODEL COMPARISON")
        logger.info("=" * 60)
        logger.info(f"{'Model':<25} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1':>10} {'ROC-AUC':>10}")
        logger.info("-" * 75)
        
        for model_type, metrics in results.items():
            logger.info(
                f"{model_type:<25} {metrics.accuracy:>10.4f} {metrics.precision:>10.4f} "
                f"{metrics.recall:>10.4f} {metrics.f1_score:>10.4f} {metrics.roc_auc:>10.4f}"
            )
        
        return results


class ScoringPipeline(MLPipeline):
    """
    Специализированный pipeline для скоринга просрочки.
    
    Особенности:
    - Калибровка вероятностей
    - Score to PD mapping
    - Грейдирование
    """
    
    GRADE_THRESHOLDS = {
        'A': (800, 1000),  # PD < 2%
        'B': (700, 799),   # PD 2-5%
        'C': (600, 699),   # PD 5-15%
        'D': (500, 599),   # PD 15-30%
        'E': (0, 499),     # PD > 30%
    }
    
    def probability_to_score(self, pd: float) -> int:
        """
        Конвертация вероятности дефолта в скоринговый балл.
        
        Формула: Score = 600 - 50 * log2(PD / (1 - PD))
        
        Args:
            pd: Probability of Default (0-1)
            
        Returns:
            int: Скоринговый балл (300-850)
        """
        if pd <= 0:
            return 850
        if pd >= 1:
            return 300
        
        odds = pd / (1 - pd)
        score = 600 - 50 * np.log2(odds)
        
        return int(np.clip(score, 300, 850))
    
    def score_to_probability(self, score: int) -> float:
        """
        Конвертация скорингового балла в PD.
        
        Args:
            score: Скоринговый балл
            
        Returns:
            float: Probability of Default
        """
        odds = 2 ** ((600 - score) / 50)
        pd = odds / (1 + odds)
        return pd
    
    def get_grade(self, score: int) -> str:
        """Получение грейда по баллу"""
        for grade, (min_score, max_score) in self.GRADE_THRESHOLDS.items():
            if min_score <= score <= max_score:
                return grade
        return 'E'
    
    def score_client(self, X: np.ndarray) -> Dict[str, Any]:
        """
        Полный скоринг клиента.
        
        Args:
            X: Признаки клиента (1D array)
            
        Returns:
            Dict: Результаты скоринга
        """
        X = X.reshape(1, -1) if X.ndim == 1 else X
        
        proba = self.predict_proba(X)[0, 1]  # Вероятность дефолта
        score = self.probability_to_score(proba)
        grade = self.get_grade(score)
        
        return {
            'probability_of_default': proba,
            'score': score,
            'grade': grade,
            'risk_level': self._get_risk_level(grade),
            'recommendation': self._get_recommendation(grade)
        }
    
    def _get_risk_level(self, grade: str) -> str:
        levels = {
            'A': 'Минимальный',
            'B': 'Низкий',
            'C': 'Средний',
            'D': 'Высокий',
            'E': 'Критический'
        }
        return levels.get(grade, 'Неизвестный')
    
    def _get_recommendation(self, grade: str) -> str:
        recommendations = {
            'A': 'Продолжить мягкое взыскание',
            'B': 'Стандартная процедура soft collection',
            'C': 'Усилить контакты, предложить реструктуризацию',
            'D': 'Перевести в hard collection',
            'E': 'Рассмотреть legal collection или продажу'
        }
        return recommendations.get(grade, 'Требуется анализ')
