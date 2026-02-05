@echo off
chcp 65001 > nul
cd /d C:\project\collection_app\backend
echo === Заполнение базы данных ===
echo.
echo Шаг 1: Заполнение основных данных...
C:\Users\zkm_0\AppData\Local\Programs\Python\Python313\python.exe manage.py populate_db
echo.
echo Шаг 2: Обучение модели скоринга...
C:\Users\zkm_0\AppData\Local\Programs\Python\Python313\python.exe manage.py train_loan_model --samples 2000
echo.
echo === База данных заполнена! ===
pause
