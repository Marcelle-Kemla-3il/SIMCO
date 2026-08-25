"""
model_trainer.py
Entraîne un Random Forest pour classifier le profil Dunning-Kruger
à partir des features DeepFace + données quiz.

Usage :
    python -m ml.model_trainer
    
Modèle sauvegardé dans : data/models/dk_classifier.pkl
"""
import json
import joblib
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

# ─── Configuration ────────────────────────────────────────────────────────────
DATA_FILE   = Path("data/training/sessions.jsonl")
MODELS_DIR  = Path("data/models")
MODEL_FILE  = MODELS_DIR / "dk_classifier.pkl"
ENCODER_FILE = MODELS_DIR / "label_encoder.pkl"

# Features utilisées pour l'entraînement
FEATURE_COLS = [
    "angry", "disgust", "fear", "happy",
    "neutral", "sad", "surprise",
    "confidence_declared",
    "confidence_observed",
    "is_correct",
    "confidence_gap",
    "confidence_error"
]

LABEL_COL = "profil"


def load_dataset():
    """Charge le dataset depuis sessions.jsonl"""
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset non trouvé : {DATA_FILE}")

    samples = []
    skipped = 0

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                features = record.get("features", {})

                # Vérifier que toutes les features sont présentes
                if not all(col in features for col in FEATURE_COLS + [LABEL_COL]):
                    skipped += 1
                    continue

                samples.append(features)
            except json.JSONDecodeError:
                skipped += 1
                continue

    print(f"✅ {len(samples)} samples chargés ({skipped} ignorés)")
    return samples


def prepare_data(samples):
    """Prépare X et y pour l'entraînement"""
    X = []
    y = []

    for s in samples:
        row = [float(s[col]) for col in FEATURE_COLS]
        X.append(row)
        y.append(s[LABEL_COL])

    X = np.array(X)
    y = np.array(y)

    # Encoder les labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    print(f"\n📊 Distribution des profils :")
    for profil, count in zip(*np.unique(y, return_counts=True)):
        print(f"   {profil:15} → {count} samples")

    return X, y_encoded, y, le


def train_model(X, y_encoded, label_encoder):
    """Entraîne le Random Forest"""

    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded,
        test_size=0.2,
        random_state=42,
        stratify=y_encoded
    )

    print(f"\n🔀 Split : {len(X_train)} train / {len(X_test)} test")

    # Entraîner le Random Forest
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=2,
        min_samples_leaf=1,
        class_weight="balanced",  # compense les classes déséquilibrées
        random_state=42
    )
    clf.fit(X_train, y_train)

    # ─── Évaluation ──────────────────────────────────────────────────────────
    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"\n🎯 Accuracy : {round(accuracy * 100, 1)}%")
    print("\n📋 Rapport de classification :")
    print(classification_report(
        y_test, y_pred,
        target_names=label_encoder.classes_
    ))

    # Cross-validation
    cv_scores = cross_val_score(clf, X, y_encoded, cv=5, scoring="accuracy")
    print(f"📈 Cross-validation (5-fold) : {round(cv_scores.mean() * 100, 1)}% ± {round(cv_scores.std() * 100, 1)}%")

    # ─── Feature importance ───────────────────────────────────────────────────
    print(f"\n🔍 Importance des features :")
    importances = clf.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    for i in sorted_idx:
        bar = "█" * int(importances[i] * 50)
        print(f"   {FEATURE_COLS[i]:25} {bar} {round(importances[i] * 100, 1)}%")

    return clf


def save_models(clf, label_encoder):
    """Sauvegarde le modèle et l'encodeur"""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_FILE)
    joblib.dump(label_encoder, ENCODER_FILE)
    print(f"\n✅ Modèle sauvegardé : {MODEL_FILE}")
    print(f"✅ Encodeur sauvegardé : {ENCODER_FILE}")


def predict_profil(behavioral_data: dict) -> dict:
    """
    Prédit le profil DK depuis des données comportementales.
    Utilisé dans cv_service.py après entraînement.

    behavioral_data doit contenir :
        angry, disgust, fear, happy, neutral, sad, surprise,
        confidence_declared, confidence_observed,
        is_correct, confidence_gap, confidence_error
    """
    if not MODEL_FILE.exists():
        return {"error": "Modèle non entraîné", "profil": None}

    clf = joblib.load(MODEL_FILE)
    le  = joblib.load(ENCODER_FILE)

    features = np.array([[
        float(behavioral_data.get(col, 0))
        for col in FEATURE_COLS
    ]])

    profil_encoded = clf.predict(features)[0]
    profil = le.inverse_transform([profil_encoded])[0]
    probabilities = clf.predict_proba(features)[0]

    proba_dict = {
        le.inverse_transform([i])[0]: round(float(p), 3)
        for i, p in enumerate(probabilities)
    }

    return {
        "profil": profil,
        "probabilities": proba_dict,
        "confidence": round(float(max(probabilities)), 3)
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  SIMCO — Entraînement du modèle Dunning-Kruger")
    print("=" * 55)

    # 1. Charger les données
    samples = load_dataset()

    if len(samples) < 20:
        print(f"⚠️  Seulement {len(samples)} samples — collecte plus de données !")
        exit(1)

    # 2. Préparer X et y
    X, y_encoded, y_raw, label_encoder = prepare_data(samples)

    # 3. Entraîner
    clf = train_model(X, y_encoded, label_encoder)

    # 4. Sauvegarder
    save_models(clf, label_encoder)

    print("\n🎉 Entraînement terminé — modèle prêt !")
    print(f"   Utilise predict_profil() dans cv_service.py")