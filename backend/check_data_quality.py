import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'collection.settings'
import django
django.setup()

from collection_app.models import Credit, CreditState, Payment
from django.db.models import Avg, Count, Min, Max

# Credit data quality
print("=== CREDITS ===")
print(f"Total: {Credit.objects.count()}")
print(f"With interest_rate=0: {Credit.objects.filter(interest_rate=0).count()}")
print(f"With monthly_payment=0: {Credit.objects.filter(monthly_payment=0).count()}")
print(f"With planned_close_date: {Credit.objects.exclude(planned_close_date=None).count()}")
print(f"Avg interest_rate: {Credit.objects.aggregate(a=Avg('interest_rate'))['a']}")

# Sample overdue credit
c = Credit.objects.filter(status='overdue').first()
if c:
    print(f"\nSample overdue credit #{c.id}:")
    print(f"  principal={c.principal_amount} rate={c.interest_rate} monthly={c.monthly_payment}")
    print(f"  open={c.open_date} close={c.planned_close_date} product={c.product_type}")
    print(f"  States: {c.states.count()}")
    print(f"  Payments: {c.payments.count()}")

# CreditState data quality
print("\n=== CREDIT STATES ===")
print(f"Total: {CreditState.objects.count()}")
agg = CreditState.objects.aggregate(
    avg_states_per_credit=Count('id') / Count('credit_id', distinct=True),
)
print(f"States per credit (avg): {CreditState.objects.count() / CreditState.objects.values('credit_id').distinct().count():.1f}")
print(f"Unique credits with states: {CreditState.objects.values('credit_id').distinct().count()}")

# Check if states have temporal progression
cs = CreditState.objects.filter(credit=c).order_by('state_date') if c else []
print(f"\nStates for credit #{c.id if c else '?'}:")
for s in cs:
    print(f"  {s.state_date}: principal={s.principal_debt} overdue_p={s.overdue_principal} interest={s.overdue_interest} penalties={s.penalties} days={s.overdue_days}")

# Payments
print("\n=== PAYMENTS ===")
print(f"Total: {Payment.objects.count()}")
print(f"Unique credits with payments: {Payment.objects.values('credit_id').distinct().count()}")
if c:
    pf = Payment.objects.filter(credit=c).order_by('payment_date')[:5]
    print(f"Payments for credit #{c.id}: {Payment.objects.filter(credit=c).count()}")
    for p in pf:
        print(f"  {p.payment_date}: {p.amount} type={p.payment_type}")
