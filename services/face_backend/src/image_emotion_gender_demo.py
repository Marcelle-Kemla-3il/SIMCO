import os
import sys
import json

import cv2
from keras.models import load_model
import numpy as np

from utils.datasets import get_labels
from utils.inference import detect_faces
from utils.inference import draw_text
from utils.inference import draw_bounding_box
from utils.inference import apply_offsets
from utils.inference import load_detection_model
from utils.inference import load_image
from utils.preprocessor import preprocess_input


def get_confidence_level(probability):
    if probability >= 0.8:
        return 'High'
    if probability >= 0.5:
        return 'Medium'
    return 'Low'


def get_stress_level(emotion_text):
    if emotion_text in ('angry', 'fear', 'disgust'):
        return 'high'
    if emotion_text in ('sad', 'surprise'):
        return 'medium'
    return 'low'

# parameters for loading data and images
if len(sys.argv) < 2:
    raise SystemExit("Usage: python image_emotion_gender_demo.py <image_path>")

image_path = sys.argv[1]
detection_model_path = '../trained_models/detection_models/haarcascade_frontalface_default.xml'
emotion_model_path = '../trained_models/emotion_models/fer2013_mini_XCEPTION.102-0.66.hdf5'
emotion_labels = get_labels('fer2013')
font = cv2.FONT_HERSHEY_SIMPLEX

# hyper-parameters for bounding boxes shape
emotion_offsets = (0, 0)

# loading models
face_detection = load_detection_model(detection_model_path)
emotion_classifier = load_model(emotion_model_path, compile=False)

# getting input model shapes for inference
emotion_target_size = emotion_classifier.input_shape[1:3]

# loading images
rgb_image = load_image(image_path, grayscale=False)
gray_image = load_image(image_path, grayscale=True)
gray_image = np.squeeze(gray_image)
gray_image = gray_image.astype('uint8')

# More robust face detection for varied photos
gray_equalized = cv2.equalizeHist(gray_image)
faces = []
detector_settings = [
    (1.3, 5),
    (1.2, 5),
    (1.1, 4),
    (1.05, 3)
]
for scale_factor, min_neighbors in detector_settings:
    faces = face_detection.detectMultiScale(gray_equalized, scale_factor, min_neighbors)
    if len(faces) > 0:
        break

# Fallback: detect on 2x upscaled image, then map boxes back
if len(faces) == 0:
    upscaled = cv2.resize(gray_equalized, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    for scale_factor, min_neighbors in detector_settings:
        upscaled_faces = face_detection.detectMultiScale(upscaled, scale_factor, min_neighbors)
        if len(upscaled_faces) > 0:
            faces = np.asarray([
                [int(x / 2), int(y / 2), int(w / 2), int(h / 2)]
                for (x, y, w, h) in upscaled_faces
            ])
            break

if len(faces) == 0:
    print('No face detected in image.')

json_results = []

for face_coordinates in faces:
    x1, x2, y1, y2 = apply_offsets(face_coordinates, emotion_offsets)
    gray_face = gray_image[y1:y2, x1:x2]

    try:
        gray_face = cv2.resize(gray_face, (emotion_target_size))
    except Exception:
        continue

    gray_face = preprocess_input(gray_face, True)
    gray_face = np.expand_dims(gray_face, 0)
    gray_face = np.expand_dims(gray_face, -1)
    emotion_prediction = emotion_classifier.predict(gray_face)
    emotion_probability = float(np.max(emotion_prediction))
    emotion_label_arg = np.argmax(emotion_prediction)
    emotion_text = emotion_labels[emotion_label_arg]
    confidence_text = get_confidence_level(emotion_probability)
    stress_level = get_stress_level(emotion_text)

    # simple color mapping by emotion (matches video demo palette)
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
                                          confidence_text),
              color, 0, 20, 0.7, 2)

    # log to console
    print('Detected emotion: {} | Confidence: {:.0f}% ({})'.format(
        emotion_text, emotion_probability * 100, confidence_text))

    json_results.append({
        'emotion': emotion_text,
        'confidence': round(emotion_probability, 2),
        'stress_level': stress_level
    })

bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
base_name = os.path.basename(image_path)
name, ext = os.path.splitext(base_name)
output_path = os.path.join(os.path.dirname(image_path), f"{name}_with_emotion{ext if ext else '.png'}")
cv2.imwrite(output_path, bgr_image)
print(f"Saved annotated image to: {output_path}")

json_output_path = os.path.join(os.path.dirname(image_path), f"{name}_emotion.json")
if json_results:
    primary_result = max(json_results, key=lambda item: item['confidence'])
else:
    primary_result = {
        'emotion': 'unknown',
        'confidence': 0.0,
        'stress_level': 'unknown'
    }

with open(json_output_path, 'w', encoding='utf-8') as json_file:
    json.dump(primary_result, json_file, indent=2)
print(f"Saved JSON output to: {json_output_path}")
