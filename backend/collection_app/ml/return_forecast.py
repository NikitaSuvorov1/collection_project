"""
Сервис прогнозирования возврата долга.

Прогнозирует:
- Вероятность возврата (полного/частичного)
- Ожидаемый срок возврата
- Ожидаемую сумму
- Рекомендацию: продолжать взыскание / продавать / списывать
- NPV при разных стратегиях
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple


@dataclass
class ReturnForecastResult:
    """Результат прогноза возврата."""
    return_probability: float
    partial_return_probability: float
    expected_return_amount: Decimal
    expected_return_days: int
    recommendation: str
    recommendation_confidence: float
    positive_factors: List[str]
    negative_factors: List[str]
    npv_continue: Decimal
    npv_sell: Decimal
    npv_write_off: Decimal


# Базовые вероятности возврата по сегментам риска
BASE_RETURN_PROBABILITY = {
    'low': 0.85,
    'medium': 0.55,
    'high': 0.25,
    'critical': 0.08,
}

# Коэффициенты влияния факторов
FACTOR_WEIGHTS = {
    # Позитивные факторы
    'has_income': 0.15,
    'employed': 0.10,
    'answers_calls': 0.12,
    'keeps_promises': 0.18,
    'partial_payments': 0.10,
    'cooperative': 0.08,
    'small_debt': 0.05,
    
    # Негативные факторы
    'no_income': -0.20,
    'unemployed': -0.12,
    'ignores_contacts': -0.15,
    'breaks_promises': -0.20,
    'long_overdue': -0.15,
    'toxic': -0.10,
    'multiple_debts': -0.08,
    'job_changed': -0.05,
}

# Цены продажи портфеля (% от суммы долга)
PORTFOLIO_SALE_PRICES = {
    'low': 0.70,      # Хорошие долги продаются дорого
    'medium': 0.35,
    'high': 0.12,
    'critical': 0.03,
}


class ReturnForecastService:
    """Сервис прогнозирования возврата долга."""

    def __init__(self, discount_rate: float = 0.15):
        """
        Args:
            discount_rate: Ставка дисконтирования для NPV (годовая)
        """
        self.discount_rate = discount_rate

    def analyze_factors(
        self,
        client_data: Dict,
        behavior_profile: Dict,
        credit_data: Dict,
        contact_history: List[Dict]
    ) -> Tuple[List[str], List[str], float]:
        """
        Анализирует факторы влияющие на возврат.
        
        Returns:
            (positive_factors, negative_factors, adjustment)
        """
        positive = []
        negative = []
        adjustment = 0.0
        
        # Доход
        income = client_data.get('income', 0)
        if income > 50000:
            positive.append('Стабильный доход')
            adjustment += FACTOR_WEIGHTS['has_income']
        elif income > 0:
            positive.append('Есть доход')
            adjustment += FACTOR_WEIGHTS['has_income'] * 0.5
        else:
            negative.append('Нет подтверждённого дохода')
            adjustment += FACTOR_WEIGHTS['no_income']
        
        # Занятость
        employment = client_data.get('employment', 'unknown')
        if employment == 'employed':
            positive.append('Трудоустроен')
            adjustment += FACTOR_WEIGHTS['employed']
        elif employment == 'unemployed':
            negative.append('Безработный')
            adjustment += FACTOR_WEIGHTS['unemployed']
        
        # Психотип
        psychotype = behavior_profile.get('psychotype', 'unknown')
        if psychotype == 'cooperative':
            positive.append('Готов к диалогу')
            adjustment += FACTOR_WEIGHTS['cooperative']
        elif psychotype == 'toxic':
            negative.append('Конфликтный клиент')
            adjustment += FACTOR_WEIGHTS['toxic']
        elif psychotype == 'unable':
            negative.append('Финансовые трудности')
            adjustment -= 0.05
        
        # Контактность
        contact_rate = behavior_profile.get('contact_rate', 0.5)
        if contact_rate > 0.7:
            positive.append('Высокая контактность')
            adjustment += FACTOR_WEIGHTS['answers_calls']
        elif contact_rate < 0.3:
            negative.append('Игнорирует контакты')
            adjustment += FACTOR_WEIGHTS['ignores_contacts']
        
        # Выполнение обещаний
        promises_kept = behavior_profile.get('promises_kept_ratio', 0.5)
        if promises_kept > 0.7:
            positive.append('Выполняет обещания')
            adjustment += FACTOR_WEIGHTS['keeps_promises']
        elif promises_kept < 0.3:
            negative.append('Не выполняет обещания')
            adjustment += FACTOR_WEIGHTS['breaks_promises']
        
        # Просрочка
        overdue_days = credit_data.get('overdue_days', 0)
        if overdue_days > 180:
            negative.append(f'Длительная просрочка ({overdue_days} дней)')
            adjustment += FACTOR_WEIGHTS['long_overdue']
        elif overdue_days > 90:
            negative.append('Просрочка более 90 дней')
            adjustment += FACTOR_WEIGHTS['long_overdue'] * 0.5
        elif overdue_days < 30:
            positive.append('Небольшая просрочка')
            adjustment += 0.05
        
        # Сумма долга относительно дохода
        debt = credit_data.get('total_debt', 0)
        if income > 0:
            debt_ratio = debt / income
            if debt_ratio < 2:
                positive.append('Посильный размер долга')
                adjustment += FACTOR_WEIGHTS['small_debt']
            elif debt_ratio > 6:
                negative.append('Долг превышает 6 месячных доходов')
                adjustment -= 0.10
        
        # Триггеры риска
        if behavior_profile.get('job_changed_recently'):
            negative.append('Недавняя смена работы')
            adjustment += FACTOR_WEIGHTS['job_changed']
        
        if behavior_profile.get('income_dropped'):
            negative.append('Падение дохода')
            adjustment -= 0.08
        
        if behavior_profile.get('multiple_credits'):
            negative.append('Множественные кредиты')
            adjustment += FACTOR_WEIGHTS['multiple_debts']
        
        # Частичные платежи
        recent_payments = [c for c in contact_history if c.get('type') == 'payment'][-5:]
        if any(p.get('partial', False) for p in recent_payments):
            positive.append('Делает частичные платежи')
            adjustment += FACTOR_WEIGHTS['partial_payments']
        
        return positive, negative, adjustment

    def calculate_return_probability(
        self,
        risk_segment: str,
        adjustment: float
    ) -> Tuple[float, float]:
        """
        Рассчитывает вероятность полного и частичного возврата.
        
        Returns:
            (full_return_prob, partial_return_prob)
        """
        base_prob = BASE_RETURN_PROBABILITY.get(risk_segment, 0.5)
        
        # Применяем корректировку
        full_prob = max(0.01, min(0.99, base_prob + adjustment))
        
        # Частичный возврат более вероятен
        partial_prob = max(0.01, min(0.99, full_prob * 1.3 + 0.1))
        
        return full_prob, partial_prob

    def calculate_expected_return(
        self,
        total_debt: Decimal,
        full_prob: float,
        partial_prob: float
    ) -> Tuple[Decimal, int]:
        """
        Рассчитывает ожидаемую сумму и срок возврата.
        
        Returns:
            (expected_amount, expected_days)
        """
        # Ожидаемая сумма = P(full)*100% + P(partial-full)*50%
        partial_only_prob = max(0, partial_prob - full_prob)
        expected_pct = full_prob * 1.0 + partial_only_prob * 0.5
        expected_amount = total_debt * Decimal(str(expected_pct))
        
        # Ожидаемый срок зависит от вероятности
        if full_prob > 0.7:
            expected_days = 30
        elif full_prob > 0.5:
            expected_days = 60
        elif full_prob > 0.3:
            expected_days = 120
        else:
            expected_days = 365
        
        return expected_amount, expected_days

    def calculate_npv(
        self,
        expected_amount: Decimal,
        expected_days: int,
        total_debt: Decimal,
        risk_segment: str
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Рассчитывает NPV для разных стратегий.
        
        Returns:
            (npv_continue, npv_sell, npv_write_off)
        """
        # Дисконт-фактор
        years = expected_days / 365
        discount_factor = 1 / ((1 + self.discount_rate) ** years)
        
        # NPV продолжения взыскания
        collection_cost_pct = 0.15  # Затраты на взыскание
        npv_continue = expected_amount * Decimal(str(discount_factor)) - total_debt * Decimal(str(collection_cost_pct))
        
        # NPV продажи
        sale_price = PORTFOLIO_SALE_PRICES.get(risk_segment, 0.20)
        npv_sell = total_debt * Decimal(str(sale_price))
        
        # NPV списания
        tax_benefit = 0.20  # Налоговый вычет при списании
        npv_write_off = total_debt * Decimal(str(tax_benefit)) * Decimal('-1')  # Убыток минус налоговый вычет
        
        return npv_continue, npv_sell, npv_write_off

    def determine_recommendation(
        self,
        full_prob: float,
        npv_continue: Decimal,
        npv_sell: Decimal,
        npv_write_off: Decimal,
        overdue_days: int,
        psychotype: str
    ) -> Tuple[str, float]:
        """
        Определяет стратегическую рекомендацию.
        
        Returns:
            (recommendation, confidence)
        """
        recommendations = []
        
        # Сравниваем NPV
        if npv_continue >= npv_sell and npv_continue >= npv_write_off:
            if full_prob > 0.5:
                recommendations.append(('continue_soft', 0.8))
            else:
                recommendations.append(('continue_hard', 0.7))
        elif npv_sell >= npv_write_off:
            recommendations.append(('sell', 0.75))
        else:
            recommendations.append(('write_off', 0.6))
        
        # Дополнительные правила
        if overdue_days > 365 and full_prob < 0.15:
            recommendations.append(('write_off', 0.85))
        
        if psychotype == 'unable' and full_prob > 0.3:
            recommendations.append(('restructure', 0.70))
        
        if overdue_days > 180 and full_prob < 0.25:
            recommendations.append(('legal', 0.65))
        
        # Выбираем лучшую рекомендацию
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[0]

    def forecast(
        self,
        client_data: Dict,
        behavior_profile: Dict,
        credit_data: Dict,
        contact_history: List[Dict] = None
    ) -> ReturnForecastResult:
        """
        Генерирует полный прогноз возврата.
        
        Args:
            client_data: {income, employment, ...}
            behavior_profile: {psychotype, contact_rate, promises_kept_ratio, ...}
            credit_data: {total_debt, overdue_days, risk_segment, ...}
            contact_history: История контактов и платежей
        
        Returns:
            ReturnForecastResult
        """
        contact_history = contact_history or []
        
        total_debt = Decimal(str(credit_data.get('total_debt', 0)))
        risk_segment = credit_data.get('risk_segment', 'medium')
        overdue_days = credit_data.get('overdue_days', 0)
        psychotype = behavior_profile.get('psychotype', 'unknown')
        
        # Анализ факторов
        positive, negative, adjustment = self.analyze_factors(
            client_data, behavior_profile, credit_data, contact_history
        )
        
        # Вероятности
        full_prob, partial_prob = self.calculate_return_probability(risk_segment, adjustment)
        
        # Ожидаемые показатели
        expected_amount, expected_days = self.calculate_expected_return(
            total_debt, full_prob, partial_prob
        )
        
        # NPV
        npv_continue, npv_sell, npv_write_off = self.calculate_npv(
            expected_amount, expected_days, total_debt, risk_segment
        )
        
        # Рекомендация
        recommendation, confidence = self.determine_recommendation(
            full_prob, npv_continue, npv_sell, npv_write_off, overdue_days, psychotype
        )
        
        return ReturnForecastResult(
            return_probability=round(full_prob, 3),
            partial_return_probability=round(partial_prob, 3),
            expected_return_amount=round(expected_amount, 2),
            expected_return_days=expected_days,
            recommendation=recommendation,
            recommendation_confidence=round(confidence, 2),
            positive_factors=positive,
            negative_factors=negative,
            npv_continue=round(npv_continue, 2),
            npv_sell=round(npv_sell, 2),
            npv_write_off=round(npv_write_off, 2),
        )


