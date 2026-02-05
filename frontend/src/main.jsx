import React, { useState, useEffect, useCallback } from 'react'
import { createRoot } from 'react-dom/client'
import Desk from './CollectionDeskApp'
import CreditsPage from './CreditsPage'
import CreditDetailPage from './CreditDetailPage'
import LoginPage from './LoginPage'
import DashboardPage from './DashboardPage'
import Client360Page from './Client360Page'
import LoanPredictionPage from './LoanPredictionPage'
import DatabaseViewPage from './DatabaseViewPage'
import './styles.css'

const SESSION_KEY = 'collection_user';
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
  const [page, setPage] = useState('desk');
  const [creditId, setCreditId] = useState(null);

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
    setPage('desk');
  };

  const handleCreditClick = (id) => {
    setCreditId(id);
    setPage('creditDetail');
  };

  const handleBackToCredits = () => {
    setCreditId(null);
    setPage('credits');
  };

  const handleClient360 = (clientId) => {
    setCreditId(clientId); // reuse for clientId
    setPage('client360');
  };

  const handleBackFromClient360 = () => {
    setCreditId(null);
    setPage('desk');
  };

  if (!user) {
    return <LoginPage onLogin={handleLogin} />;
  }

  const isManager = user.role === 'manager';

  return (
    <div>
      <nav style={{maxWidth:1400,margin:'16px auto',display:'flex',gap:12,alignItems:'center',padding:'0 16px'}}>
        <button className={`btn ${page === 'desk' ? '' : 'ghost'}`} onClick={() => setPage('desk')}>🏠 Рабочий стол</button>
        <button className={`btn ${page === 'credits' ? '' : 'ghost'}`} onClick={() => setPage('credits')}>💳 Кредиты</button>
        <button className={`btn ${page === 'client360' ? '' : 'ghost'}`} onClick={() => handleClient360(1)}>👤 360° Клиент</button>
        <button className={`btn ${page === 'prediction' ? '' : 'ghost'}`} onClick={() => setPage('prediction')}>🔮 Скоринг</button>
        <button className={`btn ${page === 'database' ? '' : 'ghost'}`} onClick={() => setPage('database')}>🗄️ База данных</button>
        {isManager && <button className={`btn ${page === 'dashboard' ? '' : 'ghost'}`} onClick={() => setPage('dashboard')}>📊 Дашборд</button>}
        <div style={{flex:1}} />
        <span className="muted" style={{fontSize:13}}>{user.name} ({user.role === 'manager' ? 'Руководитель' : 'Оператор'})</span>
        <button className="btn small ghost" onClick={handleLogout}>Выход</button>
      </nav>
      {page === 'desk' && <Desk onClient360={handleClient360} />}
      {page === 'credits' && <CreditsPage onCreditClick={handleCreditClick} />}
      {page === 'creditDetail' && creditId && <CreditDetailPage creditId={creditId} onBack={handleBackToCredits} />}
      {page === 'dashboard' && isManager && <DashboardPage />}
      {page === 'client360' && <Client360Page clientId={creditId} onBack={handleBackFromClient360} />}
      {page === 'prediction' && <LoanPredictionPage />}
      {page === 'database' && <DatabaseViewPage />}
    </div>
  )
}

createRoot(document.getElementById('root')).render(<Root />)
