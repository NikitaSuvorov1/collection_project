from django.db import models
from django.contrib.auth.models import User


class Operator(models.Model):
    """Оператор (50 записей)"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField('ФИО оператора', max_length=200)
    role = models.CharField('Роль / группа', max_length=100, default='operator')
    hire_date = models.DateField('Дата трудоустройства', null=True, blank=True)
    current_load = models.IntegerField('Текущая нагрузка', default=0)
    
    STATUS_CHOICES = [
        ('active', 'Активен'),
        ('break', 'Перерыв'),
        ('offline', 'Не в сети'),
        ('on_call', 'На звонке'),
    ]
    status = models.CharField('Статус оператора', max_length=20, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = 'Оператор'
        verbose_name_plural = 'Операторы'


class Client(models.Model):
    """Клиент (5000 записей)"""
    full_name = models.CharField('ФИО', max_length=300)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    
    GENDER_CHOICES = [('M', 'Мужской'), ('F', 'Женский')]
    gender = models.CharField('Пол', max_length=1, choices=GENDER_CHOICES, default='M')
    
    MARITAL_CHOICES = [
        ('single', 'Холост/Не замужем'),
        ('married', 'Женат/Замужем'),
        ('divorced', 'Разведён(а)'),
        ('widowed', 'Вдовец/Вдова'),
    ]
    marital_status = models.CharField('Семейное положение', max_length=20, choices=MARITAL_CHOICES, default='single')
    
    EMPLOYMENT_CHOICES = [
        ('employed', 'Работает'),
        ('self_employed', 'Самозанятый'),
        ('unemployed', 'Безработный'),
        ('retired', 'Пенсионер'),
        ('student', 'Студент'),
    ]
    employment = models.CharField('Занятость', max_length=20, choices=EMPLOYMENT_CHOICES, default='employed')
    
    employer_name = models.CharField('Место работы', max_length=300, blank=True)
    position = models.CharField('Должность', max_length=200, blank=True)
    income = models.DecimalField('Доход', max_digits=12, decimal_places=2, default=0)
    children_count = models.IntegerField('Количество детей', default=0)
    city = models.CharField('Город проживания', max_length=200, blank=True)
    region = models.CharField('Регион проживания', max_length=200, blank=True)
    phone_mobile = models.CharField('Телефон (мобильный)', max_length=32, blank=True)
    phone_work = models.CharField('Телефон (рабочий)', max_length=32, blank=True)
    phone_home = models.CharField('Телефон (домашний)', max_length=32, blank=True)
    monthly_expenses = models.DecimalField('Ежемесячные расходы', max_digits=12, decimal_places=2, default=0)
    
    CATEGORY_CHOICES = [
        ('standard', 'Стандартный'),
        ('vip', 'VIP'),
        ('problem', 'Проблемный'),
        ('new', 'Новый'),
    ]
    category = models.CharField('Категория клиента', max_length=20, choices=CATEGORY_CHOICES, default='standard')
    created_at = models.DateTimeField('Дата добавления', auto_now_add=True, null=True)

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'


class Credit(models.Model):
    """Кредит (700 записей)"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='credits', verbose_name='Клиент')
    open_date = models.DateField('Дата открытия кредита')
    planned_close_date = models.DateField('Плановая дата закрытия', null=True, blank=True)
    principal_amount = models.DecimalField('Взятая сумма', max_digits=12, decimal_places=2)
    monthly_payment = models.DecimalField('Ежемесячный платёж', max_digits=12, decimal_places=2, default=0)
    interest_rate = models.DecimalField('Процентная ставка', max_digits=5, decimal_places=2, default=0)
    
    PRODUCT_CHOICES = [
        ('consumer', 'Потребительский'),
        ('mortgage', 'Ипотека'),
        ('car', 'Автокредит'),
        ('credit_card', 'Кредитная карта'),
        ('microloan', 'Микрозайм'),
    ]
    product_type = models.CharField('Тип кредитного продукта', max_length=20, choices=PRODUCT_CHOICES, default='consumer')
    
    STATUS_CHOICES = [
        ('active', 'Активен'),
        ('closed', 'Закрыт'),
        ('overdue', 'Просрочен'),
        ('default', 'Дефолт'),
        ('restructured', 'Реструктурирован'),
    ]
    status = models.CharField('Статус кредита', max_length=20, choices=STATUS_CHOICES, default='active')
    actuality_date = models.DateField('Дата актуальности', null=True, blank=True)

    def __str__(self):
        return f"Кредит #{self.id} - {self.client.full_name}"

    class Meta:
        verbose_name = 'Кредит'
        verbose_name_plural = 'Кредиты'


