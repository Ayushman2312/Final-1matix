@echo off
echo Starting Redis Server...
cd /d %USERPROFILE%\Redis
start /b redis-server.exe redis.windows.conf
echo Redis server started on localhost:6379
echo Press any key to exit...
pause > nul 