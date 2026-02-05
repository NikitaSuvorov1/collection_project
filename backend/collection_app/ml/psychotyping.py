"""
Сервис психотипирования клиентов.

Автоматическая сегментация не по сумме долга, а по поведенческому профилю:
- "забыл / прокрастинирует"
- "может платить, но не хочет"
- "хочет платить, но не может"
- "токсичный / конфликтный"
- "готов к диалогу"
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple


@dataclass
class PsychotypeResult:
    """Результат определения психотипа."""
    psychotype: str
    confidence: float
    factors: List[str]
    recommended_approach: str


# Веса признаков для каждого психотипа
PSYCHOTYPE_INDICATORS = {
    'forgetful': {
        # Забыл / прокрастинирует
        'description': 'Забыл / Прокрастинирует',
        'indicators': {
            'small_overdue_days': 0.25,        # Небольшая просрочка
            'random_payment_pattern': 0.20,     # Нерегулярные платежи
            'answers_calls': 0.15,              # Отвечает на звонки
            'makes_promises': 0.15,             # Даёт обещания
            'partial_promise_kept': 0.15,       # Частично выполняет обещания
            'no_conflict': 0.10,                # Нет конфликтов
        },
        'approach': 'Мягкие напоминания, автоматические уведомления, удобные способы оплаты'
    },
    'unwilling': {
        # Может платить, но не хочет
        'description': 'Может платить, но не хочет',
        'indicators': {
            'has_income': 0.25,                 # Есть доход
            'low_debt_to_income': 0.20,         # Долг посильный
            'ignores_contacts': 0.20,           # Игнорирует контакты
            'no_promises': 0.15,                # Не даёт обещаний
            'excuses': 0.10,                    # Находит отговорки
            'selective_payment': 0.10,          # Платит выборочно
        },
        'approach': 'Скидки за быструю оплату, угроза последствий, жёсткий тон'
    },
    'unable': {
        # Хочет платить, но не может
        'description': 'Хочет платить, но не может',
        'indicators': {
            'low_income': 0.20,                 # Низкий доход
            'high_debt_to_income': 0.25,        # Высокая долговая нагрузка
            'answers_calls': 0.15,              # Отвечает на звонки
            'explains_situation': 0.15,         # Объясняет ситуацию
            'asks_for_restructure': 0.15,       # Просит реструктуризацию
            'partial_payments': 0.10,           # Делает частичные платежи
        },
        'approach': 'Реструктуризация, кредитные каникулы, индивидуальный график'
    },
    'toxic': {
        # Токсичный / Конфликтный
        'description': 'Токсичный / Конфликтный',
        'indicators': {
            'aggression': 0.30,                 # Агрессия в разговорах
            'threats': 0.25,                    # Угрозы жалобами
            'refuses_contact': 0.15,            # Отказывается общаться
            'disputes_debt': 0.15,              # Оспаривает долг
            'multiple_complaints': 0.15,        # Множественные жалобы
        },
        'approach': 'Только письменные контакты, юридический путь, минимум звонков'
    },
    'cooperative': {
        # Готов к диалогу
        'description': 'Готов к диалогу',
        'indicators': {
            'answers_calls': 0.20,              # Отвечает на звонки
            'keeps_promises': 0.25,             # Выполняет обещания
            'proactive_contact': 0.20,          # Сам выходит на связь
            'regular_payments': 0.20,           # Регулярные платежи
            'constructive_dialog': 0.15,        # Конструктивный диалог
        },
        'approach': 'Стандартное сопровождение, поддержка, гибкие условия'
    },
}


class PsychotypingService:
    """Сервис автоматического определения психотипа клиента."""

    def analyze_payment_behavior(
        self,
        payments: List[Dict],
        income: Decimal,
        total_debt: Decimal
    ) -> Dict[str, float]:
        """
        Анализирует платёжное поведение.
        
        Returns:
            Словарь признаков с весами
        """
        indicators = {}
        
        if not payments:
            indicators['no_payments'] = 1.0
            return indicators
        
        # Анализ регулярности платежей
        on_time = sum(1 for p in payments if p.get('overdue_days', 0) <= 3)
        late = sum(1 for p in payments if p.get('overdue_days', 0) > 3)
        
        if len(payments) > 0:
            on_time_ratio = on_time / len(payments)
            indicators['regular_payments'] = on_time_ratio
            indicators['random_payment_pattern'] = 1 - on_time_ratio if on_time_ratio < 0.7 else 0
        
        # Частичные платежи
        partial = sum(1 for p in payments if p.get('amount', 0) < p.get('min_payment', 0))
        if len(payments) > 0:
            indicators['partial_payments'] = partial / len(payments)
        
        # Отношение долга к доходу
        if income > 0:
            debt_ratio = float(total_debt) / float(income)
            indicators['high_debt_to_income'] = min(debt_ratio / 6, 1.0)  # Макс при 6x
            indicators['low_debt_to_income'] = max(0, 1 - debt_ratio / 3)
            indicators['has_income'] = 1.0
            indicators['low_income'] = 1.0 if income < 30000 else 0.5 if income < 50000 else 0
        else:
            indicators['low_income'] = 0.8
            indicators['high_debt_to_income'] = 0.8
        
        return indicators

    def analyze_contact_behavior(
        self,
        interventions: List[Dict]
    ) -> Dict[str, float]:
        """
        Анализирует поведение при контактах.
        
        Returns:
            Словарь признаков с весами
        """
        indicators = {}
        
        if not interventions:
            indicators['no_contact_history'] = 1.0
            return indicators
        
        total = len(interventions)
        
        # Отвечает на звонки
        answered = sum(1 for i in interventions if i.get('status') != 'no_answer')
        indicators['answers_calls'] = answered / total if total > 0 else 0
        indicators['ignores_contacts'] = 1 - (answered / total) if total > 0 else 0.5
        
        # Даёт обещания
        promises = sum(1 for i in interventions if i.get('status') == 'promise')
        indicators['makes_promises'] = promises / total if total > 0 else 0
        indicators['no_promises'] = 1 - (promises / total) if total > 0 else 0.5
        
        # Отказы
        refuses = sum(1 for i in interventions if i.get('status') == 'refuse')
        indicators['refuses_contact'] = refuses / total if total > 0 else 0
        
        # Агрессия (по тегам, если есть)
        aggression = sum(1 for i in interventions if i.get('aggression_detected', False))
        indicators['aggression'] = aggression / total if total > 0 else 0
        
        # Нет конфликтов
        indicators['no_conflict'] = 1 - indicators.get('aggression', 0) - indicators.get('refuses_contact', 0) / 2
        indicators['no_conflict'] = max(0, indicators['no_conflict'])
        
        return indicators

    def analyze_promise_keeping(
        self,
        promises: List[Dict]
    ) -> Dict[str, float]:
        """
        Анализирует выполнение обещаний.
        
        Returns:
            Словарь признаков с весами
        """
        indicators = {}
        
        if not promises:
            return indicators
        
        total = len(promises)
        kept = sum(1 for p in promises if p.get('kept', False))
        partial = sum(1 for p in promises if p.get('partial', False))
        
        indicators['keeps_promises'] = kept / total if total > 0 else 0
        indicators['partial_promise_kept'] = partial / total if total > 0 else 0
        
        return indicators

    def calculate_psychotype_scores(
        self,
        all_indicators: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Рассчитывает баллы для каждого психотипа.
        
        Returns:
            {psychotype: score}
        """
        scores = {}
        
        for psychotype, config in PSYCHOTYPE_INDICATORS.items():
            score = 0.0
            max_score = 0.0
            
            for indicator, weight in config['indicators'].items():
                max_score += weight
                if indicator in all_indicators:
                    score += all_indicators[indicator] * weight
            
            # Нормализуем
            scores[psychotype] = score / max_score if max_score > 0 else 0
        
        return scores

    def determine_psychotype(
        self,
        client_data: Dict,
        payments: List[Dict] = None,
        interventions: List[Dict] = None,
        promises: List[Dict] = None
    ) -> PsychotypeResult:
        """
        Определяет психотип клиента на основе всех данных.
        
        Args:
            client_data: {income, total_debt, overdue_days, ...}
            payments: История платежей
            interventions: История контактов
            promises: История обещаний
        
        Returns:
            PsychotypeResult с психотипом и уверенностью
        """
        payments = payments or []
        interventions = interventions or []
        promises = promises or []
        
        income = Decimal(str(client_data.get('income', 0)))
        total_debt = Decimal(str(client_data.get('total_debt', 0)))
        overdue_days = client_data.get('overdue_days', 0)
        
        # Собираем все индикаторы
        all_indicators = {}
        
        # Платёжное поведение
        payment_indicators = self.analyze_payment_behavior(payments, income, total_debt)
        all_indicators.update(payment_indicators)
        
        # Контактное поведение
        contact_indicators = self.analyze_contact_behavior(interventions)
        all_indicators.update(contact_indicators)
        
        # Выполнение обещаний
        promise_indicators = self.analyze_promise_keeping(promises)
        all_indicators.update(promise_indicators)
        
        # Дополнительные индикаторы по просрочке
        if overdue_days <= 14:
            all_indicators['small_overdue_days'] = 1.0
        elif overdue_days <= 30:
            all_indicators['small_overdue_days'] = 0.5
        else:
            all_indicators['small_overdue_days'] = 0
        
        # Рассчитываем баллы
        scores = self.calculate_psychotype_scores(all_indicators)
        
        # Определяем победителя
        best_psychotype = max(scores, key=scores.get)
        confidence = scores[best_psychotype]
        
        # Собираем факторы (топ-3 индикатора)
        psychotype_config = PSYCHOTYPE_INDICATORS[best_psychotype]
        relevant_indicators = [
            (ind, all_indicators.get(ind, 0))
            for ind in psychotype_config['indicators'].keys()
            if ind in all_indicators
        ]
        relevant_indicators.sort(key=lambda x: x[1], reverse=True)
        factors = [ind for ind, val in relevant_indicators[:3] if val > 0.3]
        
        # Человекочитаемые факторы
        factor_names = {
            'answers_calls': 'Отвечает на звонки',
            'ignores_contacts': 'Игнорирует контакты',
            'keeps_promises': 'Выполняет обещания',
            'partial_payments': 'Делает частичные платежи',
            'high_debt_to_income': 'Высокая долговая нагрузка',
            'low_income': 'Низкий доход',
            'aggression': 'Агрессивное поведение',
            'regular_payments': 'Регулярные платежи',
            'makes_promises': 'Даёт обещания',
            'small_overdue_days': 'Небольшая просрочка',
        }
        
        readable_factors = [factor_names.get(f, f) for f in factors]
        
        return PsychotypeResult(
            psychotype=best_psychotype,
            confidence=round(confidence, 2),
            factors=readable_factors,
            recommended_approach=psychotype_config['approach']
        )


