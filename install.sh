#!/bin/bash

echo "========================================"
echo "   SIMCO - Installation Automatisée"
echo "========================================"
echo

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "[ERREUR] Python n'est pas installé"
    echo "Veuillez installer Python 3.10+ depuis https://www.python.org/downloads/"
    exit 1
fi

echo "[OK] Python est installé"

# Vérifier Git
if ! command -v git &> /dev/null; then
    echo "[ERREUR] Git n'est pas installé"
    echo "Veuillez installer Git"
    exit 1
fi

echo "[OK] Git est installé"

# Créer l'environnement virtuel
echo
echo "[1/4] Création de l'environnement virtuel..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "[ERREUR] Erreur lors de la création de l'environnement virtuel"
    exit 1
fi

# Activer l'environnement
echo "[2/4] Activation de l'environnement virtuel..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "[ERREUR] Erreur lors de l'activation de l'environnement"
    exit 1
fi

# Installer les dépendances
echo "[3/4] Installation des dépendances..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERREUR] Erreur lors de l'installation des dépendances"
    exit 1
fi

# Configuration
echo "[4/4] Configuration initiale..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[OK] Fichier .env créé à partir de .env.example"
        echo
        echo "========================================"
        echo "    CONFIGURATION REQUISE"
        echo "========================================"
        echo
        echo "Éditez le fichier .env pour configurer:"
        echo "- Votre LLM (Ollama recommandé)"
        echo "- Vos clés API (OpenAI/Mistral)"
        echo "- La configuration de la base de données"
        echo
    else
        echo "[ATTENTION] Fichier .env.example non trouvé"
        echo "Création d'un fichier .env minimal..."
        cat > .env << EOF
DATABASE_URL=sqlite:///./simco.db
LLM_PROVIDER=ollama
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=phi3:mini
MEDIAPIPE_ENABLED=false
EOF
    fi
else
    echo "[OK] Fichier .env déjà existant"
fi

# Vérifier Ollama
echo
echo "Vérification de Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "[ATTENTION] Ollama n'est pas installé"
    echo
    echo "Pour installer Ollama:"
    echo "1. Téléchargez depuis https://ollama.ai/download"
    echo "2. Installez le modèle: ollama pull phi3:mini"
    echo
    echo "Vous pouvez aussi utiliser OpenAI ou Mistral en modifiant .env"
else
    echo "[OK] Ollama est installé"
    if ! ollama list | grep -q "phi3:mini"; then
        echo "[ATTENTION] phi3:mini n'est pas installé"
        echo "Installation: ollama pull phi3:mini"
    else
        echo "[OK] phi3:mini est disponible"
    fi
fi

echo
echo "========================================"
echo "    INSTALLATION TERMINÉE !"
echo "========================================"
echo
echo "Pour lancer le serveur:"
echo "  1. Activez l'environnement: source venv/bin/activate"
echo "  2. Lancez le serveur: uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
echo
echo "Accès:"
echo "  - Interface: http://127.0.0.1:8000/demo"
echo "  - API Docs: http://127.0.0.1:8000/docs"
echo
echo "N'oubliez pas de configurer votre fichier .env !"
echo

# Rendre le script exécutable
chmod +x install.sh 2>/dev/null || true
