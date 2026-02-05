@echo off
chcp 65001 > nul
cd /d C:\project\collection_app\backend
echo === Создание миграций ===
C:\Users\zkm_0\AppData\Local\Programs\Python\Python313\python.exe manage.py makemigrations
echo.
echo === Применение миграций ===
C:\Users\zkm_0\AppData\Local\Programs\Python\Python313\python.exe manage.py migrate
echo.
echo === Готово ===
pause
