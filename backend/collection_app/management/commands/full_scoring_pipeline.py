"""
Полный конвейер скоринга: обучение модели → скоринг клиентов → экономическая модель.

Реализует:
  1. Сбор обучающей выборки из Credit→Payment→Intervention
  2. Обучение Gradient Boosting / Random Forest / Logistic Regression
  3. Вычисление метрик: ROC-AUC, Precision, Recall, F1
  4. Построение ROC-кривой (сохраняется в MLModelVersion)
  5. Пересчёт скоринга для всех клиентов → ScoringResult
  6. Экономическая модель: expected_recovery, cost_per_contact, expected_profit
  7. Версионирование модели в БД

Запуск:
    python manage.py full_scoring_pipeline
    python manage.py full_scoring_pipeline --model-type gradient_boosting
    python manage.py full_scoring_pipeline --compare   # сравнение 3 алгоритмов
"""

import json
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
from django.core.management.base import BaseCommand
from django.db.models import Avg, Max, Count, Sum, Q
from django.utils import timezone

from collection_app.models import (
    Client, Credit, Payment, Intervention, ScoringResult,
    TrainingData, MLModelVersion, AuditLog,
)


# Фиксированные признаки (совпадают с overdue_predictor.py)
FEATURE_COLUMNS = [
    'age', 'gender', 'marital_status', 'employment', 'dependents',
    'monthly_income', 'has_other_credits', 'other_credits_count',
    'credit_amount', 'credit_term', 'interest_rate', 'lti_ratio',
    'credit_age', 'credit_status', 'monthly_payment',
    'total_payments', 'overdue_payments', 'max_overdue_days',
    'avg_payment', 'payments_count_12m', 'overdue_count_12m',
    'overdue_share_12m', 'max_overdue_12m',
    'total_interventions', 'completed_interventions', 'promises_count',
]

# Стоимость одного контакта (себестоимость звонка + зарплата оператора)
COST_PER_CONTACT = Decimal('150.00')  # ₽

# Грейды по Score
def score_to_grade(score: int) -> str:
    if score >= 800: return 'A'
    if score >= 700: return 'B'
    if score >= 600: return 'C'
    if score >= 500: return 'D'
    return 'E'


