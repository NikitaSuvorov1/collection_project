from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# =====================================================
# RBAC - Роли и разрешения
# =====================================================

class Role(models.Model):
    """Роли пользователей системы"""
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('manager', 'Менеджер'),
        ('senior_operator', 'Старший оператор'),
        ('operator', 'Оператор'),
        ('legal_specialist', 'Юрист'),
        ('analyst', 'Аналитик'),
        ('auditor', 'Аудитор'),
    ]
    
    name = models.CharField('Код роли', max_length=50, unique=True, choices=ROLE_CHOICES)
    display_name = models.CharField('Отображаемое имя', max_length=100)
    description = models.TextField('Описание', blank=True)
    
    # Разрешения
    can_view_clients = models.BooleanField('Просмотр клиентов', default=True)
    can_edit_clients = models.BooleanField('Редактирование клиентов', default=False)
    can_view_credits = models.BooleanField('Просмотр кредитов', default=True)
    can_edit_credits = models.BooleanField('Редактирование кредитов', default=False)
    can_make_calls = models.BooleanField('Совершать звонки', default=False)
    can_send_sms = models.BooleanField('Отправлять SMS', default=False)
    can_send_email = models.BooleanField('Отправлять Email', default=False)
    can_restructure = models.BooleanField('Реструктуризация', default=False)
    can_escalate = models.BooleanField('Эскалация кейсов', default=False)
    can_access_legal = models.BooleanField('Доступ к юридическому модулю', default=False)
    can_manage_operators = models.BooleanField('Управление операторами', default=False)
    can_view_reports = models.BooleanField('Просмотр отчётов', default=False)
    can_export_data = models.BooleanField('Экспорт данных', default=False)
    can_access_ml = models.BooleanField('Доступ к ML моделям', default=False)
    can_audit = models.BooleanField('Аудит действий', default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.display_name
    
    class Meta:
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'


# =====================================================
# Аудит-логирование
# =====================================================

class AuditLog(models.Model):
    """Аудит всех действий в системе"""
    ACTION_CHOICES = [
        ('create', 'Создание'),
        ('read', 'Просмотр'),
        ('update', 'Изменение'),
        ('delete', 'Удаление'),
        ('login', 'Вход'),
        ('logout', 'Выход'),
        ('call', 'Звонок'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('escalate', 'Эскалация'),
        ('restructure', 'Реструктуризация'),
        ('legal_action', 'Юридическое действие'),
        ('export', 'Экспорт'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Пользователь')
    action = models.CharField('Действие', max_length=50, choices=ACTION_CHOICES)
    model_name = models.CharField('Модель', max_length=100)
    object_id = models.IntegerField('ID объекта', null=True, blank=True)
    object_repr = models.CharField('Представление объекта', max_length=500, blank=True)
    changes = models.JSONField('Изменения', default=dict, blank=True)
    ip_address = models.GenericIPAddressField('IP адрес', null=True, blank=True)
    user_agent = models.CharField('User Agent', max_length=500, blank=True)
    timestamp = models.DateTimeField('Время', auto_now_add=True)
    
    # Для соответствия ФЗ-152
    personal_data_accessed = models.BooleanField('Доступ к ПДн', default=False)
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name} - {self.timestamp}"
    
    class Meta:
        verbose_name = 'Запись аудита'
        verbose_name_plural = 'Журнал аудита'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['action', 'timestamp']),
        ]


class Operator(models.Model):
    """Оператор (50 записей)"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField('ФИО оператора', max_length=200)
    
    ROLE_CHOICES = [
        ('junior_operator', 'Джуниор оператор'),
        ('operator', 'Оператор'),
        ('senior_operator', 'Старший оператор'),
        ('team_lead', 'Тимлид'),
        ('supervisor', 'Супервайзер'),
        ('legal_specialist', 'Юрист'),
        ('manager', 'Менеджер'),
    ]
    role = models.CharField('Роль / группа', max_length=50, choices=ROLE_CHOICES, default='operator')
    
    # Связь с системой ролей
    system_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Системная роль')
    
    hire_date = models.DateField('Дата трудоустройства', null=True, blank=True)
    current_load = models.IntegerField('Текущая нагрузка', default=0)
    max_load = models.IntegerField('Максимальная нагрузка', default=50)
    
    # Специализация оператора
    SPECIALIZATION_CHOICES = [
        ('soft', 'Soft Collection'),
        ('hard', 'Hard Collection'),
        ('legal', 'Legal Collection'),
        ('restructure', 'Реструктуризация'),
        ('universal', 'Универсальный'),
    ]
    specialization = models.CharField('Специализация', max_length=20, choices=SPECIALIZATION_CHOICES, default='universal')
    
    # Статистика
    success_rate = models.FloatField('Показатель успешности', default=0.5)
    avg_call_duration = models.IntegerField('Средняя длительность звонка (сек)', default=180)
    total_collected = models.DecimalField('Всего собрано', max_digits=14, decimal_places=2, default=0)
    
    STATUS_CHOICES = [
        ('active', 'Активен'),
        ('break', 'Перерыв'),
        ('offline', 'Не в сети'),
        ('on_call', 'На звонке'),
        ('training', 'Обучение'),
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
    
    # === 230-ФЗ: Контроль согласия на контакт ===
    contact_refused = models.BooleanField('Отказ от взаимодействия (230-ФЗ ст.8)', default=False)
    contact_refused_date = models.DateField('Дата отказа', null=True, blank=True)
    REFUSED_CHANNELS_HELP = 'JSON-список каналов, от которых клиент отказался (пустой = полный отказ). Пример: ["phone","sms"]'
    refused_channels = models.JSONField('Каналы отказа', default=list, blank=True, help_text=REFUSED_CHANNELS_HELP)
    is_bankrupt = models.BooleanField('Признан банкротом', default=False)
    bankruptcy_date = models.DateField('Дата признания банкротом', null=True, blank=True)
    # === 230-ФЗ ст.4: Согласие на взаимодействие с третьими лицами ===
    third_party_consent = models.BooleanField('Согласие на контакт с третьими лицами', default=False)
    third_party_consent_date = models.DateField('Дата согласия', null=True, blank=True)

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        indexes = [
            models.Index(fields=['full_name'], name='idx_client_fullname'),
            models.Index(fields=['phone_mobile'], name='idx_client_phone'),
            models.Index(fields=['is_bankrupt'], name='idx_client_bankrupt'),
            models.Index(fields=['contact_refused'], name='idx_client_refused'),
        ]


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
        ('legal', 'В судебном производстве'),
        ('sold', 'Продан коллекторам'),
        ('written_off', 'Списан'),
    ]
    status = models.CharField('Статус кредита', max_length=20, choices=STATUS_CHOICES, default='active')
    actuality_date = models.DateField('Дата актуальности', null=True, blank=True)

    def __str__(self):
        return f"Кредит #{self.id} - {self.client.full_name}"

    class Meta:
        verbose_name = 'Кредит'
        verbose_name_plural = 'Кредиты'


# =====================================================
# COLLECTION CASE - Кейс взыскания
# =====================================================

class CollectionCase(models.Model):
    """
    Кейс взыскания - центральная сущность для управления процессом collection.
    Один кейс может включать несколько кредитов одного клиента.
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='collection_cases', verbose_name='Клиент')
    credits = models.ManyToManyField('Credit', related_name='collection_cases', verbose_name='Кредиты')
    
    # Назначенный оператор
    assigned_operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True, blank=True, 
                                          related_name='assigned_cases', verbose_name='Назначенный оператор')
    
    # Стадия взыскания
    STAGE_CHOICES = [
        ('pre_collection', 'Pre-Collection'),
        ('soft_early', 'Soft Collection (ранняя)'),
        ('soft_late', 'Soft Collection (поздняя)'),
        ('hard', 'Hard Collection'),
        ('legal_pretrial', 'Досудебная работа'),
        ('legal_court', 'Судебное производство'),
        ('legal_execution', 'Исполнительное производство'),
        ('restructured', 'Реструктуризация'),
        ('settled', 'Урегулировано'),
        ('sold', 'Продано'),
        ('written_off', 'Списано'),
    ]
    stage = models.CharField('Стадия взыскания', max_length=30, choices=STAGE_CHOICES, default='pre_collection')
    
    # Приоритет
    PRIORITY_CHOICES = [
        (1, 'Низкий'),
        (2, 'Ниже среднего'),
        (3, 'Средний'),
        (4, 'Выше среднего'),
        (5, 'Высокий'),
        (6, 'Критический'),
    ]
    priority = models.IntegerField('Приоритет', choices=PRIORITY_CHOICES, default=3)
    priority_score = models.FloatField('Скоринг приоритета', default=50.0)
    
    # Суммы
    total_debt = models.DecimalField('Общий долг', max_digits=14, decimal_places=2, default=0)
    overdue_amount = models.DecimalField('Просроченная сумма', max_digits=14, decimal_places=2, default=0)
    penalties = models.DecimalField('Штрафы и пени', max_digits=12, decimal_places=2, default=0)
    
    # Сроки
    overdue_days = models.IntegerField('Дней просрочки', default=0)
    max_overdue_days = models.IntegerField('Макс. дней просрочки', default=0)
    
    # Статус кейса
    STATUS_CHOICES = [
        ('active', 'Активный'),
        ('paused', 'Приостановлен'),
        ('escalated', 'Эскалирован'),
        ('closed_paid', 'Закрыт - оплачен'),
        ('closed_restructured', 'Закрыт - реструктуризация'),
        ('closed_sold', 'Закрыт - продан'),
        ('closed_written_off', 'Закрыт - списан'),
    ]
    status = models.CharField('Статус кейса', max_length=30, choices=STATUS_CHOICES, default='active')
    
    # Прогнозы ML
    return_probability = models.FloatField('Вероятность возврата', default=0.5)
    predicted_return_amount = models.DecimalField('Прогноз суммы возврата', max_digits=14, decimal_places=2, default=0)
    risk_segment = models.CharField('Риск-сегмент', max_length=20, default='medium')
    
    # Даты
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    stage_changed_at = models.DateTimeField('Дата смены стадии', null=True, blank=True)
    next_action_date = models.DateField('Дата следующего действия', null=True, blank=True)
    
    # Счётчики активности
    total_contacts = models.IntegerField('Всего контактов', default=0)
    successful_contacts = models.IntegerField('Успешных контактов', default=0)
    promises_count = models.IntegerField('Количество обещаний', default=0)
    broken_promises = models.IntegerField('Нарушенных обещаний', default=0)
    
    # Психотип и стратегия
    psychotype = models.CharField('Психотип', max_length=50, blank=True)
    recommended_strategy = models.CharField('Рекомендованная стратегия', max_length=100, blank=True)
    
    def __str__(self):
        return f"Кейс #{self.id} - {self.client.full_name} ({self.get_stage_display()})"
    
    class Meta:
        verbose_name = 'Кейс взыскания'
        verbose_name_plural = 'Кейсы взыскания'
        ordering = ['-priority', '-overdue_amount']
        indexes = [
            models.Index(fields=['stage', 'status']),
            models.Index(fields=['assigned_operator', 'status']),
            models.Index(fields=['priority', 'overdue_days']),
        ]


