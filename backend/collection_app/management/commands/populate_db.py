"""
Management command to populate database with sample data.
Creates:
- 5000 Clients
- 50 Operators
- 700 Credits
- 5000 CreditStates
- 10000 Payments
- 10000 Interventions
- 3000 Assignments
- 2000 ScoringResults
"""
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from collection_app.models import (
    Client, Operator, Credit, CreditState, Payment,
    Intervention, Assignment, ScoringResult
)

# Russian names for realistic data
FIRST_NAMES_M = ['Александр', 'Михаил', 'Иван', 'Дмитрий', 'Сергей', 'Андрей', 'Алексей', 'Артём', 'Максим', 'Егор',
                 'Николай', 'Павел', 'Владимир', 'Константин', 'Роман', 'Денис', 'Евгений', 'Олег', 'Виктор', 'Антон']
FIRST_NAMES_F = ['Анна', 'Мария', 'Елена', 'Ольга', 'Наталья', 'Ирина', 'Екатерина', 'Татьяна', 'Светлана', 'Юлия',
                 'Дарья', 'Анастасия', 'Ксения', 'Полина', 'Вера', 'Алина', 'Виктория', 'Марина', 'Людмила', 'Галина']
LAST_NAMES = ['Иванов', 'Петров', 'Сидоров', 'Козлов', 'Новиков', 'Морозов', 'Волков', 'Соколов', 'Попов', 'Лебедев',
              'Кузнецов', 'Смирнов', 'Федоров', 'Алексеев', 'Егоров', 'Николаев', 'Орлов', 'Андреев', 'Макаров', 'Захаров',
              'Васильев', 'Павлов', 'Семенов', 'Голубев', 'Виноградов', 'Богданов', 'Воробьев', 'Филиппов', 'Марков', 'Романов']
PATRONYMICS_M = ['Александрович', 'Михайлович', 'Иванович', 'Дмитриевич', 'Сергеевич', 'Андреевич', 'Алексеевич', 
                 'Николаевич', 'Павлович', 'Владимирович']
PATRONYMICS_F = ['Александровна', 'Михайловна', 'Ивановна', 'Дмитриевна', 'Сергеевна', 'Андреевна', 'Алексеевна',
                 'Николаевна', 'Павловна', 'Владимировна']

CITIES = ['Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 'Казань', 'Нижний Новгород', 'Челябинск',
          'Самара', 'Омск', 'Ростов-на-Дону', 'Уфа', 'Красноярск', 'Воронеж', 'Пермь', 'Волгоград']
REGIONS = ['Московская область', 'Ленинградская область', 'Новосибирская область', 'Свердловская область',
           'Республика Татарстан', 'Нижегородская область', 'Челябинская область', 'Самарская область',
           'Омская область', 'Ростовская область', 'Республика Башкортостан', 'Красноярский край']

POSITIONS = ['Менеджер', 'Инженер', 'Бухгалтер', 'Продавец', 'Водитель', 'Программист', 'Учитель', 'Врач',
             'Юрист', 'Экономист', 'Администратор', 'Директор', 'Специалист', 'Консультант', 'Аналитик']


def random_phone():
    return f'+7 ({random.randint(900, 999)}) {random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10, 99)}'


def random_date(start_year=1960, end_year=2000):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def random_datetime_range(start_date, end_date):
    delta = (end_date - start_date).days
    random_days = random.randint(0, max(delta, 1))
    random_time = timedelta(hours=random.randint(8, 18), minutes=random.randint(0, 59))
    return datetime.combine(start_date + timedelta(days=random_days), datetime.min.time()) + random_time


