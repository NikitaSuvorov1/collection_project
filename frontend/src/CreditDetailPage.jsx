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

function formatCurrency(v) { 
  return Number(v || 0).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' }); 
}

function formatDate(d) { 
  if (!d) return '—';
  return new Date(d).toLocaleDateString('ru-RU'); 
}

export default function CreditDetailPage({ creditId, onBack }) {
  const [credit, setCredit] = useState(null);
  const [client, setClient] = useState(null);
  const [payments, setPayments] = useState([]);
  const [creditStates, setCreditStates] = useState([]);
  const [interactions, setInteractions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (creditId) {
      fetchCreditDetails();
    }
  }, [creditId]);

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
        const interactionsRes = await fetch(`${API_URL}/interactions/?client=${creditData.client}`);
        if (interactionsRes.ok) {
          const interactionsData = await interactionsRes.json();
          setInteractions(Array.isArray(interactionsData) ? interactionsData : interactionsData.results || []);
        }
      }

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{background:'#fff', minHeight:'100vh', display:'flex', alignItems:'center', justifyContent:'center'}}>
        <div style={{color:'#737373'}}>Загрузка...</div>
      </div>
    );
  }

  if (error || !credit) {
    return (
      <div style={{background:'#fff', minHeight:'100vh', padding:'40px'}}>
        <button onClick={onBack} style={{background:'none', border:'none', color:'#525252', cursor:'pointer', padding:0, marginBottom:16, fontSize:'0.875rem'}}>
          ← Назад
        </button>
        <div style={{background:'#fef2f2', color:'#991b1b', padding:'16px 20px', borderLeft:'3px solid #b91c1c'}}>
          {error || 'Кредит не найден'}
        </div>
      </div>
    );
  }

  const latestState = creditStates.length > 0 
    ? creditStates.sort((a, b) => new Date(b.report_date) - new Date(a.report_date))[0] 
    : null;

  const isOverdue = ['overdue', 'default'].includes(credit.status);

  return (
    <div style={{background:'#fff', minHeight:'100vh'}}>
      
      {/* Header */}
      <div style={{borderBottom:'1px solid #e5e5e5', padding:'20px 40px'}}>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start'}}>
          <div>
            <button onClick={onBack} style={{background:'none', border:'none', color:'#525252', cursor:'pointer', padding:0, marginBottom:12, fontSize:'0.875rem'}}>
              ← Вернуться к реестру
            </button>
            <h1 style={{margin:0, fontSize:'1.25rem', fontWeight:600, color:'#1a1a1a'}}>
              Договор № {credit.id}
            </h1>
            <div style={{color:'#737373', fontSize:'0.875rem', marginTop:4}}>
              {PRODUCT_TYPES[credit.product_type] || credit.product_type}
            </div>
          </div>
          <div style={{color: isOverdue ? '#b91c1c' : '#525252', fontWeight:500, fontSize:'0.875rem'}}>
            {STATUS_LABELS[credit.status] || credit.status}
          </div>
        </div>
      </div>

      {/* Info Sections */}
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', borderBottom:'1px solid #e5e5e5'}}>
        
        {/* Client */}
        <div style={{borderRight:'1px solid #e5e5e5'}}>
          <div style={{padding:'16px 40px', borderBottom:'1px solid #e5e5e5', background:'#fafafa'}}>
            <h2 style={{margin:0, fontSize:'0.8rem', fontWeight:500, color:'#525252', textTransform:'uppercase', letterSpacing:'0.5px'}}>Заёмщик</h2>
          </div>
          <div style={{padding:'20px 40px'}}>
            {client ? (
              <table style={{width:'100%', fontSize:'0.875rem'}}>
                <tbody>
                  <tr><td style={{color:'#737373', padding:'6px 0', width:'45%'}}>ФИО</td><td style={{color:'#1a1a1a'}}>{[client.last_name, client.first_name, client.middle_name].filter(Boolean).join(' ') || '—'}</td></tr>
                  <tr><td style={{color:'#737373', padding:'6px 0'}}>Телефон</td><td style={{color:'#1a1a1a'}}>{client.phone || '—'}</td></tr>
                  <tr><td style={{color:'#737373', padding:'6px 0'}}>Email</td><td style={{color:'#1a1a1a'}}>{client.email || '—'}</td></tr>
                  <tr><td style={{color:'#737373', padding:'6px 0'}}>Дата рождения</td><td style={{color:'#1a1a1a'}}>{formatDate(client.birth_date)}</td></tr>
                  <tr><td style={{color:'#737373', padding:'6px 0'}}>Адрес</td><td style={{color:'#1a1a1a'}}>{client.address || '—'}</td></tr>
                </tbody>
              </table>
            ) : (
              <div style={{color:'#737373'}}>Данные отсутствуют</div>
            )}
          </div>
        </div>

        {/* Credit Parameters */}
        <div>
          <div style={{padding:'16px 40px', borderBottom:'1px solid #e5e5e5', background:'#fafafa'}}>
            <h2 style={{margin:0, fontSize:'0.8rem', fontWeight:500, color:'#525252', textTransform:'uppercase', letterSpacing:'0.5px'}}>Параметры кредита</h2>
          </div>
          <div style={{padding:'20px 40px'}}>
            <table style={{width:'100%', fontSize:'0.875rem'}}>
              <tbody>
                <tr><td style={{color:'#737373', padding:'6px 0', width:'50%'}}>Сумма</td><td style={{color:'#1a1a1a', fontWeight:500}}>{formatCurrency(credit.principal_amount)}</td></tr>
                <tr><td style={{color:'#737373', padding:'6px 0'}}>Ставка</td><td style={{color:'#1a1a1a'}}>{credit.interest_rate}% годовых</td></tr>
                <tr><td style={{color:'#737373', padding:'6px 0'}}>Срок</td><td style={{color:'#1a1a1a'}}>{credit.term_months} мес.</td></tr>
                <tr><td style={{color:'#737373', padding:'6px 0'}}>Ежемесячный платёж</td><td style={{color:'#1a1a1a', fontWeight:500}}>{formatCurrency(credit.monthly_payment)}</td></tr>
                <tr><td style={{color:'#737373', padding:'6px 0'}}>Дата выдачи</td><td style={{color:'#1a1a1a'}}>{formatDate(credit.open_date)}</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Current State */}
      {latestState && (
        <div style={{borderBottom:'1px solid #e5e5e5'}}>
          <div style={{padding:'16px 40px', borderBottom:'1px solid #e5e5e5', background:'#fafafa'}}>
            <h2 style={{margin:0, fontSize:'0.8rem', fontWeight:500, color:'#525252', textTransform:'uppercase', letterSpacing:'0.5px'}}>
              Текущее состояние
              {latestState.report_date && <span style={{fontWeight:400, marginLeft:8}}>на {formatDate(latestState.report_date)}</span>}
            </h2>
          </div>
          <div style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)'}}>
            <div style={{padding:'24px 40px', borderRight:'1px solid #e5e5e5'}}>
              <div style={{color:'#737373', fontSize:'0.75rem', textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:4}}>Остаток долга</div>
              <div style={{fontSize:'1.25rem', fontWeight:600, color:'#1a1a1a'}}>{formatCurrency(latestState.current_balance)}</div>
            </div>
            <div style={{padding:'24px 40px', borderRight:'1px solid #e5e5e5'}}>
              <div style={{color:'#737373', fontSize:'0.75rem', textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:4}}>Просрочка</div>
              <div style={{fontSize:'1.25rem', fontWeight:600, color: latestState.overdue_amount > 0 ? '#b91c1c' : '#1a1a1a'}}>{formatCurrency(latestState.overdue_amount)}</div>
            </div>
            <div style={{padding:'24px 40px', borderRight:'1px solid #e5e5e5'}}>
              <div style={{color:'#737373', fontSize:'0.75rem', textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:4}}>Дней просрочки</div>
              <div style={{fontSize:'1.25rem', fontWeight:600, color: latestState.days_past_due > 0 ? '#b91c1c' : '#1a1a1a'}}>{latestState.days_past_due ?? 0}</div>
            </div>
            <div style={{padding:'24px 40px'}}>
              <div style={{color:'#737373', fontSize:'0.75rem', textTransform:'uppercase', letterSpacing:'0.5px', marginBottom:4}}>Bucket</div>
              <div style={{fontSize:'1.25rem', fontWeight:600, color:'#1a1a1a'}}>{latestState.bucket || '0'}</div>
            </div>
          </div>
        </div>
      )}

      {/* Interactions */}
      <div style={{borderBottom:'1px solid #e5e5e5'}}>
        <div style={{padding:'16px 40px', borderBottom:'1px solid #e5e5e5', background:'#fafafa'}}>
          <h2 style={{margin:0, fontSize:'0.8rem', fontWeight:500, color:'#525252', textTransform:'uppercase', letterSpacing:'0.5px'}}>Взаимодействия ({interactions.length})</h2>
        </div>
        {interactions.length > 0 ? (
          <table style={{width:'100%', borderCollapse:'collapse', fontSize:'0.875rem'}}>
            <thead>
              <tr style={{background:'#fafafa'}}>
                <th style={{textAlign:'left', padding:'10px 40px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Дата</th>
                <th style={{textAlign:'left', padding:'10px 20px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Тип</th>
                <th style={{textAlign:'left', padding:'10px 20px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Результат</th>
                <th style={{textAlign:'left', padding:'10px 40px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Комментарий</th>
              </tr>
            </thead>
            <tbody>
              {interactions.slice(0, 10).map((item, idx) => (
                <tr key={idx} style={{borderBottom:'1px solid #e5e5e5'}}>
                  <td style={{padding:'10px 40px', color:'#1a1a1a'}}>{formatDate(item.interaction_date)}</td>
                  <td style={{padding:'10px 20px', color:'#1a1a1a'}}>{item.interaction_type}</td>
                  <td style={{padding:'10px 20px', color:'#1a1a1a'}}>{item.result}</td>
                  <td style={{padding:'10px 40px', color:'#737373'}}>{item.notes || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{padding:'40px', textAlign:'center', color:'#737373'}}>Нет записей</div>
        )}
      </div>

      {/* Payments */}
      <div style={{borderBottom:'1px solid #e5e5e5'}}>
        <div style={{padding:'16px 40px', borderBottom:'1px solid #e5e5e5', background:'#fafafa'}}>
          <h2 style={{margin:0, fontSize:'0.8rem', fontWeight:500, color:'#525252', textTransform:'uppercase', letterSpacing:'0.5px'}}>Платежи ({payments.length})</h2>
        </div>
        {payments.length > 0 ? (
          <table style={{width:'100%', borderCollapse:'collapse', fontSize:'0.875rem'}}>
            <thead>
              <tr style={{background:'#fafafa'}}>
                <th style={{textAlign:'left', padding:'10px 40px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Дата</th>
                <th style={{textAlign:'right', padding:'10px 20px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Сумма</th>
                <th style={{textAlign:'left', padding:'10px 20px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Тип</th>
                <th style={{textAlign:'left', padding:'10px 40px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Статус</th>
              </tr>
            </thead>
            <tbody>
              {payments.slice(0, 15).map((item, idx) => (
                <tr key={idx} style={{borderBottom:'1px solid #e5e5e5'}}>
                  <td style={{padding:'10px 40px', color:'#1a1a1a'}}>{formatDate(item.payment_date)}</td>
                  <td style={{padding:'10px 20px', textAlign:'right', color:'#1a1a1a', fontWeight:500}}>{formatCurrency(item.amount)}</td>
                  <td style={{padding:'10px 20px', color:'#525252'}}>{item.payment_type}</td>
                  <td style={{padding:'10px 40px', color:'#525252'}}>{item.status === 'completed' ? 'Исполнен' : item.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{padding:'40px', textAlign:'center', color:'#737373'}}>Нет платежей</div>
        )}
      </div>

      {/* Credit States */}
      <div>
        <div style={{padding:'16px 40px', borderBottom:'1px solid #e5e5e5', background:'#fafafa'}}>
          <h2 style={{margin:0, fontSize:'0.8rem', fontWeight:500, color:'#525252', textTransform:'uppercase', letterSpacing:'0.5px'}}>История состояний ({creditStates.length})</h2>
        </div>
        {creditStates.length > 0 ? (
          <table style={{width:'100%', borderCollapse:'collapse', fontSize:'0.875rem'}}>
            <thead>
              <tr style={{background:'#fafafa'}}>
                <th style={{textAlign:'left', padding:'10px 40px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Дата</th>
                <th style={{textAlign:'right', padding:'10px 20px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Остаток</th>
                <th style={{textAlign:'right', padding:'10px 20px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Просрочка</th>
                <th style={{textAlign:'center', padding:'10px 20px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>DPD</th>
                <th style={{textAlign:'center', padding:'10px 40px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Bucket</th>
              </tr>
            </thead>
            <tbody>
              {creditStates.slice(0, 15).map((item, idx) => (
                <tr key={idx} style={{borderBottom:'1px solid #e5e5e5'}}>
                  <td style={{padding:'10px 40px', color:'#1a1a1a'}}>{formatDate(item.report_date)}</td>
                  <td style={{padding:'10px 20px', textAlign:'right', color:'#1a1a1a'}}>{formatCurrency(item.current_balance)}</td>
                  <td style={{padding:'10px 20px', textAlign:'right', color: item.overdue_amount > 0 ? '#b91c1c' : '#1a1a1a'}}>
                    {formatCurrency(item.overdue_amount)}
                  </td>
                  <td style={{padding:'10px 20px', textAlign:'center', color: item.days_past_due > 0 ? '#b91c1c' : '#1a1a1a'}}>
                    {item.days_past_due ?? 0}
                  </td>
                  <td style={{padding:'10px 40px', textAlign:'center', color:'#1a1a1a'}}>{item.bucket || '0'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{padding:'40px', textAlign:'center', color:'#737373'}}>Нет данных</div>
        )}
      </div>

    </div>
  );
}
