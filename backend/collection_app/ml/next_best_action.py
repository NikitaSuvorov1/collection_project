"""
Next Best Action (NBA) — ML-сервис рекомендаций по взысканию.

Подсказывает оператору:
- Когда выходить на контакт
- По какому каналу (звонок, мессенджер, письмо)
- С каким сценарием разговора
- Какое предложение дать (реструктуризация, каникулы, скидка)
"""
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

# Веса для расчёта оптимального канала связи
CHANNEL_WEIGHTS = {
    'phone': {'base': 0.5, 'contact_rate': 0.65, 'ptp_rate': 0.45},
    'whatsapp': {'base': 0.6, 'contact_rate': 0.78, 'ptp_rate': 0.35},
    'sms': {'base': 0.4, 'contact_rate': 0.42, 'ptp_rate': 0.18},
    'email': {'base': 0.3, 'contact_rate': 0.25, 'ptp_rate': 0.12},
    'push': {'base': 0.35, 'contact_rate': 0.55, 'ptp_rate': 0.15},
}

# Сценарии по психотипам
SCENARIO_BY_PSYCHOTYPE = {
    'forgetful': ['soft_reminder', 'empathy'],
    'unwilling': ['firm_demand', 'discount_offer', 'last_warning'],
    'unable': ['restructure_offer', 'payment_holiday', 'empathy'],
    'toxic': ['firm_demand', 'last_warning'],
    'cooperative': ['soft_reminder', 'restructure_offer'],
}

# Предложения по сегментам риска
OFFERS_BY_RISK = {
    'low': ['none', 'discount_10'],
    'medium': ['discount_10', 'discount_20', 'restructure_6m'],
    'high': ['discount_20', 'discount_50', 'restructure_12m', 'holiday_1m'],
    'critical': ['discount_50', 'holiday_3m', 'partial_write_off'],
}