class CreditState(models.Model):
    """Состояние кредита (5000 записей)"""
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name='states', verbose_name='Кредит')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='credit_states', verbose_name='Клиент', null=True, blank=True)
    state_date = models.DateField('Дата состояния')
    planned_payment_date = models.DateField('Плановая дата платежа', null=True, blank=True)
    principal_debt = models.DecimalField('Основной долг', max_digits=12, decimal_places=2, default=0)
    overdue_principal = models.DecimalField('Просроченный основной долг', max_digits=12, decimal_places=2, default=0)
    interest = models.DecimalField('Проценты', max_digits=12, decimal_places=2, default=0)
    overdue_interest = models.DecimalField('Просроченные проценты', max_digits=12, decimal_places=2, default=0)
    penalties = models.DecimalField('Штрафы', max_digits=12, decimal_places=2, default=0)
    overdue_start_date = models.DateField('Дата начала просрочки', null=True, blank=True)
    overdue_days = models.IntegerField('Длительность просрочки (дней)', default=0)
    overdue_close_date = models.DateField('Дата закрытия просрочки', null=True, blank=True)

    def __str__(self):
        return f"Состояние кредита #{self.credit_id} на {self.state_date}"

    class Meta:
        verbose_name = 'Состояние кредита'
        verbose_name_plural = 'Состояния кредитов'


class Payment(models.Model):
    """Платёж (10000 записей)"""
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name='payments', verbose_name='Кредит')
    payment_date = models.DateField('Дата платежа')
    amount = models.DecimalField('Сумма платежа', max_digits=12, decimal_places=2)
    
    TYPE_CHOICES = [
        ('regular', 'Регулярный'),
        ('early', 'Досрочный'),
        ('partial', 'Частичный'),
        ('penalty', 'Штраф'),
    ]
    payment_type = models.CharField('Тип платежа', max_length=20, choices=TYPE_CHOICES, default='regular')
    
    planned_date = models.DateField('Плановая дата платежа', null=True, blank=True)
    min_payment = models.DecimalField('Минимальный платёж', max_digits=12, decimal_places=2, default=0)
    overdue_days = models.IntegerField('Просрочка по платежу (дней)', default=0)
    actuality_date = models.DateField('Дата актуальности', null=True, blank=True)

    def __str__(self):
        return f"Платёж #{self.id} - {self.amount} руб."

    class Meta:
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'


class Intervention(models.Model):
    """Воздействие по кредиту (10000 записей)"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='interventions', verbose_name='Клиент')
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name='interventions', verbose_name='Кредит')
    operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Оператор')
    datetime = models.DateTimeField('Дата и время воздействия')
    
    TYPE_CHOICES = [
        ('phone', 'Звонок'),
        ('sms', 'СМС'),
        ('email', 'Email'),
        ('letter', 'Письмо'),
        ('visit', 'Визит'),
    ]
    intervention_type = models.CharField('Тип воздействия', max_length=20, choices=TYPE_CHOICES, default='phone')
    
    STATUS_CHOICES = [
        ('completed', 'Завершено'),
        ('no_answer', 'Не дозвон'),
        ('promise', 'Обещание'),
        ('refuse', 'Отказ'),
        ('callback', 'Перезвонить'),
    ]
    status = models.CharField('Статус воздействия', max_length=20, choices=STATUS_CHOICES, default='completed')
    
    duration = models.IntegerField('Длительность разговора (сек)', default=0)
    promise_amount = models.DecimalField('Сумма обещания', max_digits=12, decimal_places=2, default=0)
    promise_date = models.DateField('Дата обещания', null=True, blank=True)

    def __str__(self):
        return f"Воздействие #{self.id} - {self.intervention_type}"

    class Meta:
        verbose_name = 'Воздействие'
        verbose_name_plural = 'Воздействия'


class Assignment(models.Model):
    """Распределение работы на текущий день (3000 записей)"""
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, verbose_name='Оператор')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='Клиент', null=True, blank=True)
    debtor_name = models.CharField('ФИО должника', max_length=300)
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, verbose_name='Кредит')
    overdue_amount = models.DecimalField('Сумма просрочки', max_digits=12, decimal_places=2, default=0)
    overdue_days = models.IntegerField('Срок просрочки (дней)', default=0)
    priority = models.IntegerField('Приоритет воздействия', default=1)
    assignment_date = models.DateField('Дата')

    def __str__(self):
        return f"Задание #{self.id} - {self.debtor_name}"

    class Meta:
        verbose_name = 'Распределение работы'
        verbose_name_plural = 'Распределения работы'


class ScoringResult(models.Model):
    """Результат работы прогнозирования (2000 записей)"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='scorings', verbose_name='Клиент')
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name='scorings', verbose_name='Кредит')
    calculation_date = models.DateField('Дата расчёта')
    probability = models.FloatField('Вероятность')
    
    SEGMENT_CHOICES = [
        ('low', 'Низкий риск'),
        ('medium', 'Средний риск'),
        ('high', 'Высокий риск'),
        ('critical', 'Критический риск'),
    ]
    risk_segment = models.CharField('Сегмент риска', max_length=20, choices=SEGMENT_CHOICES, default='medium')
    predicted_overdue_date = models.DateField('Прогнозируемая дата просрочки', null=True, blank=True)

    def __str__(self):
        return f"Скоринг #{self.id} - {self.probability:.2%}"

    class Meta:
        verbose_name = 'Результат прогнозирования'
        verbose_name_plural = 'Результаты прогнозирования'


