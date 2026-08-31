@echo off
setlocal
echo ===================================================
echo   AUTOJOBS AUTONOMOUS AGENT - 09:00 AM DAILY RUNNER  
echo ===================================================

cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" main.py
) else (
    python main.py
)

echo.
echo Launching AutoJobs Talent Copilot Dashboard...
start http://localhost:8000/dashboard/

echo.
echo Daily sequence finished at %date% %time%.
echo ===================================================
endlocal
