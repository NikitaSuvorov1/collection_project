import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

// ===== MOCK DATA =====
const USE_MOCK = false; // Переключатель на реальное API

const MOCK_CLIENT = {
  id: 1,
  full_name: 'Иванов Иван Петрович',
  phone_mobile: '+7 (999) 123-45-67',
  phone_work: '+7 (495) 111-22-33',
  email: 'ivanov@mail.ru',
  city: 'Москва',
  employer: 'ООО "ТехноСофт"',
  position: 'Менеджер',
  monthly_income: 85000,
  total_debt: 156000,
  total_overdue: 42000,
  behavior_profile: {
    psychotype: 'forgetful',
    psychotype_confidence: 0.82,
    payment_discipline_score: 0.45,
    payments_on_time_ratio: 0.35,
    promises_kept_ratio: 0.6,
    avg_days_overdue: 18,
    total_contacts: 24,
    successful_contacts: 15,
    preferred_channel: 'phone',
    best_contact_hour: 14,
    best_contact_day: 2,
    income_dropped: false,
    job_changed_recently: false,
    multiple_credits: true,
    activity_dropped: false,
    return_probability: 0.68,
    strategic_recommendation: 'restructure',
  },
  credits: [
    {
      id: 101,
      contract_number: 'КР-2024-001234',
      product_type: 'Потребительский кредит',
      original_amount: 200000,
      issue_date: '2024-03-15',
      term_months: 24,
      interest_rate: 18.5,
      risk_segment: 'medium',
      latest_state: {
        principal_debt: 156000,
        overdue_principal: 42000,
        interest: 8500,
        dpd: 35,
      },
    },
  ],
  interventions: [
    { datetime: '2026-01-15T14:30:00', channel: 'phone', result: 'promise_to_pay', promise_amount: 15000, promise_date: '2026-01-25', operator_name: 'Петрова А.' },
    { datetime: '2026-01-10T11:15:00', channel: 'sms', result: 'no_answer', promise_amount: null, promise_date: null, operator_name: 'Система' },
    { datetime: '2026-01-05T16:45:00', channel: 'phone', result: 'callback', promise_amount: null, promise_date: null, operator_name: 'Сидоров В.' },
    { datetime: '2025-12-28T10:00:00', channel: 'phone', result: 'refuse', promise_amount: null, promise_date: null, operator_name: 'Петрова А.' },
    { datetime: '2025-12-20T13:20:00', channel: 'whatsapp', result: 'promise_to_pay', promise_amount: 10000, promise_date: '2025-12-30', operator_name: 'Козлов Д.' },
  ],
  nba_recommendations: [
    {
      id: 1,
      recommended_datetime: '2026-01-21T14:00:00',
      recommended_channel: 'phone',
      recommended_scenario: 'restructure_offer',
      recommended_offer: 'restructure_6m',
      confidence_score: 0.85,
      urgency: 4,
      max_discount_percent: 15,
      reasoning: 'Клиент демонстрирует желание платить, но испытывает временные финансовые трудности. Реструктуризация повысит вероятность возврата на 35%.',
    },
  ],
  latest_forecast: {
    return_probability: 0.68,
    partial_return_probability: 0.82,
    expected_return_amount: 125000,
    expected_return_days: 45,
    recommendation: 'restructure',
    recommendation_confidence: 0.78,
    positive_factors: ['Стабильная занятость', 'История частичных платежей', 'Готовность к диалогу'],
    negative_factors: ['Множественные кредиты', 'Средняя просрочка > 30 дней'],
    npv_continue: 85000,
    npv_sell: 45000,
    npv_write_off: -156000,
  },
};

const MOCK_SCRIPTS = [
  {
    id: 1,
    name: 'Забывчивый клиент',
    psychotype: 'forgetful',
    success_rate: 0.72,
    opening_phrases: [
      'Добрый день! Напоминаю вам о платеже по кредиту.',
      'Здравствуйте! Хотела уточнить, получили ли вы напоминание о платеже?',
    ],
    key_phrases: [
      'Давайте вместе посмотрим график платежей.',
      'Могу отправить вам SMS-напоминание перед следующим платежом.',
      'Для удобства можно настроить автоплатёж.',
    ],
    objection_handlers: {
      'Я забыл': ['Понимаю, такое бывает. Давайте настроим напоминания?', 'Ничего страшного! Можем обсудить удобный способ оповещений.'],
      'Не получал напоминание': ['Проверю вашу контактную информацию. Какой номер для SMS предпочтительнее?'],
    },
    closing_phrases: [
      'Отлично! Я зафиксировала дату платежа. Напомним вам за день.',
      'Спасибо за разговор! Напоминание придёт на ваш телефон.',
    ],
  },
  {
    id: 2,
    name: 'Мягкое напоминание',
    psychotype: 'cooperative',
    success_rate: 0.68,
    opening_phrases: [
      'Добрый день! Звоню уточнить статус по платежу.',
      'Здравствуйте! Как ваши дела? Хотела обсудить текущий платёж.',
    ],
    key_phrases: [
      'Понимаю, что ситуации бывают разные.',
      'Мы ценим вашу историю сотрудничества.',
      'Давайте найдём удобное решение.',
    ],
    objection_handlers: {
      'Сейчас нет денег': ['Понимаю. Когда ожидаете поступление средств?', 'Можем обсудить частичный платёж.'],
      'Перезвоните позже': ['Конечно! В какое время вам удобно?'],
    },
    closing_phrases: [
      'Спасибо за разговор! Буду ждать платёж в оговорённый срок.',
      'Отлично договорились! Хорошего дня!',
    ],
  },
];

