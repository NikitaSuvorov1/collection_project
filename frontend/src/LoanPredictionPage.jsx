import React, { useState, useEffect } from 'react';

const API_URL = 'http://127.0.0.1:8000/api';

export default function LoanPredictionPage() {
  const [formData, setFormData] = useState({
    gender: 'M',
    marital_status: 'single',
    employment: 'employed',
    income: 100000,
    monthly_expenses: 30000,
    loan_amount: 500000,
    loan_term: 36,
    children_count: 0,
    credit_history: 1,
    region: 'Москва'
  });

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [applications, setApplications] = useState([]);
  const [loadingApps, setLoadingApps] = useState(true);

  // Загрузка всех заявок при монтировании
  useEffect(() => {
    fetchApplications();
  }, []);

  const fetchApplications = async () => {
    try {
      setLoadingApps(true);
      const response = await fetch(`${API_URL}/applications/`);
      if (response.ok) {
        const data = await response.json();
        setApplications(data);
      }
    } catch (err) {
      console.error('Ошибка загрузки заявок:', err);
    } finally {
      setLoadingApps(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? Number(value) : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_URL}/applications/predict_approval/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        throw new Error(`Ошибка сервера: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatPercent = (value) => {
    return (value * 100).toFixed(1) + '%';
  };

  const getDecisionColor = (decision) => {
    return decision === 'approved' ? '#22c55e' : '#ef4444';
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return '#22c55e';
    if (confidence >= 0.6) return '#eab308';
    return '#ef4444';
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>🏦 Прогноз одобрения кредита</h1>
      <p style={styles.subtitle}>
        Заполните данные заявки для получения прогноза вероятности одобрения
      </p>

      <div style={styles.content}>
        <form onSubmit={handleSubmit} style={styles.form}>
          <h2 style={styles.sectionTitle}>👤 Данные заявителя</h2>
          
          <div style={styles.row}>
            <div style={styles.field}>
              <label style={styles.label}>Пол</label>
              <select name="gender" value={formData.gender} onChange={handleChange} style={styles.select}>
                <option value="M">Мужской</option>
                <option value="F">Женский</option>
              </select>
            </div>

            <div style={styles.field}>
              <label style={styles.label}>Семейное положение</label>
              <select name="marital_status" value={formData.marital_status} onChange={handleChange} style={styles.select}>
                <option value="single">Холост/Не замужем</option>
                <option value="married">Женат/Замужем</option>
                <option value="divorced">Разведён(а)</option>
                <option value="widowed">Вдовец/Вдова</option>
              </select>
            </div>
          </div>

          <div style={styles.row}>
            <div style={styles.field}>
              <label style={styles.label}>Занятость</label>
              <select name="employment" value={formData.employment} onChange={handleChange} style={styles.select}>
                <option value="employed">Работает</option>
                <option value="self_employed">Самозанятый</option>
                <option value="unemployed">Безработный</option>
                <option value="retired">Пенсионер</option>
                <option value="student">Студент</option>
              </select>
            </div>

            <div style={styles.field}>
              <label style={styles.label}>Количество детей</label>
              <input
                type="number"
                name="children_count"
                value={formData.children_count}
                onChange={handleChange}
                min="0"
                max="10"
                style={styles.input}
              />
            </div>
          </div>

          <div style={styles.row}>
            <div style={styles.field}>
              <label style={styles.label}>Ежемесячный доход (₽)</label>
              <input
                type="number"
                name="income"
                value={formData.income}
                onChange={handleChange}
                min="0"
                step="1000"
                style={styles.input}
              />
            </div>

            <div style={styles.field}>
              <label style={styles.label}>Ежемесячные расходы (₽)</label>
              <input
                type="number"
                name="monthly_expenses"
                value={formData.monthly_expenses}
                onChange={handleChange}
                min="0"
                step="1000"
                style={styles.input}
              />
            </div>
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Регион</label>
            <input
              type="text"
              name="region"
              value={formData.region}
              onChange={handleChange}
              placeholder="Например: Москва"
              style={styles.input}
            />
          </div>

          <h2 style={styles.sectionTitle}>💳 Параметры кредита</h2>

          <div style={styles.row}>
            <div style={styles.field}>
              <label style={styles.label}>Сумма кредита (₽)</label>
              <input
                type="number"
                name="loan_amount"
                value={formData.loan_amount}
                onChange={handleChange}
                min="10000"
                step="10000"
                style={styles.input}
              />
            </div>

            <div style={styles.field}>
              <label style={styles.label}>Срок кредита (месяцев)</label>
              <select name="loan_term" value={formData.loan_term} onChange={handleChange} style={styles.select}>
                <option value={6}>6 месяцев</option>
                <option value={12}>12 месяцев</option>
                <option value={24}>24 месяца</option>
                <option value={36}>36 месяцев</option>
                <option value={48}>48 месяцев</option>
                <option value={60}>60 месяцев</option>
              </select>
            </div>
          </div>

          <div style={styles.field}>
            <label style={styles.label}>Кредитная история</label>
            <select name="credit_history" value={formData.credit_history} onChange={handleChange} style={styles.select}>
              <option value={1}>✅ Хорошая (нет просрочек)</option>
              <option value={0}>❌ Плохая (были просрочки)</option>
            </select>
          </div>

          <button type="submit" disabled={loading} style={styles.button}>
            {loading ? '⏳ Анализ...' : '🔮 Получить прогноз'}
          </button>
        </form>

        <div style={styles.resultPanel}>
          <h2 style={styles.sectionTitle}>📊 Результат прогноза</h2>
          
          {error && (
            <div style={styles.error}>
              ❌ {error}
            </div>
          )}

          {!result && !error && !loading && (
            <div style={styles.placeholder}>
              <span style={styles.placeholderIcon}>📝</span>
              <p>Заполните форму и нажмите "Получить прогноз"</p>
            </div>
          )}

          {loading && (
            <div style={styles.placeholder}>
              <span style={styles.placeholderIcon}>⏳</span>
              <p>Анализируем данные...</p>
            </div>
          )}

          {result && (
            <div style={styles.resultContent}>
              <div style={{
                ...styles.decisionBadge,
                backgroundColor: getDecisionColor(result.decision)
              }}>
                {result.decision === 'approved' ? '✅ ОДОБРЕНО' : '❌ ОТКАЗАНО'}
              </div>

              <div style={styles.probabilitySection}>
                <div style={styles.probabilityLabel}>Вероятность одобрения</div>
                <div style={styles.probabilityValue}>
                  {formatPercent(result.approved_probability)}
                </div>
                <div style={styles.progressBar}>
                  <div 
                    style={{
                      ...styles.progressFill,
                      width: `${result.approved_probability * 100}%`,
                      backgroundColor: getDecisionColor(result.decision)
                    }}
                  />
                </div>
              </div>

              <div style={styles.confidenceSection}>
                <span style={styles.confidenceLabel}>Уверенность модели:</span>
                <span style={{
                  ...styles.confidenceValue,
                  color: getConfidenceColor(result.confidence)
                }}>
                  {formatPercent(result.confidence)}
                </span>
              </div>

              {result.risk_factors && result.risk_factors.length > 0 && (
                <div style={styles.riskSection}>
                  <h3 style={styles.riskTitle}>⚠️ Факторы риска</h3>
                  <ul style={styles.riskList}>
                    {result.risk_factors.map((factor, index) => (
                      <li key={index} style={styles.riskItem}>{factor}</li>
                    ))}
                  </ul>
                </div>
              )}

              {result.risk_factors && result.risk_factors.length === 0 && (
                <div style={styles.noRiskSection}>
                  <span>✅ Факторы риска не выявлены</span>
                </div>
              )}

              <div style={styles.infoSection}>
                <h3 style={styles.infoTitle}>ℹ️ Расчётные показатели</h3>
                <div style={styles.infoGrid}>
                  <div style={styles.infoItem}>
                    <span style={styles.infoLabel}>Ежемесячный платёж:</span>
                    <span style={styles.infoValue}>
                      {Math.round(formData.loan_amount / formData.loan_term).toLocaleString('ru-RU')} ₽
                    </span>
                  </div>
                  <div style={styles.infoItem}>
                    <span style={styles.infoLabel}>Долговая нагрузка (DTI):</span>
                    <span style={styles.infoValue}>
                      {formData.income > 0 
                        ? formatPercent((formData.loan_amount / formData.loan_term + formData.monthly_expenses) / formData.income)
                        : 'N/A'
                      }
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Таблица всех заявок */}
      <div style={styles.applicationsSection}>
        <h2 style={styles.sectionTitle}>📋 История заявок на кредит</h2>
        
        {loadingApps ? (
          <div style={styles.loadingApps}>Загрузка заявок...</div>
        ) : applications.length === 0 ? (
          <div style={styles.noApps}>Заявок пока нет</div>
        ) : (
          <div style={styles.tableWrapper}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>ID</th>
                  <th style={styles.th}>Клиент</th>
                  <th style={styles.th}>Сумма</th>
                  <th style={styles.th}>Срок</th>
                  <th style={styles.th}>Вероятность одобрения</th>
                  <th style={styles.th}>Риск просрочки</th>
                  <th style={styles.th}>Решение</th>
                  <th style={styles.th}>Дата</th>
                </tr>
              </thead>
              <tbody>
                {applications.map(app => (
                  <tr key={app.id} style={styles.tr}>
                    <td style={styles.td}>#{app.id}</td>
                    <td style={styles.td}>{app.client_name || `Клиент #${app.client}`}</td>
                    <td style={styles.td}>{Number(app.amount).toLocaleString('ru-RU')} ₽</td>
                    <td style={styles.td}>{app.requested_term} мес.</td>
                    <td style={styles.td}>
                      {app.approved_probability !== null ? (
                        <span style={{
                          ...styles.probabilityBadge,
                          backgroundColor: app.approved_probability >= 0.5 ? '#166534' : '#991b1b'
                        }}>
                          {(app.approved_probability * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span style={styles.noPrediction}>—</span>
                      )}
                    </td>
                    <td style={styles.td}>
                      {app.overdue_risk_probability !== null ? (
                        <span style={{
                          ...styles.riskBadge,
                          backgroundColor: app.overdue_risk_probability >= 0.5 ? '#991b1b' : '#166534'
                        }}>
                          {(app.overdue_risk_probability * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span style={styles.noPrediction}>—</span>
                      )}
                    </td>
                    <td style={styles.td}>
                      <span style={{
                        ...styles.decisionBadgeSmall,
                        backgroundColor: app.decision === 'approved' ? '#166534' : 
                                        app.decision === 'rejected' ? '#991b1b' : '#475569'
                      }}>
                        {app.decision_display || app.decision}
                      </span>
                    </td>
                    <td style={styles.td}>
                      {app.created_at ? new Date(app.created_at).toLocaleDateString('ru-RU') : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
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
    marginBottom: '2rem',
  },
  content: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '2rem',
    maxWidth: '1200px',
    margin: '0 auto',
  },
  form: {
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    padding: '1.5rem',
  },
  sectionTitle: {
    fontSize: '1.25rem',
    fontWeight: '600',
    marginBottom: '1rem',
    paddingBottom: '0.5rem',
    borderBottom: '1px solid #334155',
  },
  row: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '1rem',
  },
  field: {
    marginBottom: '1rem',
  },
  label: {
    display: 'block',
    fontSize: '0.875rem',
    color: '#94a3b8',
    marginBottom: '0.5rem',
  },
  input: {
    width: '100%',
    padding: '0.75rem',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: '#e2e8f0',
    fontSize: '1rem',
    boxSizing: 'border-box',
  },
  select: {
    width: '100%',
    padding: '0.75rem',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: '#e2e8f0',
    fontSize: '1rem',
    boxSizing: 'border-box',
  },
  button: {
    width: '100%',
    padding: '1rem',
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '1.1rem',
    fontWeight: '600',
    cursor: 'pointer',
    marginTop: '1rem',
    transition: 'background-color 0.2s',
  },
  resultPanel: {
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    padding: '1.5rem',
  },
  placeholder: {
    textAlign: 'center',
    padding: '3rem',
    color: '#64748b',
  },
  placeholderIcon: {
    fontSize: '4rem',
    display: 'block',
    marginBottom: '1rem',
  },
  error: {
    backgroundColor: '#7f1d1d',
    color: '#fecaca',
    padding: '1rem',
    borderRadius: '8px',
    marginBottom: '1rem',
  },
  resultContent: {
    animation: 'fadeIn 0.3s ease-in-out',
  },
  decisionBadge: {
    textAlign: 'center',
    padding: '1rem',
    borderRadius: '8px',
    fontSize: '1.5rem',
    fontWeight: 'bold',
    marginBottom: '1.5rem',
  },
  probabilitySection: {
    textAlign: 'center',
    marginBottom: '1.5rem',
  },
  probabilityLabel: {
    color: '#94a3b8',
    marginBottom: '0.5rem',
  },
  probabilityValue: {
    fontSize: '3rem',
    fontWeight: 'bold',
    marginBottom: '0.5rem',
  },
  progressBar: {
    height: '8px',
    backgroundColor: '#334155',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    transition: 'width 0.5s ease-in-out',
  },
  confidenceSection: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '0.5rem',
    marginBottom: '1.5rem',
    padding: '0.75rem',
    backgroundColor: '#0f172a',
    borderRadius: '8px',
  },
  confidenceLabel: {
    color: '#94a3b8',
  },
  confidenceValue: {
    fontWeight: 'bold',
    fontSize: '1.1rem',
  },
  riskSection: {
    backgroundColor: '#7f1d1d22',
    border: '1px solid #7f1d1d',
    borderRadius: '8px',
    padding: '1rem',
    marginBottom: '1rem',
  },
  riskTitle: {
    fontSize: '1rem',
    marginBottom: '0.5rem',
    color: '#fca5a5',
  },
  riskList: {
    margin: 0,
    paddingLeft: '1.5rem',
  },
  riskItem: {
    color: '#fecaca',
    marginBottom: '0.25rem',
  },
  noRiskSection: {
    backgroundColor: '#14532d22',
    border: '1px solid #14532d',
    borderRadius: '8px',
    padding: '1rem',
    marginBottom: '1rem',
    color: '#86efac',
  },
  infoSection: {
    backgroundColor: '#0f172a',
    borderRadius: '8px',
    padding: '1rem',
  },
  infoTitle: {
    fontSize: '0.875rem',
    color: '#94a3b8',
    marginBottom: '0.75rem',
  },
  infoGrid: {
    display: 'grid',
    gap: '0.5rem',
  },
  infoItem: {
    display: 'flex',
    justifyContent: 'space-between',
  },
  infoLabel: {
    color: '#64748b',
  },
  infoValue: {
    fontWeight: '600',
  },
  // Стили для таблицы заявок
  applicationsSection: {
    maxWidth: '1200px',
    margin: '2rem auto 0',
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    padding: '1.5rem',
  },
  loadingApps: {
    textAlign: 'center',
    padding: '2rem',
    color: '#64748b',
  },
  noApps: {
    textAlign: 'center',
    padding: '2rem',
    color: '#64748b',
  },
  tableWrapper: {
    overflowX: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.9rem',
  },
  th: {
    textAlign: 'left',
    padding: '0.75rem 1rem',
    backgroundColor: '#0f172a',
    color: '#94a3b8',
    fontWeight: '600',
    borderBottom: '2px solid #334155',
  },
  tr: {
    borderBottom: '1px solid #334155',
  },
  td: {
    padding: '0.75rem 1rem',
    verticalAlign: 'middle',
  },
  probabilityBadge: {
    padding: '0.25rem 0.5rem',
    borderRadius: '4px',
    color: 'white',
    fontWeight: '600',
    fontSize: '0.85rem',
  },
  riskBadge: {
    padding: '0.25rem 0.5rem',
    borderRadius: '4px',
    color: 'white',
    fontWeight: '600',
    fontSize: '0.85rem',
  },
  decisionBadgeSmall: {
    padding: '0.25rem 0.5rem',
    borderRadius: '4px',
    color: 'white',
    fontWeight: '500',
    fontSize: '0.8rem',
  },
  noPrediction: {
    color: '#64748b',
  },
};
