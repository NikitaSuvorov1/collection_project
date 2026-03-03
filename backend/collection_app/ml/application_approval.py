"""
Модуль прогнозирования одобрения кредитной заявки.

Реализует ML-модель на основе GradientBoostingClassifier для бинарной
классификации: одобрена / отклонена.

Признаки извлекаются из модели CreditApplication:
  1)  age                    — возраст заявителя (лет)
  2)  gender                 — пол (0/1)
  3)  marital_status         — семейное положение (one-hot)
  4)  education              — уровень образования (ordinal)
  5)  employment_type        — тип занятости (one-hot)
  6)  work_experience_total  — общий стаж (мес)
  7)  work_experience_current — стаж на текущем месте (мес)
  8)  total_income           — совокупный доход
  9)  total_expenses         — совокупные расходы
  10) dti_ratio              — debt-to-income
  11) amount                 — запрашиваемая сумма
  12) requested_term         — срок кредита (мес)
  13) monthly_payment_est    — оценка ежемесячного платежа
  14) has_collateral         — наличие залога (0/1)
  15) has_guarantor          — наличие поручителя (0/1)
  16) has_overdue_history    — были просрочки (0/1)
  17) max_overdue_days       — макс. просрочка (дней)
  18) has_real_estate        — недвижимость (0/1)
  19) has_car                — автомобиль (0/1)
  20) has_deposits           — вклады (0/1)
  21) dependents_count       — иждивенцы
  22) current_loans_count    — кол-во действующих кредитов
  23) income_confirmation    — подтверждение дохода (ordinal)
  24) property_ownership     — жилищные условия (ordinal)

Целевая переменная y:  1 — одобрено, 0 — отклонено.

Раздел 3.3 курсовой — классификация заёмщиков методом
градиентного бустинга (ensemble-модель).
"""

import os
import logging
import pickle
from datetime import date
from pathlib import Path
from typing import Optional, Dict, Any, List

import numpy as np

# Ленивый импорт: pandas/sklearn загружаются только при вызове train()
# Это позволяет серверу стартовать даже если DLL pandas заблокирована политикой ОС
pd = None
def _ensure_ml_imports():
    global pd
    if pd is not None:
        return
    import pandas as _pd
    pd = _pd

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / 'saved_models'
MODEL_PATH = MODEL_DIR / 'approval_model.pkl'
SCALER_PATH = MODEL_DIR / 'approval_scaler.pkl'
FEATURES_PATH = MODEL_DIR / 'approval_features.pkl'

# Порядок числовых признаков, используемых моделью
FEATURE_COLUMNS = [
    'age', 'gender', 'education_ord', 'work_experience_total',
    'work_experience_current', 'total_income', 'total_expenses',
    'dti_ratio', 'amount', 'requested_term', 'monthly_payment_est',
    'has_collateral', 'has_guarantor', 'has_overdue_history',
    'max_overdue_days', 'has_real_estate', 'has_car', 'has_deposits',
    'dependents_count', 'current_loans_count', 'income_confirmation_ord',
    'property_ownership_ord',
    # one-hot marital
    'marital_married', 'marital_divorced', 'marital_widowed', 'marital_civil',
    # one-hot employment
    'empl_self_employed', 'empl_business', 'empl_freelance',
    'empl_retired', 'empl_unemployed', 'empl_military', 'empl_civil_servant',
    'empl_student',
]

EDUCATION_ORD = {
    'secondary': 0, 'vocational': 1, 'incomplete_higher': 2,
    'higher': 3, 'multiple_higher': 4, 'academic': 5,
}

INCOME_CONFIRM_ORD = {
    'none': 0, 'bank_form': 1, 'bank_statement': 2,
    '2ndfl': 3, 'tax_declaration': 4,
}

PROPERTY_ORD = {
    'rent': 0, 'parents': 1, 'employer': 2, 'mortgage': 3, 'own': 4,
}


