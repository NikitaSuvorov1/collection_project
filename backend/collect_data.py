"""
Простой скрипт для сбора данных из БД для обучения модели.
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'collection.settings')
django.setup()

from datetime import date, timedelta
from decimal import Decimal
import pandas as pd
from collection_app.models import Client, Credit, Payment, Intervention
from django.db.models import Count, Sum, Avg, Max

print("Собираем данные из базы...")

# Получаем все кредиты с платежами
credits = Credit.objects.filter(
    status__in=['active', 'overdue', 'default']
).select_related('client')

print(f"Найдено кредитов: {credits.count()}")

training_data = []

for credit in credits:
    client = credit.client
    payments = Payment.objects.filter(credit=credit)
    interventions = Intervention.objects.filter(credit=credit)
    
    if not payments.exists():
        continue
    
    # Считаем признаки из реальных данных
    
    # 1. Возраст
    age = 0
    if client.birth_date:
        age = (date.today() - client.birth_date).days // 365
    
    # 2. Пол
    gender = 1 if client.gender == 'M' else 0
    
    # 3. Семейное положение
    marital_map = {'single': 0, 'married': 1, 'divorced': 2, 'widowed': 3}
    marital_status = marital_map.get(client.marital_status, 0)
    
    # 4. Занятость
    employment_map = {'employed': 2, 'self_employed': 2, 'unemployed': 0, 'retired': 1, 'student': 1}
    employment = employment_map.get(client.employment, 1)
    
    # 5. Количество детей
    dependents = client.children_count or 0
    
    # 6. Доход
    monthly_income = float(client.income or 0)
    
    # 7-8. Другие кредиты
    other_credits = Credit.objects.filter(client=client).exclude(id=credit.id).count()
    has_other_credits = 1 if other_credits > 0 else 0
    
    # 9. Сумма кредита
    credit_amount = float(credit.principal_amount or 0)
    
    # 10. Срок кредита (месяцев)
    credit_term = 12
    if credit.open_date and credit.planned_close_date:
        credit_term = max(1, (credit.planned_close_date - credit.open_date).days // 30)
    
    # 11. Процентная ставка
    interest_rate = float(credit.interest_rate or 0)
    
    # 12. LTI
    lti_ratio = credit_amount / monthly_income if monthly_income > 0 else 0
    
    # 13. Возраст кредита (дней)
    credit_age = (date.today() - credit.open_date).days if credit.open_date else 0
    
    # 14. Статус кредита
    status_map = {'active': 1, 'overdue': 2, 'default': 3}
    credit_status = status_map.get(credit.status, 1)
    
    # 15. Ежемесячный платёж
    monthly_payment = float(credit.monthly_payment or 0)
    
    # --- Данные из платежей ---
    total_payments = payments.count()
    overdue_payments = payments.filter(overdue_days__gt=0).count()
    max_overdue_days = payments.aggregate(m=Max('overdue_days'))['m'] or 0
    avg_payment = payments.aggregate(a=Avg('amount'))['a'] or 0
    
    # Платежи за последний год
    year_ago = date.today() - timedelta(days=365)
    payments_12m = payments.filter(payment_date__gte=year_ago)
    payments_count_12m = payments_12m.count()
    overdue_count_12m = payments_12m.filter(overdue_days__gt=0).count()
    max_overdue_12m = payments_12m.aggregate(m=Max('overdue_days'))['m'] or 0
    
    # Доля просрочек
    overdue_share = overdue_payments / total_payments if total_payments > 0 else 0
    overdue_share_12m = overdue_count_12m / payments_count_12m if payments_count_12m > 0 else 0
    
    # --- Данные из воздействий ---
    total_interventions = interventions.count()
    completed_interventions = interventions.filter(status='completed').count()
    promises = interventions.exclude(promise_amount__isnull=True).exclude(promise_amount=0).count()
    
    # --- Целевая переменная (категория риска) ---
    # y=0: низкий риск (<30% просрочек)
    # y=1: средний риск (30-60% просрочек)
    # y=2: высокий риск (>60% просрочек)
    risk_category = 0
    if 0.3 <= overdue_share < 0.6:
        risk_category = 1
    elif overdue_share >= 0.6:
        risk_category = 2
    
    training_data.append({
        'client_id': client.id,
        'credit_id': credit.id,
        'age': age,
        'gender': gender,
        'marital_status': marital_status,
        'employment': employment,
        'dependents': dependents,
        'monthly_income': monthly_income,
        'has_other_credits': has_other_credits,
        'other_credits_count': other_credits,
        'credit_amount': credit_amount,
        'credit_term': credit_term,
        'interest_rate': interest_rate,
        'lti_ratio': round(lti_ratio, 2),
        'credit_age': credit_age,
        'credit_status': credit_status,
        'monthly_payment': monthly_payment,
        'total_payments': total_payments,
        'overdue_payments': overdue_payments,
        'max_overdue_days': max_overdue_days,
        'avg_payment': float(avg_payment),
        'payments_count_12m': payments_count_12m,
        'overdue_count_12m': overdue_count_12m,
        'overdue_share_12m': round(overdue_share_12m, 3),
        'max_overdue_12m': max_overdue_12m,
        'total_interventions': total_interventions,
        'completed_interventions': completed_interventions,
        'promises_count': promises,
        'risk_category': risk_category
    })

print(f"Обработано записей: {len(training_data)}")

# Сохраняем
df = pd.DataFrame(training_data)
df.to_csv('training_data.csv', index=False)

print(f"\nДанные сохранены в training_data.csv")
print(f"\nРаспределение по категориям риска:")
print(df['risk_category'].value_counts())
print(f"\nПризнаки: {list(df.columns)}")
