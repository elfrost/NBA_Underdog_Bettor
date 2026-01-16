@echo off
REM NBA Underdog Bet - Daily Analysis Script
REM Run this via Windows Task Scheduler

cd /d "c:\Users\racer\OneDrive\ai-project-starter\projects\NBA_Underdog_Bet"

REM Activate venv if exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Run analysis
python main.py >> logs\daily_%date:~-4,4%%date:~-10,2%%date:~-7,2%.log 2>&1

REM Deactivate
if exist ".venv\Scripts\deactivate.bat" (
    call deactivate
)