// ===== API =====
const API_BASE = 'http://127.0.0.1:8000/api';

function getAuthHeaders() {
  const token = localStorage.getItem('authToken');
  return {
    'Content-Type': 'application/json',
    'Authorization': `Token ${token}`,
  };
}

async function fetchClient360(clientId) {
  if (USE_MOCK) {
    return Promise.resolve({ ...MOCK_CLIENT, id: clientId });
  }
  const response = await fetch(`${API_BASE}/clients/${clientId}/profile_360/`);
  if (!response.ok) throw new Error('Failed to fetch client profile');
  return response.json();
}

async function fetchSmartScripts(psychotype = '') {
  if (USE_MOCK) {
    const filtered = psychotype && psychotype !== 'unknown'
      ? MOCK_SCRIPTS.filter(s => s.psychotype === psychotype || s.psychotype === 'cooperative')
      : MOCK_SCRIPTS;
    return Promise.resolve(filtered);
  }
  const params = new URLSearchParams();
  if (psychotype && psychotype !== 'unknown') {
    params.append('psychotype', psychotype);
  }
  const response = await fetch(`${API_BASE}/scripts/?${params}`);
  if (!response.ok) throw new Error('Failed to fetch scripts');
  return response.json();
}

async function executeNBA(nbaId) {
  if (USE_MOCK) {
    return Promise.resolve({ success: true });
  }
  const response = await fetch(`${API_BASE}/nba/${nbaId}/execute/`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to execute NBA');
  return response.json();
}

async function skipNBA(nbaId) {
  if (USE_MOCK) {
    return Promise.resolve({ success: true });
  }
  const response = await fetch(`${API_BASE}/nba/${nbaId}/skip/`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to skip NBA');
  return response.json();
}

// ===== HELPER FUNCTIONS =====
function formatCurrency(value) {
  if (value === null || value === undefined) return '—';
  return Number(value).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 });
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  return date.toLocaleDateString('ru-RU');
}

