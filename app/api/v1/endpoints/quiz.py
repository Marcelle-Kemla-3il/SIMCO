from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from typing import List, Optional, Union
from app.core.database import get_db
from app.models.quiz import Quiz, QuizSession, Answer, EmotionEvent
from app.schemas.quiz import QuizGenerate, QuizResponse, AnswerSubmit, AnswerResponse, QuizSessionCreate, QuizSessionResponse, Question
from app.services.llm_service import llm_service
from app.core.config import settings
import logging
import io
import os
import re

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:
    plt = None

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
except Exception:
    canvas = None

router = APIRouter()


def _questions_uniqueness_ratio(qs):
    try:
        if not qs:
            return 0.0
        keys = []
        for q in qs:
            if not isinstance(q, dict):
                continue
            t = str(q.get("question") or "").strip().lower()
            t = re.sub(r"\s+", " ", t)
            if t:
                keys.append(t)
        if not keys:
            return 0.0
        return len(set(keys)) / float(len(keys))
    except Exception:
        return 0.0


def _avg(values: List[Optional[float]]):
    vals = [float(v) for v in values if isinstance(v, (int, float))]
    return (sum(vals) / len(vals)) if vals else None


def _median(values: List[Optional[float]]):
    vals = sorted([float(v) for v in values if isinstance(v, (int, float))])
    if not vals:
        return None
    mid = len(vals) // 2
    if len(vals) % 2 == 1:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2.0


def _std(values: List[Optional[float]]):
    vals = [float(v) for v in values if isinstance(v, (int, float))]
    if len(vals) < 2:
        return None
    m = sum(vals) / len(vals)
    var = sum((v - m) ** 2 for v in vals) / (len(vals) - 1)
    return var ** 0.5


def _clamp01(x: Optional[float]):
    if x is None:
        return None
    try:
        v = float(x)
    except Exception:
        return None
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _default_confidence(x: Optional[float], default: float = 0.5) -> float:
    v = _clamp01(x)
    return float(default) if v is None else float(v)


def _build_recommendations(score_pct: float, declared_pct: Optional[float], observed_pct: Optional[float], time_ms_avg: Optional[float]):
    recs = []
    if score_pct < 50:
        recs.append("Revoir les notions fondamentales puis refaire un QCM similaire (objectif: +15 points).")
    elif score_pct < 70:
        recs.append("S'entraîner sur des exercices ciblés sur les erreurs du QCM (objectif: stabiliser au-dessus de 70%).")
    else:
        recs.append("Passer à des questions plus complexes et travailler la justification des réponses (explication à voix haute).")

    if declared_pct is not None:
        delta = declared_pct - score_pct
        if delta >= 20:
            recs.append("Travailler la calibration: après chaque question, noter 2 raisons qui justifient ta certitude (pour réduire la surconfiance).")
        elif delta <= -20:
            recs.append("Renforcer la confiance: conserver une trace des réussites et refaire les questions réussies sans aide (pour réduire l'auto-dévalorisation).")

    if observed_pct is not None and declared_pct is not None:
        if declared_pct >= 70 and observed_pct <= 50:
            recs.append("La confiance déclarée est élevée mais les signaux non-verbaux sont bas: faire une pause de 10s avant de valider et relire la question.")

    if time_ms_avg is not None:
        if time_ms_avg < 6000:
            recs.append("Rythme très rapide: ajouter une étape de vérification systématique (relire l'énoncé + éliminer 1 option).")
        elif time_ms_avg > 45000:
            recs.append("Temps très élevé: s'entraîner en condition chronométrée avec des séries courtes et corriger immédiatement.")

    return recs[:6]


def _severity_label(delta_pct: Optional[float]):
    if delta_pct is None:
        return "faible"
    d = abs(float(delta_pct))
    if d < 10:
        return "faible"
    if d < 20:
        return "modéré"
    return "élevé"


def _plot_bars_per_question(correct_flags: List[bool], declared: List[Optional[float]], observed: List[Optional[float]]):
    if plt is None:
        return None
    try:
        import math

        n = max(len(correct_flags), len(declared), len(observed))
        xs = list(range(1, n + 1))
        declared2 = [float("nan") if v is None else float(v) for v in declared[:n]]
        observed2 = [float("nan") if v is None else float(v) for v in observed[:n]]
        score2 = [1.0 if (i < len(correct_flags) and correct_flags[i]) else 0.0 for i in range(n)]

        fig = plt.figure(figsize=(7.0, 3.2), dpi=160)
        ax = fig.add_subplot(111)
        ax.bar(xs, score2, alpha=0.25, label="Réponse correcte (1=oui)")
        ax.plot(xs[:len(declared2)], declared2, marker="o", linewidth=1.5, label="Confiance déclarée")
        ax.plot(xs[:len(observed2)], observed2, marker="o", linewidth=1.5, label="Confiance observée")
        ax.set_ylim(0.0, 1.05)
        ax.set_xlabel("Question")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="upper right", fontsize=8)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception:
        return None


