import React, { useState, useEffect } from 'react';
import './styles.css';

const API_URL = 'http://127.0.0.1:8000/api';

const PRODUCT_TYPES = {
  'consumer': 'Потребительский кредит',
  'mortgage': 'Ипотечный кредит',
  'car': 'Автокредит',
  'credit_card': 'Кредитная карта',
  'microloan': 'Микрозайм',
};

const STATUS_LABELS = {
  'active': 'Действующий',
  'closed': 'Закрыт',
  'overdue': 'Просрочен',
  'default': 'Дефолт',
  'restructured': 'Реструктуризация',
};

const PAYMENT_TYPE_LABELS = {
  'regular': 'Регулярный',
  'early': 'Досрочный',
  'partial': 'Частичный',
  'penalty': 'Штраф',
};

function formatCurrency(v) { 
  return Number(v || 0).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' }); 
}

function formatDate(d) { 
  if (!d) return '—';
  return new Date(d).toLocaleDateString('ru-RU'); 
}

export default function CreditDetailPage({ creditId, onBack, onClient360 }) {
  const [credit, setCredit] = useState(null);
  const [client, setClient] = useState(null);
  const [payments, setPayments] = useState([]);
  const [creditStates, setCreditStates] = useState([]);
  const [interactions, setInteractions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statesTab, setStatesTab] = useState('monthly'); // 'monthly' | 'daily'
  const [dailyStates, setDailyStates] = useState([]);
  const [dailyLoading, setDailyLoading] = useState(false);
  const [dailyPage, setDailyPage] = useState(1);
  const DAILY_PAGE_SIZE = 60;
  const [riskPrediction, setRiskPrediction] = useState(null);

  useEffect(() => {
    if (creditId) {
      fetchCreditDetails();
    }
  }, [creditId]);

  const fetchDailyStates = async () => {
    if (dailyStates.length > 0) return; // already loaded
    try {
      setDailyLoading(true);
      const res = await fetch(`${API_URL}/credit-daily-states/?credit=${creditId}`);
      if (res.ok) {
        const data = await res.json();
        setDailyStates(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.error('Failed to fetch daily states', e);
    } finally {
      setDailyLoading(false);
    }
  };

  const fetchCreditDetails = async () => {
    try {
      setLoading(true);
      setError(null);

      // Загружаем кредит
      const creditRes = await fetch(`${API_URL}/credits/${creditId}/`);
      if (!creditRes.ok) throw new Error('Кредит не найден');
      const creditData = await creditRes.json();
      setCredit(creditData);

      // Загружаем клиента
      if (creditData.client) {
        const clientRes = await fetch(`${API_URL}/clients/${creditData.client}/`);
        if (clientRes.ok) {
          const clientData = await clientRes.json();
          setClient(clientData);
        }
      }

      // Загружаем платежи по этому кредиту
      const paymentsRes = await fetch(`${API_URL}/payments/?credit=${creditId}`);
      if (paymentsRes.ok) {
        const paymentsData = await paymentsRes.json();
        setPayments(Array.isArray(paymentsData) ? paymentsData : paymentsData.results || []);
      }

      // Загружаем состояния кредита
      const statesRes = await fetch(`${API_URL}/credit-states/?credit=${creditId}`);
      if (statesRes.ok) {
        const statesData = await statesRes.json();
        setCreditStates(Array.isArray(statesData) ? statesData : statesData.results || []);
      }

      // Загружаем взаимодействия с клиентом
      if (creditData.client) {
        const interactionsRes = await fetch(`${API_URL}/interventions/?client=${creditData.client}`);
        if (interactionsRes.ok) {
          const interactionsData = await interactionsRes.json();
          setInteractions(Array.isArray(interactionsData) ? interactionsData : interactionsData.results || []);
        }
      }

      // Загружаем прогноз просрочки
      if (creditData.status !== 'closed') {
        try {
          const riskRes = await fetch(`${API_URL}/overdue-prediction/?credit_id=${creditId}`);
          if (riskRes.ok) {
            const riskData = await riskRes.json();
            setRiskPrediction(riskData);
          }
        } catch (e) { /* прогноз не критичен */ }
      }

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{background:'#0d1117', minHeight:'100vh', display:'flex', alignItems:'center', justifyContent:'center'}}>
        <div style={{color:'#8b949e'}}>Загрузка...</div>
      </div>
    );
  }

  if (error || !credit) {
    return (
      <div style={{background:'#0d1117', minHeight:'100vh', padding:'40px'}}>
        <button onClick={onBack} style={{background:'none', border:'none', color:'#8b949e', cursor:'pointer', padding:0, marginBottom:16, fontSize:'0.875rem'}}>
          ← Назад
        </button>
        <div style={{background:'rgba(248,81,73,0.15)', color:'#f85149', padding:'16px 20px', borderLeft:'3px solid #f85149'}}>
          {error || 'Кредит не найден'}
        </div>
      </div>
    );
  }

  const latestState = creditStates.length > 0 
    ? creditStates.sort((a, b) => new Date(b.state_date) - new Date(a.state_date))[0] 
    : null;

  const isOverdue = ['overdue', 'default'].includes(credit.status);

  // Build unified credit events timeline
  const creditEvents = (() => {
    const events = [];

    // Payment events
    payments.forEach(p => {
      const isLate = p.overdue_days > 0;
      events.push({
        date: p.payment_date,
        sortDate: new Date(p.payment_date),
        type: 'payment',
        icon: '💰',
        label: PAYMENT_TYPE_LABELS[p.payment_type] || 'Платёж',
        description: `${formatCurrency(p.amount)}${isLate ? ` (просрочка ${p.overdue_days} дн.)` : ''}`,
          color: isLate ? '#d29922' : '#3fb950',
          bgColor: isLate ? 'rgba(210,153,34,0.15)' : 'rgba(63,185,80,0.15)',
      });
    });

    // Overdue start/end events from credit states
    const sortedStates = [...creditStates].sort((a, b) => new Date(a.state_date) - new Date(b.state_date));
    let wasOverdue = false;
    sortedStates.forEach((s, i) => {
      const dpd = s.overdue_days || 0;
      const overdueAmt = parseFloat(s.overdue_principal || 0) + parseFloat(s.overdue_interest || 0);
      const isOd = dpd > 0 || overdueAmt > 0;

      if (isOd && !wasOverdue) {
        events.push({
          date: s.state_date,
          sortDate: new Date(s.state_date),
          type: 'overdue_start',
          icon: '🔴',
          label: 'Начало просрочки',
          description: `Просроч. ОД: ${formatCurrency(s.overdue_principal)}, DPD: ${dpd}`,
          color: '#f85149',
          bgColor: 'rgba(248,81,73,0.15)',
        });
      }
      if (!isOd && wasOverdue) {
        events.push({
          date: s.state_date,
          sortDate: new Date(s.state_date),
          type: 'overdue_end',
          icon: '🟢',
          label: 'Просрочка погашена',
          description: 'Просроченная задолженность закрыта',
          color: '#3fb950',
          bgColor: 'rgba(63,185,80,0.15)',
        });
      }
      // Penalty events
      if (parseFloat(s.penalties || 0) > 0 && (i === 0 || parseFloat(sortedStates[i - 1].penalties || 0) === 0)) {
        events.push({
          date: s.state_date,
          sortDate: new Date(s.state_date),
          type: 'penalty',
          icon: '⚠️',
          label: 'Начисление штрафа',
          description: `Штраф: ${formatCurrency(s.penalties)}`,
          color: '#d29922',
          bgColor: 'rgba(210,153,34,0.15)',
        });
      }
      wasOverdue = isOd;
    });

    // Credit open event
    if (credit.open_date) {
      events.push({
        date: credit.open_date,
        sortDate: new Date(credit.open_date),
        type: 'open',
        icon: '📋',
        label: 'Выдача кредита',
        description: `${PRODUCT_TYPES[credit.product_type] || credit.product_type}, ${formatCurrency(credit.principal_amount)}`,
        color: '#388bfd',
        bgColor: 'rgba(56,139,253,0.15)',
      });
    }

    // Credit close event
    if (credit.status === 'closed') {
      const lastState = sortedStates.length > 0 ? sortedStates[sortedStates.length - 1] : null;
      events.push({
        date: lastState ? lastState.state_date : credit.planned_close_date,
        sortDate: new Date(lastState ? lastState.state_date : credit.planned_close_date),
        type: 'closed',
        icon: '✅',
        label: 'Кредит закрыт',
        description: 'Задолженность полностью погашена',
        color: '#3fb950',
        bgColor: 'rgba(63,185,80,0.15)',
      });
    }

    events.sort((a, b) => b.sortDate - a.sortDate);
    return events;
  })();

  return (
    <div style={{background:'#0d1117', minHeight:'100vh'}}>
      
      {/* Header */}
      <div style={{borderBottom:'1px solid #30363d', padding:'20px 40px'}}>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start'}}>
          <div>
            <button onClick={onBack} style={{background:'none', border:'none', color:'#8b949e', cursor:'pointer', padding:0, marginBottom:12, fontSize:'0.875rem'}}>
              ← Вернуться к реестру
            </button>
            <h1 style={{margin:0, fontSize:'1.25rem', fontWeight:600, color:'#e6edf3'}}>
              Договор № {credit.id}
            </h1>
            <div style={{color:'#8b949e', fontSize:'0.875rem', marginTop:4}}>
              {PRODUCT_TYPES[credit.product_type] || credit.product_type}
            </div>
          </div>
          <div style={{display:'flex', alignItems:'center', gap:12}}>
            {client && onClient360 && (
              <button
                onClick={() => onClient360(client.id)}
                style={{background:'#21262d', border:'1px solid #30363d', borderRadius:6, padding:'6px 14px', cursor:'pointer', fontSize:'0.8rem', color:'#8b949e', fontWeight:500, display:'flex', alignItems:'center', gap:6}}
                onMouseOver={e => { e.currentTarget.style.background='#30363d'; }}
                onMouseOut={e => { e.currentTarget.style.background='#21262d'; }}
              >
                👤 Клиент 360°
              </button>
            )}
            <div style={{color: isOverdue ? '#f85149' : '#8b949e', fontWeight:500, fontSize:'0.875rem'}}>
              {STATUS_LABELS[credit.status] || credit.status}
            </div>
          </div>
        </div>
      </div>

      {/* Info Sections */}
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', borderBottom:'1px solid #30363d'}}>
        
        {/* Client */}
        <div style={{borderRight:'1px solid #30363d'}}>
          <div style={{padding:'16px 40px', borderBottom:'1px solid #30363d', background:'#1c2128'}}>
            <h2 style={{margin:0, fontSize:'0.8rem', fontWeight:500, color:'#8b949e', textTransform:'uppercase', letterSpacing:'0.5px'}}>Заёмщик</h2>
          </div>
          <div style={{padding:'20px 40px'}}>
            {client ? (
              <table style={{width:'100%', fontSize:'0.875rem'}}>
                <tbody>
                  <tr><td style={{color:'#8b949e', padding:'6px 0', width:'45%'}}>ФИО</td><td>{onClient360 ? <span onClick={() => onClient360(client.id)} style={{color:'#58a6ff', cursor:'pointer', borderBottom:'1px dashed #58a6ff'}}>{client.full_name || '—'}</span> : <span style={{color:'#e6edf3'}}>{client.full_name || '—'}</span>}</td></tr>
                  <tr><td style={{color:'#8b949e', padding:'6px 0'}}>Телефон</td><td style={{color:'#e6edf3'}}>{client.phone_mobile || client.phone_work || '—'}</td></tr>
                  <tr><td style={{color:'#8b949e', padding:'6px 0'}}>Дата рождения</td><td style={{color:'#e6edf3'}}>{formatDate(client.birth_date)}</td></tr>
                  <tr><td style={{color:'#8b949e', padding:'6px 0'}}>Город</td><td style={{color:'#e6edf3'}}>{client.city || client.region || '—'}</td></tr>
                  <tr><td style={{color:'#8b949e', padding:'6px 0'}}>Место работы</td><td style={{color:'#e6edf3'}}>{client.employer_name || '—'}</td></tr>
                  <tr><td style={{color:'#8b949e', padding:'6px 0'}}>Доход</td><td style={{color:'#e6edf3'}}>{client.income ? formatCurrency(client.income) : '—'}</td></tr>
                </tbody>
              </table>
            ) : (
              <div style={{color:'#8b949e'}}>Данные отсутствуют</div>
            )}
          </div>
        </div>

        {/* Credit Parameters */}
        <div>
          <div style={{padding:'16px 40px', borderBottom:'1px solid #30363d', background:'#1c2128'}}>
            <h2 style={{margin:0, fontSize:'0.8rem', fontWeight:500, color:'#8b949e', textTransform:'uppercase', letterSpacing:'0.5px'}}>Параметры кредита</h2>
          </div>
          <div style={{padding:'20px 40px'}}>
            <table style={{width:'100%', fontSize:'0.875rem'}}>
              <tbody>
                <tr><td style={{color:'#8b949e', padding:'6px 0', width:'50%'}}>Сумма</td><td style={{color:'#e6edf3', fontWeight:500}}>{formatCurrency(credit.principal_amount)}</td></tr>
                <tr><td style={{color:'#8b949e', padding:'6px 0'}}>Ставка</td><td style={{color:'#e6edf3'}}>{Number(credit.interest_rate || 0).toFixed(2)}% годовых</td></tr>
                <tr><td style={{color:'#8b949e', padding:'6px 0'}}>Срок</td><td style={{color:'#e6edf3'}}>{credit.term_months ? `${credit.term_months} мес.` : '—'}</td></tr>
                <tr><td style={{color:'#8b949e', padding:'6px 0'}}>Ежемесячный платёж</td><td style={{color:'#e6edf3', fontWeight:500}}>{formatCurrency(credit.monthly_payment)}</td></tr>
                <tr><td style={{color:'#8b949e', padding:'6px 0'}}>Дата выдачи</td><td style={{color:'#e6edf3'}}>{formatDate(credit.open_date)}</td></tr>
                <tr><td style={{color:'#8b949e', padding:'6px 0'}}>Дата окончания</td><td style={{color:'#e6edf3'}}>{formatDate(credit.planned_close_date)}</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Current State */}
      {latestState && (
        <div style={{borderBottom:'1px solid #30363d'}}>
          <div style={{padding:'16px 40px', borderBottom:'1px solid #30363d', background:'#1c2128'}}>
            <h2 style={{margin:0, fontSize:'0.8rem', fontWeight:500, color:'#8b949e', textTransform:'uppercase', letterSpacing:'0.5px'}}>
              Текущее состояние
              {latestState.state_date && <span style={{fontWeight:400, marginLeft:8}}>на {formatDate(latestState.state_date)}</span>}
            </h2>
          </div>
          <div style={{display:'grid', gridTemplateColumns:'repeat(5, 1fr)'}}>
            <div style={{padding:'24px 40px', borderRight:'1px solid #30363d'}}>
              <div style={{color:'#8b949e', fontSize:'0.75rem', textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:4}}>Основной долг</div>
              <div style={{fontSize:'1.25rem', fontWeight:600, color:'#e6edf3'}}>{formatCurrency(latestState.principal_debt)}</div>
            </div>
            <div style={{padding:'24px 40px', borderRight:'1px solid #30363d'}}>
              <div style={{color:'#8b949e', fontSize:'0.75rem', textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:4}}>Просроч. основной</div>
              <div style={{fontSize:'1.25rem', fontWeight:600, color: parseFloat(latestState.overdue_principal) > 0 ? '#f85149' : '#e6edf3'}}>{formatCurrency(latestState.overdue_principal)}</div>
            </div>
            <div style={{padding:'24px 40px', borderRight:'1px solid #30363d'}}>
              <div style={{color:'#8b949e', fontSize:'0.75rem', textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:4}}>Просроч. проценты</div>
              <div style={{fontSize:'1.25rem', fontWeight:600, color: parseFloat(latestState.overdue_interest) > 0 ? '#f85149' : '#e6edf3'}}>{formatCurrency(latestState.overdue_interest)}</div>
            </div>
            <div style={{padding:'24px 40px', borderRight:'1px solid #30363d'}}>
              <div style={{color:'#8b949e', fontSize:'0.75rem', textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:4}}>Штрафы / пени</div>
              <div style={{fontSize:'1.25rem', fontWeight:600, color: parseFloat(latestState.penalties) > 0 ? '#f85149' : '#e6edf3'}}>{formatCurrency(latestState.penalties)}</div>
            </div>
            <div style={{padding:'24px 40px'}}>
              <div style={{color:'#8b949e', fontSize:'0.75rem', textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:4}}>Дней просрочки</div>
              <div style={{fontSize:'1.25rem', fontWeight:600, color: latestState.overdue_days > 0 ? '#f85149' : '#e6edf3'}}>{latestState.overdue_days ?? 0}</div>
            </div>
          </div>
        </div>
      )}

      {/* Risk Prediction Widget */}
      {riskPrediction && (
        <div style={{borderBottom:'1px solid #30363d'}}>
          <div style={{padding:'16px 40px', borderBottom:'1px solid #30363d', background:'#1c2128'}}>
            <h2 style={{margin:0, fontSize:'0.8rem', fontWeight:500, color:'#8b949e', textTransform:'uppercase', letterSpacing:'0.5px'}}>
              Прогноз просрочки (ML-модель)
            </h2>
          </div>
          <div style={{display:'grid', gridTemplateColumns:'200px 1fr 1fr 1fr', gap:0}}>
            {/* Risk gauge */}
            <div style={{padding:'24px 40px', borderRight:'1px solid #30363d', display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center'}}>
              <div style={{
                width:72, height:72, borderRadius:'50%',
                display:'flex', alignItems:'center', justifyContent:'center',
                background: riskPrediction.risk_category === 0 ? 'rgba(63,185,80,0.15)' : riskPrediction.risk_category === 1 ? 'rgba(210,153,34,0.15)' : 'rgba(248,81,73,0.15)',
                border: `3px solid ${riskPrediction.risk_category === 0 ? '#3fb950' : riskPrediction.risk_category === 1 ? '#d29922' : '#f85149'}`,
                marginBottom:8,
              }}>
                <span style={{fontSize:'1.4rem', fontWeight:700, color: riskPrediction.risk_category === 0 ? '#16a34a' : riskPrediction.risk_category === 1 ? '#ca8a04' : '#dc2626'}}>
                  {riskPrediction.risk_score !== undefined ? (riskPrediction.risk_score * 100).toFixed(0) : '—'}
                </span>
              </div>
              <div style={{fontSize:'0.82rem', fontWeight:600, color: riskPrediction.risk_category === 0 ? '#16a34a' : riskPrediction.risk_category === 1 ? '#ca8a04' : '#dc2626'}}>
                {riskPrediction.risk_label || '—'}
              </div>
              <div style={{fontSize:'0.7rem', color:'#484f58', marginTop:2}}>risk score</div>
            </div>
            {/* Probabilities */}
            <div style={{padding:'24px 30px', borderRight:'1px solid #30363d'}}>
              <div style={{color:'#8b949e', fontSize:'0.75rem', textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:12}}>Вероятности</div>
              {riskPrediction.probabilities && Object.entries(riskPrediction.probabilities).map(([label, prob]) => (
                <div key={label} style={{marginBottom:8}}>
                  <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.8rem', marginBottom:3}}>
                    <span style={{color:'#8b949e'}}>{label}</span>
                    <span style={{fontWeight:600, color:'#e6edf3'}}>{(prob * 100).toFixed(1)}%</span>
                  </div>
                  <div style={{height:6, background:'#21262d', borderRadius:3, overflow:'hidden'}}>
                    <div style={{
                      height:'100%', borderRadius:3,
                      width: `${prob * 100}%`,
                      background: label === 'Низкий' ? '#22c55e' : label === 'Средний' ? '#eab308' : '#ef4444',
                    }} />
                  </div>
                </div>
              ))}
            </div>
            {/* Key features */}
            <div style={{padding:'24px 30px', borderRight:'1px solid #30363d'}}>
              <div style={{color:'#8b949e', fontSize:'0.75rem', textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:12}}>Ключевые признаки</div>
              {riskPrediction.features && (
                <table style={{fontSize:'0.78rem', width:'100%'}}>
                  <tbody>
                    {[
                      ['LTI', riskPrediction.features.lti_ratio?.toFixed(2)],
                      ['Макс. просрочка', `${riskPrediction.features.max_overdue_days || 0} дн.`],
                      ['Просрочек за 12м', riskPrediction.features.overdue_count_12m || 0],
                      ['Доля просрочек', `${((riskPrediction.features.overdue_share_12m || 0) * 100).toFixed(0)}%`],
                      ['Обещаний', riskPrediction.features.promises_count || 0],
                    ].map(([k, v]) => (
                      <tr key={k}><td style={{color:'#8b949e', padding:'3px 0'}}>{k}</td><td style={{color:'#e6edf3', fontWeight:500, textAlign:'right'}}>{v}</td></tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            {/* Recommendation */}
            <div style={{padding:'24px 30px'}}>
              <div style={{color:'#8b949e', fontSize:'0.75rem', textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:12}}>Рекомендация</div>
              <div style={{fontSize:'0.85rem', color:'#e6edf3', lineHeight:1.5}}>
                {riskPrediction.risk_category === 0 && '✅ Стандартное сопровождение. Риск просрочки минимален.'}
                {riskPrediction.risk_category === 1 && '⚠️ Повышенное внимание. Рекомендуется превентивный контакт и мониторинг платёжной дисциплины.'}
                {riskPrediction.risk_category === 2 && '🔴 Высокий риск. Необходимо срочное воздействие: звонок, предложение реструктуризации.'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Credit Events */}
      <div style={{borderBottom:'1px solid #30363d'}}>
        <div style={{padding:'16px 40px', borderBottom:'1px solid #30363d', background:'#1c2128'}}>
          <h2 style={{margin:0, fontSize:'0.8rem', fontWeight:500, color:'#8b949e', textTransform:'uppercase', letterSpacing:'0.5px'}}>
            События кредита ({creditEvents.length})
          </h2>
        </div>
        {creditEvents.length > 0 ? (
          <div style={{padding:'20px 40px'}}>
            <div style={{position:'relative'}}>
              {/* Timeline line */}
              <div style={{position:'absolute', left:15, top:8, bottom:8, width:2, background:'#30363d'}} />
              {creditEvents.slice(0, 30).map((ev, idx) => (
                <div key={idx} style={{display:'flex', gap:16, marginBottom:idx < creditEvents.length - 1 ? 12 : 0, position:'relative'}}>
                  {/* Icon dot */}
                  <div style={{
                    width:32, minWidth:32, height:32, borderRadius:'50%',
                    display:'flex', alignItems:'center', justifyContent:'center',
                    fontSize:'0.85rem', background: ev.bgColor, border: `2px solid ${ev.color}`,
                    position:'relative', zIndex:1,
                  }}>
                    {ev.icon}
                  </div>
                  {/* Content */}
                  <div style={{flex:1, paddingTop:2}}>
                    <div style={{display:'flex', alignItems:'baseline', gap:10}}>
                      <span style={{fontSize:'0.8rem', color:'#8b949e', minWidth:85}}>{formatDate(ev.date)}</span>
                      <span style={{
                        fontSize:'0.7rem', fontWeight:600, textTransform:'uppercase',
                        padding:'1px 8px', borderRadius:3,
                        background: ev.bgColor, color: ev.color,
                        letterSpacing:'0.3px',
                      }}>
                        {ev.label}
                      </span>
                    </div>
                    <div style={{fontSize:'0.82rem', color:'#8b949e', marginTop:2}}>{ev.description}</div>
                  </div>
                </div>
              ))}
              {creditEvents.length > 30 && (
                <div style={{textAlign:'center', color:'#8b949e', fontSize:'0.8rem', paddingTop:8}}>
                  … и ещё {creditEvents.length - 30} событий
                </div>
              )}
            </div>
          </div>
        ) : (
          <div style={{padding:'40px', textAlign:'center', color:'#8b949e'}}>Нет событий</div>
        )}
      </div>

      {/* Interactions */}
      <div style={{borderBottom:'1px solid #30363d'}}>
        <div style={{padding:'16px 40px', borderBottom:'1px solid #30363d', background:'#1c2128'}}>
          <h2 style={{margin:0, fontSize:'0.8rem', fontWeight:500, color:'#8b949e', textTransform:'uppercase', letterSpacing:'0.5px'}}>Взаимодействия ({interactions.length})</h2>
        </div>
        {interactions.length > 0 ? (
          <table style={{width:'100%', borderCollapse:'collapse', fontSize:'0.875rem'}}>
            <thead>
              <tr style={{background:'#1c2128'}}>
                <th style={{textAlign:'left', padding:'10px 40px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Дата</th>
                <th style={{textAlign:'left', padding:'10px 20px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Оператор</th>
                <th style={{textAlign:'left', padding:'10px 20px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Тип</th>
                <th style={{textAlign:'left', padding:'10px 20px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Результат</th>
                <th style={{textAlign:'right', padding:'10px 20px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Сумма обещания</th>
                <th style={{textAlign:'left', padding:'10px 40px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Комментарий</th>
              </tr>
            </thead>
            <tbody>
              {interactions.slice(0, 20).map((item, idx) => (
                <tr key={idx} style={{borderBottom:'1px solid #30363d'}}>
                  <td style={{padding:'10px 40px', color:'#e6edf3'}}>{formatDate(item.datetime)}</td>
                  <td style={{padding:'10px 20px', color:'#8b949e', fontSize:'0.82rem'}}>{item.operator_name || '—'}</td>
                  <td style={{padding:'10px 20px', color:'#e6edf3'}}>{item.intervention_type === 'phone' ? 'Звонок' : item.intervention_type === 'sms' ? 'СМС' : item.intervention_type === 'email' ? 'Email' : item.intervention_type === 'letter' ? 'Письмо' : item.intervention_type === 'visit' ? 'Визит' : item.intervention_type}</td>
                  <td style={{padding:'10px 20px', color:'#e6edf3'}}>{item.status === 'completed' ? 'Завершено' : item.status === 'no_answer' ? 'Не дозвон' : item.status === 'promise' ? 'Обещание' : item.status === 'refuse' ? 'Отказ' : item.status === 'callback' ? 'Перезвонить' : item.status}</td>
                  <td style={{padding:'10px 20px', textAlign:'right', color: parseFloat(item.promise_amount) > 0 ? '#3fb950' : '#484f58', fontWeight: parseFloat(item.promise_amount) > 0 ? 500 : 400}}>
                    {parseFloat(item.promise_amount) > 0 ? formatCurrency(item.promise_amount) : '—'}
                  </td>
                  <td style={{padding:'10px 40px', color:'#8b949e'}}>{item.notes || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{padding:'40px', textAlign:'center', color:'#8b949e'}}>Нет записей</div>
        )}
      </div>

      {/* Payments */}
      <div style={{borderBottom:'1px solid #30363d'}}>
        <div style={{padding:'16px 40px', borderBottom:'1px solid #30363d', background:'#1c2128'}}>
          <h2 style={{margin:0, fontSize:'0.8rem', fontWeight:500, color:'#8b949e', textTransform:'uppercase', letterSpacing:'0.5px'}}>Платежи ({payments.length})</h2>
        </div>
        {payments.length > 0 ? (
          <table style={{width:'100%', borderCollapse:'collapse', fontSize:'0.875rem'}}>
            <thead>
              <tr style={{background:'#1c2128'}}>
                <th style={{textAlign:'left', padding:'10px 40px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Дата</th>
                <th style={{textAlign:'right', padding:'10px 20px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Сумма</th>
                <th style={{textAlign:'left', padding:'10px 20px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Тип</th>
                <th style={{textAlign:'left', padding:'10px 40px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Статус</th>
              </tr>
            </thead>
            <tbody>
              {payments.slice(0, 15).map((item, idx) => (
                <tr key={idx} style={{borderBottom:'1px solid #30363d'}}>
                  <td style={{padding:'10px 40px', color:'#e6edf3'}}>{formatDate(item.payment_date)}</td>
                  <td style={{padding:'10px 20px', textAlign:'right', color:'#e6edf3', fontWeight:500}}>{formatCurrency(item.amount)}</td>
                  <td style={{padding:'10px 20px', color:'#8b949e'}}>{PAYMENT_TYPE_LABELS[item.payment_type] || item.payment_type}</td>
                  <td style={{padding:'10px 40px', color:'#8b949e'}}>{item.status === 'completed' ? 'Исполнен' : item.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{padding:'40px', textAlign:'center', color:'#8b949e'}}>Нет платежей</div>
        )}
      </div>

      {/* Credit States - Tabs */}
      <div>
        <div style={{padding:'16px 40px', borderBottom:'1px solid #30363d', background:'#1c2128', display:'flex', alignItems:'center', gap:16}}>
          <h2 style={{margin:0, fontSize:'0.8rem', fontWeight:500, color:'#8b949e', textTransform:'uppercase', letterSpacing:'0.5px'}}>
            История состояний
          </h2>
          <div style={{display:'flex', gap:4, marginLeft:12}}>
            <button
              onClick={() => setStatesTab('monthly')}
              style={{
                padding:'4px 14px', fontSize:'0.78rem', borderRadius:4, cursor:'pointer',
                border: statesTab === 'monthly' ? '1px solid #388bfd' : '1px solid #30363d',
                background: statesTab === 'monthly' ? 'rgba(56,139,253,0.15)' : '#161b22',
                color: statesTab === 'monthly' ? '#58a6ff' : '#8b949e',
                fontWeight: statesTab === 'monthly' ? 600 : 400,
              }}
            >
              📅 На плановый день платежа ({creditStates.length})
            </button>
            <button
              onClick={() => { setStatesTab('daily'); fetchDailyStates(); setDailyPage(1); }}
              style={{
                padding:'4px 14px', fontSize:'0.78rem', borderRadius:4, cursor:'pointer',
                border: statesTab === 'daily' ? '1px solid #388bfd' : '1px solid #30363d',
                background: statesTab === 'daily' ? 'rgba(56,139,253,0.15)' : '#161b22',
                color: statesTab === 'daily' ? '#58a6ff' : '#8b949e',
                fontWeight: statesTab === 'daily' ? 600 : 400,
              }}
            >
              📆 За каждый день {dailyStates.length > 0 ? `(${dailyStates.length})` : ''}
            </button>
          </div>
        </div>

        {/* Monthly states tab */}
        {statesTab === 'monthly' && (
          creditStates.length > 0 ? (
            <table style={{width:'100%', borderCollapse:'collapse', fontSize:'0.875rem'}}>
              <thead>
                <tr style={{background:'#1c2128'}}>
                  <th style={{textAlign:'left', padding:'10px 40px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Дата</th>
                  <th style={{textAlign:'right', padding:'10px 20px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Основной долг</th>
                  <th style={{textAlign:'right', padding:'10px 20px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Просроч. ОД</th>
                  <th style={{textAlign:'right', padding:'10px 20px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Просроч. %</th>
                  <th style={{textAlign:'right', padding:'10px 20px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Штрафы</th>
                  <th style={{textAlign:'center', padding:'10px 40px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>DPD</th>
                </tr>
              </thead>
              <tbody>
                {creditStates.map((item, idx) => (
                  <tr key={idx} style={{borderBottom:'1px solid #30363d'}}>
                    <td style={{padding:'10px 40px', color:'#e6edf3'}}>{formatDate(item.state_date)}</td>
                    <td style={{padding:'10px 20px', textAlign:'right', color:'#e6edf3'}}>{formatCurrency(item.principal_debt)}</td>
                    <td style={{padding:'10px 20px', textAlign:'right', color: parseFloat(item.overdue_principal) > 0 ? '#f85149' : '#e6edf3'}}>
                      {formatCurrency(item.overdue_principal)}
                    </td>
                    <td style={{padding:'10px 20px', textAlign:'right', color: parseFloat(item.overdue_interest) > 0 ? '#f85149' : '#e6edf3'}}>
                      {formatCurrency(item.overdue_interest)}
                    </td>
                    <td style={{padding:'10px 20px', textAlign:'right', color: parseFloat(item.penalties) > 0 ? '#f85149' : '#e6edf3'}}>{formatCurrency(item.penalties)}</td>
                    <td style={{padding:'10px 40px', textAlign:'center', color: item.overdue_days > 0 ? '#f85149' : '#e6edf3'}}>
                      {item.overdue_days ?? 0}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div style={{padding:'40px', textAlign:'center', color:'#8b949e'}}>Нет данных</div>
          )
        )}

        {/* Daily states tab */}
        {statesTab === 'daily' && (
          dailyLoading ? (
            <div style={{padding:'40px', textAlign:'center', color:'#8b949e'}}>Загрузка ежедневных данных...</div>
          ) : dailyStates.length > 0 ? (
            <>
              <table style={{width:'100%', borderCollapse:'collapse', fontSize:'0.875rem'}}>
                <thead>
                  <tr style={{background:'#1c2128'}}>
                    <th style={{textAlign:'left', padding:'10px 40px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Дата</th>
                    <th style={{textAlign:'right', padding:'10px 20px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Основной долг</th>
                    <th style={{textAlign:'right', padding:'10px 20px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Просроч. ОД</th>
                    <th style={{textAlign:'right', padding:'10px 20px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Просроч. %</th>
                    <th style={{textAlign:'right', padding:'10px 20px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>Штрафы</th>
                    <th style={{textAlign:'center', padding:'10px 40px', color:'#8b949e', fontWeight:500, borderBottom:'1px solid #30363d'}}>DPD</th>
                  </tr>
                </thead>
                <tbody>
                  {dailyStates.slice(0, dailyPage * DAILY_PAGE_SIZE).map((item, idx) => (
                    <tr key={idx} style={{borderBottom:'1px solid #30363d'}}>
                      <td style={{padding:'10px 40px', color:'#e6edf3'}}>{formatDate(item.state_date)}</td>
                      <td style={{padding:'10px 20px', textAlign:'right', color:'#e6edf3'}}>{formatCurrency(item.principal_debt)}</td>
                      <td style={{padding:'10px 20px', textAlign:'right', color: parseFloat(item.overdue_principal) > 0 ? '#f85149' : '#e6edf3'}}>
                        {formatCurrency(item.overdue_principal)}
                      </td>
                      <td style={{padding:'10px 20px', textAlign:'right', color: parseFloat(item.overdue_interest) > 0 ? '#f85149' : '#e6edf3'}}>
                        {formatCurrency(item.overdue_interest)}
                      </td>
                      <td style={{padding:'10px 20px', textAlign:'right', color: parseFloat(item.penalties) > 0 ? '#f85149' : '#e6edf3'}}>{formatCurrency(item.penalties)}</td>
                      <td style={{padding:'10px 40px', textAlign:'center', color: item.overdue_days > 0 ? '#f85149' : '#e6edf3'}}>
                        {item.overdue_days ?? 0}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {dailyPage * DAILY_PAGE_SIZE < dailyStates.length && (
                <div style={{padding:'16px 40px', textAlign:'center', borderTop:'1px solid #30363d'}}>
                  <button
                    onClick={() => setDailyPage(p => p + 1)}
                    style={{
                      padding:'8px 24px', fontSize:'0.8rem', borderRadius:4, cursor:'pointer',
                      border:'1px solid #30363d', background:'#161b22', color:'#8b949e',
                    }}
                  >
                    Показать ещё {Math.min(DAILY_PAGE_SIZE, dailyStates.length - dailyPage * DAILY_PAGE_SIZE)} из {dailyStates.length - dailyPage * DAILY_PAGE_SIZE} записей
                  </button>
                </div>
              )}
            </>
          ) : (
            <div style={{padding:'40px', textAlign:'center', color:'#8b949e'}}>Нет данных</div>
          )
        )}
      </div>

    </div>
  );
}
