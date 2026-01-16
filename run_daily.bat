@echo off
cd /d "c:\Users\racer\OneDrive\ai-project-starter\projects\NBA_Underdog_Bet"
if not exist "logs" mkdir logs
if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat
python main.py
