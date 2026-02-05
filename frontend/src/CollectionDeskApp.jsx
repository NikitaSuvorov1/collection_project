import React, { useEffect, useMemo, useState, useRef } from "react";

// --- Mock data ---
const MOCK_DEBTORS = [
  { id: "d1", name: "Иванов Иван", mainPhone: "+7 (912) 111-22-33", outstanding: 12500.5, daysPastDue: 45, lastContact: "2025-10-28", attempts: 2, psychotype: 'forgetful', psychotypeLabel: 'Забыл', riskSegment: 'medium' },
  { id: "d2", name: "Петров Пётр", mainPhone: "+7 (903) 444-55-66", outstanding: 5600, daysPastDue: 12, lastContact: "2025-11-05", attempts: 1, psychotype: 'cooperative', psychotypeLabel: 'Готов к диалогу', riskSegment: 'low' },
  { id: "d3", name: "Смирнова Ольга", mainPhone: "+7 (916) 777-88-99", outstanding: 30000, daysPastDue: 120, lastContact: "2025-09-12", attempts: 5, psychotype: 'unable', psychotypeLabel: 'Не может', riskSegment: 'high' },
];

// NBA рекомендации для каждого должника
const MOCK_NBA = {
  'd1': { channel: '📞 Звонок', scenario: 'Мягкое напоминание', offer: 'Без предложения', urgency: 2, confidence: 0.72, hint: 'Уверен, это просто упущение. Могу помочь с быстрой оплатой.' },
  'd2': { channel: '💬 WhatsApp', scenario: 'Стандартное сопровождение', offer: 'Без предложения', urgency: 1, confidence: 0.85, hint: 'Клиент контактный. Напомните о платеже, предложите удобный способ.' },
  'd3': { channel: '📞 Звонок', scenario: 'Реструктуризация', offer: 'Рассрочка 6 мес', urgency: 4, confidence: 0.68, hint: 'Клиент хочет платить, но не может. Предложите снизить платёж.' },
};

// Copilot-подсказки
const COPILOT_PHRASES = {
  'forgetful': ['Уверен, это просто упущение', 'Могу прямо сейчас отправить ссылку для оплаты', 'Давайте вместе посмотрим, как удобнее оплатить'],
  'cooperative': ['Ценю, что вы всегда на связи', 'Давайте найдём удобное решение', 'Спасибо за сотрудничество'],
  'unable': ['Понимаю, что сейчас сложно', 'У нас есть программа реструктуризации', 'Можем снизить ежемесячный платёж'],
  'unwilling': ['При дальнейшей просрочке будут начисляться пени', 'Предлагаю решить вопрос сейчас', 'Информация может быть передана в БКИ'],
  'toxic': ['Прошу отнестись к вопросу серьёзно', 'Это официальное уведомление', 'Готов выслушать вашу позицию'],
};

const MOCK_HISTORY = [
  { id: "i1", debtorId: "d1", channel: "phone", at: "2025-10-28T10:12:00Z", duration: 320, result: "no_answer", note: "Оставлено сообщение" },
  { id: "i2", debtorId: "d2", channel: "phone", at: "2025-11-05T14:20:00Z", duration: 120, result: "promise_to_pay", note: "Обещал заплатить 2025-11-10" },
  { id: "i3", debtorId: "d3", channel: "sms", at: "2025-09-12T09:00:00Z", result: "invalid_number", note: "Номер недоступен" },
];

const formatCurrency = (v) => v.toLocaleString("ru-RU", { style: "currency", currency: "RUB" });
const relativeDate = (iso) => (iso ? new Date(iso).toLocaleString() : "—");

const getRiskColor = (segment) => {
  const colors = { low: '#22c55e', medium: '#f59e0b', high: '#ef4444', critical: '#dc2626' };
  return colors[segment] || '#6b7280';
};

const getUrgencyLabel = (u) => {
  const labels = { 1: 'Низкая', 2: 'Средняя', 3: 'Повышенная', 4: 'Высокая', 5: 'Критическая' };
  return labels[u] || '';
};

