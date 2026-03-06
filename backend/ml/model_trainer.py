"""
model_trainer.py
Trains custom ML models for behavioral analysis using collected data.
Replaces rule-based heuristics with learned patterns.
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score, mean_squared_error
import joblib
import json
from pathlib import Path

class BehavioralModelTrainer:
    def __init__(self, data_dir="training_data", models_dir="models"):
        self.data_dir = Path(data_dir)
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        
        # Models
        self.stress_classifier = None
        self.confidence_regressor = None
        self.attention_classifier = None
        self.scaler = StandardScaler()
        
    def load_data(self):
        """Load training data from CSV"""
        features_file = self.data_dir / "features.csv"
        if not features_file.exists():
            raise FileNotFoundError(f"Features file not found: {features_file}")
        
        df = pd.read_csv(features_file)
        print(f"Loaded {len(df)} samples from {features_file}")
        return df
    
    def prepare_features(self, df):
        """Prepare feature matrix and target variables"""
        # Feature columns for prediction
        feature_cols = ['blink_rate', 'head_movement', 'gaze_stability', 'confidence']
        X = df[feature_cols].values
        
        # Target variables
        y_stress = df['high_stress'].values
        y_attention = df['low_attention'].values
        y_confidence_error = df['confidence_error'].values
        
        return X, y_stress, y_attention, y_confidence_error
    
    def train_stress_model(self, X, y_stress):
        """Train binary classifier for stress detection"""
        print("\n=== Training Stress Detection Model ===")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_stress, test_size=0.2, random_state=42, stratify=y_stress
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train Random Forest
        self.stress_classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        self.stress_classifier.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.stress_classifier.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Stress Detection Accuracy: {accuracy:.3f}")
        print("\nClassification Report:")
        
        # Handle single class edge case
        unique_classes = len(set(y_test))
        if unique_classes == 1:
            print("⚠️ Only one class in test set - need more diverse data")
            print(f"All samples are: {'High Stress' if y_test[0] == 1 else 'Low Stress'}")
        else:
            print(classification_report(y_test, y_pred, target_names=['Low Stress', 'High Stress']))
        
        # Feature importance
        feature_names = ['blink_rate', 'head_movement', 'gaze_stability', 'confidence']
        importances = self.stress_classifier.feature_importances_
        print("\nFeature Importance:")
        for name, imp in zip(feature_names, importances):
            print(f"  {name}: {imp:.3f}")
        
        return accuracy
    
    def train_attention_model(self, X, y_attention):
        """Train binary classifier for attention detection"""
        print("\n=== Training Attention Detection Model ===")
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_attention, test_size=0.2, random_state=42, stratify=y_attention
        )
        
        X_train_scaled = self.scaler.transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        self.attention_classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        self.attention_classifier.fit(X_train_scaled, y_train)
        
        y_pred = self.attention_classifier.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Attention Detection Accuracy: {accuracy:.3f}")
        print("\nClassification Report:")
        
        # Handle single class edge case
        unique_classes = len(set(y_test))
        if unique_classes == 1:
            print("⚠️ Only one class in test set - need more diverse data")
            print(f"All samples are: {'Low Attention' if y_test[0] == 1 else 'Good Attention'}")
        else:
            print(classification_report(y_test, y_pred, target_names=['Good Attention', 'Low Attention']))
        
        return accuracy
    
    def train_confidence_calibration_model(self, X, y_confidence_error):
        """Train regression model for confidence calibration prediction"""
        print("\n=== Training Confidence Calibration Model ===")
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_confidence_error, test_size=0.2, random_state=42
        )
        
        X_train_scaled = self.scaler.transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        self.confidence_regressor = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.confidence_regressor.fit(X_train_scaled, y_train)
        
        y_pred = self.confidence_regressor.predict(X_test_scaled)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        print(f"Confidence Error RMSE: {rmse:.3f}")
        
        return rmse
    
    def save_models(self):
        """Save trained models to disk"""
        joblib.dump(self.stress_classifier, self.models_dir / "stress_classifier.pkl")
        joblib.dump(self.attention_classifier, self.models_dir / "attention_classifier.pkl")
        joblib.dump(self.confidence_regressor, self.models_dir / "confidence_regressor.pkl")
        joblib.dump(self.scaler, self.models_dir / "scaler.pkl")
        
        print(f"\n✅ Models saved to {self.models_dir}/")
    
    def load_models(self):
        """Load trained models from disk"""
        self.stress_classifier = joblib.load(self.models_dir / "stress_classifier.pkl")
        self.attention_classifier = joblib.load(self.models_dir / "attention_classifier.pkl")
        self.confidence_regressor = joblib.load(self.models_dir / "confidence_regressor.pkl")
        self.scaler = joblib.load(self.models_dir / "scaler.pkl")
        print("✅ Models loaded successfully")
    
    def predict(self, behavioral_data):
        """Make predictions using trained models"""
        # Extract features
        features = np.array([[
            behavioral_data.get('blink_rate', 0),
            behavioral_data.get('head_movement_score', 0),
            behavioral_data.get('gaze_stability', 0),
            behavioral_data.get('confidence', 50)
        ]])
        
        features_scaled = self.scaler.transform(features)
        
        # Predictions
        stress_prob = self.stress_classifier.predict_proba(features_scaled)[0][1]
        attention_prob = self.attention_classifier.predict_proba(features_scaled)[0][1]
        confidence_error = self.confidence_regressor.predict(features_scaled)[0]
        
        return {
            "stress_probability": float(stress_prob),
            "low_attention_probability": float(attention_prob),
            "predicted_confidence_error": float(confidence_error),
            "stress_level": "high" if stress_prob > 0.6 else "medium" if stress_prob > 0.3 else "low",
            "attention_level": "low" if attention_prob > 0.6 else "medium" if attention_prob > 0.3 else "high"
        }

def train_all_models(data_dir="training_data", models_dir="models"):
    """Complete training pipeline"""
    trainer = BehavioralModelTrainer(data_dir=data_dir, models_dir=models_dir)
    
    # Load data
    df = trainer.load_data()
    print(f"\nDataset Summary:")
    print(f"  Total samples: {len(df)}")
    print(f"  High stress samples: {df['high_stress'].sum()} ({df['high_stress'].mean()*100:.1f}%)")
    print(f"  Low attention samples: {df['low_attention'].sum()} ({df['low_attention'].mean()*100:.1f}%)")
    
    # Prepare features
    X, y_stress, y_attention, y_confidence_error = trainer.prepare_features(df)
    
    # Train all models
    trainer.train_stress_model(X, y_stress)
    trainer.train_attention_model(X, y_attention)
    trainer.train_confidence_calibration_model(X, y_confidence_error)
    
    # Save models
    trainer.save_models()
    
    print("\n🎉 Training complete! Models ready for deployment.")

if __name__ == "__main__":
    train_all_models()
