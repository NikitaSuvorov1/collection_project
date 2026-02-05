"""
Сервис комплаенса — контроль риска и соответствия регуляторным требованиям.

Автоматическая проверка:
- Речи и текстов на нарушения (давление, угрозы)
- Времени звонков (разрешённые часы)
- Частоты контактов
- Отклонений от сценария
- Полный лог для регулятора
"""
import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple


@dataclass
class ComplianceCheckResult:
    """Результат проверки комплаенса."""
    is_compliant: bool
    score: float  # 0-1, где 1 = полное соответствие
    violations: List[Dict]
    warnings: List[Dict]


# Запрещённые слова и фразы
PROHIBITED_PATTERNS = {
    'threats': [
        r'приедем\s+к\s+вам',
        r'знаем\s+где\s+вы\s+живёте',
        r'найдём\s+вас',
        r'будет\s+хуже',
        r'пожалеете',
        r'накажем',
        r'посадим',
        r'тюрьма',
        r'уголовное',
        r'арест',
        r'опишем\s+имущество',
    ],
    'pressure': [
        r'обязаны\s+платить\s+сейчас',
        r'немедленно',
        r'в\s+течение\s+часа',
        r'последний\s+шанс',
        r'иначе\s+будет\s+поздно',
        r'не\s+отвертитесь',
        r'никуда\s+не\s+денетесь',
    ],
    'disclosure': [
        r'расскажем\s+(?:родственникам|соседям|работодателю)',
        r'позвоним\s+(?:родителям|жене|мужу|на\s+работу)',
        r'сообщим\s+всем',
        r'опубликуем',
    ],
    'rudeness': [
        r'идиот',
        r'дурак',
        r'мошенник',
        r'вор',
        r'жулик',
        r'бестолковый',
        r'тупой',
        r'дебил',
    ],
}

# Разрешённое время для звонков (по закону РФ о коллекторской деятельности)
ALLOWED_CALL_HOURS = {
    'weekday': (8, 22),  # С 8:00 до 22:00 в будни
    'weekend': (9, 20),  # С 9:00 до 20:00 в выходные
}

# Лимиты контактов (по закону)
CONTACT_LIMITS = {
    'calls_per_day': 1,
    'calls_per_week': 2,
    'calls_per_month': 8,
    'sms_per_day': 2,
    'sms_per_week': 4,
    'sms_per_month': 16,
}


