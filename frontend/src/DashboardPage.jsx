import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const API_BASE = 'http://localhost:8000/api';

// ===== HELPER FUNCTIONS =====
function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}ч ${m}м`;
  return `${m}м ${s}с`;
}

function formatCurrency(value) {
  return value.toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 });
}

// ===== COMPONENTS =====

function StatCard({ title, value, sub, trend, color, icon }) {
  const trendColor = trend > 0 ? '#22c55e' : trend < 0 ? '#ef4444' : '#6b7280';
  const trendIcon = trend > 0 ? '↑' : trend < 0 ? '↓' : '';
  
  return (
    <div className="stat-card">
      <div className="stat-header">
        <span className="muted">{title}</span>
        {icon && <span className="stat-icon">{icon}</span>}
      </div>
      <div className="stat-value" style={{ color: color || '#e6edf3' }}>{value}</div>
      <div className="stat-footer">
        {sub && <span className="stat-sub">{sub}</span>}
        {trend !== undefined && (
          <span className="stat-trend" style={{ color: trendColor }}>
            {trendIcon} {Math.abs(trend)}%
          </span>
        )}
      </div>
    </div>
  );
}

function ChartCard({ title, children, height = 300 }) {
  return (
    <div className="chart-card">
      <h3 className="chart-title">{title}</h3>
      <div style={{ height }}>{children}</div>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 300 }}>
      <div style={{ width: 40, height: 40, border: '4px solid #30363d', borderTopColor: '#388bfd', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
      <p style={{ marginTop: 16, color: '#8b949e' }}>Загрузка данных из БД...</p>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function ErrorMessage({ message, onRetry }) {
  return (
    <div style={{ textAlign: 'center', padding: 40 }}>
      <p style={{ color: '#ef4444', fontSize: 16 }}>❌ {message}</p>
      {onRetry && (
        <button className="btn" onClick={onRetry} style={{ marginTop: 16 }}>Повторить</button>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const [period, setPeriod] = useState('day');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  // Загрузка данных из API
  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/dashboard/?period=${period}`);
      
      if (!response.ok) {
        throw new Error(`Ошибка сервера: ${response.status}`);
      }
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      setError(err.message || 'Не удалось загрузить данные. Проверьте, что сервер запущен.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [period]);

  // Render loading state
  if (loading) {
    return (
      <div className="container dashboard">
        <header className="dashboard-header">
          <div>
            <h1 className="app-title">Дашборд руководителя</h1>
            <div className="muted">Аналитика работы отдела взыскания</div>
          </div>
        </header>
        <LoadingSpinner />
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="container dashboard">
        <header className="dashboard-header">
          <div>
            <h1 className="app-title">Дашборд руководителя</h1>
            <div className="muted">Аналитика работы отдела взыскания</div>
          </div>
        </header>
        <ErrorMessage message={error} onRetry={fetchDashboardData} />
      </div>
    );
  }

  // Destructure data
  const { totals, operatorStats, dailyCalls, hourlyCalls, callResults, timeDistribution } = data || {};

  return (
    <div className="container dashboard">
      <header className="dashboard-header">
        <div>
          <h1 className="app-title">Дашборд руководителя</h1>
          <div className="muted">Аналитика работы отдела взыскания • Данные из БД</div>
        </div>
        <div className="period-selector">
          <button className={`btn small ${period === 'day' ? '' : 'ghost'}`} onClick={() => setPeriod('day')}>День</button>
          <button className={`btn small ${period === 'week' ? '' : 'ghost'}`} onClick={() => setPeriod('week')}>Неделя</button>
          <button className={`btn small ${period === 'month' ? '' : 'ghost'}`} onClick={() => setPeriod('month')}>Месяц</button>
        </div>
      </header>

      {/* Key Metrics - 6 columns */}
      <div className="stats-grid-6">
        <StatCard title="Всего звонков" value={totals?.calls || 0} icon="📞" />
        <StatCard title="Контактов" value={totals?.contacts || 0} sub={`${totals?.contactRate || 0}% контактность`} icon="✓" />
        <StatCard title="Ср. длительность" value={formatDuration(totals?.avgDuration || 0)} icon="⏱" />
        <StatCard title="Время на звонках" value={formatDuration((totals?.totalTime || 0) * 60)} color="#22c55e" icon="🎧" />
        <StatCard title="Время перерывов" value={formatDuration((totals?.breakTime || 0) * 60)} color="#f59e0b" icon="☕" />
        <StatCard title="Сумма PTP" value={formatCurrency(totals?.ptpAmount || 0)} color="#3b82f6" icon="💰" />
      </div>

      {/* Charts Row 1: Call dynamics + Results pie */}
      <div className="charts-grid-2">
        <ChartCard title="📈 Динамика звонков за период">
          <ResponsiveContainer>
            <AreaChart data={dailyCalls || []}>
              <defs>
                <linearGradient id="colorCalls" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorContacts" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#8b949e' }} stroke="#484f58" />
              <YAxis tick={{ fontSize: 11, fill: '#8b949e' }} stroke="#484f58" />
              <Tooltip contentStyle={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: 8, color: '#e6edf3' }} />
              <Legend />
              <Area type="monotone" dataKey="calls" name="Звонки" stroke="#3b82f6" fillOpacity={1} fill="url(#colorCalls)" />
              <Area type="monotone" dataKey="contacts" name="Контакты" stroke="#22c55e" fillOpacity={1} fill="url(#colorContacts)" />
              <Line type="monotone" dataKey="ptp" name="PTP" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="📊 Распределение результатов звонков">
          <ResponsiveContainer>
            <PieChart>
              <Pie
                data={callResults || []}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={2}
                dataKey="value"
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                labelLine={{ stroke: '#484f58' }}
              >
                {(callResults || []).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => `${value}%`} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Charts Row 2: Hourly + Time distribution */}
      <div className="charts-grid-2">
        <ChartCard title="⏰ Активность по часам дня">
          <ResponsiveContainer>
            <BarChart data={hourlyCalls || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
              <XAxis dataKey="hour" tick={{ fontSize: 11, fill: '#8b949e' }} stroke="#484f58" />
              <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#8b949e' }} stroke="#484f58" />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#8b949e' }} stroke="#484f58" domain={[0, 100]} />
              <Tooltip contentStyle={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: 8, color: '#e6edf3' }} />
              <Legend />
              <Bar yAxisId="left" dataKey="calls" name="Звонки" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              <Line yAxisId="right" type="monotone" dataKey="contactRate" name="Контактность %" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="⏱ Распределение рабочего времени">
          <ResponsiveContainer>
            <PieChart>
              <Pie
                data={timeDistribution || []}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={3}
                dataKey="value"
                label={({ name, value }) => `${name}: ${value}%`}
              >
                {(timeDistribution || []).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => `${value}%`} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Operator Performance Table */}
      <div className="credit-section" style={{ marginTop: 24 }}>
        <h3>📋 Детальная статистика по операторам</h3>
        {operatorStats && operatorStats.length > 0 ? (
          <div className="table-scroll">
            <table className="credit-table">
              <thead>
                <tr>
                  <th>Оператор</th>
                  <th style={{ textAlign: 'right' }}>Звонков</th>
                  <th style={{ textAlign: 'right' }}>Контактов</th>
                  <th style={{ textAlign: 'right' }}>Контактность</th>
                  <th style={{ textAlign: 'right' }}>Ср. длит.</th>
                  <th style={{ textAlign: 'right' }}>На звонках</th>
                  <th style={{ textAlign: 'right' }}>Перерывы</th>
                  <th style={{ textAlign: 'right' }}>PTP кол.</th>
                  <th style={{ textAlign: 'right' }}>PTP сумма</th>
                </tr>
              </thead>
              <tbody>
                {operatorStats.map(op => (
                  <tr key={op.id}>
                    <td><strong>{op.name}</strong></td>
                    <td style={{ textAlign: 'right' }}>{op.calls}</td>
                    <td style={{ textAlign: 'right' }}>{op.contacts}</td>
                    <td style={{ textAlign: 'right' }}>
                      <span className={`rate-badge ${op.contactRate >= 65 ? 'good' : op.contactRate >= 55 ? 'medium' : 'low'}`}>
                        {op.contactRate}%
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>{formatDuration(op.avgDuration)}</td>
                    <td style={{ textAlign: 'right' }}>{formatDuration(op.totalTime * 60)}</td>
                    <td style={{ textAlign: 'right' }}>{formatDuration(op.breakTime * 60)}</td>
                    <td style={{ textAlign: 'right' }}>{op.ptpCount}</td>
                    <td style={{ textAlign: 'right' }}><strong>{formatCurrency(op.ptpAmount)}</strong></td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr style={{ background: '#1c2128' }}>
                  <td><strong>Итого</strong></td>
                  <td style={{ textAlign: 'right' }}><strong>{totals?.calls || 0}</strong></td>
                  <td style={{ textAlign: 'right' }}><strong>{totals?.contacts || 0}</strong></td>
                  <td style={{ textAlign: 'right' }}><strong>{totals?.contactRate || 0}%</strong></td>
                  <td style={{ textAlign: 'right' }}><strong>{formatDuration(totals?.avgDuration || 0)}</strong></td>
                  <td style={{ textAlign: 'right' }}><strong>{formatDuration((totals?.totalTime || 0) * 60)}</strong></td>
                  <td style={{ textAlign: 'right' }}><strong>{formatDuration((totals?.breakTime || 0) * 60)}</strong></td>
                  <td style={{ textAlign: 'right' }}><strong>{totals?.ptpCount || 0}</strong></td>
                  <td style={{ textAlign: 'right' }}><strong>{formatCurrency(totals?.ptpAmount || 0)}</strong></td>
                </tr>
              </tfoot>
            </table>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: 40, background: '#1c2128', borderRadius: 8 }}>
            <p style={{ color: '#8b949e' }}>Нет данных по операторам.</p>
            <p style={{ color: '#484f58', fontSize: 14 }}>Запустите команду для заполнения БД:</p>
            <code style={{ background: '#21262d', padding: '4px 8px', borderRadius: 4 }}>python manage.py populate_dashboard_data</code>
          </div>
        )}
      </div>

      {/* Operator Comparison Chart */}
      {operatorStats && operatorStats.length > 0 && (
        <ChartCard title="👥 Сравнение операторов" height={280}>
          <ResponsiveContainer>
            <BarChart data={operatorStats} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#8b949e' }} stroke="#484f58" />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: '#8b949e' }} stroke="#484f58" width={100} />
              <Tooltip contentStyle={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: 8, color: '#e6edf3' }} />
              <Legend />
              <Bar dataKey="calls" name="Звонки" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              <Bar dataKey="contacts" name="Контакты" fill="#22c55e" radius={[0, 4, 4, 0]} />
              <Bar dataKey="ptpCount" name="PTP" fill="#f59e0b" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      )}
    </div>
  );
}
