import React, { useEffect, useState, useRef } from 'react'

const MOCK_ASSIGNMENTS = [
  { id: 1, client_name: 'Иванов Иван', client: { first_name: 'Иван', last_name: 'Иванов', phone: '+7 (912) 111-22-33', email: 'ivan@example.com' }, amount: '12 500,50 ₽', days: '45', attempts: 2, last_contact: '28.10.2025, 03:00:00' },
  { id: 2, client_name: 'Петров Пётр', client: { first_name: 'Пётр', last_name: 'Петров', phone: '+7 (903) 444-55-66', email: 'petr@example.com' }, amount: '5 600,00 ₽', days: '12', attempts: 1, last_contact: '05.11.2025, 03:00:00' },
  { id: 3, client_name: 'Смирнова Ольга', client: { first_name: 'Ольга', last_name: 'Смирнова', phone: '+7 (916) 777-88-99', email: 'olga@example.com' }, amount: '30 000,00 ₽', days: '120', attempts: 5, last_contact: '12.09.2025, 03:00:00' },
  { id: 4, client_name: 'Клиент 6604', client: { first_name: '', last_name: '', phone: '+7 (900) 000-00-00', email: '' }, amount: '13 978,00 ₽', days: '7', attempts: 0, last_contact: '' },
]

function ClientListItem({c, selected, onSelect}){
  return (
    <div className={`client-list-item ${selected ? 'selected' : ''}`} onClick={()=>onSelect(c)}>
      <div className="cli-left">
        <div className="cli-name">{c.client_name}</div>
        <div className="cli-phone">{c.client.phone}</div>
        <div className="cli-meta">Попыток: {c.attempts} • Последний контакт: {c.last_contact || '—'}</div>
      </div>
      <div className="cli-right">
        <div className="cli-amount">{c.amount}</div>
        <div className="cli-days">{c.days} дн.</div>
      </div>
    </div>
  )
}

