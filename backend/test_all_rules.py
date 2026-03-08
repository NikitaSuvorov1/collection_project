"""
==========================================================================
  ПОЛНЫЕ ТЕСТ-КЕЙСЫ СИСТЕМЫ COLLECTION APP
  230-ФЗ • Банкротство • Smart Distribution • ML Scoring • API
==========================================================================

Запуск:
    cd backend
    py test_all_rules.py

Каждый тест-кейс выводит:
    ✅ PASS  — правило работает корректно
    ❌ FAIL  — правило НЕ работает (описание ошибки)
"""

import os, sys, json
os.environ['DJANGO_SETTINGS_MODULE'] = 'collection.settings'

import django
django.setup()

from datetime import timedelta, date
from decimal import Decimal
from django.utils import timezone
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory

from collection_app.models import (
    Client, Credit, Intervention, Operator, Assignment,
    ScoringResult, AuditLog, BankruptcyCheck, MLModelVersion,
)
from collection_app.services.compliance_230fz import (
    can_contact, validate_intervention, log_compliance_violation,
    check_bankruptcy, get_compliance_summary,
    LIMITS, ALLOWED_HOURS, MIN_CALL_INTERVAL_HOURS,
)
from collection_app.services.distribution import DistributionService


# ─────────────────────────────────────────────────────────
#  Тестовая инфраструктура
# ─────────────────────────────────────────────────────────
PASSED = 0
FAILED = 0
TOTAL  = 0

def test(name, condition, detail=''):
    global PASSED, FAILED, TOTAL
    TOTAL += 1
    if condition:
        PASSED += 1
        print(f'  ✅ {name}')
    else:
        FAILED += 1
        extra = f' — {detail}' if detail else ''
        print(f'  ❌ {name}{extra}')


def section(title):
    print(f'\n{"─"*65}')
    print(f'  {title}')
    print(f'{"─"*65}')


def get_test_client():
    """Получить или создать чистого тестового клиента."""
    c, _ = Client.objects.get_or_create(
        full_name='__TEST_CLIENT_230FZ__',
        defaults={
            'birth_date': '1990-01-15',
            'gender': 'M',
            'income': 80000,
            'contact_refused': False,
            'is_bankrupt': False,
            'refused_channels': [],
            'third_party_consent': False,
        }
    )
    # Сбросить в чистое состояние
    c.contact_refused = False
    c.contact_refused_date = None
    c.is_bankrupt = False
    c.bankruptcy_date = None
    c.refused_channels = []
    c.third_party_consent = False
    c.third_party_consent_date = None
    c.save()
    # Удалить все тестовые интервенции
    Intervention.objects.filter(client=c).delete()
    return c

def get_test_operator():
    op, _ = Operator.objects.get_or_create(
        full_name='__TEST_OPERATOR__',
        defaults={
            'role': 'operator',
            'status': 'active',
            'hire_date': date(2023, 1, 1),
            'current_load': 0,
        }
    )
    op.current_load = 0
    op.status = 'active'
    op.hire_date = date(2023, 1, 1)
    op.save()
    return op

def get_test_credit(client):
    cr = Credit.objects.filter(client=client).first()
    if not cr:
        cr = Credit.objects.create(
            client=client,
            open_date='2024-01-01',
            planned_close_date='2025-01-01',
            principal_amount=100000,
            interest_rate=15,
            monthly_payment=9000,
            status='overdue',
        )
    return cr

def create_intervention(client, credit, operator, contact_type='phone',
                        hours_ago=0, status='completed'):
    """Создать интервенцию с указанным смещением по времени."""
    dt = timezone.now() - timedelta(hours=hours_ago)
    return Intervention.objects.create(
        client=client,
        credit=credit,
        operator=operator,
        intervention_type=contact_type,
        datetime=dt,
        status=status,
    )


# =================================================================
#  БЛОК 1: 230-ФЗ — ФУНКЦИЯ can_contact()
# =================================================================

section('БЛОК 1: 230-ФЗ — can_contact()')

