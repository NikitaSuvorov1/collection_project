@echo off
chcp 65001 > nul
cd /d C:\project\collection_app\backend
echo === Полная настройка базы данных ===
echo.
echo Шаг 1: Создание миграций...
C:\Users\zkm_0\AppData\Local\Programs\Python\Python313\python.exe manage.py makemigrations
echo.
echo Шаг 2: Применение миграций...
C:\Users\zkm_0\AppData\Local\Programs\Python\Python313\python.exe manage.py migrate
echo.
echo Шаг 3: Заполнение данными (5000 клиентов, 50 операторов, 700 кредитов и т.д.)...
C:\Users\zkm_0\AppData\Local\Programs\Python\Python313\python.exe manage.py populate_db
echo.
echo Шаг 4: Обучение ML модели...
C:\Users\zkm_0\AppData\Local\Programs\Python\Python313\python.exe manage.py train_loan_model --samples 2000
echo.
echo === Готово! Теперь запустите run_server.bat ===
pause
