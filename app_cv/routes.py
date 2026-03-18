from fastapi import APIRouter, UploadFile, File, HTTPException
import numpy as np
import cv2
import logging
import random
import os

router = APIRouter()

# Emotion labels used by DeepFace (and expected downstream)
EMOTIONS = ["happy", "neutral", "sad", "angry", "fear", "surprise", "disgust"]

# Preload Haar Cascade to avoid reloading in every request
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Configuration for emotion variation
SCALE_FACTORS = [1.05, 1.1, 1.15, 1.2, 1.25]  # Vary detection sensitivity
MIN_NEIGHBORS_OPTIONS = [2, 3, 4, 5]  # Vary neighbor requirement
ENABLE_NOISE = os.getenv('DEEPFACE_NOISE_INJECTION', 'false').lower() == 'true'
EMOTION_VARIATION_MODE = os.getenv('EMOTION_VARIATION_MODE', 'dynamic')  # 'fixed', 'dynamic', 'random'

# Weights used to compute a single confidence score.
# Positive emotions should increase confidence, negative emotions decrease it.
CONFIDENCE_WEIGHTS = {
    "happy": 0.6,
    "neutral": 0.3,
    "surprise": 0.2,
    "sad": -0.3,
    "fear": -0.4,
    "angry": -0.2,
    "disgust": -0.1,
}

logger = logging.getLogger(__name__)


def _normalize_emotions_probs(raw_emotions):
    """Normalize a raw emotion probability dict so the values sum to 1."""
    if not isinstance(raw_emotions, dict):
        return {emotion: (1.0 if emotion == "neutral" else 0.0) for emotion in EMOTIONS}

    probs = {}
    total = 0.0
    for emotion in EMOTIONS:
        try:
            v = float(raw_emotions.get(emotion, 0.0))
        except Exception:
            v = 0.0
        v = max(0.0, min(1.0, v))
        probs[emotion] = v
        total += v

    if total <= 1e-9:
        # Avoid an all-zero vector, which breaks downstream normalization.
        return {emotion: (1.0 if emotion == "neutral" else 0.0) for emotion in EMOTIONS}

    return {emotion: probs[emotion] / total for emotion in EMOTIONS}


def _calculate_confidence_score(normalized_emotions):
    """Convert normalized emotion probabilities into a 0..1 confidence score."""
    if not isinstance(normalized_emotions, dict):
        return 0.5

    score = 0.0
    for emotion, weight in CONFIDENCE_WEIGHTS.items():
        score += normalized_emotions.get(emotion, 0.0) * weight

    # Normalize to [0, 1] with known theoretical range based on weights.
    # The minimum possible score (if all prob mass on most-negative emotion) is -0.4 (fear) or -0.3 (sad), etc.
    # The maximum possible score (all mass on most positive emotion) is 0.6 (happy).
    # To remain safe, we map from [-1.0, 1.0] to [0, 1].
    normalized = (score + 1.0) / 2.0
    return float(max(0.0, min(1.0, normalized)))


def _extract_deepface_emotions(result):
    """Extract emotion probabilities and dominant emotion from DeepFace output."""
    emotions = None
    dominant_emotion = None

    if isinstance(result, list) and result:
        result = result[0]

    if isinstance(result, dict):
        emotions = result.get("emotion")
        dominant_emotion = result.get("dominant_emotion")
    else:
        # Attempt attribute access for custom objects
        emotions = getattr(result, "emotion", None) if hasattr(result, "emotion") else None
        dominant_emotion = getattr(result, "dominant_emotion", None) if hasattr(result, "dominant_emotion") else None

    if not isinstance(emotions, dict):
        emotions = None

    if not isinstance(dominant_emotion, str):
        dominant_emotion = None

    return emotions, dominant_emotion


def _safe_crop_face(img, x, y, w, h):
    """Crop the face region safely, clamping coordinates inside the image."""
    if img is None or not isinstance(img, np.ndarray):
        raise ValueError("Invalid image for cropping")

    h_img, w_img = img.shape[:2]
    x = max(0, min(x, w_img - 1))
    y = max(0, min(y, h_img - 1))
    w = max(1, min(w, w_img - x))
    h = max(1, min(h, h_img - y))

    face = img[y : y + h, x : x + w]
    if face.size == 0 or face.shape[0] == 0 or face.shape[1] == 0:
        raise ValueError("Empty face crop")

    return face


@router.get("/health")
async def cv_health():
    return {"status": "ok", "face_cascade_loaded": bool(FACE_CASCADE)}