class CollectionStageHistory(models.Model):
    """История переходов между стадиями collection"""
    case = models.ForeignKey(CollectionCase, on_delete=models.CASCADE, related_name='stage_history')
    from_stage = models.CharField('Из стадии', max_length=30)
    to_stage = models.CharField('В стадию', max_length=30)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Кем изменено')
    reason = models.TextField('Причина перехода', blank=True)
    auto_transition = models.BooleanField('Автоматический переход', default=False)
    created_at = models.DateTimeField('Дата перехода', auto_now_add=True)
    
    class Meta:
        verbose_name = 'История стадий'
        verbose_name_plural = 'История стадий'
        ordering = ['-created_at']


# =====================================================
# PRE-COLLECTION
# =====================================================

class PreCollectionAlert(models.Model):
    """Алерты Pre-Collection - раннее предупреждение о возможной просрочке"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='precollection_alerts')
    credit = models.ForeignKey('Credit', on_delete=models.CASCADE, related_name='precollection_alerts')
    
    ALERT_TYPE_CHOICES = [
        ('payment_due_soon', 'Скоро платёж'),
        ('payment_missed', 'Пропущен платёж'),
        ('high_risk_detected', 'Обнаружен высокий риск'),
        ('behavior_change', 'Изменение поведения'),
        ('income_drop', 'Снижение дохода'),
    ]
    alert_type = models.CharField('Тип алерта', max_length=30, choices=ALERT_TYPE_CHOICES)
    
    days_before_due = models.IntegerField('Дней до платежа', default=0)
    risk_score = models.FloatField('Риск-скор', default=0.5)
    
    # Действия
    sms_sent = models.BooleanField('SMS отправлено', default=False)
    email_sent = models.BooleanField('Email отправлено', default=False)
    push_sent = models.BooleanField('Push отправлено', default=False)
    
    # Отслеживание реакции
    notification_opened = models.BooleanField('Уведомление открыто', default=False)
    lk_visited = models.BooleanField('Посещён ЛК', default=False)
    payment_made = models.BooleanField('Платёж совершён', default=False)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    processed_at = models.DateTimeField('Обработано', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Алерт Pre-Collection'
        verbose_name_plural = 'Алерты Pre-Collection'
        ordering = ['-created_at']


# =====================================================
# SOFT COLLECTION
# =====================================================

class CommunicationTask(models.Model):
    """Задача на коммуникацию с клиентом"""
    case = models.ForeignKey(CollectionCase, on_delete=models.CASCADE, related_name='communication_tasks')
    operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True, related_name='communication_tasks')
    
    TASK_TYPE_CHOICES = [
        ('call_first', 'Первичный звонок'),
        ('call_followup', 'Повторный звонок'),
        ('call_promise', 'Звонок по обещанию'),
        ('sms_reminder', 'SMS напоминание'),
        ('sms_demand', 'SMS требование'),
        ('email_reminder', 'Email напоминание'),
        ('email_demand', 'Email требование'),
        ('letter_soft', 'Мягкое письмо'),
        ('letter_demand', 'Письмо-требование'),
    ]
    task_type = models.CharField('Тип задачи', max_length=30, choices=TASK_TYPE_CHOICES)
    
    PRIORITY_CHOICES = [
        (1, 'Низкий'),
        (2, 'Средний'),
        (3, 'Высокий'),
        (4, 'Срочный'),
    ]
    priority = models.IntegerField('Приоритет', choices=PRIORITY_CHOICES, default=2)
    
    scheduled_date = models.DateField('Запланированная дата')
    scheduled_time = models.TimeField('Запланированное время', null=True, blank=True)
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('in_progress', 'В работе'),
        ('completed', 'Выполнено'),
        ('failed', 'Не выполнено'),
        ('cancelled', 'Отменено'),
        ('rescheduled', 'Перенесено'),
    ]
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Результат
    result_code = models.CharField('Код результата', max_length=50, blank=True)
    result_notes = models.TextField('Заметки', blank=True)
    
    # Время выполнения
    started_at = models.DateTimeField('Начало выполнения', null=True, blank=True)
    completed_at = models.DateTimeField('Завершение', null=True, blank=True)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Задача на коммуникацию'
        verbose_name_plural = 'Задачи на коммуникацию'
        ordering = ['scheduled_date', 'priority']


class CallScript(models.Model):
    """Скрипты для звонков"""
    name = models.CharField('Название', max_length=200)
    
    STAGE_CHOICES = [
        ('pre_collection', 'Pre-Collection'),
        ('soft_early', 'Soft Early'),
        ('soft_late', 'Soft Late'),
        ('hard', 'Hard Collection'),
    ]
    stage = models.CharField('Стадия', max_length=30, choices=STAGE_CHOICES)
    
    PSYCHOTYPE_CHOICES = [
        ('any', 'Любой'),
        ('cooperative', 'Кооперативный'),
        ('forgetful', 'Забывчивый'),
        ('unable', 'Не может платить'),
        ('unwilling', 'Не хочет платить'),
        ('toxic', 'Токсичный'),
    ]
    psychotype = models.CharField('Психотип', max_length=20, choices=PSYCHOTYPE_CHOICES, default='any')
    
    opening = models.TextField('Приветствие')
    key_points = models.JSONField('Ключевые тезисы', default=list)
    objection_handlers = models.JSONField('Обработка возражений', default=dict)
    closing = models.TextField('Завершение')
    tips = models.JSONField('Подсказки оператору', default=list)
    
    is_active = models.BooleanField('Активен', default=True)
    
    class Meta:
        verbose_name = 'Скрипт звонка'
        verbose_name_plural = 'Скрипты звонков'


class Promise(models.Model):
    """Обещание клиента о платеже"""
    case = models.ForeignKey(CollectionCase, on_delete=models.CASCADE, related_name='promises')
    intervention = models.ForeignKey('Intervention', on_delete=models.SET_NULL, null=True, related_name='promises')
    
    promised_amount = models.DecimalField('Обещанная сумма', max_digits=12, decimal_places=2)
    promised_date = models.DateField('Обещанная дата')
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('kept', 'Выполнено'),
        ('partial', 'Частично выполнено'),
        ('broken', 'Нарушено'),
        ('extended', 'Продлено'),
    ]
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    actual_amount = models.DecimalField('Фактическая сумма', max_digits=12, decimal_places=2, default=0)
    actual_date = models.DateField('Фактическая дата', null=True, blank=True)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    verified_at = models.DateTimeField('Проверено', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Обещание'
        verbose_name_plural = 'Обещания'
        ordering = ['promised_date']


# =====================================================
# HARD COLLECTION
# =====================================================

class FieldVisit(models.Model):
    """Выездное мероприятие (Hard Collection)"""
    case = models.ForeignKey(CollectionCase, on_delete=models.CASCADE, related_name='field_visits')
    operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True)
    
    scheduled_date = models.DateField('Запланированная дата')
    scheduled_time = models.TimeField('Запланированное время', null=True, blank=True)
    
    address = models.TextField('Адрес визита')
    
    VISIT_TYPE_CHOICES = [
        ('residence', 'По месту жительства'),
        ('work', 'По месту работы'),
        ('guarantor', 'К поручителю'),
        ('relatives', 'К родственникам'),
    ]
    visit_type = models.CharField('Тип визита', max_length=20, choices=VISIT_TYPE_CHOICES, default='residence')
    
    STATUS_CHOICES = [
        ('scheduled', 'Запланирован'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершён'),
        ('cancelled', 'Отменён'),
        ('rescheduled', 'Перенесён'),
    ]
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    RESULT_CHOICES = [
        ('contact_made', 'Контакт состоялся'),
        ('no_contact', 'Контакт не состоялся'),
        ('promise_made', 'Получено обещание'),
        ('payment_made', 'Получен платёж'),
        ('refused', 'Отказ от контакта'),
        ('not_home', 'Не застали'),
        ('wrong_address', 'Неверный адрес'),
    ]
    result = models.CharField('Результат', max_length=20, choices=RESULT_CHOICES, blank=True)
    
    notes = models.TextField('Заметки', blank=True)
    photo_evidence = models.JSONField('Фото-фиксация', default=list)
    
    actual_date = models.DateField('Фактическая дата', null=True, blank=True)
    duration_minutes = models.IntegerField('Длительность (мин)', default=0)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Выездное мероприятие'
        verbose_name_plural = 'Выездные мероприятия'
        ordering = ['scheduled_date']


# =====================================================
# LEGAL COLLECTION
# =====================================================

class LegalCase(models.Model):
    """Судебное дело"""
    collection_case = models.ForeignKey(CollectionCase, on_delete=models.CASCADE, related_name='legal_cases')
    
    case_number = models.CharField('Номер дела', max_length=100, blank=True)
    court_name = models.CharField('Наименование суда', max_length=300, blank=True)
    
    STAGE_CHOICES = [
        ('pretrial_claim', 'Досудебная претензия'),
        ('claim_filed', 'Иск подан'),
        ('court_hearing', 'Судебные заседания'),
        ('judgment', 'Вынесено решение'),
        ('appeal', 'Апелляция'),
        ('execution', 'Исполнительное производство'),
        ('closed', 'Закрыто'),
    ]
    stage = models.CharField('Стадия', max_length=30, choices=STAGE_CHOICES, default='pretrial_claim')
    
    claim_amount = models.DecimalField('Сумма иска', max_digits=14, decimal_places=2, default=0)
    awarded_amount = models.DecimalField('Присуждённая сумма', max_digits=14, decimal_places=2, default=0)
    
    # Даты
    pretrial_sent_date = models.DateField('Дата отправки претензии', null=True, blank=True)
    claim_filed_date = models.DateField('Дата подачи иска', null=True, blank=True)
    hearing_date = models.DateField('Дата заседания', null=True, blank=True)
    judgment_date = models.DateField('Дата решения', null=True, blank=True)
    
    # Исполнительное производство
    execution_number = models.CharField('Номер ИП', max_length=100, blank=True)
    bailiff_name = models.CharField('ФИО пристава', max_length=200, blank=True)
    bailiff_phone = models.CharField('Телефон пристава', max_length=32, blank=True)
    
    # Документы
    documents = models.JSONField('Документы', default=list)
    
    notes = models.TextField('Заметки', blank=True)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Судебное дело'
        verbose_name_plural = 'Судебные дела'
        ordering = ['-created_at']


class LegalDocument(models.Model):
    """Юридический документ"""
    legal_case = models.ForeignKey(LegalCase, on_delete=models.CASCADE, related_name='legal_documents')
    
    DOCUMENT_TYPE_CHOICES = [
        ('pretrial_claim', 'Досудебная претензия'),
        ('statement_of_claim', 'Исковое заявление'),
        ('motion', 'Ходатайство'),
        ('objection', 'Возражение'),
        ('judgment', 'Судебное решение'),
        ('writ_of_execution', 'Исполнительный лист'),
        ('other', 'Другое'),
    ]
    document_type = models.CharField('Тип документа', max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    
    title = models.CharField('Название', max_length=300)
    template_used = models.CharField('Использованный шаблон', max_length=200, blank=True)
    
    file_path = models.CharField('Путь к файлу', max_length=500, blank=True)
    
    sent_date = models.DateField('Дата отправки', null=True, blank=True)
    received_date = models.DateField('Дата получения', null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Юридический документ'
        verbose_name_plural = 'Юридические документы'


# =====================================================
# РЕСТРУКТУРИЗАЦИЯ
# =====================================================

class RestructuringRequest(models.Model):
    """Запрос на реструктуризацию"""
    case = models.ForeignKey(CollectionCase, on_delete=models.CASCADE, related_name='restructuring_requests')
    credit = models.ForeignKey('Credit', on_delete=models.CASCADE)
    
    # Текущие параметры
    current_debt = models.DecimalField('Текущий долг', max_digits=14, decimal_places=2)
    current_monthly_payment = models.DecimalField('Текущий платёж', max_digits=12, decimal_places=2)
    current_rate = models.DecimalField('Текущая ставка', max_digits=5, decimal_places=2)
    remaining_term = models.IntegerField('Остаток срока (мес)')
    
    # Запрашиваемые параметры
    RESTRUCTURE_TYPE_CHOICES = [
        ('term_extension', 'Пролонгация'),
        ('rate_reduction', 'Снижение ставки'),
        ('payment_holiday', 'Кредитные каникулы'),
        ('partial_write_off', 'Частичное списание'),
        ('combined', 'Комбинированная'),
    ]
    restructure_type = models.CharField('Тип реструктуризации', max_length=30, choices=RESTRUCTURE_TYPE_CHOICES)
    
    requested_term = models.IntegerField('Запрашиваемый срок (мес)', null=True, blank=True)
    requested_rate = models.DecimalField('Запрашиваемая ставка', max_digits=5, decimal_places=2, null=True, blank=True)
    requested_holiday_months = models.IntegerField('Месяцев каникул', null=True, blank=True)
    requested_write_off = models.DecimalField('Сумма списания', max_digits=14, decimal_places=2, null=True, blank=True)
    
    # Рассчитанные параметры
    new_monthly_payment = models.DecimalField('Новый платёж', max_digits=12, decimal_places=2, null=True, blank=True)
    total_overpayment = models.DecimalField('Переплата', max_digits=14, decimal_places=2, null=True, blank=True)
    
    # Обоснование
    client_income = models.DecimalField('Доход клиента', max_digits=12, decimal_places=2, default=0)
    client_expenses = models.DecimalField('Расходы клиента', max_digits=12, decimal_places=2, default=0)
    hardship_reason = models.TextField('Причина затруднений')
    supporting_documents = models.JSONField('Подтверждающие документы', default=list)
    
    # Оценка
    viability_score = models.FloatField('Оценка жизнеспособности', default=0.5)
    pd_before = models.FloatField('PD до реструктуризации', default=0.5)
    pd_after = models.FloatField('PD после реструктуризации', default=0.5)
    lgd_impact = models.FloatField('Влияние на LGD', default=0)
    
    # Статус
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('submitted', 'Подана'),
        ('under_review', 'На рассмотрении'),
        ('approved', 'Одобрена'),
        ('rejected', 'Отклонена'),
        ('activated', 'Активирована'),
        ('cancelled', 'Отменена'),
    ]
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_restructurings')
    review_notes = models.TextField('Комментарий к решению', blank=True)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    submitted_at = models.DateTimeField('Подано', null=True, blank=True)
    reviewed_at = models.DateTimeField('Рассмотрено', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Запрос на реструктуризацию'
        verbose_name_plural = 'Запросы на реструктуризацию'
        ordering = ['-created_at']


# =====================================================
# WORKFLOW ENGINE
# =====================================================

class WorkflowRule(models.Model):
    """Правила workflow для автоматических переходов"""
    name = models.CharField('Название правила', max_length=200)
    description = models.TextField('Описание', blank=True)
    
    # Условия
    from_stage = models.CharField('Из стадии', max_length=30)
    to_stage = models.CharField('В стадию', max_length=30)
    
    # Условия срабатывания (JSON)
    # Пример: {"overdue_days": {"gte": 30}, "total_contacts": {"gte": 3}, "promises_broken": {"gte": 1}}
    conditions = models.JSONField('Условия', default=dict)
    
    # Действия при переходе
    # Пример: {"create_task": "call_followup", "notify_manager": true, "change_priority": 4}
    actions = models.JSONField('Действия', default=dict)
    
    priority = models.IntegerField('Приоритет правила', default=10)
    is_active = models.BooleanField('Активно', default=True)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Правило workflow'
        verbose_name_plural = 'Правила workflow'
        ordering = ['priority']


class ScheduledAction(models.Model):
    """Запланированные автоматические действия"""
    case = models.ForeignKey(CollectionCase, on_delete=models.CASCADE, related_name='scheduled_actions')
    
    ACTION_TYPE_CHOICES = [
        ('send_sms', 'Отправить SMS'),
        ('send_email', 'Отправить Email'),
        ('create_task', 'Создать задачу'),
        ('escalate', 'Эскалировать'),
        ('change_stage', 'Сменить стадию'),
        ('check_promise', 'Проверить обещание'),
        ('check_payment', 'Проверить платёж'),
    ]
    action_type = models.CharField('Тип действия', max_length=30, choices=ACTION_TYPE_CHOICES)
    
    scheduled_at = models.DateTimeField('Запланировано на')
    
    parameters = models.JSONField('Параметры', default=dict)
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('executed', 'Выполнено'),
        ('failed', 'Ошибка'),
        ('cancelled', 'Отменено'),
    ]
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    executed_at = models.DateTimeField('Выполнено', null=True, blank=True)
    result = models.TextField('Результат', blank=True)
    
    class Meta:
        verbose_name = 'Запланированное действие'
        verbose_name_plural = 'Запланированные действия'
        ordering = ['scheduled_at']


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
    notes = models.TextField('Комментарий оператора', blank=True, default='')
    refusal_reason = models.CharField('Причина отказа', max_length=200, blank=True, default='')
    # === 230-ФЗ: Дополнительные требования ===
    caller_number = models.CharField('Исходящий номер (ст.9 — запрет скрытых)', max_length=32, blank=True, default='')
    operator_identified = models.BooleanField('Оператор представился (ст.6)', default=True)
    approved_script_used = models.BooleanField('Использован утверждённый скрипт (ст.5)', default=True)
    is_third_party = models.BooleanField('Контакт с третьим лицом', default=False)

    def __str__(self):
        return f"Воздействие #{self.id} - {self.intervention_type}"

    class Meta:
        verbose_name = 'Воздействие'
        verbose_name_plural = 'Воздействия'
        indexes = [
            models.Index(fields=['client', '-datetime'], name='idx_interv_client_dt'),
            models.Index(fields=['operator', '-datetime'], name='idx_interv_op_dt'),
            models.Index(fields=['status'], name='idx_interv_status'),
            models.Index(fields=['credit'], name='idx_interv_credit'),
        ]


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
    
    # A/B тестирование
    AB_GROUP_CHOICES = [
        ('A', 'Контрольная (обычное)'),
        ('B', 'Экспериментальная (умное)'),
    ]
    ab_group = models.CharField('A/B группа', max_length=2, choices=AB_GROUP_CHOICES, default='B')
    assignment_method = models.CharField('Метод назначения', max_length=30, default='smart')
    match_score = models.FloatField('Качество матчинга', default=0)

    def __str__(self):
        return f"Задание #{self.id} - {self.debtor_name}"

    class Meta:
        verbose_name = 'Распределение работы'
        verbose_name_plural = 'Распределения работы'
        indexes = [
            models.Index(fields=['operator', 'assignment_date'], name='idx_assign_op_date'),
            models.Index(fields=['credit'], name='idx_assign_credit'),
            models.Index(fields=['ab_group'], name='idx_assign_ab'),
        ]


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
    
    # === Расширения для полноценного скоринга ===
    score_value = models.IntegerField('Скоринговый балл (300-850)', null=True, blank=True)
    model_version = models.CharField('Версия модели', max_length=50, blank=True, default='')
    model_type = models.CharField('Тип алгоритма', max_length=50, blank=True, default='')
    roc_auc = models.FloatField('ROC-AUC модели', null=True, blank=True)
    grade = models.CharField('Грейд (A-E)', max_length=2, blank=True, default='')
    
    # Экономическая модель
    expected_recovery = models.DecimalField('Ожидаемый возврат (₽)', max_digits=12, decimal_places=2, default=0)
    cost_per_contact = models.DecimalField('Стоимость контакта (₽)', max_digits=8, decimal_places=2, default=150)
    expected_profit = models.DecimalField('Ожидаемая прибыль (₽)', max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Скоринг #{self.id} - {self.probability:.2%}"

    class Meta:
        verbose_name = 'Результат прогнозирования'
        verbose_name_plural = 'Результаты прогнозирования'
        indexes = [
            models.Index(fields=['client', '-calculation_date'], name='idx_scoring_client_date'),
            models.Index(fields=['score_value'], name='idx_scoring_score'),
            models.Index(fields=['risk_segment'], name='idx_scoring_segment'),
            models.Index(fields=['model_version'], name='idx_scoring_version'),
        ]


class TrainingData(models.Model):
    """
    Обучающая выборка для модели прогнозирования просрочки.
    Соответствует разделу 3.2 курсовой работы - матрица признаков X и целевая переменная y.
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='training_records', verbose_name='Клиент')
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name='training_records', verbose_name='Кредит')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    
    # === Параметры клиента (признаки 1-8) ===
    age = models.IntegerField('Возраст', default=0)
    gender = models.IntegerField('Пол (1=М, 0=Ж)', default=0)
    marital_status = models.IntegerField('Семейное положение', default=0)
    employment = models.IntegerField('Тип занятости', default=0)
    dependents = models.IntegerField('Количество иждивенцев', default=0)
    monthly_income = models.FloatField('Ежемесячный доход', default=0)
    has_other_credits = models.IntegerField('Наличие других кредитов', default=0)
    other_credits_count = models.IntegerField('Количество других кредитов', default=0)
    
    # === Параметры кредита (признаки 9-17) ===
    credit_amount = models.FloatField('Сумма кредита', default=0)
    credit_term = models.IntegerField('Срок кредита (мес)', default=0)
    interest_rate = models.FloatField('Процентная ставка', default=0)
    lti_ratio = models.FloatField('Коэффициент LTI', default=0)
    credit_age = models.IntegerField('Возраст кредита (дней)', default=0)
    credit_status = models.IntegerField('Статус кредита', default=0)
    monthly_payment = models.FloatField('Ежемесячный платёж', default=0)
    
    # === Показатели платёжной дисциплины (признаки 18-25) ===
    total_payments = models.IntegerField('Всего платежей', default=0)
    overdue_payments = models.IntegerField('Просроченных платежей', default=0)
    max_overdue_days = models.IntegerField('Макс. дней просрочки', default=0)
    avg_payment = models.FloatField('Средний платёж', default=0)
    payments_count_12m = models.IntegerField('Платежей за 12 мес', default=0)
    overdue_count_12m = models.IntegerField('Просрочек за 12 мес', default=0)
    overdue_share_12m = models.FloatField('Доля просрочек за 12 мес', default=0)
    max_overdue_12m = models.IntegerField('Макс. просрочка за 12 мес', default=0)
    
    # === Характеристики взаимодействия (признаки 26-28) ===
    total_interventions = models.IntegerField('Всего воздействий', default=0)
    completed_interventions = models.IntegerField('Успешных воздействий', default=0)
    promises_count = models.IntegerField('Количество обещаний', default=0)
    
    # === Целевая переменная y ===
    RISK_CHOICES = [
        (0, 'Низкий риск'),
        (1, 'Средний риск'),
        (2, 'Высокий риск'),
    ]
    risk_category = models.IntegerField('Категория риска (y)', choices=RISK_CHOICES, default=0)
    
    def __str__(self):
        return f"TrainingData #{self.id} - Credit {self.credit_id} - Risk: {self.risk_category}"
    
    class Meta:
        verbose_name = 'Обучающая выборка'
        verbose_name_plural = 'Обучающие выборки'


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


