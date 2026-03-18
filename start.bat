@echo off
setlocal ENABLEDELAYEDEXPANSION

TITLE SIMCO - Lancement
COLOR 0A
echo ========================================
echo   SIMCO - Lancement Rapide
echo ========================================
echo.

:: Vérifier si l'environnement virtuel existe
if not exist venv (
    echo [ERREUR] L'environnement virtuel n'existe pas.
    echo Exécutez d'abord: install_full.bat
    pause
    exit /b 1
)

:: Vérifier si Ollama est en cours d'exécution
echo [1/3] Vérification d'Ollama...
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [ATTENTION] Ollama n'est pas en cours d'exécution.
    echo Lancement d'Ollama en arrière-plan...
    start /B ollama serve
    timeout /t 3 >nul
)

:: Lancer le backend
echo [2/3] Lancement du backend...
start /B cmd /k "cd /d %~dp0 && venv\Scripts\activate && python -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload"

:: Attendre que le backend soit prêt
echo [INFO] Attente du démarrage du backend...
timeout /t 5 >nul

:: Lancer le frontend
echo [3/3] Lancement du frontend...
cd quiz-frontend
start /B cmd /k "npm run dev"

echo.
echo ========================================
echo   SIMCO est en cours de lancement
echo ========================================
echo   Frontend: http://localhost:5173
echo   Backend API: http://127.0.0.1:8080
echo   Documentation: http://127.0.0.1:8080/docs
echo ========================================
echo.
echo Appuyez sur une touche pour fermer cette fenêtre...
pause >nul
