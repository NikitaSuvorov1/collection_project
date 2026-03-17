import React, { useState, useEffect, useCallback } from 'react';

const API_URL = 'http://127.0.0.1:8000/api';

const fmt = (v) => Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' \u20BD';
const fmtDate = (d) => d ? new Date(d + 'T00:00:00').toLocaleDateString('ru-RU') : '\u2014';

function getRiskColor(cat) {
  if (cat === 0) return '#22c55e';
  if (cat === 1) return '#eab308';
  return '#ef4444';
}
function getRiskBg(cat) {
  if (cat === 0) return '#14532d';
  if (cat === 1) return '#422006';
  return '#7f1d1d';
}

function ComplianceBadge({ data, type }) {
  const label = type === 'phone' ? '\u0417\u0432\u043e\u043d\u043e\u043a' : '\u0421\u041c\u0421';
  if (!data) return null;
  const allowed = data.allowed;
  return (
    <span
      title={data.reason || (allowed ? '\u041a\u043e\u043d\u0442\u0430\u043a\u0442 \u0440\u0430\u0437\u0440\u0435\u0448\u0451\u043d' : '\u041a\u043e\u043d\u0442\u0430\u043a\u0442 \u0437\u0430\u043f\u0440\u0435\u0449\u0451\u043d')}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        padding: '3px 8px', borderRadius: 4, fontSize: '0.75rem', fontWeight: 600,
        background: allowed ? '#14532d' : '#7f1d1d',
        color: allowed ? '#86efac' : '#fca5a5',
        cursor: 'default',
      }}
    >
      {allowed ? '\u2713' : '\u2717'} {label}
    </span>
  );
}

