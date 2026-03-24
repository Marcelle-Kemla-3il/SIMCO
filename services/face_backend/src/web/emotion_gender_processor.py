import os
import logging
from pathlib import Path

import cv2
from keras.models import load_model
import numpy as np

try:
    from ..utils.datasets import get_labels
    from ..utils.inference import detect_faces
    from ..utils.inference import draw_text
    from ..utils.inference import draw_bounding_box
    from ..utils.inference import apply_offsets
    from ..utils.inference import load_detection_model
    from ..utils.preprocessor import preprocess_input
except ImportError:
    from utils.datasets import get_labels
    from utils.inference import detect_faces
    from utils.inference import draw_text
    from utils.inference import draw_bounding_box
    from utils.inference import apply_offsets
    from utils.inference import load_detection_model
    from utils.preprocessor import preprocess_input

BASE_DIR = Path(__file__).resolve().parents[2]
DETECTION_MODEL_PATH = BASE_DIR / 'trained_models' / 'detection_models' / 'haarcascade_frontalface_default.xml'
EMOTION_MODEL_PATH = BASE_DIR / 'trained_models' / 'emotion_models' / 'fer2013_mini_XCEPTION.102-0.66.hdf5'
RESULT_DIR = BASE_DIR / 'result'
EMOTION_OFFSETS = (0, 0)
NO_FACE_CONFIDENCE = 0.2

_face_detection = None
_emotion_classifier = None
_emotion_target_size = None
_emotion_labels = get_labels('fer2013')

EMOTION_PROFILE = {
    'happy': {
        'confidence': 0.85,
        'stress_level': 'low',
        'interpretation': 'high confidence, relaxed'
    },
    'neutral': {
        'confidence': 0.65,
        'stress_level': 'medium',
        'interpretation': 'stable, moderate confidence'
    },
    'surprise': {
        'confidence': 0.60,
        'stress_level': 'medium',
        'interpretation': 'uncertain but engaged'
    },
    'angry': {
        'confidence': 0.50,
        'stress_level': 'high',
        'interpretation': 'unstable confidence'
    },
    'sad': {
        'confidence': 0.40,
        'stress_level': 'high',
        'interpretation': 'low confidence'
    },
    'disgust': {
        'confidence': 0.45,
        'stress_level': 'medium',
        'interpretation': 'disengagement'
    },
    'fear': {
        'confidence': 0.30,
        'stress_level': 'high',
        'interpretation': 'high stress, low confidence'
    }
}


def _get_confidence_level(probability):
    if probability >= 0.8:
        return 'High'
    if probability >= 0.5:
        return 'Medium'
    return 'Low'


def _get_emotion_profile(emotion_text):
    return EMOTION_PROFILE.get(emotion_text, {
        'confidence': 0.5,
        'stress_level': 'medium',
        'interpretation': 'unknown'
    })


def _get_stress_level(emotion_text):
    return _get_emotion_profile(emotion_text)['stress_level']


def get_primary_prediction(predictions, belief_confidence=None):
    if not predictions:
        return {
            'emotion': 'unknown',
            'confidence': NO_FACE_CONFIDENCE if belief_confidence is None else belief_confidence,
            'emotion_confidence': 0.0,
            'stress_level': 'unknown'
        }

    primary = max(predictions, key=lambda item: item['confidence'])
    emotion_confidence = round(primary['confidence'], 2)
    profile = _get_emotion_profile(primary['emotion'])
    if belief_confidence is None:
        confidence = round(profile['confidence'], 2)
    else:
        confidence = belief_confidence

    return {
        'emotion': primary['emotion'],
        'confidence': confidence,
        'emotion_confidence': emotion_confidence,
        'stress_level': profile['stress_level'],
        'interpretation': profile['interpretation']
    }


def classify_images(image_bytes_list, belief_confidence=None):
    """Analyze many frames and return one final aggregated confidence."""
    frame_predictions = []
    for frame_index, image_bytes in enumerate(image_bytes_list):
        result = classify_image(image_bytes)
        primary = get_primary_prediction(result['predictions'],
                                         belief_confidence=belief_confidence)
        primary['frame_index'] = frame_index
        primary['faces_detected'] = result['faces_detected']
        if result['faces_detected'] == 0 and belief_confidence is None:
            primary['confidence'] = NO_FACE_CONFIDENCE
        frame_predictions.append(primary)

    frames_with_face = [f for f in frame_predictions if f['emotion'] != 'unknown']
    if not frames_with_face:
        return {
            'frames_analyzed': len(frame_predictions),
            'frames_with_face': 0,
            'final': {
                'emotion': 'unknown',
                'confidence': round(sum(item['confidence'] for item in frame_predictions) /
                                    len(frame_predictions), 2) if frame_predictions else NO_FACE_CONFIDENCE,
                'emotion_confidence': 0.0,
                'stress_level': 'unknown',
                'interpretation': 'unknown'
            },
            'per_frame': frame_predictions
        }

    # Confidence-first aggregation: include all frames (no-face frames use default 0.2).
    final_confidence = round(sum(item['confidence'] for item in frame_predictions) /
                             len(frame_predictions), 2)
    final_emotion_confidence = round(sum(item['emotion_confidence'] for item in frames_with_face) /
                                     len(frames_with_face), 2)

    # Representative label is the frame with highest confidence (tie-breaker: model certainty).
    representative = max(frames_with_face,
                         key=lambda item: (item['confidence'], item['emotion_confidence']))
    best_emotion = representative['emotion']
    profile = _get_emotion_profile(best_emotion)

    return {
        'frames_analyzed': len(frame_predictions),
        'frames_with_face': len(frames_with_face),
        'final': {
            'emotion': best_emotion,
            'confidence': final_confidence,
            'emotion_confidence': final_emotion_confidence,
            'stress_level': profile['stress_level'],
            'interpretation': profile['interpretation']
        },
        'per_frame': frame_predictions
    }


