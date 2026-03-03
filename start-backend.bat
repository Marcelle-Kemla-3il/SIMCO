@echo off
echo Starting SIMCO Quiz Backend...
cd backend
python -m uvicorn main:app --reload
pause
