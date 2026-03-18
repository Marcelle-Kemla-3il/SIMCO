from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import numpy as np
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime
import httpx

from pydantic import BaseModel

from app.core.database import get_db
from app.models.quiz import QuizSession, EmotionEvent
from app.core.config import settings

router = APIRouter()


EMOTIONS = ["happy", "neutral", "sad", "angry", "fear", "surprise", "disgust"]


class EmotionEventIn(BaseModel):
    emotions: Optional[Dict[str, Any]] = None


def _normalize_emotions_probs(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    if not raw or not isinstance(raw, dict):
        return None
    vals: Dict[str, float] = {}
    s = 0.0
    for k in EMOTIONS:
        try:
            v = float(raw.get(k, 0.0))
        except Exception:
            v = 0.0
        vals[k] = v
        s += v
    if s <= 1e-9:
        return {"happy": 0.0, "neutral": 1.0, "sad": 0.0, "angry": 0.0, "fear": 0.0, "surprise": 0.0, "disgust": 0.0}
    return {k: vals[k] / s for k in EMOTIONS}


def _confidence_from_probs(p: Optional[Dict[str, float]]) -> Optional[float]:
    if not p:
        return None
    score = 0.0
    score += 0.6 * float(p.get("happy", 0.0))
    score += 0.3 * float(p.get("neutral", 0.0))
    score -= 0.4 * float(p.get("fear", 0.0))
    score -= 0.3 * float(p.get("sad", 0.0))
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0
    return float(score)


@router.get("/ping")
async def ping_cv():
    # Prefer checking the external CV microservice when configured.
    if getattr(settings, "CV_SERVICE_URL", None):
        base = str(settings.CV_SERVICE_URL).rstrip("/")
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{base}/health", timeout=5.0)
            if r.status_code == 200:
                return {
                    "opencv": True,
                    "cv2_version": None,
                    "cv_service": True,
                    "cv_service_url": base,
                }
            return {
                "opencv": False,
                "cv2_version": None,
                "cv_service": False,
                "cv_service_url": base,
                "detail": f"CV service returned HTTP {r.status_code}",
            }
        except Exception as e:
            return {
                "opencv": False,
                "cv2_version": None,
                "cv_service": False,
                "cv_service_url": base,
                "detail": f"CV service unreachable: {str(e)}",
            }

    try:
        import cv2  # type: ignore
        return {"opencv": True, "cv2_version": getattr(cv2, "__version__", "unknown"), "cv_service": False}
    except Exception:
        return {"opencv": False, "cv2_version": None, "cv_service": False}


@router.post("/analyze-frame")
async def analyze_frame(file: UploadFile = File(...)):
    try:
        if getattr(settings, "CV_SERVICE_URL", None):
            base = str(settings.CV_SERVICE_URL).rstrip("/")
            content = await file.read()
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"{base}/cv/analyze-frame",
                    files={"file": (file.filename or "frame.jpg", content, file.content_type or "image/jpeg")},
                    timeout=30.0,
                )
            r.raise_for_status()
            return r.json()

        try:
            import cv2  # type: ignore
        except Exception as e:
            raise HTTPException(
                status_code=501,
                detail="OpenCV n'est pas disponible dans l'API (utilisez le microservice CV via CV_SERVICE_URL).",
            )

        content = await file.read()
        arr = np.frombuffer(content, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

        dominant_emotion = None
        emotions = None

        normalized = None
        confidence_score = None

        DeepFace = None
        if len(faces) > 0:
            try:
                try:
                    from deepface import DeepFace as _DeepFace
                    DeepFace = _DeepFace
                except Exception:
                    DeepFace = None

                if DeepFace is None:
                    raise RuntimeError("DeepFace unavailable")

                x, y, w, h = faces[0]
                face = img[y:y+h, x:x+w]
                result = DeepFace.analyze(face, actions=['emotion'], enforce_detection=False)
                # DeepFace can return list or dict
                if isinstance(result, list) and result:
                    result = result[0]
                emotions = result.get('emotion') if isinstance(result, dict) else None
                dominant_emotion = result.get('dominant_emotion') if isinstance(result, dict) else None
            except Exception:
                dominant_emotion = None
                emotions = None

        # UploadFile is multipart/form-data: no JSON body payload here.
        normalized = _normalize_emotions_probs(emotions)
        confidence_score = _confidence_from_probs(normalized)

        return {
            "faces_count": int(len(faces)),
            "faces": [
                {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
                for (x, y, w, h) in faces
            ],
            "deepface_available": DeepFace is not None,
            # Keep API stable for the frontend: never return N/A/None emotions.
            "dominant_emotion": (str(dominant_emotion).strip().lower() if dominant_emotion else "neutral"),
            "emotions": (
                normalized
                if isinstance(normalized, dict) and any(float(normalized.get(k, 0.0)) > 0.0 for k in EMOTIONS)
                else {"happy": 0.0, "neutral": 1.0, "sad": 0.0, "angry": 0.0, "fear": 0.0, "surprise": 0.0, "disgust": 0.0}
            ),
            "confidence_score": (confidence_score if isinstance(confidence_score, (int, float)) else 0.5),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Frame analysis failed: {str(e)}")


@router.post("/event")
async def create_emotion_event(
    session_id: int,
    question_index: Optional[int] = None,
    faces_count: Optional[int] = None,
    dominant_emotion: Optional[str] = None,
    emotions: Optional[Dict[str, Any]] = None,
    payload: Optional[EmotionEventIn] = None,
    db: Session = Depends(get_db),
):
    try:
        session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
        if not session:
            # Best-effort: do not hard-fail the client if the session does not exist.
            normalized = {"happy": 0.0, "neutral": 1.0, "sad": 0.0, "angry": 0.0, "fear": 0.0, "surprise": 0.0, "disgust": 0.0}
            confidence_score = _confidence_from_probs(normalized)
            return {
                "ok": False,
                "stored": False,
                "detail": "Session not found",
                "session_id": session_id,
                "question_index": question_index,
                "faces_count": faces_count,
                "dominant_emotion": dominant_emotion,
                "confidence_score": confidence_score,
                "emotions": normalized,
            }

        raw_emotions = emotions
        if payload is not None and getattr(payload, "emotions", None) is not None:
            raw_emotions = payload.emotions

        normalized = _normalize_emotions_probs(raw_emotions)
        if normalized is None:
            normalized = {"happy": 0.0, "neutral": 1.0, "sad": 0.0, "angry": 0.0, "fear": 0.0, "surprise": 0.0, "disgust": 0.0}
        confidence_score = _confidence_from_probs(normalized)

        ev = EmotionEvent(
            session_id=session_id,
            question_index=question_index,
            faces_count=faces_count,
            dominant_emotion=dominant_emotion,
            emotions=normalized,
            confidence_score=confidence_score,
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)
        return {
            "ok": True,
            "stored": True,
            "id": ev.id,
            "session_id": ev.session_id,
            "question_index": ev.question_index,
            "timestamp": ev.timestamp,
            "faces_count": ev.faces_count,
            "dominant_emotion": ev.dominant_emotion,
            "confidence_score": ev.confidence_score,
            "emotions": ev.emotions,
        }
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to save emotion event: {str(e)}")
