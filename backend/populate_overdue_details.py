"""
Populate overdue_interest and penalties fields for CreditState records that have overdue_principal > 0.
"""
import os, random
os.environ['DJANGO_SETTINGS_MODULE'] = 'collection.settings'
import django
django.setup()

from decimal import Decimal
from collection_app.models import CreditState

states = CreditState.objects.filter(overdue_principal__gt=0)
count = states.count()
print(f'Found {count} CreditState records with overdue_principal > 0')

updated = 0
for st in states:
    # overdue_interest = 5-20% of overdue_principal
    interest_pct = Decimal(str(round(random.uniform(0.05, 0.20), 4)))
    st.overdue_interest = (st.overdue_principal * interest_pct).quantize(Decimal('0.01'))
    
    # penalties = 1-8% of overdue_principal (higher for longer overdue)
    penalty_pct = Decimal(str(round(random.uniform(0.01, 0.08), 4)))
    if st.overdue_days > 60:
        penalty_pct *= 2
    elif st.overdue_days > 30:
        penalty_pct *= Decimal('1.5')
    st.penalties = (st.overdue_principal * penalty_pct).quantize(Decimal('0.01'))
    
    st.save(update_fields=['overdue_interest', 'penalties'])
    updated += 1

print(f'Updated {updated} records')

# Verify
from django.db.models import Sum, Avg
agg = CreditState.objects.filter(overdue_principal__gt=0).aggregate(
    avg_principal=Avg('overdue_principal'),
    avg_interest=Avg('overdue_interest'),
    avg_penalties=Avg('penalties'),
)
print(f'Averages: principal={agg["avg_principal"]:.2f} interest={agg["avg_interest"]:.2f} penalties={agg["avg_penalties"]:.2f}')
