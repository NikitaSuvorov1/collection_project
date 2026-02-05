"""
Модель прогнозирования одобрения кредитной заявки.

Использует RandomForestClassifier для предсказания вероятности одобрения/отказа
на основе данных клиента и параметров заявки.

Референсы:
- GeeksforGeeks: Loan Approval Prediction using Machine Learning
- GitHub: s0nya23/Loan-Approval-Prediction
"""

import os
import pickle
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

logger = logging.getLogger(__name__)

# Путь для сохранения обученной модели
MODEL_DIR = Path(__file__).parent / 'saved_models'
MODEL_PATH = MODEL_DIR / 'loan_approval_model.pkl'
ENCODERS_PATH = MODEL_DIR / 'loan_approval_encoders.pkl'


class LoanApprovalPredictor:
    """
    Предиктор для оценки вероятности одобрения кредитной заявки.
    
    Использует следующие признаки:
    - gender: Пол клиента (M/F)
    - marital_status: Семейное положение
    - children_count: Количество детей (dependents)
    - employment: Статус занятости
    - income: Доход клиента (ApplicantIncome)
    - monthly_expenses: Ежемесячные расходы
    - loan_amount: Запрашиваемая сумма кредита (LoanAmount)
    - loan_term: Срок кредита в месяцах (Loan_Amount_Term)
    - credit_history: Кредитная история (наличие просрочек)
    - region: Регион (Property_Area аналог)
    """
    
    # Признаки для модели
    CATEGORICAL_FEATURES = ['gender', 'marital_status', 'employment', 'region']
    NUMERICAL_FEATURES = ['income', 'monthly_expenses', 'loan_amount', 'loan_term', 
                          'children_count', 'credit_history', 'debt_to_income_ratio']
    
    def __init__(self):
        self.model: Optional[RandomForestClassifier] = None
        self.encoders: Dict[str, LabelEncoder] = {}
        self.is_fitted = False
        
    def _prepare_features(self, data: Dict[str, Any]) -> np.ndarray:
        """
        Подготовка признаков для модели.
        
        Args:
            data: Словарь с данными клиента и заявки
            
        Returns:
            numpy array с признаками
        """
        features = []
        
        # Категориальные признаки - кодируем через LabelEncoder
        for feat in self.CATEGORICAL_FEATURES:
            value = str(data.get(feat, 'unknown'))
            if feat in self.encoders:
                # Обработка неизвестных значений
                if value not in self.encoders[feat].classes_:
                    # Используем самый частый класс как дефолт
                    value = self.encoders[feat].classes_[0]
                encoded = self.encoders[feat].transform([value])[0]
            else:
                encoded = 0  # Если энкодер не обучен, используем 0
            features.append(encoded)
        
        # Числовые признаки
        income = float(data.get('income', 0))
        expenses = float(data.get('monthly_expenses', 0))
        loan_amount = float(data.get('loan_amount', 0))
        loan_term = int(data.get('loan_term', 12))
        children = int(data.get('children_count', 0))
        credit_history = int(data.get('credit_history', 1))  # 1 = хорошая история
        
        # Рассчитываем debt-to-income ratio
        if income > 0:
            dti = (loan_amount / loan_term + expenses) / income
        else:
            dti = 1.0
            
        features.extend([
            income,
            expenses,
            loan_amount,
            loan_term,
            children,
            credit_history,
            dti
        ])
        
        return np.array(features).reshape(1, -1)
    
    def fit(self, training_data: list, labels: list) -> Dict[str, Any]:
        """
        Обучение модели на данных.
        
        Args:
            training_data: Список словарей с данными клиентов
            labels: Список меток (1 = одобрено, 0 = отказано)
            
        Returns:
            Словарь с метриками обучения
        """
        logger.info(f"Начало обучения модели на {len(training_data)} примерах")
        
        # Сначала обучаем энкодеры на всех данных
        self._fit_encoders(training_data)
        
        # Подготавливаем признаки
        X = []
        for data in training_data:
            features = self._prepare_features(data)
            X.append(features.flatten())
        
        X = np.array(X)
        y = np.array(labels)
        
        # Разбиваем на train/test (60/40 как в референсе)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.4, random_state=42
        )
        
        # Обучаем RandomForest (лучший результат по референсу)
        self.model = RandomForestClassifier(
            n_estimators=100,  # Больше деревьев для лучшего качества
            criterion='entropy',
            max_depth=10,  # Ограничиваем глубину для избежания переобучения
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X_train, y_train)
        self.is_fitted = True
        
        # Оцениваем качество
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        metrics = {
            'accuracy': accuracy,
            'train_size': len(X_train),
            'test_size': len(X_test),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
            'classification_report': classification_report(y_test, y_pred, output_dict=True)
        }
        
        logger.info(f"Модель обучена. Accuracy: {accuracy:.2%}")
        
        # Сохраняем модель
        self.save()
        
        return metrics
    
    def _fit_encoders(self, training_data: list):
        """Обучение LabelEncoder для категориальных признаков."""
        for feat in self.CATEGORICAL_FEATURES:
            values = [str(d.get(feat, 'unknown')) for d in training_data]
            self.encoders[feat] = LabelEncoder()
            self.encoders[feat].fit(values)
    
    def predict(self, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Предсказание вероятности одобрения заявки.
        
        Args:
            application_data: Словарь с данными клиента и заявки:
                - gender: Пол ('M' или 'F')
                - marital_status: Семейное положение
                - employment: Статус занятости
                - income: Доход
                - monthly_expenses: Расходы
                - loan_amount: Сумма кредита
                - loan_term: Срок кредита (месяцев)
                - children_count: Количество детей
                - credit_history: Кредитная история (1=хорошая, 0=плохая)
                - region: Регион
                
        Returns:
            Словарь с результатами:
                - approved_probability: Вероятность одобрения (0-1)
                - decision: Рекомендуемое решение ('approved'/'rejected')
                - confidence: Уверенность в решении
                - risk_factors: Список факторов риска
        """
        if not self.is_fitted:
            # Пробуем загрузить сохранённую модель
            if not self.load():
                return self._rule_based_prediction(application_data)
        
        features = self._prepare_features(application_data)
        
        # Получаем вероятности классов
        probabilities = self.model.predict_proba(features)[0]
        
        # Класс 1 = одобрено
        approved_prob = probabilities[1] if len(probabilities) > 1 else probabilities[0]
        
        # Определяем решение
        decision = 'approved' if approved_prob >= 0.5 else 'rejected'
        confidence = max(approved_prob, 1 - approved_prob)
        
        # Анализ факторов риска
        risk_factors = self._analyze_risk_factors(application_data)
        
        return {
            'approved_probability': float(approved_prob),
            'decision': decision,
            'confidence': float(confidence),
            'risk_factors': risk_factors
        }
    
    def _rule_based_prediction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Резервное правило-основанное предсказание, если модель не обучена.
        
        Использует простые эвристики:
        - Кредитная история
        - Соотношение долга к доходу
        - Статус занятости
        """
        logger.warning("Модель не обучена, используется rule-based подход")
        
        income = float(data.get('income', 0))
        expenses = float(data.get('monthly_expenses', 0))
        loan_amount = float(data.get('loan_amount', 0))
        loan_term = int(data.get('loan_term', 12))
        credit_history = int(data.get('credit_history', 1))
        employment = data.get('employment', 'unemployed')
        
        score = 0.5  # Базовый балл
        risk_factors = []
        
        # Кредитная история (самый важный фактор)
        if credit_history == 1:
            score += 0.2
        else:
            score -= 0.3
            risk_factors.append('Плохая кредитная история')
        
        # Соотношение долга к доходу
        if income > 0:
            monthly_payment = loan_amount / loan_term
            dti = (monthly_payment + expenses) / income
            
            if dti < 0.3:
                score += 0.15
            elif dti < 0.5:
                score += 0.05
            elif dti > 0.7:
                score -= 0.2
                risk_factors.append(f'Высокая долговая нагрузка ({dti:.0%})')
        else:
            score -= 0.25
            risk_factors.append('Нет подтверждённого дохода')
        
        # Занятость
        if employment in ['employed', 'self_employed']:
            score += 0.1
        elif employment == 'unemployed':
            score -= 0.2
            risk_factors.append('Безработный')
        
        # Нормализуем
        score = max(0, min(1, score))
        
        return {
            'approved_probability': score,
            'decision': 'approved' if score >= 0.5 else 'rejected',
            'confidence': abs(score - 0.5) * 2,
            'risk_factors': risk_factors,
            'model_type': 'rule_based'
        }
    
    def _analyze_risk_factors(self, data: Dict[str, Any]) -> list:
        """Анализ факторов риска по данным заявки."""
        risk_factors = []
        
        income = float(data.get('income', 0))
        expenses = float(data.get('monthly_expenses', 0))
        loan_amount = float(data.get('loan_amount', 0))
        loan_term = int(data.get('loan_term', 12))
        credit_history = int(data.get('credit_history', 1))
        employment = data.get('employment', 'unknown')
        children = int(data.get('children_count', 0))
        
        # Кредитная история
        if credit_history == 0:
            risk_factors.append('Негативная кредитная история')
        
        # Долговая нагрузка
        if income > 0:
            monthly_payment = loan_amount / loan_term
            dti = (monthly_payment + expenses) / income
            if dti > 0.6:
                risk_factors.append(f'Высокая долговая нагрузка: {dti:.0%} от дохода')
        else:
            risk_factors.append('Отсутствие дохода')
        
        # Занятость
        if employment == 'unemployed':
            risk_factors.append('Отсутствие постоянной работы')
        
        # Количество иждивенцев
        if children >= 3:
            risk_factors.append(f'Большое количество иждивенцев: {children}')
        
        # Большая сумма кредита
        if income > 0 and loan_amount > income * 24:
            risk_factors.append('Запрашиваемая сумма превышает 2-летний доход')
        
        return risk_factors
    
    def save(self) -> bool:
        """Сохранение модели и энкодеров в файл."""
        try:
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(MODEL_PATH, 'wb') as f:
                pickle.dump(self.model, f)
                
            with open(ENCODERS_PATH, 'wb') as f:
                pickle.dump(self.encoders, f)
                
            logger.info(f"Модель сохранена в {MODEL_PATH}")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения модели: {e}")
            return False
    
    def load(self) -> bool:
        """Загрузка модели и энкодеров из файла."""
        try:
            if not MODEL_PATH.exists() or not ENCODERS_PATH.exists():
                logger.warning("Файлы модели не найдены")
                return False
                
            with open(MODEL_PATH, 'rb') as f:
                self.model = pickle.load(f)
                
            with open(ENCODERS_PATH, 'rb') as f:
                self.encoders = pickle.load(f)
                
            self.is_fitted = True
            logger.info("Модель загружена успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            return False


# Глобальный экземпляр предиктора
_predictor: Optional[LoanApprovalPredictor] = None


def get_predictor() -> LoanApprovalPredictor:
    """Получение singleton экземпляра предиктора."""
    global _predictor
    if _predictor is None:
        _predictor = LoanApprovalPredictor()
        _predictor.load()  # Попытка загрузить обученную модель
    return _predictor


def predict_loan_approval(application_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Основная функция для предсказания одобрения кредита.
    
    Пример использования:
    ```python
    result = predict_loan_approval({
        'gender': 'M',
        'marital_status': 'married',
        'employment': 'employed',
        'income': 100000,
        'monthly_expenses': 30000,
        'loan_amount': 500000,
        'loan_term': 36,
        'children_count': 2,
        'credit_history': 1,
        'region': 'Москва'
    })
    
    print(f"Вероятность одобрения: {result['approved_probability']:.1%}")
    print(f"Решение: {result['decision']}")
    ```
    """
    predictor = get_predictor()
    return predictor.predict(application_data)