class NextBestActionService:
    """Сервис генерации рекомендаций Next Best Action."""

    def __init__(self):
        self.current_hour = datetime.now().hour

    def calculate_best_contact_time(
        self,
        client_profile: Dict,
        overdue_days: int
    ) -> Tuple[datetime, int]:
        """
        Определяет лучшее время для контакта и срочность.
        
        Returns:
            (recommended_datetime, urgency 1-5)
        """
        # Базовое лучшее время из профиля клиента
        best_hour = client_profile.get('best_contact_hour', 14)
        best_day = client_profile.get('best_contact_day', 2)  # 0=Пн
        
        now = datetime.now()
        current_weekday = now.weekday()
        
        # Определяем срочность на основе просрочки
        if overdue_days > 90:
            urgency = 5  # Критично
        elif overdue_days > 60:
            urgency = 4
        elif overdue_days > 30:
            urgency = 3
        elif overdue_days > 14:
            urgency = 2
        else:
            urgency = 1  # Низкая срочность
        
        # Если высокая срочность — рекомендуем сегодня в ближайшее разрешённое время
        if urgency >= 4:
            if 9 <= now.hour < 20:
                recommended = now + timedelta(minutes=15)
            else:
                # Следующий рабочий день в 9:00
                recommended = now.replace(hour=9, minute=0, second=0, microsecond=0)
                if now.hour >= 20:
                    recommended += timedelta(days=1)
        else:
            # Рекомендуем оптимальное время
            days_until_best = (best_day - current_weekday) % 7
            if days_until_best == 0 and now.hour >= best_hour:
                days_until_best = 7
            recommended = now.replace(
                hour=best_hour, minute=0, second=0, microsecond=0
            ) + timedelta(days=days_until_best)
        
        # Не рекомендуем контакт в выходные для низкой срочности
        if urgency < 3 and recommended.weekday() >= 5:
            days_to_monday = 7 - recommended.weekday()
            recommended += timedelta(days=days_to_monday)
        
        return recommended, urgency

    def calculate_best_channel(
        self,
        client_profile: Dict,
        psychotype: str,
        overdue_amount: Decimal,
        failed_channels: List[str] = None
    ) -> Tuple[str, float]:
        """
        Определяет лучший канал связи.
        
        Returns:
            (channel, confidence)
        """
        failed_channels = failed_channels or []
        preferred = client_profile.get('preferred_channel', 'phone')
        
        scores = {}
        for channel, weights in CHANNEL_WEIGHTS.items():
            if channel in failed_channels:
                continue
            
            score = weights['base']
            
            # Бонус за предпочтительный канал
            if channel == preferred:
                score += 0.25
            
            # Психотип влияет на выбор
            if psychotype == 'toxic' and channel == 'phone':
                score -= 0.2  # Лучше избегать прямого контакта
            elif psychotype == 'forgetful' and channel in ['sms', 'push']:
                score += 0.15  # Напоминания эффективны
            elif psychotype == 'unwilling' and channel == 'phone':
                score += 0.1  # Нужен личный контакт
            
            # Большая сумма — нужен личный контакт
            if overdue_amount > 100000 and channel == 'phone':
                score += 0.2
            elif overdue_amount < 10000 and channel in ['sms', 'push']:
                score += 0.15
            
            scores[channel] = min(score, 1.0)
        
        if not scores:
            return 'phone', 0.3
        
        best_channel = max(scores, key=scores.get)
        return best_channel, scores[best_channel]

    def calculate_best_scenario(
        self,
        psychotype: str,
        overdue_days: int,
        contact_history: List[Dict],
        promises_kept_ratio: float
    ) -> Tuple[str, List[str]]:
        """
        Определяет лучший сценарий разговора.
        
        Returns:
            (scenario, reasoning)
        """
        reasoning = []
        
        # Базовые сценарии по психотипу
        possible_scenarios = SCENARIO_BY_PSYCHOTYPE.get(psychotype, ['soft_reminder'])
        
        # Корректируем на основе истории
        prev_scenarios = [c.get('scenario') for c in contact_history[-5:]]
        
        # Если мягкий подход не работает — усиливаем
        if prev_scenarios.count('soft_reminder') >= 2:
            if 'firm_demand' not in possible_scenarios:
                possible_scenarios.append('firm_demand')
            reasoning.append('Мягкий подход не дал результата')
        
        # Если клиент не выполняет обещания — жёсткий сценарий
        if promises_kept_ratio < 0.3:
            possible_scenarios = ['firm_demand', 'last_warning']
            reasoning.append(f'Низкий % выполнения обещаний ({promises_kept_ratio:.0%})')
        
        # Большая просрочка — предлагаем реструктуризацию
        if overdue_days > 60 and psychotype != 'toxic':
            if 'restructure_offer' not in possible_scenarios:
                possible_scenarios.insert(0, 'restructure_offer')
            reasoning.append('Большой срок просрочки — предложите реструктуризацию')
        
        # Выбираем сценарий (приоритет по порядку)
        scenario = possible_scenarios[0] if possible_scenarios else 'soft_reminder'
        
        if not reasoning:
            reasoning.append(f'Рекомендовано для психотипа "{psychotype}"')
        
        return scenario, reasoning

    def calculate_best_offer(
        self,
        risk_segment: str,
        overdue_amount: Decimal,
        total_debt: Decimal,
        psychotype: str,
        income: Decimal = None
    ) -> Tuple[str, float, List[str]]:
        """
        Определяет лучшее предложение клиенту.
        
        Returns:
            (offer, max_discount_percent, reasoning)
        """
        reasoning = []
        possible_offers = OFFERS_BY_RISK.get(risk_segment, ['none'])
        
        # Рассчитываем максимальную скидку
        if risk_segment == 'critical':
            max_discount = 50.0
        elif risk_segment == 'high':
            max_discount = 30.0
        elif risk_segment == 'medium':
            max_discount = 15.0
        else:
            max_discount = 5.0
        
        # Корректируем на основе дохода
        if income:
            debt_to_income = float(total_debt) / float(income) if income > 0 else 999
            if debt_to_income > 6:
                possible_offers = ['restructure_12m', 'holiday_3m', 'partial_write_off']
                max_discount = min(max_discount + 20, 50)
                reasoning.append(f'Высокое отношение долга к доходу ({debt_to_income:.1f}x)')
            elif debt_to_income > 3:
                if 'restructure_6m' not in possible_offers:
                    possible_offers.insert(0, 'restructure_6m')
                reasoning.append('Умеренная долговая нагрузка')
        
        # Психотип влияет на предложения
        if psychotype == 'unable':
            possible_offers = [o for o in possible_offers if 'restructure' in o or 'holiday' in o]
            reasoning.append('Клиент хочет платить, но не может — предложите рассрочку')
        elif psychotype == 'unwilling':
            possible_offers = [o for o in possible_offers if 'discount' in o]
            reasoning.append('Клиент может платить — предложите скидку за быструю оплату')
        
        offer = possible_offers[0] if possible_offers else 'none'
        
        return offer, max_discount, reasoning

    def generate_nba(
        self,
        client_id: int,
        credit_id: int,
        client_profile: Dict,
        credit_data: Dict,
        contact_history: List[Dict] = None
    ) -> Dict:
        """
        Генерирует полную рекомендацию Next Best Action.
        
        Args:
            client_id: ID клиента
            credit_id: ID кредита
            client_profile: Данные профиля поведения клиента
            credit_data: Данные по кредиту (overdue_amount, overdue_days, risk_segment и т.д.)
            contact_history: История контактов
        
        Returns:
            Словарь с рекомендацией NBA
        """
        contact_history = contact_history or []
        
        psychotype = client_profile.get('psychotype', 'forgetful')
        overdue_days = credit_data.get('overdue_days', 0)
        overdue_amount = Decimal(str(credit_data.get('overdue_amount', 0)))
        total_debt = Decimal(str(credit_data.get('total_debt', overdue_amount)))
        risk_segment = credit_data.get('risk_segment', 'medium')
        income = Decimal(str(client_profile.get('income', 0))) if client_profile.get('income') else None
        promises_kept_ratio = client_profile.get('promises_kept_ratio', 0.5)
        
        # Каналы, которые уже не сработали
        failed_channels = [
            c.get('channel') for c in contact_history[-3:]
            if c.get('result') in ['no_answer', 'refuse']
        ]
        
        # Генерируем рекомендации
        recommended_time, urgency = self.calculate_best_contact_time(
            client_profile, overdue_days
        )
        
        channel, channel_confidence = self.calculate_best_channel(
            client_profile, psychotype, overdue_amount, failed_channels
        )
        
        scenario, scenario_reasoning = self.calculate_best_scenario(
            psychotype, overdue_days, contact_history, promises_kept_ratio
        )
        
        offer, max_discount, offer_reasoning = self.calculate_best_offer(
            risk_segment, overdue_amount, total_debt, psychotype, income
        )
        
        # Формируем обоснование
        all_reasoning = scenario_reasoning + offer_reasoning
        reasoning_text = '. '.join(all_reasoning) if all_reasoning else 'Стандартная рекомендация'
        
        # Общая уверенность
        confidence = (channel_confidence + 0.5) / 2  # Усредняем
        
        return {
            'client_id': client_id,
            'credit_id': credit_id,
            'recommended_datetime': recommended_time.isoformat(),
            'urgency': urgency,
            'recommended_channel': channel,
            'recommended_scenario': scenario,
            'recommended_offer': offer,
            'max_discount_percent': max_discount,
            'reasoning': reasoning_text,
            'confidence_score': round(confidence, 2),
        }


