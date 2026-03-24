@echo off
setlocal

REM Resolve repository root from this script location
set "ROOT=%~dp0..\.."
cd /d "%ROOT%"

echo Starting SIMCO Quiz Frontend...
cd /d "%ROOT%\quiz-frontend"
npm run dev
pause
