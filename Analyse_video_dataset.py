import cv2
import time
import csv
import os
import numpy as np
import mediapipe as mp

# =========================
# CONFIG
# =========================
RAW_CSV = "simco_raw_frames.csv"          # TOUT: landmarks par frame
FINAL_CSV = "simco_final_dataset.csv"     # FINAL: 1 ligne par question (features + labels)

MIN_FRAMES_QUESTION = 20

# MediaPipe Futilise 468 points nuérotés donc iic je prnds les partes intéressantes
NOSE_TIP = 1#bout du nze, utilse pour mesurer le mouveemnt de la tete
LEFT_EYE_OUTER = 33#
LEFT_EYE_INNER = 133
RIGHT_EYE_INNER = 263
RIGHT_EYE_OUTER = 362

# =========================
# les foctions de calculs utiles
# =========================
def l2(a, b):#fonction pour calculer la distance euclideinne entre deux points
    return float(np.linalg.norm(np.array(a) - np.array(b)))

def safe_mean(x):#moyenne
    return float(np.mean(x)) if len(x) else 0.0

def safe_std(x):#ectrt-type
    return float(np.std(x)) if len(x) else 0.0

def ensure_header(path, header):#si le cvs est existe deja ne fait rien amsis si il esy vide cree la premeire lige
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(header)

# =========================
# les colonnes du csv
# =========================
# RAW: question_id, timestamp, face_present, then 468 landmarks * (x,y,z)
RAW_HEADER = ["user_id", "question_id", "timestamp", "face_present"]
for i in range(468):
    RAW_HEADER += [f"lm{i}_x", f"lm{i}_y", f"lm{i}_z"]

FINAL_HEADER = [
    "user_id", "question_id",
    "t_start", "t_end", "duration_sec", "n_frames",
    "is_correct", "self_confidence", "difficulty_level",
    "head_motion_mean", "head_motion_std",
    "head_stability",
    "gaze_proxy_mean", "gaze_proxy_std",
    "face_present_ratio",
]

ensure_header(RAW_CSV, RAW_HEADER)
ensure_header(FINAL_CSV, FINAL_HEADER)

# =========================
# MEDIAPIPE SETUP
# =========================
mp_face_mesh = mp.solutions.face_mesh

# =========================
# CAPTURE SETUP
# =========================
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("Impossible d'ouvrir la webcam.")

user_id = "user_001"
question_id = 0
recording = False

t_start = None
prev_nose = None
prev_t = None

# Buffers pour features (par question)
face_present_list = []
head_motion_list = []
nose_x_list = []
nose_y_list = []
gaze_proxy_list = []

print("=== SIMCO capture (RAW + FINAL) ===")
print("Touches: S=start  E=end+save  Q=quit")

with mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as face_mesh:

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        now = time.time()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = face_mesh.process(rgb)

        face_present = 0.0
        landmarks_row = None

        nose = None
        gaze_proxy = 0.0

        if res.multi_face_landmarks:
            face_present = 1.0
            lm = res.multi_face_landmarks[0].landmark

            # Build full landmarks row (468*3)
            landmarks_row = []
            for i in range(468):
                landmarks_row += [lm[i].x, lm[i].y, lm[i].z]

            # Nose
            nose = (lm[NOSE_TIP].x, lm[NOSE_TIP].y)

            # Eyes for gaze_proxy
            le_outer = (lm[LEFT_EYE_OUTER].x, lm[LEFT_EYE_OUTER].y)
            le_inner = (lm[LEFT_EYE_INNER].x, lm[LEFT_EYE_INNER].y)
            re_inner = (lm[RIGHT_EYE_INNER].x, lm[RIGHT_EYE_INNER].y)
            re_outer = (lm[RIGHT_EYE_OUTER].x, lm[RIGHT_EYE_OUTER].y)

            left_eye = ((le_outer[0] + le_inner[0]) / 2, (le_outer[1] + le_inner[1]) / 2)
            right_eye = ((re_outer[0] + re_inner[0]) / 2, (re_outer[1] + re_inner[1]) / 2)
            eye_mid = ((left_eye[0] + right_eye[0]) / 2, (left_eye[1] + right_eye[1]) / 2)

            inter_eye = l2(left_eye, right_eye)
            if inter_eye > 1e-6:
                gaze_proxy = (nose[0] - eye_mid[0]) / inter_eye
            else:
                gaze_proxy = 0.0
        else:
            # Si pas de visage, on stocke des NaN pour les landmarks (ou 0.0 si tu préfères)
            landmarks_row = [np.nan] * (468 * 3)
            nose = None
            gaze_proxy = 0.0

        # =========================
        # If recording: save RAW + accumulate features
        # =========================
        if recording:
            # Save RAW frame
            with open(RAW_CSV, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([user_id, question_id, now, face_present] + landmarks_row)

            # Accumulate for features
            face_present_list.append(face_present)
            gaze_proxy_list.append(float(gaze_proxy))

            if nose is not None:
                nose_x_list.append(nose[0])
                nose_y_list.append(nose[1])

                if prev_nose is not None and prev_t is not None:
                    dt = max(now - prev_t, 1e-3)
                    disp = l2(nose, prev_nose)
                    head_motion_list.append(disp / dt)

                prev_nose = nose
                prev_t = now
            else:
                prev_nose = None
                prev_t = None

        # =========================
        # UI
        # =========================
        status = "REC" if recording else "IDLE"
        cv2.putText(frame, f"Status: {status}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (0, 255, 0) if recording else (0, 0, 255), 2)
        cv2.putText(frame, "S=start  E=end+save  Q=quit", (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imshow("SIMCO Capture", frame)

        key = cv2.waitKey(1) & 0xFF

        # START
        if key in [ord('s'), ord('S')]:
            if not recording:
                recording = True
                t_start = now
                prev_nose = None
                prev_t = None

                # reset buffers
                face_present_list = []
                head_motion_list = []
                nose_x_list = []
                nose_y_list = []
                gaze_proxy_list = []

                print(f"\n[START] question_id={question_id}")

        # END + SAVE FINAL
        elif key in [ord('e'), ord('E')]:
            if recording:
                recording = False
                t_end = now
                duration = t_end - t_start
                n_frames = len(face_present_list)

                print(f"[END] question_id={question_id}  frames={n_frames}  duration={duration:.2f}s")

                if n_frames < MIN_FRAMES_QUESTION:
                    print("  -> Trop court, ignoré (RAW a quand même été enregistré).")
                else:
                    # Labels manuels (tu peux automatiser via ton questionnaire)
                    try:
                        is_correct = int(input("is_correct (0/1) ? ").strip())
                        self_conf = float(input("self_confidence (0-100) ? ").strip())
                        diff = int(input("difficulty_level (ex 1-3) ? ").strip())
                    except Exception:
                        print("  -> Entrée invalide, question ignorée dans FINAL (RAW ok).")
                        question_id += 1
                        continue

                    # Features
                    head_motion_mean = safe_mean(head_motion_list)
                    head_motion_std = safe_std(head_motion_list)

                    head_stability = float(np.var(nose_x_list) + np.var(nose_y_list)) if len(nose_x_list) else 0.0

                    gaze_proxy_mean = safe_mean(gaze_proxy_list)
                    gaze_proxy_std = safe_std(gaze_proxy_list)

                    face_present_ratio = safe_mean(face_present_list)

                    # Save FINAL row
                    with open(FINAL_CSV, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            user_id, question_id,
                            t_start, t_end, duration, n_frames,
                            is_correct, self_conf, diff,
                            head_motion_mean, head_motion_std,
                            head_stability,
                            gaze_proxy_mean, gaze_proxy_std,
                            face_present_ratio
                        ])

                    print(f"  ✅ FINAL sauvegardé: {FINAL_CSV}")
                    print(f"  ✅ RAW sauvegardé en continu: {RAW_CSV}")

                question_id += 1

        # QUIT
        elif key in [ord('q'), ord('Q')]:
            break

cap.release()
cv2.destroyAllWindows()
print("Bye.")
