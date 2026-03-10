import React, { useState, useEffect } from 'react';

const API = 'http://127.0.0.1:8000/api';

/* ===== Признаки модели ===== */
const FEATURE_GROUPS = [
  {
    title: '👤 Демографические',
    features: [
      { name: 'age', label: 'Возраст', source: 'CreditApplication.birth_date', transform: '(today − birth_date).days / 365.25', type: 'float' },
      { name: 'gender', label: 'Пол', source: 'CreditApplication.gender', transform: 'M → 1, F → 0', type: 'int (0/1)' },
      { name: 'marital_married', label: 'Женат/Замужем', source: 'CreditApplication.marital_status', transform: 'one-hot: married → 1', type: 'int (0/1)' },
      { name: 'marital_divorced', label: 'Разведён(а)', source: 'CreditApplication.marital_status', transform: 'one-hot: divorced → 1', type: 'int (0/1)' },
      { name: 'marital_widowed', label: 'Вдовец/Вдова', source: 'CreditApplication.marital_status', transform: 'one-hot: widowed → 1', type: 'int (0/1)' },
      { name: 'marital_civil', label: 'Гражданский брак', source: 'CreditApplication.marital_status', transform: 'one-hot: civil_marriage → 1', type: 'int (0/1)' },
      { name: 'education_ord', label: 'Образование (ordinal)', source: 'CreditApplication.education', transform: 'secondary→0, vocational→1, incomplete_higher→2, higher→3, multiple_higher→4, academic→5', type: 'int (0–5)' },
      { name: 'dependents_count', label: 'Кол-во иждивенцев', source: 'CreditApplication.dependents_count', transform: 'int', type: 'int' },
    ],
  },
  {
    title: '💼 Занятость и стаж',
    features: [
      { name: 'empl_self_employed', label: 'Самозанятый', source: 'CreditApplication.employment_type', transform: 'one-hot', type: 'int (0/1)' },
      { name: 'empl_business', label: 'Бизнес', source: 'CreditApplication.employment_type', transform: 'one-hot: business_owner → 1', type: 'int (0/1)' },
      { name: 'empl_freelance', label: 'Фрилансер', source: 'CreditApplication.employment_type', transform: 'one-hot', type: 'int (0/1)' },
      { name: 'empl_retired', label: 'Пенсионер', source: 'CreditApplication.employment_type', transform: 'one-hot', type: 'int (0/1)' },
      { name: 'empl_unemployed', label: 'Безработный', source: 'CreditApplication.employment_type', transform: 'one-hot', type: 'int (0/1)' },
      { name: 'empl_military', label: 'Военнослужащий', source: 'CreditApplication.employment_type', transform: 'one-hot', type: 'int (0/1)' },
      { name: 'empl_civil_servant', label: 'Госслужащий', source: 'CreditApplication.employment_type', transform: 'one-hot', type: 'int (0/1)' },
      { name: 'empl_student', label: 'Студент', source: 'CreditApplication.employment_type', transform: 'one-hot', type: 'int (0/1)' },
      { name: 'work_experience_total', label: 'Общий стаж', source: 'CreditApplication.work_experience_total', transform: 'int (мес.)', type: 'int' },
      { name: 'work_experience_current', label: 'Стаж на тек. месте', source: 'CreditApplication.work_experience_current', transform: 'int (мес.)', type: 'int' },
    ],
  },
  {
    title: '💰 Финансовые',
    features: [
      { name: 'total_income', label: 'Совокупный доход', source: 'income_main + additional + rental + pension + other', transform: 'Σ 5 источников', type: 'float (₽)' },
      { name: 'total_expenses', label: 'Совокупные расходы', source: 'expense_rent + utilities + food + transport + other + loans', transform: 'Σ 6 компонент', type: 'float (₽)' },
      { name: 'dti_ratio', label: 'DTI (Debt-to-Income)', source: 'Расчётный', transform: '(monthly_payment_est + total_expenses) / total_income', type: 'float' },
      { name: 'amount', label: 'Сумма кредита', source: 'CreditApplication.amount', transform: 'float', type: 'float (₽)' },
      { name: 'requested_term', label: 'Срок кредита', source: 'CreditApplication.requested_term', transform: 'int', type: 'int (мес.)' },
      { name: 'monthly_payment_est', label: 'Оценка ежемес. платежа', source: 'Расчётный', transform: 'amount / requested_term', type: 'float (₽)' },
      { name: 'income_confirmation_ord', label: 'Подтверждение дохода', source: 'CreditApplication.income_confirmation', transform: 'none→0, bank_form→1, bank_statement→2, 2ndfl→3, tax_declaration→4', type: 'int (0–4)' },
    ],
  },
  {
    title: '🏠 Имущество и кредитная история',
    features: [
      { name: 'has_collateral', label: 'Наличие залога', source: 'CreditApplication.has_collateral', transform: 'bool → int', type: 'int (0/1)' },
      { name: 'has_guarantor', label: 'Наличие поручителя', source: 'CreditApplication.has_guarantor', transform: 'bool → int', type: 'int (0/1)' },
      { name: 'has_overdue_history', label: 'История просрочек', source: 'CreditApplication.has_overdue_history', transform: 'bool → int', type: 'int (0/1)' },
      { name: 'max_overdue_days', label: 'Макс. дней просрочки', source: 'CreditApplication.max_overdue_days', transform: 'int', type: 'int' },
      { name: 'has_real_estate', label: 'Недвижимость', source: 'CreditApplication.has_real_estate', transform: 'bool → int', type: 'int (0/1)' },
      { name: 'has_car', label: 'Автомобиль', source: 'CreditApplication.has_car', transform: 'bool → int', type: 'int (0/1)' },
      { name: 'has_deposits', label: 'Вклады', source: 'CreditApplication.has_deposits', transform: 'bool → int', type: 'int (0/1)' },
      { name: 'current_loans_count', label: 'Действующих кредитов', source: 'CreditApplication.current_loans_count', transform: 'int', type: 'int' },
      { name: 'property_ownership_ord', label: 'Жилищные условия', source: 'CreditApplication.property_ownership', transform: 'rent→0, parents→1, employer→2, mortgage→3, own→4', type: 'int (0–4)' },
    ],
  },
];

