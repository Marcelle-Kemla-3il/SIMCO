import numpy as np
from typing import Dict, List, Any, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import pickle
from pathlib import Path
from app.core.config import settings

class MLService:
    def __init__(self):
        self.model_path = Path(settings.MODEL_PATH)
        self.model_path.mkdir(exist_ok=True)
        
        # Initialize models
        self.rf_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.svm_classifier = SVC(kernel='rbf', random_state=42)
        self.mlp_classifier = MLPClassifier(hidden_layer_sizes=(100, 50), random_state=42, max_iter=500)
        
        self.scaler = StandardScaler()
        self.models_trained = False
        
    def extract_features(self, performance_data: Dict[str, Any]) -> np.ndarray:
        """Extract features from performance and confidence data"""
        features = [
            performance_data.get("actual_performance", 0.0),
            performance_data.get("declared_confidence", 0.0),
            performance_data.get("observed_confidence", 0.0),
            abs(performance_data.get("declared_confidence", 0.0) - performance_data.get("actual_performance", 0.0)),
            abs(performance_data.get("observed_confidence", 0.0) - performance_data.get("actual_performance", 0.0)),
            abs(performance_data.get("declared_confidence", 0.0) - performance_data.get("observed_confidence", 0.0)),
            performance_data.get("answers_count", 0),
            performance_data.get("avg_response_time", 0.0),
            performance_data.get("confidence_variance", 0.0),
            performance_data.get("attention_avg", 0.0),
            performance_data.get("eye_contact_avg", 0.0)
        ]
        
        return np.array(features).reshape(1, -1)
    
    def analyze_cognitive_profile(
        self,
        actual_performance: float,
        declared_confidence: float,
        observed_confidence: float,
        answers_count: int,
        facial_data: Optional[List] = None
    ) -> Dict[str, Any]:
        """Analyze cognitive profile and classify type"""
        
        # Calculate key metrics
        confidence_performance_gap = abs(declared_confidence - actual_performance)
        observed_declared_gap = abs(observed_confidence - declared_confidence)
        
        # Calculate Dunning-Kruger score (overconfidence when performance is low)
        if actual_performance < 0.5 and declared_confidence > 0.7:
            dunning_kruger_score = (declared_confidence - actual_performance) * 2
        elif actual_performance > 0.7 and declared_confidence < 0.5:
            dunning_kruger_score = -(actual_performance - declared_confidence) * 2  # Negative for underconfidence
        else:
            dunning_kruger_score = 0.0
        
        # Calculate Impostor Syndrome score (high performance, low confidence)
        if actual_performance > 0.7 and declared_confidence < 0.5:
            impostor_syndrome_score = (actual_performance - declared_confidence) * 2
        elif actual_performance < 0.5 and declared_confidence > 0.7:
            impostor_syndrome_score = -(declared_confidence - actual_performance) * 2
        else:
            impostor_syndrome_score = 0.0
        
        # Calculate metacognitive accuracy
        metacognitive_accuracy = 1.0 - confidence_performance_gap
        
        # Determine cognitive profile type
        profile_type, risk_level = self._classify_profile(
            actual_performance, declared_confidence, observed_confidence,
            dunning_kruger_score, impostor_syndrome_score
        )
        
        # Extract facial features if available
        facial_features = {}
        if facial_data:
            facial_features = {
                "avg_attention": np.mean([f.attention_level for f in facial_data if f.attention_level]),
                "avg_eye_contact": np.mean([f.eye_contact for f in facial_data if f.eye_contact]),
                "avg_confidence_discrepancy": np.mean([f.confidence_discrepancy for f in facial_data if f.confidence_discrepancy])
            }
        
        return {
            "cognitive_profile_type": profile_type,
            "risk_level": risk_level,
            "dunning_kruger_score": np.clip(dunning_kruger_score, -1.0, 1.0),
            "impostor_syndrome_score": np.clip(impostor_syndrome_score, -1.0, 1.0),
            "metacognitive_accuracy": np.clip(metacognitive_accuracy, 0.0, 1.0),
            "confidence_performance_gap": confidence_performance_gap,
            "observed_declared_gap": observed_declared_gap,
            "facial_features": facial_features
        }
    
    def _classify_profile(
        self,
        performance: float,
        declared_confidence: float,
        observed_confidence: float,
        dunning_kruger_score: float,
        impostor_syndrome_score: float
    ) -> tuple[str, str]:
        """Classify cognitive profile type and risk level"""
        
        # Determine profile type
        if dunning_kruger_score > 0.5:
            profile_type = "dunning-kruger"
        elif impostor_syndrome_score > 0.5:
            profile_type = "impostor"
        elif abs(declared_confidence - performance) < 0.2:
            profile_type = "accurate"
        elif performance > 0.7 and declared_confidence > 0.7:
            profile_type = "confident"
        elif performance < 0.3 and declared_confidence < 0.3:
            profile_type = "aware"
        else:
            profile_type = "uncertain"
        
        # Determine risk level
        if dunning_kruger_score > 0.7 or impostor_syndrome_score > 0.7:
            risk_level = "high"
        elif dunning_kruger_score > 0.3 or impostor_syndrome_score > 0.3 or abs(declared_confidence - performance) > 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return profile_type, risk_level
    
    def train_models(self, training_data: List[Dict[str, Any]]):
        """Train ML models with historical data"""
        if len(training_data) < 10:
            raise ValueError("Need at least 10 training samples")
        
        # Extract features and labels
        X = []
        y_profile = []
        y_risk = []
        
        for data in training_data:
            features = self.extract_features(data).flatten()
            X.append(features)
            y_profile.append(data.get("profile_type", "accurate"))
            y_risk.append(data.get("risk_level", "low"))
        
        X = np.array(X)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train models
        self.rf_classifier.fit(X_scaled, y_profile)
        self.svm_classifier.fit(X_scaled, y_risk)
        self.mlp_classifier.fit(X_scaled, y_profile)
        
        self.models_trained = True
        
        # Save models
        self._save_models()
    
    def predict_profile(self, features: np.ndarray) -> Dict[str, Any]:
        """Predict cognitive profile using trained models"""
        if not self.models_trained:
            # Fallback to rule-based classification
            return self._rule_based_prediction(features)
        
        # Scale features
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Get predictions
        rf_profile_pred = self.rf_classifier.predict(features_scaled)[0]
        svm_risk_pred = self.svm_classifier.predict(features_scaled)[0]
        mlp_profile_pred = self.mlp_classifier.predict(features_scaled)[0]
        
        # Ensemble prediction
        profile_counts = {}
        for pred in [rf_profile_pred, mlp_profile_pred]:
            profile_counts[pred] = profile_counts.get(pred, 0) + 1
        
        final_profile = max(profile_counts, key=profile_counts.get)
        
        return {
            "predicted_profile": final_profile,
            "predicted_risk": svm_risk_pred,
            "confidence": max(profile_counts.values()) / 2.0  # Normalized confidence
        }
    
    def _rule_based_prediction(self, features: np.ndarray) -> Dict[str, Any]:
        """Fallback rule-based prediction"""
        performance = features[0, 0]
        declared_confidence = features[0, 1]
        observed_confidence = features[0, 2]
        
        profile_type, risk_level = self._classify_profile(
            performance, declared_confidence, observed_confidence, 0.0, 0.0
        )
        
        return {
            "predicted_profile": profile_type,
            "predicted_risk": risk_level,
            "confidence": 0.7  # Default confidence for rule-based
        }
    
    def _save_models(self):
        """Save trained models to disk"""
        models_data = {
            "rf_classifier": self.rf_classifier,
            "svm_classifier": self.svm_classifier,
            "mlp_classifier": self.mlp_classifier,
            "scaler": self.scaler,
            "trained": self.models_trained
        }
        
        with open(self.model_path / "cognitive_models.pkl", "wb") as f:
            pickle.dump(models_data, f)
    
    def load_models(self):
        """Load trained models from disk"""
        model_file = self.model_path / "cognitive_models.pkl"
        
        if model_file.exists():
            with open(model_file, "rb") as f:
                models_data = pickle.load(f)
            
            self.rf_classifier = models_data["rf_classifier"]
            self.svm_classifier = models_data["svm_classifier"]
            self.mlp_classifier = models_data["mlp_classifier"]
            self.scaler = models_data["scaler"]
            self.models_trained = models_data["trained"]
            
            return True
        
        return False
    
    def generate_training_sample(
        self,
        actual_performance: float,
        declared_confidence: float,
        observed_confidence: float,
        answers_count: int,
        profile_type: str,
        risk_level: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a training sample from current session"""
        return {
            "actual_performance": actual_performance,
            "declared_confidence": declared_confidence,
            "observed_confidence": observed_confidence,
            "answers_count": answers_count,
            "avg_response_time": kwargs.get("avg_response_time", 5000),
            "confidence_variance": kwargs.get("confidence_variance", 0.1),
            "attention_avg": kwargs.get("attention_avg", 0.7),
            "eye_contact_avg": kwargs.get("eye_contact_avg", 0.8),
            "profile_type": profile_type,
            "risk_level": risk_level
        }

# Global instance
ml_service = MLService()

# Try to load existing models on startup
ml_service.load_models()