export default function App(){
  const [assignments, setAssignments] = useState(MOCK_ASSIGNMENTS)
  const [selected, setSelected] = useState(MOCK_ASSIGNMENTS[0])
  const [query, setQuery] = useState('')
  const [callResult, setCallResult] = useState('no_answer')
  const [note, setNote] = useState('')
  const [seconds, setSeconds] = useState(0)
  const [timerRunning, setTimerRunning] = useState(false)
  const timerRef = useRef(null)

  useEffect(()=>{
    if(timerRunning){
      timerRef.current = setInterval(()=> setSeconds(s=>s+1), 1000)
    } else {
      clearInterval(timerRef.current)
    }
    return ()=> clearInterval(timerRef.current)
  },[timerRunning])

  const resetTimer = ()=>{ setSeconds(0); setTimerRunning(false) }

  const filtered = assignments.filter(a=>{
    const q = query.trim().toLowerCase()
    if(!q) return true
    return a.client_name.toLowerCase().includes(q) || (a.client.phone || '').includes(q)
  })

  return (
    <div>
      <div className="topbar">
        <div className="topbar-left">
          <div className="title">Коллекторский рабочий стол</div>
          <div className="operator">Оператор: <strong>Иванов</strong></div>
        </div>
        <div className="topbar-right">Горячие клавиши: N — след., C — звонок, S — сохранить</div>
      </div>

      <div className="operator-layout">
        <aside className="left-col">
          <div className="search-row">
            <input className="search" placeholder="Поиск по ФИО/телефону" value={query} onChange={e=>setQuery(e.target.value)} />
            <select>
              <option>Все</option>
            </select>
          </div>
          <div className="clients-list">
            {filtered.map(c=> (
              <ClientListItem key={c.id} c={c} selected={selected?.id===c.id} onSelect={setSelected} />
            ))}
          </div>
        </aside>

        <section className="center-col">
          {selected ? (
            <div className="detail-card">
              <div className="detail-top">
                <div>
                  <h3>{selected.client_name}</h3>
                  <div className="muted">Тел: {selected.client.phone || '—'}</div>
                </div>
                <div className="detail-right">
                  <div className="muted small">ID: d{selected.id}</div>
                  <div className="muted small">Попыток: {selected.attempts}</div>
                </div>
              </div>

              <div className="detail-amount-row">
                <div className="amount-big">Сумма: <span className="amount">{selected.amount}</span></div>
                <div className="muted small">Просрочка: {selected.days} дней</div>
              </div>

              <div className="detail-actions">
                <button className="btn large" onClick={()=> setTimerRunning(true)}>Позвонить</button>
                <button className="btn ghost">Зафиксировать обещание</button>
                <button className="btn ghost">Пометить как не дозвон</button>
              </div>

              <div className="history">
                <h4>История взаимодействий</h4>
                <div className="history-item">PHONE — Результат: promise_to_pay
                  <div className="muted small">05.11.2025, 17:20:00 — Обещал заплатить 2025-11-10</div>
                </div>
              </div>
            </div>
          ) : <div className="muted">Выберите клиента</div>}
        </section>

        <aside className="right-col">
          <div className="cti-card">
            <div className="cti-row status-row"><div className="muted">CTI статус:</div><div className="cti-status">Готов</div></div>
            <div className="cti-row timer-row">
              <div className="muted">Таймер:</div>
              <div className="timer">{String(Math.floor(seconds/60)).padStart(2,'0')}:{String(seconds%60).padStart(2,'0')}</div>
            </div>
            <div className="cti-row">
              <div className="muted">Сценарий разговора</div>
              <textarea className="script" value={"Приветствие: Добрый день, меня зовут Иван. Мы звоним по просрочке по вашему займу.\n\nЦель: Согласовать план платежа или уточнить контактные данные."} readOnly />
            </div>
            <div className="cti-row">
              <label>Результат звонка</label>
              <select value={callResult} onChange={e=>setCallResult(e.target.value)}>
                <option value="no_answer">Не дозвон</option>
                <option value="promise_to_pay">Обещание</option>
                <option value="paid">Оплата</option>
              </select>
            </div>
            <div className="cti-row">
              <label>Заметка / примерный текст</label>
              <textarea value={note} onChange={e=>setNote(e.target.value)} />
            </div>
            <div className="cti-actions">
              <button className="btn" onClick={()=>{ alert('Сохранено'); resetTimer() }}>Сохранить</button>
              <button className="btn ghost" onClick={()=>{ setTimerRunning(false); resetTimer() }}>Сброс</button>
            </div>
          </div>
        </aside>
      </div>

      <div className="footer-note">MVP prototype — интеграция CTI / backend required for production</div>
    </div>
  )
}
import React, {useEffect, useState, useRef} from 'react'

function ClientCard({item}){
  return (
    <div className="client-card">
      <div className="client-title">{item.client_name || `${item.client?.first_name || ''} ${item.client?.last_name || ''}`}</div>
      <div className="client-meta">Phone: {item.client?.phone || '-'}</div>
      <div className="client-meta">Email: {item.client?.email || '-'}</div>
      <div className="client-actions">
        <button className="btn small">Call</button>
        <button className="btn small ghost">SMS</button>
      </div>
    </div>
  )
}

