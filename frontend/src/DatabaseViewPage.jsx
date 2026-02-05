import React, { useState, useEffect } from 'react';

const API_URL = 'http://127.0.0.1:8000/api';

// Моковые данные на случай если API недоступен
const MOCK_DATA = {
  clients: [
    { id: 1, full_name: 'Иванов Иван Иванович', gender: 'M', income: 85000, employment: 'employed', city: 'Москва' },
    { id: 2, full_name: 'Петрова Мария Сергеевна', gender: 'F', income: 120000, employment: 'self_employed', city: 'СПб' },
    { id: 3, full_name: 'Сидоров Пётр Николаевич', gender: 'M', income: 65000, employment: 'employed', city: 'Казань' },
  ],
  operators: [
    { id: 1, full_name: 'Оператор 1', role: 'operator', status: 'active', current_load: 15 },
    { id: 2, full_name: 'Оператор 2', role: 'senior', status: 'on_call', current_load: 8 },
  ],
  credits: [
    { id: 1, client: 1, principal_amount: 500000, status: 'active', product_type: 'consumer' },
    { id: 2, client: 2, principal_amount: 1200000, status: 'overdue', product_type: 'mortgage' },
  ],
  payments: [
    { id: 1, credit: 1, amount: 15000, payment_date: '2026-01-15' },
    { id: 2, credit: 1, amount: 15000, payment_date: '2026-02-15' },
  ],
  interventions: [
    { id: 1, credit: 1, intervention_type: 'call', result: 'promise', created_at: '2026-01-10' },
  ],
  applications: [
    { id: 1, amount: 300000, requested_term: 24, decision: 'pending', approved_probability: null },
  ],
};

