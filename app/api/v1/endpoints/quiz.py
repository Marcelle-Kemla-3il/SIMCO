from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from app.core.database import get_db
from app.models.quiz import Quiz, QuizSession, Answer
from app.schemas.quiz import QuizGenerate, QuizResponse, AnswerSubmit, AnswerResponse, QuizSessionCreate, QuizSessionResponse, Question
from app.services.llm_service import llm_service
import json
import logging

router = APIRouter()

@router.post("/generate", response_model=List[QuizResponse])
async def generate_quiz(quiz_data: QuizGenerate, db: Session = Depends(get_db)):
    """Étape 1: Générer un questionnaire automatiquement"""
    try:
        # Generate questions using LLM
        questions = await llm_service.generate_quiz(
            subject=quiz_data.subject,
            level=quiz_data.level,
            num_questions=quiz_data.num_questions,
            topics=quiz_data.topics,
            country=quiz_data.country,
            force_refresh=bool(quiz_data.force_refresh)
        )
        
        # Create quiz in database
        quiz = Quiz(
            subject=quiz_data.subject,
            level=quiz_data.level,
            title=f"Quiz {quiz_data.subject} - Niveau {quiz_data.level}",
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
        
    except Exception as e:
        logging.error(f"Failed to generate quiz: {type(e).__name__}: {str(e)}")
        logging.error(f"Full error details: {repr(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du quiz: {str(e)}")

@router.post("/sessions", response_model=QuizSessionResponse)
async def create_session(session_data: QuizSessionCreate, db: Session = Depends(get_db)):
    """Créer une nouvelle session de quiz"""
    quiz = db.query(Quiz).filter(Quiz.id == session_data.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    session = QuizSession(
        quiz_id=session_data.quiz_id,
        student_id=session_data.student_id
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
    # Get session and quiz
    session = db.query(QuizSession).filter(QuizSession.id == answer_data.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    quiz = db.query(Quiz).filter(Quiz.id == session.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Get question and check answer
    if answer_data.question_index >= len(quiz.questions):
        raise HTTPException(status_code=400, detail="Invalid question index")
    
    question = quiz.questions[answer_data.question_index]
    
    # Normaliser la réponse sélectionnée (trim uniquement)
    clean_answer = answer_data.selected_answer.strip() if answer_data.selected_answer else ""
    # Comparer sur le texte complet des choix
    is_correct = clean_answer == question["correct_answer"]
    
    print(f"DEBUG: Original answer: {answer_data.selected_answer}, Clean answer: {clean_answer}, Correct answer: {question['correct_answer']}, Is correct: {is_correct}")
    
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
        db.commit()
        db.refresh(answer)
    except Exception as e:
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
        correct_answer=question["correct_answer"],
        explanation=question.get("explanation"),
        confidence_analysis=confidence_analysis,
        selected_answer=clean_answer
    )

@router.get("/sessions/{session_id}", response_model=QuizSessionResponse)
async def get_session(session_id: int, db: Session = Depends(get_db)):
    """Obtenir les détails d'une session"""
    session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    quiz = db.query(Quiz).filter(Quiz.id == session.quiz_id).first()
    answers = db.query(Answer).filter(Answer.session_id == session_id).all()
    
    # Calculate score
    if answers:
        correct_answers = sum(1 for a in answers if a.is_correct)
        score = correct_answers / len(answers)
    else:
        score = None
    
    return QuizSessionResponse(
        id=session.id,
        quiz_id=session.quiz_id,
        student_id=session.student_id,
        started_at=session.started_at,
        completed_at=session.completed_at,
        total_questions=len(quiz.questions) if quiz else 0,
        answered_questions=len(answers),
        score=score
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
