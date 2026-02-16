from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import math

class ComprehensiveAnalysisService:
    def __init__(self):
        self.confidence_thresholds = {
            "very_high": 0.8,
            "high": 0.6,
            "medium": 0.4,
            "low": 0.2
        }
    
    def analyze_performance_pattern(self, answers: List[Dict]) -> Dict[str, Any]:
        """Analyse les patterns de performance"""
        if not answers:
            return {"pattern": "no_data", "insights": []}
        
        correct_answers = sum(1 for a in answers if a.get("is_correct", False))
        total_answers = len(answers)
        accuracy_rate = correct_answers / total_answers if total_answers > 0 else 0
        
        # Analyser l'évolution performance
        performance_trend = []
        for i, answer in enumerate(answers):
            performance_trend.append({
                "question_index": i,
                "is_correct": answer.get("is_correct", False),
                "confidence": answer.get("confidence_level", 0),
                "response_time": answer.get("response_time_ms", 0)
            })
        
        # Détecter les patterns
        patterns = []
        
        # Pattern 1: Surconfiance
        overconfident_errors = [
            a for a in answers 
            if not a.get("is_correct", False) and a.get("confidence_level", 0) > 0.7
        ]
        if len(overconfident_errors) > total_answers * 0.3:
            patterns.append("surconfiance")
        
        # Pattern 2: Sous-confiance
        underconfident_correct = [
            a for a in answers 
            if a.get("is_correct", False) and a.get("confidence_level", 0) < 0.4
        ]
        if len(underconfident_correct) > total_answers * 0.3:
            patterns.append("sous_confiance")
        
        # Pattern 3: Temps de réponse anormal
        avg_response_time = sum(a.get("response_time_ms", 0) for a in answers) / total_answers
        fast_answers = [a for a in answers if a.get("response_time_ms", 0) < avg_response_time * 0.5]
        if len(fast_answers) > total_answers * 0.4:
            patterns.append("reponses_precipitees")
        
        return {
            "accuracy_rate": accuracy_rate,
            "correct_answers": correct_answers,
            "total_answers": total_answers,
            "performance_trend": performance_trend,
            "patterns_detected": patterns,
            "avg_response_time": avg_response_time
        }
    
    def analyze_confidence_calibration(self, answers: List[Dict]) -> Dict[str, Any]:
        """Analyse la calibration confiance/performance"""
        if not answers:
            return {"calibration": "unknown", "score": 0}
        
        confidence_accuracy_pairs = []
        for answer in answers:
            confidence_accuracy_pairs.append({
                "confidence": answer.get("confidence_level", 0),
                "accuracy": 1.0 if answer.get("is_correct", False) else 0.0
            })
        
        # Calculer le score de calibration (Brier score modifié)
        calibration_score = 0
        for pair in confidence_accuracy_pairs:
            confidence = pair["confidence"]
            accuracy = pair["accuracy"]
            calibration_score += (confidence - accuracy) ** 2
        
        calibration_score = calibration_score / len(confidence_accuracy_pairs)
        calibration_quality = max(0, 1 - calibration_score)  # Inverser pour que 1 = parfait
        
        # Déterminer le type de calibration
        if calibration_quality > 0.8:
            calibration_type = "excellente"
        elif calibration_quality > 0.6:
            calibration_type = "bonne"
        elif calibration_quality > 0.4:
            calibration_type = "moyenne"
        else:
            calibration_type = "faible"
        
        return {
            "calibration_type": calibration_type,
            "calibration_score": round(calibration_quality, 2),
            "confidence_accuracy_pairs": confidence_accuracy_pairs
        }
    
    def analyze_facial_patterns(self, facial_data: List[Dict]) -> Dict[str, Any]:
        """Analyse les patterns faciaux"""
        if not facial_data:
            return {"analysis": "no_facial_data", "insights": []}
        
        # Simuler l'analyse faciale (remplacer par vraie analyse ML)
        insights = []
        
        # Analyser la cohérence temporelle
        if len(facial_data) > 1:
            insights.append("données_temporelles_disponibles")
        
        # Détecter les patterns de stress
        stress_indicators = []
        confidence_indicators = []
        
        for data in facial_data:
            # Simulation - remplacer par vraie détection
            stress_indicators.append(0.3)  # Basé sur l'analyse faciale
            confidence_indicators.append(0.6)
        
        avg_stress = sum(stress_indicators) / len(stress_indicators)
        avg_confidence_facial = sum(confidence_indicators) / len(confidence_indicators)
        
        return {
            "avg_stress_level": round(avg_stress, 2),
            "avg_facial_confidence": round(avg_confidence_facial, 2),
            "data_points": len(facial_data),
            "insights": insights,
            "temporal_consistency": len(facial_data) > 2
        }
    
    def generate_cognitive_profile(self, performance_data: Dict, confidence_data: Dict, facial_data: Dict, global_confidence: float) -> Dict[str, Any]:
        """Génère un profil cognitif complet"""
        
        # Score de performance
        performance_score = performance_data.get("accuracy_rate", 0)
        
        # Score de calibration
        calibration_score = confidence_data.get("calibration_score", 0)
        
        # Score faciale
        facial_confidence = facial_data.get("avg_facial_confidence", 0.5)
        
        # Score global pondéré
        cognitive_score = (
            performance_score * 0.4 +
            calibration_score * 0.3 +
            (global_confidence * facial_confidence) * 0.3
        )
        
        # Déterminer le profil
        if cognitive_score > 0.8:
            profile_type = "expert_confident"
            profile_description = "Performance élevée avec excellente calibration de confiance"
        elif cognitive_score > 0.6:
            profile_type = "competent_aware"
            profile_description = "Bonne performance avec conscience de ses limites"
        elif cognitive_score > 0.4:
            profile_type = "developing"
            profile_description = "En développement avec besoin d'amélioration de la calibration"
        else:
            profile_type = "novice_struggling"
            profile_description = "Débutant avec difficultés de calibration et performance"
        
        # Forces et faiblesses
        strengths = []
        weaknesses = []
        
        if performance_score > 0.7:
            strengths.append("bonne_performance_academique")
        if calibration_score > 0.7:
            strengths.append("excellente_auto_evaluation")
        if global_confidence > 0.6:
            strengths.append("confiance_en_soit")
        
        if performance_score < 0.4:
            weaknesses.append("performance_faible")
        if calibration_score < 0.4:
            weaknesses.append("mauvaise_calibration_confiance")
        if "surconfiance" in performance_data.get("patterns_detected", []):
            weaknesses.append("surconfiance")
        if "sous_confiance" in performance_data.get("patterns_detected", []):
            weaknesses.append("sous_confiance")
        
        return {
            "profile_type": profile_type,
            "profile_description": profile_description,
            "cognitive_score": round(cognitive_score, 2),
            "performance_score": round(performance_score, 2),
            "calibration_score": round(calibration_score, 2),
            "facial_confidence": round(facial_confidence, 2),
            "global_confidence": round(global_confidence, 2),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "patterns_detected": performance_data.get("patterns_detected", [])
        }
    
    def generate_recommendations(self, profile: Dict[str, Any], performance_data: Dict, confidence_data: Dict) -> List[str]:
        """Génère des recommandations personnalisées"""
        recommendations = []
        
        profile_type = profile.get("profile_type", "")
        patterns = performance_data.get("patterns_detected", [])
        calibration_score = confidence_data.get("calibration_score", 0)
        
        # Recommandations basées sur le profil
        if profile_type == "expert_confident":
            recommendations.append("Continuez à vous challenger avec des problèmes plus complexes")
            recommendations.append("Envisagez de mentoriser d'autres étudiants")
        
        elif profile_type == "competent_aware":
            recommendations.append("Travaillez sur la vitesse de réponse pour améliorer l'efficacité")
            recommendations.append("Explorez des sujets avancés pour développer votre expertise")
        
        elif profile_type == "developing":
            recommendations.append("Pratiquez régulièrement pour améliorer la performance")
            recommendations.append("Travaillez sur la calibration de votre confiance")
        
        elif profile_type == "novice_struggling":
            recommendations.append("Retournez aux concepts fondamentaux")
            recommendations.append("Travaillez avec un tuteur ou en groupe")
            recommendations.append("Focus sur la compréhension plutôt que la vitesse")
        
        # Recommandations basées sur les patterns
        if "surconfiance" in patterns:
            recommendations.append("Prenez plus de temps pour analyser chaque question")
            recommendations.append("Vérifiez systématiquement vos réponses")
        
        if "sous_confiance" in patterns:
            recommendations.append("Faites confiance à votre premier instinct")
            recommendations.append("Pratiquez pour construire votre confiance")
        
        if "reponses_precipitees" in patterns:
            recommendations.append("Prenez conscience de votre rythme et ralentissez si nécessaire")
            recommendations.append("Utilisez des techniques de respiration pour gérer le stress")
        
        # Recommandations basées sur la calibration
        if calibration_score < 0.5:
            recommendations.append("Tenez un journal de vos prédictions de performance")
            recommendations.append("Comparez systématiquement votre confiance avec vos résultats")
        
        return recommendations
    
    def generate_comprehensive_report(self, answers: List[Dict], facial_data: List[Dict], global_confidence: float) -> Dict[str, Any]:
        """Génère un rapport d'évaluation complet"""
        
        # Analyser chaque dimension
        performance_analysis = self.analyze_performance_pattern(answers)
        confidence_analysis = self.analyze_confidence_calibration(answers)
        facial_analysis = self.analyze_facial_patterns(facial_data)
        
        # Générer le profil cognitif
        cognitive_profile = self.generate_cognitive_profile(
            performance_analysis, 
            confidence_analysis, 
            facial_analysis, 
            global_confidence
        )
        
        # Générer les recommandations
        recommendations = self.generate_recommendations(
            cognitive_profile, 
            performance_analysis, 
            confidence_analysis
        )
        
        # Position sur la courbe de connaissance
        knowledge_position = self.position_on_knowledge_curve(cognitive_profile)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "performance_analysis": performance_analysis,
            "confidence_analysis": confidence_analysis,
            "facial_analysis": facial_analysis,
            "cognitive_profile": cognitive_profile,
            "knowledge_position": knowledge_position,
            "recommendations": recommendations,
            "data_completeness": {
                "answers_count": len(answers),
                "facial_data_points": len(facial_data),
                "has_global_confidence": global_confidence > 0
            }
        }
    
    def position_on_knowledge_curve(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Détermine la position de l'utilisateur sur la courbe de connaissance"""
        cognitive_score = profile.get("cognitive_score", 0)
        
        if cognitive_score > 0.9:
            phase = "maitrise"
            description = "Vous avez atteint un niveau de maîtrise avancé"
            next_step = "Explorez des spécialisations ou mentorisez d'autres"
        elif cognitive_score > 0.7:
            phase = "competence"
            description = "Vous êtes compétent et fiable dans ce domaine"
            next_step = "Approfondissez vos connaissances et pratiquez l'application"
        elif cognitive_score > 0.5:
            phase = "conscience"
            description = "Vous comprenez les concepts mais manquez de pratique"
            next_step = "Pratiquez régulièrement pour consolider vos acquis"
        elif cognitive_score > 0.3:
            phase = "incompetence_consciente"
            description = "Vous reconnaissez vos lacunes - c'est le début du progrès"
            next_step = "Focus sur les fondamentaux et pratiquez guidée"
        else:
            phase = "incompetence_inconsciente"
            description = "Vous n'êtes pas encore conscient de l'étendue du domaine"
            next_step = "Commencez par une exploration structurée des bases"
        
        return {
            "phase": phase,
            "description": description,
            "next_step": next_step,
            "progress_percentage": round(cognitive_score * 100, 1)
        }

# Instance globale du service
comprehensive_analysis_service = ComprehensiveAnalysisService()
