@echo off
setlocal

set "ROOT=%~dp0..\.."
cd /d "%ROOT%"

"%ROOT%\.venv\Scripts\python.exe" -m uvicorn services.notification_backend.app.main:app --host 127.0.0.1 --port 8020 --reload

pause
