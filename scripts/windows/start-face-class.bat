@echo off
setlocal

REM Resolve repository root from this script location
set "ROOT=%~dp0..\.."
cd /d "%ROOT%"

REM Start face classification API
if exist "%ROOT%\services\face_backend\.venv310\Scripts\python.exe" (
	"%ROOT%\services\face_backend\.venv310\Scripts\python.exe" -m uvicorn services.face_backend.src.web.faces:app --host 127.0.0.1 --port 8084
) else if exist "%ROOT%\services\face_backend\.venv\Scripts\python.exe" (
	"%ROOT%\services\face_backend\.venv\Scripts\python.exe" -m uvicorn services.face_backend.src.web.faces:app --host 127.0.0.1 --port 8084
) else (
	"%ROOT%\.venv\Scripts\python.exe" -m uvicorn services.face_backend.src.web.faces:app --host 127.0.0.1 --port 8084
)