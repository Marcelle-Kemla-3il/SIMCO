@echo off
setlocal ENABLEDELAYEDEXPANSION

:: ========================================
::  SIMCO - Installation complete et lancement (Windows)
::  Objectif: Recréer un environnement propre sur une nouvelle machine
::            et démarrer le serveur, avec des reprises automatiques.
:: ========================================

TITLE SIMCO - Installation et Lancement
COLOR 0A
echo ========================================
echo   SIMCO - Installation Automatique Complete
echo ========================================
echo.

:: 0) Aller a la racine du projet (suppose que ce script est a la racine)
pushd %~dp0

:: 1) Vérifier Git
git --version >nul 2>&1
if errorlevel 1 (
  echo [ERREUR] Git n'est pas installe. Installez-le: https://git-scm.com/download/win
  pause
  exit /b 1
) else (
  for /f "tokens=3" %%v in ('git --version') do set GIT_VER=%%v
  echo [OK] Git detecte - version %GIT_VER%
)

:: 2) Détecter Python (py -3 en priorité, sinon python)
set PY_EXE=
where py >nul 2>&1
if not errorlevel 1 (
  for /f "usebackq tokens=*" %%p in (`py -3 -c "import sys;print(sys.executable)"`) do set PY_EXE=%%p
)
if "%PY_EXE%"=="" (
  where python >nul 2>&1
  if errorlevel 1 (
    echo [ERREUR] Python 3.x introuvable. Installez Python 3.10+ depuis https://www.python.org/downloads/
    pause
    exit /b 1
  ) else (
    for /f "usebackq tokens=*" %%p in (`python -c "import sys;print(sys.executable)"`) do set PY_EXE=%%p
  )
)
echo [OK] Python: %PY_EXE%

:: 3) Nettoyage optionnel de l'environnement existant
if exist venv (
  echo [INFO] Un environnement virtuel existe deja.
  choice /M "Voulez-vous le RECREER proprement (recommande sur nouvel ordi)?"
  if errorlevel 2 (
    echo [INFO] Conservation de venv existant.
  ) else (
    echo [INFO] Suppression de venv...
    rmdir /s /q venv
  )
)

:: 4) Creer le venv
echo [1/6] Creation de l'environnement virtuel...
"%PY_EXE%" -m venv venv
if errorlevel 1 (
  echo [ERREUR] Echec creation venv
  pause
  exit /b 1
)

:: 5) Mettre pip/setuptools/wheel a jour + purge cache
echo [2/6] Mise a jour outils de build et purge cache pip...
call venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
call venv\Scripts\python.exe -m pip cache purge >nul 2>&1

:: 6) Preparer le .env minimal si absent
echo [3/6] Configuration .env...
if not exist .env (
  echo DATABASE_URL=sqlite:///./simco.db> .env
  echo LLM_PROVIDER=ollama>> .env
  echo OLLAMA_URL=http://127.0.0.1:11434>> .env
  echo OLLAMA_MODEL=mistral>> .env
  echo MEDIAPIPE_ENABLED=false>> .env
  echo [OK] Fichier .env cree (minimal). Ajustez-le si besoin.
) else (
  echo [OK] .env deja present.
)

:: 7) Installer les dependances (avec reprises et forced reinstall si necessaire)
echo [4/6] Installation des dependances (requirements.txt)...
set RETRIES=2
:install_loop
call venv\Scripts\python.exe -m pip install --upgrade --force-reinstall -r requirements.txt
if errorlevel 1 (
  if %RETRIES% GTR 0 (
    echo [ATTENTION] Echec install. Tentative de correctifs (pins clefs) puis nouvelle tentative...
    call venv\Scripts\python.exe -m pip install --upgrade --force-reinstall "protobuf==3.20.3" "mediapipe==0.10.7" "opencv-python==4.8.1.78"
    set /a RETRIES-=1
    goto install_loop
  ) else (
    echo [ERREUR] Echec installation dependances apres plusieurs tentatives.
    pause
    exit /b 1
  )
) else (
  echo [OK] Dependances installees.
)

:: 8) Initialiser la base de donnees
echo [5/6] Initialisation de la base de donnees...
call venv\Scripts\python.exe -m app.core.init_db
if errorlevel 1 (
  echo [ERREUR] Echec creation des tables.
  pause
  exit /b 1
)

:: 9) Lancer le serveur
echo [6/6] Lancement du serveur Uvicorn...
echo   URL API:   http://127.0.0.1:8000
echo   Docs:      http://127.0.0.1:8000/docs
echo   Demo:      http://127.0.0.1:8000/demo

:: Option pour rebind si le port 8000 est occupe: changer --port 8080
call venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
if errorlevel 1 (
  echo [ATTENTION] Echec au lancement sur 8000. Tentative sur 8080...
  call venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
)

popd
endlocal

:: Fin
exit /b 0