def classify_client(client) -> PsychotypeResult:
    """
    Утилита для классификации клиента.
    
    Использовать в views:
        from collection_app.ml.psychotyping import classify_client
        result = classify_client(client)
        print(result.psychotype, result.confidence)
    """
    service = PsychotypingService()
    
    # Собираем данные
    total_debt = sum(
        float(c.states.order_by('-state_date').first().principal_debt or 0)
        for c in client.credits.all()
        if c.states.exists()
    )
    
    overdue_days = 0
    for credit in client.credits.filter(status='overdue'):
        last_payment = credit.payments.order_by('-payment_date').first()
        if last_payment and last_payment.planned_date:
            days = (date.today() - last_payment.planned_date).days
            overdue_days = max(overdue_days, days)
    
    client_data = {
        'income': float(client.income) if client.income else 0,
        'total_debt': total_debt,
        'overdue_days': overdue_days,
    }
    
    # Платежи
    all_payments = []
    for credit in client.credits.all():
        for p in credit.payments.all():
            all_payments.append({
                'amount': float(p.amount),
                'min_payment': float(p.min_payment) if p.min_payment else 0,
                'overdue_days': p.overdue_days,
            })
    
    # Контакты
    interventions = [
        {
            'status': i.status,
            'aggression_detected': False,  # Можно расширить через ConversationAnalysis
        }
        for i in client.interventions.all()
    ]
    
    # Обещания
    promises = [
        {
            'kept': i.status == 'completed' and i.promise_amount > 0,
            'partial': False,
        }
        for i in client.interventions.filter(status='promise')
    ]
    
    return service.determine_psychotype(
        client_data=client_data,
        payments=all_payments,
        interventions=interventions,
        promises=promises
    )


def update_client_profile(client) -> None:
    """
    Обновляет поведенческий профиль клиента.
    
    Использовать в cron-задаче или после каждого контакта:
        from collection_app.ml.psychotyping import update_client_profile
        update_client_profile(client)
    """
    from collection_app.models import ClientBehaviorProfile
    
    result = classify_client(client)
    
    profile, created = ClientBehaviorProfile.objects.get_or_create(client=client)
    profile.psychotype = result.psychotype
    profile.psychotype_confidence = result.confidence
    profile.save()
