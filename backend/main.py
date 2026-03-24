from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import requests
import json
import re
from uuid import uuid4
from pathlib import Path

# Import from organized modules
from config import settings
from ml import DataCollector, BehavioralModelTrainer

# Initialize data collector
data_collector = DataCollector(data_dir=settings.TRAINING_DATA_PATH)

# Try to load trained models if available
USE_TRAINED_MODELS = False
model_trainer = None
if settings.USE_ML_MODELS:
    try:
        model_trainer = BehavioralModelTrainer(
            data_dir=settings.TRAINING_DATA_PATH,
            models_dir=settings.ML_MODELS_PATH
        )
        model_path = Path(settings.ML_MODELS_PATH) / "stress_classifier.pkl"
        if model_path.exists():
            model_trainer.load_models()
            USE_TRAINED_MODELS = True
            print("✅ Loaded trained behavioral models")
        else:
            print("⚠️ No trained models found, using rule-based analysis")
    except Exception as e:
        print(f"⚠️ Model loading failed: {e}, using rule-based analysis")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama configuration
OLLAMA_API_URL = f"{settings.OLLAMA_BASE_URL}/api/generate"
OLLAMA_MODEL = settings.OLLAMA_MODEL

# Store quiz sessions in memory (in production, use a database)
quiz_sessions = {}

class QuestionRequest(BaseModel):
    subject: str
    level: str
    user_info: str = ""

class AnswerSubmission(BaseModel):
    session_id: str
    question_id: str
    selected_answer: int  # Index of the selected answer (0-3)
    confidence: int = 50  # User's confidence level
    behavioral_data: Optional[dict] = None  # Webcam metrics

class QuizSession(BaseModel):
    session_id: str
    questions: List[dict]
    score: int = 0
    total_questions: int = 0

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "ml_models_loaded": USE_TRAINED_MODELS,
        "ollama_url": OLLAMA_API_URL
    }