function ActionPanel({ row, onAction }) {
  if (!row) return null;

  const phoneOk = row.phone?.allowed;
  const smsOk = row.sms?.allowed;

  return (
    <div style={{
      background: '#161b22', border: '1px solid #30363d', borderRadius: 10, padding: 16,
    }}>
      <h3 style={{ margin: '0 0 12px', fontSize: 15, borderBottom: '1px solid #30363d', paddingBottom: 8 }}>
        {'\u0414\u0435\u0439\u0441\u0442\u0432\u0438\u044f (230-\u0424\u0417)'}
      </h3>

      {/* Phone */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>{'\u0417\u0432\u043e\u043d\u043e\u043a'}</div>
        {phoneOk ? (
          <button
            className="btn"
            style={{ fontSize: 13, width: '100%' }}
            onClick={() => onAction(row, 'phone')}
          >
            {'\u041f\u043e\u0437\u0432\u043e\u043d\u0438\u0442\u044c \u043a\u043b\u0438\u0435\u043d\u0442\u0443'}
          </button>
        ) : (
          <div style={{ background: '#1c1917', border: '1px solid #7f1d1d', borderRadius: 6, padding: 10, fontSize: 12 }}>
            <div style={{ color: '#fca5a5', fontWeight: 600, marginBottom: 4 }}>{'\u0417\u0432\u043e\u043d\u043e\u043a \u0437\u0430\u043f\u0440\u0435\u0449\u0451\u043d'}</div>
            {(row.phone?.violations || []).map((v, i) => (
              <div key={i} style={{ color: '#a8a29e', marginTop: 2 }}>{v}</div>
            ))}
          </div>
        )}
        {row.phone?.counts && (
          <div style={{ fontSize: 11, color: '#6b7280', marginTop: 4 }}>
            {'\u0417\u0432\u043e\u043d\u043a\u043e\u0432'}: {row.phone.counts.day}/{row.phone.limits.day} {'\u0437\u0430 \u0434\u0435\u043d\u044c'},{' '}
            {row.phone.counts.week}/{row.phone.limits.week} {'\u0437\u0430 \u043d\u0435\u0434\u0435\u043b\u044e'},{' '}
            {row.phone.counts.month}/{row.phone.limits.month} {'\u0437\u0430 \u043c\u0435\u0441\u044f\u0446'}
          </div>
        )}
      </div>

      {/* SMS */}
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>{'\u0421\u041c\u0421'}</div>
        {smsOk ? (
          <button
            className="btn"
            style={{ fontSize: 13, width: '100%' }}
            onClick={() => onAction(row, 'sms')}
          >
            {'\u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u0421\u041c\u0421'}
          </button>
        ) : (
          <div style={{ background: '#1c1917', border: '1px solid #7f1d1d', borderRadius: 6, padding: 10, fontSize: 12 }}>
            <div style={{ color: '#fca5a5', fontWeight: 600, marginBottom: 4 }}>{'\u0421\u041c\u0421 \u0437\u0430\u043f\u0440\u0435\u0449\u0435\u043d\u043e'}</div>
            {(row.sms?.violations || []).map((v, i) => (
              <div key={i} style={{ color: '#a8a29e', marginTop: 2 }}>{v}</div>
            ))}
          </div>
        )}
        {row.sms?.counts && (
          <div style={{ fontSize: 11, color: '#6b7280', marginTop: 4 }}>
            {'\u0421\u041c\u0421'}: {row.sms.counts.day}/{row.sms.limits.day} {'\u0437\u0430 \u0434\u0435\u043d\u044c'},{' '}
            {row.sms.counts.week}/{row.sms.limits.week} {'\u0437\u0430 \u043d\u0435\u0434\u0435\u043b\u044e'},{' '}
            {row.sms.counts.month}/{row.sms.limits.month} {'\u0437\u0430 \u043c\u0435\u0441\u044f\u0446'}
          </div>
        )}
      </div>

      {/* 230-FZ checks summary */}
      <div style={{ marginTop: 14, borderTop: '1px solid #30363d', paddingTop: 10 }}>
        <div style={{ fontSize: 12, color: '#8b949e', marginBottom: 6 }}>{'\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 230-\u0424\u0417'}</div>
        {row.phone?.checks && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, fontSize: 11 }}>
            {[
              ['bankruptcy', '\u0411\u0430\u043d\u043a\u0440\u043e\u0442\u0441\u0442\u0432\u043e (\u0441\u0442.7)', true],
              ['refused', '\u041e\u0442\u043a\u0430\u0437 (\u0441\u0442.3)', true],
              ['time_ok', '\u0412\u0440\u0435\u043c\u044f (\u0441\u0442.1)', false],
              ['frequency_ok', '\u0427\u0430\u0441\u0442\u043e\u0442\u0430 (\u0441\u0442.2)', false],
              ['interval_ok', '\u0418\u043d\u0442\u0435\u0440\u0432\u0430\u043b (\u0441\u0442.9)', false],
              ['third_party_ok', '\u0422\u0440\u0435\u0442\u044c\u0438 \u043b\u0438\u0446\u0430 (\u0441\u0442.4)', false],
            ].map(([key, label, inverted]) => {
              const val = row.phone.checks[key];
              if (val === undefined) return null;
              const ok = inverted ? !val : val;
              return (
                <span key={key} style={{
                  padding: '2px 6px', borderRadius: 3,
                  background: ok ? '#14532d' : '#7f1d1d',
                  color: ok ? '#86efac' : '#fca5a5',
                }}>
                  {ok ? '\u2713' : '\u2717'} {label}
                </span>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default function OverduePredictionPage({ onStartCall, onCreditClick }) {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [daysAhead, setDaysAhead] = useState(14);
  const [riskFilter, setRiskFilter] = useState('all');
  const [actionMsg, setActionMsg] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_URL}/pre-overdue/?days_ahead=${daysAhead}&limit=50`);
      if (!resp.ok) throw new Error(`\u041e\u0448\u0438\u0431\u043a\u0430 \u0441\u0435\u0440\u0432\u0435\u0440\u0430: ${resp.status}`);
      const data = await resp.json();
      setResults(data.results || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [daysAhead]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const filtered = results.filter(r => {
    if (riskFilter === 'high') return r.risk_category === 2;
    if (riskFilter === 'medium') return r.risk_category === 1;
    if (riskFilter === 'low') return r.risk_category === 0;
    return true;
  });

  const stats = {
    total: results.length,
    high: results.filter(r => r.risk_category === 2).length,
    medium: results.filter(r => r.risk_category === 1).length,
    low: results.filter(r => r.risk_category === 0).length,
    upcoming: results.filter(r => r.days_to_payment !== null && r.days_to_payment <= 7).length,
    phoneBlocked: results.filter(r => !r.phone?.allowed).length,
  };

  const handleAction = async (row, type) => {
    // Phone call -> navigate to operator desk with pre-overdue reminder script
    if (type === 'phone' && onStartCall) {
      onStartCall(row);
      return;
    }
    try {
      const resp = await fetch(`${API_URL}/interventions/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client: row.client_id,
          credit: row.credit_id,
          intervention_type: type,
          status: type === 'sms' ? 'completed' : 'no_answer',
          datetime: new Date().toISOString(),
          notes: `\u041f\u0440\u0435\u0432\u0435\u043d\u0442\u0438\u0432\u043d\u044b\u0439 \u043a\u043e\u043d\u0442\u0430\u043a\u0442 (pre-overdue). \u0420\u0438\u0441\u043a: ${row.risk_label} (${(row.risk_score * 100).toFixed(0)}%)`,
          caller_number: '+74951234567',
          operator_identified: true,
          approved_script_used: true,
        }),
      });
      if (resp.ok) {
        setActionMsg({ type: 'ok', text: type === 'sms' ? '\u0421\u041c\u0421 \u0437\u0430\u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0438\u0440\u043e\u0432\u0430\u043d\u043e' : '\u0417\u0432\u043e\u043d\u043e\u043a \u0437\u0430\u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0438\u0440\u043e\u0432\u0430\u043d' });
        fetchData();
      } else {
        const d = await resp.json().catch(() => ({}));
        setActionMsg({ type: 'err', text: d.detail || `\u041e\u0448\u0438\u0431\u043a\u0430: ${resp.status}` });
      }
    } catch (e) {
      setActionMsg({ type: 'err', text: e.message });
    }
    setTimeout(() => setActionMsg(null), 4000);
  };

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '16px 20px' }}>
      <h1 style={{ fontSize: 22, margin: '0 0 4px' }}>{'\u041f\u0440\u0435\u0434\u0438\u043a\u0442\u0438\u0432\u043d\u044b\u0439 \u043c\u043e\u043d\u0438\u0442\u043e\u0440\u0438\u043d\u0433 \u043f\u0440\u043e\u0441\u0440\u043e\u0447\u043a\u0438'}</h1>
      <p style={{ color: '#8b949e', fontSize: 13, margin: '0 0 16px' }}>
        {'\u041f\u0440\u043e\u0433\u043d\u043e\u0437 \u0432\u044b\u0445\u043e\u0434\u0430 \u043d\u0430 \u043f\u0440\u043e\u0441\u0440\u043e\u0447\u043a\u0443 \u0441 \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u0435\u043c 230-\u0424\u0417'}
      </p>

      {/* Summary cards */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
        {[
          { label: '\u0412\u0441\u0435\u0433\u043e \u043a\u0440\u0435\u0434\u0438\u0442\u043e\u0432', value: stats.total, color: '#e6edf3' },
          { label: '\u0412\u044b\u0441\u043e\u043a\u0438\u0439 \u0440\u0438\u0441\u043a', value: stats.high, color: '#ef4444' },
          { label: '\u0421\u0440\u0435\u0434\u043d\u0438\u0439 \u0440\u0438\u0441\u043a', value: stats.medium, color: '#eab308' },
          { label: '\u041d\u0438\u0437\u043a\u0438\u0439 \u0440\u0438\u0441\u043a', value: stats.low, color: '#22c55e' },
          { label: '\u041f\u043b\u0430\u0442\u0451\u0436 <= 7 \u0434\u043d.', value: stats.upcoming, color: '#3b82f6' },
          { label: '\u0417\u0432\u043e\u043d\u043e\u043a \u0437\u0430\u043f\u0440\u0435\u0449\u0451\u043d', value: stats.phoneBlocked, color: '#f97316' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{
            background: '#161b22', border: '1px solid #30363d', borderRadius: 8,
            padding: '10px 16px', flex: '1 1 140px', minWidth: 130,
          }}>
            <div style={{ fontSize: 11, color: '#8b949e' }}>{label}</div>
            <div style={{ fontSize: 24, fontWeight: 700, color }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Controls */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }}>
        <label style={{ fontSize: 13, color: '#8b949e', display: 'flex', alignItems: 'center', gap: 6 }}>
          {'\u0413\u043e\u0440\u0438\u0437\u043e\u043d\u0442 (\u0434\u043d\u0435\u0439)'}:
          <select
            value={daysAhead}
            onChange={e => setDaysAhead(Number(e.target.value))}
            style={{ padding: '4px 8px', background: '#161b22', border: '1px solid #30363d', borderRadius: 6, color: '#e6edf3' }}
          >
            <option value={7}>7</option>
            <option value={14}>14</option>
            <option value={30}>30</option>
            <option value={60}>60</option>
          </select>
        </label>
        <div style={{ display: 'flex', gap: 4 }}>
          {[
            { key: 'all', label: '\u0412\u0441\u0435' },
            { key: 'high', label: '\u0412\u044b\u0441\u043e\u043a\u0438\u0439' },
            { key: 'medium', label: '\u0421\u0440\u0435\u0434\u043d\u0438\u0439' },
            { key: 'low', label: '\u041d\u0438\u0437\u043a\u0438\u0439' },
          ].map(f => (
            <button
              key={f.key}
              className={`btn ${riskFilter === f.key ? '' : 'ghost'}`}
              style={{ fontSize: 12, padding: '4px 10px' }}
              onClick={() => setRiskFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <button className="btn" style={{ fontSize: 12, marginLeft: 'auto' }} onClick={fetchData} disabled={loading}>
          {loading ? '\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430...' : '\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c'}
        </button>
      </div>

      {error && (
        <div style={{ background: '#7f1d1d', color: '#fca5a5', padding: '8px 14px', borderRadius: 8, marginBottom: 12, fontSize: 13 }}>
          {error}
        </div>
      )}

      {actionMsg && (
        <div style={{
          background: actionMsg.type === 'ok' ? '#14532d' : '#7f1d1d',
          color: actionMsg.type === 'ok' ? '#86efac' : '#fca5a5',
          padding: '8px 14px', borderRadius: 8, marginBottom: 12, fontSize: 13,
        }}>
          {actionMsg.text}
        </div>
      )}

      {/* Main: table + detail */}
      <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 380px' : '1fr', gap: 16, alignItems: 'start' }}>
        {/* Table */}
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 10, overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#0d1117' }}>
                  {['#', '\u041a\u043b\u0438\u0435\u043d\u0442', '\u041f\u0440\u043e\u0434\u0443\u043a\u0442', '\u041f\u043b\u0430\u0442\u0451\u0436', '\u0414\u0430\u0442\u0430 \u043f\u043b\u0430\u0442\u0435\u0436\u0430', '\u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c \u0434\u043d.', '\u0414\u043e\u043b\u0433', 'DPD', '\u0420\u0438\u0441\u043a', '\u041a\u043e\u043d\u0442\u0430\u043a\u0442'].map(h => (
                    <th key={h} style={{ padding: '8px 10px', textAlign: 'left', color: '#8b949e', fontWeight: 600, borderBottom: '2px solid #30363d', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr><td colSpan={10} style={{ padding: 30, textAlign: 'center', color: '#8b949e' }}>{'\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u0434\u0430\u043d\u043d\u044b\u0445...'}</td></tr>
                )}
                {!loading && filtered.length === 0 && (
                  <tr><td colSpan={10} style={{ padding: 30, textAlign: 'center', color: '#6b7280' }}>{'\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445'}</td></tr>
                )}
                {!loading && filtered.map((r, i) => {
                  const isSelected = selected?.credit_id === r.credit_id;
                  const paymentSoon = r.days_to_payment !== null && r.days_to_payment <= 3;
                  return (
                    <tr
                      key={r.credit_id}
                      onClick={() => setSelected(isSelected ? null : r)}
                      style={{
                        cursor: 'pointer',
                        background: isSelected ? '#1c2541' : 'transparent',
                        borderBottom: '1px solid #21262d',
                      }}
                    >
                      <td style={tdS}>{i + 1}</td>
                      <td style={tdS}>
                        <div style={{ fontWeight: 500 }}>{r.client_name}</div>
                        <div style={{ fontSize: 11, color: '#58a6ff', cursor: 'pointer' }} onClick={(e) => { e.stopPropagation(); onCreditClick && onCreditClick(r.credit_id); }} title="\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043a\u0430\u0440\u0442\u0443 \u043a\u0440\u0435\u0434\u0438\u0442\u0430">#{r.credit_id}</div>
                      </td>
                      <td style={tdS}>{r.product_type}</td>
                      <td style={tdS}>{fmt(r.monthly_payment)}</td>
                      <td style={{ ...tdS, color: paymentSoon ? '#f97316' : '#e6edf3', fontWeight: paymentSoon ? 700 : 400 }}>
                        {fmtDate(r.next_payment_date)}
                      </td>
                      <td style={tdS}>
                        {r.days_to_payment !== null ? (
                          <span style={{
                            padding: '2px 8px', borderRadius: 4, fontWeight: 600, fontSize: 12,
                            background: r.days_to_payment <= 3 ? '#7f1d1d' : r.days_to_payment <= 7 ? '#422006' : '#1e293b',
                            color: r.days_to_payment <= 3 ? '#fca5a5' : r.days_to_payment <= 7 ? '#fde68a' : '#94a3b8',
                          }}>
                            {r.days_to_payment}
                          </span>
                        ) : '\u2014'}
                      </td>
                      <td style={tdS}>{fmt(r.total_debt)}</td>
                      <td style={tdS}>
                        {r.overdue_days > 0 ? (
                          <span style={{ color: '#ef4444', fontWeight: 600 }}>{r.overdue_days}</span>
                        ) : (
                          <span style={{ color: '#22c55e' }}>0</span>
                        )}
                      </td>
                      <td style={tdS}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{ width: 50, height: 6, background: '#30363d', borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{ width: `${r.risk_score * 100}%`, height: '100%', background: getRiskColor(r.risk_category), borderRadius: 3 }} />
                          </div>
                          <span style={{
                            padding: '2px 6px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                            background: getRiskBg(r.risk_category), color: getRiskColor(r.risk_category),
                          }}>
                            {r.risk_label}
                          </span>
                        </div>
                      </td>
                      <td style={tdS}>
                        <div style={{ display: 'flex', gap: 3 }}>
                          <ComplianceBadge data={r.phone} type="phone" />
                          <ComplianceBadge data={r.sms} type="sms" />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Detail panel */}
        {selected && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, position: 'sticky', top: 16 }}>
            {/* Risk card */}
            <div style={{
              background: getRiskBg(selected.risk_category), border: `1px solid ${getRiskColor(selected.risk_category)}44`,
              borderRadius: 10, padding: 16, textAlign: 'center',
            }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: getRiskColor(selected.risk_category) }}>
                {selected.risk_label} {'\u0440\u0438\u0441\u043a'} {'\u2014'} {(selected.risk_score * 100).toFixed(0)}%
              </div>
              <div style={{ fontSize: 13, color: '#cbd5e1', marginTop: 4 }}>
                {selected.client_name}
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 12, justifyContent: 'center' }}>
                {Object.entries(selected.probabilities || {}).map(([k, v]) => (
                  <div key={k} style={{ background: '#0d1117', borderRadius: 6, padding: '6px 10px', textAlign: 'center' }}>
                    <div style={{ fontSize: 10, color: '#8b949e' }}>{k}</div>
                    <div style={{ fontWeight: 700, color: k === '\u0412\u044b\u0441\u043e\u043a\u0438\u0439' ? '#ef4444' : k === '\u0421\u0440\u0435\u0434\u043d\u0438\u0439' ? '#eab308' : '#22c55e' }}>
                      {(v * 100).toFixed(1)}%
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Payment info */}
            <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 10, padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #30363d', paddingBottom: 8, marginBottom: 10 }}>
                <h3 style={{ margin: 0, fontSize: 15 }}>{'\u0418\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u044f \u043e \u043a\u0440\u0435\u0434\u0438\u0442\u0435'}</h3>
                <button className="btn small ghost" style={{ fontSize: 12 }} onClick={() => onCreditClick && onCreditClick(selected.credit_id)}>{'\u041a\u0430\u0440\u0442\u0430 \u043a\u0440\u0435\u0434\u0438\u0442\u0430 \u2192'}</button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13 }}>
                <div><span style={{ color: '#8b949e' }}>{'\u041f\u0440\u043e\u0434\u0443\u043a\u0442'}:</span> {selected.product_type}</div>
                <div><span style={{ color: '#8b949e' }}>{'\u0421\u0442\u0430\u0442\u0443\u0441'}:</span> {selected.credit_status}</div>
                <div><span style={{ color: '#8b949e' }}>{'\u0421\u0443\u043c\u043c\u0430'}:</span> {fmt(selected.principal_amount)}</div>
                <div><span style={{ color: '#8b949e' }}>{'\u041f\u043b\u0430\u0442\u0451\u0436'}:</span> {fmt(selected.monthly_payment)}</div>
                <div><span style={{ color: '#8b949e' }}>{'\u041e\u0431\u0449\u0438\u0439 \u0434\u043e\u043b\u0433'}:</span> {fmt(selected.total_debt)}</div>
                <div><span style={{ color: '#8b949e' }}>DPD:</span> {selected.overdue_days} {'\u0434\u043d.'}</div>
                <div><span style={{ color: '#8b949e' }}>{'\u041f\u0440\u043e\u0441\u0440\u043e\u0447\u043a\u0430'}:</span> {selected.delinquency_bucket}</div>
                <div><span style={{ color: '#8b949e' }}>{'\u0422\u0435\u043b\u0435\u0444\u043e\u043d'}:</span> {selected.client_phone || '\u2014'}</div>
              </div>
              <div style={{
                marginTop: 10, padding: '8px 12px', borderRadius: 6,
                background: selected.days_to_payment !== null && selected.days_to_payment <= 3 ? '#7f1d1d' : '#0d1117',
                border: '1px solid #30363d',
              }}>
                <div style={{ fontSize: 12, color: '#8b949e' }}>{'\u0414\u0430\u0442\u0430 \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0435\u0433\u043e \u043f\u043b\u0430\u0442\u0435\u0436\u0430'}</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: selected.days_to_payment !== null && selected.days_to_payment <= 3 ? '#fca5a5' : '#3b82f6' }}>
                  {fmtDate(selected.next_payment_date)}
                  {selected.days_to_payment !== null && (
                    <span style={{ fontSize: 13, fontWeight: 400, marginLeft: 8, color: '#8b949e' }}>
                      ({'\u0447\u0435\u0440\u0435\u0437'} {selected.days_to_payment} {'\u0434\u043d.'})
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Action panel */}
            <ActionPanel row={selected} onAction={handleAction} />
          </div>
        )}
      </div>
    </div>
  );
}

const tdS = { padding: '8px 10px', verticalAlign: 'middle' };
