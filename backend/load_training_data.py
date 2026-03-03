"""
Скрипт для загрузки обучающих данных в таблицу TrainingData
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'collection.settings')
django.setup()

import pandas as pd
from collection_app.models import Client, Credit, TrainingData

print("Загружаем данные из training_data.csv в TrainingData...")

df = pd.read_csv('training_data.csv')
print(f"Загружено {len(df)} записей из CSV")

# Удаляем старые записи
deleted = TrainingData.objects.all().delete()
print(f"Удалено старых записей: {deleted[0]}")

created = 0
errors = 0

for _, row in df.iterrows():
    try:
        client = Client.objects.get(id=row['client_id'])
        credit = Credit.objects.get(id=row['credit_id'])
        
        TrainingData.objects.create(
            client=client,
            credit=credit,
            # Параметры клиента
            age=int(row['age']),
            gender=int(row['gender']),
            marital_status=int(row['marital_status']),
            employment=int(row['employment']),
            dependents=int(row['dependents']),
            monthly_income=float(row['monthly_income']),
            has_other_credits=int(row['has_other_credits']),
            other_credits_count=int(row['other_credits_count']),
            # Параметры кредита
            credit_amount=float(row['credit_amount']),
            credit_term=int(row['credit_term']),
            interest_rate=float(row['interest_rate']),
            lti_ratio=float(row['lti_ratio']),
            credit_age=int(row['credit_age']),
            credit_status=int(row['credit_status']),
            monthly_payment=float(row['monthly_payment']),
            # Платёжная дисциплина
            total_payments=int(row['total_payments']),
            overdue_payments=int(row['overdue_payments']),
            max_overdue_days=int(row['max_overdue_days']),
            avg_payment=float(row['avg_payment']),
            payments_count_12m=int(row['payments_count_12m']),
            overdue_count_12m=int(row['overdue_count_12m']),
            overdue_share_12m=float(row['overdue_share_12m']),
            max_overdue_12m=int(row['max_overdue_12m']),
            # Взаимодействия
            total_interventions=int(row['total_interventions']),
            completed_interventions=int(row['completed_interventions']),
            promises_count=int(row['promises_count']),
            # Целевая переменная
            risk_category=int(row['risk_category'])
        )
        created += 1
    except Exception as e:
        errors += 1
        if errors <= 3:
            print(f"Ошибка: {e}")

print(f"\n=== Результат ===")
print(f"Создано записей в TrainingData: {created}")
print(f"Ошибок: {errors}")
print(f"Всего записей в таблице: {TrainingData.objects.count()}")

print(f"\nРаспределение по категориям риска (y):")
from django.db.models import Count
categories = TrainingData.objects.values('risk_category').annotate(count=Count('id')).order_by('risk_category')
for c in categories:
    labels = {0: 'Низкий', 1: 'Средний', 2: 'Высокий'}
    print(f"  {c['risk_category']} ({labels[c['risk_category']]}): {c['count']} записей")
