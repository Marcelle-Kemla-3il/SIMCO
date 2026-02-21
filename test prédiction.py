import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Perceptron
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, classification_report

# =========================
# 1️⃣ LOAD DATA
# =========================
df = pd.read_csv("C:\\Users\\deste\\OneDrive\\Bureau\\SIMCO\\simco_final_dataset_1M.csv")


# =========================
# 2️⃣ LABEL (profil cognitif)
# =========================
# score réel = moyenne glissante sur 5 questions
df["score_real"] = df["is_correct"].astype(float).rolling(5, min_periods=1).mean()

def compute_label(row):
    if row["score_real"] <= 0.4 and row["self_confidence"] >= 70:
        return 1  # sur-estimation
    elif row["score_real"] >= 0.7 and row["self_confidence"] <= 40:
        return 2  # sous-estimation
    else:
        return 0  # cohérent

df["label_profile"] = df.apply(compute_label, axis=1)

# =========================
# 3️⃣ FEATURES
# =========================
features = [
    "self_confidence",
    "duration_sec",
    "difficulty_level",
    "is_correct",
    "head_motion_mean",
    "head_motion_std",
    "head_stability",
    "gaze_proxy_mean",
    "gaze_proxy_std",
    "face_present_ratio"
]

X = df[features]
y = df["label_profile"]

# =========================
# 4️⃣ TRAIN MODEL (Perceptron)
# =========================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = Pipeline([
    ("scaler", StandardScaler()),
    ("clf", Perceptron(max_iter=5000, eta0=0.01, random_state=42))
])

model.fit(X_train, y_train)
pred = model.predict(X_test)

acc = accuracy_score(y_test, pred)
f1 = f1_score(y_test, pred, average="macro")

print("\n====================")
print("RÉSULTATS FINAUX SIMCO")
print("====================")
print("Accuracy :", round(acc, 4))
print("F1 macro :", round(f1, 4))
print("\nConfusion Matrix :")
print(confusion_matrix(y_test, pred))
print("\nClassification Report :")
print(classification_report(y_test, pred))

# =========================
# 5️⃣ STATISTIQUES COGNITIVES
# =========================
total = len(df)
sur = (df["label_profile"] == 1).sum()
sous = (df["label_profile"] == 2).sum()
coherent = (df["label_profile"] == 0).sum()

print("\n====================")
print("ANALYSE COGNITIVE")
print("====================")
print(f"Cohérent : {coherent/total*100:.1f}%")
print(f"Sur-estimation (Dunning-Kruger) : {sur/total*100:.1f}%")
print(f"Sous-estimation (Imposteur) : {sous/total*100:.1f}%")

# =========================
# 6️⃣ COURBE CONFIANCE VS SCORE RÉEL
# =========================
plt.figure()
plt.scatter(df["score_real"], df["self_confidence"])
plt.xlabel("Compétence réelle")
plt.ylabel("Confiance déclarée")
plt.title("Courbe Confiance vs Compétence (SIMCO)")
plt.show()

# =========================
# 7️⃣ DISTRIBUTION DES PROFILS
# =========================
plt.figure()
sns.countplot(x=df["label_profile"])
plt.xticks([0,1,2], ["Cohérent", "Sur-estimation", "Sous-estimation"])
plt.title("Distribution des profils cognitifs")
plt.show()