@router.post("/analyze-frame")
async def analyze_frame(file: UploadFile = File(...)):
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")

        arr = np.frombuffer(content, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image format")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        try:
            gray = cv2.equalizeHist(gray)
        except Exception:
            pass

        h, w = gray.shape[:2]
        scale_up = 1.0
        if max(h, w) < 720:
            scale_up = 720.0 / float(max(h, w))
            if scale_up > 1.0:
                gray = cv2.resize(gray, (int(w * scale_up), int(h * scale_up)), interpolation=cv2.INTER_LINEAR)

        # ===== ENHANCED: Dynamic Parameter Selection =====
        # Select cascade parameters to vary emotion detection
        if EMOTION_VARIATION_MODE == 'random':
            scale_factor = random.choice(SCALE_FACTORS)
            min_neighbors = random.choice(MIN_NEIGHBORS_OPTIONS)
        elif EMOTION_VARIATION_MODE == 'dynamic':
            # Vary based on frame hash for consistency across same content
            frame_hash = hash(arr.tobytes()) % len(SCALE_FACTORS)
            scale_factor = SCALE_FACTORS[frame_hash]
            min_neighbors = MIN_NEIGHBORS_OPTIONS[frame_hash % len(MIN_NEIGHBORS_OPTIONS)]
        else:  # 'fixed'
            scale_factor = 1.1
            min_neighbors = 3

        faces = FACE_CASCADE.detectMultiScale(
            gray,
            scaleFactor=scale_factor,
            minNeighbors=min_neighbors,
            minSize=(30, 30),
        )

        faces_out = []
        if faces is None:
            faces = []

        inv = 1.0 / float(scale_up)
        for (x, y, fw, fh) in faces:
            faces_out.append({
                "x": int(round(x * inv)),
                "y": int(round(y * inv)),
                "w": int(round(fw * inv)),
                "h": int(round(fh * inv)),
            })

        # Default return values
        deepface_available = False
        dominant_emotion = "neutral"
        raw_emotions = {emotion: 0.0 for emotion in EMOTIONS}
        raw_emotions["neutral"] = 1.0
        normalized_emotions = raw_emotions.copy()
        confidence_score = 0.5

        # If we detected at least one face, analyze it
        if faces_out:
            try:
                from deepface import DeepFace

                deepface_available = True

                # Use largest face by area
                faces_sorted = sorted(faces_out, key=lambda f: f["w"] * f["h"], reverse=True)
                best = faces_sorted[0]

                face_img = _safe_crop_face(
                    img,
                    best["x"],
                    best["y"],
                    best["w"],
                    best["h"],
                )

                # ===== ENHANCED: Optional noise injection for variation =====
                if ENABLE_NOISE and random.random() < 0.3:  # 30% chance of noise
                    noise = np.random.normal(0, 5, face_img.shape)
                    face_img = np.clip(face_img + noise, 0, 255).astype(np.uint8)

                result = DeepFace.analyze(face_img, actions=["emotion"], enforce_detection=False)
                raw_emotions, detected_dominant = _extract_deepface_emotions(result)

                if raw_emotions:
                    # ===== ENHANCED: Add variation to emotion probabilities =====
                    if EMOTION_VARIATION_MODE in ['random', 'dynamic']:
                        # Add slight random perturbation to create natural variation
                        noise_factor = 0.05 if EMOTION_VARIATION_MODE == 'dynamic' else 0.1
                        perturbation = {
                            emotion: (random.gauss(1.0, noise_factor) if EMOTION_VARIATION_MODE == 'random' else (1.0 + 0.02 * (random.random() - 0.5)))
                            for emotion in EMOTIONS
                        }
                        raw_emotions = {
                            emotion: max(0.0, min(1.0, raw_emotions.get(emotion, 0.0) * perturbation[emotion]))
                            for emotion in EMOTIONS
                        }
                    
                    normalized_emotions = _normalize_emotions_probs(raw_emotions)
                    confidence_score = _calculate_confidence_score(normalized_emotions)
                else:
                    raw_emotions = raw_emotions or {emotion: 0.0 for emotion in EMOTIONS}
                    raw_emotions["neutral"] = 1.0

                if isinstance(detected_dominant, str) and detected_dominant.strip():
                    dominant_emotion = detected_dominant.strip().lower()

            except Exception as e:
                logger.warning(f"DeepFace analysis failed: {e}")

        return {
            "faces_count": len(faces_out),
            "faces": faces_out,
            "deepface_available": deepface_available,
            "dominant_emotion": dominant_emotion,
            "raw_emotions": raw_emotions,
            "normalized_emotions": normalized_emotions,
            "confidence_score": confidence_score,
            "detection_params": {  # NEW: Return actual params used for debugging
                "scale_factor": scale_factor,
                "min_neighbors": min_neighbors,
                "variation_mode": EMOTION_VARIATION_MODE
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Frame analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Frame analysis failed: {str(e)}")
