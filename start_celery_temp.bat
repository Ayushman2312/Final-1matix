@echo off
call "C:\Users\hp5cd\Envs\one\Scripts\activate.bat"
cd /d "C:\Users\hp5cd\OneDrive\Desktop\1matrix\1matrix"
echo Checking Redis connection...
ping -n 1 localhost > NUL
set CELERY_BROKER_CONNECTION_RETRY=true
set CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP=true
set CELERY_BROKER_CONNECTION_MAX_RETRIES=10
echo Starting Celery worker...
celery -A onematrix worker -l info -Q data_mining --without-heartbeat --without-gossip --without-mingle
