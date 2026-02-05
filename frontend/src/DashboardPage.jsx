import React, { useState } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

// ===== MOCK DATA =====

// Daily call statistics
const DAILY_CALLS = [
  { date: '16.12', calls: 320, contacts: 185, ptp: 42 },
  { date: '17.12', calls: 345, contacts: 210, ptp: 55 },
  { date: '18.12', calls: 298, contacts: 165, ptp: 38 },
  { date: '19.12', calls: 412, contacts: 245, ptp: 62 },
  { date: '20.12', calls: 378, contacts: 220, ptp: 48 },
  { date: '23.12', calls: 356, contacts: 198, ptp: 51 },
  { date: '24.12', calls: 289, contacts: 155, ptp: 35 },
  { date: '25.12', calls: 125, contacts: 72, ptp: 18 },
  { date: '26.12', calls: 367, contacts: 212, ptp: 58 },
  { date: '27.12', calls: 398, contacts: 235, ptp: 61 },
  { date: '30.12', calls: 312, contacts: 178, ptp: 44 },
  { date: '31.12', calls: 156, contacts: 89, ptp: 22 },
  { date: '09.01', calls: 423, contacts: 256, ptp: 68 },
  { date: '10.01', calls: 445, contacts: 278, ptp: 72 },
  { date: '13.01', calls: 467, contacts: 289, ptp: 78 },
  { date: '14.01', calls: 489, contacts: 302, ptp: 85 },
  { date: '15.01', calls: 437, contacts: 250, ptp: 65 },
];

// Monthly aggregation
const MONTHLY_STATS = [
  { month: 'Авг', calls: 8234, contacts: 4856, ptp: 1245, ptpAmount: 12500000, avgDuration: 142 },
  { month: 'Сен', calls: 8567, contacts: 5123, ptp: 1389, ptpAmount: 14200000, avgDuration: 148 },
  { month: 'Окт', calls: 9012, contacts: 5467, ptp: 1523, ptpAmount: 15800000, avgDuration: 155 },
  { month: 'Ноя', calls: 8756, contacts: 5234, ptp: 1456, ptpAmount: 14900000, avgDuration: 151 },
  { month: 'Дек', calls: 7845, contacts: 4678, ptp: 1234, ptpAmount: 12100000, avgDuration: 145 },
  { month: 'Янв', calls: 4523, contacts: 2756, ptp: 756, ptpAmount: 7800000, avgDuration: 152 },
];

// Hourly distribution
const HOURLY_CALLS = [
  { hour: '09:00', calls: 45, avgDuration: 125, contactRate: 58 },
  { hour: '10:00', calls: 62, avgDuration: 142, contactRate: 65 },
  { hour: '11:00', calls: 58, avgDuration: 156, contactRate: 68 },
  { hour: '12:00', calls: 48, avgDuration: 138, contactRate: 62 },
  { hour: '13:00', calls: 35, avgDuration: 118, contactRate: 55 },
  { hour: '14:00', calls: 55, avgDuration: 148, contactRate: 67 },
  { hour: '15:00', calls: 65, avgDuration: 162, contactRate: 72 },
  { hour: '16:00', calls: 58, avgDuration: 155, contactRate: 69 },
  { hour: '17:00', calls: 52, avgDuration: 145, contactRate: 64 },
  { hour: '18:00', calls: 38, avgDuration: 128, contactRate: 58 },
];

