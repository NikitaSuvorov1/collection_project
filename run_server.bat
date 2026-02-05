@echo off
chcp 65001 > nul
cd /d C:\project\collection_app\backend
echo === Запуск Django сервера ===
C:\Users\zkm_0\AppData\Local\Programs\Python\Python313\python.exe manage.py runserver 8000
