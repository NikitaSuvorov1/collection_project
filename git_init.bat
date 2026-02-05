@echo off
chcp 65001 >nul
cd /d "%~dp0"

set GIT="C:\Program Files\Git\bin\git.exe"

echo Инициализация Git репозитория...
%GIT% init

echo.
echo Добавление файлов...
%GIT% add .

echo.
echo Создание первого коммита...
%GIT% commit -m "Initial commit: Collection Management System"

echo.
echo Переименование ветки в main...
%GIT% branch -M main

echo.
echo ============================================
echo Репозиторий готов!
echo.
echo Теперь создайте репозиторий на GitHub:
echo https://github.com/new
echo.
echo Затем выполните (замените YOUR_USERNAME):
echo %GIT% remote add origin https://github.com/YOUR_USERNAME/collection_app.git
echo %GIT% push -u origin main
echo ============================================
pause