class Command(BaseCommand):
    help = 'Populate database with sample data'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing data before populating')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            ScoringResult.objects.all().delete()
            Assignment.objects.all().delete()
            Intervention.objects.all().delete()
            Payment.objects.all().delete()
            CreditState.objects.all().delete()
            Credit.objects.all().delete()
            Client.objects.all().delete()
            Operator.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Data cleared.'))

        self.stdout.write('Creating operators (50)...')
        operators = self._create_operators(50)

        self.stdout.write('Creating clients (5000)...')
        clients = self._create_clients(5000)

        self.stdout.write('Creating credits (700)...')
        credits = self._create_credits(clients, 700)

        self.stdout.write('Creating credit states (5000)...')
        self._create_credit_states(credits, 5000)

        self.stdout.write('Creating payments (10000)...')
        self._create_payments(credits, 10000)

        self.stdout.write('Creating interventions (10000)...')
        self._create_interventions(clients, credits, operators, 10000)

        self.stdout.write('Creating assignments (3000)...')
        self._create_assignments(operators, credits, 3000)

        self.stdout.write('Creating scoring results (2000)...')
        self._create_scoring_results(clients, credits, 2000)

        self.stdout.write(self.style.SUCCESS('Database populated successfully!'))

    def _create_operators(self, count):
        operators = []
        roles = ['operator', 'senior_operator', 'supervisor', 'manager']
        statuses = ['active', 'break', 'offline', 'on_call']
        
        for i in range(count):
            gender = random.choice(['M', 'F'])
            if gender == 'M':
                first_name = random.choice(FIRST_NAMES_M)
                last_name = random.choice(LAST_NAMES)
                patronymic = random.choice(PATRONYMICS_M)
            else:
                first_name = random.choice(FIRST_NAMES_F)
                last_name = random.choice(LAST_NAMES) + 'а'
                patronymic = random.choice(PATRONYMICS_F)
            
            full_name = f'{last_name} {first_name} {patronymic}'
            
            op = Operator.objects.create(
                full_name=full_name,
                role=random.choice(roles),
                hire_date=random_date(2018, 2025),
                current_load=random.randint(0, 50),
                status=random.choice(statuses)
            )
            operators.append(op)
        
        return operators

    def _create_clients(self, count):
        clients = []
        genders = ['M', 'F']
        marital_statuses = ['single', 'married', 'divorced', 'widowed']
        employments = ['employed', 'self_employed', 'unemployed', 'retired', 'student']
        categories = ['standard', 'vip', 'problem', 'new']
        
        for i in range(count):
            gender = random.choice(genders)
            if gender == 'M':
                first_name = random.choice(FIRST_NAMES_M)
                last_name = random.choice(LAST_NAMES)
                patronymic = random.choice(PATRONYMICS_M)
            else:
                first_name = random.choice(FIRST_NAMES_F)
                last_name = random.choice(LAST_NAMES) + 'а'
                patronymic = random.choice(PATRONYMICS_F)
            
            full_name = f'{last_name} {first_name} {patronymic}'
            city = random.choice(CITIES)
            
            income = Decimal(random.randint(20000, 300000))
            expenses = income * Decimal(random.uniform(0.3, 0.8))
            
            client = Client.objects.create(
                full_name=full_name,
                birth_date=random_date(1960, 2000),
                gender=gender,
                marital_status=random.choice(marital_statuses),
                employment=random.choice(employments),
                position=random.choice(POSITIONS) if random.random() > 0.2 else '',
                income=income,
                has_children=random.choice([True, False]),
                city=city,
                region=random.choice(REGIONS),
                phone_mobile=random_phone(),
                phone_work=random_phone() if random.random() > 0.5 else '',
                phone_home=random_phone() if random.random() > 0.7 else '',
                monthly_expenses=expenses.quantize(Decimal('0.01')),
                category=random.choice(categories)
            )
            clients.append(client)
            
            if (i + 1) % 1000 == 0:
                self.stdout.write(f'  Created {i + 1} clients...')
        
        return clients

    def _create_credits(self, clients, count):
        credits = []
        product_types = ['consumer', 'mortgage', 'car', 'credit_card', 'microloan']
        statuses = ['active', 'closed', 'overdue', 'default', 'restructured']
        
        # Select random clients who will have credits
        clients_with_credits = random.sample(clients, min(count, len(clients)))
        
        for i in range(count):
            client = clients_with_credits[i % len(clients_with_credits)]
            product = random.choice(product_types)
            
            # Different amounts based on product type
            if product == 'mortgage':
                amount = Decimal(random.randint(1000000, 10000000))
            elif product == 'car':
                amount = Decimal(random.randint(300000, 2000000))
            elif product == 'microloan':
                amount = Decimal(random.randint(5000, 50000))
            else:
                amount = Decimal(random.randint(50000, 500000))
            
            open_date = random_date(2019, 2025)
            term_months = random.choice([6, 12, 24, 36, 48, 60, 120, 240])
            planned_close = open_date + timedelta(days=term_months * 30)
            monthly_payment = (amount / term_months * Decimal('1.15')).quantize(Decimal('0.01'))
            
            credit = Credit.objects.create(
                client=client,
                open_date=open_date,
                planned_close_date=planned_close,
                principal_amount=amount,
                monthly_payment=monthly_payment,
                product_type=product,
                status=random.choices(statuses, weights=[50, 20, 20, 5, 5])[0]
            )
            credits.append(credit)
        
        return credits

    def _create_credit_states(self, credits, count):
        states_per_credit = count // len(credits) + 1
        created = 0
        
        for credit in credits:
            if created >= count:
                break
            
            current_date = credit.open_date
            remaining = float(credit.principal_amount)
            
            for _ in range(random.randint(1, states_per_credit)):
                if created >= count:
                    break
                
                overdue = remaining * random.uniform(0, 0.3) if credit.status in ['overdue', 'default'] else 0
                interest = remaining * random.uniform(0.01, 0.05)
                
                CreditState.objects.create(
                    credit=credit,
                    state_date=current_date,
                    principal_debt=Decimal(remaining).quantize(Decimal('0.01')),
                    overdue_principal=Decimal(overdue).quantize(Decimal('0.01')),
                    interest=Decimal(interest).quantize(Decimal('0.01'))
                )
                
                current_date += timedelta(days=30)
                remaining = max(0, remaining - float(credit.monthly_payment) * 0.7)
                created += 1

    def _create_payments(self, credits, count):
        payment_types = ['regular', 'early', 'partial', 'penalty']
        created = 0
        
        for credit in credits:
            if created >= count:
                break
            
            num_payments = random.randint(1, count // len(credits) + 5)
            current_date = credit.open_date + timedelta(days=30)
            
            for _ in range(num_payments):
                if created >= count:
                    break
                
                planned_date = current_date
                overdue_days = 0
                
                if random.random() > 0.7:  # 30% chance of late payment
                    overdue_days = random.randint(1, 60)
                    payment_date = planned_date + timedelta(days=overdue_days)
                else:
                    payment_date = planned_date - timedelta(days=random.randint(0, 5))
                
                amount = float(credit.monthly_payment) * random.uniform(0.8, 1.2)
                
                Payment.objects.create(
                    credit=credit,
                    payment_date=payment_date,
                    amount=Decimal(amount).quantize(Decimal('0.01')),
                    payment_type=random.choice(payment_types),
                    planned_date=planned_date,
                    min_payment=credit.monthly_payment * Decimal('0.1'),
                    overdue_days=overdue_days
                )
                
                current_date += timedelta(days=30)
                created += 1
        
        self.stdout.write(f'  Created {created} payments')

    def _create_interventions(self, clients, credits, operators, count):
        intervention_types = ['phone', 'sms', 'email', 'letter', 'visit']
        statuses = ['completed', 'no_answer', 'promise', 'refuse', 'callback']
        
        overdue_credits = [c for c in credits if c.status in ['overdue', 'default']]
        if not overdue_credits:
            overdue_credits = credits[:100]
        
        for i in range(count):
            credit = random.choice(overdue_credits)
            
            Intervention.objects.create(
                client=credit.client,
                credit=credit,
                operator=random.choice(operators),
                datetime=random_datetime_range(date(2024, 1, 1), date(2026, 1, 15)),
                intervention_type=random.choices(intervention_types, weights=[60, 20, 10, 5, 5])[0],
                status=random.choice(statuses),
                duration=random.randint(0, 600) if random.random() > 0.3 else 0,
                promise_amount=Decimal(random.randint(1000, 50000)) if random.random() > 0.7 else 0
            )
            
            if (i + 1) % 2000 == 0:
                self.stdout.write(f'  Created {i + 1} interventions...')

    def _create_assignments(self, operators, credits, count):
        overdue_credits = [c for c in credits if c.status in ['overdue', 'default', 'active']]
        today = date.today()
        
        for i in range(count):
            credit = random.choice(overdue_credits)
            operator = random.choice(operators)
            
            overdue_amount = float(credit.monthly_payment) * random.randint(1, 6)
            overdue_days = random.randint(1, 180)
            
            Assignment.objects.create(
                operator=operator,
                debtor_name=credit.client.full_name,
                credit=credit,
                overdue_amount=Decimal(overdue_amount).quantize(Decimal('0.01')),
                overdue_days=overdue_days,
                priority=random.randint(1, 5),
                assignment_date=today - timedelta(days=random.randint(0, 30))
            )

    def _create_scoring_results(self, clients, credits, count):
        segments = ['low', 'medium', 'high', 'critical']
        
        for i in range(count):
            credit = random.choice(credits)
            probability = random.uniform(0, 1)
            
            if probability < 0.25:
                segment = 'low'
            elif probability < 0.5:
                segment = 'medium'
            elif probability < 0.75:
                segment = 'high'
            else:
                segment = 'critical'
            
            ScoringResult.objects.create(
                client=credit.client,
                credit=credit,
                calculation_date=date.today() - timedelta(days=random.randint(0, 90)),
                probability=probability,
                risk_segment=segment
            )
