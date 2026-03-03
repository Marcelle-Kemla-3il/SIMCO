# Quiz Application - API Integration Guide

## Overview
The frontend is now connected to the backend API for dynamic quiz generation and scoring.

## Backend API Endpoints

### 1. Generate Single Question
**POST** `/generate-question`
```json
{
  "subject": "mathématiques",
  "level": "lycée",
  "user_info": "Optional user information"
}
```
**Response:**
```json
{
  "session_id": "uuid",
  "question_id": "uuid",
  "question": "Question text",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "explanation": "Answer explanation"
}
```

### 2. Submit Answer
**POST** `/submit-answer`
```json
{
  "session_id": "uuid",
  "question_id": "uuid",
  "selected_answer": 0  // 0-3 for A-D
}
```
**Response:**
```json
{
  "correct": true,
  "correct_answer": 0,
  "explanation": "Why this is correct",
  "score": 1,
  "total_questions": 1
}
```

### 3. Get Quiz Score
**GET** `/quiz-score/{session_id}`

**Response:**
```json
{
  "session_id": "uuid",
  "score": 5,
  "total_questions": 10,
  "percentage": 50.0,
  "answered": 5
}
```

### 4. Generate Complete Quiz
**POST** `/generate-quiz?num_questions=5`
```json
{
  "subject": "histoire",
  "level": "collège",
  "user_info": ""
}
```
**Response:**
```json
{
  "session_id": "uuid",
  "questions": [
    {
      "id": "uuid",
      "question": "Question text",
      "options": ["A", "B", "C", "D"]
    }
  ],
  "total_questions": 5
}
```

## Frontend Changes

### QuizPage.jsx
- Added `API_BASE_URL` constant: `http://localhost:8000`
- Added state for `sessionId`, `questionId`, `error`, and `result`
- Updated `startTest()` to fetch questions from backend
- Updated `submitAnswer()` to send answers to backend and display results
- Added loading states and error handling

### QuizInterfacePage.jsx
- Changed prop from `staticQuestion` to `question`
- Added `loading` prop for submit button state
- Updated all references to use dynamic question data

## Running the Application

### 1. Start Backend
```bash
cd backend
python -m uvicorn main:app --reload
```
Backend runs on: http://localhost:8000

### 2. Start Frontend
```bash
cd quiz-frontend
npm run dev
```
Frontend runs on: http://localhost:5173

## Features Implemented

✅ Dynamic question generation from AI (Ollama/Mistral)
✅ Multiple choice questions with 4 options
✅ Answer submission and validation
✅ Real-time scoring
✅ Session management
✅ Personalized questions based on:
   - Subject (mathématiques, physique, histoire, etc.)
   - Level (collège, lycée, université)
   - User information (strengths, weaknesses)

## Flow

1. User fills out personal information
2. User selects subject and level preferences
3. User reads instructions
4. Frontend calls `/generate-question` endpoint
5. Backend generates question using AI
6. User answers and sets confidence level
7. Frontend calls `/submit-answer` endpoint
8. Backend validates answer and returns result
9. Display score and feedback to user

## CORS Configuration
The backend needs CORS enabled for the frontend. Add to `main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
