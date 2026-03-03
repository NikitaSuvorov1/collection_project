@echo off
cd /d %~dp0
python manage.py makemigrations collection_app
python manage.py migrate
echo Done!