c = get_test_client()
op = get_test_operator()
cr = get_test_credit(c)

# ── Ст.7: Банкротство ──
print('\n  ▸ Ст.7: Банкротство')
c.is_bankrupt = True
c.bankruptcy_date = date.today()
c.save()
r = can_contact(c.id, 'phone')
test('TC-01: Банкрот → контакт запрещён',
     r['allowed'] is False and r['checks']['bankruptcy'] is True)
test('TC-02: Банкрот → причина содержит "банкрот"',
     'банкрот' in (r['reason'] or '').lower())

c.is_bankrupt = False
c.bankruptcy_date = None
c.save()
r = can_contact(c.id, 'phone')
test('TC-03: Не банкрот → bankruptcy=False',
     r['checks']['bankruptcy'] is False)


# ── Ст.3: Полный отказ от взаимодействия ──
print('\n  ▸ Ст.3: Отказ от взаимодействия')
c.contact_refused = True
c.contact_refused_date = date.today()
c.refused_channels = []  # пустой = полный отказ
c.save()
r = can_contact(c.id, 'phone')
test('TC-04: Полный отказ → контакт запрещён',
     r['allowed'] is False and r['checks']['refused'] is True)
test('TC-05: Полный отказ → звонки запрещены',
     r['allowed'] is False)
r2 = can_contact(c.id, 'sms')
test('TC-06: Полный отказ → SMS тоже запрещены',
     r2['allowed'] is False)

# ── Ст.3: Частичный отказ (по каналам) ──
c.contact_refused = True
c.refused_channels = ['sms']
c.save()
r = can_contact(c.id, 'phone')
test('TC-07: Отказ от SMS → звонок разрешён',
     r['checks'].get('refused', None) is False)
r = can_contact(c.id, 'sms')
test('TC-08: Отказ от SMS → SMS запрещён',
     'Ст.3' in str(r['violations']))

c.contact_refused = True
c.refused_channels = ['phone', 'sms']
c.save()
r_phone = can_contact(c.id, 'phone')
r_email = can_contact(c.id, 'email')
test('TC-09: Отказ phone+sms → email разрешён',
     r_email['checks'].get('refused', None) is False)
test('TC-10: Отказ phone+sms → phone запрещён',
     'Ст.3' in str(r_phone['violations']))

c.contact_refused = False
c.refused_channels = []
c.save()


# ── Ст.4: Третьи лица ──
print('\n  ▸ Ст.4: Третьи лица')
c.third_party_consent = False
c.save()
r = can_contact(c.id, 'phone', is_third_party=True)
test('TC-11: Третье лицо без согласия → запрещён',
     r['checks']['third_party_ok'] is False)
test('TC-12: Третье лицо без согласия → violation содержит Ст.4',
     'Ст.4' in str(r['violations']))

c.third_party_consent = True
c.third_party_consent_date = date.today()
c.save()
r = can_contact(c.id, 'phone', is_third_party=True)
test('TC-13: Третье лицо с согласием → разрешён',
     r['checks']['third_party_ok'] is True)

# Не третье лицо — всегда ok
c.third_party_consent = False
c.save()
r = can_contact(c.id, 'phone', is_third_party=False)
test('TC-14: Контакт с клиентом (не третье лицо) → third_party_ok=True',
     r['checks']['third_party_ok'] is True)


# ── Ст.1: Время контакта ──
print('\n  ▸ Ст.1: Ограничения по времени')
now = timezone.now()
hour = now.hour
weekday = now.weekday()
if weekday < 5:
    min_h, max_h = ALLOWED_HOURS['weekday']
else:
    min_h, max_h = ALLOWED_HOURS['weekend']
expected_time_ok = min_h <= hour < max_h

r = can_contact(c.id, 'phone')
test(f'TC-15: Текущее время {hour:02d}:00 → time_ok={expected_time_ok}',
     r['checks']['time_ok'] == expected_time_ok,
     f'got time_ok={r["checks"]["time_ok"]}')

test('TC-16: Будни разрешены 08–22',
     ALLOWED_HOURS['weekday'] == (8, 22))
