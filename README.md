# Face Recognition Attendance System

A Flask web app that uses OpenCV (Haar cascade + LBPH) to register faces,
train a recognizer, and mark attendance automatically via webcam.

> **Important:** This app opens the webcam **on the machine running the
> Flask server** (via OpenCV, `cv2.VideoCapture`). It's designed to run on
> a local PC/kiosk with a camera attached — not to access a remote
> visitor's browser camera over the internet.

---

## 1. Project structure

```
FaceRecognitionAttendance/
├── app.py              # Flask app (routes, login, dashboard)
├── database.py         # SQLite schema + queries
├── capture_faces.py    # Webcam face capture for enrollment
├── train_model.py      # Trains the LBPH recognizer
├── recognize.py        # Live recognition + attendance marking
├── requirements.txt
├── dataset/            # Captured face images (auto-created, per person)
├── trainer/            # trainer.yml + labels.json (auto-created)
├── attendance.db        # SQLite DB (auto-created on first run)
├── static/css/style.css
├── static/js/script.js
└── templates/*.html
```

## 2. Prerequisites

- Python 3.9–3.11 (OpenCV wheels are most reliable on these versions)
- A webcam connected to the machine that will run the server
- Windows / macOS / Linux — all fine, as long as OpenCV can access the camera

## 3. Setup steps

**Step 1 — Create and activate a virtual environment**

```bash
cd FaceRecognitionAttendance
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

**Step 2 — Install dependencies**

```bash
pip install -r requirements.txt
```

If `cv2.face` errors out with `AttributeError: module 'cv2' has no
attribute 'face'`, it means only `opencv-python` got installed somewhere
instead of `opencv-contrib-python`. Fix with:

```bash
pip uninstall opencv-python opencv-python-headless opencv-contrib-python -y
pip install opencv-contrib-python==4.10.0.84
```

**Step 3 — Initialize the database**

```bash
python database.py
```

This creates `attendance.db` and prints a default login:

```
username: admin
password: admin123
```

**Step 4 — Run the app**

```bash
python app.py
```

Visit **http://localhost:5000** in your browser and log in with the
credentials above.

**Step 5 — Register people**

Go to **Register**, enter a person code (roll no. / employee ID) and name,
then click **Start Face Capture**. A webcam window opens on the server
machine — look at the camera from a few angles until ~50 samples are
captured, or press `Q` to stop early.

Repeat for everyone you want the system to recognize.

**Step 6 — Train the model**

Click **Train Model** (on the Register or Dashboard page). This reads
every image in `dataset/` and writes `trainer/trainer.yml` +
`trainer/labels.json`.

**Step 7 — Run attendance scanning**

Go to **Attendance → Start Scan**. The webcam opens; anyone recognized
with sufficient confidence is automatically marked present for today
(one entry per person per day). Press `Q` in the camera window to end
the session.

**Step 8 — View records**

- **Dashboard** — total registered people + today's attendance count
- **Attendance** — full attendance table, filterable by date via
  `/attendance?date=YYYY-MM-DD`

## 4. Re-training after adding new people

Every time you register someone new, click **Train Model** again — the
recognizer is retrained from scratch on the full `dataset/` folder, so it
always reflects everyone currently enrolled.

## 5. Tuning recognition accuracy

In `recognize.py`:

```python
CONFIDENCE_THRESHOLD = 70
```

LBPH confidence is actually a **distance** — lower means a more
confident match. If you're getting false positives, lower this number
(e.g. `50`). If real people aren't being recognized, raise it (e.g. `90`).

## 6. Common issues

| Problem | Fix |
|---|---|
| Webcam won't open | Check `camera_index=0` in `capture_faces.py`/`recognize.py` — try `1` if you have multiple cameras |
| `cv2.face` not found | Reinstall `opencv-contrib-python` (see Step 2) |
| Everyone recognized as "Unknown" | Re-run **Train Model**; ensure `dataset/` has images for that person |
| Same person marked twice in a day | Not possible — `attendance` table has a `UNIQUE(person_id, date)` constraint |
| Camera window opens behind the browser | Click the camera window / check your taskbar — it opens on the server desktop, not in-browser |

## 7. Security notes for production use

- Change `app.secret_key` in `app.py`
- Change the default admin password immediately (add a "change password"
  flow, or update the hash directly in the `accounts` table)
- Run behind HTTPS if exposing beyond localhost
- This demo stores plain grayscale face crops in `dataset/` — consider
  encryption-at-rest or access controls if handling real biometric data
