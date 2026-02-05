Collection App - Debt Collection / Delinquency Department

This scaffold provides a minimal full-stack starting point for the Department for Delinquent Debt (ДРПЗ) information system described by the requirements.

What's included
- Backend: Django + Django REST Framework with token auth and models for clients, credits, payments, interventions, operators, scoring results, assignments and credit applications.
- ML stubs: two model stubs under `backend/ml/` and a management command to run scoring and save `ScoringResult` records.
- Frontend: React (Vite) simple app with login and basic pages for operator, manager and admin.
- DB: `docker-compose.yml` to run PostgreSQL locally. `.env.example` shows required environment variables.

Quick start (Windows PowerShell)

1) Start Postgres with Docker Compose
```powershell
cd c:\project\collection_app
docker-compose up -d
```

2) Create and activate a Python virtual environment (optional but recommended)
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

3) Configure environment
Copy `.env.example` to `.env` and edit if needed. The default uses SQLite if DB vars are not set.

4) Run migrations and create a superuser
```powershell
cd backend
python manage.py migrate
python manage.py loaddata fixtures/initial_data.json
python manage.py createsuperuser
python manage.py runserver
```

5) Start frontend
```powershell
cd ..\frontend
npm install
npm run dev
```

Notes
- The Django settings default to SQLite for convenience. When you use PostgreSQL, point the DB env vars to the docker-compose service.
- ML models are stubs in `backend/ml/`. Replace stub functions with real models and adapt `collection/management/commands/run_scoring.py` to schedule scoring on real data.

Next steps
- Implement business logic for automatic assignment, scoring pipelines, and real ML models.
- Harden authentication & permissions for production.
