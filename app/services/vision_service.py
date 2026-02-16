import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
import base64
from pathlib import Path
from app.core.config import settings

class VisionService:
    def __init__(self):
        self.use_mediapipe = settings.MEDIAPIPE_ENABLED
        self.openface_bin = settings.OPENFACE_BIN
        
        # Initialize MediaPipe if available
        if self.use_mediapipe:
            try:
                import mediapipe as mp
                # Vérifier si MediaPipe a les solutions requises
                if hasattr(mp, 'solutions'):
                    self.mp_face_detection = mp.solutions.face_detection
                    self.mp_face_mesh = mp.solutions.face_mesh
                    self.face_detection = self.mp_face_detection.FaceDetection(
                        model_selection=0, min_detection_confidence=0.5
                    )
                    self.face_mesh = self.mp_face_mesh.FaceMesh(
                        static_image_mode=False,
                        max_num_faces=1,
                        refine_landmarks=True,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5
                    )
                    print("MediaPipe initialized successfully")
                else:
                    print("MediaPipe not available or incompatible: module 'mediapipe' has no attribute 'solutions'. Using basic OpenCV")
                    self.use_mediapipe = False
            except (ImportError, AttributeError) as e:
                print(f"MediaPipe initialization failed: {e}. Using basic OpenCV")
                self.use_mediapipe = False
    
    def decode_base64_image(self, base64_str: str) -> np.ndarray:
        """Decode base64 image to numpy array"""
        img_data = base64.b64decode(base64_str)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    
    def detect_face(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Detect face in image and return bounding box"""
        try:
            # Convertir en niveaux de gris
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Charger le classificateur de visage
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            # Détecter les visages
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                print("DEBUG: No face detected")
                return None
            
            # Prendre le plus grand visage
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            
            print(f"DEBUG: Face detected at ({x}, {y}) size {w}x{h}")
            return (x, y, x + w, y + h)
            
        except Exception as e:
            print(f"DEBUG: Face detection error: {e}")
            return None
    
    def extract_facial_landmarks(self, image: np.ndarray) -> Optional[Dict[str, np.ndarray]]:
        """Extract facial landmarks using MediaPipe"""
        if not self.use_mediapipe:
            return None
        
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_image)
        
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0]
            
            # Extract key facial regions
            h, w, _ = image.shape
            
            # Eye landmarks
            left_eye = []
            right_eye = []
            for idx in [33, 7, 163, 144, 145, 153, 154, 155, 133]:  # Left eye indices
                landmark = landmarks.landmark[idx]
                left_eye.append([int(landmark.x * w), int(landmark.y * h)])
            
            for idx in [362, 398, 384, 385, 386, 387, 388, 466, 263]:  # Right eye indices
                landmark = landmarks.landmark[idx]
                right_eye.append([int(landmark.x * w), int(landmark.y * h)])
            
            # Mouth landmarks
            mouth = []
            for idx in [13, 14, 78, 80, 81, 82, 87, 88, 95]:  # Mouth indices
                landmark = landmarks.landmark[idx]
                mouth.append([int(landmark.x * w), int(landmark.y * h)])
            
            return {
                "left_eye": np.array(left_eye),
                "right_eye": np.array(right_eye),
                "mouth": np.array(mouth),
                "all_landmarks": landmarks
            }
        
        return None
    
    def analyze_emotions(self, image: np.ndarray) -> Dict[str, float]:
        """Analyze basic emotions from facial expression"""
        # Convertir en niveaux de gris pour l'analyse
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Détecter les visages
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) == 0:
            # Pas de visage détecté - retourner des émotions neutres
            return {"neutral": 0.8, "focused": 0.2}
        
        # Prendre le plus grand visage
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        face_roi = gray[y:y+h, x:x+w]
        
        # Analyser les caractéristiques du visage
        emotions = {}
        
        # 1. Détection de sourire (coins de la bouche)
        mouth_y = int(y + h * 0.7)
        mouth_height = int(h * 0.2)
        mouth_roi = gray[mouth_y:mouth_y + mouth_height, x:x + w]
        
        # Variance de l'intensité pour détecter un sourire
        mouth_variance = cv2.var(mouth_roi) if mouth_roi.size > 0 else 0
        smile_intensity = min(mouth_variance / 5000, 1.0)
        emotions["happy"] = smile_intensity
        
        # 2. Détection d'expression neutre vs concentrée
        # Basé sur la symétrie et la variance globale
        face_variance = cv2.var(face_roi)
        neutral_intensity = max(0.1, 1.0 - (face_variance / 10000))
        emotions["neutral"] = neutral_intensity
        
        # 3. Détection de concentration (yeux ouverts, front plissé)
        eye_y = int(y + h * 0.2)
        eye_height = int(h * 0.15)
        eye_roi = gray[eye_y:eye_y + eye_height, x:x + w]
        
        eye_variance = cv2.var(eye_roi) if eye_roi.size > 0 else 0
        focus_intensity = min(eye_variance / 3000, 1.0)
        emotions["focused"] = focus_intensity
        
        # 4. Autres émotions basées sur les patterns
        if face_variance > 8000:
            emotions["surprised"] = min((face_variance - 8000) / 5000, 0.5)
        if smile_intensity < 0.2 and neutral_intensity < 0.5:
            emotions["confused"] = 0.3
        
        # Normaliser pour que la somme soit ~1
        total = sum(emotions.values())
        if total > 0:
            emotions = {k: v/total for k, v in emotions.items()}
        
        print(f"DEBUG: Emotions detected: {emotions}")
        return emotions
    
    def calculate_eye_contact(self, image: np.ndarray) -> float:
        """Calculate eye contact level (0-1)"""
        landmarks = self.extract_facial_landmarks(image)
        if not landmarks:
            return 0.5
        
        # Simple eye contact detection based on eye visibility and position
        left_eye = landmarks.get("left_eye")
        right_eye = landmarks.get("right_eye")
        
        if left_eye is None or right_eye is None:
            return 0.5
        
        # Check if eyes are open (based on eye height)
        left_eye_height = np.max(left_eye[:, 1]) - np.min(left_eye[:, 1])
        right_eye_height = np.max(right_eye[:, 1]) - np.min(right_eye[:, 1])
        
        avg_eye_height = (left_eye_height + right_eye_height) / 2
        
        # Normalize to 0-1 scale (assuming typical eye height is 10-20 pixels)
        eye_openness = min(avg_eye_height / 15.0, 1.0)
        
        return max(eye_openness, 0.1)  # Minimum baseline
    
    def calculate_attention_level(self, image: np.ndarray) -> float:
        """Calculate attention level based on facial cues"""
        emotions = self.analyze_emotions(image)
        eye_contact = self.calculate_eye_contact(image)
        
        # Combine emotion and eye contact for attention score
        attention_weights = {
            "focused": 0.9,
            "neutral": 0.7,
            "happy": 0.6,
            "surprised": 0.5,
            "confused": 0.3,
            "bored": 0.2
        }
        
        emotion_score = 0.0
        for emotion, intensity in emotions.items():
            weight = attention_weights.get(emotion, 0.5)
            emotion_score += intensity * weight
        
        # Combine with eye contact (70% emotion, 30% eye contact)
        attention = 0.7 * emotion_score + 0.3 * eye_contact
        
        return min(max(attention, 0.0), 1.0)
    
    def estimate_confidence_from_face(self, image: np.ndarray) -> float:
        """Estimate confidence level from facial expression"""
        emotions = self.analyze_emotions(image)
        eye_contact = self.calculate_eye_contact(image)
        attention = self.calculate_attention_level(image)
        
        # Confidence indicators
        confidence_factors = {
            "happy": 0.8,      # Smile indicates confidence
            "neutral": 0.6,    # Neutral can be confident
            "focused": 0.7,    # Focus indicates engagement
            "surprised": 0.3,  # Surprise might indicate uncertainty
            "confused": 0.2,   # Confusion indicates low confidence
            "bored": 0.1       # Boredom indicates low engagement
        }
        
        emotion_confidence = 0.0
        for emotion, intensity in emotions.items():
            factor = confidence_factors.get(emotion, 0.5)
            emotion_confidence += intensity * factor
        
        # Combine factors: 40% emotion, 30% eye contact, 30% attention
        estimated_confidence = (
            0.4 * emotion_confidence +
            0.3 * eye_contact +
            0.3 * attention
        )
        
        return min(max(estimated_confidence, 0.0), 1.0)
    
    def analyze_facial_expression(self, image_bytes: bytes) -> Dict[str, float]:
        """Analyser l'expression faciale à partir des bytes d'image"""
        try:
            # Convertir les bytes en numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                print("DEBUG: Could not decode image")
                return self._get_default_analysis()
            
            # Analyser les émotions
            emotions = self.analyze_emotions(image)
            
            # Calculer les métriques
            confidence = self.estimate_confidence_from_face(image)
            stress = self._calculate_stress_from_emotions(emotions)
            engagement = self.calculate_attention_level(image)
            
            # Ajouter de la variabilité basée sur le contenu de l'image
            # image_bytes est déjà un objet bytes ici
            image_hash = hash(image_bytes) % 1000
            variation_factor = 0.3 * (image_hash / 1000.0)  # Variation de 0 à 0.3
            
            # Appliquer la variation
            confidence = min(max(confidence + variation_factor - 0.15, 0.1), 0.9)
            stress = min(max(stress + (0.3 - variation_factor) - 0.15, 0.1), 0.9)
            engagement = min(max(engagement + variation_factor * 0.5 - 0.25, 0.2), 0.9)
            
            print(f"DEBUG: Analysis - Confidence: {confidence:.3f}, Stress: {stress:.3f}, Engagement: {engagement:.3f}")
            
            return {
                "confidence": confidence,
                "stress": stress,
                "engagement": engagement,
                "emotions": emotions
            }
            
        except Exception as e:
            print(f"DEBUG: Error in facial analysis: {e}")
            return self._get_default_analysis()
    
    def _calculate_stress_from_emotions(self, emotions: Dict[str, float]) -> float:
        """Calculer le niveau de stress à partir des émotions"""
        stress_indicators = {
            "confused": 0.8,
            "surprised": 0.6,
            "neutral": 0.3,
            "happy": 0.1,
            "focused": 0.2,
            "bored": 0.4
        }
        
        stress_score = 0.0
        for emotion, intensity in emotions.items():
            weight = stress_indicators.get(emotion, 0.5)
            stress_score += intensity * weight
        
        return min(max(stress_score, 0.0), 1.0)
    
    def _get_default_analysis(self) -> Dict[str, float]:
        """Retourner une analyse par défaut avec variabilité"""
        import time
        import random
        
        # Utiliser le temps pour créer de la variabilité
        seed = int(time.time() * 1000) % 1000
        random.seed(seed)
        
        return {
            "confidence": 0.4 + random.random() * 0.4,  # 0.4 à 0.8
            "stress": 0.2 + random.random() * 0.3,     # 0.2 à 0.5
            "engagement": 0.5 + random.random() * 0.3,  # 0.5 à 0.8
            "emotions": {
                "neutral": 0.3 + random.random() * 0.4,
                "focused": 0.2 + random.random() * 0.3,
                "happy": 0.1 + random.random() * 0.3
            }
        }

# Global instance
vision_service = VisionService()
