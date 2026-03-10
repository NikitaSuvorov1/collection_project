import React, { useState, useEffect, useRef } from 'react';
import LoginPage from './LoginPage';
import DashboardPage from './DashboardPage';

const API_BASE = 'http://localhost:8000/api';

// Call phases
const PHASE_IDLE = 'idle';           // До звонка — выбор клиента
const PHASE_CALLING = 'calling';     // Звонок идёт (таймер)
const PHASE_RESULT = 'result';       // Заполнение результата
const PHASE_SAVED = 'saved';         // Результат сохранён

// Status labels that match backend Intervention.STATUS_CHOICES
const RESULT_OPTIONS = [
  { value: 'no_answer', label: 'Не дозвонились', icon: '📵' },
  { value: 'callback',  label: 'Перезвонить позже', icon: '🔄' },
  { value: 'promise',   label: 'Обещание оплаты', icon: '🤝' },
  { value: 'refuse',    label: 'Отказ от оплаты', icon: '❌' },
  { value: 'completed', label: 'Вопрос решён / Оплачено', icon: '✅' },
];

const REFUSAL_REASONS = [
  'Нет финансовой возможности',
  'Не признаёт долг',
  'Не согласен с суммой',
  'Требует документы',
  'Нецензурная брань / агрессия',
  'Иная причина',
];

