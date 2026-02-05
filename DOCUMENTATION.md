# Техническая документация
## Система управления взысканием задолженности (Collection Management System)

**Версия:** 1.0.0  
**Дата:** Февраль 2026  
**Авторы:** Команда разработки

---

## Содержание

1. [Общее описание системы](#1-общее-описание-системы)
2. [Архитектура системы](#2-архитектура-системы)
3. [Технологический стек](#3-технологический-стек)
4. [Структура проекта](#4-структура-проекта)
5. [Модель данных](#5-модель-данных)
6. [REST API](#6-rest-api)
7. [Математическое обеспечение](#7-математическое-обеспечение)
8. [ML-модели](#8-ml-модели)
9. [Алгоритмы и методы](#9-алгоритмы-и-методы)
10. [Развёртывание](#10-развёртывание)
11. [Тестирование](#11-тестирование)
12. [Безопасность](#12-безопасность)

---

## 1. Общее описание системы

### 1.1 Назначение

Система управления взысканием задолженности предназначена для автоматизации процессов работы с просроченной задолженностью в банковской сфере. Система обеспечивает:

- Централизованное управление кредитным портфелем
- Автоматическое распределение должников между операторами
- Прогнозирование вероятности возврата задолженности
- Рекомендации по оптимальным стратегиям взыскания
- Психотипирование должников для персонализации коммуникации
- Аналитику эффективности работы отдела

### 1.2 Целевые пользователи

| Роль | Описание | Основные функции |
|------|----------|------------------|
| Оператор | Специалист по взысканию | Работа с очередью должников, совершение звонков, фиксация результатов |
| Старший оператор | Опытный специалист | + Работа со сложными случаями, наставничество |
| Руководитель | Начальник отдела | Аналитика, отчёты, управление командой |
| Администратор | Системный администратор | Настройка системы, управление пользователями |

### 1.3 Ключевые бизнес-процессы

```
┌─────────────────────────────────────────────────────────────────┐
│                    ПРОЦЕСС ВЗЫСКАНИЯ                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Загрузка │ -> │ Скоринг  │ -> │Распреде- │ -> │  Работа  │  │
│  │  данных  │    │          │    │  ление   │    │ оператора│  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │              │               │               │          │
│       v              v               v               v          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │   БД     │    │ML-модели │    │Алгоритмы │    │   NBA    │  │
│  │ клиентов │    │          │    │          │    │ подсказки│  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Архитектура системы

### 2.1 Общая архитектура

Система построена по архитектуре **клиент-сервер** с разделением на фронтенд и бэкенд:

```
┌─────────────────────────────────────────────────────────────────┐
│                        КЛИЕНТ (Frontend)                        │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   React     │  │    Vite     │  │  Recharts   │             │
│  │ Components  │  │   Bundler   │  │   Charts    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                           │                                     │
└───────────────────────────│─────────────────────────────────────┘
                            │ HTTP/REST
                            v
┌─────────────────────────────────────────────────────────────────┐
│                        СЕРВЕР (Backend)                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Django REST Framework                  │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │   │
│  │  │  Views   │  │Serializers│ │  Models  │  │  Auth   │  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    ML Module                             │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │   │
│  │  │ Scoring  │  │Psychotype│  │   NBA    │  │Forecast │  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
└───────────────────────────│─────────────────────────────────────┘
                            │
                            v
┌─────────────────────────────────────────────────────────────────┐
│                      БАЗА ДАННЫХ                                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     SQLite / PostgreSQL                  │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌───────┐  │   │
│  │  │Clients │ │Credits │ │Payments│ │Interv. │ │Scoring│  │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └───────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Компоненты системы

| Компонент | Технология | Порт | Описание |
|-----------|------------|------|----------|
| Frontend | React + Vite | 5173 | SPA-приложение |
| Backend API | Django REST | 8000 | REST API сервер |
| Database | SQLite | - | Хранение данных |
| ML Engine | scikit-learn | - | ML-модели |

### 2.3 Взаимодействие компонентов

```
Frontend (React)
    │
    ├── GET /api/clients/ ────────────> ClientViewSet
    ├── GET /api/credits/ ────────────> CreditViewSet
    ├── GET /api/credits/{id}/ ───────> CreditViewSet.retrieve
    ├── POST /api/applications/predict_approval/ ──> predict_approval
    │
    └── Response (JSON) <──────────────────────────┘
```

---

## 3. Технологический стек

### 3.1 Backend

| Технология | Версия | Назначение |
|------------|--------|------------|
| Python | 3.13 | Язык программирования |
| Django | 6.0.1 | Web-фреймворк |
| Django REST Framework | 3.15+ | REST API |
| scikit-learn | 1.4+ | Машинное обучение |
| pandas | 2.2+ | Обработка данных |
| numpy | 1.26+ | Численные вычисления |
| joblib | 1.3+ | Сериализация моделей |

### 3.2 Frontend

| Технология | Версия | Назначение |
|------------|--------|------------|
| React | 18.2 | UI-библиотека |
| Vite | 5.0 | Сборщик |
| Recharts | 2.10 | Графики и диаграммы |

### 3.3 Инфраструктура

| Технология | Назначение |
|------------|------------|
| SQLite | База данных (dev) |
| PostgreSQL | База данных (prod) |
| Docker | Контейнеризация |
| Git | Версионирование |

---

## 4. Структура проекта

```
collection_app/
├── backend/                      # Серверная часть
│   ├── manage.py                 # Django CLI
│   ├── requirements.txt          # Python зависимости
│   ├── db.sqlite3               # База данных
│   │
│   ├── collection/              # Настройки Django
│   │   ├── settings.py          # Конфигурация
│   │   ├── urls.py              # Корневые URL
│   │   └── wsgi.py              # WSGI точка входа
│   │
│   └── collection_app/          # Основное приложение
│       ├── models.py            # Модели данных
│       ├── views.py             # API endpoints
│       ├── serializers.py       # Сериализаторы
│       ├── urls.py              # URL маршруты
│       ├── admin.py             # Админ-панель
│       │
│       ├── ml/                  # ML модуль
│       │   ├── loan_predictor.py      # Прогноз одобрения
│       │   ├── overdue_scoring.py     # Скоринг просрочки
│       │   ├── psychotyping.py        # Психотипирование
│       │   ├── next_best_action.py    # NBA рекомендации
│       │   ├── return_forecast.py     # Прогноз возврата
│       │   ├── smart_scripts.py       # Умные скрипты
│       │   └── saved_models/          # Сохранённые модели
│       │
│       ├── services/            # Бизнес-логика
│       │   └── distribution.py  # Распределение должников
│       │
│       ├── management/          # Django команды
│       │   └── commands/
│       │       ├── populate_db.py
│       │       ├── run_scoring.py
│       │       └── train_loan_model.py
│       │
│       ├── migrations/          # Миграции БД
│       └── fixtures/            # Тестовые данные
│
├── frontend/                    # Клиентская часть
│   ├── package.json            # NPM зависимости
│   ├── index.html              # HTML точка входа
│   │
│   └── src/
│       ├── main.jsx            # React точка входа
│       ├── App.jsx             # Корневой компонент
│       ├── styles.css          # Глобальные стили
│       │
│       ├── LoginPage.jsx       # Страница входа
│       ├── DashboardPage.jsx   # Дашборд руководителя
│       ├── CreditsPage.jsx     # Реестр кредитов
│       ├── CreditDetailPage.jsx # Детали кредита
│       ├── Client360Page.jsx   # Профиль клиента 360°
│       ├── CollectionDeskApp.jsx # Рабочий стол оператора
│       ├── LoanPredictionPage.jsx # Прогноз одобрения
│       └── DatabaseViewPage.jsx # Просмотр БД
│
├── docker-compose.yml          # Docker конфигурация
├── .gitignore                  # Git исключения
├── README.md                   # Краткое описание
└── DOCUMENTATION.md            # Эта документация
```

---

## 5. Модель данных

### 5.1 ER-диаграмма

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     Client      │       │     Credit      │       │    Payment      │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ PK id           │<──┐   │ PK id           │<──┐   │ PK id           │
│    first_name   │   │   │ FK client_id    │───┘   │ FK credit_id    │───┐
│    last_name    │   └───│    principal    │       │    amount       │   │
│    middle_name  │       │    interest_rate│       │    payment_date │   │
│    phone        │       │    term_months  │       │    payment_type │   │
│    email        │       │    status       │       │    status       │   │
│    birth_date   │       │    product_type │       └─────────────────┘   │
│    gender       │       │    open_date    │                             │
│    income       │       │    close_date   │       ┌─────────────────┐   │
│    employment   │       └─────────────────┘       │  CreditState    │   │
│    address      │                │                ├─────────────────┤   │
│    segment      │                │                │ PK id           │   │
└─────────────────┘                │                │ FK credit_id    │───┤
                                   │                │    report_date  │   │
┌─────────────────┐                │                │    current_bal  │   │
│    Operator     │                │                │    overdue_amt  │   │
├─────────────────┤                │                │    days_past_due│   │
│ PK id           │<───┐           │                │    bucket       │   │
│    full_name    │    │           │                └─────────────────┘   │
│    role         │    │           │                                      │
│    status       │    │           v                                      │
│    current_load │    │   ┌─────────────────┐                           │
│    max_load     │    │   │  Interaction    │                           │
└─────────────────┘    │   ├─────────────────┤                           │
                       │   │ PK id           │                           │
                       └───│ FK operator_id  │                           │
                           │ FK credit_id    │───────────────────────────┘
                           │    type         │
                           │    result       │
                           │    notes        │
                           │    datetime     │
                           └─────────────────┘
```

### 5.2 Описание сущностей

#### 5.2.1 Client (Клиент)

```python
class Client(models.Model):
    """Модель клиента банка"""
    
    # Персональные данные
    first_name = models.CharField(max_length=100)      # Имя
    last_name = models.CharField(max_length=100)       # Фамилия
    middle_name = models.CharField(max_length=100)     # Отчество
    phone = models.CharField(max_length=20)            # Телефон
    email = models.EmailField()                        # Email
    birth_date = models.DateField()                    # Дата рождения
    gender = models.CharField(max_length=1)            # Пол (M/F)
    
    # Финансовые данные
    income = models.DecimalField()                     # Доход
    employment = models.CharField()                    # Тип занятости
    
    # Адрес
    address = models.TextField()                       # Адрес
    
    # Сегментация
    segment = models.CharField()                       # Сегмент клиента
```

**Допустимые значения:**

| Поле | Значения |
|------|----------|
| gender | `M` - мужской, `F` - женский |
| employment | `employed`, `self_employed`, `unemployed`, `retired`, `student` |
| segment | `vip`, `standard`, `problem`, `new` |

#### 5.2.2 Credit (Кредит)

```python
class Credit(models.Model):
    """Модель кредитного договора"""
    
    client = models.ForeignKey(Client)                 # Клиент
    principal_amount = models.DecimalField()           # Сумма кредита
    interest_rate = models.DecimalField()              # Процентная ставка
    term_months = models.IntegerField()                # Срок в месяцах
    monthly_payment = models.DecimalField()            # Ежемесячный платёж
    
    product_type = models.CharField()                  # Тип продукта
    status = models.CharField()                        # Статус
    
    open_date = models.DateField()                     # Дата выдачи
    close_date = models.DateField(null=True)           # Дата закрытия
    next_payment_date = models.DateField()             # След. платёж
```

**Допустимые значения:**

| Поле | Значения |
|------|----------|
| product_type | `consumer` - потребительский, `mortgage` - ипотека, `auto` - автокредит, `credit_card` - кредитная карта |
| status | `active` - активный, `overdue` - просрочка, `default` - дефолт, `closed` - закрыт, `restructured` - реструктуризирован |

#### 5.2.3 CreditState (Состояние кредита)

```python
class CreditState(models.Model):
    """Историческое состояние кредита на дату"""
    
    credit = models.ForeignKey(Credit)                 # Кредит
    report_date = models.DateField()                   # Дата отчёта
    current_balance = models.DecimalField()            # Остаток долга
    overdue_amount = models.DecimalField()             # Просроченная сумма
    days_past_due = models.IntegerField()              # Дней просрочки
    bucket = models.CharField()                        # Bucket
```

**Bucket классификация:**

| Bucket | DPD (Days Past Due) | Описание |
|--------|---------------------|----------|
| 0 | 0 | Без просрочки |
| 1 | 1-30 | Ранняя просрочка |
| 2 | 31-60 | Средняя просрочка |
| 3 | 61-90 | Поздняя просрочка |
| 4 | 91-120 | Серьёзная просрочка |
| 5 | 120+ | Дефолт |

#### 5.2.4 Payment (Платёж)

```python
class Payment(models.Model):
    """Модель платежа по кредиту"""
    
    credit = models.ForeignKey(Credit)                 # Кредит
    amount = models.DecimalField()                     # Сумма
    payment_date = models.DateField()                  # Дата платежа
    payment_type = models.CharField()                  # Тип платежа
    status = models.CharField()                        # Статус
```

#### 5.2.5 Interaction (Взаимодействие)

```python
class Interaction(models.Model):
    """Модель взаимодействия с клиентом"""
    
    credit = models.ForeignKey(Credit)                 # Кредит
    operator = models.ForeignKey(Operator)             # Оператор
    interaction_type = models.CharField()              # Тип (звонок, SMS и т.д.)
    interaction_date = models.DateTimeField()          # Дата/время
    result = models.CharField()                        # Результат
    notes = models.TextField()                         # Заметки
    
    # Для обещаний
    promise_amount = models.DecimalField(null=True)    # Обещанная сумма
    promise_date = models.DateField(null=True)         # Обещанная дата
```

**Результаты взаимодействия:**

| Код | Описание |
|-----|----------|
| `contact` | Состоялся контакт |
| `no_answer` | Нет ответа |
| `promise_to_pay` | Обещание оплатить |
| `refuse` | Отказ платить |
| `callback` | Просьба перезвонить |
| `wrong_number` | Неверный номер |
| `paid` | Оплачено |

---

## 6. REST API

### 6.1 Общая информация

**Base URL:** `http://localhost:8000/api/`

**Формат:** JSON

**Аутентификация:** Token-based (для защищённых endpoints)

### 6.2 Endpoints

#### 6.2.1 Клиенты

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/clients/` | Список клиентов |
| GET | `/api/clients/{id}/` | Детали клиента |
| GET | `/api/clients/{id}/profile_360/` | Полный профиль 360° |
| POST | `/api/clients/` | Создать клиента |
| PUT | `/api/clients/{id}/` | Обновить клиента |
| DELETE | `/api/clients/{id}/` | Удалить клиента |

**Пример ответа GET /api/clients/1/:**
```json
{
  "id": 1,
  "first_name": "Иван",
  "last_name": "Иванов",
  "middle_name": "Петрович",
  "phone": "+7 (999) 123-45-67",
  "email": "ivanov@mail.ru",
  "birth_date": "1985-03-15",
  "gender": "M",
  "income": "85000.00",
  "employment": "employed",
  "address": "г. Москва, ул. Примерная, д. 1",
  "segment": "standard"
}
```

#### 6.2.2 Кредиты

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/credits/` | Список кредитов |
| GET | `/api/credits/{id}/` | Детали кредита |
| GET | `/api/credits/?status=overdue` | Фильтр по статусу |
| GET | `/api/credits/?client={id}` | Кредиты клиента |

**Параметры фильтрации:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| status | string | Фильтр по статусу |
| client | integer | ID клиента |
| product_type | string | Тип продукта |
| min_amount | decimal | Мин. сумма |
| max_amount | decimal | Макс. сумма |

**Пример ответа GET /api/credits/1/:**
```json
{
  "id": 1,
  "client": 1,
  "client_name": "Иванов Иван Петрович",
  "principal_amount": "500000.00",
  "interest_rate": "18.50",
  "term_months": 36,
  "monthly_payment": "18150.00",
  "product_type": "consumer",
  "status": "overdue",
  "open_date": "2024-03-15",
  "close_date": null,
  "next_payment_date": "2026-02-15"
}
```

#### 6.2.3 Состояния кредитов

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/credit-states/` | Все состояния |
| GET | `/api/credit-states/?credit={id}` | Состояния кредита |

#### 6.2.4 Платежи

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/payments/` | Список платежей |
| GET | `/api/payments/?credit={id}` | Платежи по кредиту |
| POST | `/api/payments/` | Создать платёж |

#### 6.2.5 Взаимодействия

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/interventions/` | Список взаимодействий |
| GET | `/api/interventions/?credit={id}` | Взаимодействия по кредиту |
| POST | `/api/interventions/` | Создать взаимодействие |

#### 6.2.6 Заявки на кредит

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/applications/` | Список заявок |
| POST | `/api/applications/` | Создать заявку |
| POST | `/api/applications/predict_approval/` | Прогноз одобрения |
| POST | `/api/applications/{id}/process/` | Обработать заявку |

**Пример запроса POST /api/applications/predict_approval/:**
```json
{
  "gender": "M",
  "marital_status": "married",
  "employment": "employed",
  "income": 100000,
  "monthly_expenses": 30000,
  "loan_amount": 500000,
  "loan_term": 36,
  "children_count": 1,
  "credit_history": 1,
  "region": "Москва"
}
```

**Пример ответа:**
```json
{
  "decision": "approved",
  "approved_probability": 0.78,
  "confidence": 0.85,
  "risk_factors": [],
  "model_version": "1.0"
}
```

#### 6.2.7 Скоринг

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/scorings/` | Результаты скоринга |
| GET | `/api/scorings/?credit={id}` | Скоринг кредита |

#### 6.2.8 Операторы

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/operators/` | Список операторов |
| GET | `/api/operators/{id}/` | Детали оператора |
| GET | `/api/operators/{id}/queue/` | Очередь оператора |

#### 6.2.9 Назначения

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/assignments/` | Список назначений |
| POST | `/api/assignments/distribute/` | Запустить распределение |

### 6.3 Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | OK |
| 201 | Created |
| 400 | Bad Request - неверный запрос |
| 401 | Unauthorized - требуется авторизация |
| 403 | Forbidden - доступ запрещён |
| 404 | Not Found - ресурс не найден |
| 500 | Internal Server Error |

---

## 7. Математическое обеспечение

### 7.1 Теоретические основы

#### 7.1.1 Задача классификации кредитных заявок

Задача одобрения кредита формулируется как **задача бинарной классификации**:

Дано:
- Множество объектов $X$ (кредитные заявки)
- Множество ответов $Y = \{0, 1\}$ (0 — отказ, 1 — одобрение)
- Обучающая выборка $(x_1, y_1), ..., (x_n, y_n)$

Требуется построить классификатор $f: X \rightarrow Y$, минимизирующий функцию потерь:

$$L(f) = \frac{1}{n} \sum_{i=1}^{n} \mathbb{I}[f(x_i) \neq y_i] \rightarrow \min$$

где $\mathbb{I}[\cdot]$ — индикаторная функция.

#### 7.1.2 Задача оптимального распределения

Задача распределения должников формулируется как **задача о назначениях** (assignment problem):

Дано:
- Множество должников $D = \{d_1, ..., d_m\}$
- Множество операторов $O = \{o_1, ..., o_k\}$
- Матрица полезности $U_{m \times k}$, где $u_{ij}$ — эффективность назначения должника $d_i$ оператору $o_j$

Требуется найти назначение $\pi: D \rightarrow O$, максимизирующее суммарную полезность:

$$\sum_{i=1}^{m} u_{i,\pi(i)} \rightarrow \max$$

При ограничениях:
- $|\pi^{-1}(o_j)| \leq L_j$ — ограничение нагрузки оператора

#### 7.1.3 Задача прогнозирования просрочки

Задача прогнозирования просрочки — **задача регрессии вероятности**:

$$P(overdue | X) = f(X, \theta)$$

где:
- $X$ — вектор признаков клиента и кредита
- $\theta$ — параметры модели
- $f$ — функция модели (логистическая регрессия, случайный лес и др.)

### 7.2 Расчёт ежемесячного платежа

Используется формула **аннуитетного платежа**:

$$PMT = P \cdot \frac{r(1+r)^n}{(1+r)^n - 1}$$

Где:
- $PMT$ — ежемесячный платёж
- $P$ — сумма кредита (principal)
- $r$ — месячная процентная ставка ($r = \frac{annual\_rate}{12 \cdot 100}$)
- $n$ — количество месяцев

**Реализация:**
```python
def calculate_monthly_payment(principal, annual_rate, term_months):
    """
    Расчёт аннуитетного платежа
    
    Args:
        principal: сумма кредита
        annual_rate: годовая ставка в процентах
        term_months: срок в месяцах
    
    Returns:
        float: ежемесячный платёж
    """
    monthly_rate = annual_rate / 12 / 100
    
    if monthly_rate == 0:
        return principal / term_months
    
    payment = principal * (
        monthly_rate * (1 + monthly_rate) ** term_months
    ) / (
        (1 + monthly_rate) ** term_months - 1
    )
    
    return round(payment, 2)
```

### 7.2 Расчёт долговой нагрузки (DTI)

**Debt-to-Income Ratio:**

$$DTI = \frac{Total\_Monthly\_Debt\_Payments}{Gross\_Monthly\_Income} \times 100\%$$

**Пороговые значения:**

| DTI | Оценка |
|-----|--------|
| < 20% | Отличная |
| 20-35% | Хорошая |
| 35-50% | Приемлемая |
| > 50% | Высокий риск |

### 7.3 Расчёт эффективной процентной ставки

$$EIR = \left(1 + \frac{r}{n}\right)^n - 1$$

Где:
- $EIR$ — эффективная годовая ставка
- $r$ — номинальная годовая ставка
- $n$ — количество периодов капитализации в году

### 7.4 Расчёт NPV (Net Present Value)

$$NPV = \sum_{t=1}^{n} \frac{CF_t}{(1+r)^t} - C_0$$

Где:
- $CF_t$ — денежный поток в период $t$
- $r$ — ставка дисконтирования
- $C_0$ — начальные инвестиции
- $n$ — количество периодов

### 7.5 Метрики эффективности взыскания

#### Collection Rate (CR)
$$CR = \frac{Collected\_Amount}{Total\_Overdue\_Amount} \times 100\%$$

#### Contact Rate
$$Contact\_Rate = \frac{Successful\_Contacts}{Total\_Calls} \times 100\%$$

#### Promise-to-Pay Rate (PTP Rate)
$$PTP\_Rate = \frac{Promises\_Made}{Successful\_Contacts} \times 100\%$$

#### Kept Promise Rate
$$Kept\_Promise\_Rate = \frac{Kept\_Promises}{Total\_Promises} \times 100\%$$

### 7.6 Roll Rate Analysis

Матрица переходов между bucket'ами:

$$P_{ij} = P(Bucket_{t+1} = j | Bucket_t = i)$$

```
        To Bucket:
         0      1      2      3      4      5
From  0  0.95   0.05   0.00   0.00   0.00   0.00
Bucket:
      1  0.30   0.45   0.25   0.00   0.00   0.00
      2  0.10   0.15   0.40   0.35   0.00   0.00
      3  0.05   0.05   0.10   0.40   0.40   0.00
      4  0.02   0.03   0.05   0.10   0.50   0.30
      5  0.01   0.01   0.02   0.03   0.13   0.80
```

---

## 8. ML-модели

### 8.1 Обзор архитектуры машинного обучения

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PIPELINE МАШИННОГО ОБУЧЕНИЯ                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │  Сырые      │    │  Feature     │    │   Модель     │              │
│  │  данные     │───>│  Engineering │───>│   (RF/GB)    │              │
│  │             │    │              │    │              │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│        │                   │                   │                        │
│        v                   v                   v                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │ Очистка,    │    │ Кодирование, │    │  Обучение,   │              │
│  │ валидация   │    │ нормализация │    │  валидация   │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                │                        │
│                                                v                        │
│                                         ┌──────────────┐               │
│                                         │  Предсказание │               │
│                                         │  + Объяснение │               │
│                                         └──────────────┘               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Модель прогнозирования одобрения кредита (Loan Approval Predictor)

**Файл:** `backend/collection_app/ml/loan_predictor.py`

#### 8.2.1 Выбор алгоритма

В системе используется **Random Forest Classifier** (Случайный лес) — ансамблевый метод машинного обучения.

**Почему Random Forest, а не нейронная сеть:**

| Критерий | Random Forest | Нейронная сеть |
|----------|---------------|----------------|
| Размер выборки | Работает на малых данных (100-10000) | Требует больших данных (10000+) |
| Интерпретируемость | Высокая (feature importance) | Низкая (black box) |
| Время обучения | Быстрое | Медленное |
| Переобучение | Устойчив | Склонен |
| Регуляторные требования | Объяснимость важна для банков | Сложно объяснить решение |

**Теоретическое обоснование Random Forest:**

Random Forest — это ансамбль из $B$ деревьев решений $\{T_1, ..., T_B\}$, где каждое дерево обучается на bootstrap-выборке.

Предсказание классификации:

$$\hat{y} = \text{mode}\{T_b(x)\}_{b=1}^{B}$$

Вероятность класса:

$$P(y=1|x) = \frac{1}{B} \sum_{b=1}^{B} \mathbb{I}[T_b(x) = 1]$$

#### 8.2.2 Гиперпараметры модели

```python
RandomForestClassifier(
    n_estimators=100,      # Количество деревьев в ансамбле
    criterion='entropy',    # Критерий расщепления (информационный выигрыш)
    max_depth=10,          # Максимальная глубина дерева
    min_samples_split=5,   # Мин. образцов для разбиения узла
    random_state=42,       # Seed для воспроизводимости
    n_jobs=-1              # Параллелизация на всех ядрах
)
```

**Обоснование выбора параметров:**

| Параметр | Значение | Обоснование |
|----------|----------|-------------|
| n_estimators=100 | Баланс качество/скорость, закон убывающей отдачи после 100 |
| criterion='entropy' | Information Gain лучше для категориальных признаков |
| max_depth=10 | Предотвращение переобучения на малых данных |
| min_samples_split=5 | Защита от шумовых разбиений |

#### 8.2.3 Входные данные (Features)

**Таблица признаков:**

| № | Признак | Тип | Описание | Предобработка |
|---|---------|-----|----------|---------------|
| 1 | gender | categorical | Пол (M/F) | LabelEncoder |
| 2 | marital_status | categorical | Семейное положение | LabelEncoder |
| 3 | employment | categorical | Тип занятости | LabelEncoder |
| 4 | region | categorical | Регион проживания | LabelEncoder |
| 5 | income | numeric | Ежемесячный доход (руб.) | Без преобразования |
| 6 | monthly_expenses | numeric | Ежемесячные расходы (руб.) | Без преобразования |
| 7 | loan_amount | numeric | Сумма кредита (руб.) | Без преобразования |
| 8 | loan_term | numeric | Срок кредита (мес.) | Без преобразования |
| 9 | children_count | numeric | Количество детей | Без преобразования |
| 10 | credit_history | binary | Кредитная история (1=хорошая) | Без преобразования |
| 11 | debt_to_income_ratio | derived | Рассчитанный DTI | Формула ниже |

**Формула расчёта производного признака DTI:**

$$DTI = \frac{\frac{LoanAmount}{LoanTerm} + MonthlyExpenses}{Income}$$

**Кодирование категориальных признаков (LabelEncoder):**

```python
# Пример кодирования employment
employment_map = {
    'employed': 0,
    'self_employed': 1,
    'retired': 2,
    'student': 3,
    'unemployed': 4
}
```

#### 8.2.4 Выходные данные (Output)

```python
{
    'approved_probability': float,  # P(одобрение) ∈ [0, 1]
    'decision': str,                # 'approved' если P ≥ 0.5, иначе 'rejected'
    'confidence': float,            # max(P, 1-P) — уверенность модели
    'risk_factors': List[str]       # Список выявленных рисков
}
```

**Правило принятия решения:**

$$decision = \begin{cases} approved & \text{если } P(y=1|x) \geq 0.5 \\ rejected & \text{если } P(y=1|x) < 0.5 \end{cases}$$

**Расчёт уверенности:**

$$confidence = |P(y=1|x) - 0.5| \times 2 = max(P, 1-P)$$

#### 8.2.5 Формирование обучающей выборки

**Источники данных:**

1. **Исторические данные банка** — заявки с известными решениями
2. **Синтетические данные** — генерируются при отсутствии реальных

**Правила формирования обучающей выборки:**

```python
def generate_training_sample():
    """
    Генерация обучающей выборки с реалистичным распределением
    """
    samples = []
    
    for _ in range(1000):  # Размер выборки
        sample = {
            # Признаки генерируются из реалистичных распределений
            'income': np.random.lognormal(mean=11.0, sigma=0.5),  # ~60-150k
            'loan_amount': np.random.lognormal(mean=12.5, sigma=0.7),
            'credit_history': np.random.choice([0, 1], p=[0.15, 0.85]),
            'employment': np.random.choice(
                ['employed', 'self_employed', 'unemployed', 'retired'],
                p=[0.65, 0.20, 0.10, 0.05]
            ),
            ...
        }
        
        # Целевая переменная определяется по бизнес-правилам
        label = determine_approval(sample)
        samples.append((sample, label))
    
    return samples
```

**Критерии одобрения (для разметки):**

$$y = 1 \text{ (одобрено), если:}$$
$$\begin{cases}
DTI < 0.5 \\
CreditHistory = 1 \\
Employment \in \{employed, self\_employed\} \\
Income > 30000
\end{cases}$$

**Разбиение выборки:**

```
┌─────────────────────────────────────────┐
│          Полная выборка (100%)          │
├─────────────────────┬───────────────────┤
│   Train (60%)       │    Test (40%)     │
│   Обучение модели   │    Валидация      │
└─────────────────────┴───────────────────┘
```

- **Train (60%)** — для обучения параметров модели
- **Test (40%)** — для оценки качества на независимых данных

**Стратификация:**

```python
X_train, X_test, y_train, y_test = train_test_split(
    X, y, 
    test_size=0.4,      # 40% на тест
    random_state=42,    # Воспроизводимость
    stratify=y          # Сохранение пропорций классов
)
```

#### 8.2.6 Метрики качества модели

| Метрика | Формула | Текущее значение |
|---------|---------|------------------|
| Accuracy | $\frac{TP+TN}{TP+TN+FP+FN}$ | ~67% |
| Precision | $\frac{TP}{TP+FP}$ | ~70% |
| Recall | $\frac{TP}{TP+FN}$ | ~65% |
| F1-Score | $2 \cdot \frac{Precision \cdot Recall}{Precision + Recall}$ | ~67% |

**Confusion Matrix:**

```
                 Predicted
              │  Reject │ Approve │
Actual ───────┼─────────┼─────────┤
  Reject      │   TN    │   FP    │
  Approve     │   FN    │   TP    │
```

#### 8.2.7 Feature Importance

Random Forest позволяет оценить важность признаков:

$$Importance(X_j) = \frac{1}{B} \sum_{b=1}^{B} \sum_{t \in T_b} p_t \cdot \Delta i(t, X_j)$$

где:
- $p_t$ — доля образцов, достигающих узла $t$
- $\Delta i(t, X_j)$ — уменьшение impurity при разбиении по $X_j$

**Типичная важность признаков:**

| Признак | Важность |
|---------|----------|
| credit_history | 0.28 |
| debt_to_income_ratio | 0.22 |
| income | 0.18 |
| employment | 0.12 |
| loan_amount | 0.10 |
| loan_term | 0.05 |
| прочие | 0.05 |

### 8.3 Модель скоринга просрочки (Overdue Scoring)

**Файл:** `backend/collection_app/ml/overdue_scoring.py`

#### 8.3.1 Теоретическая основа

Задача — оценить вероятность дефолта (PD — Probability of Default):

$$PD = P(DPD > 90 | X)$$

**Используемый подход:** Logistic Regression + Rule Engine

#### 8.3.2 Логистическая регрессия

Модель логистической регрессии:

$$P(y=1|X) = \sigma(w^T X + b) = \frac{1}{1 + e^{-(w^T X + b)}}$$

где $\sigma$ — сигмоидная функция.

**Функция потерь (Cross-Entropy):**

$$L = -\frac{1}{n} \sum_{i=1}^{n} [y_i \log(\hat{y}_i) + (1-y_i) \log(1-\hat{y}_i)]$$

#### 8.3.3 Входные признаки для скоринга

| Признак | Описание | Вес в модели |
|---------|----------|--------------|
| dpd_current | Текущие дни просрочки | +0.05 за каждый день |
| dpd_max_12m | Макс. DPD за 12 месяцев | +0.02 за каждый день |
| payment_ratio | Оплачено / План | -0.3 если < 0.8 |
| utilization | Использование лимита | +0.2 если > 0.9 |
| num_credits | Количество кредитов | +0.1 за каждый > 2 |
| income_verified | Подтверждён доход | -0.15 если да |

#### 8.3.4 Скоринговая карта

Преобразование вероятности в балл:

$$Score = 600 - 50 \cdot \log_2\left(\frac{PD}{1-PD}\right)$$

Инверсия (балл → вероятность):

$$PD = \frac{1}{1 + 2^{(Score - 600)/50}}$$

**Грейдирование:**

| Score | Грейд | PD |
|-------|-------|-----|
| 800+ | A | < 2% |
| 700-799 | B | 2-5% |
| 600-699 | C | 5-15% |
| 500-599 | D | 15-30% |
| < 500 | E | > 30% |

### 8.4 Модель психотипирования

**Файл:** `backend/collection_app/ml/psychotyping.py`

#### 8.4.1 Метод классификации

Используется **Rule-Based система** с элементами машинного обучения:

```
┌─────────────────────────────────────────┐
│         Исторические данные             │
│  (история контактов, платежей)          │
└────────────────┬────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────┐
│      Feature Extraction                  │
│  - payment_discipline_score              │
│  - promises_kept_ratio                   │
│  - contact_success_rate                  │
│  - avg_response_time                     │
└────────────────┬────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────┐
│       Rule Engine + Fuzzy Logic          │
│                                          │
│  IF promises_kept < 0.3 AND             │
│     contact_success < 0.4               │
│  THEN psychotype = 'unwilling'          │
└────────────────┬────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────┐
│            Психотип клиента              │
│  + confidence score                      │
└─────────────────────────────────────────┘
```

#### 8.4.2 Признаки для психотипирования

$$PaymentDiscipline = \frac{\sum_{i} \mathbb{I}[payment_i \text{ on time}]}{\sum_{i} payments_i}$$

$$PromisesKept = \frac{\text{Выполненные обещания}}{\text{Всего обещаний}}$$

$$ContactSuccess = \frac{\text{Успешные контакты}}{\text{Всего попыток связи}}$$

#### 8.4.3 Правила классификации

```python
def classify_psychotype(features):
    """
    Правила определения психотипа
    """
    pd = features['payment_discipline_score']
    pk = features['promises_kept_ratio']
    cs = features['contact_success_rate']
    income_stable = features['income_stability']
    
    # Забывчивый: платит, но с опозданием
    if pd > 0.5 and pk > 0.6 and cs > 0.7:
        return 'forgetful', 0.8
    
    # Кооперативный: хорошие показатели
    if pd > 0.7 and pk > 0.7:
        return 'cooperative', 0.85
    
    # Не может платить: финансовые проблемы
    if income_stable < 0.5 and pk > 0.4:
        return 'unable', 0.75
    
    # Не хочет платить: избегание
    if pk < 0.3 and cs < 0.4:
        return 'unwilling', 0.7
    
    # Токсичный: агрессия
    if features['complaint_count'] > 2:
        return 'toxic', 0.65
    
    return 'unknown', 0.5
```

### 8.5 Next Best Action (NBA)

**Файл:** `backend/collection_app/ml/next_best_action.py`

#### 8.5.1 Теоретическая основа

NBA использует **Multi-Armed Bandit** подход с Thompson Sampling:

Для каждого действия $a$ поддерживается Beta-распределение:

$$\theta_a \sim Beta(\alpha_a, \beta_a)$$

где:
- $\alpha_a$ — количество успехов действия $a$
- $\beta_a$ — количество неудач действия $a$

**Алгоритм Thompson Sampling:**

```
1. Для каждого действия a:
   - Сэмплировать θ_a ~ Beta(α_a, β_a)
2. Выбрать действие a* = argmax_a(θ_a)
3. Выполнить a*, наблюдать результат r
4. Обновить: если r=1, то α_a* += 1, иначе β_a* += 1
```

#### 8.5.2 Расчёт ожидаемой полезности

$$E[Utility(action)] = P(success|action, context) \times Value(success) - Cost(action)$$

**Компоненты:**

| Действие | P(success) | Value | Cost |
|----------|------------|-------|------|
| soft_reminder | 0.3 | amount × 0.8 | 50 руб. |
| phone_call | 0.5 | amount × 1.0 | 200 руб. |
| restructure_offer | 0.6 | amount × 0.6 | 500 руб. |
| legal_notice | 0.2 | amount × 0.3 | 2000 руб. |

### 8.6 Прогноз возврата (Return Forecast)

**Файл:** `backend/collection_app/ml/return_forecast.py`

#### 8.6.1 Survival Analysis

Используется модель Kaplan-Meier для оценки вероятности возврата во времени:

$$\hat{S}(t) = \prod_{t_i \leq t} \left(1 - \frac{d_i}{n_i}\right)$$

где:
- $d_i$ — количество событий (невозвратов) в момент $t_i$
- $n_i$ — количество под риском в момент $t_i$

#### 8.6.2 Модель Cox Proportional Hazards

$$h(t|X) = h_0(t) \cdot \exp(\beta^T X)$$

где:
- $h_0(t)$ — базовая функция риска
- $\beta$ — коэффициенты влияния признаков

**Интерпретация коэффициентов:**

| Признак | β | Hazard Ratio | Интерпретация |
|---------|---|--------------|---------------|
| dpd | +0.02 | 1.02 | Каждый день просрочки ↑ риск на 2% |
| income | -0.00001 | 0.99999 | Доход снижает риск |
| has_collateral | -0.5 | 0.61 | Залог снижает риск на 39% |

---

## 9. Алгоритмы распределения работы по операторам

### 9.1 Постановка задачи распределения

**Формальное определение:**

Дано:
- Множество клиентов $C = \{c_1, c_2, ..., c_n\}$
- Множество операторов $O = \{o_1, o_2, ..., o_m\}$
- Функция приоритета клиента $p: C \rightarrow \mathbb{R}^+$
- Функция квалификации оператора $q: O \rightarrow \mathbb{R}^+$
- Ограничение нагрузки $L_{max}$ — максимум клиентов на оператора

**Целевая функция:**

$$\max \sum_{i,j} x_{ij} \cdot match(c_i, o_j)$$

при ограничениях:
$$\sum_{j} x_{ij} = 1, \forall i \text{ (каждый клиент назначен одному оператору)}$$
$$\sum_{i} x_{ij} \leq L_{max}, \forall j \text{ (ограничение нагрузки)}$$

где $x_{ij} \in \{0, 1\}$ — бинарная переменная назначения.

### 9.2 Функция соответствия (Match Function)

$$match(c, o) = w_1 \cdot skill\_match(c, o) + w_2 \cdot workload\_balance(o) + w_3 \cdot priority\_alignment(c, o)$$

**Веса:**
- $w_1 = 0.4$ — соответствие навыков
- $w_2 = 0.3$ — баланс нагрузки
- $w_3 = 0.3$ — соответствие приоритетов

### 9.3 Расчёт квалификации оператора

**Файл:** `backend/collection_app/services/distribution.py`

```
┌─────────────────────────────────────────────────────────────────┐
│                 РАСЧЁТ EXPERIENCE SCORE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │   Tenure     │ + │    Role      │ + │ Success Rate │        │
│  │   (0-40)     │   │   (0-30)     │   │   (0-30)     │        │
│  └──────────────┘   └──────────────┘   └──────────────┘        │
│         │                  │                  │                 │
│         v                  v                  v                 │
│    months × 2         bonus по            rate × 30            │
│    (max 40)           должности                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Формула квалификации оператора:**

$$Q(o) = T_{score}(o) + R_{score}(o) + S_{score}(o)$$

**Компонент 1: Стаж работы (Tenure Score)**

$$T_{score} = \min(months\_employed \times 2, 40)$$

| Стаж (месяцы) | Баллы |
|---------------|-------|
| 0-5 | 0-10 |
| 6-12 | 12-24 |
| 13-20 | 26-40 |
| 20+ | 40 (max) |

**Компонент 2: Роль (Role Score)**

| Роль | Баллы | Обоснование |
|------|-------|-------------|
| junior_operator | 0 | Начальный уровень |
| middle_operator | 10 | Базовая компетенция |
| senior_operator | 20 | Высокая компетенция |
| team_lead | 25 | Лидер группы |
| supervisor | 30 | Руководитель |

**Компонент 3: Показатель успешности (Success Score)**

$$S_{score} = success\_rate \times 30$$

где $success\_rate = \frac{\text{Успешно закрытые кейсы}}{\text{Всего кейсов}}$

| Success Rate | Баллы |
|--------------|-------|
| 0.0-0.3 | 0-9 |
| 0.3-0.6 | 9-18 |
| 0.6-0.8 | 18-24 |
| 0.8-1.0 | 24-30 |

**Итоговая формула:**

$$Q(o) = \min(months \times 2, 40) + role\_bonus + success\_rate \times 30$$

**Диапазон значений:** [0, 100]

**Пример расчёта:**
```
Оператор: Иванов И.И.
- Стаж: 14 месяцев → min(14×2, 40) = 28 баллов
- Роль: senior_operator → 20 баллов
- Success rate: 0.75 → 0.75×30 = 22.5 баллов
- ИТОГО: 28 + 20 + 22.5 = 70.5 баллов
```

### 9.4 Расчёт приоритета клиента

```
┌─────────────────────────────────────────────────────────────────┐
│                 РАСЧЁТ PRIORITY SCORE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐ │
│  │   Amount     │ │   DPD        │ │ Risk Segment │ │ Failed │ │
│  │   (0-30)     │ │   (0-30)     │ │   (0-25)     │ │ (0-15) │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────┘ │
│         │                │                │              │      │
│         v                v                v              v      │
│    amount/10000    min(dpd/3, 30)   risk_map[seg]   atts×5     │
│    (max 30)                                         (max 15)   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Формула приоритета клиента:**

$$P(c) = A_{score}(c) + D_{score}(c) + R_{score}(c) + F_{score}(c)$$

**Компонент 1: Сумма просрочки (Amount Score)**

$$A_{score} = \min\left(\frac{overdue\_amount}{10000}, 30\right)$$

| Сумма (руб.) | Баллы |
|--------------|-------|
| 0-50,000 | 0-5 |
| 50,000-150,000 | 5-15 |
| 150,000-300,000 | 15-30 |
| 300,000+ | 30 (max) |

**Компонент 2: Дни просрочки (DPD Score)**

$$D_{score} = \min\left(\frac{days\_overdue}{3}, 30\right)$$

| DPD (дни) | Баллы |
|-----------|-------|
| 0-30 | 0-10 |
| 31-60 | 10-20 |
| 61-90 | 20-30 |
| 90+ | 30 (max) |

**Компонент 3: Риск-сегмент (Risk Score)**

$$R_{score} = risk\_map[segment]$$

| Сегмент | Код | Баллы |
|---------|-----|-------|
| Низкий риск | low | 5 |
| Средний риск | medium | 15 |
| Высокий риск | high | 25 |

**Компонент 4: Неудачные попытки (Failed Attempts Score)**

$$F_{score} = \min(failed\_contact\_attempts \times 5, 15)$$

| Попытки | Баллы |
|---------|-------|
| 0 | 0 |
| 1 | 5 |
| 2 | 10 |
| 3+ | 15 (max) |

**Итоговая формула:**

$$P(c) = \min\left(\frac{amount}{10000}, 30\right) + \min\left(\frac{dpd}{3}, 30\right) + risk\_map[seg] + \min(attempts \times 5, 15)$$

**Диапазон значений:** [0, 100]

**Пример расчёта:**
```
Клиент: Петров П.П.
- Сумма просрочки: 180,000 руб → min(180000/10000, 30) = 18 баллов
- DPD: 45 дней → min(45/3, 30) = 15 баллов
- Risk segment: high → 25 баллов
- Failed attempts: 2 → min(2×5, 15) = 10 баллов
- ИТОГО: 18 + 15 + 25 + 10 = 68 баллов
```

### 9.5 Алгоритм сопоставления (Matching Algorithm)

**Псевдокод:**

```
ALGORITHM DistributeClients(clients, operators)
INPUT:
    clients: List[Client]     # Список клиентов для распределения
    operators: List[Operator] # Список доступных операторов
OUTPUT:
    assignments: Dict[Client, Operator]  # Назначения

BEGIN
    # Шаг 1: Рассчитать скоры
    FOR each client c IN clients:
        c.priority_score = CalculatePriority(c)
    
    FOR each operator o IN operators:
        o.experience_score = CalculateExperience(o)
    
    # Шаг 2: Сортировка по приоритету (высокий → низкий)
    sorted_clients = SORT(clients, BY priority_score, DESC)
    
    # Шаг 3: Распределение
    assignments = {}
    
    FOR each client c IN sorted_clients:
        # Найти подходящих операторов
        available_operators = FILTER(operators, WHERE current_load < max_load)
        
        IF c.priority_score >= 70:
            # Высокий приоритет → опытные операторы
            candidates = FILTER(available_operators, WHERE experience_score >= 60)
        ELIF c.priority_score >= 40:
            # Средний приоритет → средние операторы
            candidates = FILTER(available_operators, WHERE experience_score >= 30)
        ELSE:
            # Низкий приоритет → для обучения джуниоров
            candidates = available_operators
        
        IF candidates IS EMPTY:
            candidates = available_operators
        
        # Выбор по минимальной нагрузке
        best_operator = MIN(candidates, BY current_load)
        
        # Назначение
        assignments[c] = best_operator
        best_operator.current_load += 1
    
    RETURN assignments
END
```

### 9.6 Диаграмма процесса распределения

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        ПРОЦЕСС РАСПРЕДЕЛЕНИЯ                              │
└──────────────────────────────────────────────────────────────────────────┘

     ┌─────────────┐
     │   START     │
     └──────┬──────┘
            │
            v
┌───────────────────────┐
│  Получить список      │
│  нераспределённых     │
│  клиентов             │
└───────────┬───────────┘
            │
            v
┌───────────────────────┐
│  Рассчитать Priority  │
│  Score для каждого    │
│  клиента              │
└───────────┬───────────┘
            │
            v
┌───────────────────────┐
│  Получить список      │
│  активных операторов  │
└───────────┬───────────┘
            │
            v
┌───────────────────────┐
│  Рассчитать Experience│
│  Score для каждого    │
│  оператора            │
└───────────┬───────────┘
            │
            v
┌───────────────────────┐         ┌─────────────────────────────┐
│  Сортировать клиентов │         │  Правила сопоставления:     │
│  по Priority (DESC)   │────────>│  High (≥70) → Senior (≥60)  │
└───────────┬───────────┘         │  Medium (40-70) → Middle    │
            │                      │  Low (<40) → Junior (train) │
            v                      └─────────────────────────────┘
┌───────────────────────┐
│  FOR each client:     │
│  - Найти подходящих   │
│    операторов         │
│  - Выбрать с мин.     │
│    нагрузкой          │
│  - Назначить          │
└───────────┬───────────┘
            │
            v
┌───────────────────────┐
│  Создать Assignment   │
│  записи в БД          │
└───────────┬───────────┘
            │
            v
     ┌─────────────┐
     │    END      │
     └─────────────┘
```

### 9.7 Оптимизация и ограничения

**Временная сложность:**

$$O(n \log n + n \cdot m)$$

где $n$ — количество клиентов, $m$ — количество операторов

**Пространственная сложность:**

$$O(n + m)$$

**Ограничения системы:**

| Параметр | Значение | Описание |
|----------|----------|----------|
| MAX_LOAD_PER_OPERATOR | 50 | Максимум клиентов на оператора |
| MIN_EXPERIENCE_HIGH_PRIORITY | 60 | Мин. квалификация для сложных кейсов |
| PRIORITY_THRESHOLD_HIGH | 70 | Порог высокого приоритета |
| PRIORITY_THRESHOLD_MEDIUM | 40 | Порог среднего приоритета |

### 9.8 Балансировка нагрузки

**Формула балансировки:**

$$Balance = 1 - \frac{\sigma(loads)}{\mu(loads)}$$

где:
- $\sigma(loads)$ — стандартное отклонение нагрузки
- $\mu(loads)$ — средняя нагрузка

**Целевое значение:** $Balance \geq 0.8$

**Перебалансировка (если Balance < 0.7):**

```python
def rebalance():
    """
    Перераспределение для выравнивания нагрузки
    """
    avg_load = sum(o.load for o in operators) / len(operators)
    
    overloaded = [o for o in operators if o.load > avg_load * 1.2]
    underloaded = [o for o in operators if o.load < avg_load * 0.8]
    
    for over in overloaded:
        excess = over.load - avg_load
        clients_to_move = over.clients[-int(excess):]
        
        for client in clients_to_move:
            target = min(underloaded, key=lambda o: o.load)
            reassign(client, over, target)
```

---

## 10. Дополнительные алгоритмы

### 10.1 Алгоритм Smart Scripts

**Файл:** `backend/collection_app/ml/smart_scripts.py`

**Цель:** Генерация персонализированных скриптов разговора

**Структура скрипта:**
```python
Script = {
    'opening': List[str],      # Фразы приветствия
    'key_points': List[str],   # Ключевые тезисы
    'objection_handlers': {    # Обработка возражений
        'objection': List[str]
    },
    'closing': List[str],      # Завершение
    'tips': List[str]          # Подсказки оператору
}
```

**Выбор скрипта:**
```python
def select_script(psychotype, dpd, history):
    base_script = SCRIPTS[psychotype]
    
    # Адаптация под DPD
    if dpd > 60:
        base_script = add_urgency(base_script)
    
    # Адаптация под историю
    if has_broken_promises(history):
        base_script = add_commitment_phrases(base_script)
    
    return base_script
```

### 10.2 Калькулятор реструктуризации

**Цель:** Расчёт параметров реструктуризации

**Варианты реструктуризации:**

| Вариант | Описание |
|---------|----------|
| Пролонгация | Увеличение срока |
| Снижение ставки | Уменьшение процента |
| Кредитные каникулы | Отсрочка платежей |
| Частичное списание | Прощение части долга |

**Формула нового платежа при пролонгации:**

$$PMT_{new} = P_{remaining} \cdot \frac{r(1+r)^{n_{new}}}{(1+r)^{n_{new}} - 1}$$

---

## 11. Развёртывание

### 11.1 Требования к окружению

**Минимальные требования:**
- CPU: 2 ядра
- RAM: 4 GB
- Disk: 10 GB
- OS: Windows 10+ / Linux / macOS

**Рекомендуемые требования:**
- CPU: 4 ядра
- RAM: 8 GB
- Disk: 50 GB SSD
- OS: Ubuntu 22.04 LTS

### 11.2 Установка (Development)

```bash
# 1. Клонирование репозитория
git clone https://github.com/your-username/collection_app.git
cd collection_app

# 2. Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 3. Миграции БД
python manage.py migrate

# 4. Загрузка тестовых данных
python manage.py populate_db

# 5. Обучение ML модели
python manage.py train_loan_model

# 6. Запуск сервера
python manage.py runserver

# 7. Frontend (в отдельном терминале)
cd ../frontend
npm install
npm run dev
```

### 10.3 Установка (Production)

**Docker Compose:**

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: collection_db
      POSTGRES_USER: collection_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    command: gunicorn collection.wsgi:application --bind 0.0.0.0:8000
    environment:
      - DATABASE_URL=postgres://collection_user:secure_password@db:5432/collection_db
      - DEBUG=False
      - SECRET_KEY=your-secret-key
    depends_on:
      - db
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

**Запуск:**
```bash
docker-compose up -d
```

### 10.4 Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| DEBUG | Режим отладки | True |
| SECRET_KEY | Секретный ключ Django | - |
| DATABASE_URL | URL базы данных | sqlite:///db.sqlite3 |
| ALLOWED_HOSTS | Разрешённые хосты | localhost |
| CORS_ALLOWED_ORIGINS | CORS origins | http://localhost:5173 |

### 10.5 Nginx конфигурация

```nginx
server {
    listen 80;
    server_name collection.example.com;

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 11. Тестирование

### 11.1 Структура тестов

```
backend/
├── collection_app/
│   └── tests.py           # Unit тесты
├── test_api_prediction.py # API тесты
└── test_loan_predictor.py # ML тесты
```

### 11.2 Запуск тестов

```bash
# Все тесты
python manage.py test

# Конкретный файл
python manage.py test collection_app.tests

# С покрытием
pip install coverage
coverage run manage.py test
coverage report
```

### 11.3 Примеры тестов

```python
# tests.py
from django.test import TestCase
from collection_app.models import Client, Credit

class CreditModelTest(TestCase):
    def setUp(self):
        self.client = Client.objects.create(
            first_name='Тест',
            last_name='Тестов',
            phone='+7 (999) 999-99-99'
        )
    
    def test_credit_creation(self):
        credit = Credit.objects.create(
            client=self.client,
            principal_amount=100000,
            interest_rate=15.0,
            term_months=12
        )
        self.assertEqual(credit.status, 'active')
    
    def test_monthly_payment_calculation(self):
        # Тест расчёта платежа
        pass
```

### 11.4 API тесты

```python
# test_api_prediction.py
import requests

def test_predict_approval():
    response = requests.post(
        'http://localhost:8000/api/applications/predict_approval/',
        json={
            'gender': 'M',
            'income': 100000,
            'loan_amount': 500000,
            'loan_term': 36,
            'employment': 'employed',
            'credit_history': 1
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert 'decision' in data
    assert 'approved_probability' in data
```

---

## 12. Безопасность

### 12.1 Аутентификация

Система поддерживает Token-based аутентификацию:

```python
# Получение токена
POST /api/auth/login/
{
    "username": "operator1",
    "password": "password123"
}

# Ответ
{
    "token": "abc123...",
    "user": {
        "id": 1,
        "username": "operator1",
        "role": "operator"
    }
}

# Использование токена
GET /api/clients/
Authorization: Token abc123...
```

### 12.2 Разграничение доступа

| Роль | Права |
|------|-------|
| operator | Просмотр назначенных клиентов, создание взаимодействий |
| senior | + Просмотр всех клиентов |
| manager | + Отчёты, аналитика |
| admin | Полный доступ |

### 12.3 Защита данных

- Персональные данные хранятся в зашифрованном виде
- Пароли хешируются (PBKDF2)
- HTTPS обязателен в production
- Логирование всех действий

### 12.4 CORS настройки

```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://collection.example.com",
]

CORS_ALLOW_CREDENTIALS = True
```

---

## Приложения

### А. Глоссарий

| Термин | Определение |
|--------|-------------|
| DPD | Days Past Due — дни просрочки |
| PTP | Promise to Pay — обещание оплатить |
| NBA | Next Best Action — следующее лучшее действие |
| DTI | Debt-to-Income — отношение долга к доходу |
| NPV | Net Present Value — чистая приведённая стоимость |
| Bucket | Группировка по глубине просрочки |
| Roll Rate | Показатель миграции между bucket'ами |

### Б. Коды статусов кредита

| Код | Название | Описание |
|-----|----------|----------|
| active | Активный | Кредит обслуживается |
| overdue | Просрочка | Есть просроченная задолженность |
| default | Дефолт | Глубокая просрочка (90+ дней) |
| closed | Закрыт | Кредит погашен |
| restructured | Реструктуризирован | Изменены условия |
| sold | Продан | Передан коллекторам |
| written_off | Списан | Списан с баланса |

### В. Справочник API ошибок

| Код | Сообщение | Решение |
|-----|-----------|---------|
| AUTH_001 | Invalid credentials | Проверьте логин/пароль |
| AUTH_002 | Token expired | Получите новый токен |
| VAL_001 | Invalid field format | Проверьте формат данных |
| VAL_002 | Required field missing | Добавьте обязательное поле |
| ML_001 | Model not loaded | Перезапустите сервер |
| ML_002 | Prediction failed | Проверьте входные данные |

---

## История изменений

| Версия | Дата | Описание |
|--------|------|----------|
| 1.0.0 | 2026-02-05 | Начальная версия документации |

---

*Документация создана для внутреннего использования. При возникновении вопросов обращайтесь к команде разработки.*
