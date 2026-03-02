"""
data_collector.py
Collects and stores behavioral + performance data for training custom models.
Saves detailed session data for machine learning pipeline.
"""
import json
import csv
import os
from datetime import datetime
from pathlib import Path

class DataCollector:
    def __init__(self, data_dir="training_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_file = self.data_dir / "sessions.jsonl"
        self.features_file = self.data_dir / "features.csv"
        
    def save_session(self, session_data):
        """Save only essential training data in JSONL format"""
        # Collect per-question training data only
        training_samples = []
        
        for q in session_data.get("questions", []):
            qid = q["id"]
            is_correct = session_data.get("user_answers_data", {}).get(qid) == q["correct_answer"]
            confidence = session_data.get("confidence_data", {}).get(qid, 50)
            behavioral_metrics = session_data.get("behavioral_data", {}).get(qid, {})
            
            # Only save if we have behavioral data
            if behavioral_metrics:
                sample = {
                    "is_correct": int(is_correct),
                    "confidence": confidence,
                    "behavioral_metrics": behavioral_metrics
                }
                
                # Calculate derived features for training
                bm = behavioral_metrics
                sample["features"] = {
                    "blink_rate": bm.get("blink_rate", 0),
                    "head_movement": bm.get("head_movement_score", 0),
                    "gaze_stability": bm.get("gaze_stability", 0),
                    "confidence": confidence,
                    "is_correct": int(is_correct),
                    "confidence_error": abs(confidence - (100 if is_correct else 0)),
                    "high_stress": int(bm.get("blink_rate", 0) > 30 or bm.get("head_movement_score", 0) > 5),
                    "low_attention": int(bm.get("gaze_stability", 1) < 0.6),
                    "overconfident": int(confidence > 70 and not is_correct),
                    "underconfident": int(confidence < 40 and is_correct)
                }
                
                training_samples.append(sample)
        
        # Append each sample to JSONL file
        with open(self.sessions_file, "a", encoding="utf-8") as f:
            for sample in training_samples:
                f.write(json.dumps(sample) + "\n")
        
        return len(training_samples)
    
    def export_features_csv(self):
        """Export flat feature vectors for ML training"""
        if not self.sessions_file.exists():
            return
        
        rows = []
        with open(self.sessions_file, "r", encoding="utf-8") as f:
            for line in f:
                sample = json.loads(line)
                if "features" in sample:
                    rows.append(sample["features"])
        
        if rows:
            with open(self.features_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            
            return len(rows)
        return 0
    
    def get_statistics(self):
        """Get collection statistics"""
        if not self.sessions_file.exists():
            return {"total_samples": 0}
        
        samples = 0
        with open(self.sessions_file, "r", encoding="utf-8") as f:
            for line in f:
                samples += 1
        
        return {
            "total_samples": samples,
            "data_file": str(self.sessions_file),
            "features_file": str(self.features_file)
        }