def _load_resources():
    global _face_detection, _emotion_classifier, _emotion_target_size
    if _face_detection is None:
        _face_detection = load_detection_model(str(DETECTION_MODEL_PATH))
    if _emotion_classifier is None:
        _emotion_classifier = load_model(str(EMOTION_MODEL_PATH), compile=False)
        _emotion_target_size = _emotion_classifier.input_shape[1:3]


def _detect_faces_robust(gray_image):
    gray_equalized = cv2.equalizeHist(gray_image)
    detector_settings = [(1.3, 5), (1.2, 5), (1.1, 4), (1.05, 3)]
    for scale_factor, min_neighbors in detector_settings:
        faces = _face_detection.detectMultiScale(gray_equalized, scale_factor, min_neighbors)
        if len(faces) > 0:
            return faces

    upscaled = cv2.resize(gray_equalized, None, fx=2.0, fy=2.0,
                          interpolation=cv2.INTER_CUBIC)
    for scale_factor, min_neighbors in detector_settings:
        upscaled_faces = _face_detection.detectMultiScale(upscaled,
                                                           scale_factor,
                                                           min_neighbors)
        if len(upscaled_faces) > 0:
            return np.asarray([
                [int(x / 2), int(y / 2), int(w / 2), int(h / 2)]
                for (x, y, w, h) in upscaled_faces
            ])
    return []


def classify_image(image_bytes):
    _load_resources()

    image_array = np.frombuffer(image_bytes, np.uint8)
    bgr_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if bgr_image is None:
        raise ValueError('Invalid image payload.')

    rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
    gray_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)

    faces = _detect_faces_robust(gray_image)
    predictions = []

    for face_coordinates in faces:
        x1, x2, y1, y2 = apply_offsets(face_coordinates, EMOTION_OFFSETS)
        gray_face = gray_image[y1:y2, x1:x2]

        try:
            gray_face = cv2.resize(gray_face, _emotion_target_size)
        except Exception:
            continue

        gray_face = preprocess_input(gray_face, True)
        gray_face = np.expand_dims(gray_face, 0)
        gray_face = np.expand_dims(gray_face, -1)

        emotion_prediction = _emotion_classifier.predict(gray_face)
        emotion_probability = float(np.max(emotion_prediction))
        emotion_label_arg = int(np.argmax(emotion_prediction))
        emotion_text = _emotion_labels[emotion_label_arg]
        confidence_level = _get_confidence_level(emotion_probability)
        profile = _get_emotion_profile(emotion_text)

        if emotion_text == 'angry':
            color = emotion_probability * np.asarray((255, 0, 0))
        elif emotion_text == 'sad':
            color = emotion_probability * np.asarray((0, 0, 255))
        elif emotion_text == 'happy':
            color = emotion_probability * np.asarray((255, 255, 0))
        elif emotion_text == 'surprise':
            color = emotion_probability * np.asarray((0, 255, 255))
        else:
            color = emotion_probability * np.asarray((0, 255, 0))
        color = color.astype(int).tolist()

        draw_bounding_box(face_coordinates, rgb_image, color)
        draw_text(face_coordinates, rgb_image, emotion_text, color, 0, -20, 1, 2)
        draw_text(face_coordinates, rgb_image,
                  'Conf: {:.0f}% ({})'.format(emotion_probability * 100,
                                              confidence_level),
                  color, 0, 20, 0.7, 2)

        x, y, w, h = [int(v) for v in face_coordinates]
        predictions.append({
            'emotion': emotion_text,
            'confidence': emotion_probability,
            'derived_confidence': round(profile['confidence'], 2),
            'confidence_percent': round(emotion_probability * 100, 2),
            'confidence_level': confidence_level,
            'stress_level': profile['stress_level'],
            'interpretation': profile['interpretation'],
            'box': {'x': x, 'y': y, 'w': w, 'h': h}
        })

    annotated_bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
    ok, encoded = cv2.imencode('.png', annotated_bgr_image)
    if not ok:
        raise RuntimeError('Failed to encode annotated image.')

    return {
        'faces_detected': len(predictions),
        'predictions': predictions,
        'annotated_image_bytes': encoded.tobytes()
    }


def process_image(image_bytes):
    """Backward-compatible method: writes result image to disk."""
    try:
        result = classify_image(image_bytes)
        if not RESULT_DIR.exists():
            RESULT_DIR.mkdir(parents=True)
        output_path = RESULT_DIR / 'predicted_image.png'
        with open(output_path, 'wb') as output_file:
            output_file.write(result['annotated_image_bytes'])
        return result
    except Exception as err:
        logging.error('Error in emotion gender processor: "{0}"'.format(err))
        raise
