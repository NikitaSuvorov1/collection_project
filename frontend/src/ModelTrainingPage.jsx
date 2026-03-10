import React, { useState, useEffect } from 'react';

const API = 'http://127.0.0.1:8000/api';

/* ===== Константы признаков ===== */
const FEATURE_GROUPS = [
  {
    title: '👤 Клиентские признаки',
    icon: '👤',
    features: [
      { name: 'age', label: 'Возраст', source: 'Client.birth_date', transform: '(today - birth_date).days / 365.25', type: 'float' },
      { name: 'gender', label: 'Пол', source: 'Client.gender', transform: 'M → 1, F → 0', type: 'int (0/1)' },
      { name: 'marital_status', label: 'Семейное положение', source: 'Client.marital_status', transform: 'single→0, married→1, divorced→2, widowed→3', type: 'int (0–3)' },
      { name: 'employment', label: 'Тип занятости', source: 'Client.employment', transform: 'unemployed→0, employed→1, self_employed→2, retired→3, student→4', type: 'int (0–4)' },
      { name: 'dependents', label: 'Кол-во иждивенцев', source: 'Client.children_count', transform: 'int, 0 если null', type: 'int' },
      { name: 'monthly_income', label: 'Ежемесячный доход', source: 'Client.income', transform: 'float(income)', type: 'float (₽)' },
      { name: 'has_other_credits', label: 'Наличие других кредитов', source: 'Credit (count)', transform: 'count(credits) - 1 > 0 → 1, иначе 0', type: 'int (0/1)' },
      { name: 'other_credits_count', label: 'Кол-во других кредитов', source: 'Credit (count)', transform: 'count(client_credits) - 1', type: 'int' },
    ],
  },
  {
    title: '💳 Кредитные признаки',
    icon: '💳',
    features: [
      { name: 'credit_amount', label: 'Сумма кредита', source: 'Credit.principal_amount', transform: 'float(principal_amount)', type: 'float (₽)' },
      { name: 'credit_term', label: 'Срок кредита', source: 'Credit.open_date, planned_close_date', transform: '(planned_close_date - open_date).days // 30', type: 'int (мес.)' },
      { name: 'interest_rate', label: 'Процентная ставка', source: 'Credit.interest_rate', transform: 'float(interest_rate)', type: 'float (%)' },
      { name: 'lti_ratio', label: 'LTI (кредит / годовой доход)', source: 'Расчётный', transform: 'credit_amount / (monthly_income × 12)', type: 'float' },
      { name: 'credit_age', label: 'Возраст кредита', source: 'Credit.open_date', transform: '(today - open_date).days', type: 'int (дней)' },
      { name: 'credit_status', label: 'Статус кредита', source: 'Credit.status', transform: 'closed→0, active→1, overdue→2, default→3, restructured→4, legal→5, sold→6, written_off→7', type: 'int (0–7)' },
      { name: 'monthly_payment', label: 'Ежемесячный платёж', source: 'Credit.monthly_payment', transform: 'float(monthly_payment)', type: 'float (₽)' },
    ],
  },
  {
    title: '📊 Платёжная дисциплина',
    icon: '📊',
    features: [
      { name: 'total_payments', label: 'Всего платежей', source: 'Payment (count)', transform: 'count(credit.payments)', type: 'int' },
      { name: 'overdue_payments', label: 'Просроченных платежей', source: 'Payment (filter)', transform: 'count(payments где overdue_days > 0)', type: 'int' },
      { name: 'max_overdue_days', label: 'Макс. дней просрочки', source: 'Payment (aggregate)', transform: 'max(overdue_days)', type: 'int' },
      { name: 'avg_payment', label: 'Средний платёж', source: 'Payment (aggregate)', transform: 'avg(amount)', type: 'float (₽)' },
      { name: 'payments_count_12m', label: 'Платежей за 12 мес.', source: 'Payment (filter)', transform: 'count(payments за последний год)', type: 'int' },
      { name: 'overdue_count_12m', label: 'Просрочек за 12 мес.', source: 'Payment (filter)', transform: 'count(overdue за последний год)', type: 'int' },
      { name: 'overdue_share_12m', label: 'Доля просрочек (12 мес.)', source: 'Расчётный', transform: 'overdue_count_12m / payments_count_12m', type: 'float (0–1)' },
      { name: 'max_overdue_12m', label: 'Макс. просрочка за 12м', source: 'Payment (aggregate)', transform: 'max(overdue_days) за последний год', type: 'int (дней)' },
    ],
  },
  {
    title: '🤝 Взаимодействие',
    icon: '🤝',
    features: [
      { name: 'total_interventions', label: 'Всего воздействий', source: 'Intervention (count)', transform: 'count(interventions)', type: 'int' },
      { name: 'completed_interventions', label: 'Завершённых', source: 'Intervention (filter)', transform: 'count(status="completed")', type: 'int' },
      { name: 'promises_count', label: 'Обещаний оплатить', source: 'Intervention (filter)', transform: 'count(status="promise")', type: 'int' },
    ],
  },
];