test('TC-17: Выходные разрешены 09–20',
     ALLOWED_HOURS['weekend'] == (9, 20))


# ── Ст.2: Лимиты частоты ──
print('\n  ▸ Ст.2: Лимиты частоты контактов')
Intervention.objects.filter(client=c).delete()

test('TC-18: Лимит звонков: 1/день, 2/нед, 8/мес',
     LIMITS['calls_per_day'] == 1 and
     LIMITS['calls_per_week'] == 2 and
     LIMITS['calls_per_month'] == 8)
test('TC-19: Лимит SMS: 2/день, 4/нед, 16/мес',
     LIMITS['sms_per_day'] == 2 and
     LIMITS['sms_per_week'] == 4 and
     LIMITS['sms_per_month'] == 16)

# 0 звонков → разрешено
r = can_contact(c.id, 'phone')
test('TC-20: 0 звонков за день → frequency_ok=True',
     r['checks']['frequency_ok'] is True and r['counts']['day'] == 0)

# Создаём 1 звонок сегодня (с достаточным интервалом чтобы interval_ok тоже был ok)
create_intervention(c, cr, op, 'phone', hours_ago=5)
r = can_contact(c.id, 'phone')
test('TC-21: 1 звонок за день (лимит 1) → frequency_ok=False',
     r['checks']['frequency_ok'] is False,
     f'day={r["counts"]["day"]}, freq_ok={r["checks"]["frequency_ok"]}')
test('TC-22: Violations содержат "Превышен лимит за день"',
     any('лимит за день' in v.lower() for v in r['violations']),
     str(r['violations']))

# SMS: 2/день
Intervention.objects.filter(client=c).delete()
create_intervention(c, cr, op, 'sms', hours_ago=6)
r = can_contact(c.id, 'sms')
test('TC-23: 1 SMS за день (лимит 2) → frequency_ok=True',
     r['checks']['frequency_ok'] is True,
     f'day={r["counts"]["day"]}')

create_intervention(c, cr, op, 'sms', hours_ago=5)
r = can_contact(c.id, 'sms')
test('TC-24: 2 SMS за день (лимит 2) → frequency_ok=False',
     r['checks']['frequency_ok'] is False,
     f'day={r["counts"]["day"]}')

# Недельный лимит звонков
Intervention.objects.filter(client=c).delete()
create_intervention(c, cr, op, 'phone', hours_ago=48)   # 2 дня назад
create_intervention(c, cr, op, 'phone', hours_ago=72)   # 3 дня назад
r = can_contact(c.id, 'phone')
test('TC-25: 2 звонка за неделю (лимит 2) → frequency_ok=False',
     r['checks']['frequency_ok'] is False,
     f'week={r["counts"]["week"]}')


# ── Ст.9: Минимальный интервал между звонками ──
print('\n  ▸ Ст.9: Интервал 4 часа')
Intervention.objects.filter(client=c).delete()

test('TC-26: MIN_CALL_INTERVAL_HOURS == 4',
     MIN_CALL_INTERVAL_HOURS == 4)

# Звонок 2 часа назад → интервал НЕ соблюдён
create_intervention(c, cr, op, 'phone', hours_ago=2)
r = can_contact(c.id, 'phone')
test('TC-27: Последний звонок 2ч назад → interval_ok=False',
     r['checks']['interval_ok'] is False,
     f'interval_ok={r["checks"]["interval_ok"]}')

# Звонок 5 часов назад → интервал соблюдён
Intervention.objects.filter(client=c).delete()
create_intervention(c, cr, op, 'phone', hours_ago=5)
r = can_contact(c.id, 'phone')
test('TC-28: Последний звонок 5ч назад → interval_ok=True',
     r['checks']['interval_ok'] is True)

# Нет звонков → интервал ok
Intervention.objects.filter(client=c).delete()
r = can_contact(c.id, 'phone')
test('TC-29: Нет звонков → interval_ok=True',
     r['checks']['interval_ok'] is True)

# Клинап
Intervention.objects.filter(client=c).delete()