export default function CollectionDeskApp({ onClient360 }) {
  const [queue, setQueue] = useState(MOCK_DEBTORS);
  const [selectedId, setSelectedId] = useState(MOCK_DEBTORS[0].id);
  const [history, setHistory] = useState(MOCK_HISTORY);
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [isCalling, setIsCalling] = useState(false);
  const [callStart, setCallStart] = useState(null);
  const [callTick, setCallTick] = useState(0);
  const [recordingOn, setRecordingOn] = useState(false);
  const [resultCode, setResultCode] = useState("no_answer");
  const [note, setNote] = useState("");
  const callTimerRef = useRef(null);

  const selected = useMemo(() => queue.find(d => d.id === selectedId) ?? null, [queue, selectedId]);
  const selectedHistory = useMemo(() => history.filter(h => h.debtorId === selectedId), [history, selectedId]);
  const selectedNBA = selected ? MOCK_NBA[selected.id] : null;
  const selectedCopilotPhrases = selected ? (COPILOT_PHRASES[selected.psychotype] || COPILOT_PHRASES['forgetful']) : [];

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
    const t = setInterval(() => {
      const id = `d${Date.now()}`;
      const newDebtor = { id, name: `Клиент ${id.slice(-4)}`, mainPhone: "+7 (900) 000-00-00", outstanding: Math.round(Math.random() * 50000), daysPastDue: Math.floor(Math.random() * 200), attempts: 0 };
      setQueue(q => [...q, newDebtor]);
    }, 30000);
    return () => clearInterval(t);
  }, []);

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
      // compute actual duration in seconds
      const durationSec = callStart ? Math.floor((Date.now() - callStart) / 1000) : 0;
      // stop timer immediately
      if (callTimerRef.current) { clearInterval(callTimerRef.current); callTimerRef.current = null; }
      setIsCalling(false);
      setRecordingOn(false);
      const interact = { id: `int_${Date.now()}`, debtorId: selected.id, channel: "phone", at: new Date().toISOString(), duration: durationSec, result: resultCode, note };
      setHistory(h => [interact, ...h]);
      setQueue(q => q.map(d => d.id === selected.id ? { ...d, attempts: d.attempts + 1, lastContact: new Date().toISOString() } : d));
      setCallStart(null);
      setCallTick(0);
    }
  }

  function saveResult() {
    if (!selected) return;
    const interact = { id: `int_${Date.now()}`, debtorId: selected.id, channel: "phone", at: new Date().toISOString(), result: resultCode, note };
    setHistory(h => [interact, ...h]);
    if (resultCode === "promise_to_pay") { setQueue(q => q.map(d => d.id === selected.id ? { ...d, outstanding: Math.max(0, d.outstanding - 1000) } : d)); }
    setNote("");
  }

  function goNext() { const idx = queue.findIndex(q => q.id === selectedId); const next = queue[idx + 1] ?? queue[0]; setSelectedId(next?.id ?? null); setResultCode("no_answer"); setNote(""); }

  const visible = queue.filter(d => {
    if (filter === "overdue30" && d.daysPastDue < 30) return false;
    if (filter === "high" && d.outstanding < 20000) return false;
    if (search && !( (d.name + ' ' + d.mainPhone).toLowerCase().includes(search.toLowerCase()) )) return false;
    return true;
  });

  return (
    <div className="container">
      <header style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
        <div style={{display:'flex',alignItems:'center',gap:12}}>
          <h1 className="app-title">Коллекторский рабочий стол</h1>
          <div className="muted">Оператор: <strong>Иванов</strong></div>
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
          <div className="clients-list">
            {visible.map(d => (
              <div key={d.id} className={`client-list-item ${d.id===selectedId ? 'selected' : ''}`} onClick={() => setSelectedId(d.id)}>
                <div className="cli-left">
                  <div className="cli-name">{d.name}</div>
                  <div className="cli-phone">{d.mainPhone}</div>
                </div>
                <div className="cli-right">
                  <div className="cli-amount">{formatCurrency(d.outstanding)}</div>
                  <div className="cli-days">{d.daysPastDue} дн.</div>
                </div>
                <div style={{width:'100%',fontSize:12,color:'#6b7280',marginTop:8}}>Попыток: {d.attempts} • Последний контакт: {relativeDate(d.lastContact)}</div>
              </div>
            ))}
          </div>
          <footer className="muted" style={{marginTop:12}}>Всего в очереди: {visible.length}</footer>
        </aside>

        <section className="center-col">
          {selected ? (
            <div className="detail-card">
              <div className="detail-top">
                <div>
                  <h2 style={{margin:0}}>{selected.name}</h2>
                  <div className="muted">Тел: {selected.mainPhone}</div>
                  <div style={{marginTop:8}}>Сумма: <strong>{formatCurrency(selected.outstanding)}</strong></div>
                  <div className="muted">Просрочка: {selected.daysPastDue} дней</div>
                </div>
                <div style={{textAlign:'right'}}>
                  <div style={{display:'inline-block',padding:'4px 12px',borderRadius:6,background:'#f3f4f6',marginBottom:8}}>
                    <span style={{fontSize:12,color:'#6b7280'}}>Психотип:</span>
                    <strong style={{marginLeft:6}}>{selected.psychotypeLabel}</strong>
                  </div>
                  <div>
                    <span style={{display:'inline-block',padding:'2px 8px',borderRadius:4,fontSize:11,fontWeight:600,background:getRiskColor(selected.riskSegment)+'20',color:getRiskColor(selected.riskSegment)}}>
                      {selected.riskSegment.toUpperCase()} РИСК
                    </span>
                  </div>
                  <button className="btn small ghost" style={{marginTop:8}} onClick={() => onClient360 && onClient360(selected.id)}>
                    👤 360° профиль
                  </button>
                </div>
              </div>
              
              {/* NBA Widget */}
              {selectedNBA && (
                <div style={{background:'#fffbeb',border:'1px solid #fcd34d',borderRadius:8,padding:12,marginTop:12}}>
                  <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:8}}>
                    <strong style={{color:'#b45309'}}>🎯 Next Best Action</strong>
                    <span style={{fontSize:11,color:'#6b7280'}}>{Math.round(selectedNBA.confidence*100)}% уверенность</span>
                  </div>
                  <div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:8,fontSize:13}}>
                    <div><span style={{color:'#6b7280'}}>Канал:</span> <strong>{selectedNBA.channel}</strong></div>
                    <div><span style={{color:'#6b7280'}}>Сценарий:</span> <strong>{selectedNBA.scenario}</strong></div>
                    <div><span style={{color:'#6b7280'}}>Предложение:</span> <strong>{selectedNBA.offer}</strong></div>
                  </div>
                  <div style={{fontSize:12,color:selectedNBA.urgency>=4?'#dc2626':'#6b7280',marginTop:6}}>
                    Срочность: {getUrgencyLabel(selectedNBA.urgency)}
                  </div>
                </div>
              )}

              <div className="detail-actions">
                <button className="btn large" onClick={() => { setSelectedId(selected.id); toggleCall(); }}>{isCalling ? 'Завершить звонок' : 'Позвонить'}</button>
                <button className="btn ghost" onClick={() => setResultCode('promise_to_pay')}>Зафиксировать обещание</button>
                <button className="btn ghost" onClick={() => setResultCode('no_answer')}>Пометить как не дозвон</button>
              </div>
              <div className="history">
                <h4>История взаимодействий</h4>
                {selectedHistory.map(h => (
                  <div key={h.id} className="history-item">{h.channel.toUpperCase()} — {relativeDate(h.at)} — Результат: {h.result} {h.note && <div style={{color:'#6b7280',fontSize:13}}>{h.note}</div>}</div>
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
            {selectedNBA && (
              <div style={{background:'#f0fdf4',border:'1px solid #86efac',borderRadius:8,padding:10,marginBottom:10}}>
                <div style={{fontSize:12,fontWeight:600,color:'#166534',marginBottom:6}}>🤖 Copilot подсказки:</div>
                <div style={{fontSize:13,fontStyle:'italic',color:'#374151',marginBottom:8}}>
                  "{selectedNBA.hint}"
                </div>
                <div style={{fontSize:11,color:'#6b7280'}}>Фразы для этого типа клиента:</div>
                {selectedCopilotPhrases.slice(0,2).map((phrase, i) => (
                  <div key={i} style={{fontSize:12,color:'#374151',padding:'4px 0',cursor:'pointer'}} 
                       onClick={() => navigator.clipboard.writeText(phrase)} title="Клик чтобы скопировать">
                    → {phrase}
                  </div>
                ))}
              </div>
            )}
            
            <div className="cti-row"><label>Результат звонка</label><select value={resultCode} onChange={e=>setResultCode(e.target.value)} style={{marginTop:8}}><option value="no_answer">Не дозвон</option><option value="promise_to_pay">Обещание оплатить</option><option value="decline">Отказ</option></select></div>
            <div className="cti-row"><label>Заметка</label><textarea value={note} onChange={e=>setNote(e.target.value)} style={{marginTop:8}} placeholder="Комментарий к звонку..." /></div>
            <div className="cti-actions"><button className="btn" onClick={saveResult}>Сохранить</button><button className="btn ghost" onClick={()=>setRecordingOn(r=>!r)}>{recordingOn? '⏹ Стоп запись' : '⏺ Запись'}</button></div>
            <div className="muted" style={{marginTop:8}}>Запись разговора: {recordingOn ? '🔴 включена' : 'выключена'}</div>
          </div>
        </aside>
      </div>

      <footer className="muted" style={{textAlign:'center',marginTop:16}}>MVP prototype — интеграция CTI / backend required for production</footer>
    </div>
  );
}
