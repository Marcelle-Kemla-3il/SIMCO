from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Any
from app.core.database import get_db
from app.models.quiz import QuizSession, Answer
from app.services.agent_service_fast import fast_agent_service
import logging

router = APIRouter()

@router.post("/generate-qcm-instant")
async def generate_qcm_instant(
    session_id: int,
    num_questions: int = 10,
    difficulty: str = "adaptive",
    db: Session = Depends(get_db)
):
    """Génération ULTRA-RAPIDE de QCM sans LLM"""
    try:
        # Récupérer la session et les réponses
        session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        answers = db.query(Answer).filter(Answer.session_id == session_id).all()
        
        # Préparer les données pour l'analyse
        session_data = {
            'id': session.id,
            'subject': session.subject,
            'level': session.level,
            'user_name': session.user_name
        }
        
        answers_data = []
        for answer in answers:
            answers_data.append({
                'question_index': answer.question_index,
                'selected_option': answer.selected_answer,
                'is_correct': answer.is_correct,
                'response_time_ms': answer.response_time_ms
            })
        
        # Analyse rapide basique
        correct_count = len([a for a in answers_data if a.get('is_correct', False)])
        total_count = len(answers_data)
        score_percentage = (correct_count / total_count * 100) if total_count > 0 else 50
        
        analysis = {
            'score_percentage': score_percentage,
            'correct_answers': correct_count,
            'total_questions': total_count,
            'performance_by_topic': {
                session.subject: score_percentage
            }
        }
        
        user_profile = {
            'subject': session.subject,
            'level': session.level,
            'user_name': session.user_name
        }
        
        # Génération ultra-rapide
        qcm = await fast_agent_service.generate_personalized_qcm_fast(
            user_profile, analysis, num_questions, difficulty
        )
        
        return {
            "success": True,
            "qcm": qcm,
            "generation_info": {
                "method": "ultra_fast",
                "no_llm": True,
                "instant": True,
                "based_on_session": session_id
            },
            "session_info": {
                "subject": session.subject,
                "level": session.level,
                "score": score_percentage
            }
        }
        
    except Exception as e:
        logging.error(f"Error in instant QCM generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Instant QCM failed: {str(e)}")

@router.post("/generate-qcm-simple")
async def generate_qcm_simple(
    subject: str = "mathématiques",
    difficulty: str = "intermédiaire",
    num_questions: int = 10
):
    """Génération SIMPLE de QCM sans analyse"""
    try:
        # Profil minimal
        user_profile = {
            'subject': subject,
            'level': 'lycée',
            'user_name': 'utilisateur'
        }
        
        # Analyse basique
        analysis = {
            'score_percentage': 50,
            'performance_by_topic': {subject: 50}
        }
        
        # Génération instantanée
        qcm = await fast_agent_service.generate_personalized_qcm_fast(
            user_profile, analysis, num_questions, difficulty
        )
        
        return {
            "success": True,
            "qcm": qcm,
            "generation_info": {
                "method": "simple",
                "no_session_required": True,
                "instant": True
            }
        }
        
    except Exception as e:
        logging.error(f"Error in simple QCM generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Simple QCM failed: {str(e)}")
