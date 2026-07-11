"""
database.py
------------
Handles all SQLite database operations for the Face Recognition
Attendance System: user accounts (for login), registered people
(students/employees), and attendance logs.
"""

import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

DB_PATH = "attendance.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't already exist."""
    conn = get_connection()
    cur = conn.cursor()

    # Admin / operator login accounts (people who use the dashboard)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # People registered for face recognition (students / employees)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_code TEXT UNIQUE NOT NULL,   -- e.g. roll no / employee id
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Attendance records
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            FOREIGN KEY (person_id) REFERENCES people (id),
            UNIQUE(person_id, date)  -- one attendance entry per person per day
        )
    """)

    conn.commit()

    # Create a default admin account if none exists yet
    cur.execute("SELECT COUNT(*) as c FROM accounts")
    if cur.fetchone()["c"] == 0:
        cur.execute(
            "INSERT INTO accounts (username, password_hash, created_at) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("admin123"), datetime.now().isoformat()),
        )
        conn.commit()
        print("Default admin account created -> username: admin | password: admin123")

    conn.close()


# ---------------- People (registered faces) ----------------

def add_person(person_code, name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO people (person_code, name, created_at) VALUES (?, ?, ?)",
        (person_code, name, datetime.now().isoformat()),
    )
    conn.commit()
    person_id = cur.lastrowid
    conn.close()
    return person_id


def get_person_by_code(person_code):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM people WHERE person_code = ?", (person_code,))
    row = cur.fetchone()
    conn.close()
    return row


def get_person_by_id(person_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM people WHERE id = ?", (person_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_all_people():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM people ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------- Attendance ----------------

def mark_attendance(person_id):
    """Insert an attendance record for today if one doesn't already exist.
    Returns True if a new record was created, False if already marked."""
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M:%S")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO attendance (person_id, date, time) VALUES (?, ?, ?)",
            (person_id, today, now_time),
        )
        conn.commit()
        created = True
    except sqlite3.IntegrityError:
        # Already marked today
        created = False
    conn.close()
    return created


def get_attendance_by_date(date_str=None):
    """Return attendance rows joined with person info for a given date
    (defaults to today)."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, p.person_code, p.name, a.date, a.time
        FROM attendance a
        JOIN people p ON a.person_id = p.id
        WHERE a.date = ?
        ORDER BY a.time
    """, (date_str,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_attendance():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, p.person_code, p.name, a.date, a.time
        FROM attendance a
        JOIN people p ON a.person_id = p.id
        ORDER BY a.date DESC, a.time DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------- Accounts (dashboard login) ----------------

def get_account_by_username(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row


if __name__ == "__main__":
    init_db()
    print("Database initialized at", DB_PATH)