def forecast_credit_return(credit) -> ReturnForecastResult:
    """
    Утилита для прогноза возврата по кредиту.
    
    Использовать в views:
        from collection_app.ml.return_forecast import forecast_credit_return
        result = forecast_credit_return(credit)
    """
    from datetime import date
    
    service = ReturnForecastService()
    client = credit.client
    
    # Данные клиента
    client_data = {
        'income': float(client.income) if client.income else 0,
        'employment': client.employment,
    }
    
    # Поведенческий профиль
    behavior_profile = {}
    if hasattr(client, 'behavior_profile'):
        bp = client.behavior_profile
        behavior_profile = {
            'psychotype': bp.psychotype,
            'contact_rate': bp.successful_contacts / bp.total_contacts if bp.total_contacts > 0 else 0.5,
            'promises_kept_ratio': bp.promises_kept_ratio,
            'job_changed_recently': bp.job_changed_recently,
            'income_dropped': bp.income_dropped,
            'multiple_credits': bp.multiple_credits,
        }
    else:
        behavior_profile = {
            'psychotype': 'unknown',
            'contact_rate': 0.5,
            'promises_kept_ratio': 0.5,
        }
    
    # Данные по кредиту
    latest_state = credit.states.order_by('-state_date').first()
    total_debt = float(latest_state.principal_debt) if latest_state else float(credit.principal_amount)
    
    overdue_days = 0
    if credit.status == 'overdue':
        last_payment = credit.payments.order_by('-payment_date').first()
        if last_payment and last_payment.planned_date:
            overdue_days = (date.today() - last_payment.planned_date).days
    
    scoring = credit.scorings.order_by('-calculation_date').first()
    risk_segment = scoring.risk_segment if scoring else 'medium'
    
    credit_data = {
        'total_debt': total_debt,
        'overdue_days': max(overdue_days, 0),
        'risk_segment': risk_segment,
    }
    
    # История
    contact_history = []
    for payment in credit.payments.all():
        contact_history.append({
            'type': 'payment',
            'partial': float(payment.amount) < float(payment.min_payment) if payment.min_payment else False,
        })
    
    return service.forecast(client_data, behavior_profile, credit_data, contact_history)
