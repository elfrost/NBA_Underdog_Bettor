@echo off
REM NBA Underdog Bet - Scheduled Task (no pause, logs to file)
REM Use this for Windows Task Scheduler

cd /d "c:\Users\racer\OneDrive\ai-project-starter\projects\NBA_Underdog_Bet"

REM Create logs folder if not exists
if not exist "logs" mkdir logs

REM Set log file name with date
set LOGFILE=logs\daily_%date:~-4,4%-%date:~-10,2%-%date:~-7,2%.log

echo ======================================== >> %LOGFILE%
echo NBA Underdog Bet - %date% %time% >> %LOGFILE%
echo ======================================== >> %LOGFILE%

REM Activate venv
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Run analysis and log output
python main.py >> %LOGFILE% 2>&1

echo. >> %LOGFILE%
echo Completed at %time% >> %LOGFILE%
