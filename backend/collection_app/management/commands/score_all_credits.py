"""
Массовое скоринг-прогнозирование выхода на просрочку.

Перебирает все активные/просроченные кредиты, вычисляет ML-прогноз
и сохраняет результат в ScoringResult. Предназначена для периодического
запуска (cron / Task Scheduler) для поддержания актуальности скорингов.

Примеры:
  py manage.py score_all_credits
  py manage.py score_all_credits --status active overdue
  py manage.py score_all_credits --dry-run
  py manage.py score_all_credits --limit 100
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from collection_app.models import Credit, Client, ScoringResult, AuditLog
from collection_app.ml.overdue_predictor import get_model, RISK_LABELS


# Маппинг ML risk_category (0,1,2) → ScoringResult.risk_segment
CATEGORY_TO_SEGMENT = {
    0: 'low',
    1: 'medium',
    2: 'high',
}

# Грейд по risk_score
def _score_to_grade(risk_score: float) -> str:
    if risk_score < 0.15:
        return 'A'
    if risk_score < 0.35:
        return 'B'
    if risk_score < 0.55:
        return 'C'
    if risk_score < 0.75:
        return 'D'
    return 'E'

# Скоринговый балл 300-850: чем ниже risk_score → тем выше балл
def _score_to_value(risk_score: float) -> int:
    return max(300, min(850, int(850 - risk_score * 550)))


class Command(BaseCommand):
    help = 'Массовый ML-скоринг всех активных/просроченных кредитов с сохранением в ScoringResult'

    def add_arguments(self, parser):
        parser.add_argument(
            '--status', nargs='+', default=['active', 'overdue', 'restructured'],
            help='Статусы кредитов для скоринга (default: active overdue restructured)'
        )
        parser.add_argument(
            '--limit', type=int, default=0,
            help='Макс. количество кредитов (0 = все)'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Только прогноз без сохранения в БД'
        )
        parser.add_argument(
            '--force', action='store_true',
            help='Пересчитать даже если уже есть скоринг за сегодня'
        )

    def handle(self, *args, **options):
        statuses = options['status']
        limit = options['limit']
        dry_run = options['dry_run']
        force = options['force']
        today = date.today()

        self.stdout.write(self.style.WARNING(
            f'=== Массовый ML-скоринг от {today} ===\n'
            f'Статусы: {statuses}, limit={limit or "все"}, '
            f'dry_run={dry_run}, force={force}'
        ))

        credits_qs = Credit.objects.filter(
            status__in=statuses,
        ).select_related('client')

        if not force:
            # Исключаем те, у которых уже есть скоринг за сегодня
            already_scored = ScoringResult.objects.filter(
                calculation_date=today,
                model_version='overdue_rf_v1',
            ).values_list('credit_id', flat=True)
            credits_qs = credits_qs.exclude(id__in=already_scored)

        if limit:
            credits_qs = credits_qs[:limit]

        credits_list = list(credits_qs)
        total = len(credits_list)
        self.stdout.write(f'Кредитов для скоринга: {total}')

        if total == 0:
            self.stdout.write(self.style.SUCCESS('Нечего скорить — все актуальны.'))
            return

        created_count = 0
        updated_count = 0
        error_count = 0
        stats = {0: 0, 1: 0, 2: 0}

        # Build features for ALL credits in one pass
        self.stdout.write('  Извлечение признаков...')
        feature_records = []
        credits_map = {}
        for credit in credits_list:
            try:
                features = self._build_features(credit)
                features['credit_id'] = credit.id
                features['client_id'] = credit.client_id
                feature_records.append(features)
                credits_map[credit.id] = credit
            except Exception as e:
                error_count += 1
                self.stderr.write(f'  ОШИБКА features credit={credit.id}: {e}')

        self.stdout.write(f'  Признаки готовы: {len(feature_records)}. Запуск ML-модели...')

        # Use batch prediction (much faster — single model call)
        model = get_model()
        results = model.predict_batch(feature_records)
        self.stdout.write(f'  ML-прогноз готов: {len(results)} записей.')

        for i, result in enumerate(results, 1):
            try:
                credit_id = result.get('credit_id')
                credit = credits_map.get(credit_id)
                if not credit:
                    continue

                risk_cat = result.get('risk_category', 1)
                risk_score = result.get('risk_score', 0.5)
                probs = result.get('probabilities', {})

                segment = CATEGORY_TO_SEGMENT.get(risk_cat, 'medium')
                grade = _score_to_grade(risk_score)
                score_value = _score_to_value(risk_score)
                probability = probs.get('high', probs.get('Высокий', risk_score))

                # Экономическая модель
                debt = float(credit.principal_amount or 0)
                expected_recovery = Decimal(str(round(debt * (1 - risk_score) * 0.7, 2)))
                cost_per_contact = Decimal('150.00')
                expected_profit = expected_recovery - cost_per_contact

                stats[risk_cat] = stats.get(risk_cat, 0) + 1

                if not dry_run:
                    # Find existing scoring for today or create new
                    existing = ScoringResult.objects.filter(
                        credit=credit,
                        calculation_date=today,
                        model_version='overdue_rf_v1',
                    ).first()

                    if existing:
                        existing.probability = probability
                        existing.risk_segment = segment
                        existing.score_value = score_value
                        existing.model_type = 'RandomForest'
                        existing.grade = grade
                        existing.expected_recovery = expected_recovery
                        existing.cost_per_contact = cost_per_contact
                        existing.expected_profit = expected_profit
                        existing.save()
                        updated_count += 1
                    else:
                        ScoringResult.objects.create(
                            credit=credit,
                            client=credit.client,
                            calculation_date=today,
                            model_version='overdue_rf_v1',
                            probability=probability,
                            risk_segment=segment,
                            score_value=score_value,
                            model_type='RandomForest',
                            grade=grade,
                            expected_recovery=expected_recovery,
                            cost_per_contact=cost_per_contact,
                            expected_profit=expected_profit,
                        )
                        created_count += 1

                    # Обновляем risk_segment на кредите, если есть поле
                    if hasattr(credit, 'risk_segment') and credit.risk_segment != segment:
                        credit.risk_segment = segment
                        credit.save(update_fields=['risk_segment'])

                if i % 50 == 0 or i == len(results):
                    self.stdout.write(f'  [{i}/{len(results)}] credit={credit_id} → '
                                      f'{RISK_LABELS.get(risk_cat, "?")} '
                                      f'(score={risk_score:.3f}, grade={grade})')

            except Exception as e:
                error_count += 1
                self.stderr.write(f'  ОШИБКА scoring: {e}')

        # Audit log
        if not dry_run:
            AuditLog.objects.create(
                action='batch_scoring',
                severity='info',
                details={
                    'date': str(today),
                    'total': total,
                    'created': created_count,
                    'updated': updated_count,
                    'errors': error_count,
                    'distribution': {RISK_LABELS.get(k, '?'): v for k, v in stats.items()},
                },
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'=== ИТОГО ==='))
        self.stdout.write(f'  Обработано: {total}')
        if not dry_run:
            self.stdout.write(f'  Создано:    {created_count}')
            self.stdout.write(f'  Обновлено:  {updated_count}')
        self.stdout.write(f'  Ошибок:     {error_count}')
        self.stdout.write(f'  🟢 Низкий:   {stats.get(0, 0)}')
        self.stdout.write(f'  🟡 Средний:  {stats.get(1, 0)}')
        self.stdout.write(f'  🔴 Высокий:  {stats.get(2, 0)}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n  [DRY-RUN] Ничего не сохранено в БД.'))

    @staticmethod
    def _build_features(credit):
        """
        Формирование вектора признаков для ML-модели.
        Идентично OverduePredictionView._build_features()
        """
        from datetime import timedelta
        from django.db.models import Avg, Max

        client = credit.client
        today = date.today()
        year_ago = today - timedelta(days=365)

        payments = credit.payments.all()
        interventions = credit.interventions.all()

        age = (today - client.birth_date).days / 365.25 if client.birth_date else 35
        gender = 1 if client.gender == 'M' else 0
        marital_map = {'single': 0, 'married': 1, 'divorced': 2, 'widowed': 3}
        empl_map = {'employed': 1, 'self_employed': 2, 'unemployed': 0, 'retired': 3, 'student': 4}

        monthly_income = float(client.income) if client.income else 0
        other_count = Credit.objects.filter(client=client).exclude(id=credit.id).count()

        credit_amount = float(credit.principal_amount) if credit.principal_amount else 0
        td = (credit.planned_close_date - credit.open_date).days if credit.planned_close_date and credit.open_date else 365
        credit_term = max(td // 30, 1)
        interest_rate = float(credit.interest_rate) if credit.interest_rate else 0
        monthly_pay = float(credit.monthly_payment) if credit.monthly_payment else 0
        lti = (credit_amount / (monthly_income * 12)) if monthly_income > 0 else 0
        credit_age = (today - credit.open_date).days if credit.open_date else 0
        status_map = {'active': 1, 'closed': 0, 'overdue': 2, 'default': 3, 'restructured': 4, 'legal': 5, 'sold': 6, 'written_off': 7}

        total_p = payments.count()
        overdue_p = payments.filter(overdue_days__gt=0).count()
        max_od = payments.aggregate(m=Max('overdue_days'))['m'] or 0
        avg_pay = payments.aggregate(a=Avg('amount'))['a'] or 0
        p12 = payments.filter(payment_date__gte=year_ago)
        p12_cnt = p12.count()
        od12_cnt = p12.filter(overdue_days__gt=0).count()
        od12_share = od12_cnt / p12_cnt if p12_cnt > 0 else 0
        max_od_12 = p12.aggregate(m=Max('overdue_days'))['m'] or 0

        total_iv = interventions.count()
        compl_iv = interventions.filter(status='completed').count()
        promises = interventions.filter(status='promise').count()

        return {
            'age': age,
            'gender': gender,
            'marital_status': marital_map.get(client.marital_status, 0),
            'employment': empl_map.get(client.employment, 1),
            'dependents': client.children_count or 0,
            'monthly_income': monthly_income,
            'has_other_credits': 1 if other_count > 0 else 0,
            'other_credits_count': other_count,
            'credit_amount': credit_amount,
            'credit_term': credit_term,
            'interest_rate': interest_rate,
            'lti_ratio': lti,
            'credit_age': credit_age,
            'credit_status': status_map.get(credit.status, 1),
            'monthly_payment': monthly_pay,
            'total_payments': total_p,
            'overdue_payments': overdue_p,
            'max_overdue_days': max_od,
            'avg_payment': float(avg_pay),
            'payments_count_12m': p12_cnt,
            'overdue_count_12m': od12_cnt,
            'overdue_share_12m': od12_share,
            'max_overdue_12m': max_od_12,
            'total_interventions': total_iv,
            'completed_interventions': compl_iv,
            'promises_count': promises,
        }