const MOCK_ASSIGNMENTS = [
  { id: 1, client_name: 'Иванов Иван', client: { first_name: 'Иван', last_name: 'Иванов', phone: '+7 (912) 111-22-33', email: 'ivan@example.com' }, amount: '12 500,50 ₽', days: '45', attempts: 2, last_contact: '28.10.2025, 03:00:00' },
  { id: 2, client_name: 'Петров Пётр', client: { first_name: 'Пётр', last_name: 'Петров', phone: '+7 (903) 444-55-66', email: 'petr@example.com' }, amount: '5 600,00 ₽', days: '12', attempts: 1, last_contact: '05.11.2025, 03:00:00' },
  { id: 3, client_name: 'Смирнова Ольга', client: { first_name: 'Ольга', last_name: 'Смирнова', phone: '+7 (916) 777-88-99', email: 'olga@example.com' }, amount: '30 000,00 ₽', days: '120', attempts: 5, last_contact: '12.09.2025, 03:00:00' },
  { id: 4, client_name: 'Клиент 6604', client: { first_name: '', last_name: '', phone: '+7 (900) 000-00-00', email: '' }, amount: '13 978,00 ₽', days: '7', attempts: 0, last_contact: '' },
]

  return (
    <div>
      <div className="topbar">
        <div className="topbar-left">
          <div className="title">Коллекторский рабочий стол</div>
          <div className="operator">Оператор: <strong>Иванов</strong></div>
        </div>
        <div className="topbar-right">Горячие клавиши: N — след., C — звонок, S — сохранить</div>
      </div>

      <div className="operator-layout">
  const [loading, setLoading] = useState(true) 
        <div className="search-row">
          <input className="search" placeholder="Поиск по ФИО/телефону" value={query} onChange={e=>setQuery(e.target.value)} />
          <select value={filter} onChange={e=>setFilter(e.target.value)}>
            <option value="all">Все</option>
          </select>
        </div>
        <div className="clients-list">
          {list.map(c => (
            <ClientListItem key={c.id} c={c} selected={selected?.id===c.id} onSelect={(it)=>setSelected(it)} />
          ))}
        </div>
      try{
        const token = localStorage.getItem('token')
        {selected ? (
          <div className="detail-card">
            <div className="detail-top">
              <div>
                <h3>{selected.client_name}</h3>
                <div className="muted">Тел: {selected.client.phone || '—'}</div>
              </div>
              <div className="detail-right">
                <div className="muted small">ID: d{selected.id}</div>
                <div className="muted small">Попыток: {selected.attempts}</div>
              </div>
            </div>
            <div className="detail-amount-row">
              <div className="amount-big">Сумма: <span className="amount">{selected.amount}</span></div>
              <div className="muted small">Просрочка: {selected.days} дней</div>
            </div>
            <div className="detail-actions">
              <button className="btn large" onClick={()=>{ setTimerRunning(true) }}>Позвонить</button>
              <button className="btn ghost">Зафиксировать обещание</button>
              <button className="btn ghost">Пометить как не дозвон</button>
            </div>
            <div className="history">
              <h4>История взаимодействий</h4>
              <div className="history-item">PHONE — Результат: promise_to_pay
                <div className="muted small">05.11.2025, 17:20:00 — Обещал заплатить 2025-11-10</div>
              </div>
            </div>
          </div>
        ) : <div className="muted">Выберите клиента</div>}
      <header className="op-header">
        <h2>Оператор — личный список</h2>
        <div className="cti-card">
          <div className="cti-row status-row"><div className="muted">CTI статус:</div><div className="cti-status">Готов</div></div>
          <div className="cti-row timer-row">
            <div className="muted">Таймер:</div>
            <div className="timer">{String(Math.floor(seconds/60)).padStart(2,'0')}:{String(seconds%60).padStart(2,'0')}</div>
          </div>
          <div className="cti-row">
            <div className="muted">Сценарий разговора</div>
            <textarea className="script" value={"Приветствие: Добрый день, меня зовут Иван. Мы звоним по просрочке по вашему займу.\n\nЦель: Согласовать план платежа или уточнить контактные данные."} readOnly />
          </div>
          <div className="cti-row">
            <label>Результат звонка</label>
            <select value={callResult} onChange={e=>setCallResult(e.target.value)}>
              <option value="no_answer">Не дозвон</option>
              <option value="promise_to_pay">Обещание</option>
              <option value="paid">Оплата</option>
            </select>
          </div>
          <div className="cti-row">
            <label>Заметка / примерный текст</label>
            <textarea value={note} onChange={e=>setNote(e.target.value)} />
          </div>
          <div className="cti-actions">
            <button className="btn" onClick={()=>{ alert('Сохранено'); resetTimer() }}>Сохранить</button>
            <button className="btn ghost" onClick={()=>{ setTimerRunning(false); resetTimer() }}>Сброс</button>
          </div>
        </div>
    </div>
  )
    <div className="footer-note">MVP prototype — интеграция CTI / backend required for production</div>
    </div>
}
export default function App(){
  // No login screen for now — show operator view directly
  return (
    <div className="container">
      <h1 className="app-title">Collection App — Оператор</h1>
      <OperatorDashboard />
    </div>
  )
}
