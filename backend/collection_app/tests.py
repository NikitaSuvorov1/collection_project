from django.test import TestCase
from .models import Client

class ClientModelTest(TestCase):
    def test_client_creation(self):
        c = Client.objects.create(first_name='Test', last_name='User')
        self.assertEqual(str(c), 'Test User')
