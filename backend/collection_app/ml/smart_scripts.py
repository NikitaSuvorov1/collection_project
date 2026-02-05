"""
Сервис умных скриптов — Copilot для взыскания.

Функции:
- Анализ успешных разговоров
- Извлечение эффективных формулировок
- Подсказки оператору в реальном времени
- Обработка возражений
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class ScriptSuggestion:
    """Подсказка скрипта."""
    phrase: str
    context: str
    success_rate: float
    category: str  # 'opening', 'objection', 'closing', 'offer'


# Базовые скрипты по психотипам и сценариям
SCRIPT_TEMPLATES = {
    'soft_reminder': {
        'forgetful': {
            'opening': [
                'Добрый день, {client_name}! Это {operator_name} из {bank_name}. Звоню напомнить о платеже по вашему кредиту.',
                'Здравствуйте, {client_name}! Беспокоит {bank_name}. У вас образовалась небольшая задолженность, хотел уточнить — возможно, просто забыли?',
            ],
            'key_phrases': [
                'Уверен, это просто упущение',
                'Давайте вместе посмотрим, как удобнее оплатить',
                'Могу прямо сейчас отправить ссылку для оплаты',
            ],
            'closing': [
                'Отлично, тогда жду оплату до {date}. Хорошего дня!',
                'Спасибо за понимание! Если будут вопросы — звоните.',
            ],
        },
        'cooperative': {
            'opening': [
                'Добрый день, {client_name}! Это {operator_name}. Звоню по поводу вашего кредита — есть небольшая просрочка.',
            ],
            'key_phrases': [
                'Ценю, что вы всегда на связи',
                'Понимаю, что ситуации бывают разные',
                'Давайте найдём удобное решение',
            ],
            'closing': [
                'Договорились! Спасибо за сотрудничество.',
            ],
        },
    },
    'firm_demand': {
        'unwilling': {
            'opening': [
                'Добрый день, {client_name}. {operator_name}, {bank_name}. Обращаюсь по поводу вашей задолженности, которая уже {overdue_days} дней просрочена.',
            ],
            'key_phrases': [
                'Сумма задолженности составляет {amount} рублей',
                'При дальнейшей просрочке будут начисляться пени',
                'Информация может быть передана в бюро кредитных историй',
                'Предлагаю решить вопрос сейчас, пока условия ещё выгодные',
            ],
            'closing': [
                'Жду оплату до {date}. В противном случае будем вынуждены принять дополнительные меры.',
            ],
        },
        'toxic': {
            'opening': [
                'Добрый день. {operator_name}, {bank_name}. Звоню по вопросу задолженности.',
            ],
            'key_phrases': [
                'Прошу отнестись к вопросу серьёзно',
                'Это официальное уведомление',
                'Готов выслушать вашу позицию',
            ],
            'closing': [
                'Понял вас. Зафиксировал информацию. До свидания.',
            ],
        },
    },
    'restructure_offer': {
        'unable': {
            'opening': [
                'Добрый день, {client_name}! Это {operator_name} из {bank_name}. Понимаю, что сейчас непростая ситуация с платежами.',
            ],
            'key_phrases': [
                'У нас есть программа реструктуризации',
                'Можем снизить ежемесячный платёж',
                'Давайте подберём комфортный график',
                'Главное — не накапливать задолженность',
            ],
            'closing': [
                'Отлично! Оформлю заявку на реструктуризацию. Позвоню, когда будет решение.',
                'Рад, что нашли решение. Берегите себя!',
            ],
        },
    },
    'empathy': {
        'unable': {
            'opening': [
                'Добрый день, {client_name}. {operator_name}, {bank_name}. Как у вас дела? Звоню по поводу платежа.',
            ],
            'key_phrases': [
                'Понимаю, что сейчас сложно',
                'Многие оказываются в подобной ситуации',
                'Давайте вместе найдём выход',
                'Что мы можем сделать, чтобы помочь?',
            ],
            'closing': [
                'Держитесь! Мы всегда готовы помочь найти решение.',
            ],
        },
    },
}

# Обработка возражений
OBJECTION_HANDLERS = {
    'нет денег': [
        'Понимаю. Какую сумму вы смогли бы внести сейчас? Даже частичная оплата поможет.',
        'Когда ожидаете поступление средств? Можем договориться на эту дату.',
        'Рассмотрим вариант реструктуризации — это снизит ежемесячный платёж.',
    ],
    'не брал кредит': [
        'Давайте уточним данные. Ваши ФИО — {client_name}?',
        'Возможно, кредит оформлен на другого члена семьи?',
        'Если считаете, что произошла ошибка, подайте заявление — мы разберёмся.',
    ],
    'уже оплатил': [
        'Когда и каким способом производили оплату?',
        'Возможно, платёж ещё не поступил. Обычно это занимает 1-3 дня.',
        'Можете прислать подтверждение оплаты на нашу почту?',
    ],
    'не могу говорить': [
        'Когда вам будет удобно? Перезвоню в удобное время.',
        'Хорошо, могу отправить информацию СМС или на почту.',
        'Понял, какое время завтра будет удобным?',
    ],
    'буду жаловаться': [
        'Ваше право. Номер для жалоб: {complaint_phone}. Но давайте сначала попробуем решить вопрос.',
        'Готов выслушать ваши претензии и передать руководству.',
        'Понимаю ваше недовольство. Чем именно вы недовольны?',
    ],
    'перезвоните позже': [
        'Конечно. Какое время будет удобным?',
        'Хорошо. Но напоминаю, что задолженность {amount} рублей, и важно решить вопрос скорее.',
        'Договорились. Позвоню {date} в {time}.',
    ],
}

# Фразы по этапам разговора
STAGE_PHRASES = {
    'greeting': [
        'Добрый день', 'Здравствуйте', 'Доброе утро', 'Добрый вечер',
    ],
    'identification': [
        'Я разговариваю с {client_name}?',
        'Это {client_name}?',
        'Скажите, пожалуйста, это {client_name}?',
    ],
    'purpose': [
        'Звоню по поводу вашего кредитного договора',
        'Обращаюсь по вопросу задолженности',
        'Хотел уточнить по поводу платежа',
    ],
    'ptp_request': [
        'Когда сможете произвести оплату?',
        'На какую дату можем рассчитывать?',
        'Какую сумму и когда готовы внести?',
    ],
    'confirmation': [
        'Правильно ли я понял, что оплата поступит {date}?',
        'Договорились на {amount} до {date}, верно?',
        'Фиксирую: {amount} рублей до {date}.',
    ],
    'farewell': [
        'Спасибо за разговор. Всего доброго!',
        'Хорошего дня!',
        'До свидания, ждём оплату.',
    ],
}


class SmartScriptService:
    """Сервис умных скриптов для операторов."""

    def get_script_for_client(
        self,
        psychotype: str,
        scenario: str,
        client_data: Dict
    ) -> Dict[str, List[str]]:
        """
        Получает полный скрипт для клиента.
        
        Args:
            psychotype: Психотип клиента
            scenario: Сценарий разговора
            client_data: {client_name, amount, overdue_days, ...}
        
        Returns:
            {opening: [...], key_phrases: [...], closing: [...]}
        """
        # Получаем шаблон
        scenario_templates = SCRIPT_TEMPLATES.get(scenario, SCRIPT_TEMPLATES['soft_reminder'])
        template = scenario_templates.get(psychotype, scenario_templates.get('forgetful', {}))
        
        # Подставляем переменные
        result = {}
        for category, phrases in template.items():
            result[category] = [
                self._substitute_variables(phrase, client_data)
                for phrase in phrases
            ]
        
        return result

    def get_objection_response(
        self,
        objection_text: str,
        client_data: Dict
    ) -> List[str]:
        """
        Получает варианты ответа на возражение.
        
        Args:
            objection_text: Текст возражения клиента
            client_data: Данные для подстановки
        
        Returns:
            Список вариантов ответа
        """
        objection_lower = objection_text.lower()
        
        # Ищем подходящий обработчик
        for key, responses in OBJECTION_HANDLERS.items():
            if key in objection_lower:
                return [
                    self._substitute_variables(r, client_data)
                    for r in responses
                ]
        
        # Универсальные ответы
        return [
            'Понимаю вашу позицию. Давайте обсудим, как можем помочь.',
            'Хорошо, что вы это сказали. Какой вариант решения вы видите?',
        ]

    def get_stage_phrases(
        self,
        stage: str,
        client_data: Dict
    ) -> List[str]:
        """
        Получает фразы для определённого этапа разговора.
        
        Args:
            stage: 'greeting', 'identification', 'purpose', 'ptp_request', 'confirmation', 'farewell'
            client_data: Данные для подстановки
        
        Returns:
            Список фраз
        """
        phrases = STAGE_PHRASES.get(stage, [])
        return [self._substitute_variables(p, client_data) for p in phrases]

    def get_realtime_suggestions(
        self,
        current_transcript: str,
        client_data: Dict,
        psychotype: str,
        scenario: str
    ) -> List[ScriptSuggestion]:
        """
        Получает подсказки в реальном времени на основе текущего разговора.
        
        Args:
            current_transcript: Текущая транскрипция разговора
            client_data: Данные клиента
            psychotype: Психотип
            scenario: Сценарий
        
        Returns:
            Список подсказок
        """
        suggestions = []
        transcript_lower = current_transcript.lower()
        
        # Определяем этап разговора
        stage = self._detect_conversation_stage(transcript_lower)
        
        # Проверяем, есть ли возражение
        detected_objection = self._detect_objection(transcript_lower)
        if detected_objection:
            responses = self.get_objection_response(detected_objection, client_data)
            for resp in responses[:2]:
                suggestions.append(ScriptSuggestion(
                    phrase=resp,
                    context=f'Ответ на возражение: "{detected_objection}"',
                    success_rate=0.72,
                    category='objection',
                ))
        
        # Подсказки по этапу
        if stage == 'need_ptp':
            ptp_phrases = self.get_stage_phrases('ptp_request', client_data)
            for phrase in ptp_phrases[:2]:
                suggestions.append(ScriptSuggestion(
                    phrase=phrase,
                    context='Переходите к запросу обещания платежа',
                    success_rate=0.68,
                    category='ptp_request',
                ))
        
        elif stage == 'need_closing':
            closing_phrases = self.get_stage_phrases('farewell', client_data)
            for phrase in closing_phrases[:2]:
                suggestions.append(ScriptSuggestion(
                    phrase=phrase,
                    context='Завершение разговора',
                    success_rate=0.85,
                    category='closing',
                ))
        
        # Ключевые фразы сценария
        script = self.get_script_for_client(psychotype, scenario, client_data)
        for phrase in script.get('key_phrases', [])[:2]:
            if phrase.lower() not in transcript_lower:
                suggestions.append(ScriptSuggestion(
                    phrase=phrase,
                    context='Эффективная фраза для этого типа клиента',
                    success_rate=0.65,
                    category='key_phrase',
                ))
        
        return suggestions[:5]  # Максимум 5 подсказок

    def _substitute_variables(self, text: str, data: Dict) -> str:
        """Подставляет переменные в текст."""
        result = text
        for key, value in data.items():
            result = result.replace('{' + key + '}', str(value))
        return result

    def _detect_conversation_stage(self, transcript: str) -> str:
        """Определяет текущий этап разговора."""
        # Упрощённая логика
        if 'до свидания' in transcript or 'всего доброго' in transcript:
            return 'ended'
        
        if 'когда' in transcript and ('оплат' in transcript or 'внес' in transcript):
            return 'ptp_discussed'
        
        if 'задолженност' in transcript or 'долг' in transcript:
            return 'need_ptp'
        
        if 'здравствуйте' in transcript or 'добрый день' in transcript:
            if len(transcript) < 200:
                return 'greeting'
            return 'need_ptp'
        
        return 'in_progress'

    def _detect_objection(self, transcript: str) -> Optional[str]:
        """Определяет возражение в транскрипции."""
        # Последние 200 символов — вероятно, последняя реплика
        recent = transcript[-200:] if len(transcript) > 200 else transcript
        
        for objection_key in OBJECTION_HANDLERS.keys():
            if objection_key in recent:
                return objection_key
        
        return None

    def analyze_successful_calls(
        self,
        transcripts: List[Dict]
    ) -> Dict[str, List[str]]:
        """
        Анализирует успешные звонки и извлекает эффективные фразы.
        
        Args:
            transcripts: [{transcript, ptp_achieved, ptp_amount}, ...]
        
        Returns:
            {psychotype: [effective_phrases]}
        """
        # В реальной системе здесь был бы NLP-анализ
        # Пока возвращаем заглушку
        return {
            'forgetful': ['Уверен, это просто упущение', 'Могу помочь с быстрой оплатой'],
            'unwilling': ['При дальнейшей просрочке будут последствия', 'Сейчас ещё можно решить на выгодных условиях'],
            'unable': ['Давайте подберём посильный вариант', 'Есть программа реструктуризации'],
        }


def get_script_suggestions(client, credit, nba_recommendation: Dict) -> List[ScriptSuggestion]:
    """
    Утилита для получения подсказок скрипта.
    
    Использовать в views:
        from collection_app.ml.smart_scripts import get_script_suggestions
        suggestions = get_script_suggestions(client, credit, nba)
    """
    service = SmartScriptService()
    
    # Данные для подстановки
    client_data = {
        'client_name': client.full_name.split()[0] if client.full_name else 'клиент',
        'operator_name': 'Оператор',
        'bank_name': 'Банк',
        'amount': f"{credit.principal_amount:,.0f}".replace(',', ' '),
        'overdue_days': '30',  # Можно вычислить
        'date': 'пятницы',
        'time': '10:00',
        'complaint_phone': '8-800-123-45-67',
    }
    
    # Получаем психотип
    psychotype = 'forgetful'
    if hasattr(client, 'behavior_profile'):
        psychotype = client.behavior_profile.psychotype
    
    scenario = nba_recommendation.get('recommended_scenario', 'soft_reminder')
    
    return service.get_realtime_suggestions(
        current_transcript='',
        client_data=client_data,
        psychotype=psychotype,
        scenario=scenario,
    )