const PIPELINE_STEPS = [
  {
    step: 1,
    title: 'Сбор данных',
    icon: '📥',
    desc: 'Извлечение записей из таблиц Client, Credit, Payment, Intervention. Для каждого кредита собирается полный контекст клиента и истории платежей.',
    detail: 'Два режима: из таблицы TrainingData (--use-db-training-data) или генерация на лету из связанных таблиц. Используется select_related и prefetch_related для оптимизации запросов.',
    command: 'python manage.py train_overdue_model',
  },
  {
    step: 2,
    title: 'Инженерия признаков',
    icon: '🔧',
    desc: 'Вычисление 26 признаков из 4 групп: клиентские, кредитные, платёжная дисциплина и взаимодействие.',
    detail: 'Категориальные переменные кодируются числами (Label Encoding). Рассчитываются агрегаты: доля просрочек за 12 месяцев, LTI ratio, максимальные дни просрочки и средний размер платежа.',
    command: null,
  },
  {
    step: 3,
    title: 'Разметка целевой переменной',
    icon: '🏷️',
    desc: 'Определение risk_category ∈ {0, 1, 2} на основе правил:',
    detail: '0 (Низкий): overdue_ratio < 0.2 И max_overdue_days < 15\n1 (Средний): 0.2 ≤ overdue_ratio < 0.5 ИЛИ max_overdue_days 15–60\n2 (Высокий): overdue_ratio ≥ 0.5 ИЛИ max_overdue_days > 60\nАвтоматически: статусы default, legal, sold, written_off → класс 2',
    command: null,
  },
  {
    step: 4,
    title: 'Нормализация (StandardScaler)',
    icon: '⚖️',
    desc: 'Приведение всех 26 числовых признаков к единому масштабу: μ = 0, σ = 1.',
    detail: 'StandardScaler из sklearn.preprocessing. Fit выполняется только на train-выборке, transform применяется к обеим частям (train + test) для предотвращения утечки данных.',
    command: null,
  },
  {
    step: 5,
    title: 'Разделение выборки',
    icon: '✂️',
    desc: 'Стратифицированное разбиение 80% / 20% (train / test).',
    detail: 'train_test_split с stratify=y для сохранения пропорций классов. random_state=42 для воспроизводимости.',
    command: null,
  },
  {
    step: 6,
    title: 'Обучение RandomForestClassifier',
    icon: '🌲',
    desc: 'Ансамбль из 200 деревьев решений с ограничением глубины.',
    detail: 'n_estimators=200, max_depth=12, min_samples_split=8, min_samples_leaf=4, class_weight="balanced" (компенсация дисбаланса классов), n_jobs=-1 (все ядра CPU).',
    command: null,
  },
  {
    step: 7,
    title: 'Кросс-валидация (5-fold)',
    icon: '🔄',
    desc: 'Оценка устойчивости модели методом 5-fold cross-validation.',
    detail: 'cross_val_score с scoring="accuracy". Вычисляются mean и std по 5 фолдам. Модель обучается на нормализованных данных (scaler.transform(X)).',
    command: null,
  },
  {
    step: 8,
    title: 'Оценка качества',
    icon: '📈',
    desc: 'Расчёт метрик: Accuracy, Precision, Recall, F1-score по каждому классу, матрица ошибок.',
    detail: 'classification_report с target_names для каждого класса. Feature importances из модели Random Forest, confusion_matrix.',
    command: null,
  },
  {
    step: 9,
    title: 'Сохранение модели',
    icon: '💾',
    desc: 'Сериализация обученной модели, скейлера и списка признаков в .pkl файлы.',
    detail: 'Файлы: overdue_model.pkl, overdue_scaler.pkl, overdue_features.pkl. Директория: backend/collection_app/ml/saved_models/',
    command: null,
  },
  {
    step: 10,
    title: 'Инференс (Prediction API)',
    icon: '🎯',
    desc: 'Применение обученной модели к новым данным через REST API.',
    detail: 'GET /api/overdue-prediction/?credit_id=N — прогноз для одного кредита\nGET /api/overdue-prediction/?client_id=N — все кредиты клиента\nPOST /api/overdue-prediction/ — пакетный прогноз с ранжированием\n\nЕсли модель не обучена, используется rule-based эвристика (fallback).',
    command: null,
  },
];