const TOTAL_FEATURES = FEATURE_GROUPS.reduce((s, g) => s + g.features.length, 0);

const PIPELINE_STEPS = [
  {
    step: 1, title: 'Сбор данных', icon: '📥',
    desc: 'Загрузка реальных заявок из таблицы CreditApplication (с решениями approved/rejected) и генерация синтетических примеров из таблиц Client + Credit.',
    detail: 'Реальные заявки: из CreditApplication где decision ∈ {approved, rejected}.\nСинтетические: для каждого клиента генерируется случайная «заявка» на основе его реального профиля (доход, расходы, занятость, кредитная история).\nМинимум записей задаётся параметром --samples (по умолчанию 1500).',
    command: 'python manage.py train_approval_model --samples 1500',
  },
  {
    step: 2, title: 'Инженерия признаков', icon: '🔧',
    desc: `Извлечение ${TOTAL_FEATURES} числовых признаков из данных заявки. Категориальные переменные кодируются двумя способами: One-Hot и Ordinal.`,
    detail: 'One-Hot encoding: marital_status → 4 бинарных (married, divorced, widowed, civil)\nOne-Hot encoding: employment_type → 8 бинарных (self_employed, business, freelance, retired, unemployed, military, civil_servant, student)\nОпорный уровень (base): single (marital), employed (employment) — не кодируется\nOrdinal: education (0–5), income_confirmation (0–4), property_ownership (0–4)\nПроизводные: dti_ratio, monthly_payment_est, total_income, total_expenses',
    command: null,
  },
  {
    step: 3, title: 'Разметка целевой переменной', icon: '🏷️',
    desc: 'Бинарная классификация: y = 1 (одобрено), y = 0 (отказ).',
    detail: 'Для реальных заявок: decision="approved" → 1, "rejected" → 0\n\nДля синтетических: скоринг approval_score по правилам:\n  + 2.0  нет просрочек\n  − 1.5  есть просрочки\n  + 1.5  DTI < 0.3\n  − 3.5  DTI > 1.0\n  − 5.0  расходы > дохода\n  + 1.0  employed/military/civil_servant\n  − 2.0  unemployed/student\n  + шум N(0, 0.6)\n\nОдобрено если approval_score > 0.5',
    command: null,
  },
  {
    step: 4, title: 'Нормализация (StandardScaler)', icon: '⚖️',
    desc: `Приведение всех ${TOTAL_FEATURES} признаков к единому масштабу: μ = 0, σ = 1.`,
    detail: 'StandardScaler из sklearn.preprocessing. Fit только на train-выборке. Transform — на обеих частях, чтобы не допустить data leakage.',
    command: null,
  },
  {
    step: 5, title: 'Разделение выборки', icon: '✂️',
    desc: 'Стратифицированное разбиение 75% / 25% (train / test).',
    detail: 'train_test_split с test_size=0.25, stratify=y (сохранение пропорций классов), random_state=42 для воспроизводимости.',
    command: null,
  },
  {
    step: 6, title: 'Обучение GradientBoostingClassifier', icon: '🌳',
    desc: 'Градиентный бустинг: последовательное построение 200 деревьев решений, каждое исправляет ошибки предыдущих.',
    detail: 'n_estimators=200, learning_rate=0.1, max_depth=5, min_samples_split=10, min_samples_leaf=5, subsample=0.8 (стохастический бустинг), random_state=42.',
    command: null,
  },
  {
    step: 7, title: 'Кросс-валидация (5-fold)', icon: '🔄',
    desc: 'Оценка устойчивости модели методом 5-fold cross-validation на полном датасете.',
    detail: 'cross_val_score с scoring="accuracy". Среднее и стандартное отклонение по 5 фолдам. Модель обучается на нормализованных данных.',
    command: null,
  },
  {
    step: 8, title: 'Оценка качества', icon: '📈',
    desc: 'Метрики: Accuracy, ROC-AUC, Precision, Recall, F1-score по каждому классу, матрица ошибок.',
    detail: 'classification_report с target_names=["Отказ", "Одобрено"].\nROC-AUC вычисляется по predict_proba.\nFeature importances из модели GradientBoosting.\nConfusion matrix для анализа ошибок первого и второго рода.',
    command: null,
  },
  {
    step: 9, title: 'Постобработка (бизнес-правила)', icon: '📋',
    desc: 'Жёсткие правила кредитной политики, которые переопределяют решение ML-модели.',
    detail: 'Hard reject (автоматический отказ):\n  • Расходы ≥ дохода\n  • DTI > 80% (порог ЦБ РФ)\n  • Нулевой доход\n  • Платёж > 50% дохода\n  • Доход на члена семьи < прожиточного минимума (17 000 ₽)\n\nDTO-штрафы (корректировка вероятности):\n  • DTI > 1.0 → penalty до −80%\n  • DTI > 0.7 → penalty до −70%\n  • DTI > 0.5 → penalty −15%\n\nШтраф за ≥5 иждивенцев: −30%\nШтраф за ≥3 иждивенцев: −10%',
    command: null,
  },
  {
    step: 10, title: 'Сохранение модели', icon: '💾',
    desc: 'Сериализация обученной модели, скейлера и списка признаков в .pkl файлы.',
    detail: 'Файлы: approval_model.pkl, approval_scaler.pkl, approval_features.pkl.\nДиректория: backend/collection_app/ml/saved_models/',
    command: null,
  },
  {
    step: 11, title: 'Инференс (Prediction API)', icon: '🎯',
    desc: 'Применение обученной модели к новым заявкам через REST API.',
    detail: 'POST /api/applications/predict_approval/ — произвольные данные\nPOST /api/applications/{id}/process_application/ — существующая заявка из БД\n\nЕсли модель не обучена → rule-based fallback.\nЕсли жёсткие правила сработали → rule_override (без ML).',
    command: null,
  },
];

