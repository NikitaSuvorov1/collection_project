import React, { useState, useEffect, useCallback } from 'react'
import { createRoot } from 'react-dom/client'
import Desk from './CollectionDeskApp'
import CreditsPage from './CreditsPage'
import CreditDetailPage from './CreditDetailPage'
import LoginPage from './LoginPage'
import DashboardPage from './DashboardPage'
import Client360Page from './Client360Page'
import LoanPredictionPage from './LoanPredictionPage'
import OverduePredictionPage from './OverduePredictionPage'
import ModelTrainingPage from './ModelTrainingPage'
import LoanTrainingPage from './LoanTrainingPage'
import DatabaseViewPage from './DatabaseViewPage'
import OperatorStatsPage from './OperatorStatsPage'
import './styles.css'

const SESSION_KEY = 'collection_user';
const NAV_STATE_KEY = 'collection_nav';
const SESSION_TIMEOUT = 10 * 60 * 1000; // 10 minutes in ms

function Root() {
  const [user, setUser] = useState(() => {
    // Load user from localStorage on init
    const saved = localStorage.getItem(SESSION_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // Check if session is still valid
        if (parsed.lastActivity && Date.now() - parsed.lastActivity < SESSION_TIMEOUT) {
          return parsed.user;
        } else {
          localStorage.removeItem(SESSION_KEY);
        }
      } catch (e) {
        localStorage.removeItem(SESSION_KEY);
      }
    }
    return null;
  });
  // Restore navigation state from localStorage
  const savedNav = (() => {
    try {
      const raw = localStorage.getItem(NAV_STATE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch { return {}; }
  })();

  const [page, setPageRaw] = useState(savedNav.page || 'desk');
  const [creditId, setCreditId] = useState(savedNav.creditId || null);
  const [client360Id, setClient360Id] = useState(savedNav.client360Id || null);

  // Update last activity in localStorage
  const updateActivity = useCallback(() => {
    if (user) {
      localStorage.setItem(SESSION_KEY, JSON.stringify({
        user,
        lastActivity: Date.now()
      }));
    }
  }, [user]);

  // Track user activity
  useEffect(() => {
    if (!user) return;

    const events = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'];
    
    // Throttle activity updates to avoid too many writes
    let lastUpdate = 0;
    const throttledUpdate = () => {
      const now = Date.now();
      if (now - lastUpdate > 30000) { // Update at most every 30 seconds
        lastUpdate = now;
        updateActivity();
      }
    };

    events.forEach(event => window.addEventListener(event, throttledUpdate, { passive: true }));
    
    // Initial activity mark
    updateActivity();

    // Check for session timeout every minute
    const intervalId = setInterval(() => {
      const saved = localStorage.getItem(SESSION_KEY);
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          if (Date.now() - parsed.lastActivity >= SESSION_TIMEOUT) {
            // Session expired
            localStorage.removeItem(SESSION_KEY);
            setUser(null);
          }
        } catch (e) {
          localStorage.removeItem(SESSION_KEY);
          setUser(null);
        }
      }
    }, 60000); // Check every minute

    return () => {
      events.forEach(event => window.removeEventListener(event, throttledUpdate));
      clearInterval(intervalId);
    };
  }, [user, updateActivity]);

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem(SESSION_KEY, JSON.stringify({
      user: userData,
      lastActivity: Date.now()
    }));
    setPage('desk');
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(NAV_STATE_KEY);
    setPage('desk');
    setCreditId(null);
    setClient360Id(null);
  };

  const handleCreditClick = (id, fromPage) => {
    setCreditId(id);
    setPrevPage(fromPage || page);
    setPage('creditDetail');
  };

  const [prevPage, setPrevPage] = useState(savedNav.prevPage || 'credits');

  const handleBackToCredits = () => {
    setCreditId(null);
    setPage(prevPage);
  };

  const handleClient360 = (clientId) => {
    setClient360Id(clientId);
    setPrevPageClient360(page);
    setPage('client360');
  };

  const [prevPageClient360, setPrevPageClient360] = useState(savedNav.prevPageClient360 || 'desk');

  // Persist navigation state to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem(NAV_STATE_KEY, JSON.stringify({
      page, creditId, client360Id, prevPage, prevPageClient360
    }));
  }, [page, creditId, client360Id, prevPage, prevPageClient360]);

  // Wrapper for setPage that also clears stale detail IDs
  const setPage = (newPage) => {
    setPageRaw(newPage);
  };

  const handleBackFromClient360 = () => {
    setClient360Id(null);
    setPage(prevPageClient360);
  };

  if (!user) {
    return <LoginPage onLogin={handleLogin} />;
  }

  const isManager = user.role === 'manager';

  return (
    <div>
      <nav style={{maxWidth:1400,margin:'0 auto',display:'flex',gap:8,alignItems:'center',padding:'12px 16px',borderBottom:'1px solid #30363d',background:'#161b22'}}>
        <button className={`btn ${page === 'desk' ? '' : 'ghost'}`} onClick={() => setPage('desk')}>🏠 Рабочий стол</button>
        <button className={`btn ${page === 'credits' ? '' : 'ghost'}`} onClick={() => setPage('credits')}>💳 Кредиты</button>
        <button className={`btn ${page === 'client360' ? '' : 'ghost'}`} onClick={() => setPage('client360')}>👤 360° Клиент</button>
        <button className={`btn ${page === 'prediction' ? '' : 'ghost'}`} onClick={() => setPage('prediction')}>🔮 Скоринг</button>
        <button className={`btn ${page === 'overdue' ? '' : 'ghost'}`} onClick={() => setPage('overdue')}>⚠️ Просрочка</button>
        <button className={`btn ${page === 'training' ? '' : 'ghost'}`} onClick={() => setPage('training')}>🧠 Обучение</button>
        <button className={`btn ${page === 'loanTraining' ? '' : 'ghost'}`} onClick={() => setPage('loanTraining')}>🏦 Скоринг ML</button>
        <button className={`btn ${page === 'database' ? '' : 'ghost'}`} onClick={() => setPage('database')}>🗄️ База данных</button>
        <button className={`btn ${page === 'mystats' ? '' : 'ghost'}`} onClick={() => setPage('mystats')}>📈 Моя статистика</button>
        {isManager && <button className={`btn ${page === 'dashboard' ? '' : 'ghost'}`} onClick={() => setPage('dashboard')}>📊 Дашборд</button>}
        <div style={{flex:1}} />
        <span style={{fontSize:13,color:'#8b949e'}}>{user.name} ({user.role === 'manager' ? 'Руководитель' : 'Оператор'})</span>
        <button className="btn small ghost" onClick={handleLogout}>Выход</button>
      </nav>
      {page === 'desk' && <Desk user={user} onClient360={handleClient360} onCreditClick={(id) => handleCreditClick(id, 'desk')} />}
      {page === 'credits' && <CreditsPage onCreditClick={handleCreditClick} />}
      {page === 'creditDetail' && creditId && <CreditDetailPage creditId={creditId} onBack={handleBackToCredits} onClient360={handleClient360} />}
      {page === 'creditDetailFromDesk' && creditId && <CreditDetailPage creditId={creditId} onBack={() => { setCreditId(null); setPage('desk'); }} onClient360={handleClient360} />}
      {page === 'dashboard' && isManager && <DashboardPage />}
      {page === 'client360' && <Client360Page clientId={client360Id} onBack={handleBackFromClient360} />}
      {page === 'prediction' && <LoanPredictionPage />}
      {page === 'overdue' && <OverduePredictionPage />}
      {page === 'training' && <ModelTrainingPage />}
      {page === 'loanTraining' && <LoanTrainingPage />}
      {page === 'database' && <DatabaseViewPage />}
      {page === 'mystats' && <OperatorStatsPage user={user} onBack={() => setPage('desk')} />}
    </div>
  )
}

createRoot(document.getElementById('root')).render(<Root />)
