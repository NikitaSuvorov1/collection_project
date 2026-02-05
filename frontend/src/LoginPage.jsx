import React, { useState } from 'react';

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    // Mock authentication
    if (username === 'admin' && password === 'admin') {
      onLogin({ name: 'Администратор', role: 'manager' });
    } else if (username === 'iva' && password === 'iva') {
      onLogin({ name: 'Иванов И.И.', role: 'operator' });
    } else {
      setError('Неверный логин или пароль (admin/admin или iva/iva)');
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1 className="app-title" style={{textAlign:'center'}}>Вход в систему</h1>
        <form onSubmit={handleSubmit} style={{display:'flex', flexDirection:'column', gap:16}}>
          <div>
            <label style={{display:'block', marginBottom:4, fontSize:14}}>Логин</label>
            <input 
              className="search" 
              style={{width:'100%', boxSizing:'border-box'}}
              value={username} 
              onChange={e => setUsername(e.target.value)} 
              autoFocus
            />
          </div>
          <div>
            <label style={{display:'block', marginBottom:4, fontSize:14}}>Пароль</label>
            <input 
              type="password"
              className="search" 
              style={{width:'100%', boxSizing:'border-box'}}
              value={password} 
              onChange={e => setPassword(e.target.value)} 
            />
          </div>
          {error && <div className="error" style={{fontSize:14}}>{error}</div>}
          <button type="submit" className="btn large">Войти</button>
        </form>
        <div className="muted" style={{marginTop:16, textAlign:'center', fontSize:12}}>
          Для демо: admin/admin (Рук.) или iva/iva (Опер.)
        </div>
      </div>
    </div>
  );
}
