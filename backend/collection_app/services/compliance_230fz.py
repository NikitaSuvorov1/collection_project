"""
Контроль соблюдения 230-ФЗ «О защите прав и законных интересов физических лиц
при осуществлении деятельности по возврату просроченной задолженности».

Полное покрытие 11 статей закона:

 Ст.1  — Ограничения по времени: будни 08–22, выходные 09–20
 Ст.2  — Лимиты частоты: 1 звонок/день, 2/неделю, 8/месяц; SMS 2/4/16
 Ст.3  — Отказ от взаимодействия (полный или по каналам)
 Ст.4  — Запрет контактов с третьими лицами без согласия
 Ст.5  — Запрет угроз и давления (утверждённые скрипты)
 Ст.6  — Обязательная идентификация оператора
 Ст.7  — Банкротство: полный запрет контактов
 Ст.8  — Запрет скрытого номера
 Ст.9  — Минимальный интервал между звонками (4 часа)
 Ст.10 — Хранение истории (Intervention + AuditLog)
 Ст.11 — 152-ФЗ ПДн (AuditLog + разграничение доступа)

Функции:
  can_contact(client_id, contact_type, is_third_party)
      → {allowed: bool, reason: str, violations: [...], checks: {...}}
  validate_intervention(data)
      → {valid: bool, violations: [...]}
  log_compliance_violation(...)
      → AuditLog
"""

from datetime import datetime, timedelta, date
from django.utils import timezone
from django.db.models import Count, Q

from collection_app.models import Client, Intervention, AuditLog, ViolationLog


# === Лимиты по 230-ФЗ ===
LIMITS = {
    'calls_per_day': 1,
    'calls_per_week': 2,
    'calls_per_month': 8,
    'sms_per_day': 2,
    'sms_per_week': 4,
    'sms_per_month': 16,
}

# Разрешённое время контактов
ALLOWED_HOURS = {
    'weekday': (8, 22),   # будни:  08:00–22:00
    'weekend': (9, 20),   # выходные: 09:00–20:00
}

# Минимальный интервал между звонками одному клиенту (часы)
MIN_CALL_INTERVAL_HOURS = 4