export default function DatabaseViewPage() {
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [useMock, setUseMock] = useState(false);

  const entities = [
    { key: 'clients', name: 'Клиенты', endpoint: '/clients/', icon: '👤' },
    { key: 'operators', name: 'Операторы', endpoint: '/operators/', icon: '🎧' },
    { key: 'credits', name: 'Кредиты', endpoint: '/credits/', icon: '💳' },
    { key: 'payments', name: 'Платежи', endpoint: '/payments/', icon: '💰' },
    { key: 'interventions', name: 'Взаимодействия', endpoint: '/interventions/', icon: '📞' },
    { key: 'applications', name: 'Заявки на кредит', endpoint: '/applications/', icon: '📝' },
    { key: 'assignments', name: 'Назначения', endpoint: '/assignments/', icon: '📋' },
    { key: 'scoring', name: 'Результаты скоринга', endpoint: '/scorings/', icon: '📊' },
    { key: 'credit_states', name: 'Состояния кредитов', endpoint: '/credit-states/', icon: '📈' },
  ];

  useEffect(() => {
    fetchAllData();
  }, [useMock]);

  const fetchAllData = async () => {
    if (useMock) {
      setData(MOCK_DATA);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    const results = {};

    for (const entity of entities) {
      try {
        const response = await fetch(`${API_URL}${entity.endpoint}?limit=5`);
        if (response.ok) {
          let json = await response.json();
          // Handle paginated response
          if (json.results) {
            json = json.results;
          }
          // Take only first 5
          results[entity.key] = Array.isArray(json) ? json.slice(0, 5) : [];
        } else {
          results[entity.key] = [];
        }
      } catch (err) {
        console.error(`Error fetching ${entity.key}:`, err);
        results[entity.key] = [];
      }
    }

    setData(results);
    setLoading(false);
  };

  const renderValue = (value) => {
    if (value === null || value === undefined) return <span style={styles.null}>null</span>;
    if (typeof value === 'boolean') return value ? '✅' : '❌';
    if (typeof value === 'object') return JSON.stringify(value);
    if (typeof value === 'number' && value > 1000) return value.toLocaleString('ru-RU');
    return String(value);
  };

  const renderTable = (entityKey, items) => {
    if (!items || items.length === 0) {
      return <div style={styles.empty}>Нет данных</div>;
    }

    const columns = Object.keys(items[0]).slice(0, 8); // Ограничим колонки

    return (
      <div style={styles.tableWrapper}>
        <table style={styles.table}>
          <thead>
            <tr>
              {columns.map(col => (
                <th key={col} style={styles.th}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((item, idx) => (
              <tr key={idx} style={styles.tr}>
                {columns.map(col => (
                  <td key={col} style={styles.td}>{renderValue(item[col])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>🗄️ Просмотр базы данных</h1>
        <div style={styles.controls}>
          <button 
            onClick={() => setUseMock(!useMock)} 
            style={{...styles.btn, backgroundColor: useMock ? '#f59e0b' : '#3b82f6'}}
          >
            {useMock ? '📦 Мок данные' : '🔌 API данные'}
          </button>
          <button onClick={fetchAllData} style={styles.btn} disabled={loading}>
            {loading ? '⏳ Загрузка...' : '🔄 Обновить'}
          </button>
        </div>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      <div style={styles.grid}>
        {entities.map(entity => (
          <div key={entity.key} style={styles.card}>
            <div style={styles.cardHeader}>
              <span style={styles.cardIcon}>{entity.icon}</span>
              <span style={styles.cardTitle}>{entity.name}</span>
              <span style={styles.cardCount}>
                {data[entity.key]?.length || 0} записей
              </span>
            </div>
            {loading ? (
              <div style={styles.loading}>Загрузка...</div>
            ) : (
              renderTable(entity.key, data[entity.key])
            )}
          </div>
        ))}
      </div>

      <div style={styles.footer}>
        <p>Показаны первые 5 записей из каждой таблицы</p>
        <p style={styles.hint}>
          💡 Для работы API запустите: <code style={styles.code}>run_server.bat</code>
        </p>
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#0f172a',
    color: '#e2e8f0',
    padding: '1.5rem',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1.5rem',
    maxWidth: '1400px',
    margin: '0 auto 1.5rem',
  },
  title: {
    fontSize: '1.75rem',
    fontWeight: 'bold',
    margin: 0,
  },
  controls: {
    display: 'flex',
    gap: '0.75rem',
  },
  btn: {
    padding: '0.5rem 1rem',
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: '500',
    fontSize: '0.9rem',
  },
  error: {
    backgroundColor: '#7f1d1d',
    color: '#fecaca',
    padding: '1rem',
    borderRadius: '8px',
    marginBottom: '1rem',
    maxWidth: '1400px',
    margin: '0 auto 1rem',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(600px, 1fr))',
    gap: '1rem',
    maxWidth: '1400px',
    margin: '0 auto',
  },
  card: {
    backgroundColor: '#1e293b',
    borderRadius: '10px',
    overflow: 'hidden',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.75rem 1rem',
    backgroundColor: '#334155',
    borderBottom: '1px solid #475569',
  },
  cardIcon: {
    fontSize: '1.25rem',
  },
  cardTitle: {
    fontWeight: '600',
    flex: 1,
  },
  cardCount: {
    fontSize: '0.8rem',
    color: '#94a3b8',
    backgroundColor: '#0f172a',
    padding: '0.25rem 0.5rem',
    borderRadius: '4px',
  },
  loading: {
    padding: '2rem',
    textAlign: 'center',
    color: '#64748b',
  },
  empty: {
    padding: '2rem',
    textAlign: 'center',
    color: '#64748b',
    fontStyle: 'italic',
  },
  tableWrapper: {
    overflowX: 'auto',
    maxHeight: '300px',
    overflowY: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.8rem',
  },
  th: {
    textAlign: 'left',
    padding: '0.5rem 0.75rem',
    backgroundColor: '#0f172a',
    color: '#94a3b8',
    fontWeight: '600',
    position: 'sticky',
    top: 0,
    whiteSpace: 'nowrap',
  },
  tr: {
    borderBottom: '1px solid #334155',
  },
  td: {
    padding: '0.5rem 0.75rem',
    maxWidth: '200px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  null: {
    color: '#64748b',
    fontStyle: 'italic',
  },
  footer: {
    maxWidth: '1400px',
    margin: '1.5rem auto 0',
    textAlign: 'center',
    color: '#64748b',
    fontSize: '0.9rem',
  },
  hint: {
    marginTop: '0.5rem',
  },
  code: {
    backgroundColor: '#334155',
    padding: '0.2rem 0.5rem',
    borderRadius: '4px',
    fontFamily: 'monospace',
  },
};
