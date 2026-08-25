from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional
import requests
import json
import re
from uuid import uuid4
from collections import Counter

# Import from organized modules
from config import settings
from ml import DataCollector
from core.cv_service import analyze_photo, predict_dk_profil
from core.notion_service import analyze_session_notions, generate_personalized_message
from core.report_service import generate_report_pdf
from core.email_service import send_report_email

# Initialize data collector
data_collector = DataCollector(data_dir=settings.TRAINING_DATA_PATH)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_API_URL = f"{settings.OLLAMA_BASE_URL}/api/generate"
OLLAMA_MODEL   = settings.OLLAMA_MODEL
quiz_sessions  = {}


class QuestionRequest(BaseModel):
    subject: str
    level: str
    user_info: str = ""

class AnswerSubmission(BaseModel):
    session_id: str
    question_id: str
    selected_answer: int
    confidence: int = 50

class SendReportRequest(BaseModel):
    session_id: str
    student_name: str
    student_email: str
    subject: str


@app.get("/")
def root():
    return {"name": settings.APP_NAME, "version": settings.VERSION, "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "ollama_url": OLLAMA_API_URL}


def parse_quiz_response(text: str) -> Optional[dict]:
    try:
        lines = text.strip().split('\n')
        question, options, correct_answer, explanation = "", [], 0, ""
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
        if len(options) < 2:
            return None
        while len(options) < 4:
            options.append(f"Option {len(options) + 1}")
        return {
            "question": question if question else "Question de quiz",
            "options": options[:4],
            "correct_answer": correct_answer,
            "explanation": explanation if explanation else "Pas d'explication disponible"
        }
    except Exception as e:
        print(f"Error parsing: {e}")
        return None


@app.post("/submit-answer")
def submit_answer(submission: AnswerSubmission):
    session = quiz_sessions.get(submission.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")
    question = next((q for q in session["questions"] if q["id"] == submission.question_id), None)
    if not question:
        raise HTTPException(status_code=404, detail="Question non trouvée")
    if submission.question_id in session["answered"]:
        raise HTTPException(status_code=400, detail="Question déjà répondue")
    is_correct = submission.selected_answer == question["correct_answer"]
    if is_correct:
        session["score"] += 1
    session["answered"].append(submission.question_id)
    if "user_answers_data" not in session:
        session["user_answers_data"] = {}
    session["user_answers_data"][submission.question_id] = submission.selected_answer
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
    session_id = request.get("session_id")
    confidence = request.get("confidence")
    if not session_id or confidence is None:
        raise HTTPException(status_code=400, detail="session_id and confidence are required")
    session = quiz_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if "confidence_data" not in session:
        session["confidence_data"] = {}
    for question_id in session.get("answered", []):
        session["confidence_data"][question_id] = confidence
    session["overall_confidence"] = confidence
    return {"success": True, "updated_questions": len(session.get("answered", []))}


@app.get("/quiz-results/{session_id}")
def get_quiz_results(session_id: str):
    session = quiz_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    score      = session["score"]
    total      = session["total_questions"]
    percentage = (score / total * 100) if total > 0 else 0

    if percentage >= 80:
        level, message, color = "Excellent", "Félicitations ! Vous maîtrisez très bien ce sujet.", "success"
    elif percentage >= 60:
        level, message, color = "Bien", "Bonne performance ! Continuez à vous améliorer.", "good"
    elif percentage >= 40:
        level, message, color = "Moyen", "Des progrès sont nécessaires. Révisez les concepts clés.", "average"
    else:
        level, message, color = "À améliorer", "Il est recommandé de revoir les fondamentaux.", "needs-improvement"

    question_results   = []
    user_answers_data  = session.get("user_answers_data", {})
    for q in session["questions"]:
        q_id       = q["id"]
        user_answer = user_answers_data.get(q_id)
        is_answered = user_answer is not None
        is_correct  = is_answered and user_answer == q["correct_answer"]
        behavioral  = session.get("behavioral_data", {}).get(q_id, {})
        question_results.append({
            "question": q["question"],
            "options": q["options"],
            "correct_answer": q["correct_answer"],
            "user_answer": user_answer,
            "is_correct": is_correct,
            "is_answered": is_answered,
            "explanation": q["explanation"],
            "confidence_observed": behavioral.get("confidence_observed_avg")
        })

    if percentage < 50:
        recommendations = [
            "Revoir les concepts de base du sujet",
            "Pratiquer régulièrement avec des exercices",
            "Consulter des ressources pédagogiques supplémentaires",
            "Demander de l'aide à un professeur ou tuteur"
        ]
    elif percentage < 70:
        recommendations = [
            "Approfondir les points faibles identifiés",
            "Pratiquer avec des questions plus complexes",
            "Réviser les explications des questions ratées"
        ]
    elif percentage < 90:
        recommendations = [
            "Continuer à pratiquer régulièrement",
            "Explorer des sujets avancés",
            "Partager vos connaissances avec d'autres"
        ]
    else:
        recommendations = [
            "Excellent travail ! Maintenez ce niveau",
            "Explorez des défis plus avancés",
            "Envisagez de mentorer d'autres étudiants"
        ]

    dk_analysis = calculate_dunning_kruger(
        score_percentage=percentage,
        confidence_data=session.get("confidence_data", {}),
        answers_data=session.get("user_answers_data", {}),
        questions=session.get("questions", []),
        behavioral_data=session.get("behavioral_data", {})
    )

    # Sauvegarder pour entraînement
    try:
        data_collector.save_session({
            "session_id": session_id,
            "score": score, "total_questions": total, "percentage": percentage,
            "questions": session["questions"],
            "user_answers_data": session["user_answers_data"],
            "confidence_data": session["confidence_data"],
            "behavioral_data": session.get("behavioral_data", {})
        })
    except Exception as e:
        print(f"Warning: {e}")

    return {
        "session_id": session_id,
        "score": score, "total_questions": total,
        "percentage": round(percentage, 2),
        "level": level, "message": message, "color": color,
        "question_results": question_results,
        "recommendations": recommendations,
        "answered_count": len(session["answered"]),
        "dunning_kruger": dk_analysis
    }


# ─── NOUVELLE ROUTE — Analyse des notions via Ollama ─────────────────────────

@app.get("/analyze-notions/{session_id}")
async def analyze_notions(session_id: str):
    """
    Analyse les questions de la session via Ollama.
    Retourne :
    - notions_to_revise     : concepts à revoir
    - mastered_notions      : compétences maîtrisées sous-estimées
    - overconfident_notions : surconfiance détectée
    - personalized_message  : message personnalisé selon le profil DK
    """
    session = quiz_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    # Récupérer le profil ML depuis la session si disponible
    dk = calculate_dunning_kruger(
        score_percentage=(session["score"] / session["total_questions"] * 100),
        confidence_data=session.get("confidence_data", {}),
        answers_data=session.get("user_answers_data", {}),
        questions=session.get("questions", []),
        behavioral_data=session.get("behavioral_data", {})
    )
    profil_ml = dk.get("profil_ml") if dk else "calibrated"
    score     = (session["score"] / session["total_questions"] * 100)

    # Analyser les notions via Ollama
    notions = analyze_session_notions({
        "questions":       session.get("questions", []),
        "user_answers_data": session.get("user_answers_data", {}),
        "confidence_data": session.get("confidence_data", {}),
        "behavioral_data": session.get("behavioral_data", {})
    })

    # Générer le message personnalisé
    personal_msg = generate_personalized_message(profil_ml or "calibrated", score, notions)

    # Stocker dans la session pour le rapport
    session["notions_analysis"]    = notions
    session["personalized_message"] = personal_msg

    return {
        "success": True,
        "notions_to_revise":     notions["notions_to_revise"],
        "mastered_notions":      notions["mastered_notions"],
        "overconfident_notions": notions["overconfident_notions"],
        "personalized_message":  personal_msg
    }


# ─── NOUVELLE ROUTE — Génération du rapport PDF ──────────────────────────────

@app.get("/generate-report/{session_id}")
async def generate_report(session_id: str, student_name: str = "Étudiant", subject: str = ""):
    """
    Génère le rapport PDF et le retourne en téléchargement.
    """
    session = quiz_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    score      = session["score"]
    total      = session["total_questions"]
    percentage = (score / total * 100) if total > 0 else 0

    results = {
        "score": score, "total_questions": total,
        "percentage": round(percentage, 2),
        "level": "Voir rapport", "message": "",
        "recommendations": session.get("recommendations", [])
    }

    if percentage < 50:
        results["recommendations"] = [
            "Revoir les concepts de base", "Pratiquer régulièrement",
            "Consulter des ressources supplémentaires"
        ]
    elif percentage < 70:
        results["recommendations"] = [
            "Approfondir les points faibles", "Pratiquer avec des questions complexes"
        ]
    else:
        results["recommendations"] = [
            "Continuer à pratiquer", "Explorer des sujets avancés"
        ]

    dk = calculate_dunning_kruger(
        score_percentage=percentage,
        confidence_data=session.get("confidence_data", {}),
        answers_data=session.get("user_answers_data", {}),
        questions=session.get("questions", []),
        behavioral_data=session.get("behavioral_data", {})
    )

    notions = session.get("notions_analysis", {
        "notions_to_revise": [], "mastered_notions": [], "overconfident_notions": []
    })

    try:
        pdf_bytes = generate_report_pdf(
            student_name=student_name,
            subject=subject or session.get("subject", "Quiz"),
            results=results,
            notions=notions,
            dk=dk
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération PDF: {str(e)}")

    # Stocker le PDF dans la session
    session["pdf_bytes"]     = pdf_bytes
    session["student_name"]  = student_name
    session["subject_label"] = subject

    filename = f"rapport_SIMCO_{student_name.replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ─── NOUVELLE ROUTE — Envoi par email ────────────────────────────────────────

@app.post("/send-report")
async def send_report(req: SendReportRequest):
    """
    Génère le rapport PDF et l'envoie par email à l'étudiant.
    """
    session = quiz_sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    score      = session["score"]
    total      = session["total_questions"]
    percentage = (score / total * 100) if total > 0 else 0

    dk = calculate_dunning_kruger(
        score_percentage=percentage,
        confidence_data=session.get("confidence_data", {}),
        answers_data=session.get("user_answers_data", {}),
        questions=session.get("questions", []),
        behavioral_data=session.get("behavioral_data", {})
    )

    notions = session.get("notions_analysis", {
        "notions_to_revise": [], "mastered_notions": [], "overconfident_notions": []
    })

    results = {
        "score": score, "total_questions": total,
        "percentage": round(percentage, 2),
        "level": "", "message": "",
        "recommendations": []
    }

    if percentage < 50:
        results["recommendations"] = [
            "Revoir les concepts de base", "Pratiquer régulièrement"
        ]
    else:
        results["recommendations"] = [
            "Continuer à pratiquer", "Explorer des sujets avancés"
        ]

    # Générer le PDF
    try:
        pdf_bytes = generate_report_pdf(
            student_name=req.student_name,
            subject=req.subject,
            results=results,
            notions=notions,
            dk=dk
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur PDF: {str(e)}")

    # Envoyer l'email
    result = send_report_email(
        recipient_email=req.student_email,
        student_name=req.student_name,
        subject=req.subject,
        pdf_bytes=pdf_bytes,
        score=percentage,
        profil_ml=dk.get("profil_ml", "") if dk else "",
        zone_label=dk.get("zone_label", "") if dk else ""
    )

    return result


def calculate_dunning_kruger(score_percentage, confidence_data, answers_data, questions, behavioral_data={}):
    if not confidence_data or not questions:
        return None

    per_question = []
    total_declared = 0
    total_observed = 0
    observed_count = 0
    n = len(questions)

    for q in questions:
        qid          = q["id"]
        declared_conf = confidence_data.get(qid, 50)
        is_correct   = answers_data.get(qid) == q["correct_answer"] if qid in answers_data else None
        is_answered  = qid in answers_data
        behavioral   = behavioral_data.get(qid, {})
        conf_observed = behavioral.get("confidence_observed_avg")
        dominant_emotion = None
        if behavioral.get("photos"):
            dominant_emotion = behavioral["photos"][-1].get("dominant_emotion")

        if is_answered and is_correct is not None:
            dk_signal = "overconfident" if declared_conf > 65 and not is_correct else \
                        "underconfident" if declared_conf < 40 and is_correct else "calibrated"
        else:
            dk_signal = "unanswered"

        ml_profil = ml_conf = None
        ml_method = "none"
        if behavioral and behavioral.get("photos") and is_answered:
            photos = [p for p in behavioral.get("photos", []) if p.get("success")]
            if photos:
                avg_emotions = {
                    k: round(sum(p.get("emotions", {}).get(k, 0) for p in photos) / len(photos), 2)
                    for k in ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
                }
                try:
                    ml_result = predict_dk_profil(
                        emotions=avg_emotions,
                        confidence_declared=declared_conf,
                        confidence_observed=conf_observed if conf_observed is not None else 0.5,
                        is_correct=1 if is_correct else 0
                    )
                    ml_profil = ml_result["profil"]
                    ml_conf   = ml_result["confidence_ml"]
                    ml_method = ml_result["method"]
                except Exception as e:
                    print(f"⚠️ ML: {e}")

        per_question.append({
            "question_index": questions.index(q) + 1,
            "question_id": qid,
            "declared_confidence": declared_conf,
            "confidence_observed": conf_observed,
            "dominant_emotion": dominant_emotion,
            "is_correct": is_correct,
            "is_answered": is_answered,
            "dk_signal": dk_signal,
            "profil_ml": ml_profil,
            "confidence_ml": ml_conf,
            "method": ml_method
        })

        total_declared += declared_conf
        if conf_observed is not None:
            total_observed += conf_observed * 100
            observed_count += 1

    avg_declared = total_declared / n
    avg_observed = (total_observed / observed_count) if observed_count > 0 else None
    dk_index     = round(avg_declared - score_percentage, 2)
    dk_index_obs = round(avg_observed - score_percentage, 2) if avg_observed is not None else None

    if score_percentage < 40:
        if dk_index > 20:
            zone, zone_label = "dunning_kruger_peak", "Pic Dunning-Kruger"
            message = "Vous surestimez significativement vos connaissances"
            recommendation = "Pratiquez davantage et confrontez vos connaissances à des sources fiables"
            color = "red"
        elif dk_index < -20:
            zone, zone_label = "conscious_incompetence", "Incompétence Consciente"
            message = "Vous êtes conscient de vos lacunes — c'est le premier pas vers la maîtrise"
            recommendation = "Continuez à apprendre, vous progressez bien"
            color = "orange"
        else:
            zone, zone_label = "beginner_calibrated", "Débutant Calibré"
            message = "Votre auto-évaluation est réaliste pour votre niveau actuel"
            recommendation = "Consolidez les bases et progressez étape par étape"
            color = "yellow"
    elif score_percentage < 70:
        if dk_index > 20:
            zone, zone_label = "valley_of_despair", "Vallée du Désespoir"
            message = "En progression mais avec une surconfiance partielle"
            recommendation = "Identifiez précisément vos points faibles et travaillez-les"
            color = "orange"
        elif dk_index < -20:
            zone, zone_label = "impostor_syndrome", "Syndrome de l'Imposteur"
            message = "Vous sous-estimez vos compétences réelles"
            recommendation = "Faites confiance à vos connaissances, votre niveau est meilleur"
            color = "blue"
        else:
            zone, zone_label = "slope_of_enlightenment", "Pente de l'Illumination"
            message = "Bonne calibration en phase d'apprentissage intermédiaire"
            recommendation = "Continuez sur cette lancée, vous évoluez bien"
            color = "teal"
    else:
        if dk_index > 15:
            zone, zone_label = "expert_overconfident", "Expert Surconfiant"
            message = "Excellentes connaissances avec légère tendance à la surconfiance"
            recommendation = "Restez humble et continuez à approfondir"
            color = "yellow"
        elif dk_index < -15:
            zone, zone_label = "expert_modest", "Expert Humble"
            message = "Véritable expertise avec humilité — profil d'expert accompli"
            recommendation = "Partagez vos connaissances avec les autres"
            color = "green"
        else:
            zone, zone_label = "expert_calibrated", "Expert Calibré"
            message = "Expertise élevée avec auto-évaluation précise — profil idéal"
            recommendation = "Explorez des défis plus avancés et mentoring"
            color = "green"

    overconfident_count  = sum(1 for q in per_question if q["dk_signal"] == "overconfident")
    underconfident_count = sum(1 for q in per_question if q["dk_signal"] == "underconfident")
    calibrated_count     = sum(1 for q in per_question if q["dk_signal"] == "calibrated")
    calibration_score    = round((calibrated_count / n) * 100, 1) if n > 0 else 0

    ml_profils    = [q["profil_ml"] for q in per_question if q["profil_ml"]]
    global_ml     = Counter(ml_profils).most_common(1)[0][0] if ml_profils else None
    ml_confs      = [q["confidence_ml"] for q in per_question if q["confidence_ml"]]
    global_ml_conf = round(sum(ml_confs) / len(ml_confs), 3) if ml_confs else None

    return {
        "dk_index": dk_index, "dk_index_observed": dk_index_obs,
        "zone": zone, "zone_label": zone_label,
        "message": message, "recommendation": recommendation, "color": color,
        "declared_confidence": round(avg_declared, 1),
        "observed_confidence": round(avg_observed, 1) if avg_observed is not None else None,
        "actual_score": round(score_percentage, 1),
        "calibration_score": calibration_score,
        "overconfident_count": overconfident_count,
        "underconfident_count": underconfident_count,
        "calibrated_count": calibrated_count,
        "per_question": per_question,
        "profil_ml": global_ml,
        "confidence_ml": global_ml_conf,
    }


@app.post("/generate-quiz")
def generate_quiz(req: QuestionRequest, num_questions: int = 5):
    session_id = str(uuid4())
    questions  = []
    for i in range(num_questions):
        prompt = f"""Génère une question de quiz à choix multiples en {req.subject} pour un niveau {req.level}. {req.user_info}

Format EXACT requis:
Question: [La question ici]
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Réponse correcte: [A, B, C ou D]
Explication: [Brève explication de la réponse]"""
        try:
            response = requests.post(OLLAMA_API_URL, json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False})
            response.raise_for_status()
            parsed = parse_quiz_response(response.json().get("response", ""))
            if parsed:
                questions.append({"id": str(uuid4()), **parsed})
        except Exception as e:
            print(f"Error Q{i+1}: {e}")
            continue

    if not questions:
        raise HTTPException(status_code=500, detail="Impossible de générer des questions")

    quiz_sessions[session_id] = {
        "questions": questions, "score": 0,
        "total_questions": len(questions), "answered": [],
        "behavioral_data": {}, "subject": req.subject
    }
    return {
        "session_id": session_id,
        "questions": [{"id": q["id"], "question": q["question"], "options": q["options"]} for q in questions],
        "total_questions": len(questions)
    }


@app.post("/session/{session_id}/photo")
async def receive_photo(session_id: str, request: dict):
    session = quiz_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    question_id  = request.get("question_id")
    moment       = request.get("moment")
    image_base64 = request.get("image")
    if not question_id or not image_base64:
        raise HTTPException(status_code=400, detail="question_id et image requis")

    analysis = analyze_photo(image_base64)

    if "behavioral_data" not in session:
        session["behavioral_data"] = {}
    if question_id not in session["behavioral_data"]:
        session["behavioral_data"][question_id] = {"photos": [], "confidence_observed_avg": 0.5}

    session["behavioral_data"][question_id]["photos"].append({
        "moment": moment,
        "emotions": analysis.get("emotions", {}),
        "dominant_emotion": analysis.get("dominant_emotion", "unknown"),
        "confidence_observed": analysis.get("confidence_observed", 0.5),
        "success": analysis.get("success", False)
    })

    photos = session["behavioral_data"][question_id]["photos"]
    scores = [p["confidence_observed"] for p in photos if p["success"]]
    if scores:
        session["behavioral_data"][question_id]["confidence_observed_avg"] = round(sum(scores) / len(scores), 3)

    print(f"📸 Photo — {session_id[:8]}, {question_id[:8]}, {moment}, {analysis.get('dominant_emotion')}, {analysis.get('confidence_observed')}")

    return {
        "success": True, "moment": moment,
        "dominant_emotion": analysis.get("dominant_emotion"),
        "confidence_observed": analysis.get("confidence_observed")
    }