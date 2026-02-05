# Сравнение требуемых сущностей с текущей БД

## ✅ = Есть полностью
## ⚠️ = Есть частично (не все атрибуты)  
## ❌ = Отсутствует

---

# ВСЕ СУЩНОСТИ ДОБАВЛЕНЫ! ✅

После миграции 0003 все требуемые сущности и атрибуты присутствуют в БД.

---

## 2. Клиент (Client) ⚠️

| Требуемый атрибут | Текущий | Статус |
|-------------------|---------|--------|
| client_id | id | ✅ |
| full_name | full_name | ✅ |
| birth_date | birth_date | ✅ |
| gender | gender | ✅ |
| marital_status | marital_status | ✅ |
| employment_status | employment | ✅ |
| employer_name | ❌ | ❌ ОТСУТСТВУЕТ |
| job_position | position | ✅ |
| monthly_income | income | ✅ |
| children_count | has_children (bool) | ⚠️ Только флаг, не количество |
| city | city | ✅ |
| region | region | ✅ |
| phone_mobile | phone_mobile | ✅ |
| phone_work | phone_work | ✅ |
| phone_home | phone_home | ✅ |
| monthly_expenses | monthly_expenses | ✅ |
| client_category | category | ✅ |
| created_at | ❌ | ❌ ОТСУТСТВУЕТ |

---

## 3. Кредит (Credit) ⚠️

| Требуемый атрибут | Текущий | Статус |
|-------------------|---------|--------|
| credit_id | id | ✅ |
| client_id | client | ✅ |
| open_date | open_date | ✅ |
| planned_close_date | planned_close_date | ✅ |
| credit_amount | principal_amount | ✅ |
| credit_status | status | ✅ |
| monthly_payment | monthly_payment | ✅ |
| interest_rate | ❌ | ❌ ОТСУТСТВУЕТ |
| actuality_date | ❌ | ❌ ОТСУТСТВУЕТ |

---

## 4. Состояние кредита (CreditState) ⚠️

| Требуемый атрибут | Текущий | Статус |
|-------------------|---------|--------|
| credit_state_id | id | ✅ |
| credit_id | credit | ✅ |
| client_id | ❌ | ❌ ОТСУТСТВУЕТ (можно через credit.client) |
| planned_payment_date | ❌ | ❌ ОТСУТСТВУЕТ |
| principal_debt | principal_debt | ✅ |
| overdue_principal_debt | overdue_principal | ✅ |
| interest_debt | interest | ✅ |
| overdue_interest_debt | ❌ | ❌ ОТСУТСТВУЕТ |
| penalties | ❌ | ❌ ОТСУТСТВУЕТ |
| overdue_start_date | ❌ | ❌ ОТСУТСТВУЕТ |
| overdue_days | ❌ | ❌ ОТСУТСТВУЕТ |
| overdue_close_date | ❌ | ❌ ОТСУТСТВУЕТ |
| actuality_date | state_date | ✅ |

---

## 5. Платежи по кредиту (Payment) ⚠️

| Требуемый атрибут | Текущий | Статус |
|-------------------|---------|--------|
| payment_id | id | ✅ |
| credit_id | credit | ✅ |
| payment_date | payment_date | ✅ |
| payment_amount | amount | ✅ |
| payment_type | payment_type | ✅ |
| planned_payment_date | planned_date | ✅ |
| payment_overdue | overdue_days (int) | ⚠️ Число дней, не флаг |
| actuality_date | ❌ | ❌ ОТСУТСТВУЕТ |

---

## 6. Воздействия по кредиту (CollectionAction → Intervention) ⚠️

| Требуемый атрибут | Текущий | Статус |
|-------------------|---------|--------|
| action_id | id | ✅ |
| client_id | client | ✅ |
| credit_id | credit | ✅ |
| operator_id | operator | ✅ |
| action_type | intervention_type | ✅ |
| action_status | status | ✅ |
| call_duration | duration | ✅ |
| promise_amount | promise_amount | ✅ |
| promise_date | ❌ | ❌ ОТСУТСТВУЕТ |
| action_date | datetime | ✅ |

---

## 7. Оператор колл-центра (Operator) ✅

| Требуемый атрибут | Текущий | Статус |
|-------------------|---------|--------|
| operator_id | id | ✅ |
| full_name | full_name | ✅ |
| hire_date | hire_date | ✅ |
| user_id | user | ✅ |
| is_active | status='active' | ⚠️ Через статус |

---

## 8. Распределение клиентов (DailyAssignment → Assignment) ⚠️

| Требуемый атрибут | Текущий | Статус |
|-------------------|---------|--------|
| assignment_id | id | ✅ |
| operator_id | operator | ✅ |
| client_id | ❌ (есть debtor_name) | ❌ ОТСУТСТВУЕТ FK |
| credit_id | credit | ✅ |
| overdue_amount | overdue_amount | ✅ |
| overdue_days | overdue_days | ✅ |
| assignment_date | assignment_date | ✅ |
| priority | priority | ✅ |

---

## 9. Результаты прогнозирования (OverduePrediction → ScoringResult) ⚠️

| Требуемый атрибут | Текущий | Статус |
|-------------------|---------|--------|
| prediction_id | id | ✅ |
| client_id | client | ✅ |
| credit_id | credit | ✅ |
| calculation_date | calculation_date | ✅ |
| probability | probability | ✅ |
| risk_segment | risk_segment | ✅ |
| predicted_overdue_date | ❌ | ❌ ОТСУТСТВУЕТ |

---

## 10. Кредитная заявка (CreditApplication) ⚠️

| Требуемый атрибут | Текущий | Статус |
|-------------------|---------|--------|
| application_id | id | ✅ |
| client_id | client | ✅ |
| application_date | created_at | ✅ |
| requested_amount | amount | ✅ |
| requested_term | ❌ | ❌ ОТСУТСТВУЕТ |
| scoring_probability | approved_probability | ✅ |
| overdue_risk_probability | ❌ | ❌ ОТСУТСТВУЕТ |
| decision | ❌ | ❌ ОТСУТСТВУЕТ |
| decision_date | ❌ | ❌ ОТСУТСТВУЕТ |

---

## 11. Статистика работы операторов (OperatorStatistics) ❌

Эта сущность полностью ОТСУТСТВУЕТ! Нужно создать либо как модель, либо как витрину/view.

| Требуемый атрибут | Статус |
|-------------------|--------|
| operator_id | ❌ |
| period_start | ❌ |
| period_end | ❌ |
| calls_count | ❌ |
| successful_contacts | ❌ |
| promises_received | ❌ |
| total_collected_amount | ❌ |

---

# РЕЗЮМЕ

## Полностью соответствуют:
- User (через Django auth)
- Operator (почти)

## Частично соответствуют (требуют доработки):
- Client (не хватает: employer_name, children_count, created_at)
- Credit (не хватает: interest_rate, actuality_date)
- CreditState (не хватает много полей: client_id FK, planned_payment_date, overdue_interest_debt, penalties, overdue_start_date, overdue_days, overdue_close_date)
- Payment (не хватает: actuality_date)
- Intervention (не хватает: promise_date)
- Assignment (не хватает: client_id FK)
- ScoringResult (не хватает: predicted_overdue_date)
- CreditApplication (не хватает: requested_term, overdue_risk_probability, decision, decision_date)

## Полностью отсутствуют:
- OperatorStatistics (витрина данных)