// Operator statistics (extended)
const OPERATOR_STATS = [
  { id: 1, name: 'Иванов И.И.', calls: 145, contacts: 98, contactRate: 68, avgDuration: 165, totalTime: 398, breakTime: 45, ptpCount: 18, ptpAmount: 580000 },
  { id: 2, name: 'Петров П.П.', calls: 132, contacts: 82, contactRate: 62, avgDuration: 148, totalTime: 325, breakTime: 52, ptpCount: 14, ptpAmount: 420000 },
  { id: 3, name: 'Сидорова О.С.', calls: 168, contacts: 118, contactRate: 70, avgDuration: 172, totalTime: 438, breakTime: 38, ptpCount: 22, ptpAmount: 720000 },
  { id: 4, name: 'Козлов А.А.', calls: 98, contacts: 58, contactRate: 59, avgDuration: 135, totalTime: 220, breakTime: 68, ptpCount: 8, ptpAmount: 280000 },
  { id: 5, name: 'Новикова М.М.', calls: 156, contacts: 105, contactRate: 67, avgDuration: 158, totalTime: 412, breakTime: 42, ptpCount: 19, ptpAmount: 610000 },
];

// Call results distribution
const CALL_RESULTS = [
  { name: 'Не дозвон', value: 42, color: '#94a3b8' },
  { name: 'Обещание', value: 28, color: '#22c55e' },
  { name: 'Отказ', value: 15, color: '#ef4444' },
  { name: 'Перезвонить', value: 10, color: '#f59e0b' },
  { name: 'Оплачено', value: 5, color: '#3b82f6' },
];

// Time distribution by activity
const TIME_DISTRIBUTION = [
  { name: 'На звонке', value: 65, color: '#22c55e' },
  { name: 'Постобработка', value: 15, color: '#3b82f6' },
  { name: 'Ожидание', value: 12, color: '#f59e0b' },
  { name: 'Перерыв', value: 8, color: '#94a3b8' },
];

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
      <div className="stat-value" style={{ color: color || '#111827' }}>{value}</div>
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

