# SIMCO

SIMCO (Système Intelligent Multimodal d'Évaluation Cognitive) est une plateforme d'évaluation cognitive avancée qui combine intelligence artificielle, analyse comportementale par webcam, et auto-évaluation de la confiance pour offrir une analyse complète des performances et de la métacognition.

## Fonctionnalités principales

- **Génération automatique de quiz** (IA Mistral via Ollama)
- **Analyse comportementale en temps réel** (détection du stress, attention, confiance via webcam)
- **Collecte de données pour l'entraînement de modèles ML personnalisés**
- **Interface utilisateur moderne et responsive** (React + TailwindCSS)
- **Résultats détaillés avec feedback personnalisé**
- **Pipeline de formation et calibration de modèles** (scikit-learn)

## Architecture

- **Backend** : FastAPI (Python), intégration IA (Ollama/Mistral), endpoints REST, pipeline ML
- **Frontend** : React (Vite), TailwindCSS, MediaPipe pour la détection faciale
- **ML/Training** : scikit-learn, pandas, joblib, scripts de migration et d'entraînement

## Démarrage rapide

### Avec Docker (recommandé)

```bash
# Lancer le setup automatique
./docker-setup.sh    # Linux/Mac
# ou
.\docker-setup.ps1   # Windows

# Les services seront disponibles sur :
# - Frontend: http://localhost:5173
# - Backend:  http://localhost:8000
# - Ollama:   http://localhost:11434
```

### Installation manuelle

#### Prérequis
- Python 3.10+
- Node.js 18+
- Ollama (pour Mistral)

#### Installation

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sous Windows
pip install -r requirements.txt

# Frontend
cd ../quiz-frontend
npm install
```

### Lancer le backend
```bash
cd backend
uvicorn main:app --reload
```

### Lancer le frontend
```bash
cd quiz-frontend
npm run dev
```

### Lancer Ollama avec Mistral
```bash
ollama run mistral
```

## Utilisation
- Accédez à l'interface sur [http://localhost:5173](http://localhost:5173)
- Lancez un quiz, autorisez la webcam, répondez aux questions
- À la fin, évaluez votre confiance globale
- Consultez les résultats détaillés et l'analyse comportementale

## Structure du projet

```
backend/
  main.py
  requirements.txt
  Dockerfile
  ...
quiz-frontend/
  src/
    components/
      QuizPage.jsx
      WebcamAnalyzer.jsx
      ...
  Dockerfile
  ...
docker-compose.yml
docker-setup.sh
docker-setup.ps1
```

## Données et entraînement ML
- Les données de session sont stockées dans `backend/data/training/sessions.jsonl`
- Les modèles entraînés sont dans `backend/data/models/`
- Scripts d'entraînement dans `backend/ml/`

## Auteurs
- Guy (MRGUY10)

## Licence
MIT
