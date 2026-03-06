# Project Structure

## Overview
```
simco/
├── backend/                    # Python FastAPI Backend
├── frontend/                   # React Frontend (renamed from quiz-frontend)
├── docs/                      # Documentation
├── .gitignore                 # Git ignore rules
├── README.md                  # Project overview
└── docker-compose.yml         # Container orchestration (future)
```

## Backend Structure

```
backend/
├── api/                       # API Layer
│   ├── __init__.py
│   ├── routes/               # Endpoint definitions
│   │   ├── __init__.py
│   │   ├── quiz.py          # Quiz endpoints
│   │   ├── analysis.py      # Behavioral analysis endpoints
│   │   └── health.py        # Health check
│   └── dependencies.py       # Shared dependencies
│
├── core/                      # Business Logic
│   ├── __init__.py
│   ├── quiz_generator.py    # Question generation
│   ├── session_manager.py   # Session handling
│   ├── behavioral_analyzer.py # Behavioral analysis logic
│   └── result_processor.py  # Results calculation
│
├── ml/                        # Machine Learning
│   ├── __init__.py
│   ├── data_collector.py    # Training data collection
│   ├── model_trainer.py     # Model training pipeline
│   ├── train.py             # Training entry point
│   └── predictor.py         # ML inference
│
├── models/                    # Pydantic Models
│   ├── __init__.py
│   ├── quiz.py              # Quiz-related models
│   ├── session.py           # Session models
│   └── behavioral.py        # Behavioral data models
│
├── config/                    # Configuration
│   ├── __init__.py
│   └── settings.py          # App settings
│
├── data/                      # Data Storage
│   ├── training/            # Training data
│   │   ├── sessions.jsonl   # Raw sessions
│   │   └── features.csv     # Feature matrix
│   └── models/              # Trained ML models
│       ├── stress_classifier.pkl
│       ├── attention_classifier.pkl
│       └── confidence_regressor.pkl
│
├── tests/                     # Backend tests
│   ├── __init__.py
│   ├── test_quiz.py
│   └── test_analysis.py
│
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── requirements_ml.txt        # ML dependencies
└── .env.example              # Environment template
```

## Frontend Structure

```
frontend/
├── src/
│   ├── components/           # React Components
│   │   ├── quiz/            # Quiz-related components
│   │   │   ├── QuizPage.jsx
│   │   │   ├── QuizInterface.jsx
│   │   │   └── ResultsPage.jsx
│   │   ├── behavioral/      # Behavioral tracking
│   │   │   └── WebcamAnalyzer.jsx
│   │   ├── common/          # Shared components
│   │   │   ├── Button.jsx
│   │   │   ├── LoadingSpinner.jsx
│   │   │   └── ProgressBar.jsx
│   │   └── landing/
│   │       └── LandingPage.jsx
│   │
│   ├── services/             # API Services
│   │   ├── api.js           # Base API client
│   │   ├── quizService.js   # Quiz API calls
│   │   └── behavioralService.js
│   │
│   ├── hooks/                # Custom React Hooks
│   │   ├── useWebcam.js
│   │   ├── useQuiz.js
│   │   └── useTimer.js
│   │
│   ├── utils/                # Utilities
│   │   ├── mediapipe.js     # MediaPipe helpers
│   │   ├── validation.js
│   │   └── constants.js
│   │
│   ├── styles/               # Global styles
│   │   └── index.css
│   │
│   ├── assets/               # Static assets
│   │   └── images/
│   │
│   ├── App.jsx               # Root component
│   └── main.jsx              # Entry point
│
├── public/                    # Public assets
├── tests/                     # Frontend tests
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
└── .env.example
```

## Documentation

```
docs/
├── api/                      # API documentation
│   ├── endpoints.md         # Endpoint reference
│   └── models.md            # Data models
│
├── architecture/             # Architecture docs
│   ├── overview.md
│   ├── backend.md
│   └── frontend.md
│
├── guides/                   # User guides
│   ├── SETUP.md            # Setup instructions
│   ├── TRAINING_GUIDE.md   # ML training guide
│   └── DEPLOYMENT.md       # Deployment guide
│
└── research/                 # Research documentation
    ├── behavioral_metrics.md
    └── metacognition.md
```

## Key Design Principles

### Backend
1. **Separation of Concerns**: API, business logic, and data layers separated
2. **Dependency Injection**: FastAPI's dependency system for testability
3. **Type Safety**: Pydantic models for validation
4. **Async/Await**: Non-blocking I/O operations
5. **Error Handling**: Centralized exception handling

### Frontend
1. **Component-Based**: Reusable, composable components
2. **State Management**: React hooks for local state
3. **Service Layer**: Separated API calls from components
4. **Responsive Design**: Mobile-first with Tailwind
5. **Performance**: Code splitting, lazy loading

### ML Pipeline
1. **Automated Collection**: Passive data gathering
2. **Feature Engineering**: Domain-specific features
3. **Model Versioning**: Track model performance over time
4. **Graceful Fallback**: Rule-based when models unavailable
5. **Continuous Learning**: Regular retraining

## File Naming Conventions

### Backend (Python)
- `snake_case.py` for modules
- `PascalCase` for classes
- `snake_case` for functions
- `UPPER_CASE` for constants

### Frontend (JavaScript)
- `PascalCase.jsx` for components
- `camelCase.js` for utilities
- `kebab-case.css` for styles

## Environment Variables

### Backend (.env)
```
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=mistral
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
DEBUG=true
ML_MODELS_PATH=data/models
TRAINING_DATA_PATH=data/training
```

### Frontend (.env)
```
VITE_API_BASE_URL=http://localhost:8000
VITE_ENABLE_WEBCAM=true
VITE_MEDIAPIPE_MODEL_PATH=/models/face_landmarker.task
```

## Version Control

### Git Ignore
- Python: `__pycache__/`, `*.pyc`, `venv/`, `.env`
- Node: `node_modules/`, `dist/`, `.env.local`
- Data: `data/training/*.jsonl`, `data/models/*.pkl`
- IDE: `.vscode/`, `.idea/`, `*.swp`

## Next Steps for Migration

1. ✅ Create directory structure
2. ✅ Move existing files to new structure
3. ✅ Update import paths
4. ✅ Create configuration files
5. ✅ Add environment templates
6. ✅ Update documentation
7. ✅ Test everything works
