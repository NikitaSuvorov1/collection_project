# Техническая документация
## Система управления взысканием задолженности (Collection Management System)

**Версия:** 3.1.0  
**Дата:** Март 2026  
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
9. [Алгоритмы распределения](#9-алгоритмы-распределения-работы-по-операторам)
10. [Дополнительные алгоритмы](#10-дополнительные-алгоритмы)
11. [Развёртывание](#11-развёртывание)
12. [Безопасность](#12-безопасность)
13. [**Collection Workflow (BPMN)**](#13-collection-workflow-bpmn)
14. [**Комплаенс 230-ФЗ**](#14-комплаенс-230-фз)
15. [**Roadmap развития**](#15-roadmap-развития)

---

## 1. Общее описание системы

### 1.1 Назначение

Система управления взысканием задолженности предназначена для автоматизации **полного цикла collection**:

- **Pre-Collection** — раннее предупреждение и профилактика просрочки
- **Soft Collection** — мягкое взыскание (звонки, SMS, email)
- **Hard Collection** — жёсткое взыскание (выезды, претензии)
- **Legal Collection** — судебное взыскание и исполнительное производство
- **Реструктуризация** — пересмотр условий кредитования

### 1.2 Целевые пользователи

| Роль | Код | Описание | Основные функции |
|------|-----|----------|------------------|
| Администратор | admin | Системный администратор | Настройка, управление пользователями |
| Менеджер | manager | Руководитель отдела | Аналитика, отчёты, управление командой |
| Старший оператор | senior_operator | Опытный специалист | Сложные случаи, hard collection, наставничество |
| Оператор | operator | Специалист по взысканию | Soft collection, звонки, фиксация результатов |
| Юрист | legal_specialist | Юридический специалист | Legal collection, документы, суды |
| Аналитик | analyst | Аналитик данных | Отчёты, мониторинг ML моделей |
| Аудитор | auditor | Внутренний аудитор | Проверка соответствия, аудит действий |

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
| drf-spectacular | 0.27+ | OpenAPI / Swagger / ReDoc |
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
│       ├── models.py            # Модели данных (30+ моделей)
│       ├── views.py             # API endpoints (16 ViewSets + 15 APIViews)
│       ├── serializers.py       # Сериализаторы (20+)
│       ├── urls.py              # URL маршруты (30+ endpoints)
│       ├── tests.py             # Unit / Integration тесты (37 тестов)
│       ├── admin.py             # Админ-панель
│       │
│       ├── ml/                  # ML модуль
│       │   ├── loan_predictor.py      # Прогноз одобрения
│       │   ├── overdue_predictor.py   # Прогноз просрочки
│       │   ├── overdue_scoring.py     # Скоринг просрочки
│       │   ├── psychotyping.py        # Психотипирование
│       │   ├── next_best_action.py    # NBA рекомендации
│       │   ├── return_forecast.py     # Прогноз возврата
│       │   ├── smart_scripts.py       # Умные скрипты
│       │   ├── compliance.py          # Compliance-проверки
│       │   ├── pipeline.py            # ML pipeline
│       │   ├── application_approval.py # Одобрение заявок
│       │   └── saved_models/          # Сохранённые модели
│       │
│       ├── services/            # Бизнес-логика
│       │   ├── __init__.py
│       │   ├── distribution.py        # Интеллектуальное распределение (с ML)
│       │   ├── collection_service.py  # Сервис взыскания (полный цикл)
│       │   ├── workflow_service.py    # Workflow Engine (Rules Engine)
│       │   └── compliance_230fz.py    # 230-ФЗ — полный комплаенс (11 статей)
│       │
│       ├── middleware/          # Middleware
│       │   ├── __init__.py
│       │   └── security.py     # Rate limiting, Security headers
│       │
│       ├── management/          # Django команды
│       │   └── commands/
│       │       ├── populate_db.py               # Заполнение БД тестовыми данными
│       │       ├── populate_dashboard_data.py   # Данные для дашборда
│       │       ├── populate_missing_data.py     # Заполнение пробелов
│       │       ├── fill_credit_states.py        # Помесячные состояния кредитов
│       │       ├── distribute_clients.py        # Распределение клиентов
│       │       ├── run_scoring.py               # Запуск скоринга
│       │       ├── score_all_credits.py         # Пакетный скоринг всех кредитов
│       │       ├── full_scoring_pipeline.py     # Полный pipeline скоринга
│       │       ├── train_loan_model.py          # Обучение модели одобрения
│       │       ├── train_approval_model.py      # Обучение модели заявок (GB)
│       │       ├── train_overdue_model.py       # Обучение модели просрочки (RF)
│       │       ├── generate_training_data.py    # Генерация обучающей выборки
│       │       └── generate_killer_features_data.py # Killer-features данные
│       │
│       ├── migrations/          # Миграции БД (8 миграций)
│       └── fixtures/            # Тестовые данные
│           └── initial_data.json
│
├── frontend/                    # Клиентская часть
│   ├── package.json            # NPM зависимости
│   ├── index.html              # HTML точка входа
│   │
│   └── src/
│       ├── main.jsx            # React точка входа
│       ├── App.jsx             # Корневой компонент + рабочий стол оператора
│       ├── styles.css          # Глобальные стили
│       │
│       ├── LoginPage.jsx       # Страница входа
│       ├── DashboardPage.jsx   # Дашборд руководителя
│       ├── CreditsPage.jsx     # Реестр кредитов
│       ├── CreditDetailPage.jsx # Детали кредита
│       ├── Client360Page.jsx   # Профиль клиента 360°
│       ├── CollectionDeskApp.jsx # Рабочий стол оператора (устар.)
│       ├── LoanPredictionPage.jsx    # Прогноз одобрения кредита
│       ├── LoanTrainingPage.jsx      # Обучение модели одобрения (31 признак)
│       ├── ModelTrainingPage.jsx     # Обучение модели просрочки (26 признаков)
│       ├── OperatorStatsPage.jsx     # Статистика оператора (KPI)
│       ├── OverduePredictionPage.jsx # Прогноз просрочки
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
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│       Client        │     │       Credit        │     │      Payment        │
├─────────────────────┤     ├─────────────────────┤     ├─────────────────────┤
│ PK id               │<──┐ │ PK id               │<──┐ │ PK id               │
│    full_name        │   │ │ FK client_id        │───┘ │ FK credit_id        │───┐
│    birth_date       │   └─│    principal_amount  │     │    amount           │   │
│    gender           │     │    interest_rate     │     │    payment_date     │   │
│    marital_status   │     │    monthly_payment   │     │    payment_type     │   │
│    employment       │     │    product_type      │     │    planned_date     │   │
│    employer_name    │     │    status            │     │    min_payment      │   │
│    position         │     │    open_date         │     │    overdue_days     │   │
│    income           │     │    planned_close_date│     └─────────────────────┘   │
│    children_count   │     │    actuality_date    │                               │
│    city             │     └─────────────────────┘     ┌─────────────────────┐   │
│    region           │              │                  │    CreditState      │   │
│    phone_mobile     │              │                  ├─────────────────────┤   │
│    phone_work       │              │                  │ PK id               │   │
│    phone_home       │              │                  │ FK credit_id        │───┤
│    monthly_expenses │              │                  │ FK client_id        │   │
│    category         │              │                  │    state_date       │   │
└─────────────────────┘              │                  │    principal_debt   │   │
                                     │                  │    overdue_principal│   │
┌─────────────────────┐              │                  │    overdue_interest │   │
│     Operator        │              │                  │    penalties        │   │
├─────────────────────┤              │                  │    overdue_days     │   │
│ PK id               │<───┐        │                  └─────────────────────┘   │
│    full_name        │    │        │                                             │
│    role             │    │        │                  ┌─────────────────────┐    │
│    specialization   │    │        │                  │    Assignment       │    │
│    status           │    │        │                  ├─────────────────────┤    │
│    current_load     │    │        │                  │ PK id               │    │
│    max_load         │    │        │                  │ FK operator_id      │────┤
│    success_rate     │    │        │                  │ FK client_id        │    │
│    total_collected  │    │        v                  │ FK credit_id        │    │
└─────────────────────┘    │ ┌─────────────────────┐  │    overdue_amount   │    │
                           │ │   Intervention      │  │    overdue_days     │    │
                           │ ├─────────────────────┤  │    priority         │    │
                           │ │ PK id               │  │    assignment_date  │    │
                           └─│ FK operator_id      │  └─────────────────────┘    │
                             │ FK client_id        │                              │
                             │ FK credit_id        │──────────────────────────────┘
                             │    datetime         │
                             │    intervention_type│
                             │    status           │
                             │    duration         │
                             │    promise_amount   │
                             │    notes            │
                             └─────────────────────┘
```

### 5.2 Описание сущностей

#### 5.2.1 Client (Клиент)

```python
class Client(models.Model):
    """Клиент (5000 записей)"""
    
    # Персональные данные
    full_name = models.CharField(max_length=300)       # ФИО
    birth_date = models.DateField()                    # Дата рождения
    gender = models.CharField(max_length=1)            # Пол (M/F)
    marital_status = models.CharField(max_length=20)   # Семейное положение
    
    # Занятость и доход
    employment = models.CharField(max_length=20)       # Тип занятости
    employer_name = models.CharField(max_length=300)   # Место работы
    position = models.CharField(max_length=200)        # Должность
    income = models.DecimalField()                     # Доход
    monthly_expenses = models.DecimalField()           # Ежемесячные расходы
    children_count = models.IntegerField()             # Количество детей
    
    # Контакты
    phone_mobile = models.CharField(max_length=32)     # Телефон (мобильный)
    phone_work = models.CharField(max_length=32)       # Телефон (рабочий)
    phone_home = models.CharField(max_length=32)       # Телефон (домашний)
    
    # Адрес
    city = models.CharField(max_length=200)            # Город
    region = models.CharField(max_length=200)          # Регион
    
    # Категория
    category = models.CharField(max_length=20)         # Категория клиента
```

**Допустимые значения:**

| Поле | Значения |
|------|----------|
| gender | `M` - мужской, `F` - женский |
| marital_status | `single`, `married`, `divorced`, `widowed` |
| employment | `employed`, `self_employed`, `unemployed`, `retired`, `student` |
| category | `standard`, `vip`, `problem`, `new` |

#### 5.2.2 Credit (Кредит)

```python
class Credit(models.Model):
    """Кредит (700 записей)"""
    
    client = models.ForeignKey(Client)                 # Клиент
    principal_amount = models.DecimalField()           # Взятая сумма
    interest_rate = models.DecimalField()              # Процентная ставка
    monthly_payment = models.DecimalField()            # Ежемесячный платёж
    
    product_type = models.CharField()                  # Тип продукта
    status = models.CharField()                        # Статус
    
    open_date = models.DateField()                     # Дата открытия
    planned_close_date = models.DateField(null=True)   # Плановая дата закрытия
    actuality_date = models.DateField(null=True)       # Дата актуальности

    # Вычисляемые свойства (property)
    @property delinquency_bucket  # 'current' | '0-30' | '30-60' | '60-90' | '90+'
    @property days_past_due       # int — дни просрочки из последнего CreditState
```

> **Примечание:** Поле `term_months` не хранится в модели — оно вычисляется в `CreditSerializer` как `round((planned_close_date - open_date).days / 30.44)`.

**Вычисляемые свойства Credit (Delinquency Buckets):**

| Свойство | Тип | Описание |
|----------|-----|----------|
| `delinquency_bucket` | str | Стадия просрочки по DPD из последнего CreditState |
| `days_past_due` | int | Количество дней просрочки из последнего CreditState |

**Бакеты просрочки:**

| Bucket | DPD (Days Past Due) | Описание |
|--------|---------------------|----------|
| `current` | 0 | Без просрочки |
| `0-30` | 1-30 | Ранняя просрочка |
| `30-60` | 31-60 | Средняя просрочка |
| `60-90` | 61-90 | Поздняя просрочка |
| `90+` | 91+ | Дефолт |

Оба поля отдаются через REST API в `CreditSerializer` как `read_only` и доступны в ответе `GET /api/credits/`.

**Допустимые значения:**

| Поле | Значения |
|------|----------|
| product_type | `consumer` - потребительский, `mortgage` - ипотека, `car` - автокредит, `credit_card` - кредитная карта, `microloan` - микрозайм |
| status | `active` - активный, `overdue` - просрочка, `default` - дефолт, `closed` - закрыт, `restructured` - реструктуризирован, `legal` - в суде, `sold` - продан, `written_off` - списан |

#### 5.2.3 CreditState (Состояние кредита)

```python
class CreditState(models.Model):
    """Состояние кредита (~21000 записей, помесячная прогрессия)"""
    
    credit = models.ForeignKey(Credit)                        # Кредит
    client = models.ForeignKey(Client, null=True)             # Клиент
    state_date = models.DateField()                           # Дата состояния
    planned_payment_date = models.DateField(null=True)        # Плановая дата платежа
    principal_debt = models.DecimalField()                    # Основной долг
    overdue_principal = models.DecimalField()                 # Просроченный основной долг
    interest = models.DecimalField()                          # Проценты
    overdue_interest = models.DecimalField()                  # Просроченные проценты
    penalties = models.DecimalField()                         # Штрафы
    overdue_start_date = models.DateField(null=True)          # Дата начала просрочки
    overdue_days = models.IntegerField()                      # Длительность просрочки (дней)
    overdue_close_date = models.DateField(null=True)          # Дата закрытия просрочки
```

**Bucket классификация (по overdue_days):**

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
    """Платёж (~19000 записей)"""
    
    credit = models.ForeignKey(Credit)                 # Кредит
    payment_date = models.DateField()                  # Дата платежа
    amount = models.DecimalField()                     # Сумма платежа
    payment_type = models.CharField()                  # Тип платежа
    planned_date = models.DateField(null=True)         # Плановая дата
    min_payment = models.DecimalField()                # Минимальный платёж
    overdue_days = models.IntegerField()               # Просрочка по платежу (дней)
    actuality_date = models.DateField(null=True)       # Дата актуальности
```

**Типы платежей:**

| Код | Описание |
|-----|---------|
| `regular` | Регулярный |
| `early` | Досрочный |
| `partial` | Частичный |
| `penalty` | Штраф |

#### 5.2.5 Intervention (Воздействие)

```python
class Intervention(models.Model):
    """Воздействие по кредиту (10000 записей)"""
    
    client = models.ForeignKey(Client)                 # Клиент
    credit = models.ForeignKey(Credit)                 # Кредит
    operator = models.ForeignKey(Operator, null=True)  # Оператор
    datetime = models.DateTimeField()                  # Дата и время
    intervention_type = models.CharField()             # Тип воздействия
    status = models.CharField()                        # Статус воздействия
    duration = models.IntegerField()                   # Длительность (сек)
    promise_amount = models.DecimalField()             # Сумма обещания
    promise_date = models.DateField(null=True)         # Дата обещания
    notes = models.TextField()                         # Комментарий
    refusal_reason = models.CharField()                # Причина отказа
```

**Типы воздействий (intervention_type):**

| Код | Описание |
|-----|---------|
| `phone` | Звонок |
| `sms` | СМС |
| `email` | Email |
| `letter` | Письмо |
| `visit` | Визит |

**Статусы воздействий (status):**

| Код | Описание |
|-----|---------|
| `completed` | Завершено |
| `no_answer` | Не дозвон |
| `promise` | Обещание |
| `refuse` | Отказ |
| `callback` | Перезвонить |

#### 5.2.6 Assignment (Назначение)

```python
class Assignment(models.Model):
    """Распределение работы на текущий день (3000 записей)"""
    
    operator = models.ForeignKey(Operator)             # Оператор
    client = models.ForeignKey(Client, null=True)      # Клиент
    credit = models.ForeignKey(Credit)                 # Кредит
    debtor_name = models.CharField(max_length=300)     # ФИО должника
    overdue_amount = models.DecimalField()             # Сумма просрочки
    overdue_days = models.IntegerField()               # Срок просрочки (дней)
    priority = models.IntegerField()                   # Приоритет воздействия
    assignment_date = models.DateField()               # Дата назначения
```

#### 5.2.7 ViolationLog (Журнал нарушений 230-ФЗ)

```python
class ViolationLog(models.Model):
    """Журнал нарушений 230-ФЗ — отдельная таблица для аудита комплаенса"""

    client = models.ForeignKey(Client)                 # Клиент
    operator = models.ForeignKey(Operator, null=True)  # Оператор
    rule_type = models.CharField(max_length=30)        # Тип нарушения (st1..st11, other)
    severity = models.CharField(max_length=10)         # Серьёзность (low/medium/high/critical)
    description = models.TextField()                   # Описание нарушения
    action_blocked = models.BooleanField(default=True) # Действие заблокировано
    contact_type = models.CharField(max_length=20)     # Канал контакта
    details = models.JSONField(default=dict)           # Подробности (JSON)
    created_at = models.DateTimeField(auto_now_add=True) # Дата нарушения
```

**Типы нарушений (rule_type):**

| Код | Статья 230-ФЗ | Описание |
|-----|---------------|----------|
| `st1_time` | Ст. 1 | Нарушение времени контакта |
| `st2_frequency` | Ст. 2 | Превышение частоты контактов |
| `st3_refusal` | Ст. 3 | Контакт при отказе клиента |
| `st4_third_party` | Ст. 4 | Контакт с третьими лицами без согласия |
| `st5_script` | Ст. 5 | Неутверждённый скрипт |
| `st6_identification` | Ст. 6 | Нарушение идентификации оператора |
| `st7_bankruptcy` | Ст. 7 | Контакт с банкротом |
| `st8_hidden_number` | Ст. 8 | Скрытый номер звонящего |
| `st9_interval` | Ст. 9 | Нарушение минимального интервала |
| `st10_history` | Ст. 10 | Нарушение хранения истории |
| `st11_personal_data` | Ст. 11 | Нарушение 152-ФЗ (ПДн) |
| `other` | — | Иное нарушение |

**Уровни серьёзности (severity):**

| Код | Описание |
|-----|----------|
| `low` | Низкая |
| `medium` | Средняя |
| `high` | Высокая |
| `critical` | Критическая |

**Индексы:**
- `idx_violation_client_dt` — (client, -created_at)
- `idx_violation_op_dt` — (operator, -created_at)
- `idx_violation_rule` — (rule_type)
- `idx_violation_severity` — (severity)

#### 5.2.8 Operator (Оператор)

```python
class Operator(models.Model):
    """Оператор (50 записей, ID 51-100)"""
    
    user = models.OneToOneField(User, null=True)       # Связь с User
    full_name = models.CharField(max_length=200)       # ФИО
    role = models.CharField()                          # Роль
    specialization = models.CharField()                # Специализация
    hire_date = models.DateField(null=True)            # Дата трудоустройства
    current_load = models.IntegerField()               # Текущая нагрузка
    max_load = models.IntegerField()                   # Максимальная нагрузка
    success_rate = models.FloatField()                 # Показатель успешности
    avg_call_duration = models.IntegerField()          # Средняя длительность звонка (сек)
    total_collected = models.DecimalField()            # Всего собрано
    status = models.CharField()                        # Статус оператора
```

**Роли операторов:**

| Код | Описание |
|-----|---------|
| `junior_operator` | Джуниор оператор |
| `operator` | Оператор |
| `senior_operator` | Старший оператор |
| `team_lead` | Тимлид |
| `supervisor` | Супервайзер |
| `legal_specialist` | Юрист |
| `manager` | Менеджер |

#### 5.2.9 Полная карта моделей (30+ сущностей)

Помимо основных сущностей (Client, Credit, CreditState, Payment, Intervention, Assignment, Operator), система включает следующие модели, сгруппированные по доменам:

**RBAC и аудит:**

| Модель | Описание | Записей |
|--------|----------|---------|
| Role | Системные роли с 15 разрешениями (can_view_clients, can_make_calls...) | ~7 |
| AuditLog | Журнал всех действий (CRUD, звонки, SMS, эскалации, экспорт), ФЗ-152 | динамич. |

**Collection Case (кейс взыскания):**

| Модель | Описание | Записей |
|--------|----------|---------|
| CollectionCase | Центральная сущность взыскания — клиент + кредиты + стадия + приоритет + ML-прогнозы | динамич. |
| CollectionStageHistory | История переходов между стадиями (pre_collection → soft → hard → legal) | динамич. |

**Pre-Collection:**

| Модель | Описание | Записей |
|--------|----------|---------|
| PreCollectionAlert | Алерты раннего предупреждения (скоро платёж, пропущен, высокий риск) | динамич. |

**Soft Collection:**

| Модель | Описание | Записей |
|--------|----------|---------|
| CommunicationTask | Задачи на коммуникацию (первичный звонок, повторный, SMS, email, письмо) | динамич. |
| CallScript | Скрипты звонков по стадиям и психотипам | ~20 |
| Promise | Обещания клиента о платеже (pending → kept / broken / extended) | динамич. |

**Hard Collection:**

| Модель | Описание | Записей |
|--------|----------|---------|
| FieldVisit | Выездные мероприятия (по месту жительства/работы/к поручителю) | динамич. |

**Legal Collection:**

| Модель | Описание | Записей |
|--------|----------|---------|
| LegalCase | Судебное дело (досуд. претензия → иск → решение → ИП) | динамич. |
| LegalDocument | Юридические документы (претензия, иск, ходатайство, исп. лист) | динамич. |

**Реструктуризация:**

| Модель | Описание | Записей |
|--------|----------|---------|
| RestructuringRequest | Запрос на реструктуризацию с PD/LGD-оценкой | динамич. |

**Workflow Engine:**

| Модель | Описание | Записей |
|--------|----------|---------|
| WorkflowRule | Правила автоматических переходов (conditions → actions JSON) | ~10 |
| ScheduledAction | Запланированные действия (send_sms, escalate, check_promise...) | динамич. |

**Killer Features (ML + аналитика):**

| Модель | Описание | Записей |
|--------|----------|---------|
| ClientBehaviorProfile | Психотип клиента 360° (платёжная дисциплина, триггеры риска, каналы) | до 5000 |
| NextBestAction | NBA-рекомендации (когда/как/что предложить) | динамич. |
| SmartScript | Самообучающиеся скрипты с процентом успеха | ~30 |
| ConversationAnalysis | Анализ разговора (sentiment, эффективные фразы, комплаенс) | динамич. |
| ComplianceAlert | Алерты нарушений комплаенса (давление, угрозы, время, частота) | динамич. |
| ReturnForecast | Прогноз возврата долга (вероятность, NPV, рекомендация) | динамич. |

**Скоринг и ML:**

| Модель | Описание | Записей |
|--------|----------|---------|
| ScoringResult | Результат скоринга (балл 300-850, грейд A-E, ожидаемый возврат) | ~2000 |
| TrainingData | Обучающая выборка для модели просрочки (28 признаков + y) | ~700 |
| CreditApplication | Расширенная анкета заёмщика (10 разделов, 60+ полей) | динамич. |
| MLModelVersion | Версионирование ML-моделей (метрики, ROC-кривая, гиперпараметры) | ~10 |

**Compliance 230-ФЗ:**

| Модель | Описание | Записей |
|--------|----------|---------|
| ViolationLog | Журнал нарушений 230-ФЗ (11 статей, severity, блокировка) | динамич. |
| BankruptcyCheck | Проверка банкротства клиента (ЕФРСБ) | динамич. |

**Статистика:**

| Модель | Описание | Записей |
|--------|----------|---------|
| OperatorStatistics | Витрина данных: звонки, контакты, обещания, собрано по периодам | динамич. |

#### 5.2.10 CollectionCase (Кейс взыскания)

```python
class CollectionCase(models.Model):
    """Центральная сущность для управления процессом collection"""
    
    client = models.ForeignKey(Client)                 # Клиент
    credits = models.ManyToManyField(Credit)           # Кредиты (M2M)
    assigned_operator = models.ForeignKey(Operator)    # Назначенный оператор
    
    # Стадия взыскания
    stage = models.CharField(max_length=30)            # pre_collection → soft_early → soft_late → hard → legal_*
    priority = models.IntegerField()                   # Приоритет (1-6)
    priority_score = models.FloatField()               # Скоринг приоритета (0-100)
    
    # Суммы
    total_debt = models.DecimalField()                 # Общий долг
    overdue_amount = models.DecimalField()             # Просроченная сумма
    penalties = models.DecimalField()                  # Штрафы и пени
    overdue_days = models.IntegerField()               # Дней просрочки
    
    # ML-прогнозы
    return_probability = models.FloatField()           # Вероятность возврата
    predicted_return_amount = models.DecimalField()    # Прогноз суммы возврата
    risk_segment = models.CharField()                  # Риск-сегмент
    
    # Счётчики
    total_contacts = models.IntegerField()             # Всего контактов
    successful_contacts = models.IntegerField()        # Успешных контактов
    promises_count = models.IntegerField()             # Количество обещаний
    broken_promises = models.IntegerField()            # Нарушенных обещаний
    
    # Психотип и стратегия
    psychotype = models.CharField()                    # Психотип
    recommended_strategy = models.CharField()          # Рекомендованная стратегия
```

**Стадии Collection Case:**

| Стадия | DPD | Описание |
|--------|-----|----------|
| `pre_collection` | -7 to 0 | Раннее предупреждение |
| `soft_early` | 1-30 | Мягкое взыскание (ранняя) |
| `soft_late` | 31-60 | Мягкое взыскание (поздняя) |
| `hard` | 61-90 | Жёсткое взыскание |
| `legal_pretrial` | 91-120 | Досудебная претензия |
| `legal_court` | 121+ | Судебное производство |
| `legal_execution` | 121+ | Исполнительное производство |
| `restructured` | any | Реструктуризация |
| `settled` | — | Урегулировано |
| `sold` / `written_off` | — | Продано / Списано |

#### 5.2.11 ClientBehaviorProfile (Поведенческий профиль клиента)

```python
class ClientBehaviorProfile(models.Model):
    """Психотип клиента и поведенческий профиль (360° портрет)"""
    
    client = models.OneToOneField(Client)              # 1:1 с клиентом
    
    psychotype = models.CharField()                    # Психотип
    psychotype_confidence = models.FloatField()        # Уверенность (0-1)
    
    # Платёжная дисциплина
    payment_discipline_score = models.FloatField()     # Оценка (0-1)
    avg_days_overdue = models.FloatField()             # Средняя просрочка
    payments_on_time_ratio = models.FloatField()       # Доля вовремя (0-1)
    
    # Оптимальное время контакта
    best_contact_hour = models.IntegerField()          # Лучший час (0-23)
    best_contact_day = models.IntegerField()           # Лучший день (0=Пн)
    preferred_channel = models.CharField()             # Предпочтительный канал
    
    # Триггеры риска
    job_changed_recently = models.BooleanField()       # Смена работы
    income_dropped = models.BooleanField()             # Падение дохода
    activity_dropped = models.BooleanField()           # Падение активности
    multiple_credits = models.BooleanField()           # Много кредитов
    
    # Прогноз возврата
    return_probability = models.FloatField()           # Вероятность (0-1)
    expected_return_days = models.IntegerField()       # Ожидаемый срок (дней)
    strategic_recommendation = models.CharField()      # Рекомендация (continue/restructure/legal/sell/write_off)
```

**Психотипы:**

| Код | Описание | Стратегия |
|-----|----------|-----------|
| `forgetful` | Забыл / Прокрастинирует | Мягкое напоминание, SMS |
| `unwilling` | Может платить, но не хочет | Жёсткое требование, последствия |
| `unable` | Хочет, но не может | Реструктуризация, эмпатия |
| `toxic` | Токсичный / Конфликтный | Только письменные каналы |
| `cooperative` | Готов к диалогу | Стандартный подход |

#### 5.2.12 ViolationLog (Нарушения 230-ФЗ)

```python
class ViolationLog(models.Model):
    """Журнал нарушений 230-ФЗ — аудит комплаенса"""
    
    client = models.ForeignKey(Client)                 # Клиент
    operator = models.ForeignKey(Operator)             # Оператор
    rule_type = models.CharField()                     # Тип нарушения (11 статей)
    severity = models.CharField()                      # Серьёзность (low/medium/high/critical)
    description = models.TextField()                   # Описание
    action_blocked = models.BooleanField()             # Действие заблокировано
    contact_type = models.CharField()                  # Канал контакта
    details = models.JSONField()                       # Подробности (JSON)
```

**Типы нарушений (по статьям 230-ФЗ):**

| Код | Статья | Описание |
|-----|--------|----------|
| `st1_time` | Ст.1 | Нарушение времени контакта |
| `st2_frequency` | Ст.2 | Превышение частоты контактов |
| `st3_refusal` | Ст.3 | Контакт при отказе клиента |
| `st4_third_party` | Ст.4 | Контакт с третьими лицами без согласия |
| `st5_script` | Ст.5 | Неутверждённый скрипт |
| `st6_identification` | Ст.6 | Нарушение идентификации оператора |
| `st7_bankruptcy` | Ст.7 | Контакт с банкротом |
| `st8_hidden_number` | Ст.8 | Скрытый номер звонящего |
| `st9_interval` | Ст.9 | Нарушение минимального интервала (4 часа) |
| `st10_history` | Ст.10 | Нарушение хранения истории |
| `st11_personal_data` | Ст.11 | Нарушение 152-ФЗ ПДн |

#### 5.2.13 ScoringResult (Результат скоринга)

```python
class ScoringResult(models.Model):
    """Результат скоринга (2000 записей)"""
    
    client = models.ForeignKey(Client)                 # Клиент
    credit = models.ForeignKey(Credit)                 # Кредит
    calculation_date = models.DateField()              # Дата расчёта
    probability = models.FloatField()                  # Вероятность дефолта (PD)
    risk_segment = models.CharField()                  # Сегмент (low/medium/high/critical)
    
    # Расширенный скоринг
    score_value = models.IntegerField()                # Скоринговый балл (300-850)
    model_version = models.CharField()                 # Версия модели
    model_type = models.CharField()                    # Тип алгоритма
    roc_auc = models.FloatField()                      # ROC-AUC модели
    grade = models.CharField()                         # Грейд (A-E)
    
    # Экономическая модель
    expected_recovery = models.DecimalField()           # Ожидаемый возврат (₽)
    cost_per_contact = models.DecimalField()            # Стоимость контакта (₽)
    expected_profit = models.DecimalField()             # Ожидаемая прибыль (₽)
```

#### 5.2.14 CreditApplication (Заявка на кредит)

Расширенная анкета заёмщика на основе типовой банковской анкеты (60+ полей):

| Раздел | Поля | Описание |
|--------|------|----------|
| 1. Персональные данные | ФИО, дата/место рождения, пол, паспорт, ИНН, СНИЛС | Идентификация |
| 2. Контакты | Телефоны, email, адрес регистрации, адрес проживания | Связь |
| 3. Семья | Семейное положение, супруг(а), иждивенцы | Социальный профиль |
| 4. Образование | Уровень образования (среднее → учёная степень) | Квалификация |
| 5. Занятость | Тип, работодатель, отрасль, должность, стаж | Стабильность |
| 6. Доходы/расходы | 5 видов дохода, 5 видов расходов, текущие кредиты | Платёжеспособность |
| 7. Имущество | Недвижимость, авто, вклады | Обеспечение |
| 8. Кредитная история | Просрочки, банкротство, суд. взыскания | Кредитоспособность |
| 9. Параметры кредита | Цель, сумма, срок, залог, поручитель | Запрос |
| 10. Результаты | approved_probability, decision, decision_comment | ML-скоринг |

**Вычисляемые свойства (properties):**
- `total_income` — сумма всех видов дохода
- `total_expenses` — сумма всех расходов + платежи по кредитам
- `debt_to_income_ratio` — DTI = (ежемесячный платёж + расходы) / доход

#### 5.2.15 MLModelVersion (Версионирование ML-моделей)

```python
class MLModelVersion(models.Model):
    """Версионирование ML-моделей"""
    
    name = models.CharField()                          # Название модели
    version = models.CharField()                       # Версия
    model_type = models.CharField()                    # Тип алгоритма (RF, GB, LR)
    
    # Метрики качества
    accuracy = models.FloatField()                     # Accuracy
    precision = models.FloatField()                    # Precision
    recall = models.FloatField()                       # Recall
    f1_score = models.FloatField()                     # F1-Score
    roc_auc = models.FloatField()                      # ROC-AUC
    cv_mean = models.FloatField()                      # CV Mean
    cv_std = models.FloatField()                       # CV Std
    
    # Параметры
    hyperparameters = models.JSONField()               # Гиперпараметры (JSON)
    feature_names = models.JSONField()                 # Признаки
    feature_importances = models.JSONField()           # Важность признаков
    confusion_matrix = models.JSONField()              # Матрица ошибок
    roc_curve_fpr = models.JSONField()                 # ROC FPR (точки)
    roc_curve_tpr = models.JSONField()                 # ROC TPR (точки)
    
    training_data_size = models.IntegerField()         # Размер выборки
    is_active = models.BooleanField()                  # Активная модель
    model_path = models.CharField()                    # Путь к файлу
```

#### 5.3.1 Объёмы данных

| Сущность | Количество записей | Описание |
|----------|-------------------|----------|
| Client | 5 000 | Клиенты банка |
| Credit | 700 | Кредитные договоры |
| CreditState | ~21 000 | Помесячная прогрессия состояний |
| Payment | ~19 000 | Платежи с реалистичным жизненным циклом |
| Intervention | 10 000 | Воздействия по кредитам |
| Operator | 50 | Операторы (ID 51-100) |
| Assignment | 3 000 | Назначения на текущий день |
| ScoringResult | ~2 000 | Результаты скоринга (балл + грейд) |
| TrainingData | ~700 | Обучающая выборка (28 признаков) |
| CreditApplication | динамич. | Расширенные заявки (60+ полей) |
| ClientBehaviorProfile | до 5 000 | Поведенческие профили (1:1 с Client) |
| CollectionCase | динамич. | Кейсы взыскания (полный цикл) |
| ViolationLog | динамич. | Нарушения 230-ФЗ (аудит) |
| MLModelVersion | ~10 | Версии ML-моделей с метриками |
| OperatorStatistics | динамич. | Статистика операторов по периодам |

#### 5.3.2 Процентные ставки по типам продуктов

| Тип продукта | Диапазон ставок | Описание |
|-------------|----------------|----------|
| consumer | 12-25% | Потребительский кредит |
| mortgage | 7-15% | Ипотека |
| car | 10-20% | Автокредит |
| credit_card | 22-36% | Кредитная карта |
| microloan | 30-90% | Микрозайм |

> Ежемесячные платежи рассчитаны по формуле **аннуитета** (см. раздел 7.2).

#### 5.3.3 CreditState — помесячная прогрессия

Для каждого кредита генерируется цепочка ежемесячных состояний от `open_date` до текущей даты:
- Основной долг (`principal_debt`) убывает с каждым месяцем
- Просрочка (`overdue_principal`, `overdue_interest`, `penalties`) начинается в точке 30-60% от длительности кредита
- `overdue_days` нарастает после начала просрочки

---

## 6. REST API

### 6.1 Общая информация

**Base URL:** `http://localhost:8000/api/`

**Формат:** JSON

**Аутентификация:** В текущей версии все API endpoints используют `AllowAny` (доступ без авторизации). Token-based аутентификация подготовлена для production.

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
  "full_name": "Иванов Иван Петрович",
  "birth_date": "1985-03-15",
  "gender": "M",
  "marital_status": "married",
  "employment": "employed",
  "employer_name": "ООО Технологии",
  "position": "Менеджер",
  "income": "85000.00",
  "monthly_expenses": "35000.00",
  "children_count": 1,
  "phone_mobile": "+7 (999) 123-45-67",
  "phone_work": "+7 (495) 111-22-33",
  "phone_home": "",
  "city": "Москва",
  "region": "Московская область",
  "category": "standard"
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
| status | string | Фильтр по статусу (поддерживает значения через запятую: `?status=overdue,default`) |
| client | integer | ID клиента |

**Пример ответа GET /api/credits/1/:**
```json
{
  "id": 1,
  "client": 1,
  "client_name": "Иванов Иван Петрович",
  "client_phone": "+7 (999) 123-45-67",
  "principal_amount": "500000.00",
  "interest_rate": "18.50",
  "monthly_payment": "18150.00",
  "product_type": "consumer",
  "status": "overdue",
  "open_date": "2024-03-15",
  "planned_close_date": "2027-03-15",
  "actuality_date": "2026-03-01",
  "term_months": 36,
  "delinquency_bucket": "30-60",
  "days_past_due": 42,
  "latest_state": {
    "id": 123,
    "state_date": "2026-03-01",
    "principal_debt": "320000.00",
    "overdue_principal": "45000.00",
    "overdue_interest": "3200.00",
    "penalties": "1500.00",
    "overdue_days": 42
  }
}
```

> **Примечание:** Поля `client_name`, `client_phone`, `term_months`, `delinquency_bucket`, `days_past_due` и `latest_state` вычисляются в сериализаторе и не хранятся в модели.

#### 6.2.3 Состояния кредитов

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/credit-states/` | Все состояния |
| GET | `/api/credit-states/?credit={id}` | Состояния кредита |
| GET | `/api/credit-states/?client={id}` | Состояния по клиенту |

> Сортировка по умолчанию: `-state_date` (новые сначала)

#### 6.2.4 Платежи

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/payments/` | Список платежей |
| GET | `/api/payments/?credit={id}` | Платежи по кредиту |
| GET | `/api/payments/?client={id}` | Платежи по клиенту |
| POST | `/api/payments/` | Создать платёж |

> Сортировка по умолчанию: `-payment_date` (новые сначала)

#### 6.2.5 Воздействия (Interventions)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/interventions/` | Список воздействий |
| GET | `/api/interventions/?client_id={id}` | Воздействия по клиенту |
| GET | `/api/interventions/?client={id}` | Воздействия по клиенту (алиас) |
| POST | `/api/interventions/` | Создать воздействие |

> Сортировка по умолчанию: `-datetime`. Поддерживает `?ordering=` для смены сортировки.

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

#### 6.2.7 Нарушения 230-ФЗ (ViolationLog)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/violations/` | Список нарушений (последние 200) |
| GET | `/api/violations/?client_id={id}` | Нарушения по клиенту |
| GET | `/api/violations/?operator_id={id}` | Нарушения по оператору |
| GET | `/api/violations/?rule_type=st1_time` | Фильтр по типу нарушения |
| GET | `/api/violations/?severity=critical` | Фильтр по серьёзности |

**Пример ответа GET /api/violations/:**
```json
[
  {
    "id": 1,
    "client": 42,
    "client_name": "Петров П.П.",
    "operator": 3,
    "operator_name": "Иванов И.И.",
    "rule_type": "st1_time",
    "rule_type_display": "Ст.1 Нарушение времени контакта",
    "severity": "high",
    "severity_display": "Высокая",
    "description": "Ст.1: Звонок в нерабочее время",
    "action_blocked": true,
    "contact_type": "phone",
    "details": {},
    "created_at": "2026-03-10T23:15:00Z"
  }
]
```

#### 6.2.8 Скоринг

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/scorings/` | Результаты скоринга |
| GET | `/api/scorings/?credit={id}` | Скоринг кредита |

#### 6.2.9 Операторы

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/operators/` | Список операторов |
| GET | `/api/operators/{id}/` | Детали оператора |
| GET | `/api/operators/{id}/queue/` | Очередь оператора |

#### 6.2.10 Назначения

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/assignments/` | Список назначений (только с overdue > 0) |
| GET | `/api/assignments/?operator_id={id}` | Назначения оператора |
| GET | `/api/assignments/?operator={id}` | Назначения оператора (алиас) |
| POST | `/api/assignments/distribute/` | Запустить распределение |

> Сортировка по умолчанию: `-priority, -overdue_amount`. Сериализатор дополняет каждое назначение полями: `operator_name`, `client_name`, `client_phone`, `client_id`, `last_promise_amount`, `last_promise_date`, `total_attempts`.

#### 6.2.11 Поведенческие профили

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/profiles/` | Список поведенческих профилей |
| GET | `/api/profiles/{id}/` | Детали профиля |
| POST | `/api/profiles/{id}/analyze_client/` | Запустить ML-анализ психотипа |

#### 6.2.12 Next Best Action (NBA)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/nba/` | Список рекомендаций |
| GET | `/api/nba/?client={id}` | NBA для клиента |
| POST | `/api/nba/{id}/execute/` | Отметить рекомендацию выполненной |
| POST | `/api/nba/{id}/skip/` | Пропустить рекомендацию |

#### 6.2.13 Smart-скрипты

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/scripts/` | Список скриптов |
| GET | `/api/scripts/for_context/` | Скрипты для контекста (психотип, сценарий) |

#### 6.2.14 Compliance-алерты

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/compliance-alerts/` | Список алертов |
| POST | `/api/compliance-alerts/{id}/resolve/` | Закрыть алерт с комментарием |

#### 6.2.15 Прогнозы возврата

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/forecasts/` | Список прогнозов |
| GET | `/api/forecasts/?credit={id}` | Прогноз по кредиту |

#### 6.2.16 Дашборд и аналитика

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/dashboard/` | Полный дашборд (operator_stats, daily_calls, hourly, call_results) |
| GET | `/api/dashboard/stats/` | Сводная статистика (клиенты, кредиты, платежи, каналы, NBA) |
| GET | `/api/dashboard/operator/` | Статистика текущего оператора |
| GET | `/api/dashboard/operator/{id}/` | Статистика конкретного оператора |

**Параметры запроса дашборда:**

| Параметр | Описание | Значения |
|----------|----------|----------|
| period | Период агрегации | `day`, `week`, `month` |
| operator_id | ID оператора | число |

**Пример ответа GET /api/dashboard/operator/51/:**
```json
{
  "today": {
    "calls_total": 42,
    "successful_contacts": 28,
    "contact_rate": 66.7,
    "promises_count": 8,
    "promise_amount": 245000,
    "avg_duration": 185
  },
  "daily_dynamics": [...],
  "hourly_activity": [...],
  "top_promises": [...]
}
```

#### 6.2.17 Прогнозирование просрочки

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/overdue-prediction/?credit_id={id}` | Прогноз для одного кредита |
| GET | `/api/overdue-prediction/?client_id={id}` | Прогноз для всех кредитов клиента |
| POST | `/api/overdue-prediction/` | Пакетный прогноз с ранжированием |

**Пример ответа:**
```json
{
  "credit_id": 123,
  "client_name": "Иванов И.П.",
  "risk_category": "high",
  "risk_probability": 0.82,
  "risk_factors": [
    {"factor": "overdue_share_12m", "value": 0.45, "impact": "high"},
    {"factor": "max_overdue_days", "value": 67, "impact": "high"}
  ],
  "features": {...}
}
```

#### 6.2.18 Обучение ML-моделей

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/ml/train-overdue/` | Обучить модель прогноза просрочки (RF, 26 признаков) |
| POST | `/api/ml/train-approval/` | Обучить модель одобрения заявок (GB, 31 признак) |
| GET | `/api/ml/models/` | Список версий ML-моделей |
| GET | `/api/ml/models/?active=true` | Только активные модели |
| GET | `/api/ml/models/{id}/` | Детали конкретной модели |

**Пример ответа POST /api/ml/train-overdue/:**
```json
{
  "status": "success",
  "model_type": "RandomForestClassifier",
  "accuracy": 0.78,
  "cv_mean": 0.75,
  "cv_std": 0.03,
  "feature_importances": {
    "max_overdue_days": 0.15,
    "overdue_share_12m": 0.12,
    "lti_ratio": 0.10
  }
}
```

#### 6.2.19 Скоринг дашборд

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/scoring/dashboard/` | Визуализация скоринга (грейды, гистограмма, прибыль) |

#### 6.2.20 Compliance 230-ФЗ

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/compliance/check/?client_id={id}&contact_type={type}` | Проверить можно ли связаться с клиентом |
| GET/POST | `/api/compliance/bankruptcy/?client_id={id}` | Проверить/зарегистрировать банкротство |
| GET | `/api/compliance/summary/` | Сводка комплаенса (заблокировано, проверки, рейт) |
| GET | `/api/violations/` | Журнал нарушений 230-ФЗ |

**Пример ответа GET /api/compliance/check/?client_id=1&contact_type=phone:**
```json
{
  "allowed": false,
  "violations": [
    {"rule": "st2_frequency", "description": "Превышен лимит звонков (1/день)"},
    {"rule": "st1_time", "description": "Звонки запрещены в это время"}
  ],
  "limits": {
    "calls_today": 1,
    "calls_this_week": 2,
    "max_calls_per_day": 1,
    "max_calls_per_week": 2
  }
}
```

#### 6.2.21 A/B тестирование и распределение

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/ab-test/results/` | Сравнение группы A (случайное) vs B (умное) |
| POST | `/api/distribution/run/` | Запуск интеллектуального распределения |

#### 6.2.22 Аудит

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/audit/` | Журнал аудита (фильтры: action, severity, operator_id, client_id) |

#### 6.2.23 Ежедневные состояния кредитов

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/credit-daily-states/?credit_id={id}` | Интерполированные ежедневные состояния из помесячных CreditState |

#### 6.2.24 Документация API (OpenAPI / Swagger)

| URL | Описание |
|-----|----------|
| `/api/docs/` | Swagger UI — интерактивная документация |
| `/api/redoc/` | ReDoc — альтернативная документация |
| `/api/schema/` | OpenAPI 3.0 JSON-схема |

> Автодокументация реализована с помощью **drf-spectacular**. Все эндпоинты, сериализаторы и параметры автоматически попадают в схему.

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
│   └── tests.py           # Unit / Integration тесты (37 тестов, 10 классов)
├── test_api_prediction.py # API тесты
└── test_loan_predictor.py # ML тесты
```

### 11.2 Обзор тестовых классов

| Класс | Тестов | Область покрытия |
|-------|--------|------------------|
| `ClientModelTest` | 3 | Создание клиента, дефолты `contact_refused` / `is_bankrupt` |
| `CreditModelTest` | 7 | Создание кредита, бакеты просрочки (current, 0-30, 30-60, 60-90, 90+), `days_past_due` |
| `ViolationLogModelTest` | 1 | Создание записи ViolationLog с дефолтами |
| `ComplianceContactTest` | 7 | 230-ФЗ: разрешение/блокировка контактов (банкрот, отказ, канал, лимит звонков, третьи лица) |
| `ComplianceLogTest` | 2 | Логирование нарушений в ViolationLog и AuditLog |
| `ComplianceValidationTest` | 3 | Валидация Intervention: идентификация оператора, обязательные поля |
| `DistributionServiceTest` | 2 | DistributionService: ранжирование по опыту, инстанцирование |
| `BankruptcyTest` | 3 | Проверка банкротства: сервис, блокировка/разрешение контакта |
| `APIEndpointTest` | 8 | REST API: clients, credits, compliance/check, violations, scoring, operators, swagger |
| `DelinquencyBucketAPITest` | 1 | `delinquency_bucket` в ответе `/api/credits/` |

### 11.3 Запуск тестов

```bash
# Все тесты
python manage.py test

# Конкретный файл
python manage.py test collection_app.tests

# Подробный вывод
python manage.py test collection_app.tests -v 2

# С покрытием
pip install coverage
coverage run manage.py test
coverage report
```

### 11.4 Примеры тестов

```python
# tests.py
from django.test import TestCase
from collection_app.models import Client, Credit

class CreditModelTest(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(
            full_name='Тестов Тест Тестович',
            phone_mobile='+7 (999) 999-99-99',
            gender='M',
            employment='employed',
            income=80000
        )
    
    def test_credit_creation(self):
        credit = Credit.objects.create(
            client=self.client_obj,
            principal_amount=100000,
            interest_rate=15.0,
            monthly_payment=8000,
            open_date='2024-01-15',
            planned_close_date='2025-01-15'
        )
        self.assertEqual(credit.status, 'active')
    
    def test_monthly_payment_calculation(self):
        # Тест расчёта платежа
        pass
```

### 11.5 API тесты

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

### 12.5 Security Middleware (новое)

Система включает набор middleware для защиты API:

**Rate Limiting:**
```python
# Лимиты по умолчанию
DEFAULT_RATE_LIMITS = {
    'default': (100, 60),      # 100 запросов/минуту
    'auth': (10, 60),          # 10 попыток авторизации/минуту
    'api_write': (30, 60),     # 30 операций записи/минуту
    'export': (5, 300),        # 5 экспортов/5 минут
}
```

**Audit Logging:**
- Логирование всех CRUD операций
- Отслеживание доступа к персональным данным (ФЗ-152)
- IP-адрес и User-Agent для каждого действия

**Security Headers:**
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- X-Content-Type-Options: nosniff
- Content-Security-Policy (production)
- Strict-Transport-Security (HTTPS)

**Request Validation:**
- Защита от SQL injection
- Защита от XSS
- Ограничение размера запроса (10 MB)

---

## 13. Collection Workflow (BPMN)

### 13.1 Полный цикл Collection

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                            COLLECTION WORKFLOW (BPMN)                                 │
└──────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌─────────────┐
                                    │   START     │
                                    │ (Просрочка) │
                                    └──────┬──────┘
                                           │
                                           v
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              PRE-COLLECTION (DPD -7 to 0)                             │
│                                                                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐           │
│  │   Алерт     │ -> │  Автоматич. │ -> │  Отслежив.  │ -> │  Платёж?    │           │
│  │ Early Risk  │    │  SMS/Email  │    │  реакции    │    │             │           │
│  └─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘           │
│                                                                   │                  │
│                                                            Да ────┴──── Нет          │
│                                                             │            │           │
│                                                             v            v           │
│                                                        ┌────────┐   ┌────────┐      │
│                                                        │ CLOSED │   │ SOFT   │      │
│                                                        └────────┘   └────────┘      │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           v
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                         SOFT COLLECTION (DPD 1-60)                                    │
│                                                                                       │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │                          SOFT EARLY (DPD 1-30)                                 │   │
│  │                                                                                │   │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐         │   │
│  │  │   SMS   │-->│  Звонок │-->│ Promise │-->│Проверка │-->│ Оплата? │         │   │
│  │  │reminder │   │ #1      │   │ to Pay  │   │ PTP     │   │         │         │   │
│  │  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └────┬────┘         │   │
│  │                                                                │              │   │
│  └───────────────────────────────────────────────────────────────┼──────────────┘   │
│                                                                   │                  │
│                                                          Да ──────┼────── Нет        │
│                                                           │       │        │         │
│                                                           v       │        v         │
│                                                      ┌────────┐   │   ┌────────┐    │
│                                                      │ CLOSED │   │   │SOFT    │    │
│                                                      └────────┘   │   │LATE    │    │
│                                                                   │   └────────┘    │
│  ┌───────────────────────────────────────────────────────────────┼──────────────┐   │
│  │                          SOFT LATE (DPD 31-60)                 │              │   │
│  │                                                                v              │   │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐         │   │
│  │  │ Интенс. │-->│ Письмо  │-->│Реструкт.│-->│ Promise │-->│Эскалация│         │   │
│  │  │ звонки  │   │требован.│   │ офер?   │   │ #2      │   │ в HARD  │         │   │
│  │  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘         │   │
│  │                                                                               │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           v
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                         HARD COLLECTION (DPD 61-90)                                   │
│                                                                                       │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐               │
│  │ Письмо  │-->│  Выезд  │-->│ Визит   │-->│Результат│-->│Эскалация│               │
│  │претензия│   │ плани-  │   │         │   │ визита  │   │ LEGAL   │               │
│  │         │   │ рование │   │         │   │         │   │         │               │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘               │
│       │                                          │                                   │
│       v                                          v                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐            │
│  │                  РЕСТРУКТУРИЗАЦИЯ (опционально)                     │            │
│  │                                                                     │            │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐        │            │
│  │  │ Заявка   │-->│ Анализ   │-->│ Решение  │-->│Активация │        │            │
│  │  │          │   │ PD/LGD   │   │ одобрено?│   │ нового   │        │            │
│  │  │          │   │          │   │          │   │ графика  │        │            │
│  │  └──────────┘   └──────────┘   └──────────┘   └──────────┘        │            │
│  └─────────────────────────────────────────────────────────────────────┘            │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           v
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                         LEGAL COLLECTION (DPD 91+)                                    │
│                                                                                       │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                          ДОСУДЕБНАЯ СТАДИЯ                                    │   │
│  │                                                                               │   │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐                                  │   │
│  │  │Досудебная│-->│ Ожидание │-->│  Ответ   │                                  │   │
│  │  │претензия │   │ 30 дней  │   │ получен? │                                  │   │
│  │  └──────────┘   └──────────┘   └──────────┘                                  │   │
│  │                                      │                                        │   │
│  │                              Да ─────┼───── Нет                               │   │
│  │                               │      │       │                                │   │
│  │                               v      │       v                                │   │
│  │                          ┌────────┐  │  ┌────────┐                           │   │
│  │                          │Мировое │  │  │  Иск   │                           │   │
│  │                          │соглаш. │  │  │в суд   │                           │   │
│  │                          └────────┘  │  └────────┘                           │   │
│  └──────────────────────────────────────┼───────────────────────────────────────┘   │
│                                         │                                            │
│  ┌──────────────────────────────────────┼───────────────────────────────────────┐   │
│  │                          СУДЕБНАЯ СТАДИЯ                                      │   │
│  │                                      v                                        │   │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐                   │   │
│  │  │  Подача  │-->│Заседания │-->│ Решение  │-->│ Апелляция│                   │   │
│  │  │  иска    │   │          │   │          │   │ (опц.)   │                   │   │
│  │  └──────────┘   └──────────┘   └──────────┘   └──────────┘                   │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                            │
│  ┌──────────────────────────────────────┼───────────────────────────────────────┐   │
│  │                     ИСПОЛНИТЕЛЬНОЕ ПРОИЗВОДСТВО                               │   │
│  │                                      v                                        │   │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐                   │   │
│  │  │Исполнит. │-->│  Работа  │-->│ Арест    │-->│Взыскание │                   │   │
│  │  │  лист    │   │ с ФССП   │   │ активов  │   │          │                   │   │
│  │  └──────────┘   └──────────┘   └──────────┘   └──────────┘                   │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           v
                              ┌────────────────────────┐
                              │         END            │
                              │                        │
                              │  ┌─────────────────┐   │
                              │  │ • Погашен       │   │
                              │  │ • Реструктуриз. │   │
                              │  │ • Продан        │   │
                              │  │ • Списан        │   │
                              │  └─────────────────┘   │
                              └────────────────────────┘
```

### 13.2 Правила автоматических переходов (Workflow Rules)

| From Stage | To Stage | Условия | Действия |
|------------|----------|---------|----------|
| pre_collection | soft_early | DPD >= 1 | Создать задачу звонка |
| soft_early | soft_late | DPD >= 31 OR broken_promises >= 2 | Уведомить менеджера |
| soft_late | hard | DPD >= 61 OR contacts_without_result >= 10 | Запланировать выезд |
| hard | legal_pretrial | DPD >= 91 | Создать судебное дело |
| legal_pretrial | legal_court | 30 дней без ответа на претензию | Подготовить иск |
| * | restructured | Одобрена реструктуризация | Активировать новый график |
| * | settled | Полная оплата | Закрыть кейс |

### 13.3 Модель данных Workflow

```python
class WorkflowRule:
    name: str                    # Название правила
    from_stage: str              # Исходная стадия
    to_stage: str                # Целевая стадия
    conditions: Dict             # Условия срабатывания (JSON)
    actions: Dict                # Действия при переходе (JSON)
    priority: int                # Приоритет (меньше = выше)
    is_active: bool              # Активно ли правило

# Пример условий:
conditions = {
    "overdue_days": {"gte": 30},
    "broken_promises": {"gte": 2},
    "total_contacts": {"gte": 5}
}

# Пример действий:
actions = {
    "create_task": "call_followup",
    "change_priority": 5,
    "notify_manager": True,
    "schedule_action": {
        "type": "send_sms",
        "delay_hours": 24,
        "parameters": {"template": "demand"}
    }
}
```

---

## 14. Комплаенс 230-ФЗ

### 14.1 Обзор

Система реализует проверку соответствия требованиям **Федерального закона № 230-ФЗ** «О защите прав и законных интересов физических лиц при осуществлении деятельности по возврату просроченной задолженности».

**Файл:** `backend/collection_app/services/compliance_230fz.py`

### 14.2 Проверки при контакте (`can_contact`)

При каждом контакте с клиентом система автоматически проверяет:

| # | Проверка | Статья | Описание |
|---|----------|--------|----------|
| 1 | Банкротство | Ст. 7 | Контакт с банкротом запрещён |
| 2 | Отказ от взаимодействия | Ст. 3 | Клиент отказался от контактов (`contact_refused = True`) |
| 3 | Отказ по каналу | Ст. 3 | Отказ от конкретного канала связи (`refused_channels`) |
| 4 | Время контакта | Ст. 1 | Будни: 8:00–22:00, выходные: 9:00–20:00 |
| 5 | Частота звонков | Ст. 2 | Не более 2 телефонных звонков в сутки |
| 6 | Третьи лица | Ст. 4 | Контакт с третьими лицами только при наличии согласия |

### 14.3 Журнал нарушений (ViolationLog)

При блокировке контакта система автоматически фиксирует нарушение:

```
can_contact() → violations[] → log_compliance_violation()
                                      │
                           ┌──────────┴──────────┐
                           │                     │
                      ViolationLog          AuditLog
                   (отдельная таблица)    (общий лог)
```

Каждое нарушение записывается в модель **ViolationLog** с привязкой к:
- Клиенту (client)
- Оператору (operator)
- Типу нарушения по статье закона (rule_type: st1..st11)
- Уровню серьёзности (severity: low/medium/high/critical)
- Каналу контакта (contact_type)

### 14.4 API

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/compliance/check/?client_id=123&type=phone` | Проверка допустимости контакта |
| GET | `/api/compliance/bankruptcy/?client_id=123` | Проверка банкротства |
| POST | `/api/compliance/bankruptcy/` | Регистрация банкротства |
| GET | `/api/violations/` | Журнал нарушений с фильтрами |

---

## 15. Roadmap развития

### 15.1 Текущий статус (v3.1)

| Компонент | Статус | Описание |
|-----------|--------|----------|
| Архитектура | ✅ MVP+ | Services layer, RBAC, Audit |
| ML модели | ✅ Базовые | RandomForest, Pipeline с метриками |
| Security | ✅ Базовая | Rate limiting, Audit, Middleware |
| Collection процессы | ✅ Полный цикл | Pre → Soft → Hard → Legal |
| Workflow Engine | ✅ Реализован | Rules Engine с автопереходами |
| Данные | ✅ Качество | ~21k CreditState, ~19k Payments, ставки по продуктам |
| Рабочий стол оператора | ✅ Реализован | Персональная очередь, декомпозиция долга, навигация |
| Client 360° | ✅ Реализован | Реальные API, NBA, история воздействий |
| Комплаенс 230-ФЗ | ✅ Реализован | ViolationLog, проверки, банкротство |
| DPD бакеты | ✅ Реализованы | delinquency_bucket / days_past_due в Credit |
| API документация | ✅ Swagger / ReDoc | drf-spectacular, OpenAPI 3.0 |
| Тесты | ✅ 37 тестов | 10 классов: модели, комплаенс, API, распределение |
| Бизнес-логика | ⚙️ 80% | Базовые процессы + рабочее место оператора |
| Интеграции | ❌ Нет | SMS, CTI, БКИ — заглушки |
| CI/CD | ❌ Нет | Требуется настройка |

### 15.2 Версия 2.1 (Q2 2026)

**Фокус: Интеграции и автоматизация**

- [ ] Интеграция с SMS-шлюзом (SMSC, Twilio)
- [ ] Интеграция с Email-сервисом (SendGrid)
- [ ] CTI интеграция (Asterisk/FreeSWITCH)
- [ ] Асинхронные очереди (Celery + Redis)
- [ ] Scheduler для автоматических задач
- [ ] Webhook для внешних событий

### 15.3 Версия 2.2 (Q3 2026)

**Фокус: ML и аналитика**

- [ ] Улучшенная модель скоринга (XGBoost/LightGBM)
- [ ] A/B тестирование стратегий
- [ ] Real-time dashboards (Grafana)
- [ ] Мониторинг ML моделей (MLflow)
- [ ] Автоматическое переобучение
- [ ] Explainable AI (SHAP values)

### 15.4 Версия 3.0 (Q4 2026)

**Фокус: Enterprise-ready**

- [ ] Интеграция с АБС (Core Banking)
- [ ] Интеграция с БКИ (НБКИ, Эквифакс)
- [ ] Интеграция с ФССП/ГАС Правосудие
- [ ] Полный compliance ФЗ-230
- [ ] SOC 2 сертификация
- [ ] High Availability (HA) кластер
- [ ] Multi-tenant архитектура

### 15.5 Архитектура будущего (Target)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           TARGET ARCHITECTURE (v3.0)                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                           API GATEWAY (Kong/AWS)                             │   │
│  │              Rate Limiting • Auth • Routing • SSL Termination                │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                        │                                            │
│         ┌──────────────────────────────┼──────────────────────────────┐            │
│         │                              │                              │             │
│         v                              v                              v             │
│  ┌─────────────┐              ┌─────────────┐              ┌─────────────┐         │
│  │  Frontend   │              │  Backend    │              │   Admin     │         │
│  │   (React)   │              │  (Django)   │              │   Panel     │         │
│  │   CDN/S3    │              │  K8s Pods   │              │             │         │
│  └─────────────┘              └──────┬──────┘              └─────────────┘         │
│                                      │                                              │
│  ┌───────────────────────────────────┼────────────────────────────────────────┐    │
│  │                            MESSAGE BROKER                                   │    │
│  │                         (RabbitMQ / Kafka)                                  │    │
│  └───────────────────────────────────┼────────────────────────────────────────┘    │
│                                      │                                              │
│         ┌────────────────────────────┼────────────────────────────┐                │
│         │                            │                            │                 │
│         v                            v                            v                 │
│  ┌─────────────┐              ┌─────────────┐              ┌─────────────┐         │
│  │  Collection │              │     ML      │              │ Notification│         │
│  │   Worker    │              │   Service   │              │   Service   │         │
│  │             │              │   (MLflow)  │              │ SMS/Email   │         │
│  └─────────────┘              └─────────────┘              └─────────────┘         │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                              DATA LAYER                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │   │
│  │  │PostgreSQL│  │  Redis   │  │   S3     │  │Elastic   │  │ClickHouse│      │   │
│  │  │ Primary  │  │  Cache   │  │  Files   │  │ Logs     │  │Analytics │      │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                           EXTERNAL INTEGRATIONS                              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │   │
│  │  │   АБС    │  │   БКИ    │  │   CTI    │  │  ФССП    │  │   ЭДО    │      │   │
│  │  │Core Bank │  │НБКИ/Экви │  │ Asterisk │  │ГАС Право │  │  Диадок  │      │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 15.6 Оценка текущей готовности

| Критерий | Текущий проект | Требования для банка | Gap |
|----------|----------------|---------------------|-----|
| Архитектура | MVP+ с Services | Enterprise SOA | Средний |
| ML модели | RandomForest + Pipeline | Ensemble + MLOps | Средний |
| Security | Rate limit + Audit | SOC-ready + ПДн | Большой |
| Collection | Full cycle | + интеграции | Средний |
| Compliance | Базовый | ФЗ-230, ФЗ-152 | Большой |
| Scalability | Single server | HA Cluster | Большой |
| Integrations | Stubs | Real connections | Критический |

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
| PD | Probability of Default — вероятность дефолта |
| LGD | Loss Given Default — потери при дефолте |
| Bucket | Группировка по глубине просрочки |
| Roll Rate | Показатель миграции между bucket'ами |
| RBAC | Role-Based Access Control — ролевое управление доступом |
| BPMN | Business Process Model and Notation |
| CTI | Computer Telephony Integration |
| АБС | Автоматизированная банковская система |
| БКИ | Бюро кредитных историй |
| ФССП | Федеральная служба судебных приставов |

### Б. Коды статусов кредита

| Код | Название | Описание |
|-----|----------|----------|
| active | Активный | Кредит обслуживается |
| overdue | Просрочка | Есть просроченная задолженность |
| default | Дефолт | Глубокая просрочка (90+ дней) |
| closed | Закрыт | Кредит погашен |
| restructured | Реструктуризирован | Изменены условия |
| legal | Судебный | В судебном производстве |
| sold | Продан | Передан коллекторам |
| written_off | Списан | Списан с баланса |

### В. Коды стадий Collection Case

| Код | Название | DPD | Описание |
|-----|----------|-----|----------|
| pre_collection | Pre-Collection | -7 to 0 | Раннее предупреждение |
| soft_early | Soft Early | 1-30 | Мягкое взыскание (ранняя) |
| soft_late | Soft Late | 31-60 | Мягкое взыскание (поздняя) |
| hard | Hard Collection | 61-90 | Жёсткое взыскание |
| legal_pretrial | Досудебная | 91-120 | Досудебная претензия |
| legal_court | Судебная | 121+ | Судебное производство |
| legal_execution | Исполнительная | 121+ | Исполнительное производство |
| restructured | Реструктуризация | any | Изменение условий |
| settled | Урегулировано | - | Долг погашен |
| sold | Продано | - | Передано коллекторам |
| written_off | Списано | - | Признан безнадёжным |

### Г. Справочник API ошибок

| Код | Сообщение | Решение |
|-----|-----------|---------|
| AUTH_001 | Invalid credentials | Проверьте логин/пароль |
| AUTH_002 | Token expired | Получите новый токен |
| AUTH_003 | Insufficient permissions | Нет прав на операцию |
| VAL_001 | Invalid field format | Проверьте формат данных |
| VAL_002 | Required field missing | Добавьте обязательное поле |
| RATE_001 | Rate limit exceeded | Подождите и повторите |
| ML_001 | Model not loaded | Перезапустите сервер |
| ML_002 | Prediction failed | Проверьте входные данные |
| WF_001 | Invalid stage transition | Переход не разрешён |
| WF_002 | Rule condition failed | Условия правила не выполнены |

---

## История изменений

| Версия | Дата | Описание |
|--------|------|----------|
| 1.0.0 | 2026-02-05 | Начальная версия документации |
| 2.0.0 | 2026-02-05 | Полный цикл Collection, RBAC, Workflow Engine, Security Middleware, BPMN, Roadmap |
| 3.0.0 | 2026-03-15 | Обновление модели данных: Intervention вместо Interaction, CreditState с помесячной прогрессией (~21k записей), Payment с реалистичным жизненным циклом (~19k записей). Вычисляемые поля: term_months, latest_state, client_name, client_phone в CreditSerializer. Фильтры API: PaymentViewSet (?credit, ?client), CreditStateViewSet (?credit, ?client), AssignmentViewSet (?operator_id). Рабочий стол оператора: персональная очередь через Assignment, декомпозиция долга. Client360 — работа с реальными API вместо mock-данных. Процентные ставки по типам продуктов, аннуитетные платежи. |
| 3.1.0 | 2026-03-11 | Бакеты просрочки (DPD): свойства `delinquency_bucket` и `days_past_due` в Credit. Модель ViolationLog для аудита нарушений 230-ФЗ (12 типов нарушений, 4 уровня серьёзности, 4 индекса). API эндпоинт `/api/violations/` с фильтрами. Автодокументация API: drf-spectacular (Swagger `/api/docs/`, ReDoc `/api/redoc/`, OpenAPI схема `/api/schema/`). Комплексное тестирование: 37 тестов в 10 классах (модели, комплаенс, API, распределение, банкротство). |

---

*Документация создана для внутреннего использования. При возникновении вопросов обращайтесь к команде разработки.*
