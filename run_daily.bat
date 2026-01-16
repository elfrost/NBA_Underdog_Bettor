@echo off
REM NBA Underdog Bet - Daily Analysis Script
REM Run this via Windows Task Scheduler

echo ========================================
echo NBA Underdog Bet - Daily Analysis
echo %date% %time%
echo ========================================

cd /d "c:\Users\racer\OneDrive\ai-project-starter\projects\NBA_Underdog_Bet"

REM Create logs folder if not exists
if not exist "logs" mkdir logs

REM Activate venv
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo No venv found, using system Python...
)

REM Run analysis
echo Running analysis...
python main.py

echo.
echo ========================================
echo Done! Press any key to close...
pause >nul