# =================================================================
#  БЛОК 2: 230-ФЗ — validate_intervention() (пост-валидация)
# =================================================================

section('БЛОК 2: 230-ФЗ — validate_intervention()')

# ── Ст.6: Идентификация оператора ──
print('\n  ▸ Ст.6: Идентификация оператора')
v = validate_intervention({'intervention_type': 'phone'})
test('TC-30: Нет operator/operator_id → violation Ст.6',
     any('Ст.6' in x for x in v['violations']),
     str(v['violations']))

v = validate_intervention({'intervention_type': 'phone', 'operator_id': op.id})
test('TC-31: Есть operator_id → нет violation про "не указан"',
     not any('Не указан оператор' in x for x in v['violations']))

v = validate_intervention({
    'intervention_type': 'phone',
    'operator_id': op.id,
    'operator_identified': False,
})
test('TC-32: operator_identified=False → violation "не представился"',
     any('не представился' in x.lower() for x in v['violations']),
     str(v['violations']))

v = validate_intervention({
    'intervention_type': 'phone',
    'operator_id': op.id,
    'operator_identified': True,
})
test('TC-33: operator_identified=True → нет violation',
     v['valid'] is True, str(v))


# ── Ст.8: Скрытый номер ──
print('\n  ▸ Ст.8: Запрет скрытого номера')
v = validate_intervention({
    'intervention_type': 'phone',
    'operator_id': op.id,
    'caller_number': '',
})
test('TC-34: Пустой caller_number → warning Ст.8',
     any('Ст.8' in w for w in v['warnings']),
     str(v['warnings']))

v = validate_intervention({
    'intervention_type': 'phone',
    'operator_id': op.id,
    'caller_number': '+74951234567',
})
test('TC-35: Есть caller_number → нет warning Ст.8',
     not any('Ст.8' in w for w in v['warnings']))


# ── Ст.5: Утверждённый скрипт ──
print('\n  ▸ Ст.5: Утверждённый скрипт')
v = validate_intervention({
    'intervention_type': 'phone',
    'operator_id': op.id,
    'approved_script_used': False,
})
test('TC-36: approved_script_used=False → warning Ст.5',
     any('Ст.5' in w for w in v['warnings']))

v = validate_intervention({
    'intervention_type': 'phone',
    'operator_id': op.id,
    'approved_script_used': True,
})
test('TC-37: approved_script_used=True → нет warning Ст.5',
     not any('Ст.5' in w for w in v['warnings']))


# ── Ст.4: Третьи лица через validate_intervention ──
print('\n  ▸ Ст.4: Третьи лица (пост-валидация)')
c.third_party_consent = False
c.save()
v = validate_intervention({
    'intervention_type': 'phone',
    'operator_id': op.id,
    'is_third_party': True,
    'client_id': c.id,
})
test('TC-38: is_third_party + нет согласия → violation Ст.4',
     any('Ст.4' in x for x in v['violations']))

c.third_party_consent = True
c.save()
v = validate_intervention({
    'intervention_type': 'phone',
    'operator_id': op.id,
    'is_third_party': True,
    'client_id': c.id,
})
test('TC-39: is_third_party + есть согласие → нет violation Ст.4',
     not any('Ст.4' in x for x in v['violations']))
c.third_party_consent = False
c.save()


# =================================================================
#  БЛОК 3: БАНКРОТСТВО
# =================================================================

section('БЛОК 3: Банкротство (ст.7)')

# ── check_bankruptcy() ──
c = get_test_client()
c.is_bankrupt = True
c.bankruptcy_date = date.today()
c.save()

result = check_bankruptcy(c.id)
test('TC-40: check_bankruptcy → is_bankrupt=True',
     result['is_bankrupt'] is True)
test('TC-41: check_bankruptcy → создана запись BankruptcyCheck',
     BankruptcyCheck.objects.filter(id=result['check_id']).exists())
test('TC-42: check_bankruptcy → AuditLog запись',
     AuditLog.objects.filter(action='bankruptcy_check', client_id=c.id).exists())

