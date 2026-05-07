import React, { useState } from 'react';

const API_BASE = 'http://localhost:8000/api';

const TRANSLIT = {
  'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh',
  'з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o',
  'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts',
  'ч':'ch','ш':'sh','щ':'shch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
};

function translit(str) {
  return str.toLowerCase().split('').map(c => TRANSLIT[c] ?? c).join('');
}

/** "Суворов Никита Дмитриевич" → "suvorovnd" */
function makeLogin(fullName) {
  const parts = (fullName || '').trim().split(/\s+/);
  if (parts.length < 2) return translit(parts[0] || '');
  const surname = translit(parts[0]);
  const initials = parts.slice(1).map(p => translit(p[0] || '')).join('');
  return surname + initials;
}

export default function LoginPage({ onLogin }) {
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!login.trim() || !password.trim()) {
      setError('Введите логин и пароль');
      return;
    }

    // Admin login
    if (login.trim().toLowerCase() === 'admin') {
      if (password === 'admin') {
        setLoading(true);
        try {
          const res = await fetch(`${API_BASE}/operators/`);
          const data = await res.json();
          const ops = data.results || data;
          const firstOp = ops.length > 0 ? ops[0] : null;
          onLogin({
            id: firstOp ? firstOp.id : 51,
            name: 'Администратор',
            full_name: 'Администратор системы',
            role: 'admin'
          });
        } catch {
          onLogin({ id: 51, name: 'Администратор', full_name: 'Администратор системы', role: 'admin' });
        } finally {
          setLoading(false);
        }
        return;
      } else {
        setError('Неверный пароль');
        return;
      }
    }

    // Operator login — search by full_name or ID
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/operators/`);
      const data = await res.json();
      const ops = data.results || data;
      const input = login.trim().toLowerCase();
      const operator = ops.find(o => {
        const genLogin = makeLogin(o.full_name);
        return genLogin === input || o.id.toString() === input;
      });

      if (!operator) {
        setError('Пользователь не найден');
        setLoading(false);
        return;
      }

      if (password === '1' || password === operator.id.toString()) {
        onLogin({
          id: operator.id,
          name: operator.full_name,
          full_name: operator.full_name,
          role: operator.role || 'operator'
        });
      } else {
        setError('Неверный пароль');
      }
    } catch {
      setError('Ошибка подключения к серверу');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1 className="app-title" style={{ textAlign: 'center', marginBottom: 8 }}>
          Система ДРПЗ
        </h1>
        <p className="muted" style={{ textAlign: 'center', marginBottom: 24 }}>
          Вход в систему управления взысканием
        </p>
        
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 14 }}>
              Логин
            </label>
            <input
              type="text"
              className="search"
              style={{ width: '100%', boxSizing: 'border-box' }}
              value={login}
              onChange={e => setLogin(e.target.value)}
              placeholder="suvorovnd"
              autoFocus
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 14 }}>
              Пароль
            </label>
            <input 
              type="password"
              className="search" 
              style={{ width: '100%', boxSizing: 'border-box' }}
              value={password} 
              onChange={e => setPassword(e.target.value)}
              placeholder="Введите пароль"
            />
          </div>
          
          {error && (
            <div className="error" style={{ fontSize: 14, color: 'var(--danger)' }}>
              {error}
            </div>
          )}
          
          <button type="submit" className="btn large" disabled={loading || !login.trim()}>
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  );
}
