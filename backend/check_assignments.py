import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'collection.settings'
import django
django.setup()

from collection_app.models import Assignment, Operator
from django.db.models import Count

# Distribution per operator (top 15)
print("Distribution by operator (top 15):")
dist = Assignment.objects.filter(overdue_days__gt=0).values('operator__full_name', 'operator_id').annotate(cnt=Count('id')).order_by('-cnt')[:15]
for d in dist:
    print(f"  op_id={d['operator_id']} {d['operator__full_name']}: {d['cnt']} assignments")

print(f"\nTotal assignments with overdue>0: {Assignment.objects.filter(overdue_days__gt=0).count()}")

# Check first 5 operators
print("\nFirst 5 operators:")
for op in Operator.objects.all()[:5]:
    cnt = Assignment.objects.filter(operator_id=op.id, overdue_days__gt=0).count()
    print(f"  op_id={op.id} {op.full_name}: {cnt} overdue assignments")

# Check serialized data for one assignment
a = Assignment.objects.filter(overdue_days__gt=0).select_related('credit__client', 'operator').first()
if a:
    print(f"\nSample: id={a.id} op={a.operator_id} client={a.client_id} credit={a.credit_id}")
    print(f"  debtor_name={a.debtor_name} overdue_amount={a.overdue_amount} overdue_days={a.overdue_days}")
    if a.credit and a.credit.client:
        print(f"  credit.client.id={a.credit.client.id} credit.client.full_name={a.credit.client.full_name}")
        print(f"  credit.client.phone_mobile={a.credit.client.phone_mobile}")