c.is_bankrupt = False
c.bankruptcy_date = None
c.save()
result = check_bankruptcy(c.id)
test('TC-43: Не банкрот → is_bankrupt=False',
     result['is_bankrupt'] is False)

# ── Исключение банкротов из Assignments queryset ──
c.is_bankrupt = True
c.bankruptcy_date = date.today()
c.save()
cr = get_test_credit(c)
Assignment.objects.filter(credit=cr).delete()
a = Assignment.objects.create(
    operator=op, client=c, credit=cr,
    debtor_name=c.full_name,
    overdue_amount=50000, overdue_days=30,
    priority=3, assignment_date=date.today(),
)
from collection_app.views import AssignmentViewSet
factory = APIRequestFactory()
request = factory.get('/api/assignments/')
view = AssignmentViewSet.as_view({'get': 'list'})
response = view(request)
assignment_ids = [x['id'] for x in response.data]
test('TC-44: Банкрот исключён из assignments queryset',
     a.id not in assignment_ids,
     f'assignment {a.id} в списке: {a.id in assignment_ids}')

# Убираем банкротство — должно появиться
c.is_bankrupt = False
c.save()
response = view(request)
assignment_ids = [x['id'] for x in response.data]
test('TC-45: Не банкрот → assignment видно в списке',
     a.id in assignment_ids)

# Клинап
a.delete()
c.is_bankrupt = False
c.bankruptcy_date = None
c.save()


# =================================================================
#  БЛОК 4: ИСКЛЮЧЕНИЕ ОТКАЗНИКОВ ИЗ ОЧЕРЕДИ
# =================================================================

section('БЛОК 4: Отказники исключены из очереди')

c = get_test_client()
cr = get_test_credit(c)
Assignment.objects.filter(credit=cr).delete()
a = Assignment.objects.create(
    operator=op, client=c, credit=cr,
    debtor_name=c.full_name,
    overdue_amount=50000, overdue_days=30,
    priority=3, assignment_date=date.today(),
)

c.contact_refused = True
c.contact_refused_date = date.today()
c.save()
request = factory.get('/api/assignments/')
response = view(request)
ids = [x['id'] for x in response.data]
test('TC-46: Отказник исключён из assignments',
     a.id not in ids)

c.contact_refused = False
c.save()
response = view(request)
ids = [x['id'] for x in response.data]
test('TC-47: Не отказник → assignment видно',
     a.id in ids)

a.delete()


# =================================================================
#  БЛОК 5: SMART DISTRIBUTION
# =================================================================

section('БЛОК 5: Smart Distribution')

ds = DistributionService(max_load_per_operator=60)

# ── Расчёт опыта оператора ──
print('\n  ▸ Расчёт опыта оператора')
exp = ds.calculate_operator_experience(op)
test('TC-48: calculate_operator_experience → total_score > 0',
     exp['total_score'] > 0,
     f'total_score={exp["total_score"]}')
test('TC-49: Есть tenure_score, role_score, success_score',
     all(k in exp for k in ['tenure_score', 'role_score', 'success_score']))

# ── Приоритет клиента ──
print('\n  ▸ Расчёт приоритета клиента')
c = get_test_client()
cr = get_test_credit(c)
prio = ds.calculate_client_priority(cr)
test('TC-50: calculate_client_priority → total_priority >= 0',
     prio['total_priority'] >= 0,
     f'total_priority={prio["total_priority"]}')
test('TC-51: Есть overdue_amount, days_overdue, risk_segment',
     all(k in prio for k in ['overdue_amount', 'days_overdue', 'risk_segment']))

# ── Маршрутизация ──
print('\n  ▸ Smart Routing')
# Создаём операторов с разным опытом
junior = Operator.objects.filter(role__in=['junior_operator', 'operator']).first()
senior = Operator.objects.filter(role__in=['senior_operator', 'supervisor', 'manager']).first()