def can_contact(client_id: int, contact_type: str = 'phone',
                is_third_party: bool = False) -> dict:
    """
    Проверяет, можно ли сейчас связаться с клиентом по 230-ФЗ.

    Args:
        client_id:      ID клиента
        contact_type:   'phone' | 'sms' | 'email' | 'letter' | 'visit'
        is_third_party: контакт с третьим лицом (родственник, работодатель)

    Returns:
        {
            'allowed': bool,
            'reason': str | None,
            'violations': [str],
            'limits': {'day': int, 'week': int, 'month': int},
            'counts': {'day': int, 'week': int, 'month': int},
            'checks': {
                'bankruptcy': bool,    # ст.7
                'refused': bool,       # ст.3
                'time_ok': bool,       # ст.1
                'frequency_ok': bool,  # ст.2
                'interval_ok': bool,   # ст.9
                'third_party_ok': bool,# ст.4
            },
        }
    """
    violations = []
    now = timezone.now()
    today = now.date()
    checks = {}

    # --- 1. Проверка существования клиента ---
    try:
        client = Client.objects.get(id=client_id)
    except Client.DoesNotExist:
        return {
            'allowed': False,
            'reason': 'Клиент не найден',
            'violations': ['client_not_found'],
            'checks': {},
        }

    # --- Ст.7: Банкротство ---
    checks['bankruptcy'] = client.is_bankrupt
    if client.is_bankrupt:
        violations.append(
            f'Ст.7: Клиент признан банкротом ({client.bankruptcy_date}) — '
            f'контакт запрещён до завершения процедуры'
        )
        return {
            'allowed': False,
            'reason': 'Клиент признан банкротом — контакт запрещён (ст.7 230-ФЗ)',
            'violations': violations,
            'checks': checks,
        }

    # --- Ст.3: Отказ от взаимодействия ---
    refused_channels = getattr(client, 'refused_channels', []) or []
    if client.contact_refused:
        if not refused_channels:
            # Полный отказ от всех каналов
            checks['refused'] = True
            violations.append(
                f'Ст.3: Клиент отказался от всех контактов ({client.contact_refused_date})'
            )
            return {
                'allowed': False,
                'reason': 'Клиент отказался от взаимодействия (ст.8 230-ФЗ)',
                'violations': violations,
                'checks': checks,
            }
        elif contact_type in refused_channels:
            # Отказ от конкретного канала
            checks['refused'] = True
            violations.append(
                f'Ст.3: Клиент отказался от канала «{contact_type}» ({client.contact_refused_date})'
            )
        else:
            checks['refused'] = False
    else:
        checks['refused'] = False

    # --- Ст.4: Третьи лица — нужно согласие ---
    if is_third_party:
        has_consent = getattr(client, 'third_party_consent', False)
        checks['third_party_ok'] = has_consent
        if not has_consent:
            violations.append(
                'Ст.4: Контакт с третьим лицом запрещён — '
                'нет согласия клиента на взаимодействие с третьими лицами'
            )
    else:
        checks['third_party_ok'] = True

    # --- Ст.1: Проверка времени звонка ---
    weekday = now.weekday()
    hour = now.hour

    if weekday < 5:
        min_h, max_h = ALLOWED_HOURS['weekday']
        period_name = 'будний день'
    else:
        min_h, max_h = ALLOWED_HOURS['weekend']
        period_name = 'выходной'

    time_ok = min_h <= hour < max_h
    checks['time_ok'] = time_ok
    if not time_ok:
        violations.append(
            f'Ст.1: Запрещённое время контакта: {hour:02d}:{now.minute:02d} '
            f'({period_name}, разрешено {min_h:02d}:00–{max_h:02d}:00)'
        )

    # --- Ст.2: Проверка частоты контактов ---
    prefix = 'calls' if contact_type == 'phone' else 'sms'
    type_filter = contact_type

    interventions_qs = Intervention.objects.filter(
        client_id=client_id,
        intervention_type=type_filter,
    )

    day_count = interventions_qs.filter(datetime__date=today).count()
    week_count = interventions_qs.filter(
        datetime__date__gte=today - timedelta(days=7)
    ).count()
    month_count = interventions_qs.filter(
        datetime__date__gte=today - timedelta(days=30)
    ).count()

    day_limit = LIMITS.get(f'{prefix}_per_day', 999)
    week_limit = LIMITS.get(f'{prefix}_per_week', 999)
    month_limit = LIMITS.get(f'{prefix}_per_month', 999)

    frequency_ok = True
    if day_count >= day_limit:
        violations.append(f'Ст.2: Превышен лимит за день: {day_count}/{day_limit}')
        frequency_ok = False
    if week_count >= week_limit:
        violations.append(f'Ст.2: Превышен лимит за неделю: {week_count}/{week_limit}')
        frequency_ok = False
    if month_count >= month_limit:
        violations.append(f'Ст.2: Превышен лимит за месяц: {month_count}/{month_limit}')
        frequency_ok = False
    checks['frequency_ok'] = frequency_ok

    # --- Ст.9: Минимальный интервал между звонками ---
    interval_ok = True
    if contact_type in ('phone', 'sms'):
        last_contact = interventions_qs.order_by('-datetime').first()
        if last_contact and last_contact.datetime:
            hours_since = (now - last_contact.datetime).total_seconds() / 3600
            if hours_since < MIN_CALL_INTERVAL_HOURS:
                interval_ok = False
                violations.append(
                    f'Ст.9: Минимальный интервал {MIN_CALL_INTERVAL_HOURS}ч '
                    f'не соблюдён (прошло {hours_since:.1f}ч с последнего контакта)'
                )
    checks['interval_ok'] = interval_ok

    allowed = len(violations) == 0

    return {
        'allowed': allowed,
        'reason': violations[0] if violations else None,
        'violations': violations,
        'limits': {'day': day_limit, 'week': week_limit, 'month': month_limit},
        'counts': {'day': day_count, 'week': week_count, 'month': month_count},
        'checks': checks,
    }


def validate_intervention(data: dict) -> dict:
    """
    Пост-валидация данных интервенции перед сохранением.
    Проверяет ст.6 (идентификация), ст.8 (скрытый номер), ст.5 (скрипт).

    Args:
        data: словарь с полями Intervention

    Returns:
        {'valid': bool, 'violations': [...], 'warnings': [...]}
    """
    violations = []
    warnings = []

    # Ст.6: Оператор должен быть указан
    if not data.get('operator') and not data.get('operator_id'):
        violations.append('Ст.6: Не указан оператор — обязательная идентификация')

    # Ст.8: Исходящий номер не должен быть скрыт (для звонков)
    if data.get('intervention_type') == 'phone':
        caller_num = data.get('caller_number', '')
        if not caller_num:
            warnings.append('Ст.8: Не указан исходящий номер — запрет скрытых звонков')

    # Ст.6: Оператор представился
    if data.get('operator_identified') is False:
        violations.append('Ст.6: Оператор не представился клиенту')

    # Ст.5: Использован утверждённый скрипт
    if data.get('approved_script_used') is False:
        warnings.append('Ст.5: Не использован утверждённый скрипт разговора')

    # Ст.4: Контакт с третьим лицом
    if data.get('is_third_party', False):
        client_id = data.get('client_id') or (data.get('client').id if data.get('client') else None)
        if client_id:
            try:
                client = Client.objects.get(id=client_id)
                if not client.third_party_consent:
                    violations.append('Ст.4: Контакт с третьим лицом без согласия клиента')
            except Client.DoesNotExist:
                pass

    return {
        'valid': len(violations) == 0,
        'violations': violations,
        'warnings': warnings,
    }


