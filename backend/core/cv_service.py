"""
cv_service.py
Reçoit une photo base64, analyse les émotions avec DeepFace,
et retourne un score de confiance observé + profil DK via le modèle ML.
"""
import base64
import os
import numpy as np
import cv2
from pathlib import Path
from deepface import DeepFace

# ─── Import du modèle ML entraîné ────────────────────────────────────────────
MODEL_FILE   = Path("data/models/dk_classifier.pkl")
ENCODER_FILE = Path("data/models/label_encoder.pkl")

_model   = None
_encoder = None

def load_ml_model():
    """Charge le modèle ML si disponible"""
    global _model, _encoder
    try:
        if MODEL_FILE.exists() and ENCODER_FILE.exists():
            import joblib
            _model   = joblib.load(MODEL_FILE)
            _encoder = joblib.load(ENCODER_FILE)
            print("✅ Modèle ML chargé")
        else:
            print("⚠️ Modèle ML non trouvé — utilisation des règles manuelles")
    except Exception as e:
        print(f"⚠️ Erreur chargement modèle : {e}")

# Charger le modèle au démarrage
load_ml_model()

# ─── Features attendues par le modèle ────────────────────────────────────────
FEATURE_COLS = [
    "angry", "disgust", "fear", "happy",
    "neutral", "sad", "surprise",
    "confidence_declared",
    "confidence_observed",
    "is_correct",
    "confidence_gap",
    "confidence_error"
]

# Debug
_debug_count = 0
DEBUG_MAX = 3


def analyze_photo(image_base64: str) -> dict:
    """
    Analyse une photo base64 et retourne les émotions + score de confiance.
    """
    global _debug_count

    try:
        # ─── Décoder l'image base64 ───────────────────────────────────────
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]

        img_bytes = base64.b64decode(image_base64)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img is None:
            return {
                "success": False,
                "error": "Image invalide",
                "confidence_observed": 0.5
            }

        print(f"📷 Image reçue — taille: {img.shape}")

        # ─── Debug — sauvegarder les 3 premières images ───────────────────
        if _debug_count < DEBUG_MAX:
            debug_path = f"debug_capture_{_debug_count}.jpg"
            cv2.imwrite(debug_path, img)
            print(f"📁 Debug: {os.path.abspath(debug_path)}")
            _debug_count += 1

        # ─── Améliorer la luminosité si image trop sombre ─────────────────
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mean_brightness = np.mean(hsv[:, :, 2])
        print(f"💡 Luminosité: {round(float(mean_brightness), 1)}")

        if mean_brightness < 80:
            hsv[:, :, 2] = cv2.convertScaleAbs(hsv[:, :, 2], alpha=1.5, beta=30)
            img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            print("🔆 Luminosité améliorée")

        # ─── Analyser avec DeepFace ───────────────────────────────────────
        result = DeepFace.analyze(
            img,
            actions=["emotion"],
            enforce_detection=False,
            silent=True
        )

        if isinstance(result, list):
            result = result[0]

        emotions      = result.get("emotion", {})
        dominant      = result.get("dominant_emotion", "neutral")
        face_confidence = result.get("face_confidence", 0)

        print(f"🎭 Émotion: {dominant} | "
              f"Confiance visage: {round(float(face_confidence), 3)}")

        # ─── Fix float32 → float Python ───────────────────────────────────
        emotions_clean = {k: round(float(v), 2) for k, v in emotions.items()}

        # ─── Score de confiance via règles manuelles (fallback) ───────────
        confidence_observed = compute_confidence_score(
            emotions_clean,
            face_confidence=float(face_confidence)
        )

        return {
            "success": True,
            "emotions": emotions_clean,
            "dominant_emotion": dominant,
            "confidence_observed": confidence_observed,
            "face_confidence": round(float(face_confidence), 3),
            "error": None
        }

    except Exception as e:
        print(f"❌ cv_service error: {e}")
        return {
            "success": False,
            "emotions": {},
            "dominant_emotion": "unknown",
            "confidence_observed": 0.5,
            "error": str(e)
        }


