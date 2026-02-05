"""
Django management команда для обучения модели прогнозирования одобрения кредитов.

Использует данные из БД (клиенты + кредиты) для генерации обучающей выборки.
"""

import random
from django.core.management.base import BaseCommand
from collection_app.models import Client, Credit, CreditApplication
from collection_app.ml.loan_predictor import LoanApprovalPredictor, get_predictor


class Command(BaseCommand):
    help = 'Обучение модели прогнозирования одобрения кредитов'

    def add_arguments(self, parser):
        parser.add_argument(
            '--samples',
            type=int,
            default=1000,
            help='Количество обучающих примеров для генерации (default: 1000)'
        )
        parser.add_argument(
            '--use-existing',
            action='store_true',
            help='Использовать существующие CreditApplication для обучения'
        )

    def handle(self, *args, **options):
        num_samples = options['samples']
        use_existing = options['use_existing']
        
        self.stdout.write(f"Начало обучения модели прогнозирования одобрения кредитов...")
        
        if use_existing:
            training_data, labels = self._get_existing_applications()
        else:
            training_data, labels = self._generate_synthetic_data(num_samples)
        
        if len(training_data) < 50:
            self.stdout.write(self.style.ERROR(
                f"Недостаточно данных для обучения: {len(training_data)}. Нужно минимум 50."
            ))
            return
        
        self.stdout.write(f"Подготовлено {len(training_data)} примеров для обучения")
        self.stdout.write(f"  - Одобрено: {sum(labels)}")
        self.stdout.write(f"  - Отказано: {len(labels) - sum(labels)}")
        
        # Обучаем модель
        predictor = LoanApprovalPredictor()
        metrics = predictor.fit(training_data, labels)
        
        self.stdout.write(self.style.SUCCESS(
            f"\nМодель обучена успешно!"
        ))
        self.stdout.write(f"  Accuracy: {metrics['accuracy']:.2%}")
        self.stdout.write(f"  Train samples: {metrics['train_size']}")
        self.stdout.write(f"  Test samples: {metrics['test_size']}")
        
        # Показываем confusion matrix
        cm = metrics['confusion_matrix']
        self.stdout.write(f"\n  Confusion Matrix:")
        self.stdout.write(f"    Actual Rejected:  [{cm[0][0]:4d}, {cm[0][1]:4d}]")
        self.stdout.write(f"    Actual Approved:  [{cm[1][0]:4d}, {cm[1][1]:4d}]")
        
        # Тестовое предсказание
        self.stdout.write(f"\n  Тестовое предсказание:")
        test_case = {
            'gender': 'M',
            'marital_status': 'married',
            'employment': 'employed',
            'income': 100000,
            'monthly_expenses': 30000,
            'loan_amount': 500000,
            'loan_term': 36,
            'children_count': 1,
            'credit_history': 1,
            'region': 'Москва'
        }
        result = predictor.predict(test_case)
        self.stdout.write(f"    Вероятность одобрения: {result['approved_probability']:.1%}")
        self.stdout.write(f"    Решение: {result['decision']}")
        self.stdout.write(f"    Уверенность: {result['confidence']:.1%}")

    def _get_existing_applications(self):
        """Получение данных из существующих CreditApplication."""
        training_data = []
        labels = []
        
        applications = CreditApplication.objects.select_related('client').exclude(
            decision='pending'
        )
        
        for app in applications:
            client = app.client
            
            # Проверяем кредитную историю клиента
            has_overdue = Credit.objects.filter(
                client=client,
                status__in=['overdue', 'default']
            ).exists()
            
            data = {
                'gender': client.gender,
                'marital_status': client.marital_status,
                'employment': client.employment,
                'income': float(client.income),
                'monthly_expenses': float(client.monthly_expenses),
                'loan_amount': float(app.amount),
                'loan_term': app.requested_term,
                'children_count': client.children_count,
                'credit_history': 0 if has_overdue else 1,
                'region': client.region or 'unknown'
            }
            
            training_data.append(data)
            labels.append(1 if app.decision == 'approved' else 0)
        
        return training_data, labels

    def _generate_synthetic_data(self, num_samples):
        """
        Генерация синтетических данных на основе клиентов и кредитов из БД.
        
        Логика одобрения основана на реалистичных правилах:
        - Хорошая кредитная история = +30% вероятности
        - Низкий DTI (debt-to-income) = +20%
        - Стабильная занятость = +15%
        - Высокий доход = +10%
        """
        training_data = []
        labels = []
        
        clients = list(Client.objects.all())
        
        if not clients:
            self.stdout.write(self.style.WARNING("Нет клиентов в БД, генерируем случайные данные"))
            return self._generate_random_data(num_samples)
        
        self.stdout.write(f"Найдено {len(clients)} клиентов в БД")
        
        for _ in range(num_samples):
            client = random.choice(clients)
            
            # Генерируем параметры заявки
            income = float(client.income) if client.income else random.randint(30000, 200000)
            expenses = float(client.monthly_expenses) if client.monthly_expenses else income * random.uniform(0.2, 0.5)
            
            # Сумма кредита - от 3 до 36 месячных доходов
            loan_multiplier = random.uniform(3, 36)
            loan_amount = income * loan_multiplier
            loan_term = random.choice([6, 12, 24, 36, 48, 60])
            
            # Проверяем кредитную историю
            has_overdue = Credit.objects.filter(
                client=client,
                status__in=['overdue', 'default']
            ).exists()
            credit_history = 0 if has_overdue else random.choices([0, 1], weights=[0.15, 0.85])[0]
            
            data = {
                'gender': client.gender,
                'marital_status': client.marital_status,
                'employment': client.employment,
                'income': income,
                'monthly_expenses': expenses,
                'loan_amount': loan_amount,
                'loan_term': loan_term,
                'children_count': client.children_count,
                'credit_history': credit_history,
                'region': client.region or random.choice(['Москва', 'СПб', 'Регион'])
            }
            
            # Рассчитываем вероятность одобрения по правилам
            approval_score = self._calculate_approval_score(data)
            
            # Добавляем шум для реалистичности
            approval_score += random.gauss(0, 0.1)
            approval_score = max(0, min(1, approval_score))
            
            # Определяем метку с некоторой случайностью
            is_approved = random.random() < approval_score
            
            training_data.append(data)
            labels.append(1 if is_approved else 0)
        
        return training_data, labels

    def _generate_random_data(self, num_samples):
        """Генерация полностью случайных данных."""
        training_data = []
        labels = []
        
        genders = ['M', 'F']
        marital_statuses = ['single', 'married', 'divorced', 'widowed']
        employments = ['employed', 'self_employed', 'unemployed', 'retired', 'student']
        regions = ['Москва', 'Санкт-Петербург', 'Екатеринбург', 'Новосибирск', 'Казань', 'Регион']
        
        for _ in range(num_samples):
            income = random.randint(20000, 300000)
            expenses = income * random.uniform(0.2, 0.6)
            loan_amount = income * random.uniform(3, 48)
            
            data = {
                'gender': random.choice(genders),
                'marital_status': random.choice(marital_statuses),
                'employment': random.choice(employments),
                'income': income,
                'monthly_expenses': expenses,
                'loan_amount': loan_amount,
                'loan_term': random.choice([6, 12, 24, 36, 48, 60]),
                'children_count': random.randint(0, 4),
                'credit_history': random.choices([0, 1], weights=[0.2, 0.8])[0],
                'region': random.choice(regions)
            }
            
            approval_score = self._calculate_approval_score(data)
            is_approved = random.random() < approval_score
            
            training_data.append(data)
            labels.append(1 if is_approved else 0)
        
        return training_data, labels

    def _calculate_approval_score(self, data):
        """
        Расчёт вероятности одобрения на основе правил.
        
        Эти правила используются для генерации "ground truth" меток
        при создании обучающей выборки.
        """
        score = 0.5  # Базовый балл
        
        # 1. Кредитная история (самый важный фактор, как в реальной жизни)
        if data['credit_history'] == 1:
            score += 0.25
        else:
            score -= 0.35
        
        # 2. Соотношение долга к доходу (DTI)
        income = data['income']
        if income > 0:
            monthly_payment = data['loan_amount'] / data['loan_term']
            dti = (monthly_payment + data['monthly_expenses']) / income
            
            if dti < 0.3:
                score += 0.2
            elif dti < 0.4:
                score += 0.1
            elif dti < 0.5:
                score += 0.0
            elif dti < 0.6:
                score -= 0.1
            else:
                score -= 0.25
        else:
            score -= 0.3
        
        # 3. Занятость
        employment = data['employment']
        if employment == 'employed':
            score += 0.12
        elif employment == 'self_employed':
            score += 0.08
        elif employment == 'retired':
            score += 0.05
        elif employment == 'student':
            score -= 0.1
        else:  # unemployed
            score -= 0.2
        
        # 4. Уровень дохода
        if income >= 150000:
            score += 0.1
        elif income >= 80000:
            score += 0.05
        elif income < 30000:
            score -= 0.1
        
        # 5. Семейное положение (небольшое влияние)
        if data['marital_status'] == 'married':
            score += 0.05
        
        # 6. Количество иждивенцев
        children = data['children_count']
        if children == 0:
            score += 0.02
        elif children <= 2:
            pass  # нейтрально
        else:
            score -= 0.05 * (children - 2)
        
        return max(0, min(1, score))
