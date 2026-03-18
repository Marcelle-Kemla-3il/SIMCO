from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
from app.core.database import get_db
from app.models.quiz import QuizSession, Answer
from app.services.agent_service_fast import fast_agent_service
import logging

router = APIRouter()

@router.post("/analyze-results")
async def analyze_quiz_results(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Analyse complète des résultats du quiz avec l'agent intelligent"""
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
            'user_name': session.user_name,
            'started_at': session.started_at.isoformat() if getattr(session, "started_at", None) else None
        }
        
        answers_data = []
        for answer in answers:
            answers_data.append({
                'question_index': answer.question_index,
                'selected_option': answer.selected_answer,
                'is_correct': answer.is_correct,
                'response_time_ms': answer.response_time_ms,
                'confidence_level': answer.confidence_level
            })
        
        # Analyse avec le service ultra-rapide
        analysis = await fast_agent_service.analyze_quiz_results(session_data, answers_data)
        
        return {
            "success": True,
            "analysis": analysis,
            "session_info": session_data,
            "answers_count": len(answers_data)
        }
        
    except Exception as e:
        logging.error(f"Error in analyze_results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/generate-recommendations")
async def generate_recommendations(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Génère des recommandations personnalisées basées sur l'analyse"""
    try:
        # Récupérer la session et les réponses
        session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        answers = db.query(Answer).filter(Answer.session_id == session_id).all()
        
        # Préparer les données
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
        
        # Analyse d'abord
        analysis = await fast_agent_service.analyze_quiz_results(session_data, answers_data)
        
        # Puis recommandations
        user_profile = {
            'subject': session.subject,
            'level': session.level,
            'user_name': session.user_name
        }
        
        recommendations = await fast_agent_service.generate_personalized_recommendations(analysis, user_profile)
        
        return {
            "success": True,
            "recommendations": recommendations,
            "analysis_summary": {
                "score": analysis.get('score_percentage', 0),
                "weak_topics": analysis.get('performance_by_topic', {}),
                "main_issues": analysis.get('error_patterns', {})
            }
        }
        
    except Exception as e:
        logging.error(f"Error in generate_recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Recommendations failed: {str(e)}")

@router.post("/create-learning-plan")
async def create_learning_plan(
    session_id: int,
    duration_weeks: int = 4,
    db: Session = Depends(get_db)
):
    """Crée un plan d'apprentissage personnalisé"""
    try:
        # Récupérer la session et les réponses
        session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        answers = db.query(Answer).filter(Answer.session_id == session_id).all()
        
        # Préparer les données
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
        
        # Analyse et recommandations
        analysis = await fast_agent_service.analyze_quiz_results(session_data, answers_data)
        user_profile = {
            'subject': session.subject,
            'level': session.level,
            'user_name': session.user_name
        }
        recommendations = await fast_agent_service.generate_personalized_recommendations(analysis, user_profile)
        
        # Plan d'apprentissage
        learning_plan = await fast_agent_service.create_learning_plan(analysis, recommendations, duration_weeks)
        
        return {
            "success": True,
            "learning_plan": learning_plan,
            "duration_weeks": duration_weeks,
            "based_on_session": session_id,
            "creation_date": learning_plan.get('creation_date')
        }
        
    except Exception as e:
        logging.error(f"Error in create_learning_plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Learning plan failed: {str(e)}")

@router.post("/generate-personalized-qcm")
async def generate_personalized_qcm(
    session_id: int,
    num_questions: int = 10,
    difficulty: str = "adaptive",
    db: Session = Depends(get_db)
):
    """Génère un QCM personnalisé basé sur les performances"""
    try:
        # Récupérer la session et les réponses
        session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        answers = db.query(Answer).filter(Answer.session_id == session_id).all()
        
        # Préparer les données
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
        
        # Analyse pour la personnalisation
        analysis = await fast_agent_service.analyze_quiz_results(session_data, answers_data)
        
        user_profile = {
            'subject': session.subject,
            'level': session.level,
            'user_name': session.user_name,
            'previous_scores': []  # À implémenter avec l'historique
        }
        
        # Génération du QCM
        qcm = await fast_agent_service.generate_personalized_qcm(user_profile, analysis, num_questions, difficulty)
        
        return {
            "success": True,
            "qcm": qcm,
            "personalization_info": {
                "based_on_session": session_id,
                "difficulty_level": qcm.get('difficulty'),
                "target_topics": qcm.get('target_topics', []),
                "personalization_level": qcm.get('personalization_level', 'moyen')
            }
        }
        
    except Exception as e:
        logging.error(f"Error in generate_personalized_qcm: {str(e)}")
        raise HTTPException(status_code=500, detail=f"QCM generation failed: {str(e)}")

@router.get("/get-user-profile/{session_id}")
async def get_user_profile(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Récupère le profil utilisateur basé sur l'historique"""
    try:
        user_name = db.query(QuizSession.user_name).filter(QuizSession.id == session_id).scalar()
        if not user_name:
            raise HTTPException(status_code=404, detail="Session not found")

        sessions = db.query(QuizSession).filter(QuizSession.user_name == user_name).all()
        
        if not sessions:
            raise HTTPException(status_code=404, detail="User sessions not found")
        
        # Calculer les statistiques globales
        total_sessions = len(sessions)
        total_questions = 0
        correct_answers = 0
        subjects = set()
        
        for session in sessions:
            answers = db.query(Answer).filter(Answer.session_id == session.id).all()
            total_questions += len(answers)
            correct_answers += len([a for a in answers if a.is_correct])
            subjects.add(session.subject)
        
        average_score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        profile = {
            'user_name': sessions[0].user_name,
            'total_sessions': total_sessions,
            'total_questions_answered': total_questions,
            'total_correct_answers': correct_answers,
            'average_score': round(average_score, 2),
            'subjects_studied': list(subjects),
            'preferred_subject': max(set(subjects), key=list(subjects).count) if subjects else None,
            'creation_date': sessions[0].started_at.isoformat() if getattr(sessions[0], "started_at", None) else None,
            'last_activity': (
                max((s.started_at for s in sessions if getattr(s, "started_at", None)), default=None).isoformat()
                if sessions
                else None
            )
        }
        
        return {
            "success": True,
            "profile": profile
        }
        
    except Exception as e:
        logging.error(f"Error in get_user_profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Profile retrieval failed: {str(e)}")

@router.post("/get-learning-progress")
async def get_learning_progress(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Analyse les progrès d'apprentissage sur plusieurs sessions"""
    try:
        # Récupérer l'utilisateur et toutes ses sessions
        user_name = db.query(QuizSession.user_name).filter(QuizSession.id == session_id).scalar()
        if not user_name:
            raise HTTPException(status_code=404, detail="Session not found")
        
        sessions = db.query(QuizSession).filter(QuizSession.user_name == user_name).all()
        
        progress_data = []
        for session in sessions:
            answers = db.query(Answer).filter(Answer.session_id == session.id).all()
            correct_count = len([a for a in answers if a.is_correct])
            total_count = len(answers)
            score = (correct_count / total_count * 100) if total_count > 0 else 0
            
            progress_data.append({
                'session_id': session.id,
                'subject': session.subject,
                'level': session.level,
                'date': session.started_at.isoformat() if getattr(session, "started_at", None) else None,
                'score': round(score, 2),
                'correct_answers': correct_count,
                'total_questions': total_count
            })
        
        # Trier par date
        progress_data.sort(key=lambda x: x['date'] or '')
        
        # Calculer les tendances
        if len(progress_data) >= 2:
            recent_scores = [p['score'] for p in progress_data[-5:]]  # 5 dernières sessions
            trend = 'improving' if recent_scores[-1] > recent_scores[0] else 'declining' if recent_scores[-1] < recent_scores[0] else 'stable'
        else:
            trend = 'insufficient_data'
        
        return {
            "success": True,
            "progress": progress_data,
            "trend": trend,
            "total_sessions": len(progress_data),
            "average_score": round(sum(p['score'] for p in progress_data) / len(progress_data), 2) if progress_data else 0
        }
        
    except Exception as e:
        logging.error(f"Error in get_learning_progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Progress analysis failed: {str(e)}")
