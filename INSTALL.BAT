@echo off
REM ===========================================================================
REM  IntentPay - installer only (use RUN.BAT to start the app afterwards)
REM ===========================================================================
setlocal EnableDelayedExpansion
cd /d %~dp0
title IntentPay - install

set "PY_CMD="
where py >nul 2>nul
if %errorlevel%==0 ( set "PY_CMD=py -3" ) else ( where python >nul 2>nul && set "PY_CMD=python" )

if "%PY_CMD%"=="" (
    echo [ERROR] Python not found. Install Python 3.10+ from python.org and retry.
    pause
    exit /b 1
)

echo Creating virtual environment...
if not exist ".venv\" %PY_CMD% -m venv .venv
call .venv\Scripts\activate.bat

echo Installing core dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install -r REQUIREMENTS.TXT --quiet || python -m pip install -r REQUIREMENTS.TXT
if errorlevel 1 (
    echo [ERROR] core install failed
    pause
    exit /b 1
)

echo Installing optional voice packages (failures are harmless)...
if exist "REQUIREMENTS_VOICE.TXT" python -m pip install -r REQUIREMENTS_VOICE.TXT --quiet

if not exist ".env" if exist "ENV_EXAMPLE.TXT" copy /y "ENV_EXAMPLE.TXT" ".env" >nul

echo.
echo Install complete. Run RUN.BAT to start IntentPay.
pause
endlocal
