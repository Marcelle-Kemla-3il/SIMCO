# SIMCO — Système Intelligent Multimodal d'Évaluation Cognitive

> Projet I2 — 3iL Ingénieurs | Janvier – Mars 2026  
> Équipe : Marcelle · Luccin · Jordan · Mexes · Kevin · André  
> Supervision : Jesus Franco Robles & Arnaud Boujut

---

## Présentation

SIMCO est une plateforme pédagogique intelligente qui va au-delà de la simple notation. Elle analyse simultanément la performance réelle d'un étudiant, sa confiance déclarée et ses expressions faciales pour détecter les biais d'autoévaluation cognitifs (effet Dunning-Kruger, syndrome de l'imposteur).

---

## Fonctionnalités principales

- **Génération automatique de quiz** via LLM local (Ollama + Mistral)
- **Analyse faciale en temps réel** via DeepFace (7 émotions par photo)
- **Collecte automatique du dataset** (sessions.jsonl)
- **Modèle Random Forest** entraîné sur données réelles — 91% de précision en cross-validation
- **9 diagnostics cognitifs** basés sur la courbe de Dunning-Kruger
- **Courbe DK interactive** avec 3 points (D = déclaré, R = réel, O = observé)
- **Rapport PDF personnalisé** + envoi automatique par email (Gmail SMTP)
- **Interface moderne** React + Vite + TailwindCSS

---

## Architecture

```
SIMCO/
├── backend/
│   ├── main.py                  ← API principale + routes
│   ├── config/
│   │   └── settings.py          ← configuration Pydantic
│   ├── core/
│   │   ├── cv_service.py        ← DeepFace + pipeline émotions
│   │   ├── notion_service.py    ← analyse notions via Ollama
│   │   ├── report_service.py    ← génération PDF (ReportLab)
│   │   └── email_service.py     ← envoi Gmail SMTP
│   ├── ml/
│   │   ├── data_collector.py    ← collecte sessions.jsonl
│   │   └── model_trainer.py     ← entraînement Random Forest
│   ├── data/
│   │   ├── training/
│   │   │   └── sessions.jsonl   ← dataset (non versionné)
│   │   └── models/
│   │       ├── dk_classifier.pkl ← modèle entraîné
│   │       └── label_encoder.pkl
│   ├── requirements.txt
│   └── .env.example
│
└── quiz-frontend/
    └── src/
        ├── components/
        │   ├── QuizPage.jsx           ← flux complet quiz
        │   ├── QuizInterfacePage.jsx  ← interface quiz + webcam
        │   └── DunningKrugerChart.jsx ← courbe DK interactive
        └── hooks/
            └── usePhotoCapture.js     ← capture photos webcam
```

---

## Technologies utilisées

| Catégorie | Technologie |
|-----------|-------------|
| LLM local | Ollama + Mistral |
| Vision IA | DeepFace |
| ML | scikit-learn (Random Forest) |
| Backend | FastAPI + Python 3.10 |
| Frontend | React + Vite + TailwindCSS |
| Rapport | ReportLab |
| Email | Gmail SMTP |

---

## Installation et lancement

### Prérequis

- Python 3.10+
- Node.js 18+
- Ollama installé avec le modèle Mistral

```bash
ollama pull mistral
```

### Configuration email

```bash
# Copier le fichier exemple
cp backend/.env.example backend/.env

# Remplir avec vos credentials Gmail
# GMAIL_ADDRESS=votre.adresse@gmail.com
# GMAIL_PASSWORD=xxxx xxxx xxxx xxxx
```

> Le mot de passe d'application se génère sur [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

### Lancement

```bash
# Terminal 1 — Ollama
ollama serve

# Terminal 2 — Backend
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload

# Terminal 3 — Frontend
cd quiz-frontend
npm install
npm run dev
```

Accès : [http://localhost:5173](http://localhost:5173)

---

## Entraîner le modèle ML

```bash
cd backend
python -m ml.model_trainer
```

Résultats obtenus :
- Accuracy test : **100%**
- Cross-validation 5-fold : **91% ± 11%**

---

## Routes API principales

| Méthode | Route | Description |
|---------|-------|-------------|
| POST | `/generate-quiz` | Génération des questions via Ollama |
| POST | `/submit-answer` | Soumission d'une réponse |
| POST | `/update-confidence` | Enregistrement du slider de confiance |
| GET | `/quiz-results/{id}` | Résultats complets de la session |
| POST | `/session/{id}/photo` | Envoi photo webcam pour analyse |
| GET | `/analyze-notions/{id}` | Analyse des notions via Ollama |
| GET | `/generate-report/{id}` | Génération rapport PDF |
| POST | `/send-report` | Envoi du rapport par email |

---

## Les 9 diagnostics cognitifs

| Zone | Score | DK Index | Profil |
|------|-------|----------|--------|
| ⚠️ Pic Dunning-Kruger | < 40% | > +20 | Surestime ses connaissances |
| 📚 Incompétence Consciente | < 40% | < -20 | Sait qu'il a des lacunes |
| 🌱 Débutant Calibré | < 40% | ≈ 0 | Réaliste sur son niveau |
| 😓 Vallée du Désespoir | 40-70% | > +20 | Se décourage |
| 💪 Syndrome de l'Imposteur | 40-70% | < -20 | Sous-estime ses compétences |
| 📈 Pente de l'Illumination | 40-70% | ≈ 0 | Bonne progression |
| ⚠️ Expert Surconfiant | > 70% | > +15 | Légère surconfiance |
| 🏅 Expert Humble | > 70% | < -15 | Expert qui se sous-estime |
| 🎯 Expert Calibré | > 70% | ≈ 0 | Profil idéal |

---

## Licence

MIT
