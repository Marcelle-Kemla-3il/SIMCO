from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.quiz import QuizSession, Answer
from app.models.cognitive import FacialAnalysis, CognitiveProfile, Report
from app.schemas.cognitive import (
    FacialAnalysisRequest, FacialAnalysisResponse,
    CognitiveProfileResponse, ReportRequest, ReportResponse
)
from app.services.vision_service import vision_service
from app.services.llm_service import llm_service
from app.services.ml_service import ml_service
from app.services.email_service import email_service
import json
from datetime import datetime

router = APIRouter()

@router.post("/facial-analysis", response_model=FacialAnalysisResponse)
async def analyze_facial_features(
    request: FacialAnalysisRequest, 
    db: Session = Depends(get_db)
):
    """Étape 3: Extraire et persister les caractéristiques faciales liées à une réponse."""
    # Get answer
    answer = db.query(Answer).filter(Answer.id == request.answer_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    # Analyze facial features
    if request.image_frames and len(request.image_frames) > 0:
        # Prendre la première frame (base64) et l'analyser
        import base64
        frame_b64 = request.image_frames[0]
        try:
            image_bytes = base64.b64decode(frame_b64.split(',')[1] if ',' in frame_b64 else frame_b64)
        except Exception:
            image_bytes = b""
        features = vision_service.analyze_facial_expression(image_bytes)
    else:
        # Default values if no image provided
        features = {
            "emotions": {"neutral": 1.0},
            "eye_contact": 0.5,
            "attention_level": 0.5,
            "confidence": 0.5
        }

    # Calculate confidence discrepancy
    declared_confidence = db.query(Answer).filter(Answer.id == request.answer_id).first().confidence_level if request.answer_id else 0.5
    observed_confidence = features.get("confidence", features.get("observed_confidence", 0.5))
    confidence_discrepancy = abs(declared_confidence - observed_confidence)

    # Save facial analysis
    facial_analysis = FacialAnalysis(
        answer_id=request.answer_id,
        emotions=features.get("emotions"),
        facial_expressions=features.get("facial_expressions"),
        eye_contact=features.get("eye_contact"),
        attention_level=features.get("attention_level"),
        observed_confidence=observed_confidence,
        confidence_discrepancy=confidence_discrepancy,
        video_path=request.video_path
    )
    db.add(facial_analysis)
    db.commit()
    db.refresh(facial_analysis)

    # Generate analysis summary
    analysis_summary = f"Confiance déclarée: {declared_confidence:.2f}, Confiance observée: {observed_confidence:.2f}"
    if confidence_discrepancy > 0.3:
        analysis_summary += " - Discrepance importante détectée"

    return FacialAnalysisResponse(
        id=facial_analysis.id,
        observed_confidence=observed_confidence,
        confidence_discrepancy=confidence_discrepancy,
        emotions=features.get("emotions", {}),
        attention_level=features.get("attention_level", 0.5),
        analysis_summary=analysis_summary
    )

@router.post("/send-results")
async def send_results_by_email(
    session_id: int = Query(..., description="ID de la session"),
    email: str = Query(..., description="Adresse email du destinataire"),
    db: Session = Depends(get_db)
):
    """Génère le PDF du rapport et l'envoie par email au destinataire."""
    try:
        from app.services.pdf_service import pdf_service
        from app.services.comprehensive_analysis import comprehensive_analysis_service
        from fastapi import BackgroundTasks
        
        # Récupérer session et réponses
        session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        answers = db.query(Answer).filter(Answer.session_id == session_id).all()
        if not answers:
            raise HTTPException(status_code=400, detail="No answers for this session")
        
        # Récupérer facial analyses
        facial_analysis_data = []
        for answer in answers:
            facial = db.query(FacialAnalysis).filter(FacialAnalysis.answer_id == answer.id).first()
            if facial:
                facial_analysis_data.append(facial)
        facial_features = None
        if facial_analysis_data:
            facial_features = {
                "confidence": sum(f.observed_confidence or 0.5 for f in facial_analysis_data) / len(facial_analysis_data),
                "stress": 1 - sum(f.attention_level or 0.5 for f in facial_analysis_data) / len(facial_analysis_data),
                "engagement": sum(f.eye_contact or 0.5 for f in facial_analysis_data) / len(facial_analysis_data)
            }
        
        # Global confidence
        global_confidence = sum(a.confidence_level for a in answers) / len(answers)
        
        # Convert answers
        answers_data = [
            {
                "question_index": a.question_index,
                "selected_answer": a.selected_answer,
                "confidence_level": a.confidence_level,
                "response_time_ms": a.response_time_ms,
                "is_correct": a.is_correct,
            }
            for a in answers
        ]
        
        # Rapport et PDF
        comprehensive_report = comprehensive_analysis_service.generate_comprehensive_report(
            answers_data, 
            [],  # time-series not required for PDF visuals
            global_confidence
        )
        correct_answers = sum(1 for a in answers if a.is_correct)
        total_answers = len(answers)
        calculated_score = correct_answers / total_answers if total_answers else 0
        session_data = {
            "id": session.id,
            "student_id": session.student_id,
            "score": calculated_score,
            "answered_questions": correct_answers,
            "total_questions": total_answers,
        }
        pdf_bytes = pdf_service.generate_comprehensive_pdf(
            comprehensive_report, session_data, facial_features
        )
        
        subject = f"Résultats SIMCO - Session {session.id}"
        body = (
            f"Bonjour,\n\nVeuillez trouver ci-joint votre rapport d'évaluation SIMCO.\n"
            f"Session: {session.id}\nÉtudiant: {session.student_id}\nScore: {round(calculated_score*100)}%\n\n"
            f"Cordialement,\nSIMCO"
        )
        filename = f"rapport_evaluation_{session.student_id}_{session.id}.pdf"
        email_service.send_email_with_attachment(
            to_address=email,
            subject=subject,
            body=body,
            attachment_bytes=pdf_bytes,
            attachment_filename=filename,
            mime_type="application/pdf"
        )
        return {"ok": True, "message": "Rapport envoyé par email"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Error sending results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cognitive-profile/{session_id}", response_model=CognitiveProfileResponse)
async def analyze_cognitive_profile(
    session_id: int, 
    db: Session = Depends(get_db)
):
    """Étape 4: Modélisation et analyse cognitive"""
    # Get session data
    session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    answers = db.query(Answer).filter(Answer.session_id == session_id).all()
    if not answers:
        raise HTTPException(status_code=400, detail="No answers found for this session")
    
    # Calculate performance metrics
    correct_answers = sum(1 for a in answers if a.is_correct)
    actual_performance = correct_answers / len(answers)
    declared_confidence = sum(a.confidence_level for a in answers) / len(answers)
    
    # Get facial analyses
    facial_analyses = []
    for answer in answers:
        facial = db.query(FacialAnalysis).filter(FacialAnalysis.answer_id == answer.id).first()
        if facial:
            facial_analyses.append(facial)
    
    # Calculate observed confidence
    if facial_analyses:
        observed_confidence = sum(f.observed_confidence for f in facial_analyses) / len(facial_analyses)
    else:
        observed_confidence = declared_confidence  # Fallback
    
    # Use ML service for cognitive analysis
    try:
        cognitive_analysis = ml_service.analyze_cognitive_profile(
            actual_performance=actual_performance,
            declared_confidence=declared_confidence,
            observed_confidence=observed_confidence,
            answers_count=len(answers),
            facial_data=facial_analyses
        )
    except Exception as e:
        # Fallback analysis
        cognitive_analysis = {
            "cognitive_profile_type": "accurate",
            "risk_level": "low",
            "dunning_kruger_score": 0.0,
            "impostor_syndrome_score": 0.0,
            "metacognitive_accuracy": 1.0 - abs(declared_confidence - actual_performance)
        }
    
    # Generate recommendations using LLM
    profile_data = {
        "performance": actual_performance,
        "declared_confidence": declared_confidence,
        "observed_confidence": observed_confidence,
        "profile_type": cognitive_analysis["cognitive_profile_type"]
    }
    
    try:
        recommendations = await llm_service.generate_cognitive_recommendations(profile_data)
    except Exception as e:
        recommendations = [
            "Continuer à pratiquer l'autoévaluation",
            "Développer la conscience métacognitive",
            "Renforcer les points faibles identifiés"
        ]
    
    # Determine strengths and weaknesses based on answers
    strengths = []
    weaknesses = []
    
    for i, answer in enumerate(answers):
        if answer.is_correct and answer.confidence_level > 0.7:
            strengths.append(f"Question {i+1} - Maîtrise confirmée")
        elif not answer.is_correct and answer.confidence_level > 0.7:
            weaknesses.append(f"Question {i+1} - Surestimation de connaissance")
        elif not answer.is_correct and answer.confidence_level < 0.4:
            weaknesses.append(f"Question {i+1} - Faible maîtrise")
    
    # Position on cognitive curve
    cognitive_curve_position = {
        "x": declared_confidence,  # Confidence axis
        "y": actual_performance   # Performance axis
    }
    
    # Save cognitive profile
    cognitive_profile = CognitiveProfile(
        session_id=session_id,
        actual_performance=actual_performance,
        declared_confidence=declared_confidence,
        observed_confidence=observed_confidence,
        dunning_kruger_score=cognitive_analysis.get("dunning_kruger_score"),
        impostor_syndrome_score=cognitive_analysis.get("impostor_syndrome_score"),
        metacognitive_accuracy=cognitive_analysis.get("metacognitive_accuracy"),
        cognitive_profile_type=cognitive_analysis["cognitive_profile_type"],
        risk_level=cognitive_analysis["risk_level"],
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations,
        cognitive_curve_position=cognitive_curve_position
    )
    db.add(cognitive_profile)
    db.commit()
    db.refresh(cognitive_profile)
    
    return CognitiveProfileResponse(
        id=cognitive_profile.id,
        session_id=session_id,
        cognitive_profile_type=cognitive_profile.cognitive_profile_type,
        risk_level=cognitive_profile.risk_level,
        cognitive_curve_position=cognitive_curve_position,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations,
        detailed_analysis=cognitive_analysis
    )

@router.post("/analyze-facial")
async def analyze_facial_data(
    request: dict,
    db: Session = Depends(get_db)
):
    """Analyser les données faciales pour une réponse"""
    try:
        from app.services.vision_service import vision_service
        import base64
        
        # Extraire les données de la requête
        session_id = request.get("session_id")
        image_data = request.get("image_data")
        
        if not session_id or not image_data:
            raise HTTPException(status_code=422, detail="session_id et image_data sont requis")
        
        # Décoder l'image
        image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
        
        # Analyser avec le service de vision
        analysis = vision_service.analyze_facial_expression(image_bytes)
        
        # Créer une entrée d'analyse faciale (liée à une réponse)
        # Pour l'instant, on retourne juste l'analyse
        return {
            "confidence": analysis.get("confidence", 0.5),
            "stress": analysis.get("stress", 0.3),
            "engagement": analysis.get("engagement", 0.7),
            "emotions": analysis.get("emotions", {})
        }
        
    except Exception as e:
        print(f"DEBUG: Error in facial analysis: {e}")
        # Retourner des valeurs par défaut
        return {
            "confidence": 0.5,
            "stress": 0.3,
            "engagement": 0.7,
            "emotions": {"neutral": 0.8, "happy": 0.2}
        }

@router.post("/download-pdf")
async def download_comprehensive_pdf(
    session_id: int = Query(..., description="ID de la session"),
    db: Session = Depends(get_db)
):
    """Générer et télécharger un PDF complet du rapport d'évaluation"""
    try:
        from app.services.pdf_service import pdf_service
        from app.services.comprehensive_analysis import comprehensive_analysis_service
        
        print(f"DEBUG: PDF generation requested for session_id: {session_id}")
        
        # Récupérer les données
        session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
        if not session:
            print(f"DEBUG: Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        
        print(f"DEBUG: Found session: {session.id}, student: {session.student_id}")
        
        answers = db.query(Answer).filter(Answer.session_id == session_id).all()
        print(f"DEBUG: Found {len(answers)} answers")
        
        # Récupérer les données faciales
        # FacialAnalysis est liée à Answer, pas directement à Session
        facial_analysis_data = []
        if answers:
            # Récupérer les analyses faciales pour chaque réponse
            for answer in answers:
                facial = db.query(FacialAnalysis).filter(FacialAnalysis.answer_id == answer.id).first()
                if facial:
                    facial_analysis_data.append(facial)
        
        # Combiner les données faciales
        facial_features = None
        if facial_analysis_data:
            # Moyenner les features ou prendre la première
            facial_features = {
                "confidence": sum(f.observed_confidence or 0.5 for f in facial_analysis_data) / len(facial_analysis_data),
                "stress": 1 - sum(f.attention_level or 0.5 for f in facial_analysis_data) / len(facial_analysis_data),
                "engagement": sum(f.eye_contact or 0.5 for f in facial_analysis_data) / len(facial_analysis_data)
            }
        
        facial_data = []
        if facial_features:
            facial_data = [
                {
                    "timestamp": session.started_at.timestamp() + i * 5000,
                    "image_data": "simulated_facial_data",
                    "analysis": facial_features
                }
                for i in range(len(answers))
            ]
            print(f"DEBUG: Found facial analysis with {len(facial_data)} entries")
        
        # Extraire la confiance globale
        global_confidence = 0.5
        if answers:
            global_confidence = sum(a.confidence_level for a in answers) / len(answers)
        print(f"DEBUG: Global confidence: {global_confidence}")
        
        # Convertir les réponses
        answers_data = []
        for answer in answers:
            answers_data.append({
                "question_index": answer.question_index,
                "selected_answer": answer.selected_answer,
                "confidence_level": answer.confidence_level,
                "response_time_ms": answer.response_time_ms,
                "is_correct": answer.is_correct
            })
            print(f"DEBUG: Answer {answer.question_index}: selected='{answer.selected_answer}', correct={answer.is_correct}")
        
        print(f"DEBUG: Converted {len(answers_data)} answers")
        
        # Générer le rapport complet
        comprehensive_report = comprehensive_analysis_service.generate_comprehensive_report(
            answers_data, facial_data, global_confidence
        )
        print(f"DEBUG: Generated comprehensive report")
        print(f"DEBUG: Report accuracy_rate: {comprehensive_report.get('performance_analysis', {}).get('accuracy_rate', 'N/A')}")
        
        # Calculer le score directement à partir des réponses
        correct_answers = sum(1 for answer in answers if answer.is_correct)
        total_answers = len(answers)
        calculated_score = correct_answers / total_answers if total_answers > 0 else 0
        
        print(f"DEBUG: Score calculation: {correct_answers}/{total_answers} = {calculated_score}")
        print(f"DEBUG: Individual answers: {[{'idx': a.question_index, 'correct': a.is_correct} for a in answers]}")
        
        # Préparer les données pour le PDF
        session_data = {
            "id": session.id,
            "student_id": session.student_id,
            "score": calculated_score,  # Utiliser le score calculé directement
            "answered_questions": correct_answers,  # Utiliser le nombre correct
            "total_questions": total_answers
        }
        
        print(f"DEBUG: Preparing PDF generation...")
        
        # Générer le PDF
        pdf_bytes = pdf_service.generate_comprehensive_pdf(
            comprehensive_report, 
            session_data, 
            facial_features
        )
        
        print(f"DEBUG: Generated PDF with {len(pdf_bytes)} bytes")
        
        # Retourner le PDF en réponse
        from fastapi.responses import Response
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=rapport_evaluation_{session.student_id}_{session_id}.pdf"
            }
        )
        
    except Exception as e:
        print(f"DEBUG: Error in PDF generation: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")

@router.post("/comprehensive-report")
async def generate_comprehensive_report(
    session_id: int = Query(..., description="ID de la session"),
    db: Session = Depends(get_db)
):
    """Générer un rapport d'évaluation cognitif complet utilisant toutes les données"""
    try:
        from app.services.comprehensive_analysis import comprehensive_analysis_service
        
        print(f"DEBUG: Starting comprehensive report for session {session_id}")
        
        # Récupérer la session et les réponses
        session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
        if not session:
            print(f"DEBUG: Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        
        answers = db.query(Answer).filter(Answer.session_id == session_id).all()
        print(f"DEBUG: Found {len(answers)} answers for session {session_id}")
        
        # Récupérer les données faciales si disponibles
        # FacialAnalysis est liée à Answer, pas directement à Session
        facial_analysis_data = []
        if answers:
            for answer in answers:
                facial = db.query(FacialAnalysis).filter(FacialAnalysis.answer_id == answer.id).first()
                if facial:
                    facial_analysis_data.append(facial)
        
        facial_data = []
        if facial_analysis_data:
            # Simuler des données faciales temporelles
            facial_data = [
                {
                    "timestamp": session.started_at.timestamp() + i * 5000,
                    "image_data": "simulated_facial_data",
                    "analysis": {
                        "confidence": f.observed_confidence or 0.5,
                        "stress": 1 - (f.attention_level or 0.5),
                        "engagement": f.eye_contact or 0.5
                    }
                }
                for i, f in enumerate(facial_analysis_data)
            ]
        
        # Extraire la confiance globale (moyenne des confiances des réponses)
        global_confidence = 0.5
        if answers:
            global_confidence = sum(a.confidence_level for a in answers) / len(answers)
        
        # Convertir les réponses en format dictionnaire
        answers_data = []
        for answer in answers:
            answers_data.append({
                "question_index": answer.question_index,
                "selected_answer": answer.selected_answer,
                "confidence_level": answer.confidence_level,
                "response_time_ms": answer.response_time_ms,
                "is_correct": answer.is_correct
            })
        
        print(f"DEBUG: Converted {len(answers_data)} answers")
        
        # Générer le rapport complet
        comprehensive_report = comprehensive_analysis_service.generate_comprehensive_report(
            answers_data, facial_data, global_confidence
        )
        print(f"DEBUG: Generated comprehensive report successfully")
        
        return comprehensive_report
        
    except HTTPException:
        # Laisser passer les HTTPException (404, etc.)
        raise
    except Exception as e:
        print(f"DEBUG: Error in comprehensive report generation: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Retourner un rapport minimal en cas d'erreur
        return {
            "performance_analysis": {
                "accuracy_rate": 0.5,
                "correct_answers": 0,
                "total_answers": 0,
                "patterns_detected": []
            },
            "cognitive_profile": {
                "profile_type": "unknown",
                "profile_description": "Erreur lors de l'analyse",
                "cognitive_score": 0.5,
                "performance_score": 0.5,
                "calibration_score": 0.5,
                "strengths": [],
                "weaknesses": []
            },
            "knowledge_position": {
                "phase": "Inconnue",
                "progress_percentage": 0,
                "description": "Erreur lors de l'analyse",
                "next_step": "Réessayer plus tard"
            },
            "recommendations": [
                "Veuillez réessayer l'évaluation plus tard",
                "Contactez l'administrateur si le problème persiste"
            ]
        }

@router.post("/reports", response_model=ReportResponse)
async def generate_report(request: ReportRequest, db: Session = Depends(get_db)):
    """Étape 6: Générer un rapport personnalisé"""
    # Get cognitive profile
    profile = db.query(CognitiveProfile).filter(
        CognitiveProfile.session_id == request.session_id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Cognitive profile not found")
    
    # Get session and quiz details
    session = db.query(QuizSession).filter(QuizSession.id == request.session_id).first()
    answers = db.query(Answer).filter(Answer.session_id == request.session_id).all()
    
    # Generate HTML report
    html_content = generate_html_report(profile, session, answers)
    
    # Generate charts data for Plotly
    charts_data = generate_charts_data(profile, answers)
    
    # Create summary
    summary = f"""
    Évaluation cognitive terminée pour la session {request.session_id}.
    Profil: {profile.cognitive_profile_type}
    Performance: {profile.actual_performance:.2%}
    Niveau de risque: {profile.risk_level}
    """
    
    # Save report
    report = Report(
        session_id=request.session_id,
        html_content=html_content if request.format == "html" else None,
        summary=summary.strip(),
        charts_data=charts_data if request.include_charts else None,
        report_type=request.report_type
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return ReportResponse(
        id=report.id,
        session_id=report.session_id,
        summary=report.summary,
        html_content=html_content if request.format == "html" else None,
        charts_data=charts_data if request.include_charts else None,
        generated_at=report.generated_at
    )

def generate_html_report(profile, session, answers):
    """Generate HTML report content"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Rapport d'Évaluation Cognitive - SIMCO</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ text-align: center; color: #2c3e50; }}
            .section {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            .profile-type {{ color: #e74c3c; font-weight: bold; }}
            .performance {{ color: #27ae60; font-weight: bold; }}
            .risk-level {{ color: #f39c12; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Rapport d'Évaluation Cognitive</h1>
            <h2>SIMCO - Système Intelligent Multimodal d'Évaluation Cognitive</h2>
        </div>
        
        <div class="section">
            <h3>Résumé du Profil</h3>
            <p><strong>Type de profil:</strong> <span class="profile-type">{profile.cognitive_profile_type}</span></p>
            <p><strong>Performance réelle:</strong> <span class="performance">{profile.actual_performance:.1%}</span></p>
            <p><strong>Confiance déclarée:</strong> {profile.declared_confidence:.1%}</p>
            <p><strong>Confiance observée:</strong> {profile.observed_confidence:.1%}</p>
            <p><strong>Niveau de risque:</strong> <span class="risk-level">{profile.risk_level}</span></p>
        </div>
        
        <div class="section">
            <h3>Forces Identifiées</h3>
            <ul>
                {"".join(f"<li>{strength}</li>" for strength in profile.strengths)}
            </ul>
        </div>
        
        <div class="section">
            <h3>Axes d'Amélioration</h3>
            <ul>
                {"".join(f"<li>{weakness}</li>" for weakness in profile.weaknesses)}
            </ul>
        </div>
        
        <div class="section">
            <h3>Recommandations Personnalisées</h3>
            <ul>
                {"".join(f"<li>{rec}</li>" for rec in profile.recommendations)}
            </ul>
        </div>
        
        <div class="section">
            <h3>Position sur la Courbe Cognitive</h3>
            <p>Confiance: {profile.cognitive_curve_position['x']:.2f}, Performance: {profile.cognitive_curve_position['y']:.2f}</p>
        </div>
    </body>
    </html>
    """

def generate_charts_data(profile, answers):
    """Generate Plotly charts data"""
    return {
        "cognitive_curve": {
            "x": profile.cognitive_curve_position["x"],
            "y": profile.cognitive_curve_position["y"],
            "type": "scatter",
            "mode": "markers",
            "marker": {"size": 12, "color": "red"},
            "name": "Position actuelle"
        },
        "confidence_comparison": {
            "declared": profile.declared_confidence,
            "observed": profile.observed_confidence,
            "performance": profile.actual_performance
        },
        "answers_distribution": {
            "correct": sum(1 for a in answers if a.is_correct),
            "incorrect": sum(1 for a in answers if not a.is_correct)
        }
    }
