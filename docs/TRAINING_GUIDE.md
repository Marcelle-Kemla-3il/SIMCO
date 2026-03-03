# Training Your Own Behavioral Analysis Model

## Overview
This implementation allows you to collect real quiz session data and train custom ML models instead of using rule-based heuristics.

## **Best Approach: 3-Phase Pipeline**

### **Phase 1: Data Collection** (Weeks 1-4)
Collect behavioral + performance data from real quiz sessions.

**What happens automatically:**
- Every quiz session is saved to `training_data/sessions.jsonl`
- Each question captures:
  - Blink rate, head movement, gaze stability
  - User's confidence level (1-100)
  - Correctness of answer
  - Derived labels (high_stress, overconfident, underconfident)

**Minimum requirements:**
- 50+ questions for basic training
- 200+ questions recommended
- 500+ questions for production-quality models

**Target: 20-50 users × 10 questions = 200-500 samples**

---

### **Phase 2: Model Training** (After data collection)

Once you have sufficient data:

```bash
# Install ML dependencies
pip install -r requirements_ml.txt

# Export data and train models
python train.py
```

**What this does:**
1. Exports JSONL data to CSV feature matrix
2. Trains 3 models:
   - **Stress Classifier**: Predicts high/low stress from behavioral metrics
   - **Attention Classifier**: Detects low attention (gaze instability)
   - **Confidence Calibration Regressor**: Predicts confidence error
3. Saves trained models to `models/` folder

**Models used:**
- Random Forest Classifiers (stress, attention)
- Gradient Boosting Regressor (confidence calibration)
- StandardScaler for feature normalization

---

### **Phase 3: Deployment** (After training)

Restart your backend:
```bash
python -m uvicorn main:app --reload
```

**Automatic behavior:**
- If `models/stress_classifier.pkl` exists → Uses ML predictions
- If no models → Falls back to rule-based analysis
- Continues collecting data for future retraining

---

## **Feature Engineering**

The system automatically extracts these features per question:

### Input Features (X):
1. `blink_rate` - Blinks per minute (0-60+)
2. `head_movement` - Head pose change score (0-10)
3. `gaze_stability` - Proportion looking at screen (0-1)
4. `confidence` - Self-reported confidence (0-100)

### Target Labels (y):
1. `high_stress` - Binary (blink_rate > 30 OR head_movement > 5)
2. `low_attention` - Binary (gaze_stability < 0.6)
3. `overconfident` - Binary (confidence > 70 AND wrong answer)
4. `underconfident` - Binary (confidence < 40 AND correct answer)
5. `confidence_error` - Continuous (|confidence - actual_performance|)

---

## **Data Collection Strategy**

### **Option A: Natural Collection** (Recommended)
- Deploy quiz to real students
- Collect data organically over time
- Authentic behavioral patterns

### **Option B: Controlled Study**
- Recruit participants
- Vary difficulty levels
- Include think-aloud protocols for labeling

### **Option C: Self-Labeling**
- Add post-question surveys: "How stressed did you feel?"
- Collect ground truth labels
- Improves supervised learning accuracy

---

## **Model Performance Monitoring**

After training, check output for:

```
Stress Detection Accuracy: 0.847
Classification Report:
              precision    recall  f1-score
Low Stress       0.89      0.83      0.86
High Stress      0.81      0.87      0.84

Feature Importance:
  blink_rate: 0.412
  head_movement: 0.298
  gaze_stability: 0.187
  confidence: 0.103
```

**Good results:**
- Accuracy > 75%
- Balanced precision/recall
- Feature importance makes sense (blink rate most important for stress)

**If accuracy is low (<70%):**
- Collect more data
- Check for data quality issues
- Consider different features

---

## **Retraining Pipeline**

As you collect more data:

```bash
# Check current dataset size
python -c "from data_collector import DataCollector; print(DataCollector().get_statistics())"

# Retrain when you have 100+ new samples
python train.py
```

**Model versioning:**
Models are saved with timestamps. Keep old versions for comparison.

---

## **Advanced: Transfer Learning Approach**

If you want to use the Python SSIMCO models:

1. **Option 1: Hybrid System**
   - Frontend captures video frames
   - Send frames to Python backend via WebSocket
   - Use trained SSIMCO models
   - More accurate but complex

2. **Option 2: Fine-tuning**
   - Use MediaPipe as feature extractor
   - Train shallow classifier on top
   - Balance between accuracy and simplicity

---

## **Data Privacy & Ethics**

**Important considerations:**
- Inform users about webcam recording
- Store data securely (encrypted)
- Get consent for ML training
- Allow opt-out from behavioral tracking
- Anonymize session IDs

---

## **File Structure**

```
backend/
├── main.py                 # FastAPI app (auto-collects data)
├── data_collector.py       # Saves sessions to JSONL
├── model_trainer.py        # ML training pipeline
├── train.py                # Entry point for training
├── requirements_ml.txt     # ML dependencies
├── training_data/
│   ├── sessions.jsonl      # Raw session data
│   └── features.csv        # Exported feature matrix
└── models/
    ├── stress_classifier.pkl
    ├── attention_classifier.pkl
    ├── confidence_regressor.pkl
    └── scaler.pkl
```

---

## **Quick Start Commands**

```bash
# 1. Install ML dependencies
pip install -r requirements_ml.txt

# 2. Run quiz and collect data (wait for 20+ sessions)
python -m uvicorn main:app --reload

# 3. Check collected data
python -c "from data_collector import DataCollector; print(DataCollector().get_statistics())"

# 4. Train models (when you have 50+ questions)
python train.py

# 5. Restart server to use trained models
python -m uvicorn main:app --reload
```

---

## **Expected Timeline**

- **Week 1-2**: Deploy and collect 100 questions
- **Week 2**: First training (baseline models)
- **Week 3-4**: Collect 200 more questions
- **Week 4**: Retrain with 300+ samples (improved accuracy)
- **Month 2+**: Continuous improvement

---

## **Key Advantages of This Approach**

✅ **No manual labeling required** - Labels derived from quiz performance
✅ **Continuous learning** - Collect data forever, retrain periodically
✅ **Domain-specific** - Models trained on YOUR quiz data
✅ **Transparent** - Feature importance shows what matters
✅ **Hybrid fallback** - Rule-based analysis until models are ready
✅ **Privacy-preserving** - No raw video stored, only metrics

---

## **Next Steps**

1. ✅ Start collecting data (automatically happening now)
2. Monitor `training_data/sessions.jsonl` file growth
3. After 50+ questions → Run first training
4. Evaluate model performance
5. Collect more data for improvement
6. Retrain monthly or when accuracy drops

**Current status**: System is now in **data collection mode**. Every quiz session contributes to your training dataset!
