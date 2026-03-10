import React, { useEffect, useMemo, useState, useRef, useCallback } from "react";

const API_URL = 'http://127.0.0.1:8000/api';

// Причины отказа от оплаты
const REFUSAL_REASONS = [
  'Финансовые трудности',
  'Потеря работы',
  'Болезнь / нетрудоспособность',
  'Не согласен с суммой долга',
  'Считает кредит погашенным',
  'Оспаривает начисление процентов/штрафов',
  'Принципиально отказывается платить',
  'Планирует банкротство',
  'Ожидает решения суда',
  'Другая причина',
];

// Copilot-подсказки
const COPILOT_PHRASES = {
  'forgetful': ['Уверен, это просто упущение', 'Могу прямо сейчас отправить ссылку для оплаты', 'Давайте вместе посмотрим, как удобнее оплатить'],
  'cooperative': ['Ценю, что вы всегда на связи', 'Давайте найдём удобное решение', 'Спасибо за сотрудничество'],
  'unable': ['Понимаю, что сейчас сложно', 'У нас есть программа реструктуризации', 'Можем снизить ежемесячный платёж'],
  'unwilling': ['При дальнейшей просрочке будут начисляться пени', 'Предлагаю решить вопрос сейчас', 'Информация может быть передана в БКИ'],
  'toxic': ['Прошу отнестись к вопросу серьёзно', 'Это официальное уведомление', 'Готов выслушать вашу позицию'],
};

const MOCK_HISTORY = [];

// Стили для табов в сайдбаре
const tabStyle = (active) => ({
  flex: 1, padding: '6px 0', textAlign: 'center', cursor: 'pointer',
  fontWeight: 600, fontSize: 12, borderBottom: active ? '2px solid #388bfd' : '2px solid transparent',
  color: active ? '#58a6ff' : '#8b949e', background: active ? 'rgba(56,139,253,0.1)' : 'transparent',
  transition: 'all 0.15s',
});

const formatCurrency = (v) => Number(v || 0).toLocaleString("ru-RU", { style: "currency", currency: "RUB" });
const relativeDate = (iso) => (iso ? new Date(iso).toLocaleString() : "—");

const getRiskColor = (segment) => {
  const colors = { low: '#22c55e', medium: '#f59e0b', high: '#ef4444', critical: '#f85149' };
  return colors[segment] || '#8b949e';
};

const getUrgencyLabel = (u) => {
  const labels = { 1: 'Низкая', 2: 'Средняя', 3: 'Повышенная', 4: 'Высокая', 5: 'Критическая' };
  return labels[u] || '';
};