class BankruptcyCheck(models.Model):
    """Проверка банкротства клиента (ЕФРСБ)"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='bankruptcy_checks', verbose_name='Клиент')
    check_date = models.DateTimeField('Дата проверки', auto_now_add=True)
    is_bankrupt = models.BooleanField('Признан банкротом', default=False)
    bankruptcy_case_number = models.CharField('Номер дела', max_length=100, blank=True, default='')
    bankruptcy_date = models.DateField('Дата признания', null=True, blank=True)
    source = models.CharField('Источник данных', max_length=100, default='ЕФРСБ')
    details = models.JSONField('Детали проверки', default=dict, blank=True)

    def __str__(self):
        status = 'Банкрот' if self.is_bankrupt else 'Не банкрот'
        return f"Проверка #{self.id} - {self.client.full_name}: {status}"

    class Meta:
        verbose_name = 'Проверка банкротства'
        verbose_name_plural = 'Проверки банкротства'
        ordering = ['-check_date']


class MLModelVersion(models.Model):
    """Версионирование ML-моделей"""
    name = models.CharField('Название модели', max_length=100)
    version = models.CharField('Версия', max_length=50)
    model_type = models.CharField('Тип алгоритма', max_length=50)  # random_forest, gradient_boosting, logistic_regression
    created_at = models.DateTimeField('Дата обучения', auto_now_add=True)
    
    # Метрики качества
    accuracy = models.FloatField('Accuracy', default=0)
    precision = models.FloatField('Precision', default=0)
    recall = models.FloatField('Recall', default=0)
    f1_score = models.FloatField('F1-Score', default=0)
    roc_auc = models.FloatField('ROC-AUC', default=0)
    
    # Кросс-валидация
    cv_mean = models.FloatField('CV Mean', default=0)
    cv_std = models.FloatField('CV Std', default=0)
    
    # Параметры
    hyperparameters = models.JSONField('Гиперпараметры', default=dict)
    feature_names = models.JSONField('Признаки', default=list)
    feature_importances = models.JSONField('Важность признаков', default=dict)
    confusion_matrix = models.JSONField('Матрица ошибок', default=list)
    
    # ROC-кривая (точки для графика)
    roc_curve_fpr = models.JSONField('ROC FPR', default=list)
    roc_curve_tpr = models.JSONField('ROC TPR', default=list)
    
    training_data_size = models.IntegerField('Размер обучающей выборки', default=0)
    is_active = models.BooleanField('Активная модель', default=True)
    model_path = models.CharField('Путь к файлу модели', max_length=500, blank=True, default='')
    
    def __str__(self):
        return f"{self.name} v{self.version} (ROC-AUC: {self.roc_auc:.4f})"

    class Meta:
        verbose_name = 'Версия ML-модели'
        verbose_name_plural = 'Версии ML-моделей'
        ordering = ['-created_at']


class AuditLog(models.Model):
    """Журнал аудита действий (логирование)"""
    timestamp = models.DateTimeField('Время', auto_now_add=True, db_index=True)
    
    ACTION_CHOICES = [
        ('intervention_create', 'Создание воздействия'),
        ('intervention_update', 'Обновление воздействия'),
        ('assignment_create', 'Назначение клиента'),
        ('assignment_delete', 'Удаление назначения'),
        ('scoring_run', 'Запуск скоринга'),
        ('model_train', 'Обучение модели'),
        ('distribution_run', 'Распределение клиентов'),
        ('compliance_violation', 'Нарушение комплаенса'),
        ('bankruptcy_check', 'Проверка банкротства'),
        ('contact_blocked', 'Контакт заблокирован'),
        ('login', 'Вход в систему'),
        ('logout', 'Выход из системы'),
    ]
    action = models.CharField('Действие', max_length=50, choices=ACTION_CHOICES, db_index=True)
    
    operator = models.ForeignKey(Operator, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Оператор')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Клиент')
    
    details = models.JSONField('Детали', default=dict)
    ip_address = models.GenericIPAddressField('IP-адрес', null=True, blank=True)
    
    SEVERITY_CHOICES = [
        ('info', 'Информация'),
        ('warning', 'Предупреждение'),
        ('error', 'Ошибка'),
        ('critical', 'Критическое'),
    ]
    severity = models.CharField('Серьёзность', max_length=10, choices=SEVERITY_CHOICES, default='info')

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.action} - {self.operator}"

    class Meta:
        verbose_name = 'Запись аудита'
        verbose_name_plural = 'Журнал аудита'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', '-timestamp'], name='idx_audit_action_ts'),
            models.Index(fields=['operator', '-timestamp'], name='idx_audit_op_ts'),
        ]