@app.post("/generate-question")
def generate_question(req: QuestionRequest):
    prompt = f"""Génère une question de quiz à choix multiples en {req.subject} pour un niveau {req.level}. {req.user_info}

Format EXACT requis (respecte ce format strictement):
Question: [La question ici]
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Réponse correcte: [A, B, C ou D]
Explication: [Brève explication de la réponse]"""
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        generated_text = data.get("response", "")
        
        # Parse the response to extract question, options, and correct answer
        parsed_question = parse_quiz_response(generated_text)
        
        if not parsed_question:
            # Fallback if parsing fails
            return {
                "question": generated_text,
                "options": [],
                "correct_answer": 0,
                "explanation": "Réponse non disponible"
            }
        
        # Create a session for this question
        session_id = str(uuid4())
        question_id = str(uuid4())
        
        quiz_sessions[session_id] = {
            "questions": [{
                "id": question_id,
                "question": parsed_question["question"],
                "options": parsed_question["options"],
                "correct_answer": parsed_question["correct_answer"],
                "explanation": parsed_question["explanation"]
            }],
            "score": 0,
            "total_questions": 1,
            "answered": []
        }
        
        return {
            "session_id": session_id,
            "question_id": question_id,
            "question": parsed_question["question"],
            "options": parsed_question["options"],
            "explanation": parsed_question["explanation"]
        }
        
    except Exception as e:
        print("Error communicating with Ollama API:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

def parse_quiz_response(text: str) -> Optional[dict]:
    """Parse the generated quiz response to extract structured data"""
    try:
        lines = text.strip().split('\n')
        question = ""
        options = []
        correct_answer = 0
        explanation = ""
        
        option_pattern = re.compile(r'^[A-D]\)?\s*(.+)$', re.IGNORECASE)
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("Question:") or (i == 0 and not line.startswith(("A)", "B)", "C)", "D)"))):
                question = line.replace("Question:", "").strip()
            elif option_pattern.match(line):
                match = option_pattern.match(line)
                if match:
                    options.append(match.group(1).strip())
            elif line.startswith("Réponse correcte:") or line.startswith("Correct:"):
                answer_text = line.split(":")[-1].strip().upper()
                if answer_text in ['A', 'B', 'C', 'D']:
                    correct_answer = ord(answer_text) - ord('A')
            elif line.startswith("Explication:"):
                explanation = line.replace("Explication:", "").strip()
        
        # Ensure we have at least some options
        if len(options) < 2:
            return None
        
        # Fill missing options if needed
        while len(options) < 4:
            options.append(f"Option {len(options) + 1}")
        
        return {
            "question": question if question else "Question de quiz",
            "options": options[:4],
            "correct_answer": correct_answer,
            "explanation": explanation if explanation else "Pas d'explication disponible"
        }
    except Exception as e:
        print(f"Error parsing quiz response: {e}")
        return None

@app.post("/submit-answer")
def submit_answer(submission: AnswerSubmission):
    """Submit an answer and check if it's correct"""
    session = quiz_sessions.get(submission.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    
    # Find the question
    question = next((q for q in session["questions"] if q["id"] == submission.question_id), None)
    
    if not question:
        raise HTTPException(status_code=404, detail="Question non trouvée")
    
    # Check if already answered
    if submission.question_id in session["answered"]:
        raise HTTPException(status_code=400, detail="Question déjà répondue")
    
    is_correct = submission.selected_answer == question["correct_answer"]
    
    if is_correct:
        session["score"] += 1
    
    session["answered"].append(submission.question_id)
    
    # Store user answer data
    if "user_answers_data" not in session:
        session["user_answers_data"] = {}
    session["user_answers_data"][submission.question_id] = submission.selected_answer
    
    # Store confidence level
    if "confidence_data" not in session:
        session["confidence_data"] = {}
    session["confidence_data"][submission.question_id] = submission.confidence
    
    # Store behavioral data if provided
    if submission.behavioral_data:
        if "behavioral_data" not in session:
            session["behavioral_data"] = {}
        session["behavioral_data"][submission.question_id] = submission.behavioral_data
    
    return {
        "correct": is_correct,
        "correct_answer": question["correct_answer"],
        "explanation": question["explanation"],
        "score": session["score"],
        "total_questions": session["total_questions"]
    }

@app.post("/update-confidence")
async def update_confidence(request: dict):
    """Update the confidence level for all answers in a session"""
    session_id = request.get("session_id")
    confidence = request.get("confidence")
    
    if not session_id or confidence is None:
        raise HTTPException(status_code=400, detail="session_id and confidence are required")
    
    session = quiz_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update confidence_data for all answered questions
    if "confidence_data" not in session:
        session["confidence_data"] = {}
    
    # Update confidence for all questions that were answered
    for question_id in session.get("answered", []):
        session["confidence_data"][question_id] = confidence
    
    # Store the overall confidence
    session["overall_confidence"] = confidence
    
    return {
        "success": True,
        "message": "Confidence updated successfully",
        "updated_questions": len(session.get("answered", []))
    }

@app.get("/quiz-score/{session_id}")
def get_quiz_score(session_id: str):
    """Get the current score for a quiz session"""
    session = quiz_sessions.get(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    
    percentage = (session["score"] / session["total_questions"] * 100) if session["total_questions"] > 0 else 0
    
    return {
        "session_id": session_id,
        "score": session["score"],
        "total_questions": session["total_questions"],
        "percentage": round(percentage, 2),
        "answered": len(session["answered"])
    }

@app.get("/quiz-results/{session_id}")
def get_quiz_results(session_id: str):
    """Get comprehensive quiz results with analysis and recommendations"""
    session = quiz_sessions.get(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    
    score = session["score"]
    total = session["total_questions"]
    percentage = (score / total * 100) if total > 0 else 0
    
    # Determine performance level
    if percentage >= 80:
        level = "Excellent"
        message = "Félicitations ! Vous maîtrisez très bien ce sujet."
        color = "success"
    elif percentage >= 60:
        level = "Bien"
        message = "Bonne performance ! Continuez à vous améliorer."
        color = "good"
    elif percentage >= 40:
        level = "Moyen"
        message = "Des progrès sont nécessaires. Révisez les concepts clés."
        color = "average"
    else:
        level = "À améliorer"
        message = "Il est recommandé de revoir les fondamentaux."
        color = "needs-improvement"
    
    # Collect detailed question results
    question_results = []
    user_answers_data = session.get("user_answers_data", {})
    
    for q in session["questions"]:
        q_id = q["id"]
        user_answer = user_answers_data.get(q_id)
        is_answered = user_answer is not None
        is_correct = False
        
        if is_answered:
            is_correct = user_answer == q["correct_answer"]
        
        question_results.append({
            "question": q["question"],
            "options": q["options"],
            "correct_answer": q["correct_answer"],
            "user_answer": user_answer,
            "is_correct": is_correct,
            "is_answered": is_answered,
            "explanation": q["explanation"]
        })
    
    # Generate recommendations based on performance
    recommendations = []
    if percentage < 50:
        recommendations.extend([
            "Revoir les concepts de base du sujet",
            "Pratiquer régulièrement avec des exercices",
            "Consulter des ressources pédagogiques supplémentaires",
            "Demander de l'aide à un professeur ou tuteur"
        ])
    elif percentage < 70:
        recommendations.extend([
            "Approfondir les points faibles identifiés",
            "Pratiquer avec des questions plus complexes",
            "Réviser les explications des questions ratées"
        ])
    elif percentage < 90:
        recommendations.extend([
            "Continuer à pratiquer régulièrement",
            "Explorer des sujets avancés",
            "Partager vos connaissances avec d'autres"
        ])
    else:
        recommendations.extend([
            "Excellent travail ! Maintenez ce niveau",
            "Explorez des défis plus avancés",
            "Envisagez de mentorer d'autres étudiants"
        ])
    
    # Analyze behavioral data if available
    behavioral_analysis = None
    behavioral_insights = []
    if "behavioral_data" in session and session["behavioral_data"]:
        behavioral_analysis = analyze_behavioral_data(
            session["behavioral_data"],
            session["confidence_data"],
            session["user_answers_data"],
            session["questions"]
        )
        behavioral_insights = behavioral_analysis.get("insights", [])
    
    # Save session data for training
    try:
        session_data = {
            "session_id": session_id,
            "score": score,
            "total_questions": total,
            "percentage": percentage,
            "questions": session["questions"],
            "user_answers_data": session["user_answers_data"],
            "confidence_data": session["confidence_data"],
            "behavioral_data": session["behavioral_data"]
        }
        data_collector.save_session(session_data)
    except Exception as e:
        print(f"Warning: Failed to save session data: {e}")
    
    return {
        "session_id": session_id,
        "score": score,
        "total_questions": total,
        "percentage": round(percentage, 2),
        "level": level,
        "message": message,
        "color": color,
        "question_results": question_results,
        "recommendations": recommendations,
        "answered_count": len(session["answered"]),
        "behavioral_analysis": behavioral_analysis,
        "behavioral_insights": behavioral_insights
    }

def analyze_behavioral_data(behavioral_data, confidence_data, answers_data, questions):
    """Analyze webcam behavioral metrics to detect uncertainty patterns"""
    analysis = {
        "overall_stress_level": "low",
        "metacognition_accuracy": "good",
        "insights": [],
        "avg_blink_rate": 0,
        "avg_head_movement": 0,
        "avg_gaze_stability": 0,
        "confidence_calibration": "well_calibrated",
        "ml_predictions": None
    }
    
    if not behavioral_data:
        return analysis
    
    # Use trained ML models if available
    if USE_TRAINED_MODELS:
        try:
            # Calculate average metrics for ML prediction
            total_blink = sum(m.get("blink_rate", 0) for m in behavioral_data.values())
            total_head = sum(m.get("head_movement_score", 0) for m in behavioral_data.values())
            total_gaze = sum(m.get("gaze_stability", 0) for m in behavioral_data.values())
            avg_conf = sum(confidence_data.values()) / len(confidence_data) if confidence_data else 50
            count = len(behavioral_data)
            
            ml_input = {
                "blink_rate": total_blink / count if count > 0 else 0,
                "head_movement_score": total_head / count if count > 0 else 0,
                "gaze_stability": total_gaze / count if count > 0 else 0,
                "confidence": avg_conf
            }
            
            # Get ML predictions
            predictions = model_trainer.predict(ml_input)
            analysis["ml_predictions"] = predictions
            analysis["overall_stress_level"] = predictions["stress_level"]
            
            # Add ML-based insights
            if predictions["stress_probability"] > 0.7:
                analysis["insights"].append(f"Modèle ML détecte un stress élevé (probabilité: {predictions['stress_probability']*100:.0f}%)")
            if predictions["low_attention_probability"] > 0.6:
                analysis["insights"].append(f"Attention fluctuante détectée (probabilité: {predictions['low_attention_probability']*100:.0f}%)")
            if predictions["predicted_confidence_error"] > 30:
                analysis["insights"].append(f"Calibration de confiance à améliorer (erreur prédite: {predictions['predicted_confidence_error']:.1f})")
            
            return analysis
        except Exception as e:
            print(f"ML prediction failed, falling back to rule-based: {e}")
    
    # Aggregate metrics
    total_blink_rate = 0
    total_head_movement = 0
    total_gaze_stability = 0
    count = 0
    
    high_stress_questions = []
    confidence_mismatches = []
    
    for q in questions:
        qid = q["id"]
        if qid in behavioral_data:
            metrics = behavioral_data[qid]
            total_blink_rate += metrics.get("blink_rate", 0)
            total_head_movement += metrics.get("head_movement_score", 0)
            total_gaze_stability += metrics.get("gaze_stability", 0)
            count += 1
            
            # Detect high stress indicators
            if metrics.get("blink_rate", 0) > 25:
                high_stress_questions.append(qid)
            
            # Check confidence vs performance
            if qid in confidence_data and qid in answers_data:
                confidence = confidence_data[qid]
                is_correct = answers_data[qid] == q["correct_answer"]
                
                # Overconfidence: high confidence but wrong answer
                if confidence > 70 and not is_correct:
                    confidence_mismatches.append({
                        "type": "overconfident",
                        "question_id": qid
                    })
                # Underconfidence: low confidence but correct answer
                elif confidence < 40 and is_correct:
                    confidence_mismatches.append({
                        "type": "underconfident",
                        "question_id": qid
                    })
    
    if count > 0:
        analysis["avg_blink_rate"] = round(total_blink_rate / count, 2)
        analysis["avg_head_movement"] = round(total_head_movement / count, 2)
        analysis["avg_gaze_stability"] = round(total_gaze_stability / count, 2)
    
    # Determine stress level
    if analysis["avg_blink_rate"] > 30 or analysis["avg_head_movement"] > 5:
        analysis["overall_stress_level"] = "high"
        analysis["insights"].append("Niveau de stress élevé détecté pendant le quiz")
    elif analysis["avg_blink_rate"] > 20 or analysis["avg_head_movement"] > 3:
        analysis["overall_stress_level"] = "medium"
        analysis["insights"].append("Niveau de stress modéré observé")
    else:
        analysis["insights"].append("Niveau de stress faible - bonne gestion émotionnelle")
    
    # Analyze gaze stability
    if analysis["avg_gaze_stability"] < 0.6:
        analysis["insights"].append("Attention fluctuante - détournements du regard fréquents")
    elif analysis["avg_gaze_stability"] > 0.8:
        analysis["insights"].append("Excellente concentration maintenue tout au long du quiz")
    
    # Confidence calibration analysis
    if len(confidence_mismatches) > 0:
        overconfident = sum(1 for m in confidence_mismatches if m["type"] == "overconfident")
        underconfident = sum(1 for m in confidence_mismatches if m["type"] == "underconfident")
        
        if overconfident > underconfident and overconfident > 2:
            analysis["confidence_calibration"] = "overconfident"
            analysis["insights"].append("Tendance à la surconfiance - améliorer l'auto-évaluation")
        elif underconfident > overconfident and underconfident > 2:
            analysis["confidence_calibration"] = "underconfident"
            analysis["insights"].append("Manque de confiance en soi malgré de bonnes connaissances")
        else:
            analysis["insights"].append("Bonne calibration de la confiance")
    
    # Correlation with performance
    if len(high_stress_questions) > 0:
        correct_under_stress = sum(
            1 for qid in high_stress_questions 
            if qid in answers_data and answers_data[qid] == next(q["correct_answer"] for q in questions if q["id"] == qid)
        )
        stress_performance = correct_under_stress / len(high_stress_questions) if len(high_stress_questions) > 0 else 0
        
        if stress_performance < 0.3:
            analysis["insights"].append("Le stress impacte négativement vos performances")
        elif stress_performance > 0.7:
            analysis["insights"].append("Bonne gestion du stress même sous pression")
    
    return analysis

@app.post("/generate-quiz")
def generate_quiz(req: QuestionRequest, num_questions: int = 5):
    """Generate a complete quiz with multiple questions"""
    session_id = str(uuid4())
    questions = []
    
    for i in range(num_questions):
        prompt = f"""Génère une question de quiz à choix multiples en {req.subject} pour un niveau {req.level}. {req.user_info}

Format EXACT requis (respecte ce format strictement):
Question: [La question ici]
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Réponse correcte: [A, B, C ou D]
Explication: [Brève explication de la réponse]"""
        
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(OLLAMA_API_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            generated_text = data.get("response", "")
            
            parsed_question = parse_quiz_response(generated_text)
            
            if parsed_question:
                question_id = str(uuid4())
                questions.append({
                    "id": question_id,
                    "question": parsed_question["question"],
                    "options": parsed_question["options"],
                    "correct_answer": parsed_question["correct_answer"],
                    "explanation": parsed_question["explanation"]
                })
        except Exception as e:
            print(f"Error generating question {i+1}: {e}")
            continue
    
    if not questions:
        raise HTTPException(status_code=500, detail="Impossible de générer des questions")
    
    quiz_sessions[session_id] = {
        "questions": questions,
        "score": 0,
        "total_questions": len(questions),
        "answered": []
    }
    
    # Return questions without correct answers
    return {
        "session_id": session_id,
        "questions": [
            {
                "id": q["id"],
                "question": q["question"],
                "options": q["options"]
            } for q in questions
        ],
        "total_questions": len(questions)
    }
