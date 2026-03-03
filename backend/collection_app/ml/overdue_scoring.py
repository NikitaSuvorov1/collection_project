"""
Фасад (facade) для модуля прогнозирования просрочки.

Предоставляет простой интерфейс `score_client(client_data) -> float`,
внутренне делегируя вызов обученной модели OverdueRiskModel
(см. overdue_predictor.py).

Если модель не обучена — используется rule-based эвристика
(обратная совместимость).
"""

from typing import Dict, Any
from .overdue_predictor import get_model


def score_client(client_data: Dict[str, Any]) -> float:
    """
    Возвращает оценку вероятности просрочки для клиента (0..1).

    Параметры client_data могут содержать как сырые поля клиента
    (phone, email, income, …), так и расчётные признаки модели
    (overdue_share_12m, max_overdue_days, lti_ratio, …).

    Если переданы расчётные признаки — используется ML-модель.
    Если только базовые — применяется простой rule-based скоринг.
    """
    model = get_model()
    result = model.predict(client_data)
    return result['risk_score']


def score_client_full(client_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Полный результат скоринга: категория, вероятности, risk_score.
    """
    model = get_model()
    return model.predict(client_data)