const HYPERPARAMS = [
  { param: 'n_estimators', value: '200', desc: 'Количество деревьев (последовательный бустинг)' },
  { param: 'learning_rate', value: '0.1', desc: 'Темп обучения (shrinkage)' },
  { param: 'max_depth', value: '5', desc: 'Максимальная глубина каждого дерева' },
  { param: 'min_samples_split', value: '10', desc: 'Минимум объектов для разделения узла' },
  { param: 'min_samples_leaf', value: '5', desc: 'Минимальное кол-во объектов в листе' },
  { param: 'subsample', value: '0.8', desc: 'Доля выборки для каждого дерева (стохастический бустинг)' },
  { param: 'random_state', value: '42', desc: 'Фиксация случайного seed для воспроизводимости' },
  { param: 'test_size', value: '0.25', desc: 'Доля тестовой выборки (25%)' },
  { param: 'cv', value: '5', desc: 'Количество фолдов кросс-валидации' },
  { param: 'stratify', value: 'y', desc: 'Сохранение пропорций классов при разбиении' },
];

const HARD_REJECT_RULES = [
  { rule: 'Расходы ≥ дохода', condition: 'total_expenses ≥ total_income', color: '#f85149' },
  { rule: 'Критический DTI > 100%', condition: 'dti_ratio > 1.0', color: '#f85149' },
  { rule: 'DTI > 80% (порог ЦБ РФ)', condition: 'dti_ratio > 0.8', color: '#f85149' },
  { rule: 'Нулевой доход', condition: 'total_income ≤ 0', color: '#f85149' },
  { rule: 'Платёж > 50% дохода', condition: 'monthly_payment_est > total_income × 0.5', color: '#d29922' },
  { rule: 'Доход на чл. семьи < прожит. минимума', condition: '(income − expenses − payment) / family_size < 17 000 ₽', color: '#d29922' },
  { rule: '≥5 иждивенцев при доходе < 200 000', condition: 'dependents ≥ 5 AND income < 200 000', color: '#d29922' },
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
  logBox: {
    fontFamily: 'monospace', fontSize: 12, background: '#0d1117', border: '1px solid #30363d',
    borderRadius: 8, padding: 14, color: '#8b949e', maxHeight: 300, overflowY: 'auto', whiteSpace: 'pre-wrap', lineHeight: 1.6,
  },
  trainBtn: {
    padding: '10px 20px', borderRadius: 8, border: 'none', cursor: 'pointer',
    fontSize: 14, fontWeight: 600, background: '#388bfd', color: '#fff', transition: 'opacity .15s',
  },
  trainBtnDisabled: { opacity: 0.5, cursor: 'not-allowed' },
};

