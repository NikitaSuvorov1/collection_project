"""
Модель прогнозирования одобрения кредитной заявки.

Обёртка над CreditApprovalModel (application_approval.py).
Обеспечивает обратную совместимость с import-ами из views.py:
    from .ml.loan_predictor import predict_loan_approval, get_predictor

Алгоритм: GradientBoostingClassifier (200 деревьев).
Признаки: 32 (демографические, финансовые, кредитная история).
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .application_approval import CreditApprovalModel, get_model

logger = logging.getLogger(__name__)


class LoanApprovalPredictor:
    """
    Обёртка над CreditApprovalModel для обратной совместимости.
    """

    def __init__(self):
        self._model = get_model()

    def predict(self, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Предсказание вероятности одобрения заявки.

        Принимает как полные данные CreditApplication, так и
        упрощённый формат (gender, income, loan_amount, …).

        Returns:
            {
                approved_probability: float,
                decision: 'approved' | 'rejected',
                confidence: float,
                risk_factors: [...],
                model_type: str,
            }
        """
        # Конвертируем упрощённые поля в формат CreditApprovalModel
        mapped = self._map_simple_fields(application_data)
        return self._model.predict(mapped)

    @staticmethod
    def _map_simple_fields(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Маппинг упрощённых полей (gender, income, …) в поля,
        ожидаемые _extract_features_from_application.
        """
        d = dict(data)  # копия

        # Если income передан как простое число — это income_main
        if 'income' in d and 'income_main' not in d:
            d['income_main'] = float(d['income'])
            d.setdefault('income_additional', 0)
            d.setdefault('income_rental', 0)
            d.setdefault('income_pension', 0)
            d.setdefault('income_other', 0)

        # monthly_expenses → разбиваем на компоненты
        if 'monthly_expenses' in d and 'expense_food' not in d:
            exp = float(d['monthly_expenses'])
            d['expense_rent'] = exp * 0.3
            d['expense_utilities'] = exp * 0.15
            d['expense_food'] = exp * 0.3
            d['expense_transport'] = exp * 0.1
            d['expense_other'] = exp * 0.15

        if 'loan_amount' in d and 'amount' not in d:
            d['amount'] = d['loan_amount']

        if 'loan_term' in d and 'requested_term' not in d:
            d['requested_term'] = d['loan_term']

        if 'children_count' in d and 'dependents_count' not in d:
            d['dependents_count'] = d['children_count']

        if 'credit_history' in d and 'has_overdue_history' not in d:
            d['has_overdue_history'] = int(d['credit_history'] == 0)

        if 'employment' in d and 'employment_type' not in d:
            d['employment_type'] = d['employment']

        return d

    def load(self) -> bool:
        self._model = get_model()
        return self._model.is_fitted


# Singleton
_predictor: Optional[LoanApprovalPredictor] = None


def get_predictor() -> LoanApprovalPredictor:
    """Получение singleton экземпляра предиктора."""
    global _predictor
    if _predictor is None:
        _predictor = LoanApprovalPredictor()
    return _predictor


def predict_loan_approval(application_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Основная функция для предсказания одобрения кредита.

    Пример:
        result = predict_loan_approval({
            'gender': 'M',
            'marital_status': 'married',
            'employment': 'employed',
            'income': 100000,
            'monthly_expenses': 30000,
            'loan_amount': 500000,
            'loan_term': 36,
            'children_count': 2,
            'credit_history': 1,
            'region': 'Москва'
        })
    """
    predictor = get_predictor()
    return predictor.predict(application_data)
