"""
Тесты для Collection App — покрытие ключевых сервисов.

Группы:
  1. Модели (Client, Credit, ViolationLog)
  2. 230-ФЗ compliance (can_contact, log_compliance_violation)
  3. Распределение (DistributionService)
  4. Банкротство
  5. API endpoints
  6. Delinquency buckets
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    Client, Credit, CreditState, Intervention, Operator, Assignment,
    ScoringResult, ViolationLog, AuditLog,
)


# =====================================================================
# Helpers
# =====================================================================

def _make_client(**kwargs):
    defaults = dict(
        full_name='Иван Петров',
        phone_mobile='+79991112233', gender='M', birth_date=date(1990, 5, 15),
        income=Decimal('80000'), monthly_expenses=Decimal('30000'),
        employment='employed', children_count=1,
    )
    defaults.update(kwargs)
    return Client.objects.create(**defaults)


def _make_operator(**kwargs):
    defaults = dict(full_name='Оператор Тест', role='operator')
    defaults.update(kwargs)
    return Operator.objects.create(**defaults)


def _make_credit(client, **kwargs):
    defaults = dict(
        client=client,
        open_date=date.today() - timedelta(days=365),
        planned_close_date=date.today() + timedelta(days=365),
        principal_amount=Decimal('500000'),
        monthly_payment=Decimal('15000'),
        interest_rate=Decimal('12.5'),
        product_type='consumer',
        status='active',
    )
    defaults.update(kwargs)
    return Credit.objects.create(**defaults)


# =====================================================================
# 1. Тесты моделей
# =====================================================================

class ClientModelTest(TestCase):
    def test_client_creation(self):
        c = _make_client()
        self.assertEqual(str(c), 'Иван Петров')

    def test_contact_refused_default(self):
        c = _make_client()
        self.assertFalse(c.contact_refused)

    def test_bankruptcy_default(self):
        c = _make_client()
        self.assertFalse(c.is_bankrupt)


class CreditModelTest(TestCase):
    def test_credit_creation(self):
        c = _make_client()
        cr = _make_credit(c)
        self.assertIn('Кредит #', str(cr))

    def test_delinquency_bucket_current(self):
        c = _make_client()
        cr = _make_credit(c)
        self.assertEqual(cr.delinquency_bucket, 'current')

    def test_delinquency_bucket_30(self):
        c = _make_client()
        cr = _make_credit(c, status='overdue')
        CreditState.objects.create(
            credit=cr, state_date=date.today(),
            principal_debt=Decimal('490000'), overdue_principal=Decimal('15000'),
            overdue_days=20,
        )
        self.assertEqual(cr.delinquency_bucket, '0-30')

    def test_delinquency_bucket_60(self):
        c = _make_client()
        cr = _make_credit(c, status='overdue')
        CreditState.objects.create(
            credit=cr, state_date=date.today(),
            principal_debt=Decimal('490000'), overdue_principal=Decimal('30000'),
            overdue_days=45,
        )
        self.assertEqual(cr.delinquency_bucket, '30-60')

    def test_delinquency_bucket_90(self):
        c = _make_client()
        cr = _make_credit(c, status='overdue')
        CreditState.objects.create(
            credit=cr, state_date=date.today(),
            principal_debt=Decimal('490000'), overdue_principal=Decimal('45000'),
            overdue_days=75,
        )
        self.assertEqual(cr.delinquency_bucket, '60-90')

    def test_delinquency_bucket_90_plus(self):
        c = _make_client()
        cr = _make_credit(c, status='default')
        CreditState.objects.create(
            credit=cr, state_date=date.today(),
            principal_debt=Decimal('490000'), overdue_principal=Decimal('60000'),
            overdue_days=120,
        )
        self.assertEqual(cr.delinquency_bucket, '90+')

    def test_days_past_due_property(self):
        c = _make_client()
        cr = _make_credit(c, status='overdue')
        CreditState.objects.create(
            credit=cr, state_date=date.today(),
            principal_debt=Decimal('490000'), overdue_principal=Decimal('15000'),
            overdue_days=42,
        )
        self.assertEqual(cr.days_past_due, 42)


class ViolationLogModelTest(TestCase):
    def test_violation_creation(self):
        c = _make_client()
        op = _make_operator()
        v = ViolationLog.objects.create(
            client=c, operator=op, rule_type='st2_frequency',
            description='Ст.2: Превышен лимит за день: 1/1',
        )
        self.assertIn('Ст.2', str(v))
        self.assertEqual(v.severity, 'medium')
        self.assertTrue(v.action_blocked)


# =====================================================================
# 2. Тесты 230-ФЗ compliance
# =====================================================================

class ComplianceContactTest(TestCase):
    """Тесты can_contact() из compliance_230fz."""

    def setUp(self):
        self.client_obj = _make_client()
        self.operator = _make_operator()

    def test_allowed_basic(self):
        from .services.compliance_230fz import can_contact
        with patch('collection_app.services.compliance_230fz.timezone') as mock_tz:
            mock_now = timezone.now().replace(hour=12, minute=0, second=0)
            while mock_now.weekday() >= 5:
                mock_now += timedelta(days=1)
            mock_tz.now.return_value = mock_now
            result = can_contact(self.client_obj.id, 'phone')
        self.assertTrue(result['allowed'])
        self.assertEqual(len(result['violations']), 0)

    def test_bankruptcy_blocks(self):
        from .services.compliance_230fz import can_contact
        self.client_obj.is_bankrupt = True
        self.client_obj.bankruptcy_date = date.today()
        self.client_obj.save()
        result = can_contact(self.client_obj.id, 'phone')
        self.assertFalse(result['allowed'])
        self.assertTrue(result['checks']['bankruptcy'])
        self.assertTrue(any('Ст.7' in v for v in result['violations']))

    def test_refusal_blocks(self):
        from .services.compliance_230fz import can_contact
        self.client_obj.contact_refused = True
        self.client_obj.contact_refused_date = date.today()
        self.client_obj.save()
        result = can_contact(self.client_obj.id, 'phone')
        self.assertFalse(result['allowed'])
        self.assertTrue(any('Ст.3' in v for v in result['violations']))

    def test_channel_refusal_blocks_specific(self):
        from .services.compliance_230fz import can_contact
        self.client_obj.contact_refused = True
        self.client_obj.contact_refused_date = date.today()
        self.client_obj.refused_channels = ['sms']
        self.client_obj.save()
        result = can_contact(self.client_obj.id, 'sms')
        self.assertTrue(any('Ст.3' in v for v in result['violations']))

    def test_daily_call_limit(self):
        from .services.compliance_230fz import can_contact
        cr = _make_credit(self.client_obj)
        Intervention.objects.create(
            client=self.client_obj, credit=cr, operator=self.operator,
            intervention_type='phone', status='completed',
            datetime=timezone.now() - timedelta(hours=5),
        )
        with patch('collection_app.services.compliance_230fz.timezone') as mock_tz:
            mock_now = timezone.now().replace(hour=14, minute=0)
            while mock_now.weekday() >= 5:
                mock_now += timedelta(days=1)
            mock_tz.now.return_value = mock_now
            result = can_contact(self.client_obj.id, 'phone')
        self.assertFalse(result['checks']['frequency_ok'])
        self.assertTrue(any('день' in v for v in result['violations']))

    def test_client_not_found(self):
        from .services.compliance_230fz import can_contact
        result = can_contact(999999, 'phone')
        self.assertFalse(result['allowed'])
        self.assertIn('client_not_found', result['violations'])

    def test_third_party_no_consent(self):
        from .services.compliance_230fz import can_contact
        result = can_contact(self.client_obj.id, 'phone', is_third_party=True)
        self.assertTrue(any('Ст.4' in v for v in result['violations']))


class ComplianceLogTest(TestCase):
    """Тесты log_compliance_violation()."""

    def test_creates_violation_log_entries(self):
        c = _make_client()
        op = _make_operator()
        from .services.compliance_230fz import log_compliance_violation
        log_compliance_violation(
            c.id, op.id,
            ['Ст.2: Превышен лимит за день: 1/1', 'Ст.9: Минимальный интервал не соблюдён'],
            contact_type='phone',
        )
        self.assertEqual(ViolationLog.objects.filter(client=c).count(), 2)
        self.assertTrue(ViolationLog.objects.filter(rule_type='st2_frequency').exists())
        self.assertTrue(ViolationLog.objects.filter(rule_type='st9_interval').exists())

    def test_creates_audit_log(self):
        c = _make_client()
        op = _make_operator()
        from .services.compliance_230fz import log_compliance_violation
        log_compliance_violation(c.id, op.id, ['Ст.7: Контакт с банкротом'])
        self.assertTrue(AuditLog.objects.filter(client_id=c.id, action='contact_blocked').exists())


class ComplianceValidationTest(TestCase):
    """Тесты validate_intervention()."""

    def test_valid_intervention(self):
        from .services.compliance_230fz import validate_intervention
        result = validate_intervention({
            'operator_id': 1,
            'intervention_type': 'phone',
            'caller_number': '+74951234567',
            'operator_identified': True,
            'approved_script_used': True,
        })
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['violations']), 0)

    def test_missing_operator(self):
        from .services.compliance_230fz import validate_intervention
        result = validate_intervention({'intervention_type': 'phone'})
        self.assertFalse(result['valid'])
        self.assertTrue(any('Ст.6' in v for v in result['violations']))

    def test_operator_not_identified(self):
        from .services.compliance_230fz import validate_intervention
        result = validate_intervention({
            'operator_id': 1,
            'operator_identified': False,
        })
        self.assertFalse(result['valid'])
        self.assertTrue(any('Ст.6' in v for v in result['violations']))


# =====================================================================
# 3. Тесты распределения (DistributionService)
# =====================================================================

class DistributionServiceTest(TestCase):
    """Тесты DistributionService из services/distribution.py."""

    def setUp(self):
        self.op_junior = _make_operator(full_name='Джуниор', role='operator')
        self.op_senior = _make_operator(full_name='Сеньор', role='senior_operator')
        self.op_manager = _make_operator(full_name='Менеджер', role='manager')

    def test_experience_ordering(self):
        from .services.distribution import DistributionService
        svc = DistributionService()
        exp_junior = svc.calculate_operator_experience(self.op_junior)
        exp_senior = svc.calculate_operator_experience(self.op_senior)
        exp_manager = svc.calculate_operator_experience(self.op_manager)
        self.assertGreater(exp_senior['total_score'], exp_junior['total_score'])
        self.assertGreater(exp_manager['total_score'], exp_junior['total_score'])

    def test_service_instantiation(self):
        from .services.distribution import DistributionService
        svc = DistributionService(max_load_per_operator=40)
        self.assertEqual(svc.max_load, 40)


# =====================================================================
# 4. Тесты банкротства
# =====================================================================

class BankruptcyTest(TestCase):
    def test_bankruptcy_check_service(self):
        from .services.compliance_230fz import check_bankruptcy
        c = _make_client()
        result = check_bankruptcy(c.id)
        self.assertFalse(result.get('is_bankrupt', result.get('bankrupt', False)))

    def test_bankrupt_client_blocks_contact(self):
        from .services.compliance_230fz import can_contact
        c = _make_client(is_bankrupt=True, bankruptcy_date=date.today())
        result = can_contact(c.id, 'phone')
        self.assertFalse(result['allowed'])
        self.assertTrue(any('банкрот' in v.lower() for v in result['violations']))

    def test_non_bankrupt_allows_contact(self):
        from .services.compliance_230fz import can_contact
        c = _make_client()
        with patch('collection_app.services.compliance_230fz.timezone') as mock_tz:
            now = timezone.now().replace(hour=12)
            while now.weekday() >= 5:
                now += timedelta(days=1)
            mock_tz.now.return_value = now
            result = can_contact(c.id, 'phone')
        self.assertTrue(result['allowed'])


# =====================================================================
# 5. Тесты API endpoints
# =====================================================================

class APIEndpointTest(TestCase):
    def setUp(self):
        self.api = APIClient()

    def test_clients_list(self):
        _make_client()
        resp = self.api.get('/api/clients/')
        self.assertEqual(resp.status_code, 200)

    def test_credits_list(self):
        c = _make_client()
        _make_credit(c)
        resp = self.api.get('/api/credits/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        results = data if isinstance(data, list) else data.get('results', [])
        self.assertGreaterEqual(len(results), 1)
        self.assertIn('delinquency_bucket', results[0])

    def test_compliance_check(self):
        c = _make_client()
        with patch('collection_app.services.compliance_230fz.timezone') as mock_tz:
            now = timezone.now().replace(hour=12)
            while now.weekday() >= 5:
                now += timedelta(days=1)
            mock_tz.now.return_value = now
            resp = self.api.get(f'/api/compliance/check/?client_id={c.id}&type=phone')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('allowed', resp.json())

    def test_violations_list(self):
        c = _make_client()
        op = _make_operator()
        ViolationLog.objects.create(
            client=c, operator=op, rule_type='st1_time',
            description='Ст.1: Ночной звонок',
        )
        resp = self.api.get('/api/violations/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(len(data), 1)
        self.assertIn('rule_type_display', data[0])

    def test_violations_filter_by_client(self):
        c1 = _make_client(full_name='Клиент 1')
        c2 = _make_client(full_name='Клиент 2')
        op = _make_operator()
        ViolationLog.objects.create(client=c1, operator=op, rule_type='st1_time', description='test')
        ViolationLog.objects.create(client=c2, operator=op, rule_type='st2_frequency', description='test2')
        resp = self.api.get(f'/api/violations/?client_id={c1.id}')
        data = resp.json()
        self.assertEqual(len(data), 1)

    def test_scoring_endpoint(self):
        resp = self.api.get('/api/scorings/')
        self.assertEqual(resp.status_code, 200)

    def test_operators_list(self):
        _make_operator()
        resp = self.api.get('/api/operators/')
        self.assertEqual(resp.status_code, 200)

    def test_swagger_schema(self):
        resp = self.api.get('/api/schema/')
        self.assertEqual(resp.status_code, 200)


# =====================================================================
# 6. Тесты delinquency buckets через API
# =====================================================================

class DelinquencyBucketAPITest(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.client_obj = _make_client()

    def test_credit_api_returns_bucket(self):
        cr = _make_credit(self.client_obj, status='overdue')
        CreditState.objects.create(
            credit=cr, state_date=date.today(),
            principal_debt=Decimal('490000'), overdue_principal=Decimal('45000'),
            overdue_days=55,
        )
        resp = self.api.get(f'/api/credits/{cr.id}/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['delinquency_bucket'], '30-60')
        self.assertEqual(data['days_past_due'], 55)