export default function CollectionDeskApp({ user, onClient360, onCreditClick }) {
  const [queue, setQueue] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [history, setHistory] = useState([]);
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [isCalling, setIsCalling] = useState(false);
  const [callStart, setCallStart] = useState(null);
  const [callTick, setCallTick] = useState(0);
  const [recordingOn, setRecordingOn] = useState(false);
  const [resultCode, setResultCode] = useState("no_answer");
  const [note, setNote] = useState("");
  const [promiseAmount, setPromiseAmount] = useState("");
  const [promiseDate, setPromiseDate] = useState("");
  const [refusalReason, setRefusalReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [loadingQueue, setLoadingQueue] = useState(true);
  const [sidebarTab, setSidebarTab] = useState('pending'); // 'pending' | 'worked'
  const [creditDetails, setCreditDetails] = useState([]);
  const callTimerRef = useRef(null);

  const isManager = user && (user.role === 'manager' || user.role === 'supervisor' || user.role === 'admin');

  // Загрузка очереди должников из БД
  const loadQueue = useCallback(async () => {
    setLoadingQueue(true);
    try {
      let debtors = [];

      if (isManager) {
        // Руководитель видит всех должников
        const resp = await fetch(`${API_URL}/credits/?status=overdue,default`);
        if (!resp.ok) throw new Error('Ошибка загрузки');
        const credits = await resp.json();
        
        const clientMap = {};
        for (const c of credits) {
          const cid = c.client;
          if (!clientMap[cid]) {
            clientMap[cid] = {
              id: cid,
              clientId: cid,
              name: c.client_name || `Клиент #${cid}`,
              mainPhone: c.client_phone || '',
              outstanding: 0,
              daysPastDue: 0,
              lastContact: null,
              attempts: 0,
              credits: [],
              creditId: null,
            };
          }
          clientMap[cid].outstanding += parseFloat(c.overdue_amount || c.principal_amount || 0);
          clientMap[cid].daysPastDue = Math.max(clientMap[cid].daysPastDue, c.overdue_days || 0);
          clientMap[cid].credits.push(c);
          if (!clientMap[cid].creditId) clientMap[cid].creditId = c.id;
        }
        debtors = Object.values(clientMap).sort((a, b) => b.daysPastDue - a.daysPastDue);
      } else {
        // Оператор видит только назначенных ему клиентов
        const resp = await fetch(`${API_URL}/assignments/?operator_id=${user.id}`);
        if (!resp.ok) throw new Error('Ошибка загрузки назначений');
        const assignments = await resp.json();
        const list = assignments.results || assignments;

        const clientMap = {};
        for (const a of list) {
          const cid = a.client_id;
          if (!cid) continue;
          if (!clientMap[cid]) {
            clientMap[cid] = {
              id: cid,
              clientId: cid,
              name: a.client_name || `Клиент #${cid}`,
              mainPhone: a.client_phone || '',
              outstanding: 0,
              daysPastDue: 0,
              lastContact: null,
              attempts: a.total_attempts || 0,
              credits: [],
              creditId: a.credit || null,
            };
          }
          clientMap[cid].outstanding += parseFloat(a.overdue_amount || 0);
          clientMap[cid].daysPastDue = Math.max(clientMap[cid].daysPastDue, a.overdue_days || 0);
          clientMap[cid].credits.push(a);
          if (!clientMap[cid].creditId) clientMap[cid].creditId = a.credit;
        }
        debtors = Object.values(clientMap).sort((a, b) => b.outstanding - a.outstanding);
      }
      
      // Подгружаем количество попыток из interventions и определяем, отработан ли клиент сегодня
      const todayStr = new Date().toISOString().slice(0, 10); // 'YYYY-MM-DD'
      for (const d of debtors) {
        try {
          const hResp = await fetch(`${API_URL}/interventions/?client_id=${d.clientId}&ordering=-datetime`);
          if (hResp.ok) {
            const interventions = await hResp.json();
            d.attempts = interventions.length;
            d.lastContact = interventions.length > 0 ? interventions[0].datetime : null;
            // Считаем сегодняшние воздействия
            const todayInterventions = interventions.filter(i => i.datetime && i.datetime.slice(0, 10) === todayStr);
            d.workedToday = todayInterventions.length > 0;
            d.todayCount = todayInterventions.length;
          } else {
            d.workedToday = false;
            d.todayCount = 0;
          }
        } catch (e) {
          d.workedToday = false;
          d.todayCount = 0;
        }
      }

      // Подгружаем ML-прогноз риска для каждого клиента
      for (const d of debtors) {
        try {
          const riskResp = await fetch(`${API_URL}/overdue-prediction/?client_id=${d.clientId}`);
          if (riskResp.ok) {
            const riskData = await riskResp.json();
            const results = riskData.results || [];
            if (results.length > 0) {
              // Берём максимальный risk_score среди всех кредитов клиента
              const maxRisk = results.reduce((mx, r) => r.risk_score > mx.risk_score ? r : mx, results[0]);
              d.mlRiskScore = maxRisk.risk_score;
              d.mlRiskCategory = maxRisk.risk_category;
              d.mlRiskLabel = maxRisk.risk_label;
            }
          }
        } catch (e) { /* ML-прогноз не критичен */ }
      }

      setQueue(debtors);
      if (debtors.length > 0 && !selectedId) setSelectedId(debtors[0].id);
    } catch (e) {
      console.error('Ошибка загрузки очереди:', e);
    } finally {
      setLoadingQueue(false);
    }
  }, [user, isManager]);

  useEffect(() => { loadQueue(); }, [loadQueue]);

  // Загрузка истории при смене выбранного клиента
  const loadHistory = useCallback(async (clientId) => {
    if (!clientId) return;
    try {
      const resp = await fetch(`${API_URL}/interventions/?client_id=${clientId}&ordering=-datetime`);
      if (resp.ok) {
        const data = await resp.json();
        setHistory(data.map(i => ({
          id: i.id,
          debtorId: i.client,
          channel: i.intervention_type,
          at: i.datetime,
          duration: i.duration,
          result: i.status,
          note: i.notes,
          promiseAmount: i.promise_amount,
          promiseDate: i.promise_date,
          refusalReason: i.refusal_reason,
        })));
      }
    } catch (e) { console.error(e); }
  }, []);

  // Загрузка деталей кредитов при смене клиента
  const loadCreditDetails = useCallback(async (clientId) => {
    if (!clientId) { setCreditDetails([]); return; }
    try {
      const resp = await fetch(`${API_URL}/credits/?client=${clientId}`);
      if (resp.ok) {
        const data = await resp.json();
        const list = data.results || data;
        setCreditDetails(list.filter(c => c.status === 'overdue' || c.status === 'default'));
      }
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { if (selectedId) { loadHistory(selectedId); loadCreditDetails(selectedId); } }, [selectedId, loadHistory, loadCreditDetails]);

  const selected = useMemo(() => queue.find(d => d.id === selectedId) ?? null, [queue, selectedId]);

  // Агрегация разбивки долга по всем кредитам клиента
  const debtBreakdown = useMemo(() => {
    let overduePrincipal = 0, overdueInterest = 0, penalties = 0;
    for (const c of creditDetails) {
      const st = c.latest_state;
      if (st) {
        overduePrincipal += parseFloat(st.overdue_principal || 0);
        overdueInterest += parseFloat(st.overdue_interest || 0);
        penalties += parseFloat(st.penalties || 0);
      }
    }
    return { overduePrincipal, overdueInterest, penalties, total: overduePrincipal + overdueInterest + penalties };
  }, [creditDetails]);
  const selectedHistory = useMemo(() => history.filter(h => h.debtorId === selectedId), [history, selectedId]);

  // Определяем психотип и NBA по данным клиента
  const psychotype = useMemo(() => {
    if (!selected) return 'forgetful';
    if (selected.daysPastDue > 90) return 'unable';
    if (selected.daysPastDue > 30) return 'unwilling';
    return 'forgetful';
  }, [selected]);
  const selectedCopilotPhrases = COPILOT_PHRASES[psychotype] || COPILOT_PHRASES['forgetful'];

  useEffect(() => {
    function onKey(e) {
      if (e.key === "n" || e.key === "N") goNext();
      if (e.key === "c" || e.key === "C") toggleCall();
      if (e.key === "s" || e.key === "S") saveResult();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedId, isCalling, resultCode, note]);

  useEffect(() => {
    if (isCalling) {
      setCallStart(Date.now());
      setCallTick(0);
      callTimerRef.current = window.setInterval(() => setCallTick(t => t + 1), 1000);
    } else {
      if (callTimerRef.current) { clearInterval(callTimerRef.current); callTimerRef.current = null; }
      setCallStart(null);
      setCallTick(0);
    }
    return () => { if (callTimerRef.current) clearInterval(callTimerRef.current); };
  }, [isCalling]);

  function getCallDuration() {
    if (!callStart) return "00:00";
    const s = Math.floor((Date.now() - callStart) / 1000);
    const mm = String(Math.floor(s / 60)).padStart(2, "0");
    const ss = String(s % 60).padStart(2, "0");
    return `${mm}:${ss}`;
  }

  function toggleCall() {
    if (!selected) return;
    if (!isCalling) {
      console.log("Starting call to", selected.mainPhone);
      setIsCalling(true);
      setRecordingOn(true);
    } else {
      console.log("Ending call");
      const durationSec = callStart ? Math.floor((Date.now() - callStart) / 1000) : 0;
      if (callTimerRef.current) { clearInterval(callTimerRef.current); callTimerRef.current = null; }
      setIsCalling(false);
      setRecordingOn(false);
      setCallStart(null);
      setCallTick(0);

      // Сохраняем в БД
      saveInterventionToDB(durationSec);
    }
  }

  // Маппинг UI-кодов на статусы модели Intervention
  const mapResultToStatus = (code) => {
    const map = { 'no_answer': 'no_answer', 'promise_to_pay': 'promise', 'decline': 'refuse', 'callback': 'callback', 'completed': 'completed' };
    return map[code] || 'completed';
  };

  async function saveInterventionToDB(durationSec = 0) {
    if (!selected) return;
    setSaving(true);
    try {
      const body = {
        client: selected.clientId,
        credit: selected.creditId,
        operator: user?.id || null,
        datetime: new Date().toISOString(),
        intervention_type: 'phone',
        status: mapResultToStatus(resultCode),
        duration: durationSec,
        notes: note,
        promise_amount: resultCode === 'promise_to_pay' ? (parseFloat(promiseAmount) || 0) : 0,
        promise_date: resultCode === 'promise_to_pay' && promiseDate ? promiseDate : null,
        refusal_reason: resultCode === 'decline' ? refusalReason : '',
      };
      const resp = await fetch(`${API_URL}/interventions/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const err = await resp.text();
        throw new Error(err);
      }
      // Обновляем историю и очередь — помечаем клиента как отработанного сегодня
      await loadHistory(selected.clientId);
      setQueue(q => q.map(d => d.id === selected.id ? { ...d, attempts: d.attempts + 1, lastContact: new Date().toISOString(), workedToday: true, todayCount: (d.todayCount || 0) + 1 } : d));
      // Сброс полей
      setNote("");
      setPromiseAmount("");
      setPromiseDate("");
      setRefusalReason("");
    } catch (e) {
      console.error('Ошибка сохранения:', e);
      alert('Ошибка сохранения взаимодействия: ' + e.message);
    } finally {
      setSaving(false);
    }
  }

  function saveResult() {
    saveInterventionToDB(0);
  }

  function goNext() {
    // Переходим к следующему неотработанному клиенту
    const pending = queue.filter(d => !d.workedToday);
    if (pending.length === 0) {
      // Все отработаны — переходим к следующему в общем списке
      const idx = queue.findIndex(q => q.id === selectedId);
      const next = queue[idx + 1] ?? queue[0];
      setSelectedId(next?.id ?? null);
    } else {
      const currentPendingIdx = pending.findIndex(q => q.id === selectedId);
      const next = pending[currentPendingIdx + 1] ?? pending[0];
      setSelectedId(next?.id ?? null);
    }
    setResultCode("no_answer"); setNote(""); setPromiseAmount(""); setPromiseDate(""); setRefusalReason("");
  }

  const visible = queue.filter(d => {
    if (filter === "overdue30" && d.daysPastDue < 30) return false;
    if (filter === "high" && d.outstanding < 20000) return false;
    if (search && !( (d.name + ' ' + d.mainPhone).toLowerCase().includes(search.toLowerCase()) )) return false;
    return true;
  });

  const pendingVisible = visible.filter(d => !d.workedToday);
  const workedVisible = visible.filter(d => d.workedToday);

  return (
    <div className="container">
      <header style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
        <div style={{display:'flex',alignItems:'center',gap:12}}>
          <h1 className="app-title">Коллекторский рабочий стол</h1>
          <div className="muted">Оператор: <strong>{user?.name || user?.full_name || 'Неизвестный'}</strong>{isManager && <span style={{marginLeft:8,fontSize:11,color:'#f59e0b'}}>(все клиенты)</span>}</div>
        </div>
        <div className="muted">Горячие клавиши: N — след., C — звонок, S — сохранить</div>
      </header>

      <div className="operator-layout">
        <aside className="left-col">
          <div className="search-row">
            <input className="search" placeholder="Поиск по ФИО/телефону" value={search} onChange={e => setSearch(e.target.value)} />
            <select value={filter} onChange={e => setFilter(e.target.value)}>
              <option value="">Все</option>
              <option value="overdue30">Просрочка &gt; 30 дн.</option>
              <option value="high">Сумма &gt; 20k</option>
            </select>
          </div>
          {/* === Вкладки === */}
          <div style={{display:'flex',borderBottom:'1px solid #30363d',marginBottom:0}}>
            <div style={tabStyle(sidebarTab === 'pending')} onClick={() => setSidebarTab('pending')}>
              📋 К отработке ({pendingVisible.length})
            </div>
            <div style={tabStyle(sidebarTab === 'worked')} onClick={() => setSidebarTab('worked')}>
              ✅ Отработаны ({workedVisible.length})
            </div>
          </div>
          <div className="clients-list">
            {loadingQueue && <div className="muted" style={{padding:16,textAlign:'center'}}>⏳ Загрузка клиентов из БД...</div>}

            {/* === Вкладка: К отработке === */}
            {sidebarTab === 'pending' && !loadingQueue && pendingVisible.length === 0 && (
              <div className="muted" style={{padding:16,textAlign:'center'}}>🎉 Все клиенты отработаны!</div>
            )}
            {sidebarTab === 'pending' && pendingVisible.map(d => (
              <div key={d.id} className={`client-list-item ${d.id===selectedId ? 'selected' : ''}`} onClick={() => setSelectedId(d.id)}>
                <div className="cli-left">
                  <div className="cli-name">
                    {d.mlRiskCategory !== undefined && (
                      <span style={{display:'inline-block', width:8, height:8, borderRadius:'50%', marginRight:6, background: d.mlRiskCategory === 2 ? '#ef4444' : d.mlRiskCategory === 1 ? '#eab308' : '#22c55e'}} />
                    )}
                    {d.name}
                  </div>
                  <div className="cli-phone">{d.mainPhone}</div>
                </div>
                <div className="cli-right">
                  <div className="cli-amount">{formatCurrency(d.outstanding)}</div>
                  <div className="cli-days">{d.daysPastDue} дн.</div>
                </div>
                <div style={{width:'100%',fontSize:12,color:'#8b949e',marginTop:8}}>Попыток: {d.attempts} • Последний контакт: {relativeDate(d.lastContact)}</div>
              </div>
            ))}

            {/* === Вкладка: Отработаны сегодня === */}
            {sidebarTab === 'worked' && !loadingQueue && workedVisible.length === 0 && (
              <div className="muted" style={{padding:16,textAlign:'center'}}>Пока нет отработанных клиентов</div>
            )}
            {sidebarTab === 'worked' && workedVisible.map(d => (
              <div key={d.id} className={`client-list-item ${d.id===selectedId ? 'selected' : ''}`} onClick={() => setSelectedId(d.id)}>
                <div className="cli-left">
                  <div className="cli-name">{d.name}</div>
                  <div className="cli-phone">{d.mainPhone}</div>
                </div>
                <div className="cli-right">
                  <div className="cli-amount">{formatCurrency(d.outstanding)}</div>
                  <div className="cli-days">{d.daysPastDue} дн.</div>
                </div>
                <div style={{width:'100%',fontSize:12,color:'#8b949e',marginTop:8}}>
                  <span style={{color:'#16a34a',fontWeight:600}}>Сегодня: {d.todayCount} воздейств.</span> • Последний: {relativeDate(d.lastContact)}
                </div>
              </div>
            ))}
          </div>
          <footer className="muted" style={{marginTop:12}}>К отработке: {pendingVisible.length} • Отработано: {workedVisible.length} • Всего: {visible.length}</footer>
        </aside>

        <section className="center-col">
          {selected ? (
            <div className="detail-card">
              <div className="detail-top">
                <div>
                  <h2 style={{margin:0}}>{selected.name}</h2>
                  <div className="muted">Тел: {selected.mainPhone}</div>
                  <div style={{marginTop:8}}>Сумма задолженности: <strong>{formatCurrency(debtBreakdown.total > 0 ? debtBreakdown.total : selected.outstanding)}</strong></div>
                  <div className="muted">Просрочка: {selected.daysPastDue} дней</div>
                  {debtBreakdown.total > 0 && (
                    <div style={{marginTop:8,padding:'8px 12px',background:'rgba(248,81,73,0.15)',borderRadius:8,border:'1px solid rgba(248,81,73,0.4)',fontSize:13}}>
                      <div style={{fontWeight:600,fontSize:12,color:'#f85149',marginBottom:4}}>Структура задолженности:</div>
                      <div style={{display:'flex',justifyContent:'space-between'}}><span>Основной долг:</span><strong>{formatCurrency(debtBreakdown.overduePrincipal)}</strong></div>
                      <div style={{display:'flex',justifyContent:'space-between'}}><span>Проценты:</span><strong>{formatCurrency(debtBreakdown.overdueInterest)}</strong></div>
                      <div style={{display:'flex',justifyContent:'space-between'}}><span>Штрафы/пени:</span><strong style={{color:'#f85149'}}>{formatCurrency(debtBreakdown.penalties)}</strong></div>
                      <div style={{display:'flex',justifyContent:'space-between',borderTop:'1px solid rgba(248,81,73,0.4)',marginTop:4,paddingTop:4,fontWeight:700}}><span>Итого:</span><span>{formatCurrency(debtBreakdown.total)}</span></div>
                    </div>
                  )}
                </div>
                <div style={{textAlign:'right'}}>
                  <div>
                    <span style={{display:'inline-block',padding:'2px 8px',borderRadius:4,fontSize:11,fontWeight:600,
                      background: (selected.mlRiskCategory ?? (selected.daysPastDue > 90 ? 2 : selected.daysPastDue > 30 ? 1 : 0)) === 2 ? '#ef444420' : (selected.mlRiskCategory ?? (selected.daysPastDue > 90 ? 2 : selected.daysPastDue > 30 ? 1 : 0)) === 1 ? '#f59e0b20' : '#22c55e20',
                      color: (selected.mlRiskCategory ?? (selected.daysPastDue > 90 ? 2 : selected.daysPastDue > 30 ? 1 : 0)) === 2 ? '#ef4444' : (selected.mlRiskCategory ?? (selected.daysPastDue > 90 ? 2 : selected.daysPastDue > 30 ? 1 : 0)) === 1 ? '#f59e0b' : '#22c55e'
                    }}>
                      {selected.mlRiskLabel ? `${selected.mlRiskLabel.toUpperCase()} РИСК` : (selected.daysPastDue > 90 ? 'ВЫСОКИЙ' : selected.daysPastDue > 30 ? 'СРЕДНИЙ' : 'НИЗКИЙ') + ' РИСК'}
                      {selected.mlRiskScore !== undefined && <span style={{marginLeft:4, opacity:0.7}}>({(selected.mlRiskScore * 100).toFixed(0)})</span>}
                    </span>
                    {selected.mlRiskScore !== undefined && <div style={{fontSize:10, color:'#a3a3a3', marginTop:2}}>ML-прогноз</div>}
                  </div>
                  <button className="btn small ghost" style={{marginTop:8}} onClick={() => onClient360 && onClient360(selected.clientId)}>
                    👤 360° профиль
                  </button>
                  {creditDetails.length > 0 && (
                    <div style={{marginTop:8}}>
                      {creditDetails.map(c => (
                        <button key={c.id} className="btn small ghost" style={{marginTop:4,fontSize:12,display:'block',width:'100%',textAlign:'left'}}
                          onClick={() => onCreditClick && onCreditClick(c.id)}>
                          💳 Договор #{c.id}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              
              <div className="detail-actions">
                <button className="btn large" onClick={() => { setSelectedId(selected.id); toggleCall(); }}>{isCalling ? 'Завершить звонок' : 'Позвонить'}</button>
                <button className="btn ghost" onClick={() => setResultCode('promise_to_pay')}>Зафиксировать обещание</button>
                <button className="btn ghost" onClick={() => setResultCode('decline')}>Отказ от оплаты</button>
                <button className="btn ghost" onClick={() => setResultCode('no_answer')}>Не дозвон</button>
              </div>
              <div className="history">
                <h4>История взаимодействий</h4>
                {selectedHistory.length === 0 && <div className="muted">Нет записей</div>}
                {selectedHistory.map(h => (
                  <div key={h.id} className="history-item">
                    <div>{(h.channel || 'phone').toUpperCase()} — {relativeDate(h.at)} — <strong>{
                      h.result === 'promise' ? '💰 Обещание' :
                      h.result === 'refuse' ? '❌ Отказ' :
                      h.result === 'no_answer' ? '📵 Не дозвон' :
                      h.result === 'completed' ? '✅ Завершено' :
                      h.result === 'callback' ? '🔄 Перезвонить' : h.result
                    }</strong>
                    {h.duration > 0 && <span className="muted"> ({Math.floor(h.duration/60)}м {h.duration%60}с)</span>}
                    </div>
                    {h.result === 'promise' && h.promiseAmount > 0 && (
                      <div style={{color:'#16a34a',fontSize:13,marginTop:2}}>
                        💵 Обещание: {formatCurrency(h.promiseAmount)}{h.promiseDate && ` к ${h.promiseDate}`}
                      </div>
                    )}
                    {h.result === 'refuse' && h.refusalReason && (
                      <div style={{color:'#f85149',fontSize:13,marginTop:2}}>Причина: {h.refusalReason}</div>
                    )}
                    {h.note && <div style={{color:'#8b949e',fontSize:13}}>{h.note}</div>}
                  </div>
                ))}
              </div>
            </div>
          ) : <div className="muted">Выберите клиента в очереди</div>}
        </section>

        <aside className="right-col">
          <div className="cti-card">
            <div className="cti-row"><strong>CTI статус:</strong> <span className="cti-status">{isCalling ? '🟢 На звонке' : '⚪ Готов'}</span></div>
            <div className="cti-row"><div className="muted">Таймер:</div><div className="timer">{getCallDuration()}</div></div>
            
            {/* Copilot Suggestions */}
            <div style={{background:'rgba(63,185,80,0.15)',border:'1px solid rgba(63,185,80,0.4)',borderRadius:8,padding:10,marginBottom:10}}>
              <div style={{fontSize:12,fontWeight:600,color:'#3fb950',marginBottom:6}}>🤖 Copilot подсказки:</div>
              <div style={{fontSize:11,color:'#8b949e'}}>Фразы для этого типа клиента:</div>
              {selectedCopilotPhrases.slice(0,2).map((phrase, i) => (
                <div key={i} style={{fontSize:12,color:'#e6edf3',padding:'4px 0',cursor:'pointer'}} 
                     onClick={() => navigator.clipboard.writeText(phrase)} title="Клик чтобы скопировать">
                  → {phrase}
                </div>
              ))}
            </div>
            
            <div className="cti-row">
              <label>Результат звонка</label>
              <select value={resultCode} onChange={e=>setResultCode(e.target.value)} style={{marginTop:8}}>
                <option value="no_answer">Не дозвон</option>
                <option value="promise_to_pay">Обещание оплатить</option>
                <option value="decline">Отказ от оплаты</option>
                <option value="callback">Перезвонить</option>
                <option value="completed">Контакт состоялся</option>
              </select>
            </div>

            {/* Поля для обещания */}
            {resultCode === 'promise_to_pay' && (
              <div style={{background:'rgba(63,185,80,0.15)',border:'1px solid rgba(63,185,80,0.4)',borderRadius:8,padding:10,margin:'8px 0'}}>
                <label style={{fontSize:12,fontWeight:600,color:'#3fb950',display:'block',marginBottom:6}}>💰 Данные обещания</label>
                <div style={{marginBottom:6}}>
                  <label style={{fontSize:12,color:'#8b949e',display:'block'}}>Сумма обещания (₽)</label>
                  <input type="number" value={promiseAmount} onChange={e=>setPromiseAmount(e.target.value)}
                    placeholder="Например: 15000" min="0" step="1000"
                    style={{width:'100%',padding:'6px 8px',borderRadius:6,border:'1px solid #30363d',fontSize:14,marginTop:2,boxSizing:'border-box',background:'#0d1117',color:'#e6edf3'}} />
                </div>
                <div>
                  <label style={{fontSize:12,color:'#8b949e',display:'block'}}>Дата обещанной оплаты</label>
                  <input type="date" value={promiseDate} onChange={e=>setPromiseDate(e.target.value)}
                    style={{width:'100%',padding:'6px 8px',borderRadius:6,border:'1px solid #30363d',fontSize:14,marginTop:2,boxSizing:'border-box',background:'#0d1117',color:'#e6edf3'}} />
                </div>
              </div>
            )}

            {/* Поля для отказа */}
            {resultCode === 'decline' && (
              <div style={{background:'rgba(248,81,73,0.15)',border:'1px solid rgba(248,81,73,0.4)',borderRadius:8,padding:10,margin:'8px 0'}}>
                <label style={{fontSize:12,fontWeight:600,color:'#f85149',display:'block',marginBottom:6}}>❌ Причина отказа</label>
                <select value={refusalReason} onChange={e=>setRefusalReason(e.target.value)}
                  style={{width:'100%',padding:'6px 8px',borderRadius:6,border:'1px solid #30363d',fontSize:13,boxSizing:'border-box',background:'#0d1117',color:'#e6edf3'}}>
                  <option value="">— Выберите причину —</option>
                  {REFUSAL_REASONS.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
            )}

            <div className="cti-row"><label>Заметка</label><textarea value={note} onChange={e=>setNote(e.target.value)} style={{marginTop:8}} placeholder="Комментарий к звонку..." /></div>
            <div className="cti-actions"><button className="btn" onClick={saveResult} disabled={saving}>{saving ? '⏳ Сохранение...' : 'Сохранить'}</button><button className="btn ghost" onClick={()=>setRecordingOn(r=>!r)}>{recordingOn? '⏹ Стоп запись' : '⏺ Запись'}</button></div>
            <div className="muted" style={{marginTop:8}}>Запись разговора: {recordingOn ? '🔴 включена' : 'выключена'}</div>
          </div>
        </aside>
      </div>

      <footer className="muted" style={{textAlign:'center',marginTop:16}}>Данные из БД • Все взаимодействия сохраняются автоматически</footer>
    </div>
  );
}
