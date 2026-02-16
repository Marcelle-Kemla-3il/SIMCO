@echo off
echo Starting SIMCO Server...
echo Demo page: http://127.0.0.1:8000/demo
echo API docs: http://127.0.0.1:8000/docs
echo.
cd /d "C:\Fastapi\SIMCO"
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found in PATH. Please install Python from python.org
    echo Or use: py start_server.py
    pause
    exit /b 1
)
python start_server.py
if %errorlevel% neq 0 (
    echo Python command failed, trying py launcher...
    py start_server.py
)
pause