class Command(BaseCommand):
    help = 'Полный конвейер: обучение ML-модели + скоринг + экономическая модель'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model-type', default='gradient_boosting',
            choices=['random_forest', 'gradient_boosting', 'logistic_regression'],
            help='Тип алгоритма (по умолчанию: gradient_boosting)',
        )
        parser.add_argument(
            '--compare', action='store_true',
            help='Сравнить все 3 алгоритма и выбрать лучший',
        )
        parser.add_argument(
            '--skip-scoring', action='store_true',
            help='Только обучение, без пересчёта скоринга',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS(' ПОЛНЫЙ КОНВЕЙЕР СКОРИНГА'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

        # 1. Сбор обучающей выборки
        self.stdout.write('\n📊 Этап 1: Сбор обучающей выборки...')
        records = self._generate_training_data()
        if not records:
            self.stdout.write(self.style.ERROR('Нет данных для обучения.'))
            return

        X, y, feature_names = self._prepare_matrices(records)
        self.stdout.write(f'  Записей: {len(records)}')
        self.stdout.write(f'  Признаков: {len(feature_names)}')

        class_counts = dict(zip(*np.unique(y, return_counts=True)))
        for cls, cnt in sorted(class_counts.items()):
            lbl = {0: 'Низкий', 1: 'Средний', 2: 'Высокий'}.get(cls, str(cls))
            self.stdout.write(f'  Класс {cls} ({lbl}): {cnt}')

        # 2. Обучение модели
        if options['compare']:
            self.stdout.write('\n🔬 Этап 2: Сравнение 3 алгоритмов...')
            best_type, best_metrics, best_model, best_scaler, roc_data = self._compare_models(X, y, feature_names)
            model_type = best_type
        else:
            model_type = options['model_type']
            self.stdout.write(f'\n🧠 Этап 2: Обучение модели ({model_type})...')
            best_metrics, best_model, best_scaler, roc_data = self._train_single(X, y, feature_names, model_type)

        self._print_metrics(best_metrics, model_type)

        # 3. Сохранение версии модели
        self.stdout.write('\n💾 Этап 3: Сохранение версии модели...')
        model_version = self._save_model_version(model_type, best_metrics, roc_data, feature_names, len(records))

        # 4. Пересчёт скоринга
        if not options['skip_scoring']:
            self.stdout.write('\n📈 Этап 4: Пересчёт скоринга для всех клиентов...')
            scored = self._score_all_credits(records, best_model, best_scaler, model_version, best_metrics)
            self.stdout.write(self.style.SUCCESS(f'  Обработано: {scored} кредитов'))

        # 5. Аудит
        AuditLog.objects.create(
            action='model_train',
            details={
                'model_type': model_type,
                'version': model_version.version,
                'roc_auc': best_metrics['roc_auc'],
                'accuracy': best_metrics['accuracy'],
                'training_size': len(records),
            },
            severity='info',
        )

        self.stdout.write(self.style.SUCCESS('\n✅ Конвейер завершён успешно!'))

    # ========================== DATA GENERATION ==========================

    def _generate_training_data(self):
        """Генерация обучающей выборки из реальных таблиц БД."""
        credits = Credit.objects.select_related('client').prefetch_related(
            'payments', 'interventions'
        ).all()

        records = []
        today = date.today()
        year_ago = today - timedelta(days=365)

        for credit in credits:
            client = credit.client
            payments = credit.payments.all()
            interventions = credit.interventions.all()

            # Клиентские признаки
            age = (today - client.birth_date).days / 365.25 if client.birth_date else 35
            gender = 1 if client.gender == 'M' else 0
            marital_map = {'single': 0, 'married': 1, 'divorced': 2, 'widowed': 3}
            marital = marital_map.get(client.marital_status, 0)
            empl_map = {'employed': 1, 'self_employed': 2, 'unemployed': 0, 'retired': 3, 'student': 4}
            employment = empl_map.get(client.employment, 1)
            dependents = client.children_count or 0
            monthly_income = float(client.income) if client.income else 0
            other_count = Credit.objects.filter(client=client).exclude(id=credit.id).count()

            # Кредитные признаки
            credit_amount = float(credit.principal_amount) if credit.principal_amount else 0
            credit_term_days = (
                (credit.planned_close_date - credit.open_date).days
                if credit.planned_close_date and credit.open_date else 365
            )
            credit_term = max(credit_term_days // 30, 1)
            interest_rate = float(credit.interest_rate) if credit.interest_rate else 0
            monthly_pay = float(credit.monthly_payment) if credit.monthly_payment else 0
            lti_ratio = (credit_amount / (monthly_income * 12)) if monthly_income > 0 else 0
            credit_age = (today - credit.open_date).days if credit.open_date else 0
            status_map = {'active': 1, 'closed': 0, 'overdue': 2, 'default': 3,
                          'restructured': 4, 'legal': 5, 'sold': 6, 'written_off': 7}
            credit_status = status_map.get(credit.status, 1)

            # Платёжная дисциплина
            total_payments = payments.count()
            overdue_payments = payments.filter(overdue_days__gt=0).count()
            max_od = payments.aggregate(m=Max('overdue_days'))['m'] or 0
            avg_pay = payments.aggregate(a=Avg('amount'))['a'] or 0
            payments_12m = payments.filter(payment_date__gte=year_ago)
            p12_count = payments_12m.count()
            od12_count = payments_12m.filter(overdue_days__gt=0).count()
            od12_share = od12_count / p12_count if p12_count > 0 else 0
            max_od_12m = payments_12m.aggregate(m=Max('overdue_days'))['m'] or 0

            # Взаимодействия
            total_iv = interventions.count()
            completed_iv = interventions.filter(status='completed').count()
            promises = interventions.filter(status='promise').count()

            # Целевая переменная — более гранулярная для обучения
            # используем комбинацию payment discipline + overdue severity
            overdue_ratio = overdue_payments / total_payments if total_payments > 0 else 0.5

            # Калькулируем risk_score (чем выше → выше риск)
            risk_score = 0.0

            # Статус кредита
            if credit.status in ('default', 'legal', 'sold', 'written_off'):
                risk_score += 40
            elif credit.status == 'overdue':
                risk_score += 20
            elif credit.status == 'restructured':
                risk_score += 15

            # Просрочка
            risk_score += min(max_od / 3.0, 20)  # до +20 за макс просрочку
            risk_score += overdue_ratio * 15      # до +15 за долю просрочек
            risk_score += od12_share * 10         # до +10 за долю просрочек за 12м

            # LTI
            if lti_ratio > 0.5:
                risk_score += 5
            if lti_ratio > 0.8:
                risk_score += 5

            # Нет платежей — повышенный риск
            if total_payments == 0:
                risk_score += 10

            # Обещания без выполнения (в % от контактов)
            if total_iv > 0 and promises > 0 and completed_iv / total_iv < 0.3:
                risk_score += 5

            # Категоризация по risk_score
            if risk_score >= 50:
                risk_category = 2  # Высокий
            elif risk_score >= 25:
                risk_category = 1  # Средний
            else:
                risk_category = 0  # Низкий

            records.append({
                'client_id': client.id,
                'credit_id': credit.id,
                'overdue_amount': float(credit.states.order_by('-state_date').first().overdue_principal)
                    if credit.states.exists() else 0,
                'age': age, 'gender': gender, 'marital_status': marital,
                'employment': employment, 'dependents': dependents,
                'monthly_income': monthly_income,
                'has_other_credits': 1 if other_count > 0 else 0,
                'other_credits_count': other_count,
                'credit_amount': credit_amount, 'credit_term': credit_term,
                'interest_rate': interest_rate, 'lti_ratio': lti_ratio,
                'credit_age': credit_age, 'credit_status': credit_status,
                'monthly_payment': monthly_pay,
                'total_payments': total_payments, 'overdue_payments': overdue_payments,
                'max_overdue_days': max_od, 'avg_payment': float(avg_pay),
                'payments_count_12m': p12_count, 'overdue_count_12m': od12_count,
                'overdue_share_12m': od12_share, 'max_overdue_12m': max_od_12m,
                'total_interventions': total_iv, 'completed_interventions': completed_iv,
                'promises_count': promises,
                'risk_category': risk_category,
            })

        return records

    def _prepare_matrices(self, records):
        X = np.array([[r[f] for f in FEATURE_COLUMNS] for r in records], dtype=float)
        y = np.array([r['risk_category'] for r in records], dtype=int)
        return X, y, FEATURE_COLUMNS

    # ========================== TRAINING ==========================

    def _train_single(self, X, y, feature_names, model_type):
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
        from sklearn.preprocessing import StandardScaler, label_binarize
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score, f1_score,
            roc_auc_score, confusion_matrix, classification_report, roc_curve, auc
        )

        # Проверяем минимальный размер классов для стратификации
        unique, counts = np.unique(y, return_counts=True)
        min_class_size = counts.min()
        can_stratify = min_class_size >= 2 and len(unique) >= 2

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42,
            stratify=y if can_stratify else None,
        )

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        model_classes = {
            'random_forest': lambda: RandomForestClassifier(
                n_estimators=200, max_depth=12, min_samples_split=8,
                min_samples_leaf=4, class_weight='balanced', random_state=42, n_jobs=-1,
            ),
            'gradient_boosting': lambda: GradientBoostingClassifier(
                n_estimators=200, max_depth=5, learning_rate=0.1,
                min_samples_split=8, random_state=42,
            ),
            'logistic_regression': lambda: LogisticRegression(
                C=1.0, max_iter=1000, random_state=42,
            ),
        }

        model = model_classes[model_type]()
        model.fit(X_train_s, y_train)

        y_pred = model.predict(X_test_s)
        y_proba = model.predict_proba(X_test_s)

        # Метрики
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        rec = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)

        # ROC-AUC (One-vs-Rest для мультикласса)
        classes = sorted(np.unique(y))
        y_test_bin = label_binarize(y_test, classes=classes)
        if y_test_bin.shape[1] == 1:
            y_test_bin = np.column_stack([1 - y_test_bin, y_test_bin])

        try:
            roc_auc_val = roc_auc_score(y_test_bin, y_proba, multi_class='ovr', average='weighted')
        except ValueError:
            roc_auc_val = 0.5

        # ROC-кривая (для класса 2 = Высокий риск, бинарно)
        y_test_high = (y_test == 2).astype(int)
        y_proba_high = y_proba[:, list(model.classes_).index(2)] if 2 in model.classes_ else y_proba[:, -1]
        fpr, tpr, _ = roc_curve(y_test_high, y_proba_high)
        roc_auc_binary = auc(fpr, tpr)

        # Cross-validation (protect against tiny classes)
        n_splits = min(5, min(np.bincount(y_train)) if len(np.bincount(y_train)) > 0 else 2)
        n_splits = max(2, n_splits)
        try:
            cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
            cv_scores = cross_val_score(model, X_train_s, y_train, cv=cv, scoring='accuracy')
        except ValueError:
            from sklearn.model_selection import KFold
            cv = KFold(n_splits=min(5, len(y_train)), shuffle=True, random_state=42)
            cv_scores = cross_val_score(model, X_train_s, y_train, cv=cv, scoring='accuracy')

        # Feature importance
        if hasattr(model, 'feature_importances_'):
            fi = dict(zip(feature_names, [float(v) for v in model.feature_importances_]))
        elif hasattr(model, 'coef_'):
            fi = dict(zip(feature_names, [float(v) for v in np.abs(model.coef_).mean(axis=0)]))
        else:
            fi = {}

        cm = confusion_matrix(y_test, y_pred).tolist()
        unique_labels = sorted(np.unique(np.concatenate([y_test, y_pred])))
        label_names = {0: 'Низкий', 1: 'Средний', 2: 'Высокий'}
        target_names = [label_names.get(l, str(l)) for l in unique_labels]
        report = classification_report(
            y_test, y_pred,
            labels=unique_labels,
            target_names=target_names,
            output_dict=True, zero_division=0,
        )

        metrics = {
            'accuracy': float(acc),
            'precision': float(prec),
            'recall': float(rec),
            'f1_score': float(f1),
            'roc_auc': float(roc_auc_val) if not np.isnan(roc_auc_val) else 0.0,
            'roc_auc_binary': float(roc_auc_binary) if not np.isnan(roc_auc_binary) else 0.0,
            'cv_mean': float(cv_scores.mean()),
            'cv_std': float(cv_scores.std()),
            'confusion_matrix': cm,
            'classification_report': report,
            'feature_importances': fi,
        }

        roc_data = {
            'fpr': [float(v) for v in fpr],
            'tpr': [float(v) for v in tpr],
        }

        return metrics, model, scaler, roc_data

    def _compare_models(self, X, y, feature_names):
        """Сравнение 3 алгоритмов, возврат лучшего."""
        results = {}
        for mt in ['random_forest', 'gradient_boosting', 'logistic_regression']:
            metrics, model, scaler, roc_data = self._train_single(X, y, feature_names, mt)
            results[mt] = (metrics, model, scaler, roc_data)
            self.stdout.write(
                f'  {mt:<25s} ROC-AUC={metrics["roc_auc"]:.4f}  '
                f'Acc={metrics["accuracy"]:.4f}  F1={metrics["f1_score"]:.4f}'
            )

        best_type = max(results, key=lambda k: results[k][0]['roc_auc'] if not np.isnan(results[k][0]['roc_auc']) else results[k][0]['f1_score'])
        self.stdout.write(self.style.SUCCESS(f'\n  🏆 Лучшая модель: {best_type}'))
        best = results[best_type]
        return best_type, best[0], best[1], best[2], best[3]

    def _print_metrics(self, metrics, model_type):
        self.stdout.write(self.style.SUCCESS(f'\n  === Метрики ({model_type}) ==='))
        self.stdout.write(f'  Accuracy:    {metrics["accuracy"]:.4f}')
        self.stdout.write(f'  Precision:   {metrics["precision"]:.4f}')
        self.stdout.write(f'  Recall:      {metrics["recall"]:.4f}')
        self.stdout.write(f'  F1-Score:    {metrics["f1_score"]:.4f}')
        self.stdout.write(f'  ROC-AUC:     {metrics["roc_auc"]:.4f}')
        self.stdout.write(f'  ROC-AUC(bin):{metrics["roc_auc_binary"]:.4f}')
        self.stdout.write(f'  CV:          {metrics["cv_mean"]:.4f} ± {metrics["cv_std"]:.4f}')

        # Confusion matrix
        cm = metrics['confusion_matrix']
        self.stdout.write('\n  Матрица ошибок:')
        labels = ['Низкий', 'Средний', 'Высокий']
        for i, row in enumerate(cm):
            self.stdout.write(f'    {labels[i]:>10s}: {row}')

        # Top features
        fi = metrics.get('feature_importances', {})
        if fi:
            top = sorted(fi.items(), key=lambda x: x[1], reverse=True)[:7]
            self.stdout.write('\n  Топ-7 признаков:')
            for name, imp in top:
                self.stdout.write(f'    {name:30s} {imp:.4f}')

        # Per-class report
        report = metrics.get('classification_report', {})
        self.stdout.write('\n  Per-class:')
        for cls_name in ('Низкий', 'Средний', 'Высокий'):
            if cls_name in report:
                r = report[cls_name]
                self.stdout.write(
                    f'    {cls_name:10s}: P={r["precision"]:.3f}  '
                    f'R={r["recall"]:.3f}  F1={r["f1-score"]:.3f}  N={r["support"]}'
                )

    # ========================== MODEL VERSIONING ==========================

    def _save_model_version(self, model_type, metrics, roc_data, feature_names, training_size):
        version_str = timezone.now().strftime('%Y%m%d_%H%M%S')

        # Деактивируем предыдущие
        MLModelVersion.objects.filter(name='overdue_scoring', is_active=True).update(is_active=False)

        mv = MLModelVersion.objects.create(
            name='overdue_scoring',
            version=version_str,
            model_type=model_type,
            accuracy=metrics['accuracy'],
            precision=metrics['precision'],
            recall=metrics['recall'],
            f1_score=metrics['f1_score'],
            roc_auc=metrics['roc_auc'],
            cv_mean=metrics['cv_mean'],
            cv_std=metrics['cv_std'],
            hyperparameters={},
            feature_names=feature_names,
            feature_importances=metrics.get('feature_importances', {}),
            confusion_matrix=metrics['confusion_matrix'],
            roc_curve_fpr=roc_data['fpr'],
            roc_curve_tpr=roc_data['tpr'],
            training_data_size=training_size,
            is_active=True,
        )

        self.stdout.write(f'  Версия: {mv.version}  ROC-AUC: {mv.roc_auc:.4f}')
        return mv

    # ========================== SCORING + ECONOMIC MODEL ==========================

    def _score_all_credits(self, records, model, scaler, model_version, metrics):
        """Пересчёт скоринга для всех кредитов + экономическая модель."""
        today = date.today()
        scored = 0

        for rec in records:
            vec = np.array([[rec[f] for f in FEATURE_COLUMNS]], dtype=float)
            vec_s = scaler.transform(vec)

            pred = int(model.predict(vec_s)[0])
            proba = model.predict_proba(vec_s)[0]

            # Probability of default (P(class=2) — высокий риск)
            if 2 in list(model.classes_):
                pd_val = float(proba[list(model.classes_).index(2)])
            else:
                pd_val = float(proba[-1])

            # Score = 600 - 50·log2(PD / (1-PD))
            if pd_val <= 0:
                score_val = 850
            elif pd_val >= 1:
                score_val = 300
            else:
                odds = pd_val / (1 - pd_val)
                score_val = int(np.clip(600 - 50 * np.log2(odds), 300, 850))

            grade = score_to_grade(score_val)

            # Сегмент риска
            segment_map = {0: 'low', 1: 'medium', 2: 'high'}
            if pred == 2 and pd_val > 0.7:
                segment = 'critical'
            else:
                segment = segment_map.get(pred, 'medium')

            # === Экономическая модель ===
            # P_recovery — вероятность возврата (инверсия PD)
            p_recovery = 1.0 - pd_val
            overdue_amount = Decimal(str(rec.get('overdue_amount', 0)))

            # expected_recovery = P_recovery × overdue_amount
            expected_recovery = Decimal(str(round(p_recovery * float(overdue_amount), 2)))

            # expected_profit = P_recovery × debt - call_cost
            expected_profit = expected_recovery - COST_PER_CONTACT

            ScoringResult.objects.update_or_create(
                client_id=rec['client_id'],
                credit_id=rec['credit_id'],
                model_version=model_version.version,
                defaults={
                    'calculation_date': today,
                    'probability': pd_val,
                    'risk_segment': segment,
                    'score_value': score_val,
                    'model_type': model_version.model_type,
                    'roc_auc': metrics['roc_auc'],
                    'grade': grade,
                    'expected_recovery': expected_recovery,
                    'cost_per_contact': COST_PER_CONTACT,
                    'expected_profit': expected_profit,
                },
            )
            scored += 1

        return scored