const HYPERPARAMS = [
  { param: 'n_estimators', value: '200', desc: 'Количество деревьев в ансамбле' },
  { param: 'max_depth', value: '12', desc: 'Максимальная глубина дерева' },
  { param: 'min_samples_split', value: '8', desc: 'Минимум объектов для разделения узла' },
  { param: 'min_samples_leaf', value: '4', desc: 'Минимальное кол-во объектов в листе' },
  { param: 'class_weight', value: 'balanced', desc: 'Автоматическая компенсация дисбаланса классов' },
  { param: 'random_state', value: '42', desc: 'Фиксация случайного seed для воспроизводимости' },
  { param: 'n_jobs', value: '-1', desc: 'Использовать все ядра CPU для параллелизма' },
  { param: 'test_size', value: '0.2', desc: 'Доля тестовой выборки (20%)' },
  { param: 'cv', value: '5', desc: 'Количество фолдов кросс-валидации' },
  { param: 'stratify', value: 'y', desc: 'Сохранение пропорций классов при разбиении' },
];

const TARGET_RULES = [
  { cls: 0, label: 'Низкий риск', color: '#3fb950', condition: 'overdue_ratio < 0.2 И max_overdue_days < 15', bg: 'rgba(63,185,80,0.15)' },
  { cls: 1, label: 'Средний риск', color: '#d29922', condition: '0.2 ≤ overdue_ratio < 0.5 ИЛИ 15 < max_overdue_days ≤ 60', bg: 'rgba(210,153,34,0.15)' },
  { cls: 2, label: 'Высокий риск', color: '#f85149', condition: 'overdue_ratio ≥ 0.5 ИЛИ max_overdue_days > 60 ИЛИ статус ∈ {default, legal, sold, written_off}', bg: 'rgba(248,81,73,0.15)' },
];

