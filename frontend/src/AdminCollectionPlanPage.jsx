import React, { useEffect, useMemo, useState } from 'react';

const API_URL = 'http://127.0.0.1:8000/api';

function formatMoney(value) {
  return Number(value || 0).toLocaleString('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0,
  });
}

function shortName(name) {
  const parts = String(name || '').trim().split(/\s+/);
  if (parts.length < 3) return name || '—';
  return `${parts[0]} ${parts[1][0]}.${parts[2][0]}.`;
}

function maskPhone(phone) {
  return String(phone || '').replace(/(\+7\s*\(\d{3}\)\s*)\d{3}-(\d{2})-(\d{2})/, '$1***-$2-$3');
}

function AdminOnlyNotice() {
  return (
    <div className="admin-plan-page">
      <div className="admin-plan-access-denied">
        <div className="admin-plan-lock">ИС</div>
        <div>
          <h1>Доступ ограничен</h1>
          <p>План взыскания доступен только пользователям с ролью администратора.</p>
        </div>
      </div>
    </div>
  );
}

export default function AdminCollectionPlanPage({ user }) {
  const isAdmin = user?.role === 'admin';
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(isAdmin);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isAdmin) return;

    let cancelled = false;
    async function loadPlan() {
      setLoading(true);
      setError('');
      try {
        const response = await fetch(`${API_URL}/assignments/`);
        if (!response.ok) throw new Error(`Ошибка загрузки: ${response.status}`);
        const data = await response.json();
        const list = data.results || data.value || data || [];
        if (!cancelled) {
          setAssignments(Array.isArray(list) ? list : []);
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Не удалось загрузить план взыскания');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadPlan();
    return () => {
      cancelled = true;
    };
  }, [isAdmin]);

  const summary = useMemo(() => {
    const valid = assignments.filter(item => Number(item.overdue_amount || 0) > 0);
    const totalDebt = valid.reduce((sum, item) => sum + Number(item.overdue_amount || 0), 0);
    const avgDpd = valid.length
      ? Math.round(valid.reduce((sum, item) => sum + Number(item.overdue_days || 0), 0) / valid.length)
      : 0;

    return {
      valid,
      total: valid.length,
      operators: new Set(valid.map(item => item.operator)).size,
      highPriority: valid.filter(item => Number(item.priority) >= 5).length,
      totalDebt,
      avgDpd,
    };
  }, [assignments]);

  const priorityRows = useMemo(() => {
    return [...summary.valid]
      .sort((a, b) => Number(b.priority) - Number(a.priority) || Number(b.overdue_amount) - Number(a.overdue_amount))
      .slice(0, 18);
  }, [summary.valid]);

  if (!isAdmin) return <AdminOnlyNotice />;

  return (
    <div className="admin-plan-page">
      <div className="admin-plan-topbar">
        <div>
          <h1>План взыскания на текущий день</h1>
          <p>Административная сводка назначений для контроля работы ДРПЗ</p>
        </div>
        <div className="admin-plan-access">
          <span>Уровень доступа</span>
          <strong>Администратор</strong>
          <em>Доступ ограничен</em>
        </div>
      </div>

      <div className="admin-plan-meta">
        <span>Дата формирования: {new Date().toLocaleDateString('ru-RU')}</span>
        <span>Режим просмотра: только администратор</span>
        <span>Источник данных: реестр назначений</span>
      </div>

      {error && (
        <div className="admin-plan-error">
          {error}
        </div>
      )}

      <div className="admin-plan-summary">
        <div className="admin-plan-summary-item">
          <span>Всего назначений</span>
          <strong>{loading ? '—' : summary.total}</strong>
          <small>к обработке</small>
        </div>
        <div className="admin-plan-summary-item">
          <span>Сотрудников в плане</span>
          <strong>{loading ? '—' : summary.operators}</strong>
          <small>получили очередь</small>
        </div>
        <div className="admin-plan-summary-item">
          <span>Высокий приоритет</span>
          <strong className="danger">{loading ? '—' : summary.highPriority}</strong>
          <small>приоритет 5</small>
        </div>
        <div className="admin-plan-summary-item">
          <span>Сумма просрочки</span>
          <strong>{loading ? '—' : formatMoney(summary.totalDebt)}</strong>
          <small>по назначенным делам</small>
        </div>
        <div className="admin-plan-summary-item">
          <span>Средний срок</span>
          <strong>{loading ? '—' : `${summary.avgDpd} дн.`}</strong>
          <small>DPD</small>
        </div>
      </div>

      <section className="admin-plan-table-card">
        <div className="admin-plan-table-head">
          <strong>Реестр приоритетных назначений</strong>
          <span>первые 18 записей по приоритету и сумме просрочки</span>
        </div>
        <div className="admin-plan-table-wrap">
          <table className="admin-plan-table">
            <thead>
              <tr>
                <th>№</th>
                <th>Приоритет</th>
                <th>Клиент</th>
                <th>Телефон</th>
                <th className="num">Сумма просрочки</th>
                <th className="num">DPD</th>
                <th>Ответственный сотрудник</th>
                <th>Контроль</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="admin-plan-empty">Загрузка плана...</td>
                </tr>
              ) : priorityRows.length === 0 ? (
                <tr>
                  <td colSpan={8} className="admin-plan-empty">Нет назначений для отображения</td>
                </tr>
              ) : (
                priorityRows.map((item, index) => (
                  <tr key={item.id || `${item.credit}-${index}`}>
                    <td>{index + 1}</td>
                    <td><strong>{item.priority}</strong></td>
                    <td>
                      <strong>{item.client_name || item.debtor_name || '—'}</strong>
                      <span>Кредит #{item.credit}</span>
                    </td>
                    <td>{maskPhone(item.client_phone) || 'скрыт администратором'}</td>
                    <td className="num"><strong>{formatMoney(item.overdue_amount)}</strong></td>
                    <td className={`num ${Number(item.overdue_days) > 90 ? 'danger' : ''}`}>
                      <strong>{item.overdue_days}</strong>
                    </td>
                    <td>{shortName(item.operator_name)}</td>
                    <td><span className="admin-plan-status">Админ-контроль</span></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <div className="admin-plan-footer">
        <span>Документ сформирован автоматически на основании текущих назначений ИС.</span>
        <strong>Просмотр и изменение плана доступны только пользователям с ролью администратора.</strong>
      </div>
    </div>
  );
}