def _plot_time_hist(times_ms: List[Optional[float]]):
    if plt is None:
        return None
    try:
        vals = [float(v) / 1000.0 for v in times_ms if isinstance(v, (int, float)) and v >= 0]
        if not vals:
            return None
        fig = plt.figure(figsize=(7.0, 3.0), dpi=160)
        ax = fig.add_subplot(111)
        ax.hist(vals, bins=min(12, max(3, int(len(vals) ** 0.5) + 2)), alpha=0.85)
        ax.set_xlabel("Temps de réponse (secondes)")
        ax.set_ylabel("Nombre de questions")
        ax.grid(True, alpha=0.25)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception:
        return None


def _plot_emotion_pie(by_emotion: dict):
    if plt is None:
        return None
    try:
        if not by_emotion:
            return None
        labels = []
        sizes = []
        for k, v in sorted(by_emotion.items(), key=lambda kv: kv[1], reverse=True)[:6]:
            labels.append(str(k))
            sizes.append(int(v))
        if not sizes:
            return None
        fig = plt.figure(figsize=(6.4, 3.2), dpi=160)
        ax = fig.add_subplot(111)
        ax.pie(sizes, labels=labels, autopct="%1.0f%%", textprops={"fontsize": 8})
        ax.set_title("Répartition des émotions (top 6)", fontsize=10)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception:
        return None


def _safe_float(x):
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _detect_biases(score_pct: float, declared_avg: float, observed_avg: float):
    """Rule-based bias detection (production-safe, deterministic).

    Inputs are percentages in [0..100]. The function returns a stable structure:
    - flags: boolean detections
    - severity: low/medium/high
    - metrics: deltas between signals
    - notes: short actionable narrative
    """
    sp = float(score_pct or 0.0)
    dp = float(declared_avg or 50.0)
    op = float(observed_avg or 50.0)

    delta_declared = dp - sp
    delta_observed = op - sp
    delta_declared_vs_observed = dp - op

    def _sev(d: float) -> str:
        a = abs(float(d))
        if a < 10:
            return "low"
        if a < 20:
            return "medium"
        return "high"

    dk = delta_declared >= 20.0
    imp = delta_declared <= -20.0

    notes = []
    if dk:
        notes.append("Surconfiance probable: la confiance déclarée dépasse nettement la performance.")
        if op < 45.0:
            notes.append("Signal non-verbal faible: la confiance observée ne confirme pas la certitude déclarée.")
    elif imp:
        notes.append("Sous-confiance probable: la confiance déclarée est nettement inférieure à la performance.")
        if op < 45.0:
            notes.append("Signal non-verbal bas: possible anxiété malgré de bonnes réponses.")
    else:
        # Calibration issues even without strong bias
        if abs(delta_declared) >= 10.0:
            notes.append("Calibration à améliorer: confiance déclarée éloignée de la performance.")
        else:
            notes.append("Calibration globalement cohérente entre confiance déclarée et performance.")

    # Always add a small action item
    notes.append("Action: après chaque question, noter une probabilité de réussite (0-100%) puis comparer au corrigé pour recalibrer.")

    return {
        "flags": {
            "dunning_kruger": bool(dk),
            "impostor": bool(imp),
        },
        "severity": {
            "declared_vs_score": _sev(delta_declared),
            "observed_vs_score": _sev(delta_observed),
        },
        "metrics": {
            "score_pct": sp,
            "declared_pct": dp,
            "observed_pct": op,
            "delta_declared_vs_score": float(delta_declared),
            "delta_observed_vs_score": float(delta_observed),
            "delta_declared_vs_observed": float(delta_declared_vs_observed),
        },
        "notes": notes[:8],
    }


def _plot_confidence_curves(declared: List[Optional[float]], observed: List[Optional[float]]):
    if plt is None:
        return None
    try:
        xs = list(range(1, max(len(declared), len(observed)) + 1))
        yd = [(_safe_float(v) if v is not None else None) for v in declared]
        yo = [(_safe_float(v) if v is not None else None) for v in observed]

        # Replace None with NaN to create gaps
        import math
        yd2 = [float("nan") if v is None else float(v) for v in yd]
        yo2 = [float("nan") if v is None else float(v) for v in yo]

        fig = plt.figure(figsize=(7.0, 3.2), dpi=160)
        ax = fig.add_subplot(111)
        ax.plot(xs[:len(yd2)], yd2, marker="o", linewidth=1.6, label="Confiance déclarée (0-1)")
        ax.plot(xs[:len(yo2)], yo2, marker="o", linewidth=1.6, label="Confiance observée (0-1)")
        ax.set_ylim(0.0, 1.0)
        ax.set_xlabel("Question")
        ax.set_ylabel("Confiance")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="lower right", fontsize=8)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception:
        return None

