"""
Management command to populate dashboard data.
Creates:
- 10 Operators with realistic statistics
- 500+ Interventions with proper FK relationships
"""
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from collection_app.models import Client, Operator, Credit, Intervention


# Русские имена для операторов
OPERATOR_NAMES = [
    ('Иванов', 'Иван', 'Иванович', 'M'),
    ('Петрова', 'Анна', 'Сергеевна', 'F'),
    ('Сидорова', 'Ольга', 'Александровна', 'F'),
    ('Козлов', 'Алексей', 'Дмитриевич', 'M'),
    ('Новикова', 'Мария', 'Михайловна', 'F'),
    ('Морозов', 'Дмитрий', 'Николаевич', 'M'),
    ('Волкова', 'Елена', 'Павловна', 'F'),
    ('Соколов', 'Сергей', 'Андреевич', 'M'),
    ('Попова', 'Татьяна', 'Владимировна', 'F'),
    ('Лебедев', 'Андрей', 'Викторович', 'M'),
    ('Кузнецова', 'Наталья', 'Евгеньевна', 'F'),
    ('Смирнов', 'Михаил', 'Сергеевич', 'M'),
]


class Command(BaseCommand):
    help = 'Populate database with operators and interventions for dashboard'

    def add_arguments(self, parser):
        parser.add_argument('--operators', type=int, default=10, help='Number of operators to create')
        parser.add_argument('--interventions', type=int, default=1000, help='Number of interventions to create')
        parser.add_argument('--clear', action='store_true', help='Clear existing operators and interventions')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing operators and interventions...')
            Intervention.objects.all().delete()
            Operator.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Data cleared.'))

        # Получаем существующих клиентов и кредиты
        clients = list(Client.objects.all()[:500])
        credits = list(Credit.objects.select_related('client').all()[:500])
        
        if not clients:
            self.stdout.write(self.style.ERROR('No clients found! Run populate_db first.'))
            return
        
        if not credits:
            self.stdout.write(self.style.ERROR('No credits found! Run populate_db first.'))
            return

        self.stdout.write(f'Creating {options["operators"]} operators...')
        operators = self._create_operators(options['operators'])

        self.stdout.write(f'Creating {options["interventions"]} interventions...')
        self._create_interventions(clients, credits, operators, options['interventions'])

        self.stdout.write(self.style.SUCCESS('Dashboard data populated successfully!'))
        self.stdout.write(f'  - Operators: {len(operators)}')
        self.stdout.write(f'  - Interventions: {Intervention.objects.count()}')

    def _create_operators(self, count):
        operators = []
        roles = ['operator', 'senior_operator', 'team_lead', 'supervisor']
        specializations = ['soft', 'hard', 'legal', 'restructure', 'universal']
        statuses = ['active', 'active', 'active', 'on_call', 'break']  # Mostly active
        
        for i in range(min(count, len(OPERATOR_NAMES))):
            last_name, first_name, patronymic, gender = OPERATOR_NAMES[i]
            full_name = f'{last_name} {first_name[0]}.{patronymic[0]}.'
            
            # Реалистичная статистика оператора
            success_rate = round(random.uniform(0.45, 0.75), 2)
            avg_call_duration = random.randint(120, 240)
            total_collected = Decimal(random.randint(500000, 5000000))
            max_load = random.randint(40, 60)
            current_load = random.randint(10, max_load)
            
            op = Operator.objects.create(
                full_name=full_name,
                role=random.choice(roles),
                specialization=random.choice(specializations),
                hire_date=date.today() - timedelta(days=random.randint(90, 1000)),
                current_load=current_load,
                max_load=max_load,
                success_rate=success_rate,
                avg_call_duration=avg_call_duration,
                total_collected=total_collected,
                status=random.choice(statuses)
            )
            operators.append(op)
            self.stdout.write(f'  Created operator: {full_name}')
        
        return operators

    def _create_interventions(self, clients, credits, operators, count):
        """Создание интервенций с правильными связями"""
        intervention_types = ['phone', 'phone', 'phone', 'sms', 'email', 'letter']  # Больше звонков
        statuses = ['completed', 'no_answer', 'promise', 'refuse', 'callback']
        status_weights = [30, 35, 20, 10, 5]  # Вероятности
        
        # Создаём интервенции за последние 30 дней
        today = timezone.now()
        interventions = []
        
        # Группируем кредиты по клиентам для правильных связей
        credits_by_client = {}
        for credit in credits:
            client_id = credit.client_id
            if client_id not in credits_by_client:
                credits_by_client[client_id] = []
            credits_by_client[client_id].append(credit)
        
        for i in range(count):
            # Выбираем случайный кредит и берём его клиента (правильная связь!)
            credit = random.choice(credits)
            client = credit.client
            operator = random.choice(operators)
            
            # Случайная дата за последние 30 дней
            days_ago = random.randint(0, 30)
            hours = random.randint(9, 18)
            minutes = random.randint(0, 59)
            intervention_datetime = today - timedelta(days=days_ago, hours=random.randint(0, 8), minutes=minutes)
            intervention_datetime = intervention_datetime.replace(hour=hours, minute=minutes)
            
            intervention_type = random.choice(intervention_types)
            status = random.choices(statuses, weights=status_weights)[0]
            
            # Длительность только для звонков
            if intervention_type == 'phone':
                if status == 'no_answer':
                    duration = random.randint(5, 30)
                elif status == 'completed':
                    duration = random.randint(60, 300)
                elif status == 'promise':
                    duration = random.randint(180, 420)
                else:
                    duration = random.randint(30, 180)
            else:
                duration = 0
            
            # Обещания
            promise_amount = Decimal(0)
            promise_date = None
            if status == 'promise':
                promise_amount = Decimal(random.randint(5000, 100000))
                promise_date = (today + timedelta(days=random.randint(1, 14))).date()
            
            intervention = Intervention(
                client=client,
                credit=credit,
                operator=operator,
                datetime=intervention_datetime,
                intervention_type=intervention_type,
                status=status,
                duration=duration,
                promise_amount=promise_amount,
                promise_date=promise_date
            )
            interventions.append(intervention)
            
            if (i + 1) % 200 == 0:
                # Bulk create для производительности
                Intervention.objects.bulk_create(interventions)
                self.stdout.write(f'  Created {i + 1} interventions...')
                interventions = []
        
        # Создаём оставшиеся
        if interventions:
            Intervention.objects.bulk_create(interventions)
        
        self.stdout.write(f'  Total interventions created: {count}')
