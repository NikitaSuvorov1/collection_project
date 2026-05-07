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
    <div style={{background:'var(--bg-body)', minHeight:'100vh'}}>
      
      {/* Header */}
      <div style={{borderBottom:'1px solid var(--border)', padding:'20px 40px'}}>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <div>
            <h1 style={{margin:0, fontSize:'1.25rem', fontWeight:600, color:'var(--text-primary)'}}>Реестр кредитных договоров</h1>
          </div>
          <button 
            onClick={fetchCredits} 
            disabled={loading}
            style={{
              background:'var(--bg-card)',
              border:'1px solid var(--border)',
              padding:'8px 16px',
              cursor:'pointer',
              color:'var(--text-secondary)',
              fontSize:'0.875rem',
            }}
          >
            {loading ? 'Загрузка...' : 'Обновить'}
          </button>
        </div>
      </div>

      {/* Statistics */}
      <div style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)', borderBottom:'1px solid var(--border)'}}>
        <div style={{padding:'24px 40px', borderRight:'1px solid var(--border)'}}>
          <div style={{color:'var(--text-secondary)', fontSize:'0.8rem', marginBottom:4, textTransform:'uppercase', letterSpacing:'0.5px'}}>Всего договоров</div>
          <div style={{fontSize:'1.5rem', fontWeight:600, color:'var(--text-primary)'}}>{stats.total}</div>
        </div>
        <div style={{padding:'24px 40px', borderRight:'1px solid var(--border)'}}>
          <div style={{color:'var(--text-secondary)', fontSize:'0.8rem', marginBottom:4, textTransform:'uppercase', letterSpacing:'0.5px'}}>Действующих</div>
          <div style={{fontSize:'1.5rem', fontWeight:600, color:'var(--text-primary)'}}>{stats.activeCount}</div>
        </div>
        <div style={{padding:'24px 40px', borderRight:'1px solid var(--border)'}}>
          <div style={{color:'var(--text-secondary)', fontSize:'0.8rem', marginBottom:4, textTransform:'uppercase', letterSpacing:'0.5px'}}>Проблемных</div>
          <div style={{fontSize:'1.5rem', fontWeight:600, color: stats.overdueCount > 0 ? 'var(--danger)' : 'var(--text-primary)'}}>{stats.overdueCount}</div>
        </div>
        <div style={{padding:'24px 40px'}}>
          <div style={{color:'var(--text-secondary)', fontSize:'0.8rem', marginBottom:4, textTransform:'uppercase', letterSpacing:'0.5px'}}>Объём портфеля</div>
          <div style={{fontSize:'1.25rem', fontWeight:600, color:'var(--text-primary)'}}>{formatCurrency(stats.totalAmount)}</div>
        </div>
      </div>

      {/* Filter */}
      <div style={{padding:'16px 40px', borderBottom:'1px solid var(--border)', display:'flex', alignItems:'center', gap:16, background:'var(--bg-surface)'}}>
        <label style={{color:'var(--text-secondary)', fontSize:'0.875rem'}}>Статус:</label>
        <select 
          value={filterStatus} 
          onChange={e => setFilterStatus(e.target.value)}
          style={{padding:'6px 12px', border:'1px solid var(--border)', fontSize:'0.875rem', color:'var(--text-primary)', background:'var(--bg-body)'}}
        >
          <option value="all">Все ({credits.length})</option>
          <option value="active">Действующие</option>
          <option value="overdue">Просроченные</option>
          <option value="default">Дефолт</option>
          <option value="problem">Проблемные</option>
          <option value="closed">Закрытые</option>
        </select>
        <span style={{marginLeft:'auto', color:'var(--text-secondary)', fontSize:'0.875rem'}}>
          Записей: {visible.length}
        </span>
      </div>

      {error && (
        <div style={{background:'rgba(248,81,73,0.15)', color:'var(--danger)', padding:'12px 40px', borderBottom:'1px solid var(--border)'}}>
          {error}
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div style={{textAlign:'center', padding:60, color:'var(--text-secondary)'}}>Загрузка...</div>
      ) : (
        <table style={{width:'100%', borderCollapse:'collapse', fontSize:'0.875rem'}}>
          <thead>
            <tr style={{background:'var(--bg-surface)'}}>
              <th style={{textAlign:'left', padding:'12px 40px', color:'var(--text-secondary)', fontWeight:500, borderBottom:'1px solid var(--border)'}}>№</th>
              <th style={{textAlign:'left', padding:'12px 20px', color:'var(--text-secondary)', fontWeight:500, borderBottom:'1px solid var(--border)'}}>Заёмщик</th>
              <th style={{textAlign:'left', padding:'12px 20px', color:'var(--text-secondary)', fontWeight:500, borderBottom:'1px solid var(--border)'}}>Продукт</th>
              <th style={{textAlign:'right', padding:'12px 20px', color:'var(--text-secondary)', fontWeight:500, borderBottom:'1px solid var(--border)'}}>Сумма</th>
              <th style={{textAlign:'right', padding:'12px 20px', color:'var(--text-secondary)', fontWeight:500, borderBottom:'1px solid var(--border)'}}>Платёж</th>
              <th style={{textAlign:'center', padding:'12px 20px', color:'var(--text-secondary)', fontWeight:500, borderBottom:'1px solid var(--border)'}}>Ставка</th>
              <th style={{textAlign:'left', padding:'12px 20px', color:'var(--text-secondary)', fontWeight:500, borderBottom:'1px solid var(--border)'}}>Дата выдачи</th>
              <th style={{textAlign:'left', padding:'12px 40px', color:'var(--text-secondary)', fontWeight:500, borderBottom:'1px solid var(--border)'}}>Статус</th>
            </tr>
          </thead>
          <tbody>
            {visible.map(c => (
              <tr
                key={c.id}
                style={{borderBottom:'1px solid var(--border)', cursor:'pointer'}}
                onClick={() => onCreditClick && onCreditClick(c.id)}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-surface)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <td style={{padding:'14px 40px', color:'var(--text-primary)'}}>{c.id}</td>
                <td style={{padding:'14px 20px', color:'var(--text-primary)'}}>{c.client_name || `ID: ${c.client}`}</td>
                <td style={{padding:'14px 20px', color:'var(--text-secondary)'}}>{PRODUCT_TYPES[c.product_type] || c.product_type}</td>
                <td style={{padding:'14px 20px', textAlign:'right', color:'var(--text-primary)', fontWeight:500}}>{formatCurrency(c.principal_amount)}</td>
                <td style={{padding:'14px 20px', textAlign:'right', color:'var(--text-secondary)'}}>{formatCurrency(c.monthly_payment)}</td>
                <td style={{padding:'14px 20px', textAlign:'center', color:'var(--text-secondary)'}}>{c.interest_rate}%</td>
                <td style={{padding:'14px 20px', color:'var(--text-secondary)'}}>{c.open_date ? new Date(c.open_date).toLocaleDateString('ru-RU') : '—'}</td>
                <td style={{padding:'14px 40px', color: isOverdue(c.status) ? 'var(--danger)' : 'var(--text-secondary)', fontWeight: isOverdue(c.status) ? 500 : 400}}>
                  {STATUS_LABELS[c.status] || c.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      
      {!loading && visible.length === 0 && (
        <div style={{textAlign:'center', padding:60, color:'var(--text-secondary)'}}>
          Нет записей
        </div>
      )}
    </div>
  );
}