def _extract_features_from_application(app) -> Dict[str, float]:
    """
    Извлечение числового вектора признаков из объекта CreditApplication
    (Django-модель) или из словаря.
    """
    if isinstance(app, dict):
        d = app
    else:
        d = {
            'birth_date': app.birth_date,
            'gender': app.gender,
            'marital_status': app.marital_status,
            'education': app.education,
            'employment_type': app.employment_type,
            'work_experience_total': app.work_experience_total,
            'work_experience_current': app.work_experience_current,
            'income_main': float(app.income_main),
            'income_additional': float(app.income_additional),
            'income_rental': float(app.income_rental),
            'income_pension': float(app.income_pension),
            'income_other': float(app.income_other),
            'expense_rent': float(app.expense_rent),
            'expense_utilities': float(app.expense_utilities),
            'expense_food': float(app.expense_food),
            'expense_transport': float(app.expense_transport),
            'expense_other': float(app.expense_other),
            'current_loans_total_payment': float(app.current_loans_total_payment),
            'amount': float(app.amount),
            'requested_term': app.requested_term,
            'has_collateral': int(app.has_collateral),
            'has_guarantor': int(app.has_guarantor),
            'has_overdue_history': int(app.has_overdue_history),
            'max_overdue_days': app.max_overdue_days,
            'has_real_estate': int(app.has_real_estate),
            'has_car': int(app.has_car),
            'has_deposits': int(app.has_deposits),
            'dependents_count': app.dependents_count,
            'current_loans_count': app.current_loans_count,
            'income_confirmation': app.income_confirmation,
            'property_ownership': app.property_ownership,
        }

    # --- Расчёт производных признаков ---
    birth = d.get('birth_date')
    if birth:
        if isinstance(birth, str):
            birth = date.fromisoformat(birth)
        age = (date.today() - birth).days / 365.25
    else:
        age = 35  # медиана

    gender = 1 if d.get('gender', 'M') == 'M' else 0
    education_ord = EDUCATION_ORD.get(d.get('education', 'higher'), 3)

    total_income = sum([
        float(d.get('income_main', 0)),
        float(d.get('income_additional', 0)),
        float(d.get('income_rental', 0)),
        float(d.get('income_pension', 0)),
        float(d.get('income_other', 0)),
    ])
    total_expenses = sum([
        float(d.get('expense_rent', 0)),
        float(d.get('expense_utilities', 0)),
        float(d.get('expense_food', 0)),
        float(d.get('expense_transport', 0)),
        float(d.get('expense_other', 0)),
        float(d.get('current_loans_total_payment', 0)),
    ])

    amount = float(d.get('amount', 0))
    term = int(d.get('requested_term', 12))
    monthly_payment_est = amount / term if term > 0 else amount

    if total_income > 0:
        dti = (monthly_payment_est + total_expenses) / total_income
    else:
        dti = 1.0

    marital = d.get('marital_status', 'single')
    empl = d.get('employment_type', 'employed')

    row = {
        'age': age,
        'gender': gender,
        'education_ord': education_ord,
        'work_experience_total': int(d.get('work_experience_total', 0)),
        'work_experience_current': int(d.get('work_experience_current', 0)),
        'total_income': total_income,
        'total_expenses': total_expenses,
        'dti_ratio': dti,
        'amount': amount,
        'requested_term': term,
        'monthly_payment_est': monthly_payment_est,
        'has_collateral': int(d.get('has_collateral', False)),
        'has_guarantor': int(d.get('has_guarantor', False)),
        'has_overdue_history': int(d.get('has_overdue_history', False)),
        'max_overdue_days': int(d.get('max_overdue_days', 0)),
        'has_real_estate': int(d.get('has_real_estate', False)),
        'has_car': int(d.get('has_car', False)),
        'has_deposits': int(d.get('has_deposits', False)),
        'dependents_count': int(d.get('dependents_count', 0)),
        'current_loans_count': int(d.get('current_loans_count', 0)),
        'income_confirmation_ord': INCOME_CONFIRM_ORD.get(
            d.get('income_confirmation', 'none'), 0),
        'property_ownership_ord': PROPERTY_ORD.get(
            d.get('property_ownership', 'rent'), 0),
        # one-hot marital
        'marital_married': int(marital == 'married'),
        'marital_divorced': int(marital == 'divorced'),
        'marital_widowed': int(marital == 'widowed'),
        'marital_civil': int(marital == 'civil_marriage'),
        # one-hot employment
        'empl_self_employed': int(empl == 'self_employed'),
        'empl_business': int(empl == 'business_owner'),
        'empl_freelance': int(empl == 'freelance'),
        'empl_retired': int(empl == 'retired'),
        'empl_unemployed': int(empl == 'unemployed'),
        'empl_military': int(empl == 'military'),
        'empl_civil_servant': int(empl == 'civil_servant'),
        'empl_student': int(empl == 'student'),
    }
    return row


