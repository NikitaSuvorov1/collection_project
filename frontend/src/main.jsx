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
import AdminCollectionPlanPage from './AdminCollectionPlanPage'
import './styles.css'

const SESSION_KEY = 'collection_user';
const NAV_STATE_KEY = 'collection_nav';
const SESSION_TIMEOUT = 10 * 60 * 1000; // 10 minutes in ms
const APP_NAME = 'ИС "Система ДРПЗ"';

function BrandPlaque() {
  return (
    <header className="app-brand-plaque">
      <div className="app-brand-plaque-inner">
        <div className="app-brand-main">
          <div className="app-brand-mark">ИС</div>
          <div className="app-brand-title">{APP_NAME}</div>
        </div>
        <div className="app-brand-code">ДРПЗ</div>
      </div>
    </header>
  );
}

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
  const [preOverdueContext, setPreOverdueContext] = useState(null);

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
    return (
      <div className="app-shell">
        <BrandPlaque />
        <LoginPage onLogin={handleLogin} />
      </div>
    );
  }

  const isAdmin = user.role === 'admin';
  const isManager = user.role === 'manager' || isAdmin;
  const roleLabel = isAdmin ? 'Администратор' : user.role === 'manager' ? 'Руководитель' : 'Оператор';

  return (
    <div className="app-shell">
      <BrandPlaque />
      <nav className="app-nav">
        <button className={`btn ${page === 'desk' ? '' : 'ghost'}`} onClick={() => setPage('desk')}> Рабочий стол</button>
        <button className={`btn ${page === 'credits' ? '' : 'ghost'}`} onClick={() => setPage('credits')}> Кредиты</button>
        <button className={`btn ${page === 'client360' ? '' : 'ghost'}`} onClick={() => setPage('client360')}> 360° Клиент</button>
        <button className={`btn ${page === 'prediction' ? '' : 'ghost'}`} onClick={() => setPage('prediction')}> Скоринг</button>
        <button className={`btn ${page === 'overdue' ? '' : 'ghost'}`} onClick={() => setPage('overdue')}> Просрочка</button>
        <button className={`btn ${page === 'training' ? '' : 'ghost'}`} onClick={() => setPage('training')}> Обучение</button>
        <button className={`btn ${page === 'loanTraining' ? '' : 'ghost'}`} onClick={() => setPage('loanTraining')}> Скоринг ML</button>
        <button className={`btn ${page === 'database' ? '' : 'ghost'}`} onClick={() => setPage('database')}> База данных</button>
        <button className={`btn ${page === 'mystats' ? '' : 'ghost'}`} onClick={() => setPage('mystats')}> Моя статистика</button>
        {isManager && <button className={`btn ${page === 'dashboard' ? '' : 'ghost'}`} onClick={() => setPage('dashboard')}> Дашборд</button>}
        {isAdmin && <button className={`btn ${page === 'adminPlan' ? '' : 'ghost'}`} onClick={() => setPage('adminPlan')}> План взыскания</button>}
        <div style={{flex:1}} />
        <span className="app-nav-user">{user.name} ({roleLabel})</span>
        <button className="btn small ghost" onClick={handleLogout}>Выход</button>
      </nav>
      <main className="page-content">
      {page === 'desk' && <Desk user={user} onClient360={handleClient360} onCreditClick={(id) => handleCreditClick(id, 'desk')} preOverdueContext={preOverdueContext} onClearPreOverdue={() => setPreOverdueContext(null)} />}
      {page === 'credits' && <CreditsPage onCreditClick={handleCreditClick} />}
      {page === 'creditDetail' && creditId && <CreditDetailPage creditId={creditId} onBack={handleBackToCredits} onClient360={handleClient360} />}
      {page === 'creditDetailFromDesk' && creditId && <CreditDetailPage creditId={creditId} onBack={() => { setCreditId(null); setPage('desk'); }} onClient360={handleClient360} />}
      {page === 'dashboard' && isManager && <DashboardPage />}
      {page === 'client360' && <Client360Page clientId={client360Id} onBack={handleBackFromClient360} />}
      {page === 'prediction' && <LoanPredictionPage />}
      {page === 'overdue' && <OverduePredictionPage onStartCall={(row) => {
        setPreOverdueContext(row);
        setPage('desk');
      }} onCreditClick={(id) => handleCreditClick(id, 'overdue')} />}
      {page === 'training' && <ModelTrainingPage />}
      {page === 'loanTraining' && <LoanTrainingPage />}
      {page === 'database' && <DatabaseViewPage />}
      {page === 'mystats' && <OperatorStatsPage user={user} onBack={() => setPage('desk')} />}
      {page === 'adminPlan' && <AdminCollectionPlanPage user={user} />}
      </main>
    </div>
  )
}

createRoot(document.getElementById('root')).render(<Root />)