if junior and senior:
    ops = [junior, senior]
    best_op, match_info = ds.get_recommended_operator(cr, ops)
    test('TC-52: get_recommended_operator → возвращает оператора',
         best_op is not None,
         f'best_op={best_op}')
    test('TC-53: match_info содержит match_quality',
         'match_quality' in match_info,
         str(match_info.keys()))
else:
    test('TC-52: get_recommended_operator → (SKIP: нет junior/senior)',
         False, 'Недостаточно операторов с разными ролями')
    test('TC-53: match_info → (SKIP)', False, '')

# ── Лимит нагрузки ──
print('\n  ▸ Лимит нагрузки оператора')
op_overloaded = get_test_operator()
op_overloaded.current_load = 60
op_overloaded.save()

best, info = ds.get_recommended_operator(cr, [op_overloaded])
test('TC-54: Перегруженный оператор (load=60/60) → None',
     best is None,
     f'got {best}')

op_overloaded.current_load = 0
op_overloaded.save()


# =================================================================
#  БЛОК 6: ML SCORING PIPELINE
# =================================================================

section('БЛОК 6: ML Scoring Pipeline')

# ── Наличие ScoringResult ──
scoring_count = ScoringResult.objects.count()
test('TC-55: Есть записи в ScoringResult',
     scoring_count > 0,
     f'count={scoring_count}')

if scoring_count > 0:
    sr = ScoringResult.objects.exclude(score_value__isnull=True).first()
    if sr:
        test('TC-56: ScoringResult.score_value заполнен',
             sr.score_value is not None,
             f'score_value={sr.score_value}')
        test('TC-57: ScoringResult.risk_segment заполнен',
             sr.risk_segment not in [None, ''],
             f'risk_segment={sr.risk_segment}')
    else:
        test('TC-56: ScoringResult.score_value → (нет данных)', False, 'score_value=None')
        test('TC-57: ScoringResult.risk_segment → (нет данных)', False, '')

# ── Версионирование моделей ──
model_count = MLModelVersion.objects.count()
test('TC-58: Есть записи в MLModelVersion',
     model_count > 0,
     f'count={model_count}')

if model_count > 0:
    mv = MLModelVersion.objects.order_by('-created_at').first()
    test('TC-59: MLModelVersion.model_type заполнен',
         mv.model_type not in [None, ''],
         f'model_type={mv.model_type}')
    test('TC-60: MLModelVersion.roc_auc > 0',
         mv.roc_auc is not None and mv.roc_auc > 0,
         f'roc_auc={mv.roc_auc}')
    test('TC-61: MLModelVersion.hyperparameters заполнен',
         mv.hyperparameters not in [None, {}, ''],
         f'hyperparameters={mv.hyperparameters}')
else:
    test('TC-59: MLModelVersion → (нет данных)', False, 'Запустите full_scoring_pipeline')
    test('TC-60: ROC-AUC → (нет данных)', False, '')
    test('TC-61: Metrics → (нет данных)', False, '')


# =================================================================
#  БЛОК 7: АУДИТ (Ст.10, Ст.11)
# =================================================================

section('БЛОК 7: Аудит (Ст.10 + Ст.11)')

# ── log_compliance_violation ──
c = get_test_client()
before = AuditLog.objects.count()
log_compliance_violation(c.id, op.id, ['Тестовое нарушение'], action='contact_blocked')
after = AuditLog.objects.count()
test('TC-62: log_compliance_violation → создаёт AuditLog',
     after == before + 1)

log_entry = AuditLog.objects.order_by('-id').first()
test('TC-63: AuditLog.action = contact_blocked',
     log_entry.action == 'contact_blocked')
test('TC-64: AuditLog.severity = warning',
     log_entry.severity == 'warning')
test('TC-65: AuditLog.details содержит violations',
     'violations' in (log_entry.details or {}),
     str(log_entry.details))


# ── Ст.10: Хранение истории интервенций ──
total_interventions = Intervention.objects.count()
test('TC-66: Ст.10: История воздействий сохраняется',
     total_interventions > 0,
     f'count={total_interventions}')


# =================================================================
#  БЛОК 8: API COMPLIANCE ENDPOINTS
# =================================================================