@router.post("/generate", response_model=List[QuizResponse])
async def generate_quiz(quiz_data: QuizGenerate, db: Session = Depends(get_db)):
    """Étape 1: Générer un questionnaire automatiquement"""
    try:
        effective_level = quiz_data.level
        if getattr(quiz_data, "class_level", None):
            effective_level = f"{quiz_data.level} - {quiz_data.class_level}"

        # Generate questions using LLM
        questions = await llm_service.generate_quiz(
            subject=quiz_data.subject,
            level=effective_level,
            num_questions=quiz_data.num_questions,
            topics=quiz_data.topics,
            country=quiz_data.country,
            force_refresh=bool(quiz_data.force_refresh),
            sector=getattr(quiz_data, "sector", None),
            difficulty=getattr(quiz_data, "difficulty", None),
            use_llm=True,
        )
        
        # Create quiz in database
        quiz = Quiz(
            subject=quiz_data.subject,
            level=effective_level,
            title=f"Quiz {quiz_data.subject} - Niveau {effective_level}",
            questions=questions
        )
        db.add(quiz)
        db.commit()
        db.refresh(quiz)
        
        return [QuizResponse(
            id=quiz.id,
            subject=quiz.subject,
            level=quiz.level,
            title=quiz.title,
            questions=[Question(**q) for q in questions],
            created_at=quiz.created_at
        )]
        
    except ValueError as e:
        # Strict generation errors: expose a clean, actionable message.
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logging.error(f"Failed to generate quiz: {type(e).__name__}: {str(e)}")
        logging.error(f"Full error details: {repr(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du quiz: {str(e)}")


