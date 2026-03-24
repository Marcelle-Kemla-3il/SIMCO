@echo off
setlocal

REM Resolve repository root from this script location
set "ROOT=%~dp0..\.."
cd /d "%ROOT%"

REM Move to SIMCO Logic project folder
cd /d "%ROOT%\services\confidence_backend"

REM Start SIMCO Logic API
"%ROOT%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8010

REM Wait for user input to close
pause
