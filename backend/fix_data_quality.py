"""
Comprehensive data quality fix:
1. Set realistic interest rates by product type
2. Recalculate monthly payments (annuity formula)
3. Rebuild CreditState records with proper monthly progression
4. Rebuild Payments to match credit lifecycle
"""
import os, sys, django, random, math
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'collection.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from collection_app.models import Credit, CreditState, Payment

random.seed(42)

# ==========================================
# 1. Interest rates by product type
# ==========================================
RATE_RANGES = {
    'consumer':    (12.9, 24.9),
    'mortgage':    (7.5, 14.5),
    'car':         (9.9, 19.9),
    'credit_card': (22.0, 36.0),
    'microloan':   (30.0, 90.0),
}

def annuity_payment(principal, annual_rate, months):
    """Calculate annuity monthly payment."""
    if annual_rate == 0 or months == 0:
        return float(principal) / max(months, 1)
    r = float(annual_rate) / 100 / 12
    pmt = float(principal) * r * (1 + r) ** months / ((1 + r) ** months - 1)
    return pmt

def fix_credits():
    credits = Credit.objects.all()
    updated = 0
    for cr in credits:
        lo, hi = RATE_RANGES.get(cr.product_type, (12.9, 24.9))
        rate = round(random.uniform(lo, hi), 2)
        cr.interest_rate = Decimal(str(rate))

        if cr.open_date and cr.planned_close_date:
            delta = relativedelta(cr.planned_close_date, cr.open_date)
            months = delta.years * 12 + delta.months
            if months < 1:
                months = 1
        else:
            months = 12

        pmt = annuity_payment(cr.principal_amount, rate, months)
        cr.monthly_payment = Decimal(str(round(pmt, 2)))
        cr.save(update_fields=['interest_rate', 'monthly_payment'])
        updated += 1
    print(f"[1] Updated {updated} credits with interest rates and monthly payments")

# ==========================================
# 2. Rebuild CreditState history
# ==========================================
def rebuild_credit_states():
    """
    For each credit, generate monthly CreditState snapshots from open_date
    to min(today, planned_close_date + 6 months).
    For overdue/default credits, simulate missed payments and growing overdue.
    """
    # Delete old states
    deleted = CreditState.objects.all().delete()[0]
    print(f"[2] Deleted {deleted} old CreditState records")

    credits = Credit.objects.select_related('client').all()
    total_states = 0
    today = date.today()

    for cr in credits:
        if not cr.open_date:
            continue

        client = cr.client
        rate = float(cr.interest_rate)
        monthly_rate = rate / 100 / 12
        monthly_pmt = float(cr.monthly_payment)

        # Calculate term
        if cr.planned_close_date:
            delta = relativedelta(cr.planned_close_date, cr.open_date)
            term_months = delta.years * 12 + delta.months
        else:
            term_months = 12
        if term_months < 1:
            term_months = 1

        # Determine end date for states
        end_date = min(today, cr.open_date + relativedelta(months=term_months + 6))

        is_overdue = cr.status in ('overdue', 'default')

        # How many months of data will we actually generate?
        actual_months = 0
        d = cr.open_date
        while d <= end_date:
            actual_months += 1
            d += relativedelta(months=1)

        # For overdue credits, decide when overdue starts
        if is_overdue:
            # Overdue starts somewhere between 20%-60% into generated months
            # Ensure at least 2-3 months of overdue data visible
            max_start = max(2, actual_months - 3)
            min_start = max(1, int(actual_months * 0.3))
            if min_start > max_start:
                min_start = max(1, max_start - 1)
            overdue_start_month = random.randint(min_start, max_start)
        else:
            overdue_start_month = None

        principal_remaining = float(cr.principal_amount)
        overdue_principal = 0.0
        overdue_interest = 0.0
        penalties = 0.0
        overdue_days = 0
        overdue_start_date = None
        states_batch = []

        current_date = cr.open_date
        month_num = 0

        while current_date <= end_date and principal_remaining > 0.01:
            month_num += 1

            # Interest for this month
            month_interest = principal_remaining * monthly_rate

            # Determine if payment is made
            if is_overdue and overdue_start_month and month_num >= overdue_start_month:
                # Missed payment - overdue grows
                if overdue_start_date is None:
                    overdue_start_date = current_date

                overdue_days = (current_date - overdue_start_date).days
                if overdue_days < 1:
                    overdue_days = 1

                # Accumulate overdue amounts
                overdue_principal += monthly_pmt - month_interest  # missed principal portion
                if overdue_principal < 0:
                    overdue_principal = monthly_pmt * 0.6
                overdue_interest += month_interest

                # Penalties: 0.1% per day on overdue amount, approximately per month
                daily_penalty_rate = 0.001
                month_penalty = (overdue_principal + overdue_interest) * daily_penalty_rate * 30
                penalties += month_penalty

                # Sometimes partial payments reduce overdue a little
                if random.random() < 0.2:
                    partial = random.uniform(0.1, 0.4) * monthly_pmt
                    overdue_principal = max(0, overdue_principal - partial * 0.7)
                    overdue_interest = max(0, overdue_interest - partial * 0.3)
            else:
                # Normal payment - principal reduces
                interest_portion = month_interest
                principal_portion = monthly_pmt - interest_portion
                if principal_portion > 0:
                    principal_remaining -= principal_portion
                if principal_remaining < 0:
                    principal_remaining = 0

            states_batch.append(CreditState(
                credit=cr,
                client=client,
                state_date=current_date,
                planned_payment_date=current_date + timedelta(days=random.randint(25, 30)),
                principal_debt=Decimal(str(round(max(principal_remaining, 0), 2))),
                overdue_principal=Decimal(str(round(max(overdue_principal, 0), 2))),
                interest=Decimal(str(round(month_interest, 2))),
                overdue_interest=Decimal(str(round(max(overdue_interest, 0), 2))),
                penalties=Decimal(str(round(max(penalties, 0), 2))),
                overdue_start_date=overdue_start_date,
                overdue_days=overdue_days,
                overdue_close_date=None,
            ))

            current_date += relativedelta(months=1)

        CreditState.objects.bulk_create(states_batch)
        total_states += len(states_batch)

    print(f"[2] Created {total_states} CreditState records")

