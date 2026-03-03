import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'collection.settings')
django.setup()

from collection_app.models import Credit, Client, Payment, Intervention, Operator

print(f"Clients: {Client.objects.count()}")
print(f"Credits: {Credit.objects.count()}")
print(f"Payments: {Payment.objects.count()}")
print(f"Interventions: {Intervention.objects.count()}")
print(f"Operators: {Operator.objects.count()}")

print("\nCredit statuses:")
from django.db.models import Count
statuses = Credit.objects.values('status').annotate(count=Count('id'))
for s in statuses:
    print(f"  {s['status']}: {s['count']}")
