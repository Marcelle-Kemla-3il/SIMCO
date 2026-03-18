from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func
import secrets
from typing import Any, Dict, List, Optional

from app.core.database import get_db
from app.core.config import settings
from app.models.quiz import QuizSession, Answer, EmotionEvent
from app.api.v1.endpoints.quiz import download_session_report_pdf

router = APIRouter()
security = HTTPBasic()


def _require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    admin_user = getattr(settings, "ADMIN_USERNAME", None)
    admin_pass = getattr(settings, "ADMIN_PASSWORD", None)

    if not admin_user or not admin_pass:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin credentials are not configured.",
        )

    user_ok = secrets.compare_digest(credentials.username or "", str(admin_user))
    pass_ok = secrets.compare_digest(credentials.password or "", str(admin_pass))

    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


@router.get("/sessions")
def admin_list_sessions(
    _: str = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    sessions = (
        db.query(QuizSession)
        .order_by(QuizSession.started_at.desc())
        .all()
    )

    # Aggregate answers and emotion events counts for quick overview.
    ans_counts = {
        sid: cnt
        for sid, cnt in (
            db.query(Answer.session_id, func.count(Answer.id))
            .group_by(Answer.session_id)
            .all()
        )
    }
    emo_counts = {
        sid: cnt
        for sid, cnt in (
            db.query(EmotionEvent.session_id, func.count(EmotionEvent.id))
            .group_by(EmotionEvent.session_id)
            .all()
        )
    }

    out: List[Dict[str, Any]] = []
    for s in sessions:
        out.append(
            {
                "id": s.id,
                "quiz_id": s.quiz_id,
                "student_id": s.student_id,
                "user_name": s.user_name,
                "user_email": getattr(s, "user_email", None),
                "subject": s.subject,
                "level": s.level,
                "class_level": s.class_level,
                "started_at": s.started_at,
                "completed_at": s.completed_at,
                "answers_count": int(ans_counts.get(s.id, 0)),
                "emotion_events_count": int(emo_counts.get(s.id, 0)),
            }
        )

    return out


@router.get("/sessions/{session_id}/report.pdf")
async def admin_download_report_pdf(
    session_id: int,
    _: str = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    # Reuse the existing report generator.
    return await download_session_report_pdf(session_id=session_id, db=db)


@router.delete("/sessions/{session_id}")
def admin_delete_session(
    session_id: int,
    _: str = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Delete children first to avoid FK constraint issues.
    db.query(EmotionEvent).filter(EmotionEvent.session_id == session_id).delete(synchronize_session=False)
    db.query(Answer).filter(Answer.session_id == session_id).delete(synchronize_session=False)
    db.delete(session)
    db.commit()

    return {"deleted": True, "session_id": session_id}
