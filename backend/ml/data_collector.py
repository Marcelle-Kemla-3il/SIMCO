"""
data_collector.py
Collecte et stocke les données comportementales + performance
pour entraîner le Random Forest de classification DK.

Features utilisées (basées sur DeepFace) :
- angry, disgust, fear, happy, neutral, sad, surprise
- confidence_declared
- confidence_observed_avg
- is_correct
- profil (label : overconfident, impostor, calibrated, conscious)
"""
import json
import csv
from pathlib import Path


class DataCollector:
    def __init__(self, data_dir="training_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_file = self.data_dir / "sessions.jsonl"
        self.features_file = self.data_dir / "features.csv"

    def save_session(self, session_data):
        """
        Sauvegarde les données d'entraînement par question.
        Chaque question = 1 sample avec :
          - les émotions DeepFace moyennées sur les photos
          - la confiance déclarée
          - la confiance observée
          - is_correct
          - le label profil DK
        """
        training_samples = []

        for q in session_data.get("questions", []):
            qid = q["id"]
            is_correct = int(
                session_data.get("user_answers_data", {}).get(qid) == q["correct_answer"]
            )
            confidence_declared = session_data.get("confidence_data", {}).get(qid, 50)
            behavioral = session_data.get("behavioral_data", {}).get(qid, {})

            # On ne sauvegarde que si on a des photos analysées
            if not behavioral or not behavioral.get("photos"):
                continue

            # ─── Moyenner les émotions sur toutes les photos ──────────────
            photos = behavioral.get("photos", [])
            valid_photos = [p for p in photos if p.get("success")]

            if not valid_photos:
                continue

            avg_emotions = {
                "angry": 0, "disgust": 0, "fear": 0,
                "happy": 0, "neutral": 0, "sad": 0, "surprise": 0
            }

            for photo in valid_photos:
                emotions = photo.get("emotions", {})
                for key in avg_emotions:
                    avg_emotions[key] += emotions.get(key, 0)

            n = len(valid_photos)
            avg_emotions = {k: round(v / n, 2) for k, v in avg_emotions.items()}

            confidence_observed = behavioral.get("confidence_observed_avg", 0.5)

            # ─── Calculer le label profil DK ──────────────────────────────
            profil = compute_dk_profil(
                confidence_declared=confidence_declared,
                confidence_observed=confidence_observed,
                is_correct=is_correct
            )

            # ─── Construire le sample ─────────────────────────────────────
            sample = {
                "is_correct": is_correct,
                "confidence_declared": confidence_declared,
                "behavioral_metrics": behavioral,
                "features": {
                    # Émotions DeepFace moyennées
                    "angry": avg_emotions["angry"],
                    "disgust": avg_emotions["disgust"],
                    "fear": avg_emotions["fear"],
                    "happy": avg_emotions["happy"],
                    "neutral": avg_emotions["neutral"],
                    "sad": avg_emotions["sad"],
                    "surprise": avg_emotions["surprise"],
                    # Données quiz
                    "confidence_declared": confidence_declared,
                    "confidence_observed": round(float(confidence_observed), 3),
                    "is_correct": is_correct,
                    # Features dérivées
                    "confidence_gap": round(
                        confidence_declared / 100 - float(confidence_observed), 3
                    ),
                    "confidence_error": abs(
                        confidence_declared - (100 if is_correct else 0)
                    ),
                    # Label pour entraînement
                    "profil": profil
                }
            }

            training_samples.append(sample)

        # ─── Sauvegarder dans JSONL ───────────────────────────────────────
        if training_samples:
            with open(self.sessions_file, "a", encoding="utf-8") as f:
                for sample in training_samples:
                    f.write(json.dumps(sample) + "\n")

            print(f"✅ {len(training_samples)} samples sauvegardés")

        return len(training_samples)

    def export_features_csv(self):
        """
        Exporte les features en CSV pour l'entraînement du Random Forest.
        Chaque ligne = 1 question d'1 session.
        """
        if not self.sessions_file.exists():
            return 0

        rows = []
        with open(self.sessions_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    sample = json.loads(line)
                    if "features" in sample:
                        rows.append(sample["features"])
                except json.JSONDecodeError:
                    continue

        if rows:
            with open(self.features_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            print(f"✅ CSV exporté : {len(rows)} lignes → {self.features_file}")
            return len(rows)

        return 0

    def get_statistics(self):
        """Statistiques sur les données collectées"""
        if not self.sessions_file.exists():
            return {"total_samples": 0}

        samples = 0
        profils = {}

        with open(self.sessions_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    sample = json.loads(line)
                    samples += 1
                    profil = sample.get("features", {}).get("profil", "unknown")
                    profils[profil] = profils.get(profil, 0) + 1
                except json.JSONDecodeError:
                    continue

        return {
            "total_samples": samples,
            "profils": profils,
            "data_file": str(self.sessions_file),
            "features_file": str(self.features_file)
        }


def compute_dk_profil(
    confidence_declared: int,
    confidence_observed: float,
    is_correct: int
) -> str:
    """
    Calcule le label profil DK basé sur 3 sources :
    - confidence_declared  : ce que l'étudiant dit ressentir (0-100)
    - confidence_observed  : ce que DeepFace détecte (0-1)
    - is_correct           : performance réelle

    4 profils possibles :
    - overconfident  : surconfiant malgré erreur
    - impostor       : sous-confiant malgré bonne réponse
    - calibrated     : confiance alignée avec performance
    - conscious      : conscient de son ignorance
    """
    conf_obs_pct = confidence_observed * 100  # ramener à 0-100

    if is_correct == 0:
        if confidence_declared > 65 or conf_obs_pct > 65:
            return "overconfident"
        else:
            return "conscious"
    else:  # is_correct == 1
        if confidence_declared < 40 or conf_obs_pct < 40:
            return "impostor"
        else:
            return "calibrated"