def get_nba_for_client(client, credit) -> Dict:
    """
    Утилита для быстрого получения NBA для клиента.
    
    Использовать в views:
        from collection_app.ml.next_best_action import get_nba_for_client
        nba = get_nba_for_client(client, credit)
    """
    service = NextBestActionService()
    
    # Собираем профиль клиента
    profile = {}
    if hasattr(client, 'behavior_profile'):
        bp = client.behavior_profile
        profile = {
            'psychotype': bp.psychotype,
            'best_contact_hour': bp.best_contact_hour,
            'best_contact_day': bp.best_contact_day,
            'preferred_channel': bp.preferred_channel,
            'promises_kept_ratio': bp.promises_kept_ratio,
            'income': float(client.income) if client.income else 0,
        }
    else:
        profile = {
            'psychotype': 'forgetful',
            'best_contact_hour': 14,
            'best_contact_day': 2,
            'preferred_channel': 'phone',
            'promises_kept_ratio': 0.5,
            'income': float(client.income) if client.income else 0,
        }
    
    # Собираем данные по кредиту
    latest_state = credit.states.order_by('-state_date').first()
    overdue_amount = float(latest_state.overdue_principal) if latest_state else 0
    total_debt = float(latest_state.principal_debt) if latest_state else 0
    
    # Определяем дни просрочки
    from django.utils import timezone
    from datetime import date
    overdue_days = 0
    if credit.status == 'overdue':
        last_payment = credit.payments.order_by('-payment_date').first()
        if last_payment and last_payment.planned_date:
            overdue_days = (date.today() - last_payment.planned_date).days
    
    # Риск-сегмент из скоринга
    scoring = credit.scorings.order_by('-calculation_date').first()
    risk_segment = scoring.risk_segment if scoring else 'medium'
    
    credit_data = {
        'overdue_days': max(overdue_days, 0),
        'overdue_amount': overdue_amount,
        'total_debt': total_debt,
        'risk_segment': risk_segment,
    }
    
    # История контактов
    interventions = client.interventions.filter(credit=credit).order_by('-datetime')[:10]
    contact_history = [
        {
            'channel': i.intervention_type,
            'result': i.status,
            'scenario': 'soft_reminder',  # Упрощённо
        }
        for i in interventions
    ]
    
    return service.generate_nba(
        client_id=client.id,
        credit_id=credit.id,
        client_profile=profile,
        credit_data=credit_data,
        contact_history=contact_history
    )
