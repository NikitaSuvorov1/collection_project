"""
Скрипт для загрузки обучающих данных в таблицу ScoringResult
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'collection.settings')
django.setup()

import pandas as pd
from datetime import date
from collection_app.models import Client, Credit, ScoringResult

print("Загружаем данные из training_data.csv...")

df = pd.read_csv('training_data.csv')
print(f"Загружено {len(df)} записей")

# Удаляем старые записи скоринга
deleted = ScoringResult.objects.all().delete()
print(f"Удалено старых записей: {deleted[0]}")

# Маппинг категорий риска
risk_map = {0: 'low', 1: 'medium', 2: 'high'}

created = 0
errors = 0

for _, row in df.iterrows():
    try:
        client = Client.objects.get(id=row['client_id'])
        credit = Credit.objects.get(id=row['credit_id'])
        
        # Вероятность просрочки на основе доли просрочек
        probability = row['overdue_share_12m'] if row['overdue_share_12m'] > 0 else row['overdue_payments'] / max(row['total_payments'], 1)
        
        ScoringResult.objects.create(
            client=client,
            credit=credit,
            calculation_date=date.today(),
            probability=probability,
            risk_segment=risk_map.get(row['risk_category'], 'medium')
        )
        created += 1
    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"Ошибка: {e}")

print(f"\nСоздано записей в ScoringResult: {created}")
print(f"Ошибок: {errors}")

# Проверка
print(f"\nВсего записей в ScoringResult: {ScoringResult.objects.count()}")
print("\nРаспределение по сегментам риска:")
from django.db.models import Count
segments = ScoringResult.objects.values('risk_segment').annotate(count=Count('id'))
for s in segments:
    print(f"  {s['risk_segment']}: {s['count']}")
