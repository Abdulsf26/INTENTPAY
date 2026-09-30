@echo off
REM ===========================================================================
REM  IntentPay - launch only (assumes INSTALL.BAT / START_HERE.BAT already ran)
REM ===========================================================================
setlocal
cd /d %~dp0
title IntentPay

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Please run START_HERE.BAT first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo Starting IntentPay at http://127.0.0.1:8501 ...
REM give Streamlit a moment to bind the port before the browser opens
timeout /t 6 /nobreak >nul
start "" http://127.0.0.1:8501
python -m streamlit run APP.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
if errorlevel 1 echo [ERROR] the app stopped with an error - see the message above.
pause
endlocal
