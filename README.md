# SIMCO

**Système Intelligent Multimodal d'Évaluation Cognitive**

SIMCO est une plateforme d'évaluation cognitive avancée qui combine intelligence artificielle, analyse comportementale et auto-évaluation pour offrir une analyse complète des performances.

## 🚀 Démarrage rapide

### Prérequis
- Python 3.10+
- Node.js 18+
- Ollama (pour Mistral)

### Installation Windows
```bash
# Installation complète et lancement
install_full.bat
```

### Lancement manuel
```bash
# Backend
cd SIMCO
venv\Scripts\activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080

# Frontend (autre terminal)
cd quiz-frontend
npm run dev
```

## 🌐 Accès

- **Frontend**: http://localhost:5173
- **Backend API**: http://127.0.0.1:8080
- **Documentation API**: http://127.0.0.1:8080/docs

## 📋 Fonctionnalités

- **Génération automatique de quiz** (IA Mistral via Ollama)
- **Analyse comportementale** (webcam, détection de stress/attention)
- **Évaluation de la confiance** (métaconnaissance Dunning-Kruger)
- **Interface moderne** (React + TailwindCSS)
- **Résultats détaillés** avec feedback personnalisé

## 🏗️ Architecture

```
SIMCO/
├── app/                    # Backend FastAPI
│   ├── api/v1/            # Endpoints API
│   ├── core/               # Configuration, base de données
│   ├── models/             # Modèles SQLAlchemy
│   ├── services/           # Services (LLM, ML, vision)
│   └── schemas/            # Schémas Pydantic
├── quiz-frontend/          # Frontend React
│   ├── src/
│   │   ├── components/     # Composants React
│   │   └── pages/         # Pages principales
│   └── public/            # Fichiers statiques
├── venv/                  # Environnement Python
├── simco.db              # Base de données SQLite
├── requirements.txt        # Dépendances Python
└── .env                  # Configuration environnement
```

## ⚙️ Configuration

Variables d'environnement (`.env`):
```env
DATABASE_URL=sqlite:///./simco.db
LLM_PROVIDER=ollama
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=mistral
MEDIAPIPE_ENABLED=false

# Configuration email (optionnel)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=votre-email@gmail.com
SMTP_PASSWORD=votre-mot-de-passe-app
FROM_EMAIL=votre-email@gmail.com
```

### Configuration Email (Optionnel)

Pour activer l'envoi de rapports par email:

1. **Gmail**: Créez un mot de passe d'application
   - Allez dans [Paramètres Google](https://myaccount.google.com/security)
   - "Vérification en 2 étapes" > "Mots de passe d'application"
   - Générer un mot de passe pour "Mail"

2. **Variables d'environnement**:
   ```env
   SMTP_USERNAME=votre-email@gmail.com
   SMTP_PASSWORD=votre-mot-de-passe-app
   ```

3. **Sans configuration**: Les emails sont loggés dans la console (mode développement)

## 📊 Utilisation

1. **Accédez** à http://localhost:5173
2. **Remplissez** vos informations personnelles
3. **Choisissez** matière et niveau
4. **Lancez** un quiz en mode plein écran
5. **Répondez** aux 10 questions
6. **Évaluez** votre confiance globale
7. **Consultez** vos résultats détaillés

## 🤖 Ollama

Si Ollama n'est pas installé:
```bash
# Installation (Windows)
winget install Ollama.Ollama

# Lancement du service
ollama serve

# Installation du modèle
ollama pull mistral
```

## 🛠️ Développement

### Backend
```bash
cd SIMCO
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Frontend
```bash
cd quiz-frontend
npm install
npm run dev
```

## 📝 Licence

MIT License
