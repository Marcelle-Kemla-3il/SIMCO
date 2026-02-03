import cv2
import mediapipe as mp
import time
import csv
from pathlib import Path
import math
import statistics as stats

def dist(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

def safe_div(a, b, eps=1e-6):
    return a / (b + eps)

def mean_std(values):
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return float(values[0]), 0.0
    return float(stats.mean(values)), float(stats.pstdev(values))

def iris_center(lm, idxs):
    xs = [lm[i].x for i in idxs]
    ys = [lm[i].y for i in idxs]
    return (sum(xs) / len(xs), sum(ys) / len(ys))

def main():
    session_id = input("session_id (ex: s001): ").strip() or "s001"
    question_id = input("question_id (ex: q01): ").strip() or "q01"

    out_dir = Path("simco/data")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "vision_features.csv"

    # Si le fichier n'existe pas, on écrit l'en-tête
    file_exists = out_file.exists()

    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Webcam non détectée")

    # Eye landmarks (EAR)
    LEFT_EYE_TOP = 159
    LEFT_EYE_BOTTOM = 145
    LEFT_EYE_LEFT = 33
    LEFT_EYE_RIGHT = 133

    # Iris (refine_landmarks=True)
    LEFT_IRIS = [468, 469, 470, 471, 472]

    NOSE = 1

    collecting = False
    start_ts = None
    end_ts = None

    # buffers pendant la question
    eye_open_vals = []
    head_move_vals = []
    gaze_move_vals = []
    blink_count = 0

    prev_nose = None
    prev_gaze = None
    last_blink_ts = 0.0

    print("\nContrôles:")
    print("  S = start collecte (début de la question)")
    print("  E = end collecte (fin de la question) -> calcule + sauvegarde")
    print("  ESC = quitter\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        ts = time.time()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = face_mesh.process(rgb)

        face_detected = True if result.multi_face_landmarks else False

        # Affichage état
        status = "COLLECTE ON" if collecting else "COLLECTE OFF"
        cv2.putText(frame, status, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (0, 255, 0) if collecting else (0, 0, 255), 2)

        if collecting and face_detected:
            lm = result.multi_face_landmarks[0].landmark

            # Eye openness (EAR)
            p_top = (lm[LEFT_EYE_TOP].x, lm[LEFT_EYE_TOP].y)
            p_bottom = (lm[LEFT_EYE_BOTTOM].x, lm[LEFT_EYE_BOTTOM].y)
            p_left = (lm[LEFT_EYE_LEFT].x, lm[LEFT_EYE_LEFT].y)
            p_right = (lm[LEFT_EYE_RIGHT].x, lm[LEFT_EYE_RIGHT].y)

            vert = dist(p_top, p_bottom)
            horiz = dist(p_left, p_right)
            ear = safe_div(vert, horiz)
            eye_open_vals.append(ear)

            # Blink simple
            if ear < 0.18 and (ts - last_blink_ts) > 0.25:
                blink_count += 1
                last_blink_ts = ts

            # Head move (nez)
            nose = (lm[NOSE].x, lm[NOSE].y)
            if prev_nose is not None:
                head_move_vals.append(dist(nose, prev_nose))
            prev_nose = nose

            # Gaze move (centre iris)
            gaze = iris_center(lm, LEFT_IRIS)
            if prev_gaze is not None:
                gaze_move_vals.append(dist(gaze, prev_gaze))
            prev_gaze = gaze

            cv2.putText(frame, f"EAR={ear:.3f} blinks={blink_count}", (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        cv2.imshow("SIMCO - Collect Vision Features", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == 27:  # ESC
            break

        # Start collecte
        if key in [ord('s'), ord('S')]:
            collecting = True
            start_ts = time.time()
            end_ts = None

            # reset buffers
            eye_open_vals = []
            head_move_vals = []
            gaze_move_vals = []
            blink_count = 0
            prev_nose = None
            prev_gaze = None
            last_blink_ts = 0.0

            print(f"▶️ START collecte: session={session_id} question={question_id}")

        # End collecte + sauvegarde
        if key in [ord('e'), ord('E')] and collecting:
            collecting = False
            end_ts = time.time()
            duration_s = max(end_ts - start_ts, 1e-6)

            eye_mean, eye_std = mean_std(eye_open_vals)
            head_mean, head_std = mean_std(head_move_vals)
            gaze_mean, gaze_std = mean_std(gaze_move_vals)

            blink_rate = blink_count / duration_s

            row = {
                "session_id": session_id,
                "question_id": question_id,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "duration_s": duration_s,
                "blink_count": blink_count,
                "blink_rate": blink_raste,
                "eye_open_mean": eye_mean,
                "eye_open_std": eye_std,
                "head_move_mean": head_mean,
                "head_move_std": head_std,
                "gaze_move_mean": gaze_mean,
                "gaze_move_std": gaze_std,
            }

            with open(out_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(row.keys()))
                if not file_exists:
                    writer.writeheader()
                    file_exists = True
                writer.writerow(row)

            print("✅ SAVED features:", row)
            print(f"📄 File: {out_file}\n")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

