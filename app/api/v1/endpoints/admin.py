from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from app.core.database import get_db
from app.models.quiz import QuizSession, Answer
from app.models.cognitive import FacialAnalysis, CognitiveProfile
from app.services.ml_service import ml_service
from app.core.config import settings

router = APIRouter()


def _aggregate_session_features(db: Session, session_id: int) -> Optional[Dict[str, Any]]:
    """Build one training sample from a session by aggregating answers and facial analyses."""
    session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
    if not session:
        return None

    answers: List[Answer] = db.query(Answer).filter(Answer.session_id == session_id).all()
    if not answers:
        # Not enough data
        return None

    # Performance metrics
    total = len(answers)
    correct = sum(1 for a in answers if a.is_correct)
    actual_performance = correct / total if total > 0 else 0.0

    # Confidence
    declared_confidence = sum(a.confidence_level for a in answers) / total if total > 0 else 0.0

    # Response time
    avg_response_time = sum((a.response_time_ms or 0) for a in answers) / total if total > 0 else 0.0

    # Confidence variance
    conf_vals = [a.confidence_level for a in answers]
    mean_conf = declared_confidence
    confidence_variance = sum((c - mean_conf) ** 2 for c in conf_vals) / total if total > 0 else 0.0

    # Facial analyses (joined by answer)
    facials: List[FacialAnalysis] = []
    for a in answers:
        f = db.query(FacialAnalysis).filter(FacialAnalysis.answer_id == a.id).first()
        if f:
            facials.append(f)

    if facials:
        attention_avg = sum((f.attention_level or 0.5) for f in facials) / len(facials)
        eye_contact_avg = sum((f.eye_contact or 0.5) for f in facials) / len(facials)
        observed_confidence = sum((f.observed_confidence or declared_confidence) for f in facials) / len(facials)
    else:
        # Fallback
        attention_avg = 0.6
        eye_contact_avg = 0.6
        observed_confidence = declared_confidence

    # Labels if available (from cognitive profile), else derive simple labels
    profile = db.query(CognitiveProfile).filter(CognitiveProfile.session_id == session_id).first()
    if profile:
        profile_type = profile.cognitive_profile_type
        risk_level = profile.risk_level
    else:
        # Simple heuristic labels
        gap = abs(declared_confidence - actual_performance)
        if actual_performance < 0.5 and declared_confidence > 0.7:
            profile_type = "dunning-kruger"
        elif actual_performance > 0.7 and declared_confidence < 0.5:
            profile_type = "impostor"
        elif gap < 0.2:
            profile_type = "accurate"
        else:
            profile_type = "uncertain"

        if gap > 0.4:
            risk_level = "high"
        elif gap > 0.3:
            risk_level = "medium"
        else:
            risk_level = "low"

    return {
        "actual_performance": actual_performance,
        "declared_confidence": declared_confidence,
        "observed_confidence": observed_confidence,
        "answers_count": total,
        "avg_response_time": avg_response_time,
        "confidence_variance": confidence_variance,
        "attention_avg": attention_avg,
        "eye_contact_avg": eye_contact_avg,
        "profile_type": profile_type,
        "risk_level": risk_level,
    }


@router.get("/status")
def get_models_status() -> Dict[str, Any]:
    """Return status of cognitive models (trained flag and artifact presence)."""
    model_file = Path(settings.MODEL_PATH) / "cognitive_models.pkl"
    return {
        "models_trained": ml_service.models_trained,
        "model_file_exists": model_file.exists(),
        "model_file_path": str(model_file),
        "note": "Rule-based fallback is used if not trained. Use /admin/train to train from DB."
    }


@router.post("/train")
def train_from_database(
    min_sessions: int = Query(5, ge=1, description="Nombre minimal de sessions pour entraîner"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Train cognitive models from database data (sessions, answers, facial analyses)."""
    # Collect candidate session ids (those with at least one answer)
    session_ids = [s.id for s in db.query(QuizSession).all()]

    training_data: List[Dict[str, Any]] = []
    for sid in session_ids:
        sample = _aggregate_session_features(db, sid)
        if sample:
            training_data.append(sample)

    if len(training_data) < max(min_sessions, 10):
        raise HTTPException(status_code=400, detail=f"Données insuffisantes pour entraîner (actuel={len(training_data)}, requis>= {max(min_sessions, 10)})")

    # Train models
    ml_service.train_models(training_data)

    return {
        "ok": True,
        "trained": ml_service.models_trained,
        "samples_used": len(training_data),
        "message": "Modèles entraînés et sauvegardés (cognitive_models.pkl)"
    }
