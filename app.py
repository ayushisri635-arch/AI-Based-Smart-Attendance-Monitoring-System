"""
app.py
-------
Main Flask application for the Face Recognition Attendance System.

Routes:
    /login          - login page for dashboard access
    /logout         - log out
    /               - home / index page
    /register       - register a new person + capture face samples
    /train          - (re)train the recognition model
    /recognize      - run live recognition & mark attendance
    /attendance     - view today's attendance
    /dashboard      - overview: people count, attendance history

NOTE: This app opens the machine's LOCAL webcam (the one attached to the
server/computer running Flask) via OpenCV — it is designed to run on a
single local machine (e.g. a front-desk kiosk PC), not to access a
remote visitor's browser camera. For browser-camera capture you would
additionally need getUserMedia + image upload endpoints.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import check_password_hash

import database as db
from capture_faces import capture_faces
from train_model import train_model
from recognize import run_recognition

app = Flask(__name__)
app.secret_key = "change-this-secret-key-in-production"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class Account(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]


@login_manager.user_loader
def load_user(user_id):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return Account(row) if row else None


# ---------------- Auth ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        account_row = db.get_account_by_username(username)
        if account_row and check_password_hash(account_row["password_hash"], password):
            login_user(Account(account_row))
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------- Core pages ----------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
@login_required
def register():
    if request.method == "POST":
        person_code = request.form.get("person_code", "").strip()
        name = request.form.get("name", "").strip()

        if not person_code or not name:
            flash("Person code and name are required.", "error")
            return redirect(url_for("register"))

        if db.get_person_by_code(person_code):
            flash("A person with that code is already registered.", "error")
            return redirect(url_for("register"))

        try:
            # Opens the local webcam and captures ~50 face samples
            num_captured = capture_faces(person_code, name)
            db.add_person(person_code, name)
            flash(f"Captured {num_captured} images for {name}. "
                  f"Now click 'Train Model' before recognizing.", "success")
        except Exception as e:
            flash(f"Error capturing faces: {e}", "error")

        return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/train", methods=["POST"])
@login_required
def train():
    try:
        train_model()
        flash("Model trained successfully.", "success")
    except Exception as e:
        flash(f"Training failed: {e}", "error")
    return redirect(url_for("dashboard"))


@app.route("/recognize", methods=["GET", "POST"])
@login_required
def recognize():
    marked = []
    if request.method == "POST":
        try:
            marked = run_recognition()
            flash(f"Recognition session ended. Marked {len(marked)} people present.", "success")
        except Exception as e:
            flash(f"Recognition failed: {e}", "error")
    return render_template("attendance.html", marked=marked, records=db.get_attendance_by_date())


@app.route("/attendance")
@login_required
def attendance():
    date_filter = request.args.get("date")
    records = db.get_attendance_by_date(date_filter) if date_filter else db.get_all_attendance()
    return render_template("attendance.html", records=records, marked=[])


@app.route("/dashboard")
@login_required
def dashboard():
    people = db.get_all_people()
    todays_attendance = db.get_attendance_by_date()
    return render_template(
        "dashboard.html",
        people_count=len(people),
        people=people,
        todays_attendance=todays_attendance,
    )


# ---------------- JSON API (optional, handy for AJAX/testing) ----------------

@app.route("/api/attendance/today")
@login_required
def api_attendance_today():
    records = db.get_attendance_by_date()
    return jsonify([dict(r) for r in records])


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
