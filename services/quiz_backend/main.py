from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import requests
import re
from uuid import uuid4

# Import from organized modules
from .config import settings
from .core.session_store import init_session_store, save_session, load_session

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
SIMCO_LOGIC_BASE_URL = settings.SIMCO_LOGIC_BASE_URL

# Store quiz sessions in memory (in production, use a database)
quiz_sessions = {}


def get_session(session_id: str):
    session = quiz_sessions.get(session_id)
    if session is not None:
        return session

    db_session = load_session(session_id)
    if db_session is not None:
        quiz_sessions[session_id] = db_session
    return db_session


def persist_session(session_id: str) -> None:
    session = quiz_sessions.get(session_id)
    if session is not None:
        save_session(session_id, session)


def normalize_self_confidence(value) -> float:
    """Normalize confidence input to [0, 1]. Accepts either [0,100] or [0,1] scale."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.5

    # If already normalized, keep scale. Otherwise convert from percentage.
    normalized = numeric if 0 <= numeric <= 1 else (numeric / 100.0)
    return max(0.0, min(1.0, normalized))


def confidence_to_percent(value) -> float:
    """Return confidence on [0,100] scale from either [0,1] or [0,100] input."""
    return round(normalize_self_confidence(value) * 100.0, 2)


def compute_true_confidence(session: dict, self_confidence_normalized: float) -> dict:
    """Compute true confidence using only SIMCO Logic neural model."""
    face_confidence_per_question = []
    behavioral_data = session.get("behavioral_data", {}) or {}

    for q in session.get("questions", []):
        qid = q.get("id")
        q_metrics = behavioral_data.get(qid, {}) if isinstance(behavioral_data, dict) else {}
        face_conf = q_metrics.get("face_final_confidence")
        if face_conf is not None:
            try:
                face_confidence_per_question.append(float(face_conf))
            except (TypeError, ValueError):
                continue

    payload = {
        "self_confidence": self_confidence_normalized,
        "face_confidence_per_question": face_confidence_per_question,
    }

    try:
        response = requests.post(
            f"{SIMCO_LOGIC_BASE_URL}/analyze/true-confidence",
            json=payload,
            timeout=5,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"SIMCO Logic unavailable: {exc}") from exc

    if not response.ok:
        raise HTTPException(
            status_code=503,
            detail=f"SIMCO Logic error: status {response.status_code}",
        )

    data = response.json()
    if "true_confidence" not in data or "true_confidence_normalized" not in data:
        raise HTTPException(status_code=503, detail="SIMCO Logic returned invalid true confidence payload")

    return {
        "true_confidence": data.get("true_confidence"),
        "true_confidence_normalized": data.get("true_confidence_normalized"),
        "source": "simco_logic",
    }

class QuestionRequest(BaseModel):
    subject: str
    level: str
    user_info: str = ""
    user_name: Optional[str] = ""
    user_email: Optional[str] = ""

class AnswerSubmission(BaseModel):
    session_id: str
    question_id: str
    selected_answer: int  # Index of the selected answer (0-3)
    confidence: int = 50  # User's confidence level
    behavioral_data: Optional[dict] = None  # Webcam metrics


class TrueConfidenceRequest(BaseModel):
    self_confidence: float = Field(..., ge=0.0, le=1.0)
    face_confidence_per_question: List[float] = Field(default_factory=list)


def send_quiz_result_notification(session: dict, results_payload: dict) -> dict:
    """Send quiz result email through notification backend (best-effort, non-blocking)."""
    user_name = (session.get("user_name") or "").strip()
    user_email = (session.get("user_email") or "").strip()

    if not user_email:
        return {
            "attempted": False,
            "sent": False,
            "reason": "missing_user_email",
        }

    quiz_result_payload = {
        "score": results_payload.get("score", 0),
        "total_questions": results_payload.get("total_questions", 0),
        "percentage": results_payload.get("percentage", 0),
        "level": results_payload.get("level"),
        "message": results_payload.get("message"),
        "recommendations": results_payload.get("recommendations", []),
        "self_confidence": results_payload.get("self_confidence"),
        "true_confidence": (results_payload.get("true_confidence") or {}).get("true_confidence"),
        "profile_label": (results_payload.get("dunning_kruger") or {}).get("zone_label"),
    }

    payload = {
        "user_name": user_name or "Étudiant",
        "user_email": user_email,
        "quiz_result": quiz_result_payload,
        "question_results": [
            {
                "question": q.get("question", ""),
                "is_correct": q.get("is_correct"),
                "confidence_analysis": q.get("confidence_analysis"),
                "face_confidence": q.get("face_confidence"),
            }
            for q in results_payload.get("question_results", [])
        ],
        "dunning_kruger": {
            "actual_score": (results_payload.get("dunning_kruger") or {}).get("actual_score"),
            "declared_confidence": (results_payload.get("dunning_kruger") or {}).get("declared_confidence"),
            "calibration_score": (results_payload.get("dunning_kruger") or {}).get("calibration_score"),
        },
    }

    try:
        response = requests.post(
            f"{settings.NOTIFICATION_BASE_URL}/notifications/quiz-result",
            json=payload,
            timeout=settings.NOTIFICATION_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        return {
            "attempted": True,
            "sent": False,
            "reason": "notification_service_unavailable",
            "error": str(exc),
        }

    if not response.ok:
        return {
            "attempted": True,
            "sent": False,
            "reason": "notification_service_error",
            "status_code": response.status_code,
            "detail": response.text[:500],
        }

    try:
        response_json = response.json()
    except ValueError:
        response_json = {"detail": "notification_sent"}

    return {
        "attempted": True,
        "sent": True,
        "detail": response_json.get("detail", "notification_sent"),
    }

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


@app.post("/analyze/true-confidence")
def analyze_true_confidence(payload: TrueConfidenceRequest):
    """Proxy endpoint to SIMCO Logic neural confidence service."""
    try:
        response = requests.post(
            f"{SIMCO_LOGIC_BASE_URL}/analyze/true-confidence",
            json=payload.model_dump(),
            timeout=5,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"SIMCO Logic unavailable: {exc}") from exc

    if not response.ok:
        raise HTTPException(
            status_code=503,
            detail=f"SIMCO Logic error: status {response.status_code}",
        )

    return response.json()


@app.on_event("startup")
def startup_event():
    init_session_store()

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
    session = get_session(submission.session_id)
    
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
    
    # Store behavioral data if provided
    if submission.behavioral_data:
        if "behavioral_data" not in session:
            session["behavioral_data"] = {}
        session["behavioral_data"][submission.question_id] = submission.behavioral_data

    persist_session(submission.session_id)
    
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
    self_confidence = request.get("self_confidence")
    if self_confidence is None:
        # Backward compatibility with older frontend payloads
        self_confidence = request.get("confidence")
    
    if not session_id or self_confidence is None:
        raise HTTPException(status_code=400, detail="session_id and self_confidence are required")
    
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    normalized_self_confidence = normalize_self_confidence(self_confidence)
    self_confidence_percent = round(normalized_self_confidence * 100.0, 2)
    
    # Store one global self-confidence for the whole session
    session["self_confidence"] = self_confidence_percent
    session["self_confidence_normalized"] = normalized_self_confidence
    # Keep backward compatibility key in persisted session
    session["overall_confidence"] = self_confidence_percent
    # Clean old per-question confidence payloads if they exist
    if "confidence_data" in session:
        del session["confidence_data"]

    persist_session(session_id)
    
    return {
        "success": True,
        "message": "Self confidence updated successfully",
        "self_confidence": self_confidence_percent,
        "self_confidence_normalized": normalized_self_confidence,
        "updated_questions": len(session.get("answered", []))
    }

@app.get("/quiz-results/{session_id}")
def get_quiz_results(session_id: str):
    """Get comprehensive quiz results with analysis and recommendations"""
    session = get_session(session_id)
    
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
    behavioral_data = session.get("behavioral_data", {}) if isinstance(session.get("behavioral_data", {}), dict) else {}

    # Global self confidence (single value for the full quiz)
    global_self_conf = session.get("self_confidence", session.get("overall_confidence", 50))
    try:
        global_self_conf = confidence_to_percent(global_self_conf)
    except Exception:
        global_self_conf = 50.0
    legacy_confidence_per_question = session.get("confidence_per_question", {}) if isinstance(session.get("confidence_per_question", {}), dict) else {}
    
    for q in session["questions"]:
        q_id = q["id"]
        user_answer = user_answers_data.get(q_id)
        is_answered = user_answer is not None
        is_correct = False
        
        if is_answered:
            is_correct = user_answer == q["correct_answer"]

        # Prefer legacy per-question confidence if available, else fallback to global confidence
        raw_declared = legacy_confidence_per_question.get(q_id, global_self_conf)
        try:
            declared_confidence = confidence_to_percent(raw_declared)
        except Exception:
            declared_confidence = global_self_conf

        # Optional face confidence from webcam pipeline
        q_behavior = behavioral_data.get(q_id, {}) if isinstance(behavioral_data, dict) else {}
        raw_face_conf = q_behavior.get("face_final_confidence")
        face_confidence = None
        if raw_face_conf is not None:
            try:
                raw_face_conf_float = float(raw_face_conf)
                face_confidence = round(raw_face_conf_float * 100.0, 1) if raw_face_conf_float <= 1.0 else round(raw_face_conf_float, 1)
            except Exception:
                face_confidence = None

        # Human-friendly per-question analysis
        # Use face confidence for analysis when available (this is what frontend displays).
        analysis_confidence = face_confidence if face_confidence is not None else declared_confidence
        if not is_answered:
            confidence_analysis = "Question non répondue."
        elif is_correct and analysis_confidence >= 70:
            confidence_analysis = "Bonne réponse avec confiance élevée : continue cette méthode."
        elif is_correct and analysis_confidence < 40:
            confidence_analysis = "Bonne réponse mais confiance basse : fais plus confiance à ton raisonnement."
        elif (not is_correct) and analysis_confidence >= 70:
            confidence_analysis = "Confiance élevée mais réponse incorrecte : vérifie davantage avant de valider."
        elif (not is_correct) and analysis_confidence < 40:
            confidence_analysis = "Confiance basse et réponse incorrecte : reprends les bases de ce type de question."
        else:
            confidence_analysis = "Confiance et résultat partiellement alignés : continue à ajuster ton auto-évaluation."
        
        question_results.append({
            "question_id": q_id,
            "question": q["question"],
            "options": q["options"],
            "correct_answer": q["correct_answer"],
            "user_answer": user_answer,
            "is_correct": is_correct,
            "is_answered": is_answered,
            "explanation": q["explanation"],
            "declared_confidence": round(declared_confidence, 1),
            "face_confidence": face_confidence,
            "confidence_analysis": confidence_analysis
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
    
    # Use one declared confidence value for all answers (user inputs once)
    self_confidence = session.get("self_confidence")
    if self_confidence is None:
        self_confidence = session.get("overall_confidence")
    if self_confidence is None:
        # Backward compatibility with older sessions
        old_conf = session.get("confidence_data", {})
        if isinstance(old_conf, dict) and old_conf:
            self_confidence = next(iter(old_conf.values()))
        else:
            self_confidence = 50

    # Keep both scales available in backend
    self_confidence = confidence_to_percent(self_confidence)
    self_confidence_normalized = round(self_confidence / 100.0, 4)
    session["self_confidence"] = self_confidence
    session["self_confidence_normalized"] = self_confidence_normalized

    true_confidence = compute_true_confidence(session, self_confidence_normalized)

    # Analyze behavioral data if available
    behavioral_analysis = None
    behavioral_insights = []
    if "behavioral_data" in session and session["behavioral_data"]:
        behavioral_analysis = analyze_behavioral_data(
            session["behavioral_data"],
            self_confidence,
            session["user_answers_data"],
            session["questions"]
        )
        behavioral_insights = behavioral_analysis.get("insights", [])

    # Dunning-Kruger effect analysis
    dk_analysis = calculate_dunning_kruger(
        score_percentage=percentage,
        confidence_data=self_confidence,
        answers_data=session.get("user_answers_data", {}),
        questions=session.get("questions", []),
        behavioral_data=session.get("behavioral_data", {})
    )
    
    results_payload = {
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
        "self_confidence": self_confidence,
        "self_confidence_normalized": self_confidence_normalized,
        "true_confidence": true_confidence,
        "behavioral_analysis": behavioral_analysis,
        "behavioral_insights": behavioral_insights,
        "dunning_kruger": dk_analysis
    }

    notification_result = send_quiz_result_notification(session, results_payload)
    results_payload["notification"] = notification_result

    return results_payload

def calculate_dunning_kruger(score_percentage, confidence_data, answers_data, questions, behavioral_data=None):
    """
    Calculate Dunning-Kruger effect based on:
    - Declared confidence vs actual performance
    - Behavioral signals (blink rate, hesitation, hover times)
    - Per-question calibration analysis
    """
    if not questions:
        return None

    per_question = []
    total_declared_confidence = 0
    total_behavioral_confidence = 0
    n = len(questions)

    for q in questions:
        qid = q["id"]
        declared_conf = 50 if confidence_data is None else confidence_data
        is_correct = answers_data.get(qid) == q["correct_answer"] if qid in answers_data else None
        is_answered = qid in answers_data

        # Compute behavioral confidence correction
        behavioral_conf = declared_conf
        b = (behavioral_data or {}).get(qid, {})
        answer_changes = b.get("answer_changes", 0)
        blink_rate = b.get("blink_rate", 0)
        hover_time = b.get("total_hover_time", 0)
        time_first_click = b.get("time_to_first_click", 10)

        if answer_changes > 1:
            behavioral_conf -= answer_changes * 5
        if blink_rate > 20:
            behavioral_conf -= 10
        if hover_time > 15:
            behavioral_conf -= 5
        if time_first_click < 3 and is_correct:
            behavioral_conf += 10
        behavioral_conf = max(0, min(100, behavioral_conf))

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
            "behavioral_confidence": round(behavioral_conf, 1),
            "is_correct": is_correct,
            "is_answered": is_answered,
            "dk_signal": dk_signal
        })

        total_declared_confidence += declared_conf
        total_behavioral_confidence += behavioral_conf

    avg_declared = total_declared_confidence / n
    avg_behavioral = total_behavioral_confidence / n
    dk_index = round(avg_behavioral - score_percentage, 2)

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
        "behavioral_confidence": round(avg_behavioral, 1),
        "actual_score": round(score_percentage, 1),
        "calibration_score": calibration_score,
        "overconfident_count": overconfident_count,
        "underconfident_count": underconfident_count,
        "calibrated_count": calibrated_count,
        "per_question": per_question
    }


def analyze_behavioral_data(behavioral_data, confidence_value, answers_data, questions):
    """Analyze webcam behavioral metrics to detect uncertainty patterns"""
    analysis = {
        "overall_stress_level": "low",
        "insights": [],
        "avg_blink_rate": 0,
        "avg_head_movement": 0,
        "avg_gaze_stability": 0,
        "confidence_calibration": "well_calibrated"
    }

    if not behavioral_data:
        return analysis

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
            
            # Check confidence vs performance (single confidence for the whole quiz)
            if qid in answers_data:
                confidence = 50 if confidence_value is None else confidence_value
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
        "answered": [],
        "user_name": (req.user_name or "").strip(),
        "user_email": (req.user_email or "").strip(),
        "user_info": req.user_info,
    }
    persist_session(session_id)
    
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