@router.post("/generate/test")
async def generate_quiz_test(quiz_data: QuizGenerate):
    """Endpoint de test: génère des questions sans écrire en base.

    Retourne des métriques (provider, ratio d'unicité) + un échantillon.
    """
    try:
        effective_level = quiz_data.level
        if getattr(quiz_data, "class_level", None):
            effective_level = f"{quiz_data.level} - {quiz_data.class_level}"

        questions = await llm_service.generate_quiz(
            subject=quiz_data.subject,
            level=effective_level,
            num_questions=quiz_data.num_questions,
            topics=quiz_data.topics,
            country=quiz_data.country,
            force_refresh=bool(quiz_data.force_refresh),
            sector=getattr(quiz_data, "sector", None),
            difficulty=getattr(quiz_data, "difficulty", None),
            use_llm=True,
        )

        provider = str(getattr(settings, "LLM_PROVIDER", "") or "").strip().lower()
        model = (
            str(getattr(settings, "MISTRAL_MODEL", "") or "").strip()
            if provider == "mistral"
            else str(getattr(settings, "OLLAMA_MODEL", "") or "").strip()
        )
        uniq_ratio = _questions_uniqueness_ratio(list(questions or []))

        # Small, safe payload back to client
        sample = []
        for q in (questions or [])[: min(5, len(questions or []))]:
            if not isinstance(q, dict):
                continue
            sample.append(
                {
                    "question": q.get("question"),
                    "choices": q.get("choices"),
                    "correct_answer": q.get("correct_answer"),
                    "difficulty": q.get("difficulty"),
                }
            )

        return {
            "ok": True,
            "provider": provider,
            "model": model,
            "count": len(questions or []),
            "unique_ratio": uniq_ratio,
            "sample": sample,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération test: {type(e).__name__}: {str(e)}")

@router.post("/sessions", response_model=QuizSessionResponse)
async def create_session(session_data: QuizSessionCreate, db: Session = Depends(get_db)):
    """Créer une nouvelle session de quiz"""
    quiz = db.query(Quiz).filter(Quiz.id == session_data.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # If the same person (same email) requests a new session, reuse the most recent
    # session for that email (and same quiz), so their history is kept together.
    if getattr(session_data, "user_email", None):
        email = str(session_data.user_email).strip().lower()
        if email:
            existing = (
                db.query(QuizSession)
                .filter(QuizSession.user_email == email)
                .filter(QuizSession.quiz_id == session_data.quiz_id)
                .order_by(QuizSession.started_at.desc())
                .first()
            )
            if existing:
                return QuizSessionResponse(
                    id=existing.id,
                    quiz_id=existing.quiz_id,
                    student_id=existing.student_id,
                    started_at=existing.started_at,
                    completed_at=existing.completed_at,
                    total_questions=len(quiz.questions),
                    answered_questions=len(existing.answers or []),
                    score=None,
                )
    
    session = QuizSession(
        quiz_id=session_data.quiz_id,
        student_id=session_data.student_id,
        user_name=session_data.user_name,
        user_email=getattr(session_data, "user_email", None),
        subject=session_data.subject,
        level=session_data.level,
        class_level=session_data.class_level
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return QuizSessionResponse(
        id=session.id,
        quiz_id=session.quiz_id,
        student_id=session.student_id,
        started_at=session.started_at,
        total_questions=len(quiz.questions),
        answered_questions=0
    )

@router.post("/submit", response_model=AnswerResponse)
async def submit_answer(answer_data: AnswerSubmit, db: Session = Depends(get_db)):
    """Soumettre une réponse et collecter les données"""
    try:
        db.execute("PRAGMA journal_mode=WAL;")
        db.execute("PRAGMA synchronous=NORMAL;")
        db.execute("PRAGMA busy_timeout=5000;")
    except Exception:
        pass

    # Get session and quiz
    session = db.query(QuizSession).filter(QuizSession.id == answer_data.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    quiz = db.query(Quiz).filter(Quiz.id == session.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Global declared confidence (post-test): accept question_index < 0
    is_global_confidence = bool(answer_data.question_index is not None and int(answer_data.question_index) < 0)

    question = None
    clean_answer = (answer_data.selected_answer or "").strip().upper()
    is_correct = False

    if not is_global_confidence:
        # Get question and check answer
        if answer_data.question_index >= len(quiz.questions):
            raise HTTPException(status_code=400, detail="Invalid question index")

        question = quiz.questions[answer_data.question_index]

        if clean_answer in {"1", "UN"}:
            clean_answer = "A"
        elif clean_answer in {"2", "DEUX"}:
            clean_answer = "B"
        elif clean_answer in {"3", "TROIS"}:
            clean_answer = "C"
        elif clean_answer in {"4", "QUATRE"}:
            clean_answer = "D"

        correct = str(question.get("correct_answer") or "").strip().upper()
        is_correct = clean_answer == correct
    
    # Save answer
    try:
        answer = Answer(
            session_id=answer_data.session_id,
            question_index=answer_data.question_index,
            selected_answer=clean_answer,
            confidence_level=answer_data.confidence_level,
            response_time_ms=answer_data.response_time_ms,
            is_correct=is_correct
        )
        db.add(answer)
        try:
            db.commit()
        except OperationalError as oe:
            db.rollback()
            try:
                db.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            except Exception:
                pass
            db.add(answer)
            db.commit()
        db.refresh(answer)
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"DEBUG: Error saving answer: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save answer: {str(e)}")
    
    # Get confidence analysis from LLM (simplifié pour éviter les erreurs)
    confidence_analysis = {
        "confidence_consistency": "Analyse simplifiée",
        "metacognitive_feedback": "Continuez à évaluer votre confiance",
        "bias_indicators": []
    }
    
    return AnswerResponse(
        id=answer.id,
        is_correct=is_correct,
        correct_answer=(question["correct_answer"] if isinstance(question, dict) else ""),
        explanation=(question.get("explanation") if isinstance(question, dict) else None),
        confidence_analysis=confidence_analysis,
        selected_answer=clean_answer
    )


@router.post("/send-email-report/{session_id}")
async def send_email_report(
    session_id: int,
    email: str = Query(..., description="Email address"),
    db: Session = Depends(get_db)
):
    """Envoyer le rapport de test par email"""
    try:
        # Get session and quiz data
        session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        quiz = db.query(Quiz).filter(Quiz.id == session.quiz_id).first()
        answers = db.query(Answer).filter(Answer.session_id == session_id).all()
        
        # Calculate results
        correct_count = len([a for a in answers if a.is_correct])
        total_count = len(answers)
        score_percentage = (correct_count / total_count * 100) if total_count > 0 else 0
        
        # Create email content
        email_content = f"""
        RAPPORT DE TEST SIMCO
        
        Utilisateur: {session.user_name}
        Email: {email}
        Matière: {session.subject}
        Niveau: {session.level}
        
        RÉSULTATS:
        • Score: {score_percentage:.1f}%
        • Questions correctes: {correct_count}/{total_count}
        • Date: {session.started_at.strftime('%d/%m/%Y %H:%M')}
        
        Test effectué avec succès !
        
        ---
        SIMCO - Système Intelligent de Monitoring Cognitif et Optimisation
        """
        
        # For now, just log the email (would need SMTP configuration for real sending)
        logging.info(f"Email report for session {session_id}:")
        logging.info(f"To: {email}")
        logging.info(f"Content: {email_content}")
        
        return {
            "success": True,
            "message": "Rapport envoyé par email avec succès",
            "email": email,
            "score": score_percentage,
            "test_completed": True
        }
        
    except Exception as e:
        logging.error(f"Error sending email report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'envoi de l'email: {str(e)}")


@router.get("/sessions/{session_id}/report")
async def get_session_report(session_id: int, db: Session = Depends(get_db)):
    session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    quiz = db.query(Quiz).filter(Quiz.id == session.quiz_id).first()
    answers = db.query(Answer).filter(Answer.session_id == session_id).order_by(Answer.question_index.asc()).all()
    events = db.query(EmotionEvent).filter(EmotionEvent.session_id == session_id).order_by(EmotionEvent.timestamp.asc()).all()

    quiz_answers = [a for a in answers if (a.question_index is not None and int(a.question_index) >= 0)]
    global_conf_answers = [a for a in answers if (a.question_index is not None and int(a.question_index) < 0)]

    total_answered = len(quiz_answers)
    correct_count = sum(1 for a in quiz_answers if a.is_correct)
    score_percentage = (correct_count / total_answered * 100.0) if total_answered else 0.0

    total_questions = len(quiz.questions) if quiz else 0

    # Confidence aggregation
    confidence_by_question = {i: [] for i in range(total_questions)}
    for ev in events:
        if ev.question_index is None:
            continue
        if not isinstance(ev.question_index, int):
            continue
        if ev.question_index < 0 or ev.question_index >= total_questions:
            continue
        if ev.confidence_score is None:
            continue
        try:
            confidence_by_question[ev.question_index].append(float(ev.confidence_score))
        except Exception:
            continue

    per_question_confidence = []
    confidence_vector_c = []
    for i in range(total_questions):
        vals = confidence_by_question.get(i) or []
        if vals:
            avg = sum(vals) / len(vals)
        else:
            avg = 0.5
        per_question_confidence.append({
            "question_index": i,
            "captures": len(vals),
            "confidence_avg": avg,
        })
        confidence_vector_c.append(avg)

    observed_vals_for_baseline = [v for v in confidence_vector_c if isinstance(v, (int, float))]
    overall_confidence_baseline = (sum(observed_vals_for_baseline) / len(observed_vals_for_baseline)) if observed_vals_for_baseline else None

    declared_vector_d = []
    for i in range(total_questions):
        declared_vector_d.append(None)
    for a in quiz_answers:
        if a.question_index is None:
            continue
        if a.question_index < 0 or a.question_index >= total_questions:
            continue
        declared_vector_d[a.question_index] = _safe_float(a.confidence_level)

    declared_vals = [v for v in declared_vector_d if isinstance(v, (int, float))]
    declared_avg = (sum(declared_vals) / len(declared_vals)) if declared_vals else 0.5

    # Prefer a single global declared confidence if provided (question_index < 0)
    global_declared = None
    if global_conf_answers:
        try:
            global_declared = _safe_float(global_conf_answers[-1].confidence_level)
        except Exception:
            global_declared = None

    if global_declared is None:
        global_declared = declared_avg

    observed_vals = [v for v in confidence_vector_c if isinstance(v, (int, float))]
    observed_avg = (sum(observed_vals) / len(observed_vals)) if observed_vals else 0.5

    declared_for_bias = global_declared if global_declared is not None else declared_avg
    biases = _detect_biases(
        score_percentage,
        (float(_default_confidence(declared_for_bias)) * 100.0),
        (float(_default_confidence(observed_avg)) * 100.0),
    )

    by_emotion = {}
    for ev in events:
        if not ev.dominant_emotion:
            continue
        em = str(ev.dominant_emotion).strip().lower()
        if em in {"n/a", "na", "none", "null"}:
            continue
        if (ev.faces_count is not None) and int(ev.faces_count) <= 0:
            continue
        by_emotion[em] = by_emotion.get(em, 0) + 1
    top_emotion = None
    if by_emotion:
        top_emotion = sorted(by_emotion.items(), key=lambda kv: kv[1], reverse=True)[0][0]

    # Simple narrative summary (rule-based)
    total_valid = sum(by_emotion.values())
    top_ratio = (by_emotion.get(top_emotion, 0) / total_valid) if (top_emotion and total_valid) else 0.0
    if not total_valid:
        emotion_comment = "Aucune émotion exploitable détectée (visage non détecté ou analyse indisponible)."
    else:
        if top_emotion in {"happy"}:
            tone = "globalement positif"
        elif top_emotion in {"neutral"}:
            tone = "globalement neutre"
        elif top_emotion in {"sad"}:
            tone = "plutôt triste"
        elif top_emotion in {"angry"}:
            tone = "plutôt tendu"
        elif top_emotion in {"fear"}:
            tone = "plutôt anxieux"
        elif top_emotion in {"surprise"}:
            tone = "marqué par la surprise"
        elif top_emotion in {"disgust"}:
            tone = "marqué par le dégoût"
        else:
            tone = f"dominé par '{top_emotion}'"

        dominance_txt = "très stable" if top_ratio >= 0.65 else "variable"
        emotion_comment = f"État émotionnel {tone} pendant le quiz (dominance {dominance_txt})."

    questions = quiz.questions if quiz else []
    answer_details = []
    for a in answers:
        # Never index with negatives (e.g. global declared confidence uses question_index < 0).
        q = (
            questions[a.question_index]
            if (isinstance(a.question_index, int) and a.question_index >= 0 and a.question_index < len(questions))
            else None
        )
        answer_details.append({
            "question_index": a.question_index,
            "question": (q.get("question") if isinstance(q, dict) else None),
            "selected_answer": a.selected_answer,
            "correct_answer": (q.get("correct_answer") if isinstance(q, dict) else None),
            "is_correct": bool(a.is_correct),
            "explanation": (q.get("explanation") if isinstance(q, dict) else None),
            "confidence_level": a.confidence_level,
            "response_time_ms": a.response_time_ms,
        })

    # Multimodal vector per question: X = (correct, declared_confidence, observed_confidence)
    multimodal_by_question = []
    correct_by_q = {i: 0 for i in range(total_questions)}
    declared_by_q = {i: 0.5 for i in range(total_questions)}
    observed_by_q = {i: 0.5 for i in range(total_questions)}

    for a in quiz_answers:
        try:
            qi = int(a.question_index)
        except Exception:
            continue
        if qi < 0 or qi >= total_questions:
            continue
        correct_by_q[qi] = 1 if bool(a.is_correct) else 0
        declared_by_q[qi] = _default_confidence(_safe_float(a.confidence_level))

    for i in range(total_questions):
        observed_by_q[i] = _default_confidence(_safe_float(confidence_vector_c[i] if i < len(confidence_vector_c) else None))

    for i in range(total_questions):
        x = [int(correct_by_q.get(i, 0)), float(declared_by_q.get(i, 0.5)), float(observed_by_q.get(i, 0.5))]
        multimodal_by_question.append({
            "question_index": i,
            "correct": x[0],
            "confidence_declared": x[1],
            "confidence_observed": x[2],
            "x": x,
        })

    emotion_timeline = [
        {
            "id": ev.id,
            "timestamp": ev.timestamp,
            "question_index": ev.question_index,
            "faces_count": ev.faces_count,
            "dominant_emotion": ev.dominant_emotion,
        }
        for ev in events
    ]

    return {
        "session": {
            "id": session.id,
            "quiz_id": session.quiz_id,
            "student_id": session.student_id,
            "user_name": session.user_name,
            "subject": session.subject,
            "level": session.level,
            "class_level": session.class_level,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
        },
        "quiz": {
            "id": quiz.id if quiz else None,
            "title": quiz.title if quiz else None,
            "total_questions": len(questions),
        },
        "results": {
            "answered": total_answered,
            "correct": correct_count,
            "score_percentage": score_percentage,
        },
        "confidence": {
            "per_question": per_question_confidence,
            "vector_c": confidence_vector_c,
            "overall_baseline": overall_confidence_baseline,
            "vector_d": declared_vector_d,
            "declared_avg": declared_avg,
            "declared_global": global_declared,
            "observed_avg": observed_avg,
        },
        "biases": biases,
        "multimodal": {
            "per_question": multimodal_by_question,
            "x_mean": [
                float(sum(v[0] for v in [m["x"] for m in multimodal_by_question]) / float(len(multimodal_by_question) or 1)),
                float(sum(v[1] for v in [m["x"] for m in multimodal_by_question]) / float(len(multimodal_by_question) or 1)),
                float(sum(v[2] for v in [m["x"] for m in multimodal_by_question]) / float(len(multimodal_by_question) or 1)),
            ],
        },
        "answers": answer_details,
        "emotions": {
            "events_count": len(events),
            "top_emotion": top_emotion,
            "top_emotion_ratio": top_ratio if total_valid else 0.0,
            "by_emotion": by_emotion,
            "comment": emotion_comment,
            "timeline": emotion_timeline,
        },
    }


@router.get("/sessions/{session_id}/report.pdf")
async def download_session_report_pdf(session_id: int, db: Session = Depends(get_db)):
    if canvas is None:
        raise HTTPException(
            status_code=501,
            detail="PDF generation is not available. Please install 'reportlab' in the backend venv.",
        )

    report = await get_session_report(session_id=session_id, db=db)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    s = report.get("session", {})
    r = report.get("results", {})
    emo = report.get("emotions", {})
    conf = report.get("confidence", {})
    biases = report.get("biases") or {}

    declared_global = conf.get("declared_global")
    declared_avg = conf.get("declared_avg")
    declared_for_display = declared_global if declared_global is not None else declared_avg
    declared_pct = float(_default_confidence(declared_for_display)) * 100.0
    observed_avg = conf.get("observed_avg")
    observed_pct = float(_default_confidence(observed_avg)) * 100.0
    score_pct = float(r.get("score_percentage") or 0.0)

    quiz_answers = [a for a in report.get("answers", []) if (a.get("question_index") is not None and int(a.get("question_index")) >= 0)]
    correct_flags = [bool(a.get("is_correct")) for a in quiz_answers]
    times_ms = [a.get("response_time_ms") for a in quiz_answers]
    time_ms_avg = _avg(times_ms)
    time_ms_med = _median(times_ms)
    time_ms_std = _std(times_ms)

    declared_vector = conf.get("vector_d") or []
    observed_vector = conf.get("vector_c") or []
    declared_q_avg = _avg([v for v in declared_vector if v is not None])
    observed_q_avg = _avg([v for v in observed_vector if v is not None])

    calibration_delta = (declared_pct - score_pct) if (declared_pct is not None) else None
    observed_delta = (observed_pct - score_pct) if (observed_pct is not None) else None
    multimodal_gap = (declared_pct - observed_pct) if (declared_pct is not None and observed_pct is not None) else None

    recommendations = _build_recommendations(score_pct, declared_pct, observed_pct, time_ms_avg)

    def _footer(page_title: str):
        c.setFont("Helvetica", 9)
        c.setFillGray(0.35)
        c.drawString(50, 25, f"SIMCO — {page_title}")
        c.drawRightString(width - 50, 25, f"Session {s.get('id')} — Généré")
        c.setFillGray(0)

    def _section_title(y, title):
        c.setFont("Helvetica-Bold", 13)
        c.setFillGray(0)
        c.drawString(50, y, title)
        return y - 16

    def _wrap_text(text: str, max_len: int = 110):
        words = str(text or "").split()
        lines = []
        cur = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) + (1 if cur else 0) > max_len:
                lines.append(" ".join(cur))
                cur = [w]
                cur_len = len(w)
            else:
                cur.append(w)
                cur_len += len(w) + (1 if cur_len else 0)
        if cur:
            lines.append(" ".join(cur))
        return lines

    def _kpi_box(x, y, w, h, title, value):
        c.setStrokeGray(0.85)
        c.setFillGray(0.97)
        c.rect(x, y - h, w, h, stroke=1, fill=1)
        c.setFillGray(0)
        c.setFont("Helvetica", 9)
        c.drawString(x + 10, y - 18, str(title))
        c.setFont("Helvetica-Bold", 16)
        c.drawString(x + 10, y - 40, str(value))

    # PAGE 1 — Synthèse
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 60, "RAPPORT D'ÉVALUATION COGNITIVE MULTIMODALE")
    c.setFont("Helvetica", 11)
    c.setFillGray(0.2)
    c.drawString(50, height - 82, "SIMCO — Système Intégré de Monitoring Cognitif")
    c.setFillGray(0)

    y = height - 120
    c.setFont("Helvetica", 10)
    started_at = s.get("started_at")
    completed_at = s.get("completed_at")
    date_txt = ""
    try:
        if started_at:
            date_txt = started_at.strftime("%d/%m/%Y %H:%M")
    except Exception:
        date_txt = str(started_at or "")

    c.drawString(50, y, f"Nom/ID étudiant: {s.get('user_name') or s.get('student_id') or ''}")
    y -= 14
    c.drawString(50, y, f"Date de l'évaluation: {date_txt}")
    y -= 14
    c.drawString(50, y, f"Contexte: QCM + analyse non-verbale (expressions faciales)")
    y -= 14
    c.drawString(50, y, f"Session: {s.get('id')} — Matière: {s.get('subject') or ''} — Niveau: {s.get('level') or ''}")

    y -= 26
    kpi_y = y
    _kpi_box(50, kpi_y, 165, 65, "Score", f"{score_pct:.1f}%")
    _kpi_box(230, kpi_y, 165, 65, "Confiance déclarée", f"{declared_pct:.1f}%")
    _kpi_box(410, kpi_y, 165, 65, "Confiance observée", f"{observed_pct:.1f}%")

    y = kpi_y - 85
    y = _section_title(y, "1) Synthèse des résultats")
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Répartition: {int(r.get('correct') or 0)}/{int(r.get('answered') or 0)} correctes")
    y -= 14

    if calibration_delta is not None:
        c.drawString(50, y, f"Écart confiance déclarée − performance: {calibration_delta:+.1f} points (sévérité: {_severity_label(calibration_delta)})")
        y -= 14
    if observed_delta is not None:
        c.drawString(50, y, f"Écart confiance observée − performance: {observed_delta:+.1f} points")
        y -= 14
    if multimodal_gap is not None:
        c.drawString(50, y, f"Écart déclarée − observée: {multimodal_gap:+.1f} points")
        y -= 14

    if time_ms_avg is not None:
        y -= 4
        c.drawString(
            50,
            y,
            "Temps de réponse: "
            + (f"moyenne {time_ms_avg/1000.0:.1f}s" if time_ms_avg is not None else "")
            + (f", médiane {time_ms_med/1000.0:.1f}s" if time_ms_med is not None else "")
            + (f", dispersion {time_ms_std/1000.0:.1f}s" if time_ms_std is not None else ""),
        )
        y -= 14

    y -= 6
    y = _section_title(y, "2) Biais et signaux multimodaux")
    c.setFont("Helvetica", 10)
    notes = (biases.get("notes") or [])[:5]
    if not notes:
        notes = ["Aucun biais net détecté selon les règles actuelles."]
    for n in notes:
        for line in _wrap_text(f"- {n}", 105):
            c.drawString(50, y, line)
            y -= 12

    y -= 6
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Émotion dominante: {emo.get('top_emotion') or 'neutral'} — Captures: {emo.get('events_count', 0)}")
    y -= 14
    for line in _wrap_text(emo.get("comment") or "", 105)[:3]:
        c.drawString(50, y, line)
        y -= 12

    y -= 8
    y = _section_title(y, "3) Plan d'amélioration (priorités)")
    c.setFont("Helvetica", 10)
    for i, rec in enumerate(recommendations, start=1):
        for line in _wrap_text(f"{i}. {rec}", 105):
            c.drawString(50, y, line)
            y -= 12

    _footer("Synthèse")
    c.showPage()

    # PAGE 2 — Graphiques
    y = height - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Analyse visuelle")
    y -= 22
    c.setFont("Helvetica", 10)
    c.drawString(50, y, "Courbes et distributions issues des réponses et des signaux non-verbaux.")
    y -= 18

    if ImageReader is not None:
        buf1 = _plot_confidence_curves(conf.get("vector_d") or [], conf.get("vector_c") or [])
        buf2 = _plot_bars_per_question(correct_flags, conf.get("vector_d") or [], conf.get("vector_c") or [])
        buf3 = _plot_time_hist(times_ms)
        buf4 = _plot_emotion_pie(emo.get("by_emotion") or {})

        plots = [("Courbes de confiance", buf1), ("Correct / confiance par question", buf2), ("Distribution des temps", buf3), ("Émotions", buf4)]
        for title, buf in plots:
            if buf is None:
                continue
            if y < 160:
                _footer("Analyse visuelle")
                c.showPage()
                y = height - 60
                c.setFont("Helvetica-Bold", 16)
                c.drawString(50, y, "Analyse visuelle (suite)")
                y -= 30
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, title)
            y -= 10
            try:
                img = ImageReader(buf)
                c.drawImage(img, 50, y - 210, width=500, height=210, preserveAspectRatio=True, mask='auto')
                y -= 230
            except Exception:
                y -= 10

    _footer("Analyse visuelle")
    c.showPage()

    # PAGE 3+ — Détails des réponses
    y = height - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Détails des réponses")
    y -= 18
    c.setFont("Helvetica", 9)
    c.drawString(50, y, "Chaque question: résultat, choix, confiance et explication (si disponible).")
    y -= 18

    for a in quiz_answers:
        qidx = a.get("question_index")
        qnum = (int(qidx) + 1) if isinstance(qidx, int) else qidx
        ok = "Correct" if a.get("is_correct") else "Incorrect"
        sel = a.get("selected_answer")
        corr = a.get("correct_answer")
        conf_level = a.get("confidence_level")
        conf_pct = (float(conf_level) * 100.0) if isinstance(conf_level, (int, float)) else None
        rt = a.get("response_time_ms")
        rt_s = (float(rt) / 1000.0) if isinstance(rt, (int, float)) else None
        qtxt = a.get("question") or ""
        expl = a.get("explanation") or ""

        block = [
            f"Q{qnum} — {ok} | Choisi: {sel} | Attendu: {corr} | Confiance: {conf_pct:.0f}%" if conf_pct is not None else f"Q{qnum} — {ok} | Choisi: {sel} | Attendu: {corr}",
            (f"Temps: {rt_s:.1f}s" if rt_s is not None else ""),
            f"Énoncé: {qtxt}",
        ]
        if expl:
            block.append(f"Explication: {expl}")

        for line0 in block:
            if not line0:
                continue
            for line in _wrap_text(line0, 115):
                if y < 60:
                    _footer("Détails")
                    c.showPage()
                    y = height - 60
                    c.setFont("Helvetica", 9)
                c.drawString(50, y, line)
                y -= 11
        y -= 6

    _footer("Détails")
    c.showPage()
    c.save()
    buffer.seek(0)

    filename = f"simco_report_session_{session_id}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

@router.get("/sessions/{session_id}", response_model=QuizSessionResponse)
async def get_session(session_id: int, db: Session = Depends(get_db)):
    """Récupérer les détails d'une session"""
    session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    quiz = db.query(Quiz).filter(Quiz.id == session.quiz_id).first()
    answers = db.query(Answer).filter(Answer.session_id == session_id).all()
    
    return QuizSessionResponse(
        id=session.id,
        quiz_id=session.quiz_id,
        student_id=session.student_id,
        started_at=session.started_at,
        completed_at=session.completed_at,
        total_questions=len(quiz.questions) if quiz else 0,
        answered_questions=len(answers),
        score=sum(1 for a in answers if a.is_correct) / len(answers) * 100 if answers else None
    )

@router.post("/sessions/{session_id}/complete")
async def complete_session(session_id: int, db: Session = Depends(get_db)):
    """Marquer une session comme terminée"""
    session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    from datetime import datetime
    session.completed_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Session completed successfully"}


# Nouveau: progression d'un étudiant
@router.get("/students/{student_id}/progress")
async def get_student_progress(
    student_id: str,
    subject: Optional[str] = Query(default=None, description="Filtrer par matière"),
    db: Session = Depends(get_db)
):
    """Retourne la progression d'un étudiant (scores au fil du temps) et l'amélioration récente.
    Si 'subject' est fourni, ne considère que les sessions de cette matière."""
    # Récupérer les sessions de l'étudiant
    sessions = db.query(QuizSession).filter(QuizSession.student_id == student_id).order_by(QuizSession.started_at.asc()).all()
    if not sessions:
        return {
            "student_id": student_id,
            "total_sessions": 0,
            "message": "Aucune session trouvée pour cet utilisateur"
        }

    history = []
    for s in sessions:
        quiz = db.query(Quiz).filter(Quiz.id == s.quiz_id).first()
        if subject and quiz and quiz.subject != subject:
            continue
        answers = db.query(Answer).filter(Answer.session_id == s.id).all()
        if not answers:
            continue
        total = len(answers)
        correct = sum(1 for a in answers if a.is_correct)
        score = correct / total if total else None
        history.append({
            "session_id": s.id,
            "started_at": s.started_at,
            "subject": quiz.subject if quiz else None,
            "level": quiz.level if quiz else None,
            "score": score,
            "answered": total
        })

    if not history:
        return {
            "student_id": student_id,
            "total_sessions": 0,
            "message": "Aucune session exploitable (pas de réponses)"
        }

    # Calculs agrégés
    scores = [h["score"] for h in history if h["score"] is not None]
    last = scores[-1] if scores else None
    prev = scores[-2] if len(scores) > 1 else None
    delta = (last - prev) if (last is not None and prev is not None) else None
    improved = (delta is not None and delta > 0)

    return {
        "student_id": student_id,
        "subject": subject,
        "total_sessions": len(history),
        "last_score": last,
        "previous_score": prev,
        "delta": delta,
        "improved": improved,
        "best_score": max(scores) if scores else None,
        "average_score": (sum(scores) / len(scores)) if scores else None,
        "history": history
    }

