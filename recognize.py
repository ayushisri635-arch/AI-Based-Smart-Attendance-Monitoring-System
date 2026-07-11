"""
recognize.py
-------------
Opens the webcam, recognizes faces using the trained LBPH model,
and marks attendance in the database for recognized people.

Run standalone:
    python recognize.py

Or import run_recognition() from app.py for a web-triggered flow.
"""

import cv2
import os
import json
import database as db

TRAINER_FILE = os.path.join("trainer", "trainer.yml")
LABELS_FILE = os.path.join("trainer", "labels.json")
FACE_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

CONFIDENCE_THRESHOLD = 70  # LBPH: LOWER distance = more confident match. Tune as needed.


def load_model():
    if not os.path.exists(TRAINER_FILE) or not os.path.exists(LABELS_FILE):
        raise RuntimeError("Model not found. Run train_model.py first.")

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(TRAINER_FILE)

    with open(LABELS_FILE, "r") as f:
        raw_labels = json.load(f)
    # JSON keys are strings; convert back to int
    label_map = {int(k): v for k, v in raw_labels.items()}

    return recognizer, label_map


def run_recognition(camera_index=0, show_window=True):
    """Runs live recognition. Returns a list of (person_code, name) marked present
    during this session."""

    recognizer, label_map = load_model()
    face_detector = cv2.CascadeClassifier(FACE_CASCADE_PATH)
    cam = cv2.VideoCapture(camera_index)

    if not cam.isOpened():
        raise RuntimeError("Could not open webcam.")

    marked_this_session = set()
    print("[INFO] Starting recognition. Press Q to quit.")

    while True:
        ret, frame = cam.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)

        for (x, y, w, h) in faces:
            face_img = cv2.resize(gray[y:y + h, x:x + w], (200, 200))
            label_id, confidence = recognizer.predict(face_img)

            if confidence < CONFIDENCE_THRESHOLD and label_id in label_map:
                person_code = label_map[label_id]["person_code"]
                name = label_map[label_id]["name"]
                display_text = f"{name} ({confidence:.0f})"
                color = (0, 255, 0)

                if person_code not in marked_this_session:
                    person = db.get_person_by_code(person_code)
                    if person:
                        created = db.mark_attendance(person["id"])
                        marked_this_session.add(person_code)
                        if created:
                            print(f"[ATTENDANCE] Marked present: {name} ({person_code})")
                        else:
                            print(f"[INFO] {name} already marked today.")
            else:
                display_text = "Unknown"
                color = (0, 0, 255)

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, display_text, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        if show_window:
            cv2.imshow("Attendance - Press Q to quit", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cam.release()
    cv2.destroyAllWindows()
    return list(marked_this_session)


if __name__ == "__main__":
    run_recognition()