class CreditApplication(models.Model):
    """
    Заявка на кредит - расширенная анкета заёмщика.
    На основе типовой банковской анкеты (РСХБ и др.)
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='Клиент', null=True, blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    
    # ===== РАЗДЕЛ 1: ПЕРСОНАЛЬНЫЕ ДАННЫЕ =====
    last_name = models.CharField('Фамилия', max_length=100, blank=True)
    first_name = models.CharField('Имя', max_length=100, blank=True)
    middle_name = models.CharField('Отчество', max_length=100, blank=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    birth_place = models.CharField('Место рождения', max_length=300, blank=True)
    
    GENDER_CHOICES = [('M', 'Мужской'), ('F', 'Женский')]
    gender = models.CharField('Пол', max_length=1, choices=GENDER_CHOICES, default='M')
    
    # Документ, удостоверяющий личность
    passport_series = models.CharField('Серия паспорта', max_length=10, blank=True)
    passport_number = models.CharField('Номер паспорта', max_length=20, blank=True)
    passport_issued_by = models.CharField('Кем выдан', max_length=300, blank=True)
    passport_issued_date = models.DateField('Дата выдачи', null=True, blank=True)
    passport_division_code = models.CharField('Код подразделения', max_length=20, blank=True)
    
    # ИНН и СНИЛС
    inn = models.CharField('ИНН', max_length=12, blank=True)
    snils = models.CharField('СНИЛС', max_length=14, blank=True)
    
    # ===== РАЗДЕЛ 2: КОНТАКТНАЯ ИНФОРМАЦИЯ =====
    phone_mobile = models.CharField('Мобильный телефон', max_length=20, blank=True)
    phone_home = models.CharField('Домашний телефон', max_length=20, blank=True)
    phone_work = models.CharField('Рабочий телефон', max_length=20, blank=True)
    email = models.EmailField('Email', blank=True)
    
    # Адрес регистрации
    registration_address = models.TextField('Адрес регистрации', blank=True)
    registration_date = models.DateField('Дата регистрации', null=True, blank=True)
    
    # Адрес фактического проживания
    actual_address = models.TextField('Адрес фактического проживания', blank=True)
    same_as_registration = models.BooleanField('Совпадает с адресом регистрации', default=True)
    
    # ===== РАЗДЕЛ 3: СЕМЕЙНОЕ ПОЛОЖЕНИЕ =====
    MARITAL_CHOICES = [
        ('single', 'Холост/Не замужем'),
        ('married', 'Женат/Замужем'),
        ('divorced', 'Разведён(а)'),
        ('widowed', 'Вдовец/Вдова'),
        ('civil_marriage', 'Гражданский брак'),
    ]
    marital_status = models.CharField('Семейное положение', max_length=20, choices=MARITAL_CHOICES, default='single')
    
    # Информация о супруге
    spouse_full_name = models.CharField('ФИО супруга(и)', max_length=300, blank=True)
    spouse_birth_date = models.DateField('Дата рождения супруга(и)', null=True, blank=True)
    spouse_phone = models.CharField('Телефон супруга(и)', max_length=20, blank=True)
    spouse_employer = models.CharField('Место работы супруга(и)', max_length=300, blank=True)
    spouse_income = models.DecimalField('Доход супруга(и)', max_digits=12, decimal_places=2, default=0)
    
    # Иждивенцы
    dependents_count = models.IntegerField('Количество иждивенцев', default=0)
    children_under_18 = models.IntegerField('Детей до 18 лет', default=0)
    
    # ===== РАЗДЕЛ 4: ОБРАЗОВАНИЕ =====
    EDUCATION_CHOICES = [
        ('secondary', 'Среднее'),
        ('vocational', 'Среднее специальное'),
        ('incomplete_higher', 'Неоконченное высшее'),
        ('higher', 'Высшее'),
        ('multiple_higher', 'Два и более высших'),
        ('academic', 'Учёная степень'),
    ]
    education = models.CharField('Образование', max_length=30, choices=EDUCATION_CHOICES, default='higher')
    
    # ===== РАЗДЕЛ 5: ЗАНЯТОСТЬ И ДОХОД =====
    EMPLOYMENT_CHOICES = [
        ('employed', 'Работаю по найму'),
        ('self_employed', 'Индивидуальный предприниматель'),
        ('business_owner', 'Владелец бизнеса'),
        ('freelance', 'Фрилансер/Самозанятый'),
        ('retired', 'Пенсионер'),
        ('student', 'Студент'),
        ('unemployed', 'Временно не работаю'),
        ('military', 'Военнослужащий'),
        ('civil_servant', 'Госслужащий'),
    ]
    employment_type = models.CharField('Тип занятости', max_length=30, choices=EMPLOYMENT_CHOICES, default='employed')
    
    # Информация о работодателе
    employer_name = models.CharField('Наименование организации', max_length=300, blank=True)
    employer_inn = models.CharField('ИНН организации', max_length=12, blank=True)
    employer_address = models.TextField('Адрес организации', blank=True)
    employer_phone = models.CharField('Телефон организации', max_length=20, blank=True)
    
    COMPANY_TYPE_CHOICES = [
        ('commercial', 'Коммерческая организация'),
        ('government', 'Государственная структура'),
        ('non_profit', 'Некоммерческая организация'),
        ('individual', 'ИП'),
    ]
    company_type = models.CharField('Тип организации', max_length=30, choices=COMPANY_TYPE_CHOICES, default='commercial')
    
    INDUSTRY_CHOICES = [
        ('it', 'IT/Телекоммуникации'),
        ('finance', 'Финансы/Банки/Страхование'),
        ('trade', 'Торговля'),
        ('manufacturing', 'Производство'),
        ('construction', 'Строительство'),
        ('transport', 'Транспорт/Логистика'),
        ('healthcare', 'Медицина'),
        ('education', 'Образование'),
        ('agriculture', 'Сельское хозяйство'),
        ('services', 'Услуги'),
        ('government', 'Госслужба'),
        ('other', 'Другое'),
    ]
    industry = models.CharField('Отрасль', max_length=30, choices=INDUSTRY_CHOICES, default='other')
    
    position = models.CharField('Должность', max_length=200, blank=True)
    
    POSITION_TYPE_CHOICES = [
        ('specialist', 'Специалист'),
        ('middle_manager', 'Руководитель среднего звена'),
        ('top_manager', 'Топ-менеджер'),
        ('owner', 'Владелец/Учредитель'),
    ]
    position_type = models.CharField('Уровень должности', max_length=30, choices=POSITION_TYPE_CHOICES, default='specialist')
    
    work_experience_total = models.IntegerField('Общий стаж (месяцев)', default=0)
    work_experience_current = models.IntegerField('Стаж на текущем месте (месяцев)', default=0)
    employment_date = models.DateField('Дата трудоустройства', null=True, blank=True)
    
    # Доходы
    income_main = models.DecimalField('Основной доход (зарплата)', max_digits=12, decimal_places=2, default=0)
    income_additional = models.DecimalField('Дополнительный доход', max_digits=12, decimal_places=2, default=0)
    income_rental = models.DecimalField('Доход от аренды', max_digits=12, decimal_places=2, default=0)
    income_pension = models.DecimalField('Пенсия', max_digits=12, decimal_places=2, default=0)
    income_other = models.DecimalField('Прочие доходы', max_digits=12, decimal_places=2, default=0)
    
    INCOME_CONFIRMATION_CHOICES = [
        ('2ndfl', 'Справка 2-НДФЛ'),
        ('bank_form', 'Справка по форме банка'),
        ('tax_declaration', 'Налоговая декларация'),
        ('bank_statement', 'Выписка из банка'),
        ('none', 'Без подтверждения'),
    ]
    income_confirmation = models.CharField('Подтверждение дохода', max_length=30, choices=INCOME_CONFIRMATION_CHOICES, default='2ndfl')
    
    # ===== РАЗДЕЛ 6: РАСХОДЫ И ОБЯЗАТЕЛЬСТВА =====
    expense_rent = models.DecimalField('Аренда жилья', max_digits=12, decimal_places=2, default=0)
    expense_utilities = models.DecimalField('Коммунальные платежи', max_digits=12, decimal_places=2, default=0)
    expense_food = models.DecimalField('Питание', max_digits=12, decimal_places=2, default=0)
    expense_transport = models.DecimalField('Транспорт', max_digits=12, decimal_places=2, default=0)
    expense_other = models.DecimalField('Прочие расходы', max_digits=12, decimal_places=2, default=0)
    
    # Текущие кредитные обязательства
    has_current_loans = models.BooleanField('Есть действующие кредиты', default=False)
    current_loans_count = models.IntegerField('Количество кредитов', default=0)
    current_loans_total_payment = models.DecimalField('Общий ежемесячный платёж по кредитам', max_digits=12, decimal_places=2, default=0)
    current_loans_total_balance = models.DecimalField('Общий остаток долга', max_digits=12, decimal_places=2, default=0)
    
    # Кредитные карты
    has_credit_cards = models.BooleanField('Есть кредитные карты', default=False)
    credit_cards_limit = models.DecimalField('Общий лимит по картам', max_digits=12, decimal_places=2, default=0)
    credit_cards_used = models.DecimalField('Использовано по картам', max_digits=12, decimal_places=2, default=0)
    
    # ===== РАЗДЕЛ 7: ИМУЩЕСТВО =====
    PROPERTY_OWNERSHIP_CHOICES = [
        ('own', 'Собственность'),
        ('mortgage', 'Ипотека'),
        ('rent', 'Аренда'),
        ('parents', 'У родственников'),
        ('employer', 'Служебное'),
    ]
    property_ownership = models.CharField('Жилищные условия', max_length=20, choices=PROPERTY_OWNERSHIP_CHOICES, default='own')
    
    has_car = models.BooleanField('Есть автомобиль', default=False)
    car_year = models.IntegerField('Год выпуска авто', null=True, blank=True)
    car_brand = models.CharField('Марка авто', max_length=100, blank=True)
    
    has_real_estate = models.BooleanField('Есть недвижимость в собственности', default=False)
    real_estate_value = models.DecimalField('Стоимость недвижимости', max_digits=14, decimal_places=2, default=0)
    
    has_deposits = models.BooleanField('Есть вклады', default=False)
    deposits_amount = models.DecimalField('Сумма вкладов', max_digits=14, decimal_places=2, default=0)
    
    # ===== РАЗДЕЛ 8: КРЕДИТНАЯ ИСТОРИЯ =====
    has_overdue_history = models.BooleanField('Были просрочки по кредитам', default=False)
    max_overdue_days = models.IntegerField('Макс. срок просрочки (дней)', default=0)
    has_bankruptsy = models.BooleanField('Процедура банкротства', default=False)
    has_court_debts = models.BooleanField('Судебные взыскания', default=False)
    
    # ===== РАЗДЕЛ 9: ПАРАМЕТРЫ КРЕДИТА =====
    CREDIT_PURPOSE_CHOICES = [
        ('consumer', 'Потребительские нужды'),
        ('car', 'Покупка автомобиля'),
        ('renovation', 'Ремонт'),
        ('education', 'Образование'),
        ('medical', 'Лечение'),
        ('travel', 'Отдых'),
        ('wedding', 'Свадьба'),
        ('refinance', 'Рефинансирование'),
        ('business', 'Развитие бизнеса'),
        ('other', 'Другое'),
    ]
    credit_purpose = models.CharField('Цель кредита', max_length=30, choices=CREDIT_PURPOSE_CHOICES, default='consumer')
    
    amount = models.DecimalField('Запрашиваемая сумма', max_digits=12, decimal_places=2)
    requested_term = models.IntegerField('Срок кредита (месяцев)', default=12)
    
    has_collateral = models.BooleanField('Есть залог', default=False)
    collateral_type = models.CharField('Тип залога', max_length=100, blank=True)
    collateral_value = models.DecimalField('Стоимость залога', max_digits=14, decimal_places=2, default=0)
    
    has_guarantor = models.BooleanField('Есть поручитель', default=False)
    guarantor_name = models.CharField('ФИО поручителя', max_length=300, blank=True)
    guarantor_phone = models.CharField('Телефон поручителя', max_length=20, blank=True)
    
    # ===== РАЗДЕЛ 10: ДОПОЛНИТЕЛЬНО =====
    is_public_official = models.BooleanField('Публичное должностное лицо', default=False)
    is_bank_employee = models.BooleanField('Сотрудник банка', default=False)
    consent_credit_history = models.BooleanField('Согласие на запрос БКИ', default=True)
    consent_personal_data = models.BooleanField('Согласие на обработку ПД', default=True)
    
    # ===== РЕЗУЛЬТАТЫ СКОРИНГА =====
    approved_probability = models.FloatField('Вероятность одобрения', null=True, blank=True)
    overdue_risk_probability = models.FloatField('Риск просрочки', null=True, blank=True)
    
    DECISION_CHOICES = [
        ('pending', 'На рассмотрении'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отказано'),
        ('additional_docs', 'Требуются документы'),
    ]
    decision = models.CharField('Решение', max_length=20, choices=DECISION_CHOICES, default='pending')
    decision_date = models.DateTimeField('Дата решения', null=True, blank=True)
    decision_comment = models.TextField('Комментарий к решению', blank=True)

    def __str__(self):
        name = f"{self.last_name} {self.first_name}".strip() or (self.client.full_name if self.client else f"Заявка #{self.id}")
        return f"Заявка #{self.id} - {name}"
    
    @property
    def total_income(self):
        """Общий доход"""
        return (self.income_main + self.income_additional + self.income_rental + 
                self.income_pension + self.income_other)
    
    @property
    def total_expenses(self):
        """Общие расходы"""
        return (self.expense_rent + self.expense_utilities + self.expense_food + 
                self.expense_transport + self.expense_other + self.current_loans_total_payment)
    
    @property
    def debt_to_income_ratio(self):
        """Коэффициент долговой нагрузки (DTI)"""
        if self.total_income > 0:
            monthly_payment = float(self.amount) / self.requested_term
            return (monthly_payment + float(self.total_expenses)) / float(self.total_income)
        return 1.0

    class Meta:
        verbose_name = 'Заявка на кредит'
        verbose_name_plural = 'Заявки на кредиты'


# ==================== KILLER FEATURES ====================

class ClientBehaviorProfile(models.Model):
    """Психотип клиента и поведенческий профиль (360° портрет)"""
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='behavior_profile')
    
    # Психотип (автосегментация не по сумме, а по поведению)
    PSYCHOTYPE_CHOICES = [
        ('forgetful', 'Забыл / Прокрастинирует'),
        ('unwilling', 'Может платить, но не хочет'),
        ('unable', 'Хочет платить, но не может'),
        ('toxic', 'Токсичный / Конфликтный'),
        ('cooperative', 'Готов к диалогу'),
    ]
    psychotype = models.CharField('Психотип', max_length=20, choices=PSYCHOTYPE_CHOICES, default='forgetful')
    psychotype_confidence = models.FloatField('Уверенность в психотипе', default=0.5)  # 0-1
    
    # Платежная дисциплина
    payment_discipline_score = models.FloatField('Оценка платёжной дисциплины', default=0.5)  # 0-1
    avg_days_overdue = models.FloatField('Средняя просрочка (дней)', default=0)
    payments_on_time_ratio = models.FloatField('Доля платежей вовремя', default=0)  # 0-1
    
    # Поведенческие паттерны
    best_contact_hour = models.IntegerField('Лучший час для контакта', default=14)  # 0-23
    best_contact_day = models.IntegerField('Лучший день недели', default=2)  # 0=Пн, 6=Вс
    
    PREFERRED_CHANNEL_CHOICES = [
        ('phone', 'Звонок'),
        ('sms', 'СМС'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('push', 'Push-уведомление'),
    ]
    preferred_channel = models.CharField('Предпочтительный канал', max_length=20, choices=PREFERRED_CHANNEL_CHOICES, default='phone')
    
    # Триггеры риска
    job_changed_recently = models.BooleanField('Смена работы недавно', default=False)
    income_dropped = models.BooleanField('Падение дохода', default=False)
    activity_dropped = models.BooleanField('Резкое падение активности', default=False)
    multiple_credits = models.BooleanField('Много кредитов одновременно', default=False)
    
    # История контактов
    total_contacts = models.IntegerField('Всего контактов', default=0)
    successful_contacts = models.IntegerField('Успешных контактов', default=0)
    promises_kept_ratio = models.FloatField('Доля выполненных обещаний', default=0)  # 0-1
    avg_promise_delay = models.FloatField('Средняя задержка по обещаниям (дней)', default=0)
    
    # Прогноз возврата
    return_probability = models.FloatField('Вероятность возврата', default=0.5)  # 0-1
    expected_return_days = models.IntegerField('Ожидаемый срок возврата (дней)', default=30)
    
    RECOMMENDATION_CHOICES = [
        ('continue', 'Продолжать взыскание'),
        ('restructure', 'Предложить реструктуризацию'),
        ('soft_collection', 'Мягкое взыскание'),
        ('legal', 'Передать юристам'),
        ('sell', 'Продать портфель'),
        ('write_off', 'Списать'),
    ]
    strategic_recommendation = models.CharField('Стратегическая рекомендация', max_length=20, choices=RECOMMENDATION_CHOICES, default='continue')
    
    last_updated = models.DateTimeField('Последнее обновление', auto_now=True)

    def __str__(self):
        return f"Профиль {self.client.full_name}: {self.get_psychotype_display()}"

    class Meta:
        verbose_name = 'Поведенческий профиль'
        verbose_name_plural = 'Поведенческие профили'


class NextBestAction(models.Model):
    """Рекомендация следующего лучшего действия (NBA)"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='nba_recommendations')
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name='nba_recommendations')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    # Когда контактировать
    recommended_datetime = models.DateTimeField('Рекомендуемое время контакта')
    urgency = models.IntegerField('Срочность (1-5)', default=3)
    
    # Как контактировать
    CHANNEL_CHOICES = [
        ('phone', 'Звонок'),
        ('sms', 'СМС'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('push', 'Push-уведомление'),
    ]
    recommended_channel = models.CharField('Рекомендуемый канал', max_length=20, choices=CHANNEL_CHOICES)
    
    # Какой сценарий
    SCENARIO_CHOICES = [
        ('soft_reminder', 'Мягкое напоминание'),
        ('firm_demand', 'Жёсткое требование'),
        ('empathy', 'Эмпатичный подход'),
        ('restructure_offer', 'Предложение реструктуризации'),
        ('discount_offer', 'Предложение скидки'),
        ('payment_holiday', 'Кредитные каникулы'),
        ('last_warning', 'Последнее предупреждение'),
    ]
    recommended_scenario = models.CharField('Рекомендуемый сценарий', max_length=30, choices=SCENARIO_CHOICES)
    
    # Какое предложение
    OFFER_CHOICES = [
        ('none', 'Без предложения'),
        ('discount_10', 'Скидка 10%'),
        ('discount_20', 'Скидка 20%'),
        ('discount_50', 'Скидка 50%'),
        ('restructure_6m', 'Реструктуризация на 6 мес'),
        ('restructure_12m', 'Реструктуризация на 12 мес'),
        ('holiday_1m', 'Каникулы 1 месяц'),
        ('holiday_3m', 'Каникулы 3 месяца'),
        ('partial_write_off', 'Частичное списание'),
    ]
    recommended_offer = models.CharField('Рекомендуемое предложение', max_length=30, choices=OFFER_CHOICES, default='none')
    max_discount_percent = models.FloatField('Макс. скидка %', default=0)
    
    # Обоснование
    reasoning = models.TextField('Обоснование рекомендации', blank=True)
    confidence_score = models.FloatField('Уверенность в рекомендации', default=0.5)  # 0-1
    
    # Статус
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('accepted', 'Принята'),
        ('rejected', 'Отклонена'),
        ('executed', 'Выполнена'),
        ('expired', 'Истекла'),
    ]
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Результат (для обучения)
    outcome_successful = models.BooleanField('Успешный результат', null=True, blank=True)

    def __str__(self):
        return f"NBA #{self.id}: {self.get_recommended_channel_display()} / {self.get_recommended_scenario_display()}"

    class Meta:
        verbose_name = 'Рекомендация NBA'
        verbose_name_plural = 'Рекомендации NBA'
        ordering = ['-created_at']