def predict_dk_profil(
    emotions: dict,
    confidence_declared: int,
    confidence_observed: float,
    is_correct: int
) -> dict:
    """
    ─── ÉTAPE 13 ───────────────────────────────────────────────────────────────
    Prédit le profil Dunning-Kruger en utilisant le modèle ML entraîné.
    
    Si le modèle n'est pas disponible → fallback sur les règles manuelles.
    
    Paramètres :
        emotions            : dict DeepFace (angry, fear, happy...)
        confidence_declared : slider étudiant 0-100
        confidence_observed : score DeepFace 0-1
        is_correct          : 0 ou 1
    
    Retourne :
        {
            profil: "overconfident",
            probabilities: { overconfident: 0.89, calibrated: 0.07... },
            confidence_ml: 0.89,
            method: "ml" | "rules"
        }
    """
    confidence_gap   = round(confidence_declared / 100 - confidence_observed, 3)
    confidence_error = abs(confidence_declared - (100 if is_correct else 0))

    # ─── Utiliser le modèle ML si disponible ─────────────────────────────
    if _model is not None and _encoder is not None:
        try:
            features = np.array([[
                float(emotions.get("angry",    0)),
                float(emotions.get("disgust",  0)),
                float(emotions.get("fear",     0)),
                float(emotions.get("happy",    0)),
                float(emotions.get("neutral",  0)),
                float(emotions.get("sad",      0)),
                float(emotions.get("surprise", 0)),
                float(confidence_declared),
                float(confidence_observed),
                float(is_correct),
                float(confidence_gap),
                float(confidence_error)
            ]])

            profil_encoded  = _model.predict(features)[0]
            profil          = _encoder.inverse_transform([profil_encoded])[0]
            probabilities   = _model.predict_proba(features)[0]

            proba_dict = {
                _encoder.inverse_transform([i])[0]: round(float(p), 3)
                for i, p in enumerate(probabilities)
            }

            print(f"🤖 ML → profil: {profil} | "
                  f"certitude: {round(float(max(probabilities)) * 100, 1)}%")

            return {
                "profil": profil,
                "probabilities": proba_dict,
                "confidence_ml": round(float(max(probabilities)), 3),
                "method": "ml"
            }

        except Exception as e:
            print(f"⚠️ ML prediction échouée : {e} → fallback règles")

    # ─── Fallback — règles manuelles ─────────────────────────────────────
    profil = compute_dk_profil_rules(confidence_declared, confidence_observed, is_correct)
    print(f"📏 Règles → profil: {profil}")

    return {
        "profil": profil,
        "probabilities": {profil: 1.0},
        "confidence_ml": 1.0,
        "method": "rules"
    }


def compute_dk_profil_rules(
    confidence_declared: int,
    confidence_observed: float,
    is_correct: int
) -> str:
    """Règles manuelles de fallback pour le profil DK"""
    conf_obs_pct = confidence_observed * 100

    if is_correct == 0:
        if confidence_declared > 65 or conf_obs_pct > 65:
            return "overconfident"
        return "conscious"
    else:
        if confidence_declared < 40 or conf_obs_pct < 40:
            return "impostor"
        return "calibrated"


def compute_confidence_score(emotions: dict, face_confidence: float = 0.0) -> float:
    """
    Règles manuelles — score de confiance 0-1 depuis les émotions.
    Utilisé comme fallback si le modèle ML n'est pas disponible.
    """
    if face_confidence == 0.0:
        return 0.5

    if not emotions:
        return 0.5

    confidence_score = (
        emotions.get("happy",   0) * 0.40 +
        emotions.get("neutral", 0) * 0.30
    )

    uncertainty_score = (
        emotions.get("fear",     0) * 0.35 +
        emotions.get("surprise", 0) * 0.25 +
        emotions.get("sad",      0) * 0.20 +
        emotions.get("angry",    0) * 0.10 +
        emotions.get("disgust",  0) * 0.10
    )

    total = confidence_score + uncertainty_score
    if total == 0:
        return 0.5

    return round(float(confidence_score / total), 3)