section('БЛОК 8: API Endpoints')

# ── /api/compliance/summary/ ──
summary = get_compliance_summary()
test('TC-67: get_compliance_summary() → compliance_rate число',
     isinstance(summary['compliance_rate'], (int, float)),
     f'type={type(summary["compliance_rate"])}')
test('TC-68: compliance_summary → rules_covered = 11',
     len(summary['rules_covered']) == 11,
     f'count={len(summary["rules_covered"])}')
test('TC-69: compliance_summary → blocked_contacts >= 0',
     summary['blocked_contacts'] >= 0)
test('TC-70: compliance_summary → bankrupt_clients >= 0',
     summary['bankrupt_clients'] >= 0)

# ── can_contact() возвращает структуру ──
c = get_test_client()
r = can_contact(c.id, 'phone')
test('TC-71: can_contact → ключ "allowed" в ответе',
     'allowed' in r)
test('TC-72: can_contact → ключ "checks" в ответе',
     'checks' in r)
test('TC-73: can_contact → ключ "limits" в ответе',
     'limits' in r)
test('TC-74: can_contact → ключ "counts" в ответе',
     'counts' in r)
test('TC-75: can_contact → ключ "violations" в ответе',
     'violations' in r)


# =================================================================
#  БЛОК 9: КОМПЛЕКСНЫЕ СЦЕНАРИИ
# =================================================================

section('БЛОК 9: Комплексные сценарии')

# ── Сценарий 1: Банкрот + отказ одновременно ──
print('\n  ▸ Сценарий: банкрот + отказ')
c = get_test_client()
c.is_bankrupt = True
c.bankruptcy_date = date.today()
c.contact_refused = True
c.save()
r = can_contact(c.id, 'phone')
test('TC-76: Банкрот+отказ → блокировка по банкротству (приоритет)',
     r['allowed'] is False and r['checks']['bankruptcy'] is True)
c.is_bankrupt = False
c.contact_refused = False
c.save()

# ── Сценарий 2: Чистый клиент → всё разрешено ──
print('\n  ▸ Сценарий: чистый клиент')
c = get_test_client()
Intervention.objects.filter(client=c).delete()
r = can_contact(c.id, 'phone')
all_checks_ok = (
    r['checks']['bankruptcy'] is False and
    r['checks']['refused'] is False and
    r['checks']['third_party_ok'] is True and
    r['checks']['frequency_ok'] is True and
    r['checks']['interval_ok'] is True
)
if r['checks']['time_ok']:
    test('TC-77: Чистый клиент → allowed=True',
         r['allowed'] is True and all_checks_ok)
else:
    test('TC-77: Чистый клиент → allowed=False (только из-за времени)',
         r['allowed'] is False and
         r['checks']['frequency_ok'] is True and
         r['checks']['interval_ok'] is True)

# ── Сценарий 3: Несуществующий клиент ──
print('\n  ▸ Сценарий: несуществующий клиент')
r = can_contact(999999, 'phone')
test('TC-78: Несуществующий client_id → allowed=False',
     r['allowed'] is False)
test('TC-79: Несуществующий client_id → reason содержит "не найден"',
     'не найден' in (r.get('reason') or '').lower())

# ── Сценарий 4: Полный цикл интервенции ──
print('\n  ▸ Сценарий: полный цикл интервенции')
c = get_test_client()
Intervention.objects.filter(client=c).delete()
audit_before = AuditLog.objects.count()

# Шаг 1: Проверка → разрешено
r1 = can_contact(c.id, 'phone')
step1_ok = r1['allowed'] is True or r1['checks']['time_ok'] is False  # может быть ночь

# Шаг 2: Валидация данных
v = validate_intervention({
    'intervention_type': 'phone',
    'operator_id': op.id,
    'caller_number': '+79001234567',
    'operator_identified': True,
    'approved_script_used': True,
})
step2_ok = v['valid'] is True and len(v['warnings']) == 0

# Шаг 3: Создаём интервенцию
i = create_intervention(c, cr, op, 'phone', hours_ago=0)
step3_ok = i.id is not None