class SmartScript(models.Model):
    """Самообучающийся скрипт разговора"""
    name = models.CharField('Название скрипта', max_length=200)
    
    PSYCHOTYPE_CHOICES = [
        ('forgetful', 'Забыл / Прокрастинирует'),
        ('unwilling', 'Может платить, но не хочет'),
        ('unable', 'Хочет платить, но не может'),
        ('toxic', 'Токсичный / Конфликтный'),
        ('cooperative', 'Готов к диалогу'),
        ('any', 'Универсальный'),
    ]
    target_psychotype = models.CharField('Целевой психотип', max_length=20, choices=PSYCHOTYPE_CHOICES, default='any')
    
    SCENARIO_CHOICES = [
        ('soft_reminder', 'Мягкое напоминание'),
        ('firm_demand', 'Жёсткое требование'),
        ('empathy', 'Эмпатичный подход'),
        ('restructure_offer', 'Предложение реструктуризации'),
        ('discount_offer', 'Предложение скидки'),
        ('payment_holiday', 'Кредитные каникулы'),
        ('last_warning', 'Последнее предупреждение'),
    ]
    scenario = models.CharField('Сценарий', max_length=30, choices=SCENARIO_CHOICES)
    
    # Контент скрипта
    opening_phrases = models.JSONField('Вступительные фразы', default=list)
    key_phrases = models.JSONField('Ключевые фразы (работающие)', default=list)
    objection_handlers = models.JSONField('Обработка возражений', default=dict)  # {"возражение": ["ответ1", "ответ2"]}
    closing_phrases = models.JSONField('Завершающие фразы', default=list)
    
    # Статистика эффективности
    times_used = models.IntegerField('Использований', default=0)
    success_count = models.IntegerField('Успешных применений', default=0)
    success_rate = models.FloatField('Процент успеха', default=0)  # 0-1
    avg_ptp_amount = models.DecimalField('Средняя сумма PTP', max_digits=12, decimal_places=2, default=0)
    
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.success_rate:.0%})"

    class Meta:
        verbose_name = 'Умный скрипт'
        verbose_name_plural = 'Умные скрипты'