function formatDateTime(dateStr) {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  return date.toLocaleString('ru-RU', { 
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}

function getPsychotypeColor(psychotype) {
  const colors = {
    forgetful: '#f59e0b',
    unwilling: '#ef4444',
    unable: '#3b82f6',
    toxic: '#dc2626',
    cooperative: '#22c55e',
  };
  return colors[psychotype] || '#6b7280';
}

function getPsychotypeLabel(psychotype) {
  const labels = {
    forgetful: 'Забывчивый',
    unwilling: 'Не хочет платить',
    unable: 'Хочет, но не может',
    toxic: 'Токсичный',
    cooperative: 'Кооперативный',
  };
  return labels[psychotype] || 'Неизвестно';
}

function getResultBadge(result) {
  const badges = {
    promise_to_pay: { label: 'Обещание', color: '#3fb950', bg: 'rgba(63,185,80,0.2)' },
    no_answer: { label: 'Не дозвон', color: '#8b949e', bg: '#21262d' },
    callback: { label: 'Перезвонить', color: '#d29922', bg: 'rgba(210,153,34,0.2)' },
    refuse: { label: 'Отказ', color: '#f85149', bg: 'rgba(248,81,73,0.2)' },
    promise: { label: 'Обещание', color: '#3fb950', bg: 'rgba(63,185,80,0.2)' },
    completed: { label: 'Завершено', color: '#3fb950', bg: 'rgba(63,185,80,0.2)' },
    partial_payment: { label: 'Частичная оплата', color: '#388bfd', bg: 'rgba(56,139,253,0.2)' },
    full_payment: { label: 'Полная оплата', color: '#3fb950', bg: 'rgba(63,185,80,0.2)' },
  };
  return badges[result] || { label: result || '—', color: '#8b949e', bg: '#21262d' };
}

function getChannelIcon(channel) {
  const icons = { phone: '📞', sms: '✉️', whatsapp: '💬', email: '📧', push: '🔔', letter: '✉️', visit: '🚶' };
  return icons[channel] || '📞';
}

function getChannelLabel(channel) {
  const labels = { phone: 'Телефон', sms: 'SMS', whatsapp: 'WhatsApp', email: 'Email', push: 'Push', letter: 'Письмо', visit: 'Визит' };
  return labels[channel] || channel;
}

function getScenarioLabel(scenario) {
  const labels = {
    soft_reminder: 'Мягкое напоминание',
    firm_demand: 'Жёсткое требование',
    empathy: 'Эмпатичный подход',
    restructure_offer: 'Предложение реструктуризации',
    discount_offer: 'Предложение скидки',
    payment_holiday: 'Кредитные каникулы',
    last_warning: 'Последнее предупреждение',
  };
  return labels[scenario] || scenario;
}

function getOfferLabel(offer) {
  const labels = {
    none: 'Без предложения',
    discount_10: 'Скидка 10%',
    discount_20: 'Скидка 20%',
    discount_50: 'Скидка 50%',
    restructure_6m: 'Реструктуризация на 6 мес',
    restructure_12m: 'Реструктуризация на 12 мес',
    holiday_1m: 'Каникулы 1 месяц',
    holiday_3m: 'Каникулы 3 месяца',
  };
  return labels[offer] || offer;
}

function getRecommendationLabel(rec) {
  const labels = {
    continue_soft: 'Мягкое взыскание',
    continue_hard: 'Усилить давление',
    restructure: 'Реструктуризация',
    sell: 'Продать коллекторам',
    write_off: 'Списать долг',
    legal: 'Судебное взыскание',
  };
  return labels[rec] || rec;
}

function getDayLabel(day) {
  const days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'];
  return days[day] || '—';
}

// ===== COMPONENTS =====

function RiskTriggerBadge({ type, active }) {
  if (!active) return null;
  const triggers = {
    income_dropped: { bg: 'rgba(248,81,73,0.2)', color: '#f85149', icon: '💰', label: 'Падение дохода' },
    job_changed_recently: { bg: 'rgba(248,81,73,0.2)', color: '#f85149', icon: '💼', label: 'Смена работы' },
    multiple_credits: { bg: 'rgba(210,153,34,0.2)', color: '#d29922', icon: '🏦', label: 'Много кредитов' },
    activity_dropped: { bg: 'rgba(210,153,34,0.2)', color: '#d29922', icon: '📉', label: 'Падение активности' },
  };
  const style = triggers[type] || { bg: '#21262d', color: '#8b949e', icon: '⚡', label: type };
  
  return (
    <div className="risk-trigger" style={{ background: style.bg, color: style.color }}>
      <span>{style.icon}</span>
      <span>{style.label}</span>
    </div>
  );
}

function NBAPanel({ nba, onExecute, onSkip }) {
  if (!nba) {
    return (
      <div className="nba-panel empty">
        <h3>🎯 Next Best Action</h3>
        <p>Нет активных рекомендаций для этого клиента</p>
      </div>
    );
  }
  
  const confidenceScore = Number(nba.confidence_score || 0);
  const urgency = nba.urgency || 3;
  const urgencyLabels = { 1: 'Низкая', 2: 'Ниже среднего', 3: 'Средняя', 4: 'Высокая', 5: 'Критическая' };
  
  return (
    <div className="nba-panel">
      <div className="nba-header">
        <h3>🎯 Next Best Action</h3>
        <span className="nba-confidence">{Math.round(confidenceScore * 100)}% уверенность</span>
      </div>
      
      <div className="nba-grid">
        <div className="nba-item">
          <div className="nba-label">Когда</div>
          <div className="nba-value">{formatDateTime(nba.recommended_datetime)}</div>
          <div className={`urgency-badge urgency-${urgency}`}>
            Срочность: {urgencyLabels[urgency]}
          </div>
        </div>
        
        <div className="nba-item">
          <div className="nba-label">Канал</div>
          <div className="nba-value channel-icon">
            {getChannelIcon(nba.recommended_channel)}
            {' '}{getChannelLabel(nba.recommended_channel)}
          </div>
        </div>
        
        <div className="nba-item">
          <div className="nba-label">Сценарий</div>
          <div className="nba-value">{getScenarioLabel(nba.recommended_scenario)}</div>
        </div>
        
        <div className="nba-item">
          <div className="nba-label">Предложение</div>
          <div className="nba-value offer-value">{getOfferLabel(nba.recommended_offer)}</div>
          {nba.max_discount_percent > 0 && (
            <div className="max-discount">Макс. скидка: {nba.max_discount_percent}%</div>
          )}
        </div>
      </div>
      
      <div className="nba-reasoning">
        <strong>💡 Обоснование:</strong> {nba.reasoning}
      </div>
      
      <div className="nba-actions">
        <button className="btn" onClick={() => onExecute(nba.id)}>✓ Принять</button>
        <button className="btn ghost" onClick={() => onSkip(nba.id)}>✗ Отклонить</button>
      </div>
    </div>
  );
}

function ForecastPanel({ forecast }) {
  if (!forecast) {
    return (
      <div className="forecast-panel empty">
        <h3>📊 Прогноз возврата</h3>
        <p>Нет данных о прогнозе</p>
      </div>
    );
  }
  
  const returnProb = Number(forecast.return_probability || 0);
  const partialProb = Number(forecast.partial_return_probability || 0);
  const expectedAmount = Number(forecast.expected_return_amount || 0);
  const expectedDays = forecast.expected_return_days || 0;
  const recConfidence = Number(forecast.recommendation_confidence || 0);
  
  const probColor = returnProb >= 0.6 ? '#22c55e' : returnProb >= 0.4 ? '#f59e0b' : '#ef4444';
  
  const positiveFactors = forecast.positive_factors || [];
  const negativeFactors = forecast.negative_factors || [];
  
  return (
    <div className="forecast-panel">
      <h3>📊 Прогноз возврата</h3>
      
      <div className="forecast-main">
        <div className="forecast-probability">
          <div className="prob-circle" style={{ borderColor: probColor }}>
            <span className="prob-value" style={{ color: probColor }}>
              {Math.round(returnProb * 100)}%
            </span>
            <span className="prob-label">вероятность</span>
          </div>
        </div>
        
        <div className="forecast-details">
          <div className="forecast-row">
            <span>Частичный возврат:</span>
            <strong>{Math.round(partialProb * 100)}%</strong>
          </div>
          <div className="forecast-row">
            <span>Ожидаемая сумма:</span>
            <strong>{formatCurrency(expectedAmount)}</strong>
          </div>
          <div className="forecast-row">
            <span>Ожидаемый срок:</span>
            <strong>{expectedDays} дней</strong>
          </div>
        </div>
      </div>
      
      <div className="forecast-factors">
        {positiveFactors.length > 0 && (
          <div className="factors-positive">
            <strong>✅ Позитивные факторы:</strong>
            <ul>{positiveFactors.map((f, i) => <li key={i}>{f}</li>)}</ul>
          </div>
        )}
        {negativeFactors.length > 0 && (
          <div className="factors-negative">
            <strong>❌ Негативные факторы:</strong>
            <ul>{negativeFactors.map((f, i) => <li key={i}>{f}</li>)}</ul>
          </div>
        )}
      </div>
      
      <div className="forecast-npv">
        <strong>NPV стратегий:</strong>
        <div className="npv-grid">
          <div className="npv-item">
            <span>Продолжать</span>
            <strong className={Number(forecast.npv_continue) >= 0 ? 'positive' : 'negative'}>
              {formatCurrency(forecast.npv_continue)}
            </strong>
          </div>
          <div className="npv-item">
            <span>Продать</span>
            <strong>{formatCurrency(forecast.npv_sell)}</strong>
          </div>
          <div className="npv-item">
            <span>Списать</span>
            <strong className="negative">{formatCurrency(forecast.npv_write_off)}</strong>
          </div>
        </div>
      </div>
      
      <div className="forecast-recommendation">
        <strong>🎯 Рекомендация:</strong> {getRecommendationLabel(forecast.recommendation)}
        <span className="rec-confidence">({Math.round(recConfidence * 100)}%)</span>
      </div>
    </div>
  );
}

function CopilotPanel({ psychotype, onUsePhrase }) {
  const [scripts, setScripts] = useState([]);
  const [activeScript, setActiveScript] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadScripts();
  }, [psychotype]);
  
  async function loadScripts() {
    setLoading(true);
    try {
      const data = await fetchSmartScripts(psychotype);
      setScripts(data.results || data || []);
      if (data.results?.length > 0 || data.length > 0) {
        setActiveScript((data.results || data)[0]);
      }
    } catch (error) {
      console.error('Failed to load scripts:', error);
    } finally {
      setLoading(false);
    }
  }
  
  if (loading) {
    return (
      <div className="copilot-panel loading">
        <h3>🤖 Copilot-подсказки</h3>
        <p>Загрузка скриптов...</p>
      </div>
    );
  }
  
  return (
    <div className="copilot-panel">
      <div className="copilot-header">
        <h3>🤖 Copilot-подсказки</h3>
        <span className="copilot-badge">AI-ассистент</span>
      </div>
      
      {/* Script selector */}
      <div className="copilot-section">
        <h4>📜 Выберите скрипт</h4>
        <div className="script-selector">
          {scripts.map((script) => (
            <button 
              key={script.id}
              className={`script-btn ${activeScript?.id === script.id ? 'active' : ''}`}
              onClick={() => setActiveScript(script)}
            >
              {script.name} ({Math.round((script.success_rate || 0) * 100)}%)
            </button>
          ))}
        </div>
      </div>
      
      {activeScript && (
        <>
          <div className="copilot-section">
            <h4>💬 Вступительные фразы</h4>
            <div className="suggestions-list">
              {(activeScript.opening_phrases || []).map((phrase, i) => (
                <div key={i} className="script-suggestion">
                  <div className="suggestion-phrase">"{phrase}"</div>
                  <button className="btn small ghost" onClick={() => onUsePhrase(phrase)}>📋</button>
                </div>
              ))}
            </div>
          </div>
          
          <div className="copilot-section">
            <h4>⭐ Ключевые фразы</h4>
            <div className="suggestions-list">
              {(activeScript.key_phrases || []).map((phrase, i) => (
                <div key={i} className="script-suggestion">
                  <div className="suggestion-phrase">"{phrase}"</div>
                  <button className="btn small ghost" onClick={() => onUsePhrase(phrase)}>📋</button>
                </div>
              ))}
            </div>
          </div>
          
          <div className="copilot-section">
            <h4>🛡️ Обработка возражений</h4>
            <div className="objections-list">
              {Object.entries(activeScript.objection_handlers || {}).map(([objection, responses]) => (
                <div key={objection} className="objection-item">
                  <div className="objection-trigger">"{objection}"</div>
                  <div className="objection-responses">
                    {responses.map((response, i) => (
                      <div key={i} className="response-item" onClick={() => onUsePhrase(response)}>
                        <span>→ {response}</span>
                        <button className="btn small ghost">📋</button>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          <div className="copilot-section">
            <h4>✅ Завершающие фразы</h4>
            <div className="suggestions-list">
              {(activeScript.closing_phrases || []).map((phrase, i) => (
                <div key={i} className="script-suggestion">
                  <div className="suggestion-phrase">"{phrase}"</div>
                  <button className="btn small ghost" onClick={() => onUsePhrase(phrase)}>📋</button>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ===== MAIN COMPONENT =====

export default function Client360Page({ clientId, onBack }) {
  const [activeTab, setActiveTab] = useState('overview');
  const [copiedPhrase, setCopiedPhrase] = useState(null);
  const [loading, setLoading] = useState(!!clientId);
  const [error, setError] = useState(null);
  
  // Данные клиента
  const [client, setClient] = useState(null);
  const [profile, setProfile] = useState(null);
  const [credits, setCredits] = useState([]);
  const [interventions, setInterventions] = useState([]);
  const [nbaList, setNbaList] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [riskPredictions, setRiskPredictions] = useState(null);
  
  useEffect(() => {
    loadClientData();
  }, [clientId]);
  
  async function loadClientData() {
    setLoading(true);
    setError(null);
    
    try {
      const data = await fetchClient360(clientId);
      
      setClient(data);
      setProfile(data.behavior_profile);
      setCredits(data.credits || []);
      setInterventions(data.interventions || []);
      setNbaList(data.nba_recommendations || []);
      setForecast(data.latest_forecast);
      
      // Fetch ML risk predictions
      try {
        const riskResp = await fetch(`${API_BASE}/overdue-prediction/?client_id=${clientId}`);
        if (riskResp.ok) {
          const riskData = await riskResp.json();
          setRiskPredictions(riskData.results || []);
        }
      } catch (e) {
        console.warn('Risk prediction fetch failed:', e);
      }
      
    } catch (err) {
      console.error('Failed to load client data:', err);
      setError('Ошибка загрузки данных клиента');
    } finally {
      setLoading(false);
    }
  }
  
  const handleUsePhrase = (phrase) => {
    navigator.clipboard.writeText(phrase);
    setCopiedPhrase(phrase);
    setTimeout(() => setCopiedPhrase(null), 2000);
  };
  
  const handleExecuteNBA = async (nbaId) => {
    try {
      await executeNBA(nbaId);
      setNbaList(prev => prev.filter(n => n.id !== nbaId));
    } catch (err) {
      console.error('Failed to execute NBA:', err);
    }
  };
  
  const handleSkipNBA = async (nbaId) => {
    try {
      await skipNBA(nbaId);
      setNbaList(prev => prev.filter(n => n.id !== nbaId));
    } catch (err) {
      console.error('Failed to skip NBA:', err);
    }
  };

  if (!clientId) {
    return (
      <div className="client-360-page error">
        <header className="client-360-header">
          <button className="btn ghost" onClick={onBack}>← Назад</button>
          <div className="client-main-info">
            <h1>360° Профиль клиента</h1>
          </div>
        </header>
        <div className="error-message" style={{textAlign:'center',padding:'60px 40px',color:'#737373'}}>
          Выберите клиента из рабочего стола оператора, нажав кнопку «👤 360° профиль»
        </div>
      </div>
    );
  }
  
  if (loading) {
    return (
      <div className="client-360-page loading">
        <header className="client-360-header">
          <button className="btn ghost" onClick={onBack}>← Назад</button>
          <div className="client-main-info">
            <h1>Загрузка...</h1>
          </div>
        </header>
        <div className="loading-spinner">Загрузка данных клиента...</div>
      </div>
    );
  }
  
  if (error || !client) {
    return (
      <div className="client-360-page error">
        <header className="client-360-header">
          <button className="btn ghost" onClick={onBack}>← Назад</button>
          <div className="client-main-info">
            <h1>Ошибка</h1>
          </div>
        </header>
        <div className="error-message">{error || 'Клиент не найден'}</div>
      </div>
    );
  }
  
  const psychotype = profile?.psychotype || 'unknown';
  const psychotypeLabel = getPsychotypeLabel(psychotype);
  const psychotypeConfidence = Number(profile?.psychotype_confidence || 0);
  
  const totalDebt = client.total_debt || 0;
  const totalOverdue = client.total_overdue || 0;
  
  const paymentDiscipline = Number(profile?.payment_discipline_score || 0);
  const paymentsOnTime = Number(profile?.payments_on_time_ratio || 0);
  const promisesKeptRatio = Number(profile?.promises_kept_ratio || 0);
  const avgDaysOverdue = profile?.avg_days_overdue || 0;
  const totalContacts = profile?.total_contacts || 0;
  const successfulContacts = profile?.successful_contacts || 0;
  
  const preferredChannel = getChannelLabel(profile?.preferred_channel);
  const bestContactHour = profile?.best_contact_hour || 12;
  const bestContactDay = profile?.best_contact_day ?? 0;
  
  const primaryNBA = nbaList.length > 0 ? nbaList[0] : null;
  
  return (
    <div className="client-360-page">
      {/* Header */}
      <header className="client-360-header">
        <button className="btn ghost" onClick={onBack}>← Назад</button>
        <div className="client-main-info">
          <h1>{client.full_name}</h1>
          <div className="client-meta">
            <span>{client.phone_mobile}</span>
            <span>•</span>
            <span>{client.city}</span>
            {(client.employer_name || client.employer) && (
              <>
                <span>•</span>
                <span>{client.employer_name || client.employer}</span>
              </>
            )}
          </div>
        </div>
        <div className="client-psychotype" style={{ borderColor: getPsychotypeColor(psychotype) }}>
          <span className="psychotype-label">{psychotypeLabel}</span>
          <span className="psychotype-confidence">{Math.round(psychotypeConfidence * 100)}%</span>
        </div>
      </header>
      
      {/* Tabs */}
      <nav className="client-360-tabs">
        <button className={activeTab === 'overview' ? 'active' : ''} onClick={() => setActiveTab('overview')}>
          📊 Обзор
        </button>
        <button className={activeTab === 'nba' ? 'active' : ''} onClick={() => setActiveTab('nba')}>
          🎯 NBA
        </button>
        <button className={activeTab === 'history' ? 'active' : ''} onClick={() => setActiveTab('history')}>
          📞 История
        </button>
        <button className={activeTab === 'copilot' ? 'active' : ''} onClick={() => setActiveTab('copilot')}>
          🤖 Copilot
        </button>
      </nav>
      
      {/* Copied notification */}
      {copiedPhrase && (
        <div className="copied-notification">✓ Скопировано в буфер</div>
      )}
      
      {/* Content */}
      <div className="client-360-content">
        {activeTab === 'overview' && (
          <div className="overview-layout">
            {/* Left: Key metrics */}
            <div className="overview-left">
              {/* Debt Summary */}
              <div className="metric-card debt-summary">
                <h3>💰 Задолженность</h3>
                <div className="debt-total">
                  <span className="debt-label">Общий долг:</span>
                  <span className="debt-value">{formatCurrency(totalDebt)}</span>
                </div>
                <div className="debt-overdue">
                  <span className="debt-label">Просрочено:</span>
                  <span className="debt-value overdue">{formatCurrency(totalOverdue)}</span>
                </div>
                
                {credits.map(credit => {
                  const state = credit.latest_state;
                  const debt = Number(state?.principal_debt || 0);
                  const overdueDays = state?.overdue_days || state?.dpd || 0;
                  const productLabels = { consumer: 'Потребительский кредит', mortgage: 'Ипотека', car: 'Автокредит', credit_card: 'Кредитная карта', microloan: 'Микрозайм' };
                  const mlRisk = riskPredictions?.find(r => r.credit_id === credit.id);
                  const riskColorMap = { 0: '#22c55e', 1: '#f59e0b', 2: '#ef4444' };
                  const riskLabelMap = { 0: 'Низкий', 1: 'Средний', 2: 'Высокий' };
                  
                  return (
                    <div key={credit.id} className="credit-mini">
                      <div className="credit-mini-header">
                        <span>{productLabels[credit.product_type] || credit.product_type || 'Кредит'}</span>
                        {mlRisk ? (
                          <span style={{
                            padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                            background: `${riskColorMap[mlRisk.risk_category ?? 1]}18`,
                            color: riskColorMap[mlRisk.risk_category ?? 1],
                            border: `1px solid ${riskColorMap[mlRisk.risk_category ?? 1]}40`
                          }}>
                            {riskLabelMap[mlRisk.risk_category ?? 1]} · {Math.round((mlRisk.risk_score || 0) * 100)}
                          </span>
                        ) : (
                          <span className={`risk-badge risk-${credit.risk_segment || 'medium'}`}>
                            {credit.risk_segment || 'medium'}
                          </span>
                        )}
                      </div>
                      <div className="credit-mini-row">
                        <span>Долг: {formatCurrency(debt)}</span>
                        <span className="overdue-days">{overdueDays} дн.</span>
                      </div>
                    </div>
                  );
                })}
              </div>
              
              {/* Payment Discipline */}
              <div className="metric-card">
                <h3>📈 Платёжная дисциплина</h3>
                <div className="discipline-meter">
                  <div 
                    className="discipline-fill" 
                    style={{ 
                      width: `${paymentDiscipline * 100}%`,
                      background: paymentDiscipline > 0.6 ? '#22c55e' : paymentDiscipline > 0.3 ? '#f59e0b' : '#ef4444'
                    }}
                  />
                </div>
                <div className="discipline-stats">
                  <div>
                    <span>Вовремя:</span>
                    <strong>{Math.round(paymentsOnTime * 100)}%</strong>
                  </div>
                  <div>
                    <span>Ср. просрочка:</span>
                    <strong>{Math.round(avgDaysOverdue)} дн.</strong>
                  </div>
                </div>
              </div>
              
              {/* Risk Triggers */}
              <div className="metric-card">
                <h3>⚠️ Триггеры риска</h3>
                <div className="triggers-list">
                  <RiskTriggerBadge type="income_dropped" active={profile?.income_dropped} />
                  <RiskTriggerBadge type="job_changed_recently" active={profile?.job_changed_recently} />
                  <RiskTriggerBadge type="multiple_credits" active={profile?.multiple_credits} />
                  <RiskTriggerBadge type="activity_dropped" active={profile?.activity_dropped} />
                  {!profile?.income_dropped && !profile?.job_changed_recently && !profile?.multiple_credits && !profile?.activity_dropped && (
                    <div className="no-triggers">Триггеров не обнаружено ✓</div>
                  )}
                </div>
              </div>
              
              {/* Contact Preferences */}
              <div className="metric-card">
                <h3>📱 Предпочтения контакта</h3>
                <div className="contact-prefs">
                  <div>
                    <span>Лучший канал:</span>
                    <strong>{preferredChannel}</strong>
                  </div>
                  <div>
                    <span>Лучшее время:</span>
                    <strong>{bestContactHour}:00, {getDayLabel(bestContactDay)}</strong>
                  </div>
                  <div>
                    <span>Контактность:</span>
                    <strong>{totalContacts > 0 ? Math.round((successfulContacts / totalContacts) * 100) : 0}%</strong>
                  </div>
                  <div>
                    <span>Обещания:</span>
                    <strong>{Math.round(promisesKeptRatio * 100)}%</strong>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Right: Risk, Forecast & NBA */}
            <div className="overview-right">
              {/* ML Risk Predictions */}
              {riskPredictions && riskPredictions.length > 0 && (() => {
                const maxRisk = riskPredictions.reduce((a, b) => (b.risk_score || 0) > (a.risk_score || 0) ? b : a, riskPredictions[0]);
                const avgScore = riskPredictions.reduce((s, r) => s + (r.risk_score || 0), 0) / riskPredictions.length;
                const riskColorMap = { 0: '#22c55e', 1: '#f59e0b', 2: '#ef4444' };
                const riskLabelMap = { 0: 'Низкий', 1: 'Средний', 2: 'Высокий' };
                const overallCategory = avgScore > 0.66 ? 2 : avgScore > 0.33 ? 1 : 0;
                const overallColor = riskColorMap[overallCategory];
                const productLabels = { consumer: 'Потребительский', mortgage: 'Ипотека', car: 'Автокредит', credit_card: 'Кредитная карта', microloan: 'Микрозайм' };

                return (
                  <div className="metric-card" style={{ borderLeft: `4px solid ${overallColor}` }}>
                    <h3>🤖 ML-прогноз просрочки</h3>
                    
                    {/* Overall risk gauge */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16, margin: '12px 0' }}>
                      <div style={{
                        width: 64, height: 64, borderRadius: '50%',
                        border: `4px solid ${overallColor}`,
                        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                        background: `${overallColor}15`
                      }}>
                        <span style={{ fontSize: 18, fontWeight: 700, color: overallColor }}>{Math.round(avgScore * 100)}</span>
                        <span style={{ fontSize: 9, color: '#888' }}>из 100</span>
                      </div>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 15, color: overallColor }}>
                          {riskLabelMap[overallCategory]} риск
                        </div>
                        <div style={{ fontSize: 12, color: '#888' }}>
                          {riskPredictions.length} кредит{riskPredictions.length === 1 ? '' : riskPredictions.length < 5 ? 'а' : 'ов'} проанализировано
                        </div>
                        <div style={{ fontSize: 11, color: '#aaa', marginTop: 2 }}>ML-модель · RandomForest</div>
                      </div>
                    </div>

                    {/* Per-credit risks */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
                      {riskPredictions.map((r, i) => {
                        const cat = r.risk_category ?? 1;
                        const clr = riskColorMap[cat];
                        const score = Math.round((r.risk_score || 0) * 100);
                        const cred = credits.find(c => c.id === r.credit_id);
                        const label = cred ? (productLabels[cred.product_type] || cred.product_type) : `Кредит #${r.credit_id}`;
                        return (
                          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderTop: i > 0 ? '1px solid #f0f0f0' : 'none' }}>
                            <div style={{
                              width: 36, height: 36, borderRadius: '50%',
                              background: `${clr}20`, display: 'flex', alignItems: 'center', justifyContent: 'center',
                              fontWeight: 700, fontSize: 13, color: clr, flexShrink: 0
                            }}>{score}</div>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ fontSize: 13, fontWeight: 500 }}>{label}</div>
                              <div style={{ fontSize: 11, color: '#888' }}>{r.risk_label || riskLabelMap[cat]}</div>
                            </div>
                            {/* Probability bars */}
                            {r.probabilities && (
                              <div style={{ display: 'flex', gap: 2, alignItems: 'flex-end', height: 24 }}>
                                {['low', 'medium', 'high'].map((k, j) => {
                                  const pct = Math.round((r.probabilities[k] || 0) * 100);
                                  return (
                                    <div key={k} title={`${k}: ${pct}%`} style={{
                                      width: 8, background: riskColorMap[j],
                                      height: `${Math.max(pct, 4)}%`, borderRadius: 2, opacity: cat === j ? 1 : 0.3
                                    }} />
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {/* Key risk features from highest-risk credit */}
                    {maxRisk.features && (
                      <div style={{ marginTop: 10, padding: '8px 10px', background: '#1c2128', borderRadius: 6, fontSize: 12 }}>
                        <div style={{ fontWeight: 600, marginBottom: 4, color: '#8b949e' }}>Ключевые факторы (макс. риск):</div>
                        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'2px 12px', color:'#8b949e' }}>
                          {maxRisk.features.overdue_days != null && <div>Дней просрочки: <b>{maxRisk.features.overdue_days}</b></div>}
                          {maxRisk.features.debt_to_income != null && <div>Долг/доход: <b>{(maxRisk.features.debt_to_income * 100).toFixed(0)}%</b></div>}
                          {maxRisk.features.payment_ratio != null && <div>Доля платежа: <b>{(maxRisk.features.payment_ratio * 100).toFixed(0)}%</b></div>}
                          {maxRisk.features.total_debt != null && <div>Общий долг: <b>{Number(maxRisk.features.total_debt).toLocaleString('ru')} ₽</b></div>}
                        </div>
                      </div>
                    )}

                    {/* Recommendation */}
                    {maxRisk.recommendation && (
                      <div style={{ marginTop: 8, padding: '6px 10px', background: `${overallColor}10`, borderRadius: 6, fontSize: 12, color: '#8b949e' }}>
                        💡 {maxRisk.recommendation}
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* Forecast Mini */}
              {forecast && (
                <div className="forecast-mini">
                  <h3>🔮 Прогноз возврата</h3>
                  <div className="forecast-mini-content">
                    <div className="forecast-prob" style={{ 
                      color: Number(forecast.return_probability) >= 0.5 ? '#22c55e' : '#f59e0b' 
                    }}>
                      {Math.round(Number(forecast.return_probability) * 100)}%
                    </div>
                    <div className="forecast-details-mini">
                      <div>Ожидается: {formatCurrency(forecast.expected_return_amount)}</div>
                      <div>Срок: {forecast.expected_return_days} дней</div>
                      <div className="recommendation-mini">{getRecommendationLabel(forecast.recommendation)}</div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Quick NBA */}
              {primaryNBA && (
                <div className="nba-mini">
                  <h3>🎯 Рекомендация</h3>
                  <div className="nba-mini-content">
                    <div className="nba-channel-icon">{getChannelIcon(primaryNBA.recommended_channel)}</div>
                    <div className="nba-mini-details">
                      <strong>{getScenarioLabel(primaryNBA.recommended_scenario)}</strong>
                      <div>{getOfferLabel(primaryNBA.recommended_offer)}</div>
                      <div className="nba-time">{formatDateTime(primaryNBA.recommended_datetime)}</div>
                    </div>
                  </div>
                  <button className="btn" onClick={() => setActiveTab('nba')}>Подробнее →</button>
                </div>
              )}
              
              {/* Profile info */}
              {profile && (
                <div className="metric-card">
                  <h3>📋 Рекомендация по стратегии</h3>
                  <div className="strategy-rec">
                    {getRecommendationLabel(profile.strategic_recommendation)}
                  </div>
                  <div className="return-forecast">
                    <span>Вероятность возврата:</span>
                    <strong style={{ color: profile.return_probability >= 0.5 ? '#22c55e' : '#f59e0b' }}>
                      {Math.round((profile.return_probability || 0) * 100)}%
                    </strong>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
        
        {activeTab === 'nba' && (
          <div className="nba-layout">
            <NBAPanel nba={primaryNBA} onExecute={handleExecuteNBA} onSkip={handleSkipNBA} />
            <ForecastPanel forecast={forecast} />
          </div>
        )}
        
        {activeTab === 'history' && (
          <div className="history-layout">
            <div className="history-header">
              <h3>📞 История контактов</h3>
              <div className="history-stats">
                <span>Всего: {interventions.length}</span>
                <span>Контактность: {totalContacts > 0 ? Math.round((successfulContacts / totalContacts) * 100) : 0}%</span>
              </div>
            </div>
            
            <table className="credit-table">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Канал</th>
                  <th>Результат</th>
                  <th>Сумма</th>
                  <th>Дата обещания</th>
                  <th>Оператор</th>
                </tr>
              </thead>
              <tbody>
                {interventions.length > 0 ? (
                  interventions.map((intervention, i) => {
                    const badge = getResultBadge(intervention.status || intervention.result);
                    return (
                      <tr key={i}>
                        <td>{formatDateTime(intervention.datetime)}</td>
                        <td>{getChannelIcon(intervention.intervention_type || intervention.channel)} {getChannelLabel(intervention.intervention_type || intervention.channel)}</td>
                        <td>
                          <span style={{ background: badge.bg, color: badge.color, padding: '2px 8px', borderRadius: 4 }}>
                            {badge.label}
                          </span>
                        </td>
                        <td>{intervention.promise_amount ? formatCurrency(intervention.promise_amount) : '—'}</td>
                        <td>{intervention.promise_date ? formatDate(intervention.promise_date) : '—'}</td>
                        <td>{intervention.operator_name || '—'}</td>
                      </tr>
                    );
                  })
                ) : (
                  <tr><td colSpan="6" className="no-data">Нет истории контактов</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        
        {activeTab === 'copilot' && (
          <CopilotPanel psychotype={psychotype} onUsePhrase={handleUsePhrase} />
        )}
      </div>
    </div>
  );
}
