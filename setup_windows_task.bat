@echo off
setlocal
echo =================================================================
echo   AUTOJOBS AGENT - WINDOWS 09:00 AM TASK SCHEDULER SETUP
echo =================================================================

set "TASK_NAME=AutoJobsDailyAgent"
set "BAT_PATH=%~dp0run_agent.bat"

echo Registering daily 09:00 AM task '%TASK_NAME%'...
schtasks /create /tn "%TASK_NAME%" /tr "\"%BAT_PATH%\"" /sc daily /st 09:00 /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] Windows Scheduled Task '%TASK_NAME%' successfully created!
    echo The agent will run automatically every day at 09:00 AM.
) else (
    echo.
    echo [ERROR] Failed to register scheduled task. If permission denied, please run this script as Administrator.
)

echo.
pause
endlocal
