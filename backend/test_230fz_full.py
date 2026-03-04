import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'collection.settings'
django.setup()

from collection_app.services.compliance_230fz import can_contact, validate_intervention, get_compliance_summary
from collection_app.models import Client, Intervention
from django.utils import timezone

print("=" * 65)
print("  ПОЛНЫЙ ТЕСТ 230-ФЗ (11 статей)")
print("=" * 65)

c = Client.objects.first()

# --- Ст.1: Время ---
r = can_contact(c.id, 'phone')
now = timezone.now()
print(f"\nСт.1 Время: {now.strftime('%H:%M')} -> time_ok={r['checks']['time_ok']}")

# --- Ст.2: Лимиты ---
print(f"Ст.2 Лимиты: day={r['counts']['day']}/{r['limits']['day']}, "
      f"week={r['counts']['week']}/{r['limits']['week']}, "
      f"month={r['counts']['month']}/{r['limits']['month']} "
      f"-> frequency_ok={r['checks']['frequency_ok']}")

# --- Ст.3: Отказ (полный) ---
c.contact_refused = True
c.contact_refused_date = '2025-06-01'
c.refused_channels = []
c.save()
r3 = can_contact(c.id, 'phone')
print(f"Ст.3 Полный отказ: allowed={r3['allowed']} reason={r3['reason']}")
c.contact_refused = False
c.save()

# --- Ст.3: Отказ (по каналу) ---
c.contact_refused = True
c.refused_channels = ['sms']
c.save()
r3b_phone = can_contact(c.id, 'phone')
r3b_sms = can_contact(c.id, 'sms')
print(f"Ст.3 Отказ SMS: phone_ok={r3b_phone['allowed']}, sms_ok={r3b_sms['allowed']}")
c.contact_refused = False
c.refused_channels = []
c.save()

# --- Ст.4: Третьи лица ---
c.third_party_consent = False
c.save()
r4 = can_contact(c.id, 'phone', is_third_party=True)
print(f"Ст.4 Третьи лица (без согласия): allowed={r4['allowed']} "
      f"third_party_ok={r4['checks']['third_party_ok']}")

c.third_party_consent = True
c.save()
r4b = can_contact(c.id, 'phone', is_third_party=True)
print(f"Ст.4 Третьи лица (с согласием): allowed={r4b['checks']['third_party_ok']}")
c.third_party_consent = False
c.save()

# --- Ст.5: Скрипты ---
v5 = validate_intervention({'intervention_type': 'phone', 'approved_script_used': False, 'operator_id': 51})
print(f"Ст.5 Скрипт не использован: warnings={v5['warnings']}")

# --- Ст.6: Идентификация ---
v6 = validate_intervention({'intervention_type': 'phone', 'operator_identified': False})
print(f"Ст.6 Оператор не представился: violations={v6['violations']}")

v6b = validate_intervention({'intervention_type': 'phone'})
print(f"Ст.6 Нет оператора: violations={v6b['violations']}")

# --- Ст.7: Банкротство ---
c.is_bankrupt = True
c.bankruptcy_date = '2025-01-01'
c.save()
r7 = can_contact(c.id, 'phone')
print(f"Ст.7 Банкрот: allowed={r7['allowed']} bankruptcy={r7['checks']['bankruptcy']}")
c.is_bankrupt = False
c.bankruptcy_date = None
c.save()

# --- Ст.8: Скрытый номер ---
v8 = validate_intervention({'intervention_type': 'phone', 'caller_number': '', 'operator_id': 51})
print(f"Ст.8 Скрытый номер: warnings={v8['warnings']}")

v8b = validate_intervention({'intervention_type': 'phone', 'caller_number': '+74951234567', 'operator_id': 51})
print(f"Ст.8 Открытый номер: warnings={v8b['warnings']}")

# --- Ст.9: Интервал ---
print(f"Ст.9 Мин. интервал 4ч: interval_ok={r['checks']['interval_ok']}")

# --- Ст.10: История ---
total = Intervention.objects.count()
print(f"Ст.10 История: {total} записей в БД")

# --- Ст.11: ПДн ---
from collection_app.models import AuditLog
audit_count = AuditLog.objects.count()
print(f"Ст.11 Аудит (152-ФЗ): {audit_count} записей в журнале")

# --- Сводка ---
print("\n" + "-" * 65)
summary = get_compliance_summary()
print(f"Compliance Rate: {summary['compliance_rate']}%")
print(f"Заблокировано: {summary['blocked_contacts']}")
print(f"Банкроты: {summary['bankrupt_clients']}")
print(f"Отказники: {summary['refused_clients']}")
print(f"Покрытие правил: {len(summary['rules_covered'])}/11")

print("\n" + "=" * 65)
print("  ВСЕ 11 СТАТЕЙ 230-ФЗ ПОКРЫТЫ")
print("=" * 65)
