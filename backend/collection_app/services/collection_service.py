"""
Collection Service - Бизнес-логика управления процессом взыскания

Разделение ответственности:
- Views: обработка HTTP запросов/ответов
- Serializers: валидация и сериализация данных
- Services: бизнес-логика
- Models: данные и ORM
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Tuple
from django.db import transaction
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone

from ..models import (
    CollectionCase, CollectionStageHistory, Client, Credit, CreditState,
    Operator, CommunicationTask, Promise, FieldVisit, LegalCase,
    RestructuringRequest, WorkflowRule, ScheduledAction, PreCollectionAlert,
    Intervention, AuditLog
)


class CollectionService:
    """
    Сервис управления процессом взыскания.
    Инкапсулирует всю бизнес-логику collection.
    """
    
    # Пороги для автоматического перехода между стадиями
    STAGE_THRESHOLDS = {
        'pre_collection': {'max_dpd': 0, 'min_dpd': -7},  # за 7 дней до просрочки
        'soft_early': {'max_dpd': 30, 'min_dpd': 1},
        'soft_late': {'max_dpd': 60, 'min_dpd': 31},
        'hard': {'max_dpd': 90, 'min_dpd': 61},
        'legal_pretrial': {'max_dpd': 120, 'min_dpd': 91},
        'legal_court': {'max_dpd': None, 'min_dpd': 121},
    }
    
    # Правила эскалации
    ESCALATION_RULES = {
        'soft_early': {
            'max_contacts_without_result': 5,
            'max_broken_promises': 2,
            'escalate_to': 'soft_late'
        },
        'soft_late': {
            'max_contacts_without_result': 7,
            'max_broken_promises': 3,
            'escalate_to': 'hard'
        },
        'hard': {
            'max_contacts_without_result': 10,
            'max_field_visits_failed': 2,
            'escalate_to': 'legal_pretrial'
        }
    }
    
    @classmethod
    def create_case(cls, client: Client, credits: List[Credit], 
                    operator: Optional[Operator] = None) -> CollectionCase:
        """
        Создание нового кейса взыскания
        
        Args:
            client: Клиент
            credits: Список кредитов для включения в кейс
            operator: Назначенный оператор (опционально)
        
        Returns:
            CollectionCase: Созданный кейс
        """
        with transaction.atomic():
            # Расчёт агрегированных показателей
            total_debt = Decimal('0')
            overdue_amount = Decimal('0')
            max_dpd = 0
            
            for credit in credits:
                # Получаем последнее состояние кредита
                latest_state = credit.states.order_by('-state_date').first()
                if latest_state:
                    total_debt += latest_state.principal_debt
                    overdue_amount += latest_state.overdue_principal + latest_state.overdue_interest
                    max_dpd = max(max_dpd, latest_state.overdue_days)
            
            # Определение начальной стадии
            stage = cls._determine_stage(max_dpd)
            
            # Расчёт приоритета
            priority, priority_score = cls._calculate_priority(
                overdue_amount, max_dpd, client
            )
            
            case = CollectionCase.objects.create(
                client=client,
                assigned_operator=operator,
                stage=stage,
                priority=priority,
                priority_score=priority_score,
                total_debt=total_debt,
                overdue_amount=overdue_amount,
                overdue_days=max_dpd,
                max_overdue_days=max_dpd,
                status='active'
            )
            
            case.credits.set(credits)
            
            # Создаём первую запись в истории
            CollectionStageHistory.objects.create(
                case=case,
                from_stage='',
                to_stage=stage,
                reason='Создание кейса',
                auto_transition=True
            )
            
            # Создаём первую задачу
            cls._create_initial_task(case)
            
            return case
    
    @classmethod
    def change_stage(cls, case: CollectionCase, new_stage: str, 
                     user=None, reason: str = '', auto: bool = False) -> bool:
        """
        Изменение стадии кейса с валидацией и логированием
        
        Args:
            case: Кейс взыскания
            new_stage: Новая стадия
            user: Пользователь, инициировавший переход
            reason: Причина перехода
            auto: Автоматический переход
            
        Returns:
            bool: Успешность операции
        """
        if case.stage == new_stage:
            return False
        
        # Валидация перехода
        if not cls._validate_stage_transition(case.stage, new_stage):
            return False
        
        old_stage = case.stage
        
        with transaction.atomic():
            case.stage = new_stage
            case.stage_changed_at = timezone.now()
            case.save(update_fields=['stage', 'stage_changed_at', 'updated_at'])
            
            # Логируем переход
            CollectionStageHistory.objects.create(
                case=case,
                from_stage=old_stage,
                to_stage=new_stage,
                changed_by=user,
                reason=reason,
                auto_transition=auto
            )
            
            # Выполняем действия при переходе
            cls._execute_stage_transition_actions(case, old_stage, new_stage)
            
            return True
    
    @classmethod
    def process_intervention_result(cls, intervention: Intervention) -> None:
        """
        Обработка результата воздействия (звонка, SMS и т.д.)
        
        Args:
            intervention: Воздействие
        """
        case = intervention.credit.collection_cases.filter(status='active').first()
        if not case:
            return
        
        with transaction.atomic():
            # Обновляем счётчики
            case.total_contacts += 1
            
            if intervention.status == 'completed':
                case.successful_contacts += 1
            
            if intervention.status == 'promise' and intervention.promise_amount > 0:
                # Создаём обещание
                Promise.objects.create(
                    case=case,
                    intervention=intervention,
                    promised_amount=intervention.promise_amount,
                    promised_date=intervention.promise_date or (date.today() + timedelta(days=7))
                )
                case.promises_count += 1
            
            case.save()
            
            # Проверяем правила эскалации
            cls._check_escalation_rules(case)
    
    @classmethod
    def check_promise_fulfillment(cls, promise: Promise) -> None:
        """
        Проверка выполнения обещания
        
        Args:
            promise: Обещание
        """
        from django.db.models import Sum
        
        case = promise.case
        credit = case.credits.first()
        
        if not credit:
            return
        
        # Ищем платежи за период
        payments = credit.payments.filter(
            payment_date__gte=promise.created_at.date(),
            payment_date__lte=promise.promised_date + timedelta(days=3)  # +3 дня grace period
        )
        
        total_paid = payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        with transaction.atomic():
            promise.actual_amount = total_paid
            promise.verified_at = timezone.now()
            
            if total_paid >= promise.promised_amount:
                promise.status = 'kept'
            elif total_paid > 0:
                promise.status = 'partial'
                promise.actual_date = payments.order_by('-payment_date').first().payment_date
            else:
                promise.status = 'broken'
                case.broken_promises += 1
                case.save(update_fields=['broken_promises'])
            
            promise.save()
            
            # Проверяем правила эскалации при нарушенном обещании
            if promise.status == 'broken':
                cls._check_escalation_rules(case)
    
    @classmethod
    def get_operator_workload(cls, operator: Operator) -> Dict:
        """
        Получение информации о нагрузке оператора
        
        Args:
            operator: Оператор
            
        Returns:
            Dict: Информация о нагрузке
        """
        today = date.today()
        
        active_cases = CollectionCase.objects.filter(
            assigned_operator=operator,
            status='active'
        )
        
        pending_tasks = CommunicationTask.objects.filter(
            operator=operator,
            status='pending',
            scheduled_date=today
        )
        
        return {
            'active_cases': active_cases.count(),
            'max_load': operator.max_load,
            'utilization': active_cases.count() / operator.max_load if operator.max_load > 0 else 0,
            'pending_tasks_today': pending_tasks.count(),
            'high_priority_cases': active_cases.filter(priority__gte=5).count(),
            'overdue_tasks': CommunicationTask.objects.filter(
                operator=operator,
                status='pending',
                scheduled_date__lt=today
            ).count()
        }
    
    @classmethod
    def auto_distribute_cases(cls, cases: Optional[List[CollectionCase]] = None) -> Dict[str, int]:
        """
        Автоматическое распределение кейсов по операторам
        
        Args:
            cases: Список кейсов для распределения (если None - все неназначенные)
            
        Returns:
            Dict: Статистика распределения
        """
        if cases is None:
            cases = CollectionCase.objects.filter(
                assigned_operator__isnull=True,
                status='active'
            )
        
        stats = {'distributed': 0, 'failed': 0}
        
        # Получаем доступных операторов
        operators = Operator.objects.filter(
            status='active'
        ).annotate(
            current_cases=Count('assigned_cases', filter=Q(assigned_cases__status='active'))
        ).filter(
            current_cases__lt=models.F('max_load')
        ).order_by('current_cases')
        
        for case in cases:
            operator = cls._find_best_operator(case, operators)
            if operator:
                case.assigned_operator = operator
                case.save(update_fields=['assigned_operator', 'updated_at'])
                stats['distributed'] += 1
            else:
                stats['failed'] += 1
        
        return stats
    
    # ==================== Приватные методы ====================
    
    @classmethod
    def _determine_stage(cls, dpd: int) -> str:
        """Определение стадии по DPD"""
        for stage, thresholds in cls.STAGE_THRESHOLDS.items():
            min_dpd = thresholds.get('min_dpd', float('-inf'))
            max_dpd = thresholds.get('max_dpd', float('inf'))
            
            if max_dpd is None:
                max_dpd = float('inf')
            
            if min_dpd <= dpd <= max_dpd:
                return stage
        
        return 'soft_early'
    
    @classmethod
    def _calculate_priority(cls, overdue_amount: Decimal, dpd: int, 
                           client: Client) -> Tuple[int, float]:
        """
        Расчёт приоритета кейса
        
        Returns:
            Tuple[int, float]: (priority_level, priority_score)
        """
        score = 0.0
        
        # Компонент суммы (0-30)
        amount_score = min(float(overdue_amount) / 10000, 30)
        score += amount_score
        
        # Компонент DPD (0-30)
        dpd_score = min(dpd / 3, 30)
        score += dpd_score
        
        # Компонент категории клиента (0-20)
        category_scores = {
            'vip': 20,
            'standard': 10,
            'new': 5,
            'problem': 15,
        }
        score += category_scores.get(client.category, 10)
        
        # Нормализация к уровню приоритета (1-6)
        if score >= 70:
            priority = 6
        elif score >= 55:
            priority = 5
        elif score >= 40:
            priority = 4
        elif score >= 25:
            priority = 3
        elif score >= 10:
            priority = 2
        else:
            priority = 1
        
        return priority, score
    
    @classmethod
    def _validate_stage_transition(cls, from_stage: str, to_stage: str) -> bool:
        """Валидация допустимости перехода между стадиями"""
        # Определяем допустимые переходы
        allowed_transitions = {
            'pre_collection': ['soft_early', 'settled'],
            'soft_early': ['soft_late', 'settled', 'restructured'],
            'soft_late': ['hard', 'settled', 'restructured'],
            'hard': ['legal_pretrial', 'settled', 'restructured', 'sold'],
            'legal_pretrial': ['legal_court', 'settled', 'restructured'],
            'legal_court': ['legal_execution', 'settled'],
            'legal_execution': ['settled', 'written_off'],
            'restructured': ['soft_early', 'settled'],
        }
        
        return to_stage in allowed_transitions.get(from_stage, [])
    
    @classmethod
    def _execute_stage_transition_actions(cls, case: CollectionCase, 
                                         from_stage: str, to_stage: str) -> None:
        """Выполнение действий при переходе между стадиями"""
        # Создание задач для новой стадии
        if to_stage == 'soft_early':
            cls._create_soft_collection_tasks(case)
        elif to_stage == 'hard':
            cls._create_hard_collection_tasks(case)
        elif to_stage == 'legal_pretrial':
            cls._create_legal_case(case)
    
    @classmethod
    def _create_initial_task(cls, case: CollectionCase) -> None:
        """Создание первой задачи для кейса"""
        task_type = 'call_first' if case.stage.startswith('soft') else 'sms_reminder'
        
        CommunicationTask.objects.create(
            case=case,
            operator=case.assigned_operator,
            task_type=task_type,
            priority=case.priority,
            scheduled_date=date.today(),
            status='pending'
        )
    
    @classmethod
    def _create_soft_collection_tasks(cls, case: CollectionCase) -> None:
        """Создание задач для Soft Collection"""
        today = date.today()
        
        # План коммуникаций на неделю
        tasks = [
            ('sms_reminder', 0),
            ('call_first', 1),
            ('email_reminder', 3),
            ('call_followup', 5),
            ('sms_demand', 7),
        ]
        
        for task_type, days_offset in tasks:
            CommunicationTask.objects.create(
                case=case,
                operator=case.assigned_operator,
                task_type=task_type,
                priority=case.priority,
                scheduled_date=today + timedelta(days=days_offset),
                status='pending'
            )
    
    @classmethod
    def _create_hard_collection_tasks(cls, case: CollectionCase) -> None:
        """Создание задач для Hard Collection"""
        today = date.today()
        
        # Планируем выездное мероприятие
        FieldVisit.objects.create(
            case=case,
            operator=case.assigned_operator,
            scheduled_date=today + timedelta(days=3),
            address=case.client.actual_address if hasattr(case.client, 'actual_address') else '',
            visit_type='residence',
            status='scheduled'
        )
        
        # И письмо-требование
        CommunicationTask.objects.create(
            case=case,
            operator=case.assigned_operator,
            task_type='letter_demand',
            priority=4,
            scheduled_date=today,
            status='pending'
        )
    
    @classmethod
    def _create_legal_case(cls, case: CollectionCase) -> None:
        """Создание судебного дела"""
        LegalCase.objects.create(
            collection_case=case,
            stage='pretrial_claim',
            claim_amount=case.total_debt
        )
    
    @classmethod
    def _check_escalation_rules(cls, case: CollectionCase) -> None:
        """Проверка правил эскалации"""
        rules = cls.ESCALATION_RULES.get(case.stage)
        if not rules:
            return
        
        should_escalate = False
        reason = ''
        
        # Проверка количества контактов без результата
        if 'max_contacts_without_result' in rules:
            unsuccessful = case.total_contacts - case.successful_contacts
            if unsuccessful >= rules['max_contacts_without_result']:
                should_escalate = True
                reason = f'Превышено количество безуспешных контактов ({unsuccessful})'
        
        # Проверка нарушенных обещаний
        if 'max_broken_promises' in rules:
            if case.broken_promises >= rules['max_broken_promises']:
                should_escalate = True
                reason = f'Превышено количество нарушенных обещаний ({case.broken_promises})'
        
        if should_escalate:
            cls.change_stage(
                case=case,
                new_stage=rules['escalate_to'],
                reason=reason,
                auto=True
            )
    
    @classmethod
    def _find_best_operator(cls, case: CollectionCase, 
                           operators) -> Optional[Operator]:
        """Поиск лучшего оператора для кейса"""
        # Фильтруем по специализации
        stage_to_spec = {
            'soft_early': ['soft', 'universal'],
            'soft_late': ['soft', 'universal'],
            'hard': ['hard', 'universal'],
            'legal_pretrial': ['legal'],
            'legal_court': ['legal'],
        }
        
        required_specs = stage_to_spec.get(case.stage, ['universal'])
        
        suitable_operators = [
            op for op in operators 
            if op.specialization in required_specs
        ]
        
        if not suitable_operators:
            suitable_operators = list(operators)
        
        if not suitable_operators:
            return None
        
        # Для высокоприоритетных кейсов - опытных операторов
        if case.priority >= 5:
            senior_ops = [
                op for op in suitable_operators 
                if op.role in ['senior_operator', 'team_lead', 'supervisor']
            ]
            if senior_ops:
                suitable_operators = senior_ops
        
        # Выбираем наименее загруженного
        return min(suitable_operators, key=lambda op: getattr(op, 'current_cases', 0))
