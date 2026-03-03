from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import requests
import json
import re
from uuid import uuid4

# Import from organized modules
from config import settings
from ml import DataCollector

# Initialize data collector
data_collector = DataCollector(data_dir=settings.TRAINING_DATA_PATH)

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
        "ollama_url": OLLAMA_API_URL
    }

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
    
    # Dunning-Kruger effect analysis
    dk_analysis = calculate_dunning_kruger(
        score_percentage=percentage,
        confidence_data=session.get("confidence_data", {}),
        answers_data=session.get("user_answers_data", {}),
        questions=session.get("questions", [])
    )
    
    # Save session data for training
    try:
        session_data = {
            "session_id": session_id,
            "score": score,
            "total_questions": total,
            "percentage": percentage,
            "questions": session["questions"],
            "user_answers_data": session["user_answers_data"],
            "confidence_data": session["confidence_data"]
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
        "dunning_kruger": dk_analysis
    }

def calculate_dunning_kruger(score_percentage, confidence_data, answers_data, questions):
    """
    Calculate Dunning-Kruger effect based on:
    - Declared confidence vs actual performance
    - Per-question calibration analysis
    """
    if not confidence_data or not questions:
        return None

    per_question = []
    total_declared_confidence = 0
    n = len(questions)

    for q in questions:
        qid = q["id"]
        declared_conf = confidence_data.get(qid, 50)
        is_correct = answers_data.get(qid) == q["correct_answer"] if qid in answers_data else None
        is_answered = qid in answers_data

        # Determine DK signal per question
        if is_answered and is_correct is not None:
            if declared_conf > 65 and not is_correct:
                dk_signal = "overconfident"
            elif declared_conf < 40 and is_correct:
                dk_signal = "underconfident"
            else:
                dk_signal = "calibrated"
        else:
            dk_signal = "unanswered"

        per_question.append({
            "question_index": questions.index(q) + 1,
            "question_id": qid,
            "declared_confidence": declared_conf,
            "is_correct": is_correct,
            "is_answered": is_answered,
            "dk_signal": dk_signal
        })

        total_declared_confidence += declared_conf

    avg_declared = total_declared_confidence / n
    dk_index = round(avg_declared - score_percentage, 2)

    # Classify zone
    if score_percentage < 40:
        if dk_index > 20:
            zone = "dunning_kruger_peak"
            zone_label = "Pic Dunning-Kruger"
            message = "Vous surestimez significativement vos connaissances"
            recommendation = "Pratiquez davantage et confrontez vos connaissances à des sources fiables"
            color = "red"
        elif dk_index < -20:
            zone = "conscious_incompetence"
            zone_label = "Incompétence Consciente"
            message = "Vous êtes conscient de vos lacunes — c'est le premier pas vers la maîtrise"
            recommendation = "Continuez à apprendre, vous progressez bien"
            color = "orange"
        else:
            zone = "beginner_calibrated"
            zone_label = "Débutant Calibré"
            message = "Votre auto-évaluation est réaliste pour votre niveau actuel"
            recommendation = "Consolidez les bases et progressez étape par étape"
            color = "yellow"
    elif score_percentage < 70:
        if dk_index > 20:
            zone = "valley_of_despair"
            zone_label = "Vallée du Désespoir"
            message = "En progression mais avec une surconfiance partielle"
            recommendation = "Identifiez précisément vos points faibles et travaillez-les"
            color = "orange"
        elif dk_index < -20:
            zone = "impostor_syndrome"
            zone_label = "Syndrome de l'Imposteur"
            message = "Vous sous-estimez vos compétences réelles"
            recommendation = "Faites confiance à vos connaissances, votre niveau est meilleur que vous ne le pensez"
            color = "blue"
        else:
            zone = "slope_of_enlightenment"
            zone_label = "Pente de l'Illumination"
            message = "Bonne calibration en phase d'apprentissage intermédiaire"
            recommendation = "Continuez sur cette lancée, vous évoluez bien"
            color = "teal"
    else:
        if dk_index > 15:
            zone = "expert_overconfident"
            zone_label = "Expert Surconfiant"
            message = "Excellentes connaissances avec légère tendance à la surconfiance"
            recommendation = "Restez humble et continuez à approfondir"
            color = "yellow"
        elif dk_index < -15:
            zone = "expert_modest"
            zone_label = "Expert Humble"
            message = "Véritable expertise avec humilité — profil d'expert accompli"
            recommendation = "Partagez vos connaissances avec les autres"
            color = "green"
        else:
            zone = "expert_calibrated"
            zone_label = "Expert Calibré"
            message = "Expertise élevée avec auto-évaluation précise — profil idéal"
            recommendation = "Explorez des défis plus avancés et mentoring"
            color = "green"

    # Per-question breakdown counts
    overconfident_count = sum(1 for q in per_question if q["dk_signal"] == "overconfident")
    underconfident_count = sum(1 for q in per_question if q["dk_signal"] == "underconfident")
    calibrated_count = sum(1 for q in per_question if q["dk_signal"] == "calibrated")
    calibration_score = round((calibrated_count / n) * 100, 1) if n > 0 else 0

    return {
        "dk_index": dk_index,
        "zone": zone,
        "zone_label": zone_label,
        "message": message,
        "recommendation": recommendation,
        "color": color,
        "declared_confidence": round(avg_declared, 1),
        "actual_score": round(score_percentage, 1),
        "calibration_score": calibration_score,
        "overconfident_count": overconfident_count,
        "underconfident_count": underconfident_count,
        "calibrated_count": calibrated_count,
        "per_question": per_question
    }


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
