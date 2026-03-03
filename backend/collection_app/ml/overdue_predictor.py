"""
Модуль прогнозирования выхода клиента на просрочку с ранжированием по рискам.

Реализует мультиклассовую классификацию (3 класса):
  0 — Низкий риск
  1 — Средний риск
  2 — Высокий риск

Алгоритмы:
  • RandomForestClassifier  — основная модель (ensemble, устойчивость к шуму)
  • StandardScaler          — нормализация признаков
  • Cross-validation (5-fold) — оценка устойчивости

Признаки (28 штук, раздел 3.2 курсовой):
  Клиент: age, gender, marital, employment, dependents, income,
          has_other_credits, other_credits_count
  Кредит: amount, term, interest_rate, lti_ratio, credit_age,
          credit_status, monthly_payment
  Платёжная дисциплина: total_payments, overdue_payments, max_overdue_days,
          avg_payment, payments_12m, overdue_12m, overdue_share_12m, max_overdue_12m
  Взаимодействие: total_interventions, completed_interventions, promises_count

Целевая: risk_category ∈ {0, 1, 2}
"""

import logging
import pickle
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import numpy as np

# Ленивый импорт: pandas/sklearn загружаются только при вызове train()
pd = None
def _ensure_ml_imports():
    global pd
    if pd is not None:
        return
    import pandas as _pd
    pd = _pd

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / 'saved_models'
MODEL_PATH = MODEL_DIR / 'overdue_model.pkl'
SCALER_PATH = MODEL_DIR / 'overdue_scaler.pkl'
FEATURES_PATH = MODEL_DIR / 'overdue_features.pkl'

# Фиксированный порядок признаков
FEATURE_COLUMNS = [
    'age', 'gender', 'marital_status', 'employment', 'dependents',
    'monthly_income', 'has_other_credits', 'other_credits_count',
    'credit_amount', 'credit_term', 'interest_rate', 'lti_ratio',
    'credit_age', 'credit_status', 'monthly_payment',
    'total_payments', 'overdue_payments', 'max_overdue_days',
    'avg_payment', 'payments_count_12m', 'overdue_count_12m',
    'overdue_share_12m', 'max_overdue_12m',
    'total_interventions', 'completed_interventions', 'promises_count',
]

RISK_LABELS = {0: 'Низкий', 1: 'Средний', 2: 'Высокий'}


def _row_to_vector(row: Dict[str, Any]) -> List[float]:
    """Преобразование словаря признаков в числовой вектор."""
    return [float(row.get(c, 0)) for c in FEATURE_COLUMNS]