// ===== OPERATOR WORKSPACE COMPONENT =====
function OperatorWorkspace({ operator, onLogout }) {
  const [assignments, setAssignments] = useState([]);
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Call workflow
  const [phase, setPhase] = useState(PHASE_IDLE);
  const [callResult, setCallResult] = useState('');
  const [note, setNote] = useState('');
  const [promiseAmount, setPromiseAmount] = useState('');
  const [promiseDate, setPromiseDate] = useState('');
  const [refusalReason, setRefusalReason] = useState('');
  const [duration, setDuration] = useState(0);
  const timerRef = useRef(null);

  // Validation
  const [validationError, setValidationError] = useState('');

  // History
  const [history, setHistory] = useState([]);
  // Stats bar
  const [todayStats, setTodayStats] = useState({ calls: 0, promises: 0, totalPromised: 0 });

  // Load assignments
  useEffect(() => { loadAssignments(); }, [operator.id]);

  // Timer
  useEffect(() => {
    if (phase === PHASE_CALLING) {
      timerRef.current = setInterval(() => setDuration(d => d + 1), 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [phase]);

  const loadAssignments = async () => {
    setLoading(true);
    try {
      // Load assignments for this specific operator from /api/assignments/
      const res = await fetch(`${API_BASE}/assignments/?operator_id=${operator.id}`);
      const data = await res.json();
      const list = data.results || data;
      const items = list.map(a => ({
        id: a.id,
        assignment_id: a.id,
        credit_id: a.credit,
        client_id: a.client_id || a.client,
        client_name: a.client_name || a.debtor_name || `Клиент #${a.client_id}`,
        phone: a.client_phone || '',
        overdue_amount: parseFloat(a.overdue_amount) || 0,
        overdue_days: a.overdue_days || 0,
        priority: a.priority || 1,
        attempts: a.total_attempts || 0,
        last_promise_amount: a.last_promise_amount ? parseFloat(a.last_promise_amount) : null,
        last_promise_date: a.last_promise_date || null,
        last_contact: null,
        last_status: null,
      }));
      setAssignments(items);
      if (items.length > 0) setSelected(items[0]);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const loadHistory = async (clientId) => {
    try {
      const res = await fetch(`${API_BASE}/interventions/?client=${clientId}&ordering=-datetime`);
      const data = await res.json();
      const list = data.results || data || [];
      setHistory(list);
    } catch { setHistory([]); }
  };

  useEffect(() => {
    if (selected?.client_id) loadHistory(selected.client_id);
  }, [selected?.client_id]);

  // ---- Call workflow handlers ----
  const handleStartCall = () => {
    if (!selected) return;
    setPhase(PHASE_CALLING);
    setDuration(0);
    setCallResult('');
    setNote('');
    setPromiseAmount('');
    setPromiseDate('');
    setRefusalReason('');
    setValidationError('');
  };

  const handleEndCall = () => {
    setPhase(PHASE_RESULT);
  };

  const handleSelectResult = (val) => {
    setCallResult(val);
    setValidationError('');
  };

  const validate = () => {
    if (!callResult) {
      setValidationError('Выберите результат звонка');
      return false;
    }
    if (callResult === 'promise') {
      if (!promiseAmount || parseFloat(promiseAmount) <= 0) {
        setValidationError('Укажите сумму обещания');
        return false;
      }
      if (!promiseDate) {
        setValidationError('Укажите дату обещанной оплаты');
        return false;
      }
    }
    if (callResult === 'refuse') {
      if (!refusalReason) {
        setValidationError('Укажите причину отказа');
        return false;
      }
    }
    setValidationError('');
    return true;
  };

  const handleSaveIntervention = async () => {
    if (!validate()) return;
    if (!selected?.client_id || !selected?.credit_id) {
      setValidationError('Ошибка: не выбран клиент или кредит');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        client: selected.client_id,
        credit: selected.credit_id,
        operator: operator.id,
        datetime: new Date().toISOString(),
        intervention_type: 'phone',
        status: callResult,
        duration: duration,
        notes: note || '',
        promise_amount: callResult === 'promise' ? parseFloat(promiseAmount) : 0,
        promise_date: callResult === 'promise' ? promiseDate : null,
        refusal_reason: callResult === 'refuse' ? refusalReason : '',
      };

      console.log('Saving intervention:', payload);

      const res = await fetch(`${API_BASE}/interventions/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setPhase(PHASE_SAVED);
        // Update local stats
        setTodayStats(prev => ({
          calls: prev.calls + 1,
          promises: callResult === 'promise' ? prev.promises + 1 : prev.promises,
          totalPromised: callResult === 'promise'
            ? prev.totalPromised + parseFloat(promiseAmount || 0)
            : prev.totalPromised,
        }));
        // Update assignment list with new promise info
        setAssignments(prev => prev.map(a =>
          a.id === selected.id
            ? {
                ...a,
                attempts: a.attempts + 1,
                last_contact: new Date().toLocaleString('ru-RU'),
                last_status: callResult,
                last_promise_amount: callResult === 'promise' ? parseFloat(promiseAmount) : a.last_promise_amount,
                last_promise_date: callResult === 'promise' ? promiseDate : a.last_promise_date,
              }
            : a
        ));
        // Also update selected
        if (callResult === 'promise') {
          setSelected(prev => ({
            ...prev,
            last_promise_amount: parseFloat(promiseAmount),
            last_promise_date: promiseDate,
          }));
        }
        loadHistory(selected.client_id);
      } else {
        const errText = await res.text();
        console.error('Save failed:', res.status, errText);
        try {
          const errJson = JSON.parse(errText);
          const msgs = Object.entries(errJson).map(([k,v]) => `${k}: ${Array.isArray(v)?v.join(', '):v}`).join('; ');
          setValidationError('Ошибка: ' + msgs);
        } catch {
          setValidationError('Ошибка сервера: ' + res.status);
        }
      }
    } catch (err) {
      console.error('Network error:', err);
      setValidationError('Ошибка сети: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleNextClient = () => {
    const idx = assignments.findIndex(a => a.id === selected?.id);
    const next = assignments[idx + 1] || assignments[0];
    setSelected(next);
    setPhase(PHASE_IDLE);
  };

  const handleCancel = () => {
    setPhase(PHASE_IDLE);
    setDuration(0);
  };

  // ---- Helpers ----
  const filtered = assignments.filter(a => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return a.client_name.toLowerCase().includes(q) || (a.phone || '').includes(q);
  });

  const fmt = (sec) => `${String(Math.floor(sec / 60)).padStart(2, '0')}:${String(sec % 60).padStart(2, '0')}`;
  const money = (v) => Number(v || 0).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' });

  const statusLabel = (s) => {
    const opt = RESULT_OPTIONS.find(o => o.value === s);
    return opt ? opt.label : s;
  };
  const statusColor = (s) => {
    if (s === 'promise' || s === 'completed') return '#16a34a';
    if (s === 'refuse') return '#f85149';
    if (s === 'no_answer') return '#484f58';
    return '#d97706';
  };

  return (
    <div>
      {/* Top bar */}
      <div className="topbar">
        <div className="topbar-left">
          <div className="title">Рабочий стол оператора</div>
          <div className="operator">
            Оператор: <strong>{operator.full_name}</strong>
          </div>
        </div>
        <div className="topbar-right" style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <div style={{ textAlign: 'right', fontSize: 13, lineHeight: 1.4 }}>
            <div>Звонков сегодня: <b>{todayStats.calls}</b></div>
            <div>Обещаний: <b>{todayStats.promises}</b> на {money(todayStats.totalPromised)}</div>
          </div>
          <button className="btn ghost" onClick={onLogout}>Выход</button>
        </div>
      </div>

      <div className="operator-layout">
        {/* ===== LEFT: Client list ===== */}
        <aside className="left-col">
          <div className="search-row">
            <input className="search" placeholder="Поиск по ФИО/телефону" value={query} onChange={e => setQuery(e.target.value)} />
          </div>
          {loading ? (
            <div style={{ padding: 20 }} className="muted">Загрузка клиентов...</div>
          ) : (
            <div className="clients-list">
              {filtered.map(c => (
                <div key={c.id}
                  className={`client-list-item ${selected?.id === c.id ? 'selected' : ''}`}
                  onClick={() => { if (phase === PHASE_IDLE || phase === PHASE_SAVED) { setSelected(c); setPhase(PHASE_IDLE); } }}
                  style={{ opacity: (phase === PHASE_CALLING || phase === PHASE_RESULT) && selected?.id !== c.id ? 0.5 : 1 }}
                >
                  <div className="cli-left">
                    <div className="cli-name">{c.client_name}</div>
                    <div className="cli-phone">{c.phone}</div>
                    <div className="cli-meta" style={{ fontSize: 12 }}>
                      Попыток: {c.attempts}
                      {c.last_status && <span style={{ marginLeft: 6, color: statusColor(c.last_status) }}>● {statusLabel(c.last_status)}</span>}
                    </div>
                    {c.last_promise_amount && (
                      <div style={{ fontSize: 11, color: '#16a34a', marginTop: 2 }}>
                        🤝 Обещание: {money(c.last_promise_amount)}
                        {c.last_promise_date && <span> до {c.last_promise_date}</span>}
                      </div>
                    )}
                  </div>
                  <div className="cli-right">
                    <div className="cli-amount" style={{ color: '#f85149' }}>{money(c.overdue_amount)}</div>
                    <div className="cli-days" style={{ color: c.overdue_days > 30 ? '#f85149' : '#d97706' }}>{c.overdue_days} дн.</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </aside>

        {/* ===== CENTER: Client info + history ===== */}
        <section className="center-col">
          {selected ? (
            <div className="detail-card">
              <div className="detail-top">
                <div>
                  <h3 style={{ margin: 0 }}>{selected.client_name}</h3>
                  <div className="muted" style={{ marginTop: 4 }}>📞 {selected.phone}</div>
                  <div className="muted" style={{ fontSize: 13, marginTop: 2 }}>Кредит #{selected.credit_id} • Приоритет: {selected.priority}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 13, color: '#8b949e' }}>Сумма просрочки</div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: '#f85149' }}>{money(selected.overdue_amount)}</div>
                  <div className="muted" style={{ fontSize: 13 }}>
                    Просрочка: <b style={{ color: selected.overdue_days > 30 ? '#f85149' : '#d97706' }}>{selected.overdue_days} дн.</b>
                  </div>
                </div>
              </div>

              {/* Promise info block */}
              {selected.last_promise_amount && (
                <div style={{ 
                  background: 'rgba(63,185,80,0.15)', border: '1px solid rgba(63,185,80,0.4)', borderRadius: 8, 
                  padding: '10px 14px', marginTop: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' 
                }>
                  <div>
                    <div style={{ fontSize: 13, color: '#3fb950', fontWeight: 600 }}>🤝 Последнее обещание оплаты</div>
                    <div style={{ fontSize: 12, color: '#3fb950', marginTop: 2 }}>
                      {selected.last_promise_date ? `Срок: до ${selected.last_promise_date}` : ''}
                    </div>
                  </div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#16a34a' }}>
                    {money(selected.last_promise_amount)}
                  </div>
                </div>
              )}

              {/* History */}
              <div style={{ marginTop: 16 }}>
                <h4 style={{ margin: '0 0 8px' }}>История воздействий ({history.length})</h4>
                {history.length === 0 ? (
                  <div className="muted">Нет записей</div>
                ) : (
                  <div className="history">
                    {history.slice(0, 15).map(h => (
                      <div key={h.id} className="history-item">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div>
                            <strong style={{ color: statusColor(h.status) }}>{statusLabel(h.status)}</strong>
                            <span className="muted" style={{ marginLeft: 8, fontSize: 12 }}>
                              {h.operator_name || ''}
                            </span>
                          </div>
                          <div className="muted" style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
                            {new Date(h.datetime).toLocaleString('ru-RU')} • {h.duration || 0} сек
                          </div>
                        </div>
                        {h.promise_amount > 0 && (
                          <div style={{ fontSize: 13, color: '#16a34a', marginTop: 4 }}>
                            💰 Обещание: {money(h.promise_amount)}
                            {h.promise_date && ` до ${h.promise_date}`}
                          </div>
                        )}
                        {h.refusal_reason && (
                          <div style={{ fontSize: 13, color: '#f85149', marginTop: 4 }}>
                            Причина отказа: {h.refusal_reason}
                          </div>
                        )}
                        {h.notes && (
                          <div className="muted" style={{ fontSize: 12, marginTop: 4, fontStyle: 'italic' }}>
                            «{h.notes}»
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="muted" style={{ padding: 40, textAlign: 'center' }}>Выберите клиента из списка</div>
          )}
        </section>

        {/* ===== RIGHT: Call panel ===== */}
        <aside className="right-col">
          <div className="cti-card">

            {/* ---- PHASE: IDLE ---- */}
            {phase === PHASE_IDLE && (
              <>
                <div style={{ textAlign: 'center', padding: '20px 0' }}>
                  <div style={{ fontSize: 48 }}>📞</div>
                  <div style={{ marginTop: 8, fontSize: 14 }} className="muted">
                    {selected ? `Готов к звонку: ${selected.client_name}` : 'Выберите клиента'}
                  </div>
                </div>
                <button className="btn large" style={{ width: '100%' }} onClick={handleStartCall} disabled={!selected}>
                  Начать звонок
                </button>
              </>
            )}

            {/* ---- PHASE: CALLING ---- */}
            {phase === PHASE_CALLING && (
              <>
                <div style={{ textAlign: 'center', padding: '12px 0' }}>
                  <div style={{ color: '#22c55e', fontWeight: 600, fontSize: 14, marginBottom: 4 }}>● Звонок идёт</div>
                  <div style={{ fontSize: 36, fontWeight: 700, fontFamily: 'monospace' }}>{fmt(duration)}</div>
                  <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>{selected?.client_name}</div>
                  <div className="muted" style={{ fontSize: 13 }}>{selected?.phone}</div>
                </div>
                <button className="btn large" style={{ width: '100%', background: '#f85149' }} onClick={handleEndCall}>
                  Завершить звонок
                </button>
                <button className="btn ghost" style={{ width: '100%', marginTop: 8 }} onClick={handleCancel}>
                  Отмена
                </button>
              </>
            )}

            {/* ---- PHASE: RESULT ---- */}
            {phase === PHASE_RESULT && (
              <>
                <div style={{ marginBottom: 12 }}>
                  <div className="muted" style={{ fontSize: 12 }}>Длительность звонка: <b>{fmt(duration)}</b></div>
                </div>

                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: 'block', fontWeight: 600, marginBottom: 6, fontSize: 14 }}>Результат звонка *</label>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {RESULT_OPTIONS.map(opt => (
                      <label key={opt.value}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 8,
                          padding: '8px 10px', borderRadius: 6, cursor: 'pointer',
                          border: callResult === opt.value ? '2px solid #388bfd' : '1px solid #30363d',
                          background: callResult === opt.value ? 'rgba(56,139,253,0.15)' : '#161b22',
                        }}
                      >
                        <input type="radio" name="result" value={opt.value}
                          checked={callResult === opt.value}
                          onChange={() => handleSelectResult(opt.value)}
                          style={{ accentColor: '#388bfd' }}
                        />
                        <span>{opt.icon} {opt.label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Promise fields */}
                {callResult === 'promise' && (
                  <div style={{ background: 'rgba(63,185,80,0.15)', border: '1px solid rgba(63,185,80,0.4)', borderRadius: 8, padding: 12, marginBottom: 12 }}>
                    <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: 13 }}>Сумма обещания (₽) *</label>
                    <input type="number" className="search" style={{ width: '100%', boxSizing: 'border-box', marginBottom: 8 }}
                      value={promiseAmount} onChange={e => setPromiseAmount(e.target.value)}
                      placeholder="Например: 15000" min="0"
                    />
                    <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: 13 }}>Дата обещанной оплаты *</label>
                    <input type="date" className="search" style={{ width: '100%', boxSizing: 'border-box' }}
                      value={promiseDate} onChange={e => setPromiseDate(e.target.value)}
                    />
                  </div>
                )}

                {/* Refusal reason */}
                {callResult === 'refuse' && (
                  <div style={{ background: 'rgba(248,81,73,0.15)', border: '1px solid rgba(248,81,73,0.4)', borderRadius: 8, padding: 12, marginBottom: 12 }}>
                    <label style={{ display: 'block', fontWeight: 600, marginBottom: 6, fontSize: 13 }}>Причина отказа *</label>
                    {REFUSAL_REASONS.map(r => (
                      <label key={r} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, fontSize: 13, cursor: 'pointer' }}>
                        <input type="radio" name="refusal" value={r}
                          checked={refusalReason === r}
                          onChange={() => { setRefusalReason(r); setValidationError(''); }}
                        />
                        {r}
                      </label>
                    ))}
                  </div>
                )}

                {/* Notes */}
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: 13 }}>Комментарий</label>
                  <textarea className="script" style={{ width: '100%', boxSizing: 'border-box' }}
                    value={note} onChange={e => setNote(e.target.value)}
                    placeholder="Заметки по звонку..." rows={3}
                  />
                </div>

                {validationError && (
                  <div style={{ color: '#f85149', fontSize: 13, marginBottom: 8, fontWeight: 500 }}>
                    ⚠ {validationError}
                  </div>
                )}

                <button className="btn large" style={{ width: '100%' }}
                  onClick={handleSaveIntervention} disabled={saving}
                >
                  {saving ? 'Сохранение...' : '💾 Сохранить результат'}
                </button>
                <button className="btn ghost" style={{ width: '100%', marginTop: 8 }} onClick={() => setPhase(PHASE_CALLING)}>
                  ← Вернуться к звонку
                </button>
              </>
            )}

            {/* ---- PHASE: SAVED ---- */}
            {phase === PHASE_SAVED && (
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                <div style={{ fontSize: 48 }}>✅</div>
                <div style={{ fontWeight: 600, fontSize: 16, marginTop: 8, color: '#16a34a' }}>
                  Результат сохранён!
                </div>
                <div className="muted" style={{ marginTop: 6, fontSize: 13 }}>
                  {statusLabel(callResult)} • {fmt(duration)}
                  {callResult === 'promise' && <><br/>Обещание: {money(promiseAmount)} до {promiseDate}</>}
                  {callResult === 'refuse' && <><br/>Причина: {refusalReason}</>}
                </div>
                <button className="btn large" style={{ width: '100%', marginTop: 16 }} onClick={handleNextClient}>
                  → Следующий клиент
                </button>
                <button className="btn ghost" style={{ width: '100%', marginTop: 8 }} onClick={() => setPhase(PHASE_IDLE)}>
                  Остаться на клиенте
                </button>
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

// ===== MAIN APP =====
export default function App() {
  const [user, setUser] = useState(null);
  const [page, setPage] = useState('workspace');

  // Check saved session
  useEffect(() => {
    const saved = localStorage.getItem('operator');
    if (saved) {
      try {
        setUser(JSON.parse(saved));
      } catch (e) {
        localStorage.removeItem('operator');
      }
    }
  }, []);

  const handleLogin = (operatorData) => {
    setUser(operatorData);
    localStorage.setItem('operator', JSON.stringify(operatorData));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('operator');
    setPage('workspace');
  };

  // Not logged in - show login page
  if (!user) {
    return <LoginPage onLogin={handleLogin} />;
  }

  // Manager/Admin role - show dashboard with navigation
  if (user.role === 'manager' || user.role === 'admin') {
    return (
      <div>
        <div className="topbar">
          <div className="topbar-left">
            <div className="title">ДРПЗ — Система управления взысканием</div>
          </div>
          <div className="topbar-right">
            <span className="muted" style={{ marginRight: 16 }}>{user.full_name || user.name}</span>
            <button className="btn ghost" onClick={handleLogout}>Выход</button>
          </div>
        </div>
        
        <div style={{ padding: '16px 20px' }}>
          <div style={{ marginBottom: 20, display: 'flex', gap: 8 }}>
            <button 
              className={`btn ${page === 'dashboard' ? '' : 'ghost'}`}
              onClick={() => setPage('dashboard')}
            >
              📊 Дашборд руководителя
            </button>
            <button 
              className={`btn ${page === 'workspace' ? '' : 'ghost'}`}
              onClick={() => setPage('workspace')}
            >
              📞 Рабочий стол оператора
            </button>
          </div>
          
          {page === 'dashboard' ? (
            <DashboardPage />
          ) : (
            <OperatorWorkspace 
              operator={{ ...user, id: user.id, full_name: user.full_name || user.name }} 
              onLogout={handleLogout} 
            />
          )}
        </div>
      </div>
    );
  }

  // Operator role - show only workspace
  return <OperatorWorkspace operator={user} onLogout={handleLogout} />;
}