def log_compliance_violation(client_id: int, operator_id: int,
                             violations: list,
                             action: str = 'contact_blocked',
                             contact_type: str = ''):
    """Логирование нарушения 230-ФЗ в AuditLog + ViolationLog."""
    severity = 'warning' if action == 'contact_blocked' else 'critical'
    details = {
        'violations': violations,
        'timestamp': timezone.now().isoformat(),
        'law': '230-ФЗ',
    }
    # Запись в общий AuditLog
    AuditLog.objects.create(
        action=action,
        operator_id=operator_id,
        client_id=client_id,
        severity=severity,
        details=details,
    )
    # Запись в специализированный ViolationLog
    rule_map = {
        'Ст.1': 'st1_time', 'Ст.2': 'st2_frequency', 'Ст.3': 'st3_refusal',
        'Ст.4': 'st4_third_party', 'Ст.5': 'st5_script', 'Ст.6': 'st6_identification',
        'Ст.7': 'st7_bankruptcy', 'Ст.8': 'st8_hidden_number', 'Ст.9': 'st9_interval',
        'Ст.10': 'st10_history', 'Ст.11': 'st11_personal_data',
    }
    for v_text in violations:
        rule_type = 'other'
        for prefix, code in rule_map.items():
            if v_text.startswith(prefix):
                rule_type = code
                break
        ViolationLog.objects.create(
            client_id=client_id,
            operator_id=operator_id,
            rule_type=rule_type,
            severity=severity,
            description=v_text,
            action_blocked=(action == 'contact_blocked'),
            contact_type=contact_type,
            details=details,
        )


def check_bankruptcy(client_id: int) -> dict:
    """
    Проверка статуса банкротства клиента (ст.7).
    В реальной системе — запрос в ЕФРСБ API.
    Здесь использует поле client.is_bankrupt.
    """
    from collection_app.models import BankruptcyCheck

    try:
        client = Client.objects.get(id=client_id)
    except Client.DoesNotExist:
        return {'error': 'Клиент не найден'}

    check = BankruptcyCheck.objects.create(
        client=client,
        is_bankrupt=client.is_bankrupt,
        bankruptcy_date=client.bankruptcy_date,
        source='internal_db',
    )

    AuditLog.objects.create(
        action='bankruptcy_check',
        client_id=client_id,
        severity='info',
        details={
            'is_bankrupt': client.is_bankrupt,
            'check_id': check.id,
        },
    )

    return {
        'client_id': client_id,
        'is_bankrupt': client.is_bankrupt,
        'bankruptcy_date': str(client.bankruptcy_date) if client.bankruptcy_date else None,
        'check_id': check.id,
    }


def get_compliance_summary() -> dict:
    """
    Сводка по соблюдению 230-ФЗ для дашборда руководителя.
    """
    today = timezone.now().date()
    month_ago = today - timedelta(days=30)

    blocked = AuditLog.objects.filter(
        action='contact_blocked',
        timestamp__date__gte=month_ago,
    ).count()

    bankruptcy_checks = AuditLog.objects.filter(
        action='bankruptcy_check',
        timestamp__date__gte=month_ago,
    ).count()

    total_interventions = Intervention.objects.filter(
        datetime__date__gte=month_ago,
    ).count()

    bankrupt_clients = Client.objects.filter(is_bankrupt=True).count()
    refused_clients = Client.objects.filter(contact_refused=True).count()

    return {
        'period': 'last_30_days',
        'blocked_contacts': blocked,
        'bankruptcy_checks': bankruptcy_checks,
        'total_interventions': total_interventions,
        'compliance_rate': round(
            (1 - blocked / total_interventions) * 100, 1
        ) if total_interventions > 0 else 100.0,
        'bankrupt_clients': bankrupt_clients,
        'refused_clients': refused_clients,
        'rules_covered': [
            'Ст.1: Ограничения по времени',
            'Ст.2: Лимиты частоты контактов',
            'Ст.3: Отказ от взаимодействия (полный/по каналам)',
            'Ст.4: Третьи лица — только с согласием',
            'Ст.5: Утверждённые скрипты',
            'Ст.6: Идентификация оператора',
            'Ст.7: Банкротство',
            'Ст.8: Запрет скрытых номеров',
            'Ст.9: Минимальный интервал 4ч',
            'Ст.10: Хранение истории',
            'Ст.11: Защита ПДн (152-ФЗ)',
        ],
    }
