import React, { useState, useEffect } from 'react';

const API_URL = 'http://127.0.0.1:8000/api';

const FEATURE_LABELS = {
  age: 'Возраст',
  gender: 'Пол',
  marital_status: 'Семейное положение',
  employment: 'Занятость',
  dependents: 'Иждивенцы',
  monthly_income: 'Ежемесячный доход',
  has_other_credits: 'Есть другие кредиты',
  other_credits_count: 'Кол-во других кредитов',
  credit_amount: 'Сумма кредита',
  credit_term: 'Срок (мес.)',
  interest_rate: 'Процентная ставка',
  lti_ratio: 'LTI (кредит/доход)',
  credit_age: 'Возраст кредита (дн.)',
  credit_status: 'Статус кредита',
  monthly_payment: 'Ежемесячный платёж',
  total_payments: 'Всего платежей',
  overdue_payments: 'Просроченных платежей',
  max_overdue_days: 'Макс. дней просрочки',
  avg_payment: 'Средний платёж',
  payments_count_12m: 'Платежей за 12 мес.',
  overdue_count_12m: 'Просрочек за 12 мес.',
  overdue_share_12m: 'Доля просрочек 12м',
  max_overdue_12m: 'Макс. просрочка 12м (дн.)',
  total_interventions: 'Всего взаимодействий',
  completed_interventions: 'Завершённых',
  promises_count: 'Обещаний оплатить',
};

const STATUS_MAP = { 0: 'Закрыт', 1: 'Активный', 2: 'Просрочен', 3: 'Дефолт', 4: 'Реструктуризация', 5: 'Судебный', 6: 'Продан', 7: 'Списан' };
const GENDER_MAP = { 1: 'Мужской', 0: 'Женский' };
const MARITAL_MAP = { 0: 'Холост', 1: 'Женат/Замужем', 2: 'Разведён(а)', 3: 'Вдовец/Вдова' };
const EMPL_MAP = { 0: 'Безработный', 1: 'Работает', 2: 'Самозанятый', 3: 'Пенсионер', 4: 'Студент' };

function formatFeatureValue(key, val) {
  if (val === undefined || val === null) return '—';
  if (key === 'gender') return GENDER_MAP[val] || val;
  if (key === 'marital_status') return MARITAL_MAP[val] || val;
  if (key === 'employment') return EMPL_MAP[val] || val;
  if (key === 'credit_status') return STATUS_MAP[val] || val;
  if (key === 'has_other_credits') return val ? 'Да' : 'Нет';
  if (key === 'overdue_share_12m') return (val * 100).toFixed(1) + '%';
  if (key === 'lti_ratio') return val.toFixed(2);
  if (['monthly_income', 'credit_amount', 'monthly_payment', 'avg_payment'].includes(key))
    return Number(val).toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' ₽';
  if (key === 'interest_rate') return val.toFixed(1) + '%';
  if (key === 'age') return val.toFixed(0) + ' лет';
  return typeof val === 'number' ? (Number.isInteger(val) ? val : val.toFixed(2)) : val;
}

function getRiskColor(category) {
  if (category === 0) return '#22c55e';
  if (category === 1) return '#eab308';
  return '#ef4444';
}

function getRiskBg(category) {
  if (category === 0) return '#14532d';
  if (category === 1) return '#713f12';
  return '#7f1d1d';
}