# ==========================================
# 3. Rebuild Payments
# ==========================================
def rebuild_payments():
    """
    Generate payments matching credit lifecycle.
    Regular payments until overdue starts, then sporadic partial payments.
    """
    deleted = Payment.objects.all().delete()[0]
    print(f"[3] Deleted {deleted} old Payment records")

    credits = Credit.objects.select_related('client').all()
    total_payments = 0
    today = date.today()

    for cr in credits:
        if not cr.open_date:
            continue

        monthly_pmt = float(cr.monthly_payment)
        rate = float(cr.interest_rate)
        monthly_rate = rate / 100 / 12

        if cr.planned_close_date:
            delta = relativedelta(cr.planned_close_date, cr.open_date)
            term_months = delta.years * 12 + delta.months
        else:
            term_months = 12
        if term_months < 1:
            term_months = 1

        is_overdue = cr.status in ('overdue', 'default')

        # States tell us when overdue starts
        states = list(cr.states.order_by('state_date'))
        overdue_start_date = None
        for s in states:
            if s.overdue_days > 0:
                overdue_start_date = s.state_date
                break

        payments_batch = []
        current_date = cr.open_date + relativedelta(months=1)  # First payment 1 month after open
        month_num = 0

        end_date = min(today, cr.open_date + relativedelta(months=term_months + 3))

        while current_date <= end_date:
            month_num += 1
            planned_date = current_date

            if is_overdue and overdue_start_date and current_date >= overdue_start_date:
                # After overdue: sporadic partial payments
                if random.random() < 0.35:
                    # Some months have partial payment
                    pmt_amount = round(random.uniform(0.2, 0.7) * monthly_pmt, 2)
                    pmt_type = random.choice(['partial', 'partial', 'penalty'])
                    actual_date = planned_date + timedelta(days=random.randint(5, 25))
                    payment_overdue_days = (actual_date - planned_date).days

                    payments_batch.append(Payment(
                        credit=cr,
                        payment_date=actual_date,
                        amount=Decimal(str(pmt_amount)),
                        payment_type=pmt_type,
                        planned_date=planned_date,
                        min_payment=Decimal(str(round(monthly_pmt, 2))),
                        overdue_days=payment_overdue_days,
                    ))
            else:
                # Normal payment
                # Small variation in payment date (0-3 days late)
                actual_date = planned_date + timedelta(days=random.randint(0, 3))
                # Small variation in amount
                pmt_amount = round(monthly_pmt * random.uniform(0.98, 1.02), 2)
                pmt_type = 'regular'

                # Occasionally early repayment
                if random.random() < 0.05:
                    pmt_amount = round(monthly_pmt * random.uniform(1.5, 3.0), 2)
                    pmt_type = 'early'

                payments_batch.append(Payment(
                    credit=cr,
                    payment_date=actual_date,
                    amount=Decimal(str(pmt_amount)),
                    payment_type=pmt_type,
                    planned_date=planned_date,
                    min_payment=Decimal(str(round(monthly_pmt, 2))),
                    overdue_days=max(0, (actual_date - planned_date).days),
                ))

            current_date += relativedelta(months=1)

        Payment.objects.bulk_create(payments_batch)
        total_payments += len(payments_batch)

    print(f"[3] Created {total_payments} Payment records")


if __name__ == '__main__':
    print("=== Fixing credit data quality ===")
    fix_credits()
    rebuild_credit_states()
    rebuild_payments()
    
    # Quick verification
    print("\n=== Verification ===")
    sample = Credit.objects.filter(status__in=['overdue', 'default']).first()
    if sample:
        delta = relativedelta(sample.planned_close_date, sample.open_date) if sample.planned_close_date else None
        term = (delta.years * 12 + delta.months) if delta else '?'
        print(f"Credit #{sample.id}: rate={sample.interest_rate}% term={term}m pmt={sample.monthly_payment}")
        states = sample.states.order_by('state_date')
        print(f"  States: {states.count()}")
        for s in states[:5]:
            print(f"    {s.state_date}: debt={s.principal_debt} overdue_p={s.overdue_principal} "
                  f"overdue_i={s.overdue_interest} penalties={s.penalties} dpd={s.overdue_days}")
        pmts = sample.payments.order_by('payment_date')
        print(f"  Payments: {pmts.count()}")
        for p in pmts[:5]:
            print(f"    {p.payment_date}: {p.amount} type={p.payment_type}")
    print("\nDone!")
