"""
Workflow Service - Управление автоматическими бизнес-процессами

Реализует Rules Engine для автоматизации:
- Переходов между стадиями
- Создания задач
- Отправки уведомлений
- Эскалации
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..models import (
    CollectionCase, WorkflowRule, ScheduledAction, CommunicationTask,
    Promise, PreCollectionAlert, Credit, Client
)


class WorkflowEngine:
    """
    Rules Engine для автоматизации бизнес-процессов collection.
    
    Поддерживает:
    - Условные правила (if-then)
    - Запланированные действия
    - Событийную модель
    """
    
    # Операторы сравнения для условий
    OPERATORS = {
        'eq': lambda a, b: a == b,
        'ne': lambda a, b: a != b,
        'gt': lambda a, b: a > b,
        'gte': lambda a, b: a >= b,
        'lt': lambda a, b: a < b,
        'lte': lambda a, b: a <= b,
        'in': lambda a, b: a in b,
        'not_in': lambda a, b: a not in b,
        'contains': lambda a, b: b in str(a),
        'is_null': lambda a, b: a is None if b else a is not None,
    }
    
    @classmethod
    def evaluate_rules(cls, case: CollectionCase) -> List[Dict]:
        """
        Оценка всех активных правил для кейса
        
        Args:
            case: Кейс для оценки
            
        Returns:
            List[Dict]: Список сработавших правил и их действий
        """
        triggered_rules = []
        
        rules = WorkflowRule.objects.filter(
            is_active=True,
            from_stage=case.stage
        ).order_by('priority')
        
        case_data = cls._extract_case_data(case)
        
        for rule in rules:
            if cls._evaluate_conditions(rule.conditions, case_data):
                triggered_rules.append({
                    'rule': rule,
                    'actions': rule.actions,
                    'to_stage': rule.to_stage
                })
        
        return triggered_rules
    
    @classmethod
    def execute_rule(cls, case: CollectionCase, rule: WorkflowRule, 
                     user=None) -> bool:
        """
        Выполнение правила для кейса
        
        Args:
            case: Кейс
            rule: Правило для выполнения
            user: Пользователь (для аудита)
            
        Returns:
            bool: Успешность выполнения
        """
        from .collection_service import CollectionService
        
        with transaction.atomic():
            # Выполняем переход стадии если указан
            if rule.to_stage and rule.to_stage != case.stage:
                success = CollectionService.change_stage(
                    case=case,
                    new_stage=rule.to_stage,
                    user=user,
                    reason=f'Правило: {rule.name}',
                    auto=True
                )
                if not success:
                    return False
            
            # Выполняем действия
            cls._execute_actions(case, rule.actions)
            
            return True
    
    @classmethod
    def process_scheduled_actions(cls) -> Dict[str, int]:
        """
        Обработка запланированных действий
        
        Returns:
            Dict: Статистика обработки
        """
        stats = {'executed': 0, 'failed': 0}
        
        actions = ScheduledAction.objects.filter(
            status='pending',
            scheduled_at__lte=timezone.now()
        ).select_related('case')
        
        for action in actions:
            try:
                cls._execute_scheduled_action(action)
                action.status = 'executed'
                action.executed_at = timezone.now()
                stats['executed'] += 1
            except Exception as e:
                action.status = 'failed'
                action.result = str(e)
                stats['failed'] += 1
            
            action.save()
        
        return stats
    
    @classmethod
    def schedule_action(cls, case: CollectionCase, action_type: str,
                       scheduled_at: datetime, parameters: Dict = None) -> ScheduledAction:
        """
        Планирование действия
        
        Args:
            case: Кейс
            action_type: Тип действия
            scheduled_at: Время выполнения
            parameters: Параметры действия
            
        Returns:
            ScheduledAction: Созданное запланированное действие
        """
        return ScheduledAction.objects.create(
            case=case,
            action_type=action_type,
            scheduled_at=scheduled_at,
            parameters=parameters or {},
            status='pending'
        )
    
    @classmethod
    def create_pre_collection_alerts(cls) -> int:
        """
        Создание алертов Pre-Collection для кредитов близких к просрочке
        
        Returns:
            int: Количество созданных алертов
        """
        today = date.today()
        alert_window = today + timedelta(days=7)  # За 7 дней до платежа
        
        # Находим кредиты с приближающимся платежом
        from ..models import Payment
        
        # Это упрощённая логика - в реальности нужно анализировать график платежей
        credits_at_risk = Credit.objects.filter(
            status='active'
        ).exclude(
            precollection_alerts__created_at__gte=today - timedelta(days=3)
        )
        
        created_count = 0
        
        for credit in credits_at_risk[:100]:  # Лимит на итерацию
            # Проверяем риск-скор
            risk_score = cls._calculate_early_warning_score(credit)
            
            if risk_score > 0.6:  # Порог риска
                PreCollectionAlert.objects.create(
                    client=credit.client,
                    credit=credit,
                    alert_type='high_risk_detected',
                    days_before_due=7,
                    risk_score=risk_score
                )
                created_count += 1
        
        return created_count
    
    @classmethod
    def check_promises(cls) -> Dict[str, int]:
        """
        Проверка выполнения обещаний
        
        Returns:
            Dict: Статистика проверки
        """
        from .collection_service import CollectionService
        
        stats = {'kept': 0, 'broken': 0, 'partial': 0}
        
        # Обещания с истёкшим сроком
        overdue_promises = Promise.objects.filter(
            status='pending',
            promised_date__lt=date.today()
        )
        
        for promise in overdue_promises:
            CollectionService.check_promise_fulfillment(promise)
            stats[promise.status] = stats.get(promise.status, 0) + 1
        
        return stats
    
    # ==================== Приватные методы ====================
    
    @classmethod
    def _extract_case_data(cls, case: CollectionCase) -> Dict[str, Any]:
        """Извлечение данных кейса для оценки условий"""
        return {
            'stage': case.stage,
            'status': case.status,
            'priority': case.priority,
            'priority_score': case.priority_score,
            'total_debt': float(case.total_debt),
            'overdue_amount': float(case.overdue_amount),
            'overdue_days': case.overdue_days,
            'total_contacts': case.total_contacts,
            'successful_contacts': case.successful_contacts,
            'promises_count': case.promises_count,
            'broken_promises': case.broken_promises,
            'return_probability': case.return_probability,
            'risk_segment': case.risk_segment,
            'psychotype': case.psychotype,
            'days_in_stage': (timezone.now() - case.stage_changed_at).days if case.stage_changed_at else 0,
            'has_operator': case.assigned_operator is not None,
        }
    
    @classmethod
    def _evaluate_conditions(cls, conditions: Dict, data: Dict) -> bool:
        """
        Оценка условий правила
        
        Args:
            conditions: Словарь условий {field: {operator: value}}
            data: Данные для проверки
            
        Returns:
            bool: Все условия выполнены
        """
        for field, field_conditions in conditions.items():
            if field not in data:
                return False
            
            field_value = data[field]
            
            for operator, expected_value in field_conditions.items():
                op_func = cls.OPERATORS.get(operator)
                if not op_func:
                    continue
                
                if not op_func(field_value, expected_value):
                    return False
        
        return True
    
    @classmethod
    def _execute_actions(cls, case: CollectionCase, actions: Dict) -> None:
        """Выполнение действий правила"""
        
        # Создание задачи
        if 'create_task' in actions:
            task_type = actions['create_task']
            CommunicationTask.objects.create(
                case=case,
                operator=case.assigned_operator,
                task_type=task_type,
                priority=actions.get('task_priority', case.priority),
                scheduled_date=date.today() + timedelta(days=actions.get('task_delay_days', 0)),
                status='pending'
            )
        
        # Изменение приоритета
        if 'change_priority' in actions:
            case.priority = actions['change_priority']
            case.save(update_fields=['priority', 'updated_at'])
        
        # Уведомление менеджера
        if actions.get('notify_manager'):
            cls._send_manager_notification(case)
        
        # Планирование действия
        if 'schedule_action' in actions:
            action_config = actions['schedule_action']
            cls.schedule_action(
                case=case,
                action_type=action_config['type'],
                scheduled_at=timezone.now() + timedelta(hours=action_config.get('delay_hours', 24)),
                parameters=action_config.get('parameters', {})
            )
    
    @classmethod
    def _execute_scheduled_action(cls, action: ScheduledAction) -> None:
        """Выполнение запланированного действия"""
        case = action.case
        params = action.parameters
        
        if action.action_type == 'send_sms':
            cls._send_sms(case.client, params.get('template', 'default'))
        
        elif action.action_type == 'send_email':
            cls._send_email(case.client, params.get('template', 'default'))
        
        elif action.action_type == 'create_task':
            CommunicationTask.objects.create(
                case=case,
                operator=case.assigned_operator,
                task_type=params.get('task_type', 'call_followup'),
                priority=params.get('priority', 2),
                scheduled_date=date.today(),
                status='pending'
            )
        
        elif action.action_type == 'escalate':
            from .collection_service import CollectionService
            CollectionService.change_stage(
                case=case,
                new_stage=params.get('to_stage', 'soft_late'),
                reason='Автоматическая эскалация',
                auto=True
            )
        
        elif action.action_type == 'check_promise':
            from .collection_service import CollectionService
            pending_promises = case.promises.filter(status='pending')
            for promise in pending_promises:
                CollectionService.check_promise_fulfillment(promise)
        
        elif action.action_type == 'check_payment':
            # Проверка поступления платежа
            cls._check_payment_received(case)
    
    @classmethod
    def _calculate_early_warning_score(cls, credit: Credit) -> float:
        """Расчёт раннего предупреждающего скора"""
        score = 0.5
        
        # Получаем последнее состояние
        latest_state = credit.states.order_by('-state_date').first()
        if not latest_state:
            return score
        
        # Факторы риска
        if latest_state.overdue_days > 0:
            score += 0.3
        
        # История просрочек
        past_overdue = credit.states.filter(overdue_days__gt=0).count()
        if past_overdue > 2:
            score += 0.2
        
        # DTI
        client = credit.client
        if client.income > 0:
            dti = (float(credit.monthly_payment) + float(client.monthly_expenses)) / float(client.income)
            if dti > 0.6:
                score += 0.15
        
        return min(score, 1.0)
    
    @classmethod
    def _send_sms(cls, client: Client, template: str) -> None:
        """Отправка SMS (заглушка для интеграции)"""
        # TODO: Интеграция с SMS-шлюзом
        pass
    
    @classmethod
    def _send_email(cls, client: Client, template: str) -> None:
        """Отправка Email (заглушка для интеграции)"""
        # TODO: Интеграция с email-сервисом
        pass
    
    @classmethod
    def _send_manager_notification(cls, case: CollectionCase) -> None:
        """Уведомление менеджера (заглушка)"""
        # TODO: Интеграция с системой уведомлений
        pass
    
    @classmethod
    def _check_payment_received(cls, case: CollectionCase) -> bool:
        """Проверка поступления платежа"""
        from django.db.models import Sum
        
        credit = case.credits.first()
        if not credit:
            return False
        
        recent_payments = credit.payments.filter(
            payment_date__gte=date.today() - timedelta(days=3)
        ).aggregate(Sum('amount'))
        
        return (recent_payments['amount__sum'] or 0) > 0


class RulesBuilder:
    """
    Фабрика для создания типовых правил workflow
    """
    
    @classmethod
    def create_dpd_escalation_rule(cls, from_stage: str, to_stage: str, 
                                   dpd_threshold: int) -> WorkflowRule:
        """Создание правила эскалации по DPD"""
        return WorkflowRule.objects.create(
            name=f'Эскалация {from_stage} → {to_stage} при DPD >= {dpd_threshold}',
            description=f'Автоматический переход при достижении {dpd_threshold} дней просрочки',
            from_stage=from_stage,
            to_stage=to_stage,
            conditions={
                'overdue_days': {'gte': dpd_threshold}
            },
            actions={
                'notify_manager': True,
                'create_task': 'call_followup'
            },
            priority=10,
            is_active=True
        )
    
    @classmethod
    def create_broken_promise_rule(cls, from_stage: str, to_stage: str,
                                   max_broken: int = 2) -> WorkflowRule:
        """Создание правила эскалации по нарушенным обещаниям"""
        return WorkflowRule.objects.create(
            name=f'Эскалация при {max_broken}+ нарушенных обещаниях',
            from_stage=from_stage,
            to_stage=to_stage,
            conditions={
                'broken_promises': {'gte': max_broken}
            },
            actions={
                'change_priority': 5,
                'notify_manager': True
            },
            priority=5,
            is_active=True
        )
    
    @classmethod
    def create_no_contact_rule(cls, from_stage: str, to_stage: str,
                               max_attempts: int = 10) -> WorkflowRule:
        """Создание правила при невозможности связаться"""
        return WorkflowRule.objects.create(
            name=f'Эскалация при {max_attempts}+ безуспешных контактах',
            from_stage=from_stage,
            to_stage=to_stage,
            conditions={
                'total_contacts': {'gte': max_attempts},
                'successful_contacts': {'lt': 2}
            },
            actions={
                'create_task': 'letter_demand'
            },
            priority=15,
            is_active=True
        )
    
    @classmethod
    def setup_default_rules(cls) -> int:
        """Создание набора типовых правил"""
        rules = [
            # Soft Early → Soft Late
            cls.create_dpd_escalation_rule('soft_early', 'soft_late', 30),
            cls.create_broken_promise_rule('soft_early', 'soft_late', 2),
            
            # Soft Late → Hard
            cls.create_dpd_escalation_rule('soft_late', 'hard', 60),
            cls.create_broken_promise_rule('soft_late', 'hard', 3),
            cls.create_no_contact_rule('soft_late', 'hard', 10),
            
            # Hard → Legal
            cls.create_dpd_escalation_rule('hard', 'legal_pretrial', 90),
        ]
        
        return len(rules)