# Шаг 4: Повторный звонок → blocked (дневной лимит)
r4 = can_contact(c.id, 'phone')
step4_ok = r4['checks']['frequency_ok'] is False  # уже 1/1

test('TC-80: Цикл: шаг 1 — проверка разрешения',
     step1_ok)
test('TC-81: Цикл: шаг 2 — валидация данных ok',
     step2_ok, str(v))
test('TC-82: Цикл: шаг 3 — интервенция создана',
     step3_ok)
test('TC-83: Цикл: шаг 4 — повторный звонок blocked (лимит 1/день)',
     step4_ok,
     f'day={r4["counts"]["day"]}, freq={r4["checks"]["frequency_ok"]}')

# Шаг 5: SMS ещё можно (другой тип)
r5 = can_contact(c.id, 'sms')
test('TC-84: Цикл: шаг 5 — SMS после звонка всё ещё разрешён',
     r5['checks']['frequency_ok'] is True,
     f'sms day={r5["counts"]["day"]}')

Intervention.objects.filter(client=c).delete()


# =================================================================
#  БЛОК 10: МОДЕЛИ (поля 230-ФЗ)
# =================================================================

section('БЛОК 10: Модели — поля 230-ФЗ')

# ── Client ──
print('\n  ▸ Поля Client')
test('TC-85: Client.contact_refused существует',
     hasattr(Client, 'contact_refused'))
test('TC-86: Client.contact_refused_date существует',
     hasattr(Client, 'contact_refused_date'))
test('TC-87: Client.refused_channels существует (JSONField)',
     hasattr(Client, 'refused_channels'))
test('TC-88: Client.is_bankrupt существует',
     hasattr(Client, 'is_bankrupt'))
test('TC-89: Client.bankruptcy_date существует',
     hasattr(Client, 'bankruptcy_date'))
test('TC-90: Client.third_party_consent существует',
     hasattr(Client, 'third_party_consent'))
test('TC-91: Client.third_party_consent_date существует',
     hasattr(Client, 'third_party_consent_date'))

# ── Intervention ──
print('\n  ▸ Поля Intervention')
test('TC-92: Intervention.caller_number существует',
     hasattr(Intervention, 'caller_number'))
test('TC-93: Intervention.operator_identified существует',
     hasattr(Intervention, 'operator_identified'))
test('TC-94: Intervention.approved_script_used существует',
     hasattr(Intervention, 'approved_script_used'))
test('TC-95: Intervention.is_third_party существует',
     hasattr(Intervention, 'is_third_party'))

# ── Assignment ──
print('\n  ▸ Поля Assignment (A/B тестирование)')
test('TC-96: Assignment.ab_group существует',
     hasattr(Assignment, 'ab_group'))
test('TC-97: Assignment.assignment_method существует',
     hasattr(Assignment, 'assignment_method'))
test('TC-98: Assignment.match_score существует',
     hasattr(Assignment, 'match_score'))

# ── BankruptcyCheck ──
print('\n  ▸ Модель BankruptcyCheck')
test('TC-99: Модель BankruptcyCheck существует',
     BankruptcyCheck is not None)
bc = BankruptcyCheck.objects.first()
test('TC-100: BankruptcyCheck записи в БД',
     BankruptcyCheck.objects.exists())


# =================================================================
#  ИТОГИ
# =================================================================

print('\n' + '=' * 65)
print(f'  ИТОГО: {PASSED} ✅  /  {FAILED} ❌  /  {TOTAL} всего')
pct = round(PASSED / TOTAL * 100, 1) if TOTAL else 0
if FAILED == 0:
    print(f'  🎉 ВСЕ {TOTAL} ТЕСТОВ ПРОЙДЕНЫ ({pct}%)')
else:
    print(f'  ⚠️  Процент успеха: {pct}%')
print('=' * 65)


# Очистка тестовых данных
Client.objects.filter(full_name='__TEST_CLIENT_230FZ__').delete()
Operator.objects.filter(full_name='__TEST_OPERATOR__').delete()
