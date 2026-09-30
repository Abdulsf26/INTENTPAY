@echo off
REM ===========================================================================
REM  IntentPay - one-click setup and launch (NAS CODERS)
REM  Double-click this file. It installs everything and opens the app.
REM  Works on Windows 10/11 with Python 3.10+ (the "py" launcher is used if
REM  present, otherwise "python").
REM ===========================================================================
setlocal EnableDelayedExpansion
cd /d %~dp0
title IntentPay - setup and launch

echo.
echo ============================================================
echo   IntentPay ^| AI Payment Intent Guardian
echo   Team: NAS CODERS
echo ============================================================
echo.

REM --- locate a Python interpreter -------------------------------------------
set "PY_CMD="
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>nul
    if !errorlevel!==0 ( set "PY_CMD=python" )
)

if "%PY_CMD%"=="" (
    echo [ERROR] Python was not found on this computer.
    echo.
    echo   Install Python 3.10 or newer from https://www.python.org/downloads/
    echo   IMPORTANT: tick "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

%PY_CMD% --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] "%PY_CMD%" did not run. Please reinstall Python and retry.
    pause
    exit /b 1
)
echo [1/5] Python found:
%PY_CMD% --version

REM --- create the virtual environment -----------------------------------------
if not exist ".venv\" (
    echo [2/5] Creating virtual environment .venv ...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        echo         Try: py -3 -m pip install --upgrade virtualenv
        pause
        exit /b 1
    )
) else (
    echo [2/5] Virtual environment .venv already exists.
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Could not activate the virtual environment.
    pause
    exit /b 1
)

REM --- install dependencies ----------------------------------------------------
echo [3/5] Installing core dependencies ^(this can take a few minutes the first time^) ...
python -m pip install --upgrade pip --quiet
python -m pip install -r REQUIREMENTS.TXT --quiet
if errorlevel 1 (
    echo [WARN] Core install reported an error. Retrying once without --quiet ...
    python -m pip install -r REQUIREMENTS.TXT
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed.
        echo         Check your internet connection and try again.
        pause
        exit /b 1
    )
)

REM --- optional voice dependencies (never fatal) ------------------------------
if exist "REQUIREMENTS_VOICE.TXT" (
    echo [4/5] Installing optional voice packages ^(failures here are harmless^) ...
    python -m pip install -r REQUIREMENTS_VOICE.TXT --quiet
    if errorlevel 1 echo [INFO] Voice packages could not be installed - typing still works.
) else (
    echo [4/5] No optional voice packages file found - skipping.
)

REM --- environment file ---------------------------------------------------------
if not exist ".env" (
    if exist "ENV_EXAMPLE.TXT" (
        copy /y "ENV_EXAMPLE.TXT" ".env" >nul
        echo [5/5] Created .env from ENV_EXAMPLE.TXT
    )
) else (
    echo [5/5] .env already present.
)

echo.
echo ============================================================
echo   Starting IntentPay at  http://127.0.0.1:8501
echo   Your browser should open automatically.
echo   Close this window (or press Ctrl+C) to stop the app.
echo ============================================================
echo.

REM give Streamlit a moment to bind the port before the browser opens
timeout /t 6 /nobreak >nul
start "" http://127.0.0.1:8501
python -m streamlit run APP.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false

if errorlevel 1 (
    echo.
    echo [ERROR] The app stopped with an error. Scroll up to see the message.
    echo         Common fixes: run this file again, or delete the .venv folder first.
)
pause
endlocal
