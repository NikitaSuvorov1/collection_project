import React, { useEffect, useState, useMemo } from "react";

const API_URL = 'http://127.0.0.1:8000/api';
const fmt = (v) => Number(v || 0).toLocaleString("ru-RU", { style: "currency", currency: "RUB" });
const fmtDur = (sec) => {
  if (!sec) return '0с';
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m > 0 ? `${m}м ${s}с` : `${s}с`;
};

const STATUS_LABELS = {
  promise: '🤝 Обещание',
  no_answer: '📵 Не дозвон',
  refuse: '❌ Отказ',
  completed: '✅ Завершено',
  callback: '🔄 Перезвонить',
};
const STATUS_COLORS = {
  promise: '#16a34a',
  no_answer: '#9ca3af',
  refuse: '#f85149',
  completed: '#2563eb',
  callback: '#d97706',
};

// Simple bar chart component
function MiniBar({ data, labelKey, valueKey, maxValue, color = '#3b82f6', height = 160 }) {
  const max = maxValue || Math.max(...data.map(d => d[valueKey]), 1);
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height, padding: '0 4px' }}>
      {data.map((d, i) => {
        const h = Math.max((d[valueKey] / max) * (height - 24), 2);
        return (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div style={{ fontSize: 10, color: '#8b949e', marginBottom: 2 }}>{d[valueKey] > 0 ? d[valueKey] : ''}</div>
            <div style={{ width: '100%', height: h, background: color, borderRadius: '3px 3px 0 0', minWidth: 8, transition: 'height 0.3s' }}
              title={`${d[labelKey]}: ${d[valueKey]}`} />
            <div style={{ fontSize: 9, color: '#484f58', marginTop: 2, whiteSpace: 'nowrap' }}>{d[labelKey]}</div>
          </div>
        );
      })}
    </div>
  );
}