class OverdueRiskModel:
    """
    Модель мультиклассовой классификации риска просрочки.

    Алгоритм: RandomForestClassifier (sklearn).
    Классы: 0 — низкий, 1 — средний, 2 — высокий.
    """

    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names: List[str] = FEATURE_COLUMNS[:]
        self.is_fitted = False

    # ------------------------------------------------------------------ train
    def train(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Обучение модели.

        Args:
            records: список словарей, каждый содержит FEATURE_COLUMNS + 'risk_category'

        Returns:
            Словарь с метриками качества.
        """
        _ensure_ml_imports()
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split, cross_val_score
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
        df = pd.DataFrame(records)
        X = df[self.feature_names].values.astype(float)
        y = df['risk_category'].values.astype(int)

        if len(np.unique(y)) < 2:
            raise ValueError('Нужны как минимум 2 разных класса для обучения')

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42,
            stratify=y if len(np.unique(y)) >= 2 else None,
        )

        self.scaler = StandardScaler()
        X_train_s = self.scaler.fit_transform(X_train)
        X_test_s = self.scaler.transform(X_test)

        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            min_samples_split=8,
            min_samples_leaf=4,
            class_weight='balanced',     # компенсация дисбаланса классов
            random_state=42,
            n_jobs=-1,
        )
        self.model.fit(X_train_s, y_train)
        self.is_fitted = True

        y_pred = self.model.predict(X_test_s)
        acc = accuracy_score(y_test, y_pred)

        target_names = [RISK_LABELS[i] for i in sorted(np.unique(y))]
        cv_scores = cross_val_score(
            self.model, self.scaler.transform(X), y, cv=5, scoring='accuracy'
        )

        metrics = {
            'accuracy': float(acc),
            'cv_mean': float(cv_scores.mean()),
            'cv_std': float(cv_scores.std()),
            'train_size': len(X_train),
            'test_size': len(X_test),
            'class_distribution': {
                RISK_LABELS[int(k)]: int(v)
                for k, v in zip(*np.unique(y, return_counts=True))
            },
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
            'classification_report': classification_report(
                y_test, y_pred,
                target_names=target_names,
                output_dict=True,
                zero_division=0,
            ),
            'feature_importances': dict(zip(
                self.feature_names,
                [float(v) for v in self.model.feature_importances_],
            )),
        }

        self._save()
        logger.info('OverdueRiskModel trained — acc=%.3f  cv=%.3f', acc, cv_scores.mean())
        return metrics

    # --------------------------------------------------------------- predict
    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Прогноз для одного клента/кредита.

        Returns:
            {
                risk_category: int (0/1/2),
                risk_label: str,
                probabilities: {
                    'Низкий': float,
                    'Средний': float,
                    'Высокий': float,
                },
                risk_score: float (0..1, взвешенная оценка),
            }
        """
        if not self.is_fitted:
            if not self._load():
                return self._rule_based(features)

        vec = np.array([_row_to_vector(features)], dtype=float)
        vec_s = self.scaler.transform(vec)

        pred = int(self.model.predict(vec_s)[0])
        proba = self.model.predict_proba(vec_s)[0]

        prob_dict = {}
        for cls_idx, prob_val in enumerate(proba):
            label = RISK_LABELS.get(self.model.classes_[cls_idx], f'Class {cls_idx}')
            prob_dict[label] = float(prob_val)

        # Взвешенный risk_score: 0·P(low) + 0.5·P(med) + 1·P(high)
        risk_score = 0.0
        for cls_idx, prob_val in enumerate(proba):
            cls_val = self.model.classes_[cls_idx]
            risk_score += cls_val * prob_val
        risk_score = risk_score / 2.0  # нормируем в 0..1

        return {
            'risk_category': pred,
            'risk_label': RISK_LABELS.get(pred, str(pred)),
            'probabilities': prob_dict,
            'risk_score': float(risk_score),
        }

    # -------------------------------------------------- predict batch (ранжирование)
    def predict_batch(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Прогноз для списка записей с автоматическим ранжированием по risk_score.
        Возвращает список, отсортированный от самого рискового к наименее рискованному.
        """
        results = []
        for rec in records:
            pred = self.predict(rec)
            pred['client_id'] = rec.get('client_id')
            pred['credit_id'] = rec.get('credit_id')
            results.append(pred)

        results.sort(key=lambda x: x['risk_score'], reverse=True)

        for rank, item in enumerate(results, 1):
            item['rank'] = rank

        return results

    # -------------------------------------------------- rule-based fallback
    @staticmethod
    def _rule_based(features: Dict[str, Any]) -> Dict[str, Any]:
        """Эвристический прогноз при отсутствии обученной модели."""
        overdue_share = float(features.get('overdue_share_12m', 0))
        max_od = float(features.get('max_overdue_days', 0))
        lti = float(features.get('lti_ratio', 0))

        score = 0.0
        if overdue_share > 0.5:
            score += 0.4
        elif overdue_share > 0.2:
            score += 0.2
        if max_od > 60:
            score += 0.3
        elif max_od > 30:
            score += 0.15
        if lti > 5:
            score += 0.15
        score = min(score, 1.0)

        if score >= 0.6:
            cat, label = 2, 'Высокий'
        elif score >= 0.3:
            cat, label = 1, 'Средний'
        else:
            cat, label = 0, 'Низкий'

        return {
            'risk_category': cat,
            'risk_label': label,
            'probabilities': {'Низкий': 1 - score, 'Средний': 0.0, 'Высокий': score},
            'risk_score': score,
        }

    # ------------------------------------------------------------- save/load
    def _save(self):
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        with open(MODEL_PATH, 'wb') as f:
            pickle.dump(self.model, f)
        with open(SCALER_PATH, 'wb') as f:
            pickle.dump(self.scaler, f)
        with open(FEATURES_PATH, 'wb') as f:
            pickle.dump(self.feature_names, f)
        logger.info('OverdueRiskModel saved to %s', MODEL_DIR)

    def _load(self) -> bool:
        try:
            if not MODEL_PATH.exists():
                return False
            with open(MODEL_PATH, 'rb') as f:
                self.model = pickle.load(f)
            with open(SCALER_PATH, 'rb') as f:
                self.scaler = pickle.load(f)
            if FEATURES_PATH.exists():
                with open(FEATURES_PATH, 'rb') as f:
                    self.feature_names = pickle.load(f)
            self.is_fitted = True
            logger.info('OverdueRiskModel loaded')
            return True
        except Exception as e:
            logger.error('OverdueRiskModel load error: %s', e)
            return False


# =====================================================================
# Публичный API
# =====================================================================

_model: Optional[OverdueRiskModel] = None


def get_model() -> OverdueRiskModel:
    global _model
    if _model is None:
        _model = OverdueRiskModel()
        _model._load()
    return _model


def train_model(data: list) -> str:
    """
    Обратная совместимость с предыдущим API.

    Args:
        data: список словарей (FEATURE_COLUMNS + risk_category)
    Returns:
        путь к сохранённой модели
    """
    global _model
    m = OverdueRiskModel()
    metrics = m.train(data)
    _model = m
    return str(MODEL_PATH)


def predict_risk(features_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Прогноз для одного клиента/кредита."""
    return get_model().predict(features_dict)


def predict_risk_batch(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Прогноз + ранжирование для списка."""
    return get_model().predict_batch(records)
