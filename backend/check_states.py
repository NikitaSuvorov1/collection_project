import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'collection.settings'
import django
django.setup()

from collection_app.models import CreditState, Credit

print('CreditState count:', CreditState.objects.count())
cs = CreditState.objects.first()
if cs:
    print(f'Sample: credit_id={cs.credit_id} overdue_principal={cs.overdue_principal} overdue_interest={cs.overdue_interest} penalties={cs.penalties} overdue_days={cs.overdue_days}')
else:
    print('NO CreditState records!')

print('\nChecking overdue credits for latest_state:')
overdue_credits = Credit.objects.filter(status__in=['overdue', 'default']).prefetch_related('states')[:5]
for c in overdue_credits:
    latest = c.states.order_by('-state_date').first()
    if latest:
        print(f'  credit={c.id} client={c.client_id}: overdue_principal={latest.overdue_principal} overdue_interest={latest.overdue_interest} penalties={latest.penalties}')
    else:
        print(f'  credit={c.id} client={c.client_id}: NO STATE')
