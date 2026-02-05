"""Тестовый скрипт для API прогнозирования"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'collection.settings')

import django
django.setup()

from django.contrib.auth.models import User
from collection_app.views import CreditApplicationViewSet
from rest_framework.test import APIRequestFactory, force_authenticate

print("=" * 60)
print("Тестирование API прогнозирования одобрения кредитов")
print("=" * 60)

# Создаем или получаем тестового пользователя
user, _ = User.objects.get_or_create(username='testuser', defaults={'is_staff': True})

factory = APIRequestFactory()
view = CreditApplicationViewSet.as_view({'post': 'predict_approval'})

# Тест 1: С данными напрямую
print("\nТест 1: Прямой запрос с данными")
data = {
    'gender': 'M',
    'marital_status': 'married',
    'employment': 'employed',
    'income': 100000,
    'monthly_expenses': 30000,
    'loan_amount': 500000,
    'loan_term': 36,
    'children_count': 1,
    'credit_history': 1,
    'region': 'Moscow'
}
request = factory.post('/api/applications/predict_approval/', data, format='json')
force_authenticate(request, user=user)
response = view(request)
print(f"  Status: {response.status_code}")
print(f"  Response: {response.data}")

# Тест 2: С client_id из базы
print("\nТест 2: Запрос с client_id (берет данные клиента из БД)")
from collection_app.models import Client
client = Client.objects.first()
if client:
    data = {
        'client_id': client.id,
        'loan_amount': 300000,
        'loan_term': 24
    }
    request = factory.post('/api/applications/predict_approval/', data, format='json')
    force_authenticate(request, user=user)
    response = view(request)
    print(f"  Client: {client.full_name}")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.data}")

# Тест 3: Обработка заявки
print("\nТест 3: Обработка существующей заявки")
from collection_app.models import CreditApplication
app = CreditApplication.objects.first()
if app:
    view2 = CreditApplicationViewSet.as_view({'post': 'process_application'})
    request = factory.post(f'/api/applications/{app.id}/process_application/', {'auto_decide': True}, format='json')
    force_authenticate(request, user=user)
    response = view2(request, pk=app.id)
    print(f"  Application: {app}")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.data}")

print("\n" + "=" * 60)
print("Тестирование API завершено!")
print("=" * 60)