const s = {
  page: { maxWidth: 1200, margin: '0 auto', padding: '24px 16px' },
  h1: { fontSize: 24, fontWeight: 700, color: '#e6edf3', margin: '0 0 4px' },
  subtitle: { fontSize: 14, color: '#8b949e', marginBottom: 24 },
  section: { background: '#161b22', border: '1px solid #30363d', borderRadius: 10, padding: 20, marginBottom: 20 },
  sectionTitle: { fontSize: 17, fontWeight: 700, color: '#e6edf3', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 },
  tabs: { display: 'flex', gap: 4, marginBottom: 20, flexWrap: 'wrap' },
  tab: (active) => ({
    padding: '8px 16px', borderRadius: 6, border: '1px solid #30363d', cursor: 'pointer',
    fontSize: 13, fontWeight: 500, transition: 'all .15s',
    background: active ? 'rgba(56,139,253,0.15)' : '#0d1117',
    color: active ? '#388bfd' : '#8b949e',
    borderColor: active ? '#388bfd' : '#30363d',
  }),
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { textAlign: 'left', padding: '10px 12px', borderBottom: '2px solid #30363d', color: '#8b949e', fontWeight: 600, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.5px' },
  td: { padding: '10px 12px', borderBottom: '1px solid #21262d', color: '#e6edf3', verticalAlign: 'top' },
  mono: { fontFamily: 'monospace', fontSize: 12, color: '#8b949e', background: '#0d1117', padding: '2px 6px', borderRadius: 4 },
  badge: (color, bg) => ({ display: 'inline-block', padding: '3px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600, color, background: bg }),
  stepCard: (active) => ({
    background: active ? '#1c2128' : '#161b22', border: `1px solid ${active ? '#388bfd' : '#30363d'}`, borderRadius: 10, padding: 16, cursor: 'pointer', transition: 'all .15s',
  }),
  stepN: { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 28, height: 28, borderRadius: '50%', background: '#21262d', color: '#e6edf3', fontSize: 13, fontWeight: 700, marginRight: 10 },
  arrow: { textAlign: 'center', color: '#484f58', fontSize: 20, padding: '4px 0' },
  code: { fontFamily: 'monospace', fontSize: 13, background: '#0d1117', border: '1px solid #30363d', borderRadius: 6, padding: '10px 14px', color: '#e6edf3', display: 'block', marginTop: 10, wordBreak: 'break-all' },
  metricBox: { background: '#0d1117', border: '1px solid #30363d', borderRadius: 8, padding: '12px 16px', textAlign: 'center' },
  metricValue: { fontSize: 28, fontWeight: 700, color: '#e6edf3', lineHeight: 1.1 },
  metricLabel: { fontSize: 12, color: '#8b949e', marginTop: 4 },
  groupHeader: { fontSize: 15, fontWeight: 600, color: '#e6edf3', padding: '12px 0 8px', borderBottom: '1px solid #30363d', marginBottom: 12 },
  featureRow: { display: 'grid', gridTemplateColumns: '180px 1fr 1fr 90px', gap: 8, padding: '8px 0', borderBottom: '1px solid #21262d', fontSize: 13, alignItems: 'start' },
  muted: { color: '#8b949e' },
  param: { fontFamily: 'monospace', fontSize: 13, color: '#388bfd' },
  trainBtn: {
    padding: '10px 20px', borderRadius: 8, border: 'none', cursor: 'pointer',
    fontSize: 14, fontWeight: 600, background: '#388bfd', color: '#fff', transition: 'opacity .15s',
  },
  trainBtnDisabled: { opacity: 0.5, cursor: 'not-allowed' },
  logBox: {
    fontFamily: 'monospace', fontSize: 12, background: '#0d1117', border: '1px solid #30363d',
    borderRadius: 8, padding: 14, color: '#8b949e', maxHeight: 300, overflowY: 'auto', whiteSpace: 'pre-wrap',
    lineHeight: 1.6,
  },
};

export default function ModelTrainingPage() {
  const [activeTab, setActiveTab] = useState('pipeline');
  const [activeStep, setActiveStep] = useState(0);
  const [trainingResult, setTrainingResult] = useState(null);
  const [training, setTraining] = useState(false);
  const [trainError, setTrainError] = useState('');
  const [dbStats, setDbStats] = useState(null);

  // Fetch basic DB stats on mount
  useEffect(() => {
    fetch(`${API}/credits/`)
      .then(r => r.json())
      .then(data => {
        const credits = Array.isArray(data) ? data : data.results || [];
        setDbStats({
          creditsCount: credits.length,
          activeCount: credits.filter(c => c.status === 'active').length,
          overdueCount: credits.filter(c => c.status === 'overdue').length,
        });
      })
      .catch(() => {});
  }, []);

  const handleTrain = async () => {
    setTraining(true);
    setTrainError('');
    setTrainingResult(null);
    try {
      const resp = await fetch(`${API}/ml/train-overdue/`, { method: 'POST' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setTrainingResult(data);
    } catch (e) {
      setTrainError(e.message || 'Ошибка запуска обучения');
    } finally {
      setTraining(false);
    }
  };

  const TABS = [
    { key: 'pipeline', label: '🔄 Пайплайн обучения' },
    { key: 'features', label: '📋 Признаки (26)' },
    { key: 'target', label: '🏷️ Целевая переменная' },
    { key: 'model', label: '🌲 Модель и гиперпараметры' },
    { key: 'api', label: '🌐 API инференса' },
    { key: 'run', label: '▶️ Запуск обучения' },
  ];

  return (
    <div style={s.page}>
      <h1 style={s.h1}>🧠 Обучение модели прогнозирования просрочки</h1>
      <div style={s.subtitle}>
        Мультиклассовая классификация риска выхода клиента на просрочку при следующем платеже • RandomForestClassifier • 26 признаков • 3 класса риска
      </div>

      {/* Tabs */}
      <div style={s.tabs}>
        {TABS.map(t => (
          <button key={t.key} style={s.tab(activeTab === t.key)} onClick={() => setActiveTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {/* =================== PIPELINE =================== */}
      {activeTab === 'pipeline' && (
        <div style={s.section}>
          <div style={s.sectionTitle}>🔄 Пайплайн обучения модели</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {PIPELINE_STEPS.map((step, i) => (
              <React.Fragment key={step.step}>
                <div
                  style={s.stepCard(activeStep === i)}
                  onClick={() => setActiveStep(activeStep === i ? -1 : i)}
                >
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <span style={s.stepN}>{step.step}</span>
                    <span style={{ fontSize: 18, marginRight: 8 }}>{step.icon}</span>
                    <strong style={{ color: '#e6edf3', fontSize: 14 }}>{step.title}</strong>
                  </div>
                  <div style={{ color: '#8b949e', fontSize: 13, marginTop: 8, marginLeft: 38 }}>
                    {step.desc}
                  </div>
                  {activeStep === i && (
                    <div style={{ marginTop: 12, marginLeft: 38 }}>
                      <div style={{ color: '#e6edf3', fontSize: 13, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                        {step.detail}
                      </div>
                      {step.command && (
                        <code style={s.code}>$ {step.command}</code>
                      )}
                    </div>
                  )}
                </div>
                {i < PIPELINE_STEPS.length - 1 && <div style={s.arrow}>↓</div>}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {/* =================== FEATURES =================== */}
      {activeTab === 'features' && (
        <div style={s.section}>
          <div style={s.sectionTitle}>📋 Вектор признаков — 26 features</div>
          <div style={{ color: '#8b949e', fontSize: 13, marginBottom: 20 }}>
            Каждая запись обучающей выборки содержит вектор из 26 числовых признаков, извлечённых из 4 таблиц БД.
          </div>

          {/* Header */}
          <div style={{ ...s.featureRow, fontWeight: 700, color: '#8b949e', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '2px solid #30363d' }}>
            <div>Признак</div>
            <div>Источник (таблица.поле)</div>
            <div>Трансформация</div>
            <div>Тип</div>
          </div>

          {FEATURE_GROUPS.map(group => (
            <div key={group.title}>
              <div style={s.groupHeader}>{group.title}</div>
              {group.features.map(f => (
                <div key={f.name} style={s.featureRow}>
                  <div>
                    <span style={{ color: '#e6edf3', fontWeight: 500 }}>{f.label}</span>
                    <div style={{ fontFamily: 'monospace', fontSize: 11, color: '#484f58', marginTop: 2 }}>{f.name}</div>
                  </div>
                  <div style={s.muted}>{f.source}</div>
                  <div><span style={s.mono}>{f.transform}</span></div>
                  <div style={s.muted}>{f.type}</div>
                </div>
              ))}
            </div>
          ))}

          <div style={{ marginTop: 20, padding: '12px 16px', background: 'rgba(56,139,253,0.1)', border: '1px solid rgba(56,139,253,0.3)', borderRadius: 8, fontSize: 13, color: '#8b949e' }}>
            💡 Все признаки нормализуются через <strong style={{ color: '#e6edf3' }}>StandardScaler</strong> (μ=0, σ=1) перед подачей в модель. Fit выполняется только на train-выборке.
          </div>
        </div>
      )}

      {/* =================== TARGET =================== */}
      {activeTab === 'target' && (
        <div style={s.section}>
          <div style={s.sectionTitle}>🏷️ Целевая переменная — risk_category</div>
          <div style={{ color: '#8b949e', fontSize: 13, marginBottom: 20 }}>
            Мультиклассовая классификация: 3 категории риска выхода на просрочку.
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {TARGET_RULES.map(r => (
              <div key={r.cls} style={{ background: r.bg, border: `1px solid ${r.color}40`, borderRadius: 10, padding: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                  <span style={s.badge(r.color, r.bg)}>{r.cls}</span>
                  <strong style={{ color: r.color, fontSize: 15 }}>{r.label}</strong>
                </div>
                <div style={{ color: '#e6edf3', fontSize: 13, fontFamily: 'monospace' }}>{r.condition}</div>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 20 }}>
            <div style={{ ...s.sectionTitle, fontSize: 15 }}>Формула определения risk_category</div>
            <div style={s.logBox}>{`if credit.status ∈ {default, legal, sold, written_off}:
    risk_category = 2  (Высокий)

elif credit.status == 'overdue' AND max_overdue_days > 60:
    risk_category = 2

elif overdue_ratio ≥ 0.5 OR max_overdue_days > 60:
    risk_category = 2

elif overdue_ratio ≥ 0.2 OR max_overdue_days > 15:
    risk_category = 1  (Средний)

else:
    risk_category = 0  (Низкий)

where overdue_ratio = overdue_payments / total_payments`}</div>
          </div>

          <div style={{ marginTop: 16 }}>
            <div style={{ ...s.sectionTitle, fontSize: 15 }}>Формула risk_score (при инференсе)</div>
            <div style={s.logBox}>{`risk_score = (0 × P(Низкий) + 1 × P(Средний) + 2 × P(Высокий)) / 2

Нормировка в диапазон [0, 1]:
  0.0 — минимальный риск (100% вероятность класса 0)
  1.0 — максимальный риск (100% вероятность класса 2)`}</div>
          </div>
        </div>
      )}

      {/* =================== MODEL =================== */}
      {activeTab === 'model' && (
        <div style={s.section}>
          <div style={s.sectionTitle}>🌲 RandomForestClassifier — гиперпараметры</div>
          <div style={{ color: '#8b949e', fontSize: 13, marginBottom: 20 }}>
            Ансамблевый метод: коллектив из 200 деревьев решений с ограничением сложности и балансировкой классов.
          </div>

          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>Параметр</th>
                <th style={s.th}>Значение</th>
                <th style={s.th}>Описание</th>
              </tr>
            </thead>
            <tbody>
              {HYPERPARAMS.map(h => (
                <tr key={h.param}>
                  <td style={s.td}><span style={s.param}>{h.param}</span></td>
                  <td style={s.td}><strong style={{ color: '#e6edf3' }}>{h.value}</strong></td>
                  <td style={s.td}><span style={s.muted}>{h.desc}</span></td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ marginTop: 24 }}>
            <div style={{ ...s.sectionTitle, fontSize: 15 }}>📂 Артефакты модели</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
              {[
                { file: 'overdue_model.pkl', desc: 'Обученный RandomForestClassifier', icon: '🌲' },
                { file: 'overdue_scaler.pkl', desc: 'StandardScaler (fit на train)', icon: '⚖️' },
                { file: 'overdue_features.pkl', desc: 'Список из 26 признаков (порядок)', icon: '📋' },
              ].map(a => (
                <div key={a.file} style={{ ...s.metricBox, textAlign: 'left' }}>
                  <div style={{ fontSize: 20, marginBottom: 6 }}>{a.icon}</div>
                  <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#388bfd', marginBottom: 4 }}>{a.file}</div>
                  <div style={{ fontSize: 12, color: '#8b949e' }}>{a.desc}</div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 12, fontSize: 13, color: '#484f58' }}>
              Путь: <span style={s.mono}>backend/collection_app/ml/saved_models/</span>
            </div>
          </div>

          <div style={{ marginTop: 24 }}>
            <div style={{ ...s.sectionTitle, fontSize: 15 }}>🔄 Fallback: Rule-based эвристика</div>
            <div style={{ color: '#8b949e', fontSize: 13, marginBottom: 12 }}>
              Если обученная модель не найдена на диске, используется детерминированная эвристика:
            </div>
            <div style={s.logBox}>{`score = 0.0
if overdue_share_12m > 0.5:  score += 0.4
elif overdue_share_12m > 0.2: score += 0.2

if max_overdue_days > 60:    score += 0.3
elif max_overdue_days > 30:  score += 0.15

if lti_ratio > 5:            score += 0.15
score = min(score, 1.0)

risk_category:
  score ≥ 0.6 → 2 (Высокий)
  score ≥ 0.3 → 1 (Средний)
  иначе       → 0 (Низкий)`}</div>
          </div>
        </div>
      )}

      {/* =================== API =================== */}
      {activeTab === 'api' && (
        <div style={s.section}>
          <div style={s.sectionTitle}>🌐 REST API — Инференс модели</div>
          <div style={{ color: '#8b949e', fontSize: 13, marginBottom: 20 }}>
            Эндпоинт <span style={s.mono}>/api/overdue-prediction/</span> — прогнозирование риска просрочки для клиентов/кредитов.
          </div>

          {[
            {
              method: 'GET', url: '/api/overdue-prediction/?credit_id=123',
              desc: 'Прогноз для одного кредита',
              response: `{
  "risk_category": 2,
  "risk_label": "Высокий",
  "probabilities": { "Низкий": 0.12, "Средний": 0.28, "Высокий": 0.60 },
  "risk_score": 0.74,
  "credit_id": 123,
  "client_name": "Иванов И.И.",
  "features": { "age": 42, "monthly_income": 65000, ... }
}`,
            },
            {
              method: 'GET', url: '/api/overdue-prediction/?client_id=456',
              desc: 'Прогноз по всем активным кредитам клиента',
              response: `{
  "results": [
    { "risk_category": 1, "risk_score": 0.45, "credit_id": 101, ... },
    { "risk_category": 0, "risk_score": 0.12, "credit_id": 102, ... }
  ]
}`,
            },
            {
              method: 'POST', url: '/api/overdue-prediction/',
              desc: 'Пакетный прогноз с ранжированием (top-N)',
              response: `POST body: { "credit_ids": [1,2,3], "top": 50 }

Response:
{
  "total": 3,
  "results": [
    { "rank": 1, "risk_score": 0.89, "risk_label": "Высокий", ... },
    { "rank": 2, "risk_score": 0.52, "risk_label": "Средний", ... },
    ...
  ]
}`,
            },
          ].map((ep, i) => (
            <div key={i} style={{ marginBottom: 20, background: '#0d1117', border: '1px solid #30363d', borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ padding: '10px 14px', borderBottom: '1px solid #30363d', display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={s.badge(ep.method === 'GET' ? '#3fb950' : '#388bfd', ep.method === 'GET' ? 'rgba(63,185,80,0.15)' : 'rgba(56,139,253,0.15)')}>
                  {ep.method}
                </span>
                <code style={{ fontSize: 13, color: '#e6edf3' }}>{ep.url}</code>
              </div>
              <div style={{ padding: '10px 14px', borderBottom: '1px solid #21262d' }}>
                <span style={{ fontSize: 13, color: '#8b949e' }}>{ep.desc}</span>
              </div>
              <pre style={{ margin: 0, padding: 14, fontSize: 12, color: '#8b949e', overflowX: 'auto', lineHeight: 1.5 }}>{ep.response}</pre>
            </div>
          ))}
        </div>
      )}

      {/* =================== RUN =================== */}
      {activeTab === 'run' && (
        <div style={s.section}>
          <div style={s.sectionTitle}>▶️ Запуск обучения модели</div>

          {/* DB Stats */}
          {dbStats && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 20 }}>
              <div style={s.metricBox}>
                <div style={s.metricValue}>{dbStats.creditsCount}</div>
                <div style={s.metricLabel}>Кредитов в БД</div>
              </div>
              <div style={s.metricBox}>
                <div style={{ ...s.metricValue, color: '#3fb950' }}>{dbStats.activeCount}</div>
                <div style={s.metricLabel}>Активных</div>
              </div>
              <div style={s.metricBox}>
                <div style={{ ...s.metricValue, color: '#f85149' }}>{dbStats.overdueCount}</div>
                <div style={s.metricLabel}>Просроченных</div>
              </div>
            </div>
          )}

          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 14, color: '#e6edf3', fontWeight: 600, marginBottom: 8 }}>Команда для запуска из терминала:</div>
            <code style={s.code}>$ cd backend{'\n'}$ python manage.py train_overdue_model</code>
            <div style={{ fontSize: 13, color: '#8b949e', marginTop: 8 }}>
              С использованием таблицы TrainingData:
            </div>
            <code style={s.code}>$ python manage.py train_overdue_model --use-db-training-data</code>
          </div>

          <div style={{ borderTop: '1px solid #30363d', paddingTop: 20 }}>
            <div style={{ fontSize: 14, color: '#e6edf3', fontWeight: 600, marginBottom: 12 }}>Запуск через API (если эндпоинт настроен):</div>
            <button
              style={{ ...s.trainBtn, ...(training ? s.trainBtnDisabled : {}) }}
              onClick={handleTrain}
              disabled={training}
            >
              {training ? '⏳ Обучение...' : '🚀 Запустить обучение модели'}
            </button>
          </div>

          {trainError && (
            <div style={{ marginTop: 16, padding: 12, background: 'rgba(248,81,73,0.15)', border: '1px solid rgba(248,81,73,0.4)', borderRadius: 8, color: '#f85149', fontSize: 13 }}>
              ❌ {trainError}
            </div>
          )}

          {trainingResult && (
            <div style={{ marginTop: 20 }}>
              <div style={{ ...s.sectionTitle, fontSize: 15 }}>📊 Результаты обучения</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
                <div style={s.metricBox}>
                  <div style={s.metricValue}>{(trainingResult.accuracy * 100).toFixed(1)}%</div>
                  <div style={s.metricLabel}>Accuracy</div>
                </div>
                <div style={s.metricBox}>
                  <div style={s.metricValue}>{(trainingResult.cv_mean * 100).toFixed(1)}%</div>
                  <div style={s.metricLabel}>CV Mean</div>
                </div>
                <div style={s.metricBox}>
                  <div style={s.metricValue}>{trainingResult.train_size}</div>
                  <div style={s.metricLabel}>Train</div>
                </div>
                <div style={s.metricBox}>
                  <div style={s.metricValue}>{trainingResult.test_size}</div>
                  <div style={s.metricLabel}>Test</div>
                </div>
              </div>

              {trainingResult.classification_report && (
                <table style={{ ...s.table, marginBottom: 16 }}>
                  <thead>
                    <tr>
                      <th style={s.th}>Класс</th>
                      <th style={{ ...s.th, textAlign: 'right' }}>Precision</th>
                      <th style={{ ...s.th, textAlign: 'right' }}>Recall</th>
                      <th style={{ ...s.th, textAlign: 'right' }}>F1-Score</th>
                      <th style={{ ...s.th, textAlign: 'right' }}>Support</th>
                    </tr>
                  </thead>
                  <tbody>
                    {['Низкий', 'Средний', 'Высокий'].map(name => {
                      const r = trainingResult.classification_report[name];
                      if (!r) return null;
                      return (
                        <tr key={name}>
                          <td style={s.td}><strong>{name}</strong></td>
                          <td style={{ ...s.td, textAlign: 'right' }}>{(r.precision * 100).toFixed(1)}%</td>
                          <td style={{ ...s.td, textAlign: 'right' }}>{(r.recall * 100).toFixed(1)}%</td>
                          <td style={{ ...s.td, textAlign: 'right' }}>{(r['f1-score'] * 100).toFixed(1)}%</td>
                          <td style={{ ...s.td, textAlign: 'right' }}>{r.support}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}

              {trainingResult.feature_importances && (
                <>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3', marginBottom: 10 }}>Top-10 признаков</div>
                  {Object.entries(trainingResult.feature_importances)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 10)
                    .map(([name, imp]) => {
                      const maxImp = Math.max(...Object.values(trainingResult.feature_importances));
                      const pct = maxImp > 0 ? (imp / maxImp) * 100 : 0;
                      const featureLabel = FEATURE_GROUPS.flatMap(g => g.features).find(f => f.name === name)?.label || name;
                      return (
                        <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                          <div style={{ width: 160, fontSize: 12, color: '#8b949e', textAlign: 'right' }}>{featureLabel}</div>
                          <div style={{ flex: 1, height: 12, background: '#21262d', borderRadius: 6, overflow: 'hidden' }}>
                            <div style={{ width: `${pct}%`, height: '100%', background: '#388bfd', borderRadius: 6, transition: 'width 0.5s' }} />
                          </div>
                          <div style={{ width: 50, fontSize: 12, color: '#e6edf3', fontFamily: 'monospace' }}>{(imp * 100).toFixed(1)}%</div>
                        </div>
                      );
                    })}
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