class ConversationAnalysis(models.Model):
    """Анализ разговора (для ML и комплаенса)"""
    intervention = models.OneToOneField(Intervention, on_delete=models.CASCADE, related_name='analysis')
    
    # Транскрипция и аналитика
    transcript = models.TextField('Транскрипция', blank=True)
    
    # Эмоциональный анализ
    SENTIMENT_CHOICES = [
        ('very_negative', 'Очень негативный'),
        ('negative', 'Негативный'),
        ('neutral', 'Нейтральный'),
        ('positive', 'Позитивный'),
        ('very_positive', 'Очень позитивный'),
    ]
    client_sentiment = models.CharField('Настроение клиента', max_length=20, choices=SENTIMENT_CHOICES, default='neutral')
    operator_sentiment = models.CharField('Настроение оператора', max_length=20, choices=SENTIMENT_CHOICES, default='neutral')
    
    # Успешные фразы (для обучения скриптов)
    effective_phrases = models.JSONField('Эффективные фразы', default=list)
    ineffective_phrases = models.JSONField('Неэффективные фразы', default=list)
    
    # Комплаенс
    compliance_score = models.FloatField('Оценка комплаенса', default=1.0)  # 0-1
    compliance_violations = models.JSONField('Нарушения комплаенса', default=list)
    
    # Ключевые метрики разговора
    talk_ratio = models.FloatField('Соотношение речи (оператор/клиент)', default=1.0)
    interruption_count = models.IntegerField('Перебиваний', default=0)
    silence_ratio = models.FloatField('Доля пауз', default=0)
    
    # Результат
    ptp_achieved = models.BooleanField('Получено PTP', default=False)
    ptp_amount = models.DecimalField('Сумма PTP', max_digits=12, decimal_places=2, default=0)
    
    analyzed_at = models.DateTimeField('Дата анализа', auto_now_add=True)

    def __str__(self):
        return f"Анализ разговора #{self.intervention_id}"

    class Meta:
        verbose_name = 'Анализ разговора'
        verbose_name_plural = 'Анализы разговоров'


