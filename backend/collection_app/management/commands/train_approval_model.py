"""
Django management command: обучение модели одобрения кредитных заявок.

Генерирует синтетические обучающие примеры на основе реальных данных
из таблиц Client, Credit, CreditApplication, Payment, затем обучает
GradientBoostingClassifier (см. application_approval.py).

Запуск:
    python manage.py train_approval_model
    python manage.py train_approval_model --samples 2000
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from collection_app.models import Client, Credit, CreditApplication
from collection_app.ml.application_approval import (
    CreditApprovalModel,
    _extract_features_from_application,
)


class Command(BaseCommand):
    help = 'Обучает модель прогнозирования одобрения кредитной заявки.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--samples', type=int, default=1500,
            help='Минимальное количество обучающих примеров (default: 1500)',
        )

    def handle(self, *args, **options):
        min_samples = options['samples']
        self.stdout.write('=== Обучение модели одобрения кредита ===')

        # ----- Шаг 1: собираем реальные заявки (если есть) -----
        applications = []
        labels = []

        real_apps = CreditApplication.objects.all()
        for app in real_apps:
            if app.decision in ('approved', 'rejected'):
                applications.append(app)
                labels.append(1 if app.decision == 'approved' else 0)

        self.stdout.write(f'  Реальных заявок с решением: {len(applications)}')

        # ----- Шаг 2: генерируем синтетические заявки из Client+Credit -----
        clients = list(
            Client.objects.prefetch_related('credits').all()[:3000]
        )

        if not clients:
            self.stdout.write(self.style.ERROR(
                'В БД нет клиентов — невозможно сгенерировать данные.'
            ))
            return

        random.shuffle(clients)

        synthetic_count = max(0, min_samples - len(applications))
        generated = 0

        for client in clients:
            if generated >= synthetic_count:
                break

            credits_qs = client.credits.all()
            has_overdue = credits_qs.filter(
                status__in=['overdue', 'default']
            ).exists()
            active_credits = credits_qs.filter(
                status__in=['active', 'overdue', 'restructured']
            ).count()

            income = float(client.income) if client.income else random.uniform(20000, 200000)
            # Расходы могут превышать доход — это важно для обучения
            expense_ratio = random.choice([
                random.uniform(0.2, 0.5),   # нормальные (60%)
                random.uniform(0.2, 0.5),
                random.uniform(0.2, 0.5),
                random.uniform(0.5, 0.8),   # высокие (20%)
                random.uniform(0.8, 1.5),   # превышают доход (20%)
            ])
            expenses = float(client.monthly_expenses) if client.monthly_expenses else income * expense_ratio

            # Генерируем «заявку» как словарь
            amount = random.choice([
                random.uniform(50000, 300000),
                random.uniform(300000, 1000000),
                random.uniform(1000000, 5000000),
            ])
            term = random.choice([6, 12, 24, 36, 48, 60])
            monthly_pay = amount / term

            education_choices = ['secondary', 'vocational', 'incomplete_higher',
                                 'higher', 'multiple_higher', 'academic']
            empl_choices = ['employed', 'self_employed', 'business_owner',
                            'freelance', 'retired', 'unemployed',
                            'military', 'civil_servant', 'student']
            marital_choices = ['single', 'married', 'divorced', 'widowed', 'civil_marriage']
            property_choices = ['own', 'mortgage', 'rent', 'parents', 'employer']
            confirm_choices = ['2ndfl', 'bank_form', 'tax_declaration',
                               'bank_statement', 'none']

            empl = client.employment if client.employment else random.choice(empl_choices)

            work_total = random.randint(0, 360)
            work_current = random.randint(0, min(work_total, 120))
            bd = client.birth_date if client.birth_date else (
                date.today() - timedelta(days=random.randint(20*365, 65*365))
            )

            app_data = {
                'birth_date': bd,
                'gender': client.gender or random.choice(['M', 'F']),
                'marital_status': client.marital_status or random.choice(marital_choices),
                'education': random.choice(education_choices),
                'employment_type': empl,
                'work_experience_total': work_total,
                'work_experience_current': work_current,
                'income_main': income * 0.85,
                'income_additional': income * 0.15,
                'income_rental': 0,
                'income_pension': 0,
                'income_other': 0,
                'expense_rent': expenses * 0.3,
                'expense_utilities': expenses * 0.15,
                'expense_food': expenses * 0.3,
                'expense_transport': expenses * 0.1,
                'expense_other': expenses * 0.15,
                'current_loans_total_payment': float(sum(
                    c.monthly_payment for c in credits_qs if c.status in ('active', 'overdue')
                )),
                'amount': amount,
                'requested_term': term,
                'has_collateral': random.random() < 0.25,
                'has_guarantor': random.random() < 0.15,
                'has_overdue_history': has_overdue,
                'max_overdue_days': random.choice([0, 0, 0, 5, 15, 30, 60, 90]) if has_overdue else 0,
                'has_real_estate': random.random() < 0.4,
                'has_car': random.random() < 0.35,
                'has_deposits': random.random() < 0.2,
                'dependents_count': client.children_count,
                'current_loans_count': active_credits,
                'income_confirmation': random.choice(confirm_choices),
                'property_ownership': random.choice(property_choices),
            }

            # ----- Определяем целевую метку (реалистично) -----
            dti = (monthly_pay + expenses) / income if income > 0 else 99.0
            approval_score = 0.0

            # === Жёсткие правила — автоматический отказ ===
            # Расходы превышают доход
            if expenses >= income:
                approval_score -= 5.0
            # Нулевой доход
            if income <= 0:
                approval_score -= 5.0
            # Ежемесячный платёж > 80% дохода
            if income > 0 and monthly_pay > income * 0.8:
                approval_score -= 4.0

            # Хорошая кредитная история +2
            if not has_overdue:
                approval_score += 2.0
            else:
                approval_score -= 1.5

            # DTI — более жёсткая градация
            if dti < 0.3:
                approval_score += 1.5
            elif dti < 0.5:
                approval_score += 0.5
            elif dti < 0.7:
                approval_score -= 0.5
            elif dti < 1.0:
                approval_score -= 2.0
            else:
                approval_score -= 3.5  # DTI > 100%

            # Занятость
            if empl in ('employed', 'military', 'civil_servant'):
                approval_score += 1.0
            elif empl == 'self_employed':
                approval_score += 0.5
            elif empl in ('unemployed', 'student'):
                approval_score -= 2.0
            elif empl == 'retired':
                approval_score -= 0.3

            # Стаж
            if work_current >= 12:
                approval_score += 0.5

            # Залог
            if app_data['has_collateral']:
                approval_score += 0.5

            # Активные кредиты
            if active_credits >= 3:
                approval_score -= 0.5

            # Недвижимость / вклады
            if app_data['has_real_estate']:
                approval_score += 0.3
            if app_data['has_deposits']:
                approval_score += 0.3

            # Шум
            approval_score += random.gauss(0, 0.6)

            label = 1 if approval_score > 0.5 else 0

            applications.append(app_data)
            labels.append(label)
            generated += 1

        self.stdout.write(f'  Сгенерировано синтетических: {generated}')
        self.stdout.write(f'  Всего обучающих примеров:    {len(applications)}')
        self.stdout.write(
            f'  Одобрено / Отказано: '
            f'{sum(labels)} / {len(labels) - sum(labels)}'
        )

        # ----- Шаг 3: обучаем модель -----
        model = CreditApprovalModel()
        metrics = model.train(applications, labels)

        self.stdout.write(self.style.SUCCESS('\n=== Результаты обучения ==='))
        self.stdout.write(f"  Accuracy:  {metrics['accuracy']:.4f}")
        self.stdout.write(f"  ROC AUC:   {metrics['roc_auc']:.4f}")
        self.stdout.write(f"  CV mean:   {metrics['cv_mean']:.4f} ± {metrics['cv_std']:.4f}")
        self.stdout.write(f"  Train/Test: {metrics['train_size']}/{metrics['test_size']}")

        report = metrics.get('classification_report', {})
        for cls_name in ('Отказ', 'Одобрено'):
            if cls_name in report:
                r = report[cls_name]
                self.stdout.write(
                    f"  {cls_name}: precision={r['precision']:.3f}  "
                    f"recall={r['recall']:.3f}  f1={r['f1-score']:.3f}"
                )

        # Top-5 важных признаков
        fi = metrics.get('feature_importances', {})
        if fi:
            top = sorted(fi.items(), key=lambda x: x[1], reverse=True)[:5]
            self.stdout.write('\n  Top-5 признаков:')
            for name, imp in top:
                self.stdout.write(f'    {name:30s} {imp:.4f}')

        # Сохраняем метрики в JSON для API
        import json as _json
        from pathlib import Path as _Path
        meta_dir = _Path(__file__).resolve().parent.parent.parent / 'ml' / 'saved_models'
        meta_dir.mkdir(parents=True, exist_ok=True)
        with open(meta_dir / 'approval_train_meta.json', 'w') as _f:
            _json.dump(metrics, _f, default=str)

        self.stdout.write(self.style.SUCCESS('\nМодель сохранена.'))