// KPI Card
function KpiCard({ icon, label, value, sub, color = '#e6edf3' }) {
  return (
    <div style={{
      background: '#161b22', border: '1px solid #30363d', borderRadius: 10, padding: '14px 18px',
      flex: '1 1 180px', minWidth: 160,
    }}>
      <div style={{ fontSize: 12, color: '#8b949e', marginBottom: 4 }}>{icon} {label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color, lineHeight: 1.1 }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: '#484f58', marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

export default function OperatorStatsPage({ user, onBack }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [period, setPeriod] = useState('today'); // today | week | month

  useEffect(() => {
    if (!user?.id) return;
    setLoading(true);
    setError(null);
    fetch(`${API_URL}/dashboard/operator/${user.id}/`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(d => setData(d))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [user?.id]);

  const stats = useMemo(() => {
    if (!data) return null;
    if (period === 'today') return data.today;
    if (period === 'week') return data.week;
    return data.month;
  }, [data, period]);

  if (loading) return (
    <div style={{ padding: 40, textAlign: 'center' }}>
      <div style={{ fontSize: 48 }}>⏳</div>
      <div style={{ marginTop: 12, color: '#8b949e' }}>Загрузка статистики...</div>
    </div>
  );

  if (error) return (
    <div style={{ padding: 40, textAlign: 'center' }}>
      <div style={{ fontSize: 48 }}>⚠️</div>
      <div style={{ marginTop: 12, color: '#f85149' }}>Ошибка: {error}</div>
      <button className="btn" style={{ marginTop: 12 }} onClick={onBack}>← Назад</button>
    </div>
  );

  if (!data) return null;

  const periodLabels = { today: 'Сегодня', week: 'За неделю', month: 'За месяц' };

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '12px 20px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <button className="btn ghost" onClick={onBack} style={{ fontSize: 14 }}>← Назад</button>
          <div>
            <h2 style={{ margin: 0, fontSize: 22 }}>📊 Моя статистика</h2>
            <div style={{ fontSize: 13, color: '#8b949e', marginTop: 2 }}>
              {data.operator.name} • {data.operator.role} • {data.operator.specialization}
              {data.operator.hireDate && <span> • С {new Date(data.operator.hireDate).toLocaleDateString('ru-RU')}</span>}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {['today', 'week', 'month'].map(p => (
            <button key={p}
              className={`btn ${period === p ? '' : 'ghost'}`}
              onClick={() => setPeriod(p)}
              style={{ fontSize: 13 }}
            >{periodLabels[p]}</button>
          ))}
        </div>
      </div>

      {/* KPI Row */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
        <KpiCard icon="📞" label="Звонков" value={stats.calls} sub={`Всего воздействий: ${stats.total}`} />
        <KpiCard icon="📡" label="Контактность" value={`${stats.contactRate}%`}
          sub={`${stats.contacts} из ${stats.calls} дозвонов`}
          color={stats.contactRate >= 50 ? '#16a34a' : stats.contactRate >= 30 ? '#d97706' : '#f85149'} />
        <KpiCard icon="🤝" label="Обещаний (PTP)" value={stats.promises}
          sub={fmt(stats.promiseAmount)}
          color="#16a34a" />
        <KpiCard icon="⏱" label="Ср. длительность" value={fmtDur(stats.avgDuration)}
          sub={`Общее время: ${fmtDur(stats.totalDuration)}`} />
        <KpiCard icon="❌" label="Отказов" value={stats.refusals}
          sub={`Не дозвон: ${stats.noAnswer}`}
          color="#f85149" />
        <KpiCard icon="📋" label="В очереди" value={data.activeAssignments}
          sub="Активных назначений" />
      </div>

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, marginBottom: 20 }}>
        {/* Daily chart */}
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 10, padding: 16 }}>
          <h4 style={{ margin: '0 0 12px', fontSize: 14 }}>📈 Динамика звонков (30 дней)</h4>
          {data.daily.length > 0 ? (
            <MiniBar data={data.daily} labelKey="date" valueKey="calls" color="#3b82f6" height={160} />
          ) : (
            <div className="muted" style={{ textAlign: 'center', padding: 20 }}>Нет данных за период</div>
          )}
          {data.daily.length > 0 && (
            <div style={{ display: 'flex', gap: 16, marginTop: 12, fontSize: 12, color: '#8b949e', justifyContent: 'center' }}>
              <span>Макс: {Math.max(...data.daily.map(d => d.calls))} зв/день</span>
              <span>Средн: {Math.round(data.daily.reduce((s, d) => s + d.calls, 0) / data.daily.length)} зв/день</span>
            </div>
          )}
        </div>

        {/* Status distribution */}
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 10, padding: 16 }}>
          <h4 style={{ margin: '0 0 12px', fontSize: 14 }}>📊 Распределение статусов (месяц)</h4>
          {data.statusDistribution.length > 0 ? (
            <div>
              {data.statusDistribution.map((s, i) => {
                const total = data.statusDistribution.reduce((sum, x) => sum + x.count, 0);
                const pct = total > 0 ? Math.round(s.count / total * 100) : 0;
                return (
                  <div key={i} style={{ marginBottom: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 3 }}>
                      <span style={{ color: STATUS_COLORS[s.status] || '#6b7280' }}>
                        {STATUS_LABELS[s.status] || s.status}
                      </span>
                      <span style={{ fontWeight: 600 }}>{s.count} ({pct}%)</span>
                    </div>
                    <div style={{ height: 8, background: '#21262d', borderRadius: 4, overflow: 'hidden' }}>
                      <div style={{
                        width: `${pct}%`, height: '100%',
                        background: STATUS_COLORS[s.status] || '#9ca3af',
                        borderRadius: 4, transition: 'width 0.5s'
                      }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="muted" style={{ textAlign: 'center', padding: 20 }}>Нет данных</div>
          )}
        </div>
      </div>

      {/* Bottom row: hourly + top promises */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Hourly distribution */}
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 10, padding: 16 }}>
          <h4 style={{ margin: '0 0 12px', fontSize: 14 }}>🕐 Активность по часам (месяц)</h4>
          {data.hourly.length > 0 ? (
            <MiniBar data={data.hourly} labelKey="hour" valueKey="calls" color="#8b5cf6" height={120} />
          ) : (
            <div className="muted" style={{ textAlign: 'center', padding: 20 }}>Нет данных</div>
          )}
        </div>

        {/* Top promises */}
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 10, padding: 16 }}>
          <h4 style={{ margin: '0 0 12px', fontSize: 14 }}>💰 Крупнейшие обещания (месяц)</h4>
          {data.topPromises.length > 0 ? (
            <div style={{ maxHeight: 200, overflowY: 'auto' }}>
              {data.topPromises.map((p, i) => (
                <div key={p.id} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '6px 0', borderBottom: i < data.topPromises.length - 1 ? '1px solid #21262d' : 'none',
                  fontSize: 13,
                }}>
                  <div>
                    <div style={{ fontWeight: 500 }}>{p.client__full_name || `Клиент`}</div>
                    <div style={{ fontSize: 11, color: '#484f58' }}>
                      {p.datetime ? new Date(p.datetime).toLocaleDateString('ru-RU') : ''}
                      {p.promise_date && <span> → до {new Date(p.promise_date).toLocaleDateString('ru-RU')}</span>}
                    </div>
                  </div>
                  <div style={{ fontWeight: 700, color: '#16a34a', whiteSpace: 'nowrap' }}>{fmt(p.promise_amount)}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="muted" style={{ textAlign: 'center', padding: 20 }}>Нет обещаний за период</div>
          )}
        </div>
      </div>

      {/* All-time summary */}
      <div style={{
        marginTop: 20, background: '#1c2128', border: '1px solid #30363d', borderRadius: 10,
        padding: '12px 20px', display: 'flex', gap: 32, fontSize: 13, color: '#8b949e',
      }}>
        <span>📦 За всё время: <b>{data.allTime.totalInterventions}</b> воздействий</span>
        <span>💰 Собрано: <b>{fmt(data.allTime.totalCollected)}</b></span>
        <span>🎯 Успешность: <b>{Math.round(data.allTime.successRate * 100)}%</b></span>
      </div>
    </div>
  );
}