class ComplianceAlert(models.Model):
    """Алерт нарушения комплаенса"""
    intervention = models.ForeignKey(Intervention, on_delete=models.CASCADE, related_name='compliance_alerts')
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, related_name='compliance_alerts')
    
    SEVERITY_CHOICES = [
        ('info', 'Информация'),
        ('warning', 'Предупреждение'),
        ('critical', 'Критическое'),
        ('violation', 'Нарушение'),
    ]
    severity = models.CharField('Серьёзность', max_length=20, choices=SEVERITY_CHOICES)
    
    ALERT_TYPE_CHOICES = [
        ('pressure', 'Давление на клиента'),
        ('threat', 'Угрозы'),
        ('disclosure', 'Разглашение информации'),
        ('timing', 'Звонок в неразрешённое время'),
        ('frequency', 'Превышена частота контактов'),
        ('script_deviation', 'Отклонение от скрипта'),
        ('prohibited_words', 'Запрещённые слова'),
        ('rudeness', 'Грубость'),
    ]
    alert_type = models.CharField('Тип алерта', max_length=30, choices=ALERT_TYPE_CHOICES)
    
    description = models.TextField('Описание')
    evidence = models.TextField('Доказательство (цитата)', blank=True)
    timestamp_in_call = models.IntegerField('Секунда в разговоре', null=True, blank=True)
    
    # Статус обработки
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('reviewed', 'Рассмотрен'),
        ('confirmed', 'Подтверждён'),
        ('false_positive', 'Ложное срабатывание'),
        ('escalated', 'Эскалирован'),
    ]
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Рассмотрел')
    review_comment = models.TextField('Комментарий проверки', blank=True)
    
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    def __str__(self):
        return f"Алерт: {self.get_alert_type_display()} ({self.get_severity_display()})"

    class Meta:
        verbose_name = 'Алерт комплаенса'
        verbose_name_plural = 'Алерты комплаенса'
        ordering = ['-created_at']


