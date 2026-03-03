import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000/api';

export default function LoginPage({ onLogin }) {
  const [operators, setOperators] = useState([]);
  const [selectedOperator, setSelectedOperator] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  // Load operators from DB
  useEffect(() => {
    loadOperators();
  }, []);

  const loadOperators = async () => {
    try {
      const res = await fetch(`${API_BASE}/operators/`);
      const data = await res.json();
      const ops = data.results || data;
      setOperators(ops);
      setLoading(false);
    } catch (err) {
      console.error('Failed to load operators:', err);
      // Fallback to mock data
      setOperators([
        { id: 1, full_name: 'Иванов Иван', role: 'operator' },
        { id: 2, full_name: 'Петрова Мария', role: 'operator' },
        { id: 3, full_name: 'Сидоров Алексей', role: 'senior_operator' },
      ]);
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    // Admin login — use first real operator ID for API calls
    if (selectedOperator === 'admin') {
      if (password === 'admin') {
        const firstOp = operators.length > 0 ? operators[0] : null;
        onLogin({ 
          id: firstOp ? firstOp.id : 51, 
          name: 'Администратор', 
          full_name: 'Администратор системы',
          role: 'manager' 
        });
        return;
      } else {
        setError('Неверный пароль');
        return;
      }
    }

    // Operator login (password = "1" for demo)
    const operator = operators.find(o => o.id === parseInt(selectedOperator));
    if (operator) {
      if (password === '1' || password === operator.id.toString()) {
        onLogin({
          id: operator.id,
          name: operator.full_name,
          full_name: operator.full_name,
          role: operator.role || 'operator'
        });
      } else {
        setError('Неверный пароль (подсказка: 1)');
      }
    } else {
      setError('Выберите оператора');
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
              Пользователь
            </label>
            {loading ? (
              <div className="muted">Загрузка операторов...</div>
            ) : (
              <select
                className="search"
                style={{ width: '100%', boxSizing: 'border-box', padding: '8px 12px' }}
                value={selectedOperator}
                onChange={e => setSelectedOperator(e.target.value)}
              >
                <option value="">-- Выберите --</option>
                <option value="admin">👑 Руководитель (admin)</option>
                <optgroup label="Операторы">
                  {operators.slice(0, 15).map(op => (
                    <option key={op.id} value={op.id}>
                      {op.full_name} {op.role === 'senior_operator' ? '(старший)' : ''}
                    </option>
                  ))}
                </optgroup>
              </select>
            )}
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
            <div className="error" style={{ fontSize: 14, color: '#ef4444' }}>
              {error}
            </div>
          )}
          
          <button type="submit" className="btn large" disabled={!selectedOperator}>
            Войти
          </button>
        </form>
        
        <div className="muted" style={{ marginTop: 20, textAlign: 'center', fontSize: 12 }}>
          <strong>Демо-доступ:</strong><br />
          Руководитель: admin / admin<br />
          Операторы: выберите из списка, пароль: 1
        </div>
      </div>
    </div>
  );
}
