"""
Заполняет пропущенные месяцы в истории CreditState.

Для каждого кредита строит непрерывную ежемесячную историю
от даты открытия до текущей даты (или даты закрытия).
Также создаёт недостающие платежи (Payment).

Запуск:
    py manage.py fill_credit_states
    py manage.py fill_credit_states --dry-run     # только показать что будет сделано
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from collection_app.models import Credit, CreditState, Payment


class Command(BaseCommand):
    help = 'Заполняет пропуски в ежемесячной истории CreditState и Payment'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Только показать статистику, не менять БД')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = date(2026, 3, 4)

        total_states_created = 0
        total_payments_created = 0
        credits_fixed = 0

        credits = Credit.objects.all().order_by('id')
        self.stdout.write(f'Всего кредитов: {credits.count()}')

        for credit in credits:
            existing_states = list(
                CreditState.objects.filter(credit=credit)
                .order_by('state_date')
                .values('state_date', 'principal_debt', 'overdue_principal',
                         'interest', 'overdue_interest', 'penalties', 'overdue_days')
            )
            existing_payments = list(
                Payment.objects.filter(credit=credit)
                .order_by('payment_date')
                .values('payment_date', 'amount')
            )

            existing_dates = {s['state_date'] for s in existing_states}
            existing_pay_dates = {p['payment_date'] for p in existing_payments}

            # Определяем конечную дату
            if credit.status == 'closed':
                # Для закрытых — до последнего существующего состояния или planned_close_date
                if existing_states:
                    end_date = existing_states[-1]['state_date']
                elif credit.planned_close_date:
                    end_date = credit.planned_close_date
                else:
                    end_date = today
            else:
                # Для активных/просроченных — до текущего месяца
                end_date = today

            # Определяем день месяца (берём из open_date)
            day_of_month = credit.open_date.day

            # Строим полный набор ожидаемых дат
            expected_dates = []
            cur = credit.open_date
            while cur <= end_date:
                expected_dates.append(cur)
                # Следующий месяц
                month = cur.month + 1
                year = cur.year
                if month > 12:
                    month = 1
                    year += 1
                try:
                    cur = date(year, month, day_of_month)
                except ValueError:
                    # Для дней 29-31 в коротких месяцах
                    cur = date(year, month, min(day_of_month, 28))

            missing_dates = [d for d in expected_dates if d not in existing_dates]

            if not missing_dates:
                continue

            credits_fixed += 1

            if dry_run:
                if credits_fixed <= 10:
                    self.stdout.write(
                        f'  Credit #{credit.id} ({credit.status}): '
                        f'{len(existing_states)} states, need +{len(missing_dates)} '
                        f'(open={credit.open_date}, end={end_date})'
                    )
                continue

            # Берём последнее известное состояние для интерполяции
            last_known = existing_states[-1] if existing_states else None
            initial_amount = float(credit.principal_amount)
            monthly = float(credit.monthly_payment)
            rate_monthly = float(credit.interest_rate) / 100 / 12
            is_overdue = credit.status in ['overdue', 'default']

            # Строим карту: дата -> principal_debt для существующих
            debt_map = {s['state_date']: float(s['principal_debt']) for s in existing_states}

            for d in missing_dates:
                # Рассчитываем долг: интерполяция между известными точками
                months_from_open = (d.year - credit.open_date.year) * 12 + \
                                   (d.month - credit.open_date.month)

                # Простая аннуитетная модель: остаток = amount - (monthly * principal_share * months)
                principal_share = monthly - initial_amount * rate_monthly
                if principal_share <= 0:
                    principal_share = monthly * 0.7

                remaining = max(0, initial_amount - principal_share * months_from_open)

                # Если кредит закрыт и эта дата >= last state — долг 0
                if credit.status == 'closed' and last_known and d >= last_known['state_date']:
                    remaining = 0

                # Для просроченных — добавляем случайные суммы просрочки
                overdue_principal = Decimal(0)
                overdue_interest = Decimal(0)
                penalties = Decimal(0)
                overdue_days = 0

                if is_overdue and remaining > 0:
                    if random.random() < 0.6:  # 60% месяцев с просрочкой
                        overdue_principal = Decimal(remaining * random.uniform(0.05, 0.25)).quantize(Decimal('0.01'))
                        overdue_interest = Decimal(remaining * rate_monthly * random.uniform(0.5, 1.5)).quantize(Decimal('0.01'))
                        overdue_days = random.randint(5, 90)
                        if random.random() < 0.3:
                            penalties = Decimal(float(overdue_principal) * random.uniform(0.01, 0.05)).quantize(Decimal('0.01'))

                interest = Decimal(remaining * rate_monthly).quantize(Decimal('0.01'))

                # planned_payment_date = следующий месяц
                pp_month = d.month + 1
                pp_year = d.year
                if pp_month > 12:
                    pp_month = 1
                    pp_year += 1
                try:
                    planned_pay = date(pp_year, pp_month, day_of_month)
                except ValueError:
                    planned_pay = date(pp_year, pp_month, min(day_of_month, 28))

                CreditState.objects.create(
                    credit=credit,
                    client=credit.client,
                    state_date=d,
                    planned_payment_date=planned_pay,
                    principal_debt=Decimal(remaining).quantize(Decimal('0.01')),
                    overdue_principal=overdue_principal,
                    interest=interest,
                    overdue_interest=overdue_interest,
                    penalties=penalties,
                    overdue_days=overdue_days,
                )
                total_states_created += 1

                # Создаём платёж если его нет за этот месяц (и долг > 0)
                if remaining > 0 and d not in existing_pay_dates:
                    # Определяем, был ли платёж
                    if credit.status == 'closed' or random.random() < 0.85:
                        pay_overdue_days = 0
                        if random.random() < 0.25:
                            pay_overdue_days = random.randint(1, 30)
                        pay_date = d + timedelta(days=pay_overdue_days)

                        # Сумма платежа ~= ежемесячный ± 5%
                        pay_amount = monthly * random.uniform(0.95, 1.05)

                        Payment.objects.create(
                            credit=credit,
                            payment_date=pay_date,
                            amount=Decimal(pay_amount).quantize(Decimal('0.01')),
                            payment_type='regular',
                            planned_date=d,
                            min_payment=credit.monthly_payment * Decimal('0.1'),
                            overdue_days=pay_overdue_days,
                        )
                        total_payments_created += 1
                        existing_pay_dates.add(pay_date)

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'\n[DRY RUN] Кредитов с пропусками: {credits_fixed}'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\nГотово:'
                f'\n  Кредитов исправлено: {credits_fixed}'
                f'\n  Состояний создано:   {total_states_created}'
                f'\n  Платежей создано:    {total_payments_created}'
            ))