class ReturnForecast(models.Model):
    """Прогноз возврата долга"""
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name='forecasts')
    calculated_at = models.DateTimeField('Дата расчёта', auto_now_add=True)
    
    # Прогноз
    return_probability = models.FloatField('Вероятность возврата')  # 0-1
    partial_return_probability = models.FloatField('Вероятность частичного возврата', default=0)  # 0-1
    
    expected_return_amount = models.DecimalField('Ожидаемая сумма возврата', max_digits=12, decimal_places=2)
    expected_return_date = models.DateField('Ожидаемая дата возврата', null=True, blank=True)
    expected_return_days = models.IntegerField('Ожидаемый срок (дней)', default=30)
    
    # Рекомендация
    RECOMMENDATION_CHOICES = [
        ('continue_soft', 'Продолжить мягкое взыскание'),
        ('continue_hard', 'Усилить давление'),
        ('restructure', 'Предложить реструктуризацию'),
        ('legal', 'Передать в юридический'),
        ('sell', 'Продать коллекторам'),
        ('write_off', 'Списать как безнадёжный'),
    ]
    recommendation = models.CharField('Рекомендация', max_length=30, choices=RECOMMENDATION_CHOICES)
    recommendation_confidence = models.FloatField('Уверенность в рекомендации', default=0.5)
    
    # Факторы прогноза
    positive_factors = models.JSONField('Позитивные факторы', default=list)
    negative_factors = models.JSONField('Негативные факторы', default=list)
    
    # NPV при разных стратегиях (для принятия решений)
    npv_continue = models.DecimalField('NPV при продолжении взыскания', max_digits=12, decimal_places=2, default=0)
    npv_sell = models.DecimalField('NPV при продаже', max_digits=12, decimal_places=2, default=0)
    npv_write_off = models.DecimalField('NPV при списании', max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Прогноз #{self.id}: {self.return_probability:.0%} возврата"

    class Meta:
        verbose_name = 'Прогноз возврата'
        verbose_name_plural = 'Прогнозы возврата'
        ordering = ['-calculated_at']


class OperatorStatistics(models.Model):
    """Статистика работы операторов (витрина данных)"""
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, related_name='statistics', verbose_name='Оператор')
    period_start = models.DateField('Начало периода')
    period_end = models.DateField('Конец периода')
    calls_count = models.IntegerField('Количество звонков', default=0)
    successful_contacts = models.IntegerField('Успешные контакты', default=0)
    promises_received = models.IntegerField('Количество обещаний', default=0)
    total_collected_amount = models.DecimalField('Сумма погашенной задолженности', max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Статистика {self.operator.full_name}: {self.period_start} - {self.period_end}"

    class Meta:
        verbose_name = 'Статистика оператора'
        verbose_name_plural = 'Статистика операторов'
        ordering = ['-period_start']
