from django.core.management.base import BaseCommand
from collection_app.models import Client, ScoringResult
from collection_app.ml.overdue_scoring import score_client

class Command(BaseCommand):
    help = 'Run overdue scoring for clients and store results'

    def handle(self, *args, **options):
        clients = Client.objects.all()
        self.stdout.write(f'Found {clients.count()} clients')
        for c in clients:
            data = {'phone': c.phone, 'email': c.email}
            prob = score_client(data)
            ScoringResult.objects.create(client=c, model='overdue_v0', probability=prob)
            self.stdout.write(f'Client {c}: prob={prob:.3f}')