class CreditApprovalModel:
    """
    Модель прогнозирования одобрения кредитной заявки.

    Алгоритм: GradientBoostingClassifier (sklearn).
    """

    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names: List[str] = FEATURE_COLUMNS[:]
        self.is_fitted = False

    # ------------------------------------------------------------------ train
    def train(self, applications, labels) -> Dict[str, Any]:
        """
        Обучение модели.

        Args:
            applications: список объектов CreditApplication или словарей
            labels: список целевых меток (1=одобрено, 0=отказ)

        Returns:
            Словарь с метриками качества модели.
        """
        _ensure_ml_imports()
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.model_selection import train_test_split, cross_val_score
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score

        rows = [_extract_features_from_application(a) for a in applications]
        df = pd.DataFrame(rows, columns=self.feature_names)
        X = df.values.astype(float)
        y = np.array(labels, dtype=int)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=y,
        )

        self.scaler = StandardScaler()
        X_train_s = self.scaler.fit_transform(X_train)
        X_test_s = self.scaler.transform(X_test)

        self.model = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=5,
            min_samples_split=10,
            min_samples_leaf=5,
            subsample=0.8,
            random_state=42,
        )
        self.model.fit(X_train_s, y_train)
        self.is_fitted = True

        y_pred = self.model.predict(X_test_s)
        y_proba = self.model.predict_proba(X_test_s)

        acc = accuracy_score(y_test, y_pred)
        try:
            auc = roc_auc_score(y_test, y_proba[:, 1])
        except Exception:
            auc = 0.0

        cv_scores = cross_val_score(self.model, self.scaler.transform(X), y, cv=5, scoring='accuracy')

        metrics = {
            'accuracy': float(acc),
            'roc_auc': float(auc),
            'cv_mean': float(cv_scores.mean()),
            'cv_std': float(cv_scores.std()),
            'train_size': len(X_train),
            'test_size': len(X_test),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
            'classification_report': classification_report(
                y_test, y_pred, target_names=['Отказ', 'Одобрено'],
                output_dict=True
            ),
            'feature_importances': dict(zip(
                self.feature_names,
                [float(v) for v in self.model.feature_importances_]
            )),
        }

        self._save()
        logger.info("CreditApprovalModel trained — acc=%.3f  AUC=%.3f", acc, auc)
        return metrics

    # --------------------------------------------------------------- predict
    def predict(self, application) -> Dict[str, Any]:
        """
        Прогноз по одной заявке.

        Returns:
            {
                approved_probability: float,
                decision: 'approved' | 'rejected',
                confidence: float,
                risk_factors: [...],
                model_type: 'gradient_boosting' | 'rule_based',
            }
        """
        if not self.is_fitted:
            if not self._load():
                return self._rule_based(application)

        row = _extract_features_from_application(application)

        # === Жёсткие бизнес-правила (override ML-модели) ===
        hard_reject = self._hard_reject_check(row)
        if hard_reject is not None:
            return hard_reject

        X = np.array([[row[c] for c in self.feature_names]], dtype=float)
        X_s = self.scaler.transform(X)

        proba = self.model.predict_proba(X_s)[0]
        approved_prob = float(proba[1]) if len(proba) > 1 else float(proba[0])

        # Корректировка вероятности по DTI — модель может ошибаться
        # на экстремальных значениях, которых мало в обучающей выборке
        dti = row.get('dti_ratio', 0)
        if dti > 1.0:
            # Расходы + платёж > дохода — сильный штраф
            penalty = min(approved_prob * 0.7, 0.5)
            approved_prob = max(0.02, approved_prob - penalty)
        elif dti > 0.7:
            penalty = min(approved_prob * 0.3, 0.25)
            approved_prob = max(0.05, approved_prob - penalty)

        decision = 'approved' if approved_prob >= 0.5 else 'rejected'
        confidence = float(max(approved_prob, 1 - approved_prob))

        risk_factors = self._risk_factors(row)

        return {
            'approved_probability': approved_prob,
            'decision': decision,
            'confidence': confidence,
            'risk_factors': risk_factors,
            'model_type': 'gradient_boosting',
        }

    # -------------------------------------------------- hard reject rules
    @staticmethod
    def _hard_reject_check(row: Dict) -> Optional[Dict[str, Any]]:
        """
        Жёсткие бизнес-правила, при которых заявка отклоняется
        вне зависимости от ML-модели.
        """
        factors: List[str] = []
        dti = row.get('dti_ratio', 0)
        income = row.get('total_income', 0)
        expenses = row.get('total_expenses', 0)

        # Расходы превышают доход — автоматический отказ
        if income > 0 and expenses >= income:
            factors.append(f'Расходы ({expenses:,.0f}) превышают доход ({income:,.0f})')

        # Крайне высокая долговая нагрузка (>150%)
        if dti > 1.5:
            factors.append(f'Критическая долговая нагрузка: {dti:.0%}')

        # Нет дохода при запросе кредита
        if income <= 0:
            factors.append('Нулевой доход')

        # Ежемесячный платёж > 80% дохода
        monthly_pay = row.get('monthly_payment_est', 0)
        if income > 0 and monthly_pay > income * 0.8:
            factors.append(f'Платёж ({monthly_pay:,.0f}) > 80% дохода ({income:,.0f})')

        if factors:
            return {
                'approved_probability': max(0.02, 0.15 - len(factors) * 0.04),
                'decision': 'rejected',
                'confidence': 0.95,
                'risk_factors': factors,
                'model_type': 'rule_override',
            }
        return None

    # -------------------------------------------------- rule-based fallback
    @staticmethod
    def _rule_based(application) -> Dict[str, Any]:
        row = _extract_features_from_application(
            application if isinstance(application, dict) else application
        )
        score = 0.5
        factors: List[str] = []

        # Жёсткие отказы
        dti = row['dti_ratio']
        income = row['total_income']
        expenses = row['total_expenses']

        if income > 0 and expenses >= income:
            score = 0.05
            factors.append(f'Расходы ({expenses:,.0f}) превышают доход ({income:,.0f})')
        elif dti > 1.5:
            score = 0.05
            factors.append(f'Критическая долговая нагрузка: {dti:.0%}')
        elif income <= 0:
            score = 0.05
            factors.append('Нулевой доход')
        else:
            # DTI-штрафы
            if dti > 0.8:
                score -= 0.35
                factors.append(f'Очень высокая долговая нагрузка: {dti:.0%}')
            elif dti > 0.6:
                score -= 0.2
                factors.append(f'Высокая долговая нагрузка: {dti:.0%}')
            elif dti < 0.3:
                score += 0.1

        if row['has_overdue_history']:
            score -= 0.25
            factors.append('Негативная кредитная история')
        if row.get('empl_unemployed') or row.get('empl_student'):
            score -= 0.2
            factors.append('Безработный/студент')
        if row.get('dependents_count', 0) >= 4:
            score -= 0.1
            factors.append(f"Много иждивенцев: {row['dependents_count']}")
        if row['has_collateral']:
            score += 0.1
        if row['has_deposits']:
            score += 0.05
        if row['education_ord'] >= 3:
            score += 0.05
        if row['work_experience_total'] > 60:
            score += 0.05

        score = max(0.0, min(1.0, score))
        return {
            'approved_probability': score,
            'decision': 'approved' if score >= 0.5 else 'rejected',
            'confidence': abs(score - 0.5) * 2,
            'risk_factors': factors,
            'model_type': 'rule_based',
        }

    # --------------------------------------------------------- risk factors
    @staticmethod
    def _risk_factors(row: Dict) -> List[str]:
        factors: List[str] = []
        income = row.get('total_income', 0)
        expenses = row.get('total_expenses', 0)
        dti = row.get('dti_ratio', 0)
        monthly_pay = row.get('monthly_payment_est', 0)

        if income > 0 and expenses >= income:
            factors.append(f'Расходы ({expenses:,.0f} ₽) превышают доход ({income:,.0f} ₽)')
        elif dti > 1.0:
            factors.append(f'Критическая долговая нагрузка: {dti:.0%}')
        elif dti > 0.6:
            factors.append(f'Высокая долговая нагрузка: {dti:.0%}')

        if income > 0 and monthly_pay > income * 0.5:
            factors.append(f'Платёж ({monthly_pay:,.0f} ₽) > 50% дохода')

        if row.get('has_overdue_history'):
            factors.append('Негативная кредитная история')
        if income <= 0:
            factors.append('Нет подтверждённого дохода')
        if row.get('empl_unemployed'):
            factors.append('Безработный')
        if row.get('empl_student'):
            factors.append('Студент (нестабильный доход)')
        if row.get('dependents_count', 0) >= 3:
            factors.append(f"Много иждивенцев: {row['dependents_count']}")
        if row.get('max_overdue_days', 0) > 30:
            factors.append(f"Макс. просрочка {row['max_overdue_days']} дн.")
        if row.get('current_loans_count', 0) >= 3:
            factors.append(f"Действующих кредитов: {row['current_loans_count']}")
        return factors

    # ------------------------------------------------------------- save/load
    def _save(self):
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        with open(MODEL_PATH, 'wb') as f:
            pickle.dump(self.model, f)
        with open(SCALER_PATH, 'wb') as f:
            pickle.dump(self.scaler, f)
        with open(FEATURES_PATH, 'wb') as f:
            pickle.dump(self.feature_names, f)
        logger.info("CreditApprovalModel saved to %s", MODEL_DIR)

    def _load(self) -> bool:
        try:
            if not MODEL_PATH.exists():
                return False
            with open(MODEL_PATH, 'rb') as f:
                self.model = pickle.load(f)
            with open(SCALER_PATH, 'rb') as f:
                self.scaler = pickle.load(f)
            if FEATURES_PATH.exists():
                with open(FEATURES_PATH, 'rb') as f:
                    self.feature_names = pickle.load(f)
            self.is_fitted = True
            logger.info("CreditApprovalModel loaded")
            return True
        except Exception as e:
            logger.error("CreditApprovalModel load error: %s", e)
            return False


# =====================================================================
# Публичный API (совместим со старым score_application и loan_predictor)
# =====================================================================

_model: Optional[CreditApprovalModel] = None


def get_model() -> CreditApprovalModel:
    global _model
    if _model is None:
        _model = CreditApprovalModel()
        _model._load()
    return _model


def score_application(application_data: dict) -> float:
    """
    Обратная совместимость: возвращает вероятность одобрения (0..1).
    """
    result = get_model().predict(application_data)
    return result['approved_probability']
