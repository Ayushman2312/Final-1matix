@echo off
echo Activating virtual environment...
call C:\Users\hp5cd\Envs\one\Scripts\activate.bat

echo Starting Celery worker...
cd /d C:\Users\hp5cd\OneDrive\Desktop\1matrix\1matrix
celery -A matrix worker -l info -Q data_mining 