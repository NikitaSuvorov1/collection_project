"""Тестовый скрипт для проверки модели прогнозирования одобрения кредитов"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'collection.settings')

import django
django.setup()

from collection_app.ml.loan_predictor import predict_loan_approval, LoanApprovalPredictor

print("=" * 60)
print("Тестирование модели прогнозирования одобрения кредитов")
print("=" * 60)

# Тест 1: Хороший клиент
test_good = {
    'gender': 'M',
    'marital_status': 'married',
    'employment': 'employed',
    'income': 150000,
    'monthly_expenses': 40000,
    'loan_amount': 500000,
    'loan_term': 36,
    'children_count': 1,
    'credit_history': 1,  # хорошая история
    'region': 'Москва'
}

print("\nТест 1: Хороший клиент (доход 150к, кредит 500к на 36 мес)")
result = predict_loan_approval(test_good)
print(f"  Вероятность одобрения: {result['approved_probability']:.1%}")
print(f"  Решение: {result['decision']}")
print(f"  Уверенность: {result['confidence']:.1%}")
print(f"  Факторы риска: {result.get('risk_factors', [])}")

# Тест 2: Рискованный клиент
test_risky = {
    'gender': 'F',
    'marital_status': 'single',
    'employment': 'unemployed',
    'income': 30000,
    'monthly_expenses': 25000,
    'loan_amount': 1000000,
    'loan_term': 12,
    'children_count': 3,
    'credit_history': 0,  # плохая история
    'region': 'Регион'
}

print("\nТест 2: Рискованный клиент (безработный, доход 30к, кредит 1М на 12 мес)")
result = predict_loan_approval(test_risky)
print(f"  Вероятность одобрения: {result['approved_probability']:.1%}")
print(f"  Решение: {result['decision']}")
print(f"  Уверенность: {result['confidence']:.1%}")
print(f"  Факторы риска: {result.get('risk_factors', [])}")

# Тест 3: Средний клиент
test_medium = {
    'gender': 'M',
    'marital_status': 'divorced',
    'employment': 'self_employed',
    'income': 80000,
    'monthly_expenses': 35000,
    'loan_amount': 400000,
    'loan_term': 24,
    'children_count': 2,
    'credit_history': 1,
    'region': 'СПб'
}

print("\nТест 3: Средний клиент (самозанятый, доход 80к, кредит 400к на 24 мес)")
result = predict_loan_approval(test_medium)
print(f"  Вероятность одобрения: {result['approved_probability']:.1%}")
print(f"  Решение: {result['decision']}")
print(f"  Уверенность: {result['confidence']:.1%}")
print(f"  Факторы риска: {result.get('risk_factors', [])}")

print("\n" + "=" * 60)
print("Тестирование завершено!")
print("=" * 60)
