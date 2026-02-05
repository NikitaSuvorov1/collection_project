import React, { useMemo, useState, useEffect } from 'react';
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
  return Number(v).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' }); 
}

export default function CreditsPage({ onCreditClick }) {
  const [credits, setCredits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterStatus, setFilterStatus] = useState('all');

  useEffect(() => {
    fetchCredits();
  }, []);

  const fetchCredits = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/credits/`);
      if (!response.ok) throw new Error('Ошибка загрузки данных');
      const data = await response.json();
      setCredits(Array.isArray(data) ? data : data.results || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const visible = useMemo(() => {
    if (filterStatus === 'all') return credits;
    if (filterStatus === 'problem') {
      return credits.filter(c => ['overdue', 'default'].includes(c.status));
    }
    return credits.filter(c => c.status === filterStatus);
  }, [credits, filterStatus]);

  const stats = useMemo(() => {
    const total = credits.length;
    const activeCount = credits.filter(c => c.status === 'active').length;
    const overdueCount = credits.filter(c => ['overdue', 'default'].includes(c.status)).length;
    const totalAmount = credits.reduce((sum, c) => sum + Number(c.principal_amount || 0), 0);
    return { total, activeCount, overdueCount, totalAmount };
  }, [credits]);

  const isOverdue = (status) => ['overdue', 'default'].includes(status);

  return (
    <div style={{background:'#fff', minHeight:'100vh'}}>
      
      {/* Header */}
      <div style={{borderBottom:'1px solid #e5e5e5', padding:'20px 40px'}}>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <div>
            <h1 style={{margin:0, fontSize:'1.25rem', fontWeight:600, color:'#1a1a1a'}}>Реестр кредитных договоров</h1>
          </div>
          <button 
            onClick={fetchCredits} 
            disabled={loading}
            style={{
              background:'#fff', 
              border:'1px solid #d4d4d4', 
              padding:'8px 16px', 
              cursor:'pointer',
              color:'#404040',
              fontSize:'0.875rem',
            }}
          >
            {loading ? 'Загрузка...' : 'Обновить'}
          </button>
        </div>
      </div>

      {/* Statistics */}
      <div style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)', borderBottom:'1px solid #e5e5e5'}}>
        <div style={{padding:'24px 40px', borderRight:'1px solid #e5e5e5'}}>
          <div style={{color:'#737373', fontSize:'0.8rem', marginBottom:4, textTransform:'uppercase', letterSpacing:'0.5px'}}>Всего договоров</div>
          <div style={{fontSize:'1.5rem', fontWeight:600, color:'#1a1a1a'}}>{stats.total}</div>
        </div>
        <div style={{padding:'24px 40px', borderRight:'1px solid #e5e5e5'}}>
          <div style={{color:'#737373', fontSize:'0.8rem', marginBottom:4, textTransform:'uppercase', letterSpacing:'0.5px'}}>Действующих</div>
          <div style={{fontSize:'1.5rem', fontWeight:600, color:'#1a1a1a'}}>{stats.activeCount}</div>
        </div>
        <div style={{padding:'24px 40px', borderRight:'1px solid #e5e5e5'}}>
          <div style={{color:'#737373', fontSize:'0.8rem', marginBottom:4, textTransform:'uppercase', letterSpacing:'0.5px'}}>Проблемных</div>
          <div style={{fontSize:'1.5rem', fontWeight:600, color: stats.overdueCount > 0 ? '#b91c1c' : '#1a1a1a'}}>{stats.overdueCount}</div>
        </div>
        <div style={{padding:'24px 40px'}}>
          <div style={{color:'#737373', fontSize:'0.8rem', marginBottom:4, textTransform:'uppercase', letterSpacing:'0.5px'}}>Объём портфеля</div>
          <div style={{fontSize:'1.25rem', fontWeight:600, color:'#1a1a1a'}}>{formatCurrency(stats.totalAmount)}</div>
        </div>
      </div>

      {/* Filter */}
      <div style={{padding:'16px 40px', borderBottom:'1px solid #e5e5e5', display:'flex', alignItems:'center', gap:16, background:'#fafafa'}}>
        <label style={{color:'#525252', fontSize:'0.875rem'}}>Статус:</label>
        <select 
          value={filterStatus} 
          onChange={e => setFilterStatus(e.target.value)}
          style={{padding:'6px 12px', border:'1px solid #d4d4d4', fontSize:'0.875rem', color:'#1a1a1a', background:'#fff'}}
        >
          <option value="all">Все ({credits.length})</option>
          <option value="active">Действующие</option>
          <option value="overdue">Просроченные</option>
          <option value="default">Дефолт</option>
          <option value="problem">Проблемные</option>
          <option value="closed">Закрытые</option>
        </select>
        <span style={{marginLeft:'auto', color:'#737373', fontSize:'0.875rem'}}>
          Записей: {visible.length}
        </span>
      </div>

      {error && (
        <div style={{background:'#fef2f2', color:'#991b1b', padding:'12px 40px', borderBottom:'1px solid #e5e5e5'}}>
          {error}
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div style={{textAlign:'center', padding:60, color:'#737373'}}>Загрузка...</div>
      ) : (
        <table style={{width:'100%', borderCollapse:'collapse', fontSize:'0.875rem'}}>
          <thead>
            <tr style={{background:'#fafafa'}}>
              <th style={{textAlign:'left', padding:'12px 40px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>№</th>
              <th style={{textAlign:'left', padding:'12px 20px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Заёмщик</th>
              <th style={{textAlign:'left', padding:'12px 20px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Продукт</th>
              <th style={{textAlign:'right', padding:'12px 20px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Сумма</th>
              <th style={{textAlign:'right', padding:'12px 20px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Платёж</th>
              <th style={{textAlign:'center', padding:'12px 20px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Ставка</th>
              <th style={{textAlign:'left', padding:'12px 20px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Дата выдачи</th>
              <th style={{textAlign:'left', padding:'12px 40px', color:'#525252', fontWeight:500, borderBottom:'1px solid #e5e5e5'}}>Статус</th>
            </tr>
          </thead>
          <tbody>
            {visible.map(c => (
              <tr 
                key={c.id} 
                style={{borderBottom:'1px solid #e5e5e5', cursor:'pointer'}} 
                onClick={() => onCreditClick && onCreditClick(c.id)}
                onMouseEnter={e => e.currentTarget.style.background = '#fafafa'}
                onMouseLeave={e => e.currentTarget.style.background = '#fff'}
              >
                <td style={{padding:'14px 40px', color:'#1a1a1a'}}>{c.id}</td>
                <td style={{padding:'14px 20px', color:'#1a1a1a'}}>{c.client_name || `ID: ${c.client}`}</td>
                <td style={{padding:'14px 20px', color:'#525252'}}>{PRODUCT_TYPES[c.product_type] || c.product_type}</td>
                <td style={{padding:'14px 20px', textAlign:'right', color:'#1a1a1a', fontWeight:500}}>{formatCurrency(c.principal_amount)}</td>
                <td style={{padding:'14px 20px', textAlign:'right', color:'#525252'}}>{formatCurrency(c.monthly_payment)}</td>
                <td style={{padding:'14px 20px', textAlign:'center', color:'#525252'}}>{c.interest_rate}%</td>
                <td style={{padding:'14px 20px', color:'#525252'}}>{c.open_date ? new Date(c.open_date).toLocaleDateString('ru-RU') : '—'}</td>
                <td style={{padding:'14px 40px', color: isOverdue(c.status) ? '#b91c1c' : '#525252', fontWeight: isOverdue(c.status) ? 500 : 400}}>
                  {STATUS_LABELS[c.status] || c.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      
      {!loading && visible.length === 0 && (
        <div style={{textAlign:'center', padding:60, color:'#737373'}}>
          Нет записей
        </div>
      )}
    </div>
  );
}
