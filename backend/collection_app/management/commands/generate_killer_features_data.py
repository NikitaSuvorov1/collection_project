"""
Генерация данных для killer features:
- ClientBehaviorProfile (психотипы)
- NextBestAction (рекомендации)
- ReturnForecast (прогнозы возврата)
- SmartScript (скрипты)
"""
import random
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from collection_app.models import (
    Client, Credit, Operator, ClientBehaviorProfile, 
    NextBestAction, SmartScript, ReturnForecast
)


class Command(BaseCommand):
    help = 'Генерирует данные для killer features'

    def handle(self, *args, **options):
        self.stdout.write('Генерация данных для killer features...')
        
        self.generate_behavior_profiles()
        self.generate_nba_recommendations()
        self.generate_return_forecasts()
        self.generate_smart_scripts()
        
        self.stdout.write(self.style.SUCCESS('Данные для killer features созданы!'))

    def generate_behavior_profiles(self):
        """Генерация поведенческих профилей для всех клиентов"""
        clients = Client.objects.all()
        
        psychotypes = ['forgetful', 'unwilling', 'unable', 'toxic', 'cooperative']
        psychotype_weights = [0.15, 0.25, 0.35, 0.10, 0.15]
        
        channels = ['phone', 'sms', 'whatsapp', 'email']
        strategies = ['continue', 'restructure', 'soft_collection', 'legal', 'write_off']
        
        for client in clients:
            psychotype = random.choices(psychotypes, psychotype_weights)[0]
            
            # Коэффициенты на основе психотипа
            if psychotype == 'cooperative':
                payment_discipline = random.uniform(0.6, 0.9)
                total_contacts = random.randint(5, 15)
                successful = int(total_contacts * random.uniform(0.7, 0.95))
            elif psychotype == 'forgetful':
                payment_discipline = random.uniform(0.4, 0.7)
                total_contacts = random.randint(3, 10)
                successful = int(total_contacts * random.uniform(0.5, 0.8))
            elif psychotype == 'unable':
                payment_discipline = random.uniform(0.2, 0.5)
                total_contacts = random.randint(5, 20)
                successful = int(total_contacts * random.uniform(0.6, 0.85))
            elif psychotype == 'unwilling':
                payment_discipline = random.uniform(0.1, 0.4)
                total_contacts = random.randint(5, 25)
                successful = int(total_contacts * random.uniform(0.3, 0.6))
            else:  # toxic
                payment_discipline = random.uniform(0.0, 0.2)
                total_contacts = random.randint(10, 30)
                successful = int(total_contacts * random.uniform(0.1, 0.4))
            
            # Триггеры риска - булевы значения
            income_dropped = random.random() > 0.7
            job_changed = random.random() > 0.85
            multiple_credits = random.random() > 0.6
            activity_dropped = random.random() > 0.8
            
            profile, created = ClientBehaviorProfile.objects.update_or_create(
                client=client,
                defaults={
                    'psychotype': psychotype,
                    'psychotype_confidence': round(random.uniform(0.6, 0.95), 2),
                    'payment_discipline_score': round(payment_discipline, 2),
                    'avg_days_overdue': random.randint(5, 90),
                    'payments_on_time_ratio': round(random.uniform(0.1, 0.8), 2),
                    'preferred_channel': random.choice(channels),
                    'best_contact_hour': random.randint(9, 20),
                    'best_contact_day': random.randint(0, 4),  # 0=Пн, 4=Пт
                    'job_changed_recently': job_changed,
                    'income_dropped': income_dropped,
                    'activity_dropped': activity_dropped,
                    'multiple_credits': multiple_credits,
                    'total_contacts': total_contacts,
                    'successful_contacts': successful,
                    'promises_kept_ratio': round(random.uniform(0.2, 0.8), 2),
                    'avg_promise_delay': round(random.uniform(1, 10), 1),
                    'return_probability': round(random.uniform(0.2, 0.9), 2),
                    'expected_return_days': random.randint(7, 90),
                    'strategic_recommendation': random.choice(strategies),
                }
            )
        
        self.stdout.write(f'  ✓ Создано {clients.count()} поведенческих профилей')

    def generate_nba_recommendations(self):
        """Генерация NBA рекомендаций"""
        credits = Credit.objects.filter(status='overdue').select_related('client')
        
        channels = ['phone', 'sms', 'whatsapp', 'email', 'push']
        scenarios = ['soft_reminder', 'firm_demand', 'empathy', 'restructure_offer', 'discount_offer', 'payment_holiday', 'last_warning']
        offers = ['none', 'discount_10', 'discount_20', 'discount_50', 'restructure_6m', 'restructure_12m', 'holiday_1m', 'holiday_3m']
        
        scenario_reasoning = {
            'soft_reminder': 'Клиент забывчивый — мягкое напоминание будет эффективным',
            'firm_demand': 'Стандартный запрос оплаты для клиента со средним риском',
            'empathy': 'Клиент в сложной ситуации — используйте эмпатичный подход',
            'restructure_offer': 'Клиент хочет платить, но не может — предложите рассрочку',
            'discount_offer': 'Предложение скидки может мотивировать к быстрой оплате',
            'payment_holiday': 'Клиенту нужна передышка — предложите каникулы',
            'last_warning': 'Клиент игнорирует контакты — предупреждение о правовых последствиях',
        }
        
        for credit in credits:
            # Генерируем 1-2 рекомендации на кредит
            for _ in range(random.randint(1, 2)):
                scenario = random.choice(scenarios)
                channel = random.choice(channels)
                
                # Если есть профиль — используем его канал
                profile = getattr(credit.client, 'behavior_profile', None)
                if profile:
                    channel = profile.preferred_channel
                
                nba = NextBestAction.objects.create(
                    client=credit.client,
                    credit=credit,
                    recommended_datetime=timezone.now() + timedelta(hours=random.randint(1, 48)),
                    recommended_channel=channel,
                    recommended_scenario=scenario,
                    recommended_offer=random.choice(offers),
                    max_discount_percent=random.choice([0, 5, 10, 15, 20]),
                    urgency=random.randint(1, 5),
                    confidence_score=round(random.uniform(0.5, 0.95), 2),
                    reasoning=scenario_reasoning.get(scenario, 'Рекомендация на основе анализа данных'),
                    status='pending',
                )
        
        self.stdout.write(f'  ✓ Создано {NextBestAction.objects.count()} NBA рекомендаций')

    def generate_return_forecasts(self):
        """Генерация прогнозов возврата"""
        credits = Credit.objects.filter(status='overdue').select_related('client')
        
        # Должны соответствовать RECOMMENDATION_CHOICES модели
        recommendations = ['continue_soft', 'continue_hard', 'restructure', 'legal', 'sell', 'write_off']
        
        for credit in credits:
            # Вероятность возврата зависит от психотипа
            profile = getattr(credit.client, 'behavior_profile', None)
            
            if profile:
                psychotype = profile.psychotype
                if psychotype == 'cooperative':
                    base_prob = random.uniform(0.7, 0.95)
                elif psychotype == 'forgetful':
                    base_prob = random.uniform(0.5, 0.8)
                elif psychotype == 'unable':
                    base_prob = random.uniform(0.3, 0.6)
                elif psychotype == 'unwilling':
                    base_prob = random.uniform(0.15, 0.4)
                else:  # toxic
                    base_prob = random.uniform(0.05, 0.2)
            else:
                base_prob = random.uniform(0.3, 0.7)
            
            # Получаем сумму долга
            state = credit.states.order_by('-state_date').first()
            debt = float(state.principal_debt) if state else 100000
            
            forecast = ReturnForecast.objects.create(
                credit=credit,
                return_probability=round(base_prob, 2),
                partial_return_probability=round(min(base_prob + 0.2, 0.95), 2),
                expected_return_amount=Decimal(str(round(debt * base_prob, 2))),
                expected_return_days=random.randint(14, 120),
                recommendation=random.choice(recommendations),
                recommendation_confidence=round(random.uniform(0.5, 0.9), 2),
                positive_factors=['Стабильный доход', 'Отвечает на звонки', 'Делает частичные платежи'][:random.randint(1, 3)],
                negative_factors=['Высокая долговая нагрузка', 'Множественные кредиты', 'Падение дохода'][:random.randint(0, 2)],
                npv_continue=Decimal(str(round(debt * 0.5, 2))),
                npv_sell=Decimal(str(round(debt * 0.15, 2))),
                npv_write_off=Decimal(str(round(-debt * 0.8, 2))),
            )
        
        self.stdout.write(f'  ✓ Создано {ReturnForecast.objects.count()} прогнозов возврата')

    def generate_smart_scripts(self):
        """Генерация умных скриптов"""
        scripts_data = [
            {
                'name': 'Мягкое напоминание для забывчивых',
                'target_psychotype': 'forgetful',
                'scenario': 'soft_reminder',
                'opening_phrases': [
                    'Добрый день, {client_name}! Напоминаю о платеже по кредиту. Возможно, вы просто забыли?',
                    'Здравствуйте! Беспокоит банк по поводу небольшой просрочки. Уверен, это недоразумение.',
                ],
                'key_phrases': [
                    'Понимаю, что это просто упущение',
                    'Давайте вместе посмотрим, как удобнее оплатить',
                    'Могу прямо сейчас отправить ссылку для оплаты',
                ],
                'objection_handlers': {
                    'забыл': ['Ничего страшного! Давайте прямо сейчас оформим платёж?'],
                    'нет денег': ['Когда ожидаете поступление? Можем договориться на эту дату.'],
                },
                'closing_phrases': [
                    'Отлично, тогда жду оплату до {date}. Хорошего дня!',
                    'Спасибо! Если будут вопросы — звоните.',
                ],
                'success_rate': 0.72,
            },
            {
                'name': 'Эмпатичный подход для неспособных платить',
                'target_psychotype': 'unable',
                'scenario': 'empathy',
                'opening_phrases': [
                    'Понимаю, что сейчас непростая ситуация с платежами. У нас есть программа помощи.',
                    'Добрый день! Вижу, что возникли сложности. Давайте вместе найдём решение.',
                ],
                'key_phrases': [
                    'Мы готовы пойти навстречу',
                    'Главное — не накапливать долг',
                    'Есть несколько вариантов реструктуризации',
                ],
                'objection_handlers': {
                    'нет денег': ['Понимаю. Какую сумму смогли бы внести сейчас? Даже частичная оплата поможет.'],
                    'потерял работу': ['Сочувствую. У нас есть программа каникул — можем отложить платежи.'],
                },
                'closing_phrases': [
                    'Давайте подберём комфортный график. Вы не одиноки в этой ситуации.',
                    'Спасибо за честный разговор. Оформлю заявку на реструктуризацию.',
                ],
                'success_rate': 0.68,
            },
            {
                'name': 'Работа с кооперативными клиентами',
                'target_psychotype': 'cooperative',
                'scenario': 'soft_reminder',
                'opening_phrases': [
                    'Добрый день! Знаю, что вы ответственный клиент. Звоню по поводу платежа.',
                ],
                'key_phrases': [
                    'Ценю, что вы всегда на связи',
                    'Понимаю, что ситуации бывают разные',
                ],
                'objection_handlers': {
                    'перезвоните': ['Конечно! Какое время будет удобным?'],
                },
                'closing_phrases': [
                    'Спасибо за понимание! Ждём оплату и всегда на связи.',
                ],
                'success_rate': 0.82,
            },
            {
                'name': 'Предложение реструктуризации',
                'target_psychotype': 'any',
                'scenario': 'restructure_offer',
                'opening_phrases': [
                    'Добрый день! У меня для вас хорошие новости — есть возможность снизить платёж.',
                ],
                'key_phrases': [
                    'Можем снизить ежемесячный платёж в 1.5 раза',
                    'Рассрочка на более длительный срок',
                    'Без штрафов за просрочку при согласии',
                ],
                'objection_handlers': {
                    'не верю': ['Это официальная программа банка. Могу отправить условия в письменном виде.'],
                    'подумаю': ['Конечно! Только учтите, что предложение действует до конца недели.'],
                },
                'closing_phrases': [
                    'Оформляю заявку. Новый график придёт на почту.',
                ],
                'success_rate': 0.65,
            },
            {
                'name': 'Жёсткое требование',
                'target_psychotype': 'unwilling',
                'scenario': 'firm_demand',
                'opening_phrases': [
                    'Добрый день. Звоню по поводу задолженности, которая требует немедленного погашения.',
                ],
                'key_phrases': [
                    'Долг продолжает расти каждый день',
                    'Необходимо решить вопрос сегодня',
                    'При отсутствии оплаты будем вынуждены передать дело юристам',
                ],
                'objection_handlers': {
                    'не буду платить': ['Понимаю вашу позицию, но это приведёт к серьёзным последствиям.'],
                    'подавайте в суд': ['Это крайняя мера. Давайте сначала попробуем договориться.'],
                },
                'closing_phrases': [
                    'Жду оплату до конца дня. В противном случае будем вынуждены принять меры.',
                ],
                'success_rate': 0.45,
            },
            {
                'name': 'Предложение скидки',
                'target_psychotype': 'any',
                'scenario': 'discount_offer',
                'opening_phrases': [
                    'Добрый день! У меня специальное предложение для вас.',
                ],
                'key_phrases': [
                    'При оплате в течение 3 дней — скидка 10%',
                    'Можем списать часть штрафов',
                    'Акция действует ограниченное время',
                ],
                'objection_handlers': {
                    'мало': ['Это максимум, что мы можем предложить на данный момент.'],
                    'подумаю': ['Предложение действует только сегодня.'],
                },
                'closing_phrases': [
                    'Фиксирую скидку. Жду оплату!',
                ],
                'success_rate': 0.58,
            },
        ]
        
        for data in scripts_data:
            SmartScript.objects.get_or_create(
                name=data['name'],
                defaults={
                    'target_psychotype': data['target_psychotype'],
                    'scenario': data['scenario'],
                    'opening_phrases': data['opening_phrases'],
                    'key_phrases': data['key_phrases'],
                    'objection_handlers': data['objection_handlers'],
                    'closing_phrases': data['closing_phrases'],
                    'times_used': random.randint(100, 1000),
                    'success_count': random.randint(50, 500),
                    'success_rate': data['success_rate'],
                    'avg_ptp_amount': Decimal(str(random.randint(5000, 50000))),
                    'is_active': True,
                }
            )
        
        self.stdout.write(f'  ✓ Создано {SmartScript.objects.count()} умных скриптов')