export default function DashboardPage() {
  const [period, setPeriod] = useState('day');

  // Calculate totals
  const todayStats = OPERATOR_STATS.reduce((acc, op) => ({
    calls: acc.calls + op.calls,
    contacts: acc.contacts + op.contacts,
    totalTime: acc.totalTime + op.totalTime,
    breakTime: acc.breakTime + op.breakTime,
    ptpCount: acc.ptpCount + op.ptpCount,
    ptpAmount: acc.ptpAmount + op.ptpAmount,
  }), { calls: 0, contacts: 0, totalTime: 0, breakTime: 0, ptpCount: 0, ptpAmount: 0 });

  const avgDuration = Math.round(OPERATOR_STATS.reduce((acc, op) => acc + op.avgDuration, 0) / OPERATOR_STATS.length);
  const contactRate = Math.round((todayStats.contacts / todayStats.calls) * 100);

  return (
    <div className="container dashboard">
      <header className="dashboard-header">
        <div>
          <h1 className="app-title">Дашборд руководителя</h1>
          <div className="muted">Аналитика работы отдела взыскания</div>
        </div>
        <div className="period-selector">
          <button className={`btn small ${period === 'day' ? '' : 'ghost'}`} onClick={() => setPeriod('day')}>День</button>
          <button className={`btn small ${period === 'week' ? '' : 'ghost'}`} onClick={() => setPeriod('week')}>Неделя</button>
          <button className={`btn small ${period === 'month' ? '' : 'ghost'}`} onClick={() => setPeriod('month')}>Месяц</button>
        </div>
      </header>

      {/* Key Metrics - 6 columns */}
      <div className="stats-grid-6">
        <StatCard title="Всего звонков" value={todayStats.calls} trend={12} icon="📞" />
        <StatCard title="Контактов" value={todayStats.contacts} sub={`${contactRate}% контактность`} trend={8} icon="✓" />
        <StatCard title="Ср. длительность" value={formatDuration(avgDuration)} trend={5} icon="⏱" />
        <StatCard title="Время на звонках" value={formatDuration(todayStats.totalTime * 60)} color="#22c55e" icon="🎧" />
        <StatCard title="Время перерывов" value={formatDuration(todayStats.breakTime * 60)} color="#f59e0b" icon="☕" />
        <StatCard title="Сумма PTP" value={formatCurrency(todayStats.ptpAmount)} color="#3b82f6" trend={15} icon="💰" />
      </div>

      {/* Charts Row 1: Call dynamics + Results pie */}
      <div className="charts-grid-2">
        <ChartCard title="📈 Динамика звонков за период">
          <ResponsiveContainer>
            <AreaChart data={DAILY_CALLS}>
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
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#9ca3af" />
              <YAxis tick={{ fontSize: 11 }} stroke="#9ca3af" />
              <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: 8 }} />
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
                data={CALL_RESULTS}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={2}
                dataKey="value"
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                labelLine={{ stroke: '#9ca3af' }}
              >
                {CALL_RESULTS.map((entry, index) => (
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
            <BarChart data={HOURLY_CALLS}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="hour" tick={{ fontSize: 11 }} stroke="#9ca3af" />
              <YAxis yAxisId="left" tick={{ fontSize: 11 }} stroke="#9ca3af" />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} stroke="#9ca3af" domain={[0, 100]} />
              <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: 8 }} />
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
                data={TIME_DISTRIBUTION}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={3}
                dataKey="value"
                label={({ name, value }) => `${name}: ${value}%`}
              >
                {TIME_DISTRIBUTION.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => `${value}%`} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Monthly Trends */}
      <ChartCard title="📅 Тренды по месяцам" height={320}>
        <ResponsiveContainer>
          <LineChart data={MONTHLY_STATS}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="#9ca3af" />
            <YAxis yAxisId="left" tick={{ fontSize: 11 }} stroke="#9ca3af" />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} stroke="#9ca3af" tickFormatter={(v) => `${v}с`} />
            <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: 8 }} />
            <Legend />
            <Line yAxisId="left" type="monotone" dataKey="calls" name="Звонки" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
            <Line yAxisId="left" type="monotone" dataKey="contacts" name="Контакты" stroke="#22c55e" strokeWidth={2} dot={{ r: 4 }} />
            <Line yAxisId="left" type="monotone" dataKey="ptp" name="PTP" stroke="#f59e0b" strokeWidth={2} dot={{ r: 4 }} />
            <Line yAxisId="right" type="monotone" dataKey="avgDuration" name="Ср. длительность (сек)" stroke="#8b5cf6" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Operator Performance Table */}
      <div className="credit-section" style={{ marginTop: 24 }}>
        <h3>📋 Детальная статистика по операторам</h3>
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
              {OPERATOR_STATS.map(op => (
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
              <tr style={{ background: '#f8fafc' }}>
                <td><strong>Итого</strong></td>
                <td style={{ textAlign: 'right' }}><strong>{todayStats.calls}</strong></td>
                <td style={{ textAlign: 'right' }}><strong>{todayStats.contacts}</strong></td>
                <td style={{ textAlign: 'right' }}><strong>{contactRate}%</strong></td>
                <td style={{ textAlign: 'right' }}><strong>{formatDuration(avgDuration)}</strong></td>
                <td style={{ textAlign: 'right' }}><strong>{formatDuration(todayStats.totalTime * 60)}</strong></td>
                <td style={{ textAlign: 'right' }}><strong>{formatDuration(todayStats.breakTime * 60)}</strong></td>
                <td style={{ textAlign: 'right' }}><strong>{todayStats.ptpCount}</strong></td>
                <td style={{ textAlign: 'right' }}><strong>{formatCurrency(todayStats.ptpAmount)}</strong></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Operator Comparison Chart */}
      <ChartCard title="👥 Сравнение операторов" height={280}>
        <ResponsiveContainer>
          <BarChart data={OPERATOR_STATS} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis type="number" tick={{ fontSize: 11 }} stroke="#9ca3af" />
            <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} stroke="#9ca3af" width={100} />
            <Tooltip contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: 8 }} />
            <Legend />
            <Bar dataKey="calls" name="Звонки" fill="#3b82f6" radius={[0, 4, 4, 0]} />
            <Bar dataKey="contacts" name="Контакты" fill="#22c55e" radius={[0, 4, 4, 0]} />
            <Bar dataKey="ptpCount" name="PTP" fill="#f59e0b" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
