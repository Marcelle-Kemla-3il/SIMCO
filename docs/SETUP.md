# Setup Guide

## Prerequisites

### Required Software
- **Python 3.9+**: [Download](https://www.python.org/downloads/)
- **Node.js 18+**: [Download](https://nodejs.org/)
- **Ollama**: [Download](https://ollama.com/download)

### Ollama Setup
```bash
# Install Ollama, then pull the Mistral model
ollama pull mistral

# Verify it's running
ollama list
```

## Backend Setup

### 1. Navigate to backend folder
```bash
cd backend
```

### 2. Create virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt

# Optional: For ML training
pip install -r requirements_ml.txt
```

### 4. Configure environment
```bash
# Copy example environment file
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Edit .env if needed (default values should work)
```

### 5. Run the backend
```bash
python -m uvicorn main:app --reload
```

Backend will be available at: **http://localhost:8000**

API documentation: **http://localhost:8000/docs**

## Frontend Setup

### 1. Navigate to frontend folder
```bash
cd frontend
```

### 2. Install dependencies
```bash
npm install
```

### 3. Configure environment (optional)
```bash
# Copy example if you have one
# copy .env.example .env
```

### 4. Run the frontend
```bash
npm run dev
```

Frontend will be available at: **http://localhost:5173**

## Verification

### Test Backend
```bash
# Check health endpoint
curl http://localhost:8000/health

# Or visit in browser
http://localhost:8000/docs
```

### Test Ollama
```bash
# Verify Mistral is working
ollama run mistral "Hello, test message"
```

### Test Frontend
Open http://localhost:5173 in your browser. You should see the landing page.

## Quick Start Scripts

### Windows
```batch
# Start backend
cd backend
venv\Scripts\activate
python -m uvicorn main:app --reload

# Start frontend (in new terminal)
cd frontend
npm run dev
```

### Linux/Mac
```bash
# Start backend
cd backend
source venv/bin/activate
python -m uvicorn main:app --reload

# Start frontend (in new terminal)
cd frontend
npm run dev
```

## Common Issues

### Ollama not running
```bash
# Check if Ollama service is running
# Windows: Check Task Manager
# Linux/Mac: ps aux | grep ollama

# Restart Ollama if needed
```

### Port already in use
```bash
# Backend (8000)
lsof -ti:8000 | xargs kill -9  # Linux/Mac
netstat -ano | findstr :8000   # Windows

# Frontend (5173)
lsof -ti:5173 | xargs kill -9  # Linux/Mac
netstat -ano | findstr :5173   # Windows
```

### Python dependencies error
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Node modules error
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

## Next Steps

After successful setup:

1. ✅ Test quiz generation at http://localhost:5173
2. ✅ Complete a few quiz sessions to collect data
3. ✅ Check `backend/data/training/` for collected data
4. ✅ Train ML models (see [TRAINING_GUIDE.md](TRAINING_GUIDE.md))
5. ✅ Review behavioral analysis in quiz results

## Development Mode

Both services run in development mode with:
- **Hot reload**: Changes automatically restart servers
- **Debug logging**: Detailed console output
- **CORS enabled**: Frontend can call backend API

## Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for production configuration.
