"""
Django management command: обучение модели прогнозирования просрочки.

Собирает обучающие данные из реальных таблиц Client → Credit → Payment → Intervention,
вычисляет 26 признаков и целевую переменную risk_category ∈ {0, 1, 2},
затем обучает RandomForestClassifier (см. overdue_predictor.py).

Запуск:
    python manage.py train_overdue_model
    python manage.py train_overdue_model --use-db-training-data
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum, Avg, Max, Q
from django.utils import timezone

from collection_app.models import (
    Client, Credit, Payment, Intervention, TrainingData,
)
from collection_app.ml.overdue_predictor import OverdueRiskModel, FEATURE_COLUMNS


class Command(BaseCommand):
    help = 'Обучает модель прогнозирования просрочки с ранжированием по рискам.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--use-db-training-data', action='store_true',
            help='Использовать записи TrainingData из БД вместо генерации из Credit/Payment',
        )

    def handle(self, *args, **options):
        self.stdout.write('=== Обучение модели прогнозирования просрочки ===')

        if options['use_db_training_data']:
            records = self._load_from_training_data()
        else:
            records = self._generate_from_credits()

        if not records:
            self.stdout.write(self.style.ERROR('Нет данных для обучения.'))
            return

        self.stdout.write(f'  Всего записей: {len(records)}')

        # Статистика по классам
        class_counts = {}
        for r in records:
            c = r['risk_category']
            class_counts[c] = class_counts.get(c, 0) + 1
        for k in sorted(class_counts):
            label = {0: 'Низкий', 1: 'Средний', 2: 'Высокий'}.get(k, str(k))
            self.stdout.write(f'  Класс {k} ({label}): {class_counts[k]}')

        # ----- Обучение -----
        model = OverdueRiskModel()
        metrics = model.train(records)

        self.stdout.write(self.style.SUCCESS('\n=== Результаты обучения ==='))
        self.stdout.write(f"  Accuracy:  {metrics['accuracy']:.4f}")
        self.stdout.write(f"  CV mean:   {metrics['cv_mean']:.4f} ± {metrics['cv_std']:.4f}")
        self.stdout.write(f"  Train/Test: {metrics['train_size']}/{metrics['test_size']}")

        report = metrics.get('classification_report', {})
        for cls_name in ('Низкий', 'Средний', 'Высокий'):
            if cls_name in report:
                r = report[cls_name]
                self.stdout.write(
                    f"  {cls_name:10s}: precision={r['precision']:.3f}  "
                    f"recall={r['recall']:.3f}  f1={r['f1-score']:.3f}"
                )

        # Top-5 признаков
        fi = metrics.get('feature_importances', {})
        if fi:
            top = sorted(fi.items(), key=lambda x: x[1], reverse=True)[:7]
            self.stdout.write('\n  Top-7 признаков:')
            for name, imp in top:
                self.stdout.write(f'    {name:30s} {imp:.4f}')

        self.stdout.write(self.style.SUCCESS('\nМодель сохранена.'))

        # Save metrics to JSON for API access
        import json
        from pathlib import Path
        meta_path = Path(__file__).resolve().parent.parent.parent / 'ml' / 'saved_models' / 'overdue_train_meta.json'
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_path, 'w') as f:
            json.dump(metrics, f, ensure_ascii=False, default=str)

    # ================================================================
    # Вариант 1: из таблицы TrainingData (если --use-db-training-data)
    # ================================================================
    def _load_from_training_data(self):
        qs = TrainingData.objects.all()
        self.stdout.write(f'  Записей TrainingData в БД: {qs.count()}')
        records = []
        for td in qs:
            records.append({
                'client_id': td.client_id,
                'credit_id': td.credit_id,
                'age': td.age,
                'gender': td.gender,
                'marital_status': td.marital_status,
                'employment': td.employment,
                'dependents': td.dependents,
                'monthly_income': td.monthly_income,
                'has_other_credits': td.has_other_credits,
                'other_credits_count': td.other_credits_count,
                'credit_amount': td.credit_amount,
                'credit_term': td.credit_term,
                'interest_rate': td.interest_rate,
                'lti_ratio': td.lti_ratio,
                'credit_age': td.credit_age,
                'credit_status': td.credit_status,
                'monthly_payment': td.monthly_payment,
                'total_payments': td.total_payments,
                'overdue_payments': td.overdue_payments,
                'max_overdue_days': td.max_overdue_days,
                'avg_payment': td.avg_payment,
                'payments_count_12m': td.payments_count_12m,
                'overdue_count_12m': td.overdue_count_12m,
                'overdue_share_12m': td.overdue_share_12m,
                'max_overdue_12m': td.max_overdue_12m,
                'total_interventions': td.total_interventions,
                'completed_interventions': td.completed_interventions,
                'promises_count': td.promises_count,
                'risk_category': td.risk_category,
            })
        return records

    # ================================================================
    # Вариант 2: генерация на лету из Credit → Payment → Intervention
    # ================================================================
    def _generate_from_credits(self):
        credits = Credit.objects.select_related('client').prefetch_related(
            'payments', 'interventions'
        ).all()

        self.stdout.write(f'  Кредитов в БД: {credits.count()}')

        records = []
        today = date.today()
        year_ago = today - timedelta(days=365)

        for credit in credits:
            client = credit.client
            payments = credit.payments.all()
            interventions = credit.interventions.all()

            # === Клиентские признаки ===
            if client.birth_date:
                age = (today - client.birth_date).days / 365.25
            else:
                age = 35

            gender = 1 if client.gender == 'M' else 0

            marital_map = {'single': 0, 'married': 1, 'divorced': 2, 'widowed': 3}
            marital = marital_map.get(client.marital_status, 0)

            empl_map = {
                'employed': 1, 'self_employed': 2, 'unemployed': 0,
                'retired': 3, 'student': 4,
            }
            employment = empl_map.get(client.employment, 1)

            dependents = client.children_count or 0
            monthly_income = float(client.income) if client.income else 0

            other_count = Credit.objects.filter(client=client).exclude(id=credit.id).count()
            has_other = 1 if other_count > 0 else 0

            # === Кредитные признаки ===
            credit_amount = float(credit.principal_amount) if credit.principal_amount else 0
            credit_term_days = (
                (credit.planned_close_date - credit.open_date).days
                if credit.planned_close_date and credit.open_date
                else 365
            )
            credit_term = max(credit_term_days // 30, 1)

            interest_rate = float(credit.interest_rate) if credit.interest_rate else 0
            monthly_pay = float(credit.monthly_payment) if credit.monthly_payment else 0
            lti_ratio = (credit_amount / (monthly_income * 12)) if monthly_income > 0 else 0
            credit_age = (today - credit.open_date).days if credit.open_date else 0

            status_map = {
                'active': 1, 'closed': 0, 'overdue': 2, 'default': 3,
                'restructured': 4, 'legal': 5, 'sold': 6, 'written_off': 7,
            }
            credit_status = status_map.get(credit.status, 1)

            # === Платёжная дисциплина ===
            total_payments = payments.count()
            overdue_payments = payments.filter(overdue_days__gt=0).count()
            max_od = payments.aggregate(m=Max('overdue_days'))['m'] or 0
            avg_pay = payments.aggregate(a=Avg('amount'))['a'] or 0

            payments_12m = payments.filter(payment_date__gte=year_ago)
            p12_count = payments_12m.count()
            od12_count = payments_12m.filter(overdue_days__gt=0).count()
            od12_share = od12_count / p12_count if p12_count > 0 else 0
            max_od_12m = payments_12m.aggregate(m=Max('overdue_days'))['m'] or 0

            # === Взаимодействие ===
            total_iv = interventions.count()
            completed_iv = interventions.filter(status='completed').count()
            promises = interventions.filter(status='promise').count()

            # === Целевая переменная ===
            if total_payments > 0:
                overdue_ratio = overdue_payments / total_payments
            else:
                overdue_ratio = 0

            # Определение risk_category:
            #   0 — низкий: overdue_ratio < 0.2 И макс. просрочка < 15 дн.
            #   1 — средний: 0.2 ≤ overdue_ratio < 0.5 ИЛИ макс. просрочка 15-60
            #   2 — высокий: overdue_ratio ≥ 0.5 ИЛИ макс. просрочка > 60
            #   + учёт статуса кредита
            if credit.status in ('default', 'legal', 'sold', 'written_off'):
                risk_category = 2
            elif credit.status == 'overdue' and max_od > 60:
                risk_category = 2
            elif overdue_ratio >= 0.5 or max_od > 60:
                risk_category = 2
            elif overdue_ratio >= 0.2 or max_od > 15:
                risk_category = 1
            else:
                risk_category = 0

            records.append({
                'client_id': client.id,
                'credit_id': credit.id,
                'age': age,
                'gender': gender,
                'marital_status': marital,
                'employment': employment,
                'dependents': dependents,
                'monthly_income': monthly_income,
                'has_other_credits': has_other,
                'other_credits_count': other_count,
                'credit_amount': credit_amount,
                'credit_term': credit_term,
                'interest_rate': interest_rate,
                'lti_ratio': lti_ratio,
                'credit_age': credit_age,
                'credit_status': credit_status,
                'monthly_payment': monthly_pay,
                'total_payments': total_payments,
                'overdue_payments': overdue_payments,
                'max_overdue_days': max_od,
                'avg_payment': float(avg_pay),
                'payments_count_12m': p12_count,
                'overdue_count_12m': od12_count,
                'overdue_share_12m': od12_share,
                'max_overdue_12m': max_od_12m,
                'total_interventions': total_iv,
                'completed_interventions': completed_iv,
                'promises_count': promises,
                'risk_category': risk_category,
            })

        return records