export default function LoanTrainingPage() {
  const [activeTab, setActiveTab] = useState('pipeline');
  const [activeStep, setActiveStep] = useState(0);
  const [trainingResult, setTrainingResult] = useState(null);
  const [training, setTraining] = useState(false);
  const [trainError, setTrainError] = useState('');
  const [dbStats, setDbStats] = useState(null);

  useEffect(() => {
    fetch(`${API}/applications/`)
      .then(r => r.json())
      .then(data => {
        const apps = Array.isArray(data) ? data : data.results || [];
        setDbStats({
          total: apps.length,
          approved: apps.filter(a => a.decision === 'approved').length,
          rejected: apps.filter(a => a.decision === 'rejected').length,
          pending: apps.filter(a => !a.decision || a.decision === 'pending').length,
        });
      })
      .catch(() => {});
  }, []);

  const handleTrain = async () => {
    setTraining(true);
    setTrainError('');
    setTrainingResult(null);
    try {
      const resp = await fetch(`${API}/ml/train-approval/`, { method: 'POST' });
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
    { key: 'features', label: `📋 Признаки (${TOTAL_FEATURES})` },
    { key: 'target', label: '🏷️ Целевая переменная' },
    { key: 'model', label: '🌳 Модель и гиперпараметры' },
    { key: 'rules', label: '📋 Бизнес-правила' },
    { key: 'api', label: '🌐 API инференса' },
    { key: 'run', label: '▶️ Запуск обучения' },
  ];

  return (
    <div style={s.page}>
      <h1 style={s.h1}>🏦 Обучение модели одобрения кредитных заявок</h1>
      <div style={s.subtitle}>
        Бинарная классификация: одобрение / отказ • GradientBoostingClassifier • {TOTAL_FEATURES} признаков • Жёсткие бизнес-правила
      </div>

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
                <div style={s.stepCard(activeStep === i)} onClick={() => setActiveStep(activeStep === i ? -1 : i)}>
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <span style={s.stepN}>{step.step}</span>
                    <span style={{ fontSize: 18, marginRight: 8 }}>{step.icon}</span>
                    <strong style={{ color: '#e6edf3', fontSize: 14 }}>{step.title}</strong>
                  </div>
                  <div style={{ color: '#8b949e', fontSize: 13, marginTop: 8, marginLeft: 38 }}>{step.desc}</div>
                  {activeStep === i && (
                    <div style={{ marginTop: 12, marginLeft: 38 }}>
                      <div style={{ color: '#e6edf3', fontSize: 13, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{step.detail}</div>
                      {step.command && <code style={s.code}>$ {step.command}</code>}
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
          <div style={s.sectionTitle}>📋 Вектор признаков — {TOTAL_FEATURES} features</div>
          <div style={{ color: '#8b949e', fontSize: 13, marginBottom: 20 }}>
            Каждая кредитная заявка преобразуется в числовой вектор из {TOTAL_FEATURES} признаков. Категориальные переменные кодируются через One-Hot (семейное положение, тип занятости) и Ordinal encoding (образование, подтверждение дохода, жилищные условия).
          </div>

          <div style={{ ...s.featureRow, fontWeight: 700, color: '#8b949e', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '2px solid #30363d' }}>
            <div>Признак</div>
            <div>Источник</div>
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
            💡 Все признаки нормализуются через <strong style={{ color: '#e6edf3' }}>StandardScaler</strong> (μ=0, σ=1). Опорные уровни (base): <span style={s.mono}>single</span> для family, <span style={s.mono}>employed</span> для employment — не кодируются (предотвращение мультиколлинеарности).
          </div>
        </div>
      )}

      {/* =================== TARGET =================== */}
      {activeTab === 'target' && (
        <div style={s.section}>
          <div style={s.sectionTitle}>🏷️ Целевая переменная — decision</div>
          <div style={{ color: '#8b949e', fontSize: 13, marginBottom: 20 }}>
            Бинарная классификация: одобрение или отказ в выдаче кредита.
          </div>

          <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
            {[
              { cls: 1, label: 'Одобрено (approved)', color: '#3fb950', bg: 'rgba(63,185,80,0.15)', icon: '✅' },
              { cls: 0, label: 'Отказано (rejected)', color: '#f85149', bg: 'rgba(248,81,73,0.15)', icon: '❌' },
            ].map(r => (
              <div key={r.cls} style={{ flex: 1, background: r.bg, border: `1px solid ${r.color}40`, borderRadius: 10, padding: 20, textAlign: 'center' }}>
                <div style={{ fontSize: 32, marginBottom: 8 }}>{r.icon}</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: r.color }}>{r.label}</div>
                <div style={{ fontFamily: 'monospace', fontSize: 14, color: '#8b949e', marginTop: 6 }}>y = {r.cls}</div>
              </div>
            ))}
          </div>

          <div style={{ ...s.sectionTitle, fontSize: 15 }}>Скоринг для синтетических данных</div>
          <div style={s.logBox}>{`approval_score = 0.0

# === Жёсткие правила (автоматический отказ) ===
if expenses ≥ income:         score −= 5.0
if income ≤ 0:                score −= 5.0
if monthly_pay > 80% income:  score −= 4.0

# === Кредитная история ===
if no overdue:    score += 2.0
if has overdue:   score −= 1.5

# === DTI (Debt-to-Income) ===
if dti < 0.3:    score += 1.5
if dti < 0.5:    score += 0.5
if dti < 0.7:    score −= 0.5
if dti < 1.0:    score −= 2.0
if dti ≥ 1.0:    score −= 3.5

# === Занятость ===
if employed/military/civil_servant:  score += 1.0
if self_employed:                    score += 0.5
if unemployed/student:               score −= 2.0
if retired:                          score −= 0.3

# === Другие факторы ===
if work_current ≥ 12 мес:   score += 0.5
if has_collateral:            score += 0.5
if active_credits ≥ 3:       score −= 0.5
if has_real_estate:           score += 0.3
if has_deposits:              score += 0.3

# === Шум ===
score += N(0, 0.6)

# === Решение ===
y = 1 (одобрено) если approval_score > 0.5, иначе 0`}</div>
        </div>
      )}

      {/* =================== MODEL =================== */}
      {activeTab === 'model' && (
        <div style={s.section}>
          <div style={s.sectionTitle}>🌳 GradientBoostingClassifier — гиперпараметры</div>
          <div style={{ color: '#8b949e', fontSize: 13, marginBottom: 20 }}>
            Ансамблевый метод: последовательное построение деревьев решений, каждое дерево корректирует ошибки предыдущих (градиентный бустинг).
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
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
                { file: 'approval_model.pkl', desc: 'Обученный GradientBoostingClassifier', icon: '🌳' },
                { file: 'approval_scaler.pkl', desc: 'StandardScaler (fit на train)', icon: '⚖️' },
                { file: 'approval_features.pkl', desc: `Список из ${TOTAL_FEATURES} признаков (порядок)`, icon: '📋' },
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
            <div style={s.logBox}>{`score = 0.5

# Жёсткие отказы
if expenses ≥ income:   score = 0.05
elif dti > 1.5:         score = 0.05
elif income ≤ 0:        score = 0.05

# DTI-штрафы
if dti > 0.8:   score −= 0.45
elif dti > 0.6: score −= 0.30
elif dti > 0.4: score −= 0.10
elif dti < 0.3: score += 0.10

# Другие факторы
if overdue_history:         score −= 0.25
if unemployed/student:      score −= 0.20
if dependents ≥ 5:          score −= 0.20
elif dependents ≥ 3:        score −= 0.10
if has_collateral:          score += 0.10
if has_deposits:            score += 0.05
if education ≥ higher:      score += 0.05
if work_experience > 60m:   score += 0.05

decision = "approved" если score ≥ 0.5`}</div>
          </div>
        </div>
      )}

      {/* =================== BUSINESS RULES =================== */}
      {activeTab === 'rules' && (
        <div style={s.section}>
          <div style={s.sectionTitle}>📋 Жёсткие бизнес-правила (Hard Reject)</div>
          <div style={{ color: '#8b949e', fontSize: 13, marginBottom: 20 }}>
            Правила кредитной политики, которые срабатывают <strong style={{ color: '#e6edf3' }}>до</strong> ML-модели и автоматически отклоняют заявку вне зависимости от прогноза. Тип модели в ответе: <span style={s.mono}>rule_override</span>.
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>
            {HARD_REJECT_RULES.map((r, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, background: '#0d1117', border: '1px solid #30363d', borderRadius: 8, padding: '12px 16px' }}>
                <span style={s.badge(r.color, r.color + '20')}>⛔</span>
                <div style={{ flex: 1 }}>
                  <div style={{ color: '#e6edf3', fontWeight: 500, fontSize: 14 }}>{r.rule}</div>
                  <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#8b949e', marginTop: 2 }}>{r.condition}</div>
                </div>
              </div>
            ))}
          </div>

          <div style={{ ...s.sectionTitle, fontSize: 15 }}>Корректировка вероятности (DTI-штрафы)</div>
          <div style={{ color: '#8b949e', fontSize: 13, marginBottom: 12 }}>
            Если жёсткие правила не сработали, ML-модель выдаёт вероятность, которая корректируется DTI-штрафами:
          </div>
          <div style={s.logBox}>{`# Вероятность одобрения: approved_prob = model.predict_proba(X)[1]

if dti > 1.0:
    penalty = min(approved_prob × 0.8, 0.6)
    approved_prob = max(0.02, approved_prob − penalty)

elif dti > 0.7:
    severity = (dti − 0.7) / 0.3         # 0..1
    penalty = approved_prob × (0.4 + severity × 0.3)
    approved_prob = max(0.05, approved_prob − penalty)

elif dti > 0.5:
    penalty = approved_prob × 0.15
    approved_prob = max(0.10, approved_prob − penalty)

# Штрафы за иждивенцев
if dependents ≥ 5:   penalty = min(prob × 0.3, 0.2)
elif dependents ≥ 3: penalty = min(prob × 0.1, 0.1)

# Итоговое решение
decision = "approved" если approved_prob ≥ 0.5`}</div>
        </div>
      )}

      {/* =================== API =================== */}
      {activeTab === 'api' && (
        <div style={s.section}>
          <div style={s.sectionTitle}>🌐 REST API — Инференс модели</div>
          <div style={{ color: '#8b949e', fontSize: 13, marginBottom: 20 }}>
            Два эндпоинта для прогнозирования одобрения кредитных заявок.
          </div>

          {[
            {
              method: 'POST', url: '/api/applications/predict_approval/',
              desc: 'Прогноз по произвольным данным (без сохранения)',
              response: `POST body:
{
  "client_id": 123,          // опционально — данные из БД
  "loan_amount": 500000,
  "loan_term": 36,
  "gender": "M",
  "marital_status": "married",
  "employment": "employed",
  "income": 100000,
  "monthly_expenses": 30000,
  "children_count": 2,
  "credit_history": 1
}

Response:
{
  "approved_probability": 0.78,
  "decision": "approved",
  "confidence": 0.56,
  "risk_factors": [],
  "model_type": "gradient_boosting"
}`,
            },
            {
              method: 'POST', url: '/api/applications/{id}/process_application/',
              desc: 'Обработка существующей заявки из БД (с сохранением результата)',
              response: `POST body: { "auto_decide": true }

Response:
{
  "application_id": 42,
  "prediction": {
    "approved_probability": 0.23,
    "decision": "rejected",
    "confidence": 0.85,
    "risk_factors": [
      "Высокая долговая нагрузка: 72%",
      "Негативная кредитная история"
    ],
    "model_type": "rule_override"
  },
  "auto_decision_applied": true
}`,
            },
          ].map((ep, i) => (
            <div key={i} style={{ marginBottom: 20, background: '#0d1117', border: '1px solid #30363d', borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ padding: '10px 14px', borderBottom: '1px solid #30363d', display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={s.badge('#388bfd', 'rgba(56,139,253,0.15)')}>{ep.method}</span>
                <code style={{ fontSize: 13, color: '#e6edf3' }}>{ep.url}</code>
              </div>
              <div style={{ padding: '10px 14px', borderBottom: '1px solid #21262d' }}>
                <span style={{ fontSize: 13, color: '#8b949e' }}>{ep.desc}</span>
              </div>
              <pre style={{ margin: 0, padding: 14, fontSize: 12, color: '#8b949e', overflowX: 'auto', lineHeight: 1.5 }}>{ep.response}</pre>
            </div>
          ))}

          <div style={{ marginTop: 16, padding: '12px 16px', background: 'rgba(210,153,34,0.1)', border: '1px solid rgba(210,153,34,0.3)', borderRadius: 8, fontSize: 13, color: '#8b949e' }}>
            ⚠️ Поле <span style={s.mono}>model_type</span> в ответе: <strong style={{ color: '#e6edf3' }}>gradient_boosting</strong> — решение ML-модели,{' '}
            <strong style={{ color: '#d29922' }}>rule_override</strong> — жёсткие бизнес-правила,{' '}
            <strong style={{ color: '#8b949e' }}>rule_based</strong> — fallback (модель не обучена).
          </div>
        </div>
      )}

      {/* =================== RUN =================== */}
      {activeTab === 'run' && (
        <div style={s.section}>
          <div style={s.sectionTitle}>▶️ Запуск обучения модели</div>

          {dbStats && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
              <div style={s.metricBox}>
                <div style={s.metricValue}>{dbStats.total}</div>
                <div style={s.metricLabel}>Заявок в БД</div>
              </div>
              <div style={s.metricBox}>
                <div style={{ ...s.metricValue, color: '#3fb950' }}>{dbStats.approved}</div>
                <div style={s.metricLabel}>Одобрено</div>
              </div>
              <div style={s.metricBox}>
                <div style={{ ...s.metricValue, color: '#f85149' }}>{dbStats.rejected}</div>
                <div style={s.metricLabel}>Отказано</div>
              </div>
              <div style={s.metricBox}>
                <div style={{ ...s.metricValue, color: '#d29922' }}>{dbStats.pending}</div>
                <div style={s.metricLabel}>Ожидают</div>
              </div>
            </div>
          )}

          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 14, color: '#e6edf3', fontWeight: 600, marginBottom: 8 }}>Команда для запуска из терминала:</div>
            <code style={s.code}>$ cd backend{'\n'}$ python manage.py train_approval_model</code>
            <div style={{ fontSize: 13, color: '#8b949e', marginTop: 8 }}>С указанием количества обучающих примеров:</div>
            <code style={s.code}>$ python manage.py train_approval_model --samples 2000</code>
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
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 16 }}>
                {[
                  { label: 'Accuracy', value: trainingResult.accuracy, fmt: v => (v * 100).toFixed(1) + '%' },
                  { label: 'ROC AUC', value: trainingResult.roc_auc, fmt: v => (v * 100).toFixed(1) + '%' },
                  { label: 'CV Mean', value: trainingResult.cv_mean, fmt: v => (v * 100).toFixed(1) + '%' },
                  { label: 'Train', value: trainingResult.train_size, fmt: v => v },
                  { label: 'Test', value: trainingResult.test_size, fmt: v => v },
                ].filter(m => m.value != null).map(m => (
                  <div key={m.label} style={s.metricBox}>
                    <div style={s.metricValue}>{m.fmt(m.value)}</div>
                    <div style={s.metricLabel}>{m.label}</div>
                  </div>
                ))}
              </div>

              {trainingResult.classification_report && (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, marginBottom: 16 }}>
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
                    {['Отказ', 'Одобрено'].map(name => {
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
