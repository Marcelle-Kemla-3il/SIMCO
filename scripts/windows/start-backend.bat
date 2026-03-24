@echo off
setlocal

REM Resolve repository root from this script location
set "ROOT=%~dp0..\.."
cd /d "%ROOT%"

REM Start backend server
"%ROOT%\.venv\Scripts\python.exe" -m uvicorn services.quiz_backend.main:app --host 127.0.0.1 --port 8000

REM Wait for user input to close
pause
