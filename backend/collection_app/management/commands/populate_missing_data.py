"""
Management command to populate missing database entities.
Creates data for:
- Payments
- Interventions  
- Assignments
- ScoringResults
- CreditApplications
- ComplianceAlerts
- ConversationAnalysis
"""
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from collection_app.models import (
    Client, Operator, Credit, CreditState, Payment,
    Intervention, Assignment, ScoringResult, CreditApplication,
    ComplianceAlert, ConversationAnalysis
)


def random_datetime_range(start_date, end_date):
    delta = (end_date - start_date).days
    random_days = random.randint(0, max(delta, 1))
    random_time = timedelta(hours=random.randint(8, 18), minutes=random.randint(0, 59))
    return datetime.combine(start_date + timedelta(days=random_days), datetime.min.time()) + random_time


class Command(BaseCommand):
    help = 'Populate missing database entities'

    def handle(self, *args, **options):
        # Get existing data
        clients = list(Client.objects.all())
        operators = list(Operator.objects.all())
        credits = list(Credit.objects.all())

        if not clients or not operators or not credits:
            self.stdout.write(self.style.ERROR('Need base data first. Run populate_db command.'))
            return

        self.stdout.write(f'Found {len(clients)} clients, {len(operators)} operators, {len(credits)} credits')

        # Check what's missing and create
        payment_count = Payment.objects.count()
        if payment_count < 10000:
            self.stdout.write(f'Creating payments (have {payment_count}, need 10000)...')
            self._create_payments(credits, 10000 - payment_count)

        intervention_count = Intervention.objects.count()
        if intervention_count < 10000:
            self.stdout.write(f'Creating interventions (have {intervention_count}, need 10000)...')
            self._create_interventions(clients, credits, operators, 10000 - intervention_count)

        assignment_count = Assignment.objects.count()
        if assignment_count < 3000:
            self.stdout.write(f'Creating assignments (have {assignment_count}, need 3000)...')
            self._create_assignments(operators, credits, 3000 - assignment_count)

        scoring_count = ScoringResult.objects.count()
        if scoring_count < 2000:
            self.stdout.write(f'Creating scoring results (have {scoring_count}, need 2000)...')
            self._create_scoring_results(clients, credits, 2000 - scoring_count)

        application_count = CreditApplication.objects.count()
        if application_count < 500:
            self.stdout.write(f'Creating credit applications (have {application_count}, need 500)...')
            self._create_credit_applications(clients, 500 - application_count)

        compliance_count = ComplianceAlert.objects.count()
        if compliance_count < 200:
            self.stdout.write(f'Creating compliance alerts (have {compliance_count}, need 200)...')
            # Need interventions for compliance alerts
            interventions = list(Intervention.objects.all())
            if interventions:
                self._create_compliance_alerts(operators, interventions, 200 - compliance_count)
            else:
                self.stdout.write(self.style.WARNING('No interventions found for compliance alerts'))

        conversation_count = ConversationAnalysis.objects.count()
        if conversation_count < 500:
            self.stdout.write(f'Creating conversation analyses (have {conversation_count}, need 500)...')
            # Need interventions for conversation analysis
            interventions = list(Intervention.objects.all())
            if interventions:
                self._create_conversation_analyses(interventions, 500 - conversation_count)
            else:
                self.stdout.write(self.style.WARNING('No interventions found for conversation analyses'))

        # Fill remaining CreditStates if needed
        state_count = CreditState.objects.count()
        if state_count < 5000:
            self.stdout.write(f'Creating credit states (have {state_count}, need 5000)...')
            self._create_credit_states(credits, 5000 - state_count)

        self.stdout.write(self.style.SUCCESS('Missing data populated successfully!'))

    def _create_payments(self, credits, count):
        payment_types = ['regular', 'early', 'partial', 'penalty']
        created = 0
        batch_size = 1000
        payments_batch = []

        for credit in credits:
            if created >= count:
                break

            num_payments = random.randint(1, max(1, count // len(credits) + 5))
            current_date = credit.open_date + timedelta(days=30)

            for _ in range(num_payments):
                if created >= count:
                    break

                planned_date = current_date
                overdue_days = 0

                if random.random() > 0.7:
                    overdue_days = random.randint(1, 60)
                    payment_date = planned_date + timedelta(days=overdue_days)
                else:
                    payment_date = planned_date - timedelta(days=random.randint(0, 5))

                amount = float(credit.monthly_payment) * random.uniform(0.8, 1.2)

                payments_batch.append(Payment(
                    credit=credit,
                    payment_date=payment_date,
                    amount=Decimal(amount).quantize(Decimal('0.01')),
                    payment_type=random.choice(payment_types),
                    planned_date=planned_date,
                    min_payment=credit.monthly_payment * Decimal('0.1'),
                    overdue_days=overdue_days
                ))

                current_date += timedelta(days=30)
                created += 1

                if len(payments_batch) >= batch_size:
                    Payment.objects.bulk_create(payments_batch)
                    payments_batch = []
                    self.stdout.write(f'  Created {created} payments...')

        if payments_batch:
            Payment.objects.bulk_create(payments_batch)

        self.stdout.write(f'  Total created: {created} payments')

    def _create_interventions(self, clients, credits, operators, count):
        intervention_types = ['phone', 'sms', 'email', 'letter', 'visit']
        statuses = ['completed', 'no_answer', 'promise', 'refuse', 'callback']
        batch_size = 1000
        interventions_batch = []

        overdue_credits = [c for c in credits if c.status in ['overdue', 'default']]
        if not overdue_credits:
            overdue_credits = credits[:100]

        for i in range(count):
            credit = random.choice(overdue_credits)

            interventions_batch.append(Intervention(
                client=credit.client,
                credit=credit,
                operator=random.choice(operators),
                datetime=random_datetime_range(date(2024, 1, 1), date(2026, 1, 15)),
                intervention_type=random.choices(intervention_types, weights=[60, 20, 10, 5, 5])[0],
                status=random.choice(statuses),
                duration=random.randint(0, 600) if random.random() > 0.3 else 0,
                promise_amount=Decimal(random.randint(1000, 50000)) if random.random() > 0.7 else 0
            ))

            if len(interventions_batch) >= batch_size:
                Intervention.objects.bulk_create(interventions_batch)
                interventions_batch = []
                self.stdout.write(f'  Created {i + 1} interventions...')

        if interventions_batch:
            Intervention.objects.bulk_create(interventions_batch)

        self.stdout.write(f'  Total created: {count} interventions')

    def _create_assignments(self, operators, credits, count):
        batch_size = 500
        assignments_batch = []
        overdue_credits = [c for c in credits if c.status in ['overdue', 'default', 'active']]
        today = date.today()

        for i in range(count):
            credit = random.choice(overdue_credits)
            operator = random.choice(operators)

            overdue_amount = float(credit.monthly_payment) * random.randint(1, 6)
            overdue_days = random.randint(1, 180)

            assignments_batch.append(Assignment(
                operator=operator,
                debtor_name=credit.client.full_name,
                credit=credit,
                overdue_amount=Decimal(overdue_amount).quantize(Decimal('0.01')),
                overdue_days=overdue_days,
                priority=random.randint(1, 5),
                assignment_date=today - timedelta(days=random.randint(0, 30))
            ))

            if len(assignments_batch) >= batch_size:
                Assignment.objects.bulk_create(assignments_batch)
                assignments_batch = []
                self.stdout.write(f'  Created {i + 1} assignments...')

        if assignments_batch:
            Assignment.objects.bulk_create(assignments_batch)

        self.stdout.write(f'  Total created: {count} assignments')

    def _create_scoring_results(self, clients, credits, count):
        segments = ['low', 'medium', 'high', 'critical']
        batch_size = 500
        scoring_batch = []

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

            scoring_batch.append(ScoringResult(
                client=credit.client,
                credit=credit,
                calculation_date=date.today() - timedelta(days=random.randint(0, 90)),
                probability=probability,
                risk_segment=segment
            ))

            if len(scoring_batch) >= batch_size:
                ScoringResult.objects.bulk_create(scoring_batch)
                scoring_batch = []
                self.stdout.write(f'  Created {i + 1} scoring results...')

        if scoring_batch:
            ScoringResult.objects.bulk_create(scoring_batch)

        self.stdout.write(f'  Total created: {count} scoring results')

    def _create_credit_applications(self, clients, count):
        """Create credit applications."""
        statuses = ['pending', 'approved', 'rejected', 'cancelled']
        product_types = ['consumer', 'mortgage', 'car', 'credit_card', 'microloan']
        decision_reasons = [
            'Хорошая кредитная история',
            'Стабильный доход',
            'Низкий DTI',
            'Высокий риск невозврата',
            'Недостаточный доход',
            'Плохая кредитная история',
            'Требуется дополнительная проверка',
            None
        ]
        batch_size = 100
        applications_batch = []

        for i in range(count):
            client = random.choice(clients)
            status = random.choices(statuses, weights=[20, 50, 25, 5])[0]
            product = random.choice(product_types)

            # Amount depends on product type
            if product == 'mortgage':
                amount = Decimal(random.randint(2000000, 15000000))
            elif product == 'car':
                amount = Decimal(random.randint(500000, 3000000))
            elif product == 'microloan':
                amount = Decimal(random.randint(10000, 100000))
            else:
                amount = Decimal(random.randint(50000, 1000000))

            application_date = date.today() - timedelta(days=random.randint(0, 365))
            
            decision_date = None
            decision_reason = None
            if status != 'pending':
                decision_date = application_date + timedelta(days=random.randint(1, 14))
                decision_reason = random.choice(decision_reasons)

            # CreditApplication model: client, amount, approved_probability (created_at is auto)
            applications_batch.append(CreditApplication(
                client=client,
                amount=amount,
                approved_probability=random.uniform(0.1, 0.95) if random.random() > 0.2 else None
            ))

            if len(applications_batch) >= batch_size:
                CreditApplication.objects.bulk_create(applications_batch)
                applications_batch = []
                self.stdout.write(f'  Created {i + 1} applications...')

        if applications_batch:
            CreditApplication.objects.bulk_create(applications_batch)

        self.stdout.write(f'  Total created: {count} credit applications')

    def _create_compliance_alerts(self, operators, interventions, count):
        """Create compliance alerts linked to interventions."""
        # Match model ALERT_TYPE_CHOICES
        alert_types = ['pressure', 'threat', 'disclosure', 'timing', 'frequency', 'script_deviation', 'prohibited_words', 'rudeness']
        # Match model SEVERITY_CHOICES
        severities = ['info', 'warning', 'critical', 'violation']
        # Match model STATUS_CHOICES
        statuses = ['new', 'reviewed', 'confirmed', 'false_positive', 'escalated']
        
        descriptions = {
            'pressure': [
                'Чрезмерное давление на должника',
                'Многократные звонки за короткий период',
                'Агрессивный тон общения'
            ],
            'threat': [
                'Использование угроз в разговоре',
                'Упоминание незаконных последствий',
                'Угрозы передачей дела в суд без оснований'
            ],
            'disclosure': [
                'Разглашение информации третьим лицам',
                'Обсуждение долга с родственниками без согласия',
                'Нарушение конфиденциальности'
            ],
            'timing': [
                'Звонок в неразрешённое время',
                'Контакт в выходной день',
                'Звонок поздно вечером'
            ],
            'frequency': [
                'Превышение лимита звонков в день',
                'Слишком частые контакты',
                'Более 2 звонков за день'
            ],
            'script_deviation': [
                'Отклонение от утверждённого скрипта',
                'Пропуск обязательных фраз',
                'Несоблюдение структуры разговора'
            ],
            'prohibited_words': [
                'Использование запрещённых слов',
                'Некорректная лексика',
                'Оскорбительные выражения'
            ],
            'rudeness': [
                'Грубость в общении',
                'Повышение голоса на клиента',
                'Пренебрежительный тон'
            ]
        }
        
        batch_size = 50
        alerts_batch = []
        # Use random sample of interventions
        selected_interventions = random.sample(interventions, min(count, len(interventions)))

        for i in range(min(count, len(selected_interventions))):
            intervention = selected_interventions[i]
            alert_type = random.choice(alert_types)
            severity = random.choices(severities, weights=[40, 35, 20, 5])[0]
            status = random.choices(statuses, weights=[30, 25, 25, 10, 10])[0]
            
            alerts_batch.append(ComplianceAlert(
                intervention=intervention,
                operator=intervention.operator,
                alert_type=alert_type,
                severity=severity,
                description=random.choice(descriptions[alert_type]),
                evidence=f"[{random.randint(0, 300)}s] Фрагмент разговора с нарушением",
                timestamp_in_call=random.randint(10, 600) if random.random() > 0.3 else None,
                status=status
            ))

            if len(alerts_batch) >= batch_size:
                ComplianceAlert.objects.bulk_create(alerts_batch)
                alerts_batch = []
                self.stdout.write(f'  Created {i + 1} alerts...')

        if alerts_batch:
            ComplianceAlert.objects.bulk_create(alerts_batch)

        self.stdout.write(f'  Total created: {min(count, len(selected_interventions))} compliance alerts')

    def _create_conversation_analyses(self, interventions, count):
        """Create conversation analyses linked to interventions (OneToOne)."""
        # Match model SENTIMENT_CHOICES
        sentiments = ['very_negative', 'negative', 'neutral', 'positive', 'very_positive']
        
        effective_phrases_options = [
            ['Я понимаю вашу ситуацию', 'Давайте найдём решение вместе'],
            ['Мы можем предложить рассрочку', 'Это поможет избежать дополнительных расходов'],
            ['Спасибо за готовность к диалогу', 'Мы ценим ваше сотрудничество'],
            ['Какой вариант вам удобнее?', 'Давайте обсудим возможности'],
        ]
        
        ineffective_phrases_options = [
            [],
            ['Вы обязаны оплатить немедленно'],
            ['Это ваша последняя возможность'],
            ['Мы будем вынуждены принять меры'],
        ]
        
        compliance_violations_options = [
            [],
            [],
            [],
            ['Превышение времени разговора'],
            ['Некорректное обращение'],
        ]
        
        batch_size = 100
        analyses_batch = []
        
        # Get interventions that don't already have analysis (OneToOne)
        existing_ids = set(ConversationAnalysis.objects.values_list('intervention_id', flat=True))
        available_interventions = [i for i in interventions if i.id not in existing_ids]
        
        if not available_interventions:
            self.stdout.write(self.style.WARNING('All interventions already have analyses'))
            return
        
        # Use random sample of available interventions
        selected_interventions = random.sample(available_interventions, min(count, len(available_interventions)))

        for i, intervention in enumerate(selected_interventions):
            sentiment = random.choices(sentiments, weights=[5, 20, 45, 25, 5])[0]
            
            ptp_achieved = random.random() > 0.6
            ptp_amount = Decimal(random.randint(5000, 50000)) if ptp_achieved else Decimal('0')
            
            analyses_batch.append(ConversationAnalysis(
                intervention=intervention,
                transcript=f"Оператор: Добрый день, это служба взыскания...\nКлиент: Да, слушаю...",
                client_sentiment=sentiment,
                operator_sentiment=random.choices(sentiments, weights=[2, 5, 60, 30, 3])[0],
                effective_phrases=random.choice(effective_phrases_options),
                ineffective_phrases=random.choice(ineffective_phrases_options),
                compliance_score=random.uniform(0.7, 1.0),
                compliance_violations=random.choice(compliance_violations_options),
                talk_ratio=random.uniform(0.5, 2.0),
                interruption_count=random.randint(0, 5),
                silence_ratio=random.uniform(0.05, 0.25),
                ptp_achieved=ptp_achieved,
                ptp_amount=ptp_amount
            ))

            if len(analyses_batch) >= batch_size:
                ConversationAnalysis.objects.bulk_create(analyses_batch)
                analyses_batch = []
                self.stdout.write(f'  Created {i + 1} analyses...')

        if analyses_batch:
            ConversationAnalysis.objects.bulk_create(analyses_batch)

        self.stdout.write(f'  Total created: {len(selected_interventions)} conversation analyses')

    def _create_credit_states(self, credits, count):
        """Create additional credit states."""
        batch_size = 500
        states_batch = []
        created = 0

        for credit in credits:
            if created >= count:
                break

            num_states = random.randint(1, min(10, count - created + 1))
            current_date = credit.open_date
            remaining = float(credit.principal_amount)

            for _ in range(num_states):
                if created >= count:
                    break

                # Model fields: credit, state_date, principal_debt, overdue_principal, interest
                overdue_pct = random.uniform(0, 0.3) if credit.status in ['overdue', 'default'] else random.uniform(0, 0.05)
                interest_pct = random.uniform(0.01, 0.05)

                states_batch.append(CreditState(
                    credit=credit,
                    state_date=current_date,
                    principal_debt=Decimal(remaining).quantize(Decimal('0.01')),
                    overdue_principal=Decimal(remaining * overdue_pct).quantize(Decimal('0.01')),
                    interest=Decimal(remaining * interest_pct).quantize(Decimal('0.01'))
                ))

                current_date += timedelta(days=30)
                remaining = max(0, remaining - float(credit.monthly_payment) * 0.7)
                created += 1

                if len(states_batch) >= batch_size:
                    CreditState.objects.bulk_create(states_batch)
                    states_batch = []
                    self.stdout.write(f'  Created {created} credit states...')

        if states_batch:
            CreditState.objects.bulk_create(states_batch)

        self.stdout.write(f'  Total created: {created} credit states')