class ComplianceService:
    """Сервис проверки комплаенса."""

    def check_text_compliance(
        self,
        text: str,
        context: str = 'call'
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Проверяет текст на нарушения комплаенса.
        
        Args:
            text: Текст для проверки (транскрипция или сообщение)
            context: 'call' или 'message'
        
        Returns:
            (violations, warnings)
        """
        violations = []
        warnings = []
        text_lower = text.lower()
        
        for category, patterns in PROHIBITED_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text_lower)
                for match in matches:
                    violation = {
                        'type': category,
                        'severity': 'violation' if category in ['threats', 'disclosure'] else 'warning',
                        'pattern': pattern,
                        'match': match.group(),
                        'position': match.start(),
                        'context': text[max(0, match.start()-30):match.end()+30],
                    }
                    
                    if violation['severity'] == 'violation':
                        violations.append(violation)
                    else:
                        warnings.append(violation)
        
        return violations, warnings

    def check_call_timing(
        self,
        call_datetime: datetime
    ) -> Optional[Dict]:
        """
        Проверяет, был ли звонок в разрешённое время.
        
        Returns:
            Violation dict or None
        """
        weekday = call_datetime.weekday()
        call_hour = call_datetime.hour
        
        if weekday < 5:  # Будний день
            min_hour, max_hour = ALLOWED_CALL_HOURS['weekday']
        else:  # Выходной
            min_hour, max_hour = ALLOWED_CALL_HOURS['weekend']
        
        if call_hour < min_hour or call_hour >= max_hour:
            return {
                'type': 'timing',
                'severity': 'violation',
                'description': f'Звонок в неразрешённое время: {call_datetime.strftime("%H:%M")}',
                'allowed_hours': f'{min_hour}:00 - {max_hour}:00',
                'datetime': call_datetime.isoformat(),
            }
        
        return None

    def check_contact_frequency(
        self,
        client_id: int,
        contact_type: str,
        recent_contacts: List[Dict]
    ) -> List[Dict]:
        """
        Проверяет частоту контактов.
        
        Args:
            client_id: ID клиента
            contact_type: 'call' или 'sms'
            recent_contacts: Список недавних контактов [{datetime, type}, ...]
        
        Returns:
            List of violations
        """
        violations = []
        now = datetime.now()
        
        # Фильтруем по типу
        contacts = [c for c in recent_contacts if c.get('type') == contact_type]
        
        # Подсчитываем
        today = sum(1 for c in contacts if c['datetime'].date() == now.date())
        this_week = sum(1 for c in contacts if (now - c['datetime']).days < 7)
        this_month = sum(1 for c in contacts if (now - c['datetime']).days < 30)
        
        # Проверяем лимиты
        prefix = 'calls' if contact_type == 'call' else 'sms'
        
        if today >= CONTACT_LIMITS[f'{prefix}_per_day']:
            violations.append({
                'type': 'frequency',
                'severity': 'violation',
                'description': f'Превышен лимит {contact_type} в день',
                'limit': CONTACT_LIMITS[f'{prefix}_per_day'],
                'actual': today + 1,
                'period': 'day',
            })
        
        if this_week >= CONTACT_LIMITS[f'{prefix}_per_week']:
            violations.append({
                'type': 'frequency',
                'severity': 'warning',
                'description': f'Превышен лимит {contact_type} в неделю',
                'limit': CONTACT_LIMITS[f'{prefix}_per_week'],
                'actual': this_week + 1,
                'period': 'week',
            })
        
        if this_month >= CONTACT_LIMITS[f'{prefix}_per_month']:
            violations.append({
                'type': 'frequency',
                'severity': 'warning',
                'description': f'Превышен лимит {contact_type} в месяц',
                'limit': CONTACT_LIMITS[f'{prefix}_per_month'],
                'actual': this_month + 1,
                'period': 'month',
            })
        
        return violations

    def check_script_deviation(
        self,
        transcript: str,
        required_elements: List[str]
    ) -> List[Dict]:
        """
        Проверяет отклонение от обязательных элементов скрипта.
        
        Args:
            transcript: Транскрипция разговора
            required_elements: Обязательные элементы ['представление', 'цель_звонка', ...]
        
        Returns:
            List of warnings
        """
        warnings = []
        transcript_lower = transcript.lower()
        
        # Обязательные элементы и их паттерны
        element_patterns = {
            'представление': [r'меня\s+зовут', r'моё?\s+имя', r'компания', r'банк'],
            'цель_звонка': [r'звоню\s+по\s+поводу', r'хотел\s+бы\s+обсудить', r'напоминаю\s+о'],
            'сумма_долга': [r'сумма\s+(?:долга|задолженности)', r'\d+\s*(?:руб|₽)'],
            'срок_оплаты': [r'срок\s+(?:оплаты|погашения)', r'до\s+\d+\s+(?:числа|января|февраля)'],
            'способы_оплаты': [r'оплатить\s+можно', r'способ(?:ы)?\s+оплаты', r'через\s+(?:банк|приложение)'],
            'завершение': [r'всего\s+доброго', r'до\s+свидания', r'хорошего\s+дня'],
        }
        
        for element in required_elements:
            if element not in element_patterns:
                continue
            
            patterns = element_patterns[element]
            found = any(re.search(p, transcript_lower) for p in patterns)
            
            if not found:
                warnings.append({
                    'type': 'script_deviation',
                    'severity': 'warning',
                    'description': f'Не обнаружен обязательный элемент: {element}',
                    'element': element,
                })
        
        return warnings

    def analyze_conversation(
        self,
        transcript: str,
        call_datetime: datetime,
        client_id: int,
        recent_contacts: List[Dict] = None,
        required_script_elements: List[str] = None
    ) -> ComplianceCheckResult:
        """
        Полный анализ разговора на комплаенс.
        
        Args:
            transcript: Транскрипция разговора
            call_datetime: Время звонка
            client_id: ID клиента
            recent_contacts: Недавние контакты
            required_script_elements: Обязательные элементы скрипта
        
        Returns:
            ComplianceCheckResult
        """
        recent_contacts = recent_contacts or []
        required_script_elements = required_script_elements or [
            'представление', 'цель_звонка', 'завершение'
        ]
        
        all_violations = []
        all_warnings = []
        
        # 1. Проверка текста
        text_violations, text_warnings = self.check_text_compliance(transcript)
        all_violations.extend(text_violations)
        all_warnings.extend(text_warnings)
        
        # 2. Проверка времени
        timing_violation = self.check_call_timing(call_datetime)
        if timing_violation:
            all_violations.append(timing_violation)
        
        # 3. Проверка частоты
        freq_violations = self.check_contact_frequency(client_id, 'call', recent_contacts)
        for v in freq_violations:
            if v['severity'] == 'violation':
                all_violations.append(v)
            else:
                all_warnings.append(v)
        
        # 4. Проверка скрипта
        script_warnings = self.check_script_deviation(transcript, required_script_elements)
        all_warnings.extend(script_warnings)
        
        # Расчёт скора
        violation_weight = 0.3  # Каждое нарушение снижает на 30%
        warning_weight = 0.05  # Каждое предупреждение на 5%
        
        score = 1.0
        score -= len(all_violations) * violation_weight
        score -= len(all_warnings) * warning_weight
        score = max(0.0, score)
        
        is_compliant = len(all_violations) == 0
        
        return ComplianceCheckResult(
            is_compliant=is_compliant,
            score=round(score, 2),
            violations=all_violations,
            warnings=all_warnings,
        )


def check_intervention_compliance(intervention) -> ComplianceCheckResult:
    """
    Утилита для проверки комплаенса воздействия.
    
    Использовать в views или сигналах:
        from collection_app.ml.compliance import check_intervention_compliance
        result = check_intervention_compliance(intervention)
        if not result.is_compliant:
            create_alerts(result.violations)
    """
    service = ComplianceService()
    
    # Получаем транскрипцию, если есть
    transcript = ''
    if hasattr(intervention, 'analysis') and intervention.analysis:
        transcript = intervention.analysis.transcript
    
    # Недавние контакты
    from collection_app.models import Intervention
    recent = Intervention.objects.filter(
        client=intervention.client,
        datetime__gte=datetime.now() - timedelta(days=30)
    ).exclude(id=intervention.id)
    
    recent_contacts = [
        {'datetime': i.datetime, 'type': 'call' if i.intervention_type == 'phone' else 'sms'}
        for i in recent
    ]
    
    return service.analyze_conversation(
        transcript=transcript,
        call_datetime=intervention.datetime,
        client_id=intervention.client_id,
        recent_contacts=recent_contacts,
    )


def create_compliance_alerts(intervention, check_result: ComplianceCheckResult) -> List:
    """
    Создаёт алерты комплаенса на основе результата проверки.
    
    Returns:
        Список созданных ComplianceAlert
    """
    from collection_app.models import ComplianceAlert
    
    created_alerts = []
    
    for violation in check_result.violations:
        alert = ComplianceAlert.objects.create(
            intervention=intervention,
            operator=intervention.operator,
            severity='violation' if violation['type'] in ['threats', 'disclosure', 'timing'] else 'warning',
            alert_type=violation['type'],
            description=violation.get('description', f'Нарушение: {violation["type"]}'),
            evidence=violation.get('context', violation.get('match', '')),
            timestamp_in_call=violation.get('position'),
            status='new',
        )
        created_alerts.append(alert)
    
    return created_alerts