export default function OverduePredictionPage() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [topN, setTopN] = useState(30);
  const [selectedRow, setSelectedRow] = useState(null);
  const [features, setFeatures] = useState(null);
  const [loadingFeatures, setLoadingFeatures] = useState(false);

  // Загрузка пакетного прогноза
  const fetchBatchPrediction = async () => {
    setLoading(true);
    setError(null);
    setResults([]);
    setSelectedRow(null);
    setFeatures(null);
    try {
      const resp = await fetch(`${API_URL}/overdue-prediction/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ top: topN }),
      });
      if (!resp.ok) throw new Error(`Ошибка сервера: ${resp.status}`);
      const data = await resp.json();
      setResults(data.results || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Загрузка признаков конкретного кредита
  const fetchCreditFeatures = async (creditId) => {
    setLoadingFeatures(true);
    try {
      const resp = await fetch(`${API_URL}/overdue-prediction/?credit_id=${creditId}`);
      if (!resp.ok) throw new Error(`Ошибка: ${resp.status}`);
      const data = await resp.json();
      setFeatures(data.features || data);
    } catch (e) {
      console.error(e);
      setFeatures(null);
    } finally {
      setLoadingFeatures(false);
    }
  };

  const handleRowClick = (row) => {
    setSelectedRow(row);
    if (row.credit_id) fetchCreditFeatures(row.credit_id);
  };

  useEffect(() => {
    fetchBatchPrediction();
  }, []);

  return (
    <div style={s.container}>
      <h1 style={s.title}>⚠️ Прогноз выхода на просрочку</h1>
      <p style={s.subtitle}>
        Ранжирование кредитов по вероятности просрочки (от высокого риска к низкому)
      </p>

      {/* Управление */}
      <div style={s.controls}>
        <label style={s.controlLabel}>
          Кол-во кредитов:
          <select value={topN} onChange={e => setTopN(Number(e.target.value))} style={s.select}>
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={30}>30</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </label>
        <button onClick={fetchBatchPrediction} disabled={loading} style={s.btn}>
          {loading ? '⏳ Загрузка...' : '🔄 Обновить прогноз'}
        </button>
      </div>

      {error && <div style={s.error}>❌ {error}</div>}

      {/* Основной контент: таблица + панель деталей */}
      <div style={s.mainContent}>
        {/* Таблица ранжирования */}
        <div style={s.tablePanel}>
          <h2 style={s.sectionTitle}>📊 Ранжирование по риску ({results.length} кредитов)</h2>
          {loading ? (
            <div style={s.placeholder}>⏳ Загрузка прогнозов...</div>
          ) : results.length === 0 ? (
            <div style={s.placeholder}>Нет данных. Нажмите «Обновить прогноз».</div>
          ) : (
            <div style={s.tableWrap}>
              <table style={s.table}>
                <thead>
                  <tr>
                    <th style={s.th}>#</th>
                    <th style={s.th}>Клиент</th>
                    <th style={s.th}>Кредит ID</th>
                    <th style={s.th}>Риск</th>
                    <th style={s.th}>Категория</th>
                    <th style={s.th}>P(Низкий)</th>
                    <th style={s.th}>P(Средний)</th>
                    <th style={s.th}>P(Высокий)</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r, i) => (
                    <tr
                      key={r.credit_id || i}
                      style={{
                        ...s.tr,
                        backgroundColor: selectedRow?.credit_id === r.credit_id ? '#334155' : 'transparent',
                        cursor: 'pointer',
                      }}
                      onClick={() => handleRowClick(r)}
                    >
                      <td style={s.td}>{r.rank || i + 1}</td>
                      <td style={s.td}>{r.client_name || `#${r.client_id}`}</td>
                      <td style={s.td}>#{r.credit_id}</td>
                      <td style={s.td}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={s.scoreBarBg}>
                            <div style={{ ...s.scoreBarFill, width: `${(r.risk_score * 100)}%`, backgroundColor: getRiskColor(r.risk_category) }} />
                          </div>
                          <span style={{ fontWeight: 600, color: getRiskColor(r.risk_category), minWidth: 40 }}>
                            {(r.risk_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>
                      <td style={s.td}>
                        <span style={{ ...s.badge, backgroundColor: getRiskBg(r.risk_category), color: getRiskColor(r.risk_category) }}>
                          {r.risk_label}
                        </span>
                      </td>
                      <td style={{ ...s.td, color: '#22c55e' }}>{((r.probabilities?.['Низкий'] || 0) * 100).toFixed(1)}%</td>
                      <td style={{ ...s.td, color: '#eab308' }}>{((r.probabilities?.['Средний'] || 0) * 100).toFixed(1)}%</td>
                      <td style={{ ...s.td, color: '#ef4444' }}>{((r.probabilities?.['Высокий'] || 0) * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Панель деталей */}
        <div style={s.detailPanel}>
          <h2 style={s.sectionTitle}>🔍 Детали и признаки</h2>
          {!selectedRow ? (
            <div style={s.placeholder}>
              <span style={{ fontSize: '3rem', display: 'block', marginBottom: 12 }}>👈</span>
              Выберите строку в таблице для просмотра признаков
            </div>
          ) : loadingFeatures ? (
            <div style={s.placeholder}>⏳ Загрузка признаков...</div>
          ) : (
            <div>
              {/* Шапка: результат прогноза */}
              <div style={{ ...s.riskHeader, backgroundColor: getRiskBg(selectedRow.risk_category) }}>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, color: getRiskColor(selectedRow.risk_category) }}>
                  {selectedRow.risk_label} риск
                </div>
                <div style={{ fontSize: '0.9rem', color: '#cbd5e1', marginTop: 4 }}>
                  {selectedRow.client_name} • Кредит #{selectedRow.credit_id}
                </div>
                <div style={{ marginTop: 12, display: 'flex', gap: 16 }}>
                  <div style={s.probBox}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Низкий</div>
                    <div style={{ fontWeight: 700, color: '#22c55e' }}>
                      {((selectedRow.probabilities?.['Низкий'] || 0) * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div style={s.probBox}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Средний</div>
                    <div style={{ fontWeight: 700, color: '#eab308' }}>
                      {((selectedRow.probabilities?.['Средний'] || 0) * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div style={s.probBox}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Высокий</div>
                    <div style={{ fontWeight: 700, color: '#ef4444' }}>
                      {((selectedRow.probabilities?.['Высокий'] || 0) * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div style={s.probBox}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Risk Score</div>
                    <div style={{ fontWeight: 700, color: getRiskColor(selectedRow.risk_category) }}>
                      {(selectedRow.risk_score * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
              </div>

              {/* Табличка признаков */}
              <div style={{ marginTop: 16 }}>
                <h3 style={{ fontSize: '0.95rem', color: '#94a3b8', marginBottom: 8 }}>
                  📋 Признаки модели (26 входных параметров)
                </h3>
                <div style={s.featuresGrid}>
                  {Object.keys(FEATURE_LABELS).map(key => {
                    const val = features ? features[key] : undefined;
                    // Highlight risky features
                    let highlight = false;
                    if (key === 'max_overdue_days' && val > 30) highlight = true;
                    if (key === 'overdue_share_12m' && val > 0.3) highlight = true;
                    if (key === 'overdue_payments' && val > 3) highlight = true;
                    if (key === 'lti_ratio' && val > 4) highlight = true;
                    if (key === 'credit_status' && val >= 2) highlight = true;

                    return (
                      <div key={key} style={{ ...s.featureRow, backgroundColor: highlight ? '#7f1d1d22' : 'transparent' }}>
                        <span style={{ ...s.featureLabel, color: highlight ? '#fca5a5' : '#94a3b8' }}>
                          {FEATURE_LABELS[key]}
                        </span>
                        <span style={{ ...s.featureValue, color: highlight ? '#fca5a5' : '#e2e8f0' }}>
                          {formatFeatureValue(key, val)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Сводка по категориям */}
      {results.length > 0 && (
        <div style={s.summaryContainer}>
          <h2 style={s.sectionTitle}>📈 Сводка по категориям риска</h2>
          <div style={s.summaryGrid}>
            {[
              { cat: 0, label: 'Низкий риск', icon: '🟢' },
              { cat: 1, label: 'Средний риск', icon: '🟡' },
              { cat: 2, label: 'Высокий риск', icon: '🔴' },
            ].map(({ cat, label, icon }) => {
              const items = results.filter(r => r.risk_category === cat);
              const avgScore = items.length > 0
                ? items.reduce((s, r) => s + r.risk_score, 0) / items.length
                : 0;
              return (
                <div key={cat} style={{ ...s.summaryCard, borderColor: getRiskColor(cat) }}>
                  <div style={{ fontSize: '2rem' }}>{icon}</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{items.length}</div>
                  <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>{label}</div>
                  <div style={{ color: '#64748b', fontSize: '0.75rem', marginTop: 4 }}>
                    Ср. оценка: {(avgScore * 100).toFixed(1)}%
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

const s = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#0f172a',
    color: '#e2e8f0',
    padding: '2rem',
  },
  title: {
    fontSize: '2rem',
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: '0.5rem',
  },
  subtitle: {
    textAlign: 'center',
    color: '#94a3b8',
    marginBottom: '1.5rem',
  },
  controls: {
    maxWidth: 1400,
    margin: '0 auto 1.5rem',
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  },
  controlLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    color: '#94a3b8',
    fontSize: '0.9rem',
  },
  select: {
    padding: '0.5rem 0.75rem',
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 6,
    color: '#e2e8f0',
    fontSize: '0.9rem',
  },
  btn: {
    padding: '0.6rem 1.25rem',
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: 8,
    fontSize: '0.95rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  error: {
    maxWidth: 1400,
    margin: '0 auto 1rem',
    backgroundColor: '#7f1d1d',
    color: '#fecaca',
    padding: '0.75rem 1rem',
    borderRadius: 8,
  },
  mainContent: {
    maxWidth: 1400,
    margin: '0 auto',
    display: 'grid',
    gridTemplateColumns: '1fr 400px',
    gap: '1.5rem',
    alignItems: 'start',
  },
  tablePanel: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: '1.25rem',
    overflow: 'hidden',
  },
  detailPanel: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: '1.25rem',
    position: 'sticky',
    top: 16,
    maxHeight: 'calc(100vh - 32px)',
    overflowY: 'auto',
  },
  sectionTitle: {
    fontSize: '1.1rem',
    fontWeight: 600,
    marginBottom: '1rem',
    paddingBottom: '0.5rem',
    borderBottom: '1px solid #334155',
  },
  placeholder: {
    textAlign: 'center',
    padding: '2rem',
    color: '#64748b',
  },
  tableWrap: {
    overflowX: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.85rem',
  },
  th: {
    textAlign: 'left',
    padding: '0.6rem 0.75rem',
    backgroundColor: '#0f172a',
    color: '#94a3b8',
    fontWeight: 600,
    borderBottom: '2px solid #334155',
    whiteSpace: 'nowrap',
  },
  tr: {
    borderBottom: '1px solid #1e293b',
    transition: 'background-color 0.15s',
  },
  td: {
    padding: '0.55rem 0.75rem',
    verticalAlign: 'middle',
    whiteSpace: 'nowrap',
  },
  scoreBarBg: {
    height: 6,
    width: 60,
    backgroundColor: '#334155',
    borderRadius: 3,
    overflow: 'hidden',
  },
  scoreBarFill: {
    height: '100%',
    borderRadius: 3,
    transition: 'width 0.3s',
  },
  badge: {
    padding: '3px 10px',
    borderRadius: 4,
    fontWeight: 600,
    fontSize: '0.8rem',
    display: 'inline-block',
  },
  riskHeader: {
    borderRadius: 8,
    padding: '1rem',
    textAlign: 'center',
  },
  probBox: {
    flex: 1,
    textAlign: 'center',
    backgroundColor: '#0f172a',
    borderRadius: 6,
    padding: '6px 4px',
  },
  featuresGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
  },
  featureRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '4px 8px',
    borderRadius: 4,
    fontSize: '0.8rem',
  },
  featureLabel: {
    color: '#94a3b8',
  },
  featureValue: {
    fontWeight: 600,
    textAlign: 'right',
  },
  summaryContainer: {
    maxWidth: 1400,
    margin: '1.5rem auto 0',
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: '1.25rem',
  },
  summaryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 16,
  },
  summaryCard: {
    textAlign: 'center',
    padding: '1.25rem',
    backgroundColor: '#0f172a',
    borderRadius: 8,
    border: '1px solid #334155',
  },
};
