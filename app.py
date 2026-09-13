import csv
import io
import json
import os
import random
import re
import secrets
import sqlite3
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import Flask, Response, abort, flash, jsonify, redirect, render_template, request, session, url_for

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.environ.get("SQLITE_PATH", os.path.join(BASE_DIR, "quiz_database.db"))
SECRET_KEY = os.environ.get("SECRET_KEY", "DiplomaQuizPortal_SecuredSecretKey_2026_99X!")
TEACHER_USERNAME = os.environ.get("TEACHER_USERNAME", "admin")
TEACHER_PASSWORD = os.environ.get("TEACHER_PASSWORD", "QuizPortal#2026!SecureKey99")
DEFAULT_DURATION = int(os.environ.get("EXAM_DURATION_MINUTES", "45"))

# Optional PDF text extraction. No cloud service or AI model is required.
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
try:
    from docx import Document
except ImportError:
    Document = None

app = Flask(__name__)
app.config.update(SECRET_KEY=SECRET_KEY, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
if os.environ.get("COOKIE_SECURE", "0") == "1":
    app.config["SESSION_COOKIE_SECURE"] = True

@app.errorhandler(500)
def internal_server_error(error):
    app.logger.exception("Unhandled application error: %s", error)
    return render_template("error.html", message="Something went wrong on the server. Please try again."), 500

SEED_QUESTIONS = [
    ("Digital Electronics (302)", "A circuit in which the output depends only on the present input is called", "Sequential circuit", "Combinational circuit", "Counter", "Register", "B"),
    ("Digital Electronics (302)", "A 4-to-1 multiplexer requires how many select lines?", "1", "2", "3", "4", "B"),
    ("Digital Electronics (302)", "A multiplexer is also called a", "Data distributor", "Data selector", "Code converter", "Decoder", "B"),
    ("Digital Electronics (302)", "A 1-to-4 demultiplexer requires", "1 select line", "2 select lines", "3 select lines", "4 select lines", "B"),
    ("Digital Electronics (302)", "The main function of a demultiplexer is to", "Select one input from many", "Send one input to one of many outputs", "Convert binary to decimal", "Store data", "B"),
    ("Digital Electronics (302)", "An 8-to-3 encoder has", "8 inputs and 3 outputs", "3 inputs and 8 outputs", "8 inputs and 8 outputs", "3 inputs and 3 outputs", "A"),
    ("Digital Electronics (302)", "A decoder with 3 input lines has a maximum of", "3 outputs", "6 outputs", "8 outputs", "9 outputs", "C"),
    ("Digital Electronics (302)", "A half adder has", "2 inputs and 1 output", "2 inputs and 2 outputs", "3 inputs and 2 outputs", "3 inputs and 3 outputs", "B"),
    ("Digital Electronics (302)", "The outputs of a half adder are", "Sum and Carry", "Difference and Borrow", "Product and Carry", "Sum and Borrow", "A"),
    ("Digital Electronics (302)", "A full adder has", "2 inputs", "3 inputs", "4 inputs", "5 inputs", "B"),
    ("Data Structures Through C (303)", "Bubble Sort works by repeatedly:", "Selecting the smallest element", "Swapping adjacent elements if out of order", "Dividing array into halves", "Using a pivot element", "B"),
    ("Data Structures Through C (303)", "Best case time complexity of Insertion Sort is:", "O(n²)", "O(n log n)", "O(n)", "O(1)", "C"),
    ("Data Structures Through C (303)", "Which sorting algorithm always has O(n²) complexity in best, average, and worst cases?", "Bubble Sort", "Selection Sort", "Quick Sort", "Merge Sort", "B"),
    ("Data Structures Through C (303)", "In Quick Sort, the worst case occurs when:", "Pivot is always the middle element", "Pivot is always the smallest or largest element", "Array is already sorted", "Array is random", "B"),
    ("Data Structures Through C (303)", "Binary Search requires:", "Unsorted array", "Linked list", "Sorted array", "Hash table", "C"),
    ("Data Structures Through C (303)", "A stack follows which principle?", "FIFO", "LIFO", "FILO", "None", "B"),
    ("Data Structures Through C (303)", "Infix expression (A+B)*C converts to postfix as:", "AB+C*", "A+BC", "ABC+", "A*B+C", "A"),
    ("Data Structures Through C (303)", "Which of the following is an application of queues?", "Undo/Redo in editors", "CPU scheduling", "Parenthesis matching", "Function recursion", "B"),
    ("Data Structures Through C (303)", "Condition for circular queue full is:", "front == rear", "rear == MAX-1", "(rear + 1) % MAX == front", "front == -1", "C"),
    ("Data Structures Through C (303)", "While evaluating postfix expression, when an operator is encountered:", "Push it onto stack", "Pop required operands, apply operator, push result", "Add it directly to result", "Ignore it", "B"),
    ("OOPS Through C++ (304)", "Which mode deletes all existing contents before writing?", "ios::app", "ios::trunc", "ios::ate", "ios::in", "B"),
    ("OOPS Through C++ (304)", "What is the purpose of ws manipulator?", "Writes string", "Ignores leading white spaces before reading input", "Aligns output to left", "Displays in hex", "B"),
    ("OOPS Through C++ (304)", 'What does file.open("student.txt", ios::out | ios::in) and seekg(3) do?', "Opens file only for reading and seekg moves put pointer", "Opens for both reading & writing, seekg(3) moves get pointer to position 3 for reading", "Deletes file and creates new one", "Appends data at end", "B"),
    ("OOPS Through C++ (304)", "Which class hierarchy is correct?", "ios is base, istream/ostream derived from ios, iostream derived from istream+ostream, ifstream derived from istream, ofstream from ostream, fstream from iostream", "fstream is base of all", "iostream is base of ios", "ifstream and ofstream are base", "A"),
    ("OOPS Through C++ (304)", "Which header is needed for setw() and setprecision()?", "<iostream>", "<iomanip>", "<fstream>", "<conio.h>", "B"),
    ("OOPS Through C++ (304)", "What is the name and return type of Constructor?", "Different name from class, returns void", "Same name as class, no return type not even void", "Same name as class, returns int", "Starts with ~ and no return type", "B"),
    ("OOPS Through C++ (304)", "What is Constructor Overloading?", "Having one constructor only", "One class having multiple constructors with different parameters", "Deleting constructor", "Same as Destructor", "B"),
    ("OOPS Through C++ (304)", "Find Error: class A{ public: ~A(int x){} };", "No error", "Destructor cannot take arguments", "Destructor needs return type", "~ wrong", "B"),
    ("OOPS Through C++ (304)", "You have: Student(), Student(string name), Student(string name, int age). You create Student s; Which constructor is called?", "Second", "First - 0 arguments - Default constructor", "Third", "All three", "B"),
    ("OOPS Through C++ (304)", "new does what?", "Deletes", "Allocates memory in heap", "Copies", "Nothing", "B"),
    ("Computer Organisation & Architecture (305)", "Which register stores the address of the next instruction to be executed?", "IR", "PC", "MAR", "MDR", "B"),
    ("Computer Organisation & Architecture (305)", "In immediate addressing mode, the operand is:", "Stored in memory", "Stored in a register", "Given directly in the instruction", "Stored in cache", "C"),
    ("Computer Organisation & Architecture (305)", "Which addressing mode calculates the effective address by adding a base register and an index register?", "Immediate addressing", "Direct addressing", "Indexed addressing", "Implied addressing", "C"),
    ("Computer Organisation & Architecture (305)", "Consider the instruction: MOV R1, [R2 + 20]. If R2 contains 1000, what is the effective address of the operand?", "980", "1000", "1020", "2020", "C"),
    ("Computer Organisation & Architecture (305)", "Which addressing mode is most suitable for accessing elements of an array using a base address and an index?", "Immediate addressing", "Indexed addressing", "Implied addressing", "Direct addressing", "B"),
    ("Computer Organisation & Architecture (305)", "Which memory is the fastest among the following?", "Magnetic Disk", "Main Memory", "Cache Memory", "Secondary Memory", "C"),
    ("Computer Organisation & Architecture (305)", "Which type of memory loses its contents when power is switched off?", "Non-volatile memory", "Volatile memory", "Secondary memory", "Optical memory", "B"),
    ("Computer Organisation & Architecture (305)", "In which cache mapping technique can a main memory block be placed in any cache line?", "Direct Mapping", "Associative Mapping", "Set-Associative Mapping", "Sequential Mapping", "B"),
    ("Computer Organisation & Architecture (305)", "A system uses a 32-bit address and has a cache organized into sets. If the cache uses set-associative mapping, which components are generally used to determine the location of a block?", "Tag, set index and word/byte offset", "Only tag", "Only offset", "Opcode and operand", "A"),
    ("Computer Organisation & Architecture (305)", "Which statement correctly describes virtual memory?", "It completely replaces cache memory", "It allows programs larger than physical main memory to execute", "It is faster than cache memory", "It is used only for permanent storage", "B"),
    ("Computer Networks (306)", "What is the main purpose of the Data Link Layer?", "Frame-to-frame communication", "Creating websites", "Storing files", "Managing passwords", "A"),
    ("Computer Networks (306)", "Which part of a frame contains the actual information?", "Header", "Data/Payload", "Trailer", "Address", "B"),
    ("Computer Networks (306)", "In Stop-and-Wait, the sender waits for a", "ACK", "MAC address", "Router", "Port number", "A"),
    ("Computer Networks (306)", "Which IEEE standard is used for Ethernet?", "802.3", "802.11", "802.15", "802.16", "A"),
    ("Computer Networks (306)", "What is a Bluetooth network formed by one master and active slaves called?", "LAN", "Piconet", "WAN", "Ethernet", "B"),
    ("Computer Networks (306)", "Which Bluetooth protocol is used to discover available services?", "SDP", "ARP", "CRC", "RARP", "A"),
    ("Computer Networks (306)", "Which address identifies a network interface/device at the Data Link Layer?", "Port address", "MAC address", "IP address", "Website address", "B"),
    ("Computer Networks (306)", "Which address is used at the Network Layer?", "IP address", "MAC address", "Port address", "Frame address", "A"),
    ("Computer Networks (306)", "Which protocol finds the MAC address from an IP address?", "RARP", "ARP", "FTP", "HTTP", "B"),
    ("Computer Networks (306)", "Which routing method sends packets through all possible paths?", "Flooding", "Static routing", "Subnetting", "ARP", "A"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS exams (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL DEFAULT '',
  duration_minutes INTEGER NOT NULL DEFAULT 45,
  active INTEGER NOT NULL DEFAULT 1,
  started INTEGER NOT NULL DEFAULT 0,
  allow_review INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS questions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
  subject TEXT NOT NULL DEFAULT 'General',
  question_text TEXT NOT NULL,
  option_a TEXT NOT NULL,
  option_b TEXT NOT NULL,
  option_c TEXT NOT NULL,
  option_d TEXT NOT NULL,
  correct_option TEXT NOT NULL CHECK(correct_option IN ('A','B','C','D')),
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
  student_pin TEXT NOT NULL,
  student_name TEXT NOT NULL,
  score INTEGER NOT NULL,
  total_questions INTEGER NOT NULL,
  time_taken_seconds INTEGER NOT NULL,
  submitted_at TEXT NOT NULL,
  answers_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(exam_id, student_pin)
);
CREATE INDEX IF NOT EXISTS idx_questions_exam ON questions(exam_id);
CREATE INDEX IF NOT EXISTS idx_submissions_exam ON submissions(exam_id);
CREATE INDEX IF NOT EXISTS idx_submissions_exam_rank ON submissions(exam_id, score DESC, time_taken_seconds ASC);
"""


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def db_conn():
    os.makedirs(os.path.dirname(DATABASE) or ".", exist_ok=True)
    conn = sqlite3.connect(DATABASE, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def init_db():
    conn = db_conn()
    conn.executescript(SCHEMA)
    # Check if started and allow_review columns exist in existing DBs
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(exams)").fetchall()]
    if "started" not in cols:
        conn.execute("ALTER TABLE exams ADD COLUMN started INTEGER NOT NULL DEFAULT 0")
    if "allow_review" not in cols:
        conn.execute("ALTER TABLE exams ADD COLUMN allow_review INTEGER NOT NULL DEFAULT 0")

    sub_cols = [r["name"] for r in conn.execute("PRAGMA table_info(submissions)").fetchall()]
    if "answers_json" not in sub_cols:
        conn.execute("ALTER TABLE submissions ADD COLUMN answers_json TEXT NOT NULL DEFAULT '{}'")

    exam_count = conn.execute("SELECT COUNT(*) FROM exams").fetchone()[0]
    if exam_count == 0:
        cur = conn.execute("INSERT INTO exams(title,description,duration_minutes,active,started,allow_review,created_at) VALUES(?,?,?,?,?,?,?)",
                           ("Diploma Core Subjects — Model Assessment",
                            "50 MCQs covering Digital Electronics, Data Structures, OOPS, COA and Computer Networks.",
                            DEFAULT_DURATION, 1, 0, 0, now_iso()))
        exam_id = cur.lastrowid
        conn.executemany("""INSERT INTO questions(exam_id,subject,question_text,option_a,option_b,option_c,option_d,correct_option,created_at)
                           VALUES(?,?,?,?,?,?,?,?,?)""",
                          [(exam_id, *q, now_iso()) for q in SEED_QUESTIONS])
    conn.commit()
    conn.close()


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


@app.context_processor
def globals_for_templates():
    return {"csrf_token": csrf_token()}


def check_csrf():
    if app.config.get("TESTING"):
        return True
    supplied = request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")
    return bool(supplied and expected and secrets.compare_digest(supplied, expected))


def teacher_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if session.get("role") != "teacher":
            flash("Please log in as a teacher first.", "error")
            return redirect(url_for("teacher_login_page"))
        return fn(*args, **kwargs)
    return wrapped


def student_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if session.get("role") != "student":
            return redirect(url_for("home"))
        return fn(*args, **kwargs)
    return wrapped


@app.get("/")
def home():
    conn = db_conn()
    exams = conn.execute("SELECT e.*, COUNT(q.id) AS question_count FROM exams e LEFT JOIN questions q ON q.exam_id=e.id WHERE e.active=1 GROUP BY e.id ORDER BY e.id DESC").fetchall()
    conn.close()
    return render_template("login.html", exams=exams)


@app.get("/teacher_login")
def teacher_login_page():
    return render_template("teacher_login.html")


@app.post("/login")
def login():
    if not check_csrf(): abort(400, "Invalid form token")
    role = request.form.get("role")
    if role == "teacher":
        username = request.form.get("teacher_user", "")
        password = request.form.get("teacher_pass", "")
        if secrets.compare_digest(username, TEACHER_USERNAME) and secrets.compare_digest(password, TEACHER_PASSWORD):
            session.clear(); session["role"] = "teacher"; csrf_token()
            return redirect(url_for("teacher_dashboard"))
        flash("Invalid teacher username or password.", "error")
        return redirect(url_for("teacher_login_page"))

    if role == "student":
        pin = request.form.get("student_pin", "").strip()
        name = request.form.get("student_name", "").strip()
        exam_id = request.form.get("exam_id", type=int)
        if not (3 <= len(pin) <= 80) or not name or len(name) > 120:
            flash("Enter a valid student PIN and full name.", "error"); return redirect(url_for("home"))
        conn = db_conn()
        exam = conn.execute("SELECT * FROM exams WHERE id=? AND active=1", (exam_id,)).fetchone()
        existing = conn.execute("SELECT * FROM submissions WHERE exam_id=? AND student_pin=?", (exam_id, pin)).fetchone()
        questions = conn.execute("SELECT * FROM questions WHERE exam_id=?", (exam_id,)).fetchall()
        if not exam:
            conn.close(); flash("That exam is not currently available.", "error"); return redirect(url_for("home"))
        if existing:
            # Discreetly load student's result & answer review page
            user_answers = {}
            if existing["answers_json"]:
                try: user_answers = json.loads(existing["answers_json"])
                except Exception: pass

            review_data = []
            for q in questions:
                ans = user_answers.get(str(q["id"]))
                is_cor = (ans == q["correct_option"])
                review_data.append({
                    "id": q["id"],
                    "question": q["question_text"],
                    "subject": q["subject"],
                    "A": q["option_a"],
                    "B": q["option_b"],
                    "C": q["option_c"],
                    "D": q["option_d"],
                    "selected": ans,
                    "correct": q["correct_option"],
                    "is_correct": is_cor
                })

            raw_subs = conn.execute("SELECT * FROM submissions WHERE exam_id=?", (exam_id,)).fetchall()
            subs, first_topper, second_topper, third_topper, exam_avg_pct, tier_counts, tier_pcts = process_submissions_analytics(raw_subs)
            student_sub = next((s for s in subs if s["student_pin"] == pin), None)

            conn.close()
            session.clear()
            return render_template("result.html", score=existing["score"], total=existing["total_questions"],
                                   name=existing["student_name"], exam=exam, review_data=review_data,
                                   student_sub=student_sub, first_topper=first_topper, second_topper=second_topper,
                                   exam_avg_pct=exam_avg_pct, total_submissions=len(subs),
                                   allow_review=bool(exam["allow_review"]))
        conn.close()
        if not questions:
            flash("This exam has no questions yet.", "error"); return redirect(url_for("home"))
        ids = [q[0] for q in questions]; random.shuffle(ids)
        session.clear()
        session.update(role="student", student_pin=pin, student_name=name, exam_id=exam_id, question_ids=ids)
        csrf_token()
        if exam["started"] == 1:
            session["exam_started_at"] = now_iso()
            return redirect(url_for("student_quiz"))
        return redirect(url_for("student_lobby"))
    flash("Invalid login request.", "error")
    return redirect(url_for("home"))


@app.get("/lobby")
@student_required
def student_lobby():
    conn = db_conn()
    exam_id = session.get("exam_id")
    if not exam_id:
        conn.close()
        session.clear()
        flash("Session expired. Please log in with your PIN again.", "error")
        return redirect(url_for("home"))
    exam = conn.execute("SELECT * FROM exams WHERE id=?", (exam_id,)).fetchone()
    conn.close()
    if not exam:
        session.clear()
        flash("Exam not found.", "error")
        return redirect(url_for("home"))
    if exam["started"] == 1:
        if "exam_started_at" not in session:
            session["exam_started_at"] = now_iso()
        return redirect(url_for("student_quiz"))
    return render_template("student_lobby.html", exam=exam, student_pin=session["student_pin"], student_name=session["student_name"])


@app.post("/teacher/exams/<int:exam_id>/start_live")
@teacher_required
def start_live_exam(exam_id):
    if not check_csrf(): abort(400, "Invalid form token")
    conn = db_conn()
    exam = conn.execute("SELECT id, title FROM exams WHERE id=?", (exam_id,)).fetchone()
    if not exam: conn.close(); abort(404)
    conn.execute("UPDATE exams SET started=1, active=1 WHERE id=?", (exam_id,))
    conn.commit(); conn.close()
    flash(f"🚀 Live Exam Launched! '{exam['title']}' is now live for all student devices.", "success")
    return redirect(url_for("teacher_dashboard", exam_id=exam_id))


@app.post("/teacher/exams/<int:exam_id>/reset_lobby")
@teacher_required
def reset_lobby_exam(exam_id):
    if not check_csrf(): abort(400, "Invalid form token")
    conn = db_conn()
    exam = conn.execute("SELECT id, title FROM exams WHERE id=?", (exam_id,)).fetchone()
    if not exam: conn.close(); abort(404)
    conn.execute("UPDATE exams SET started=0 WHERE id=?", (exam_id,))
    conn.commit(); conn.close()
    flash(f"⏸️ Assessment '{exam['title']}' reset to Student Waiting Lobby mode.", "success")
    return redirect(url_for("teacher_dashboard", exam_id=exam_id))


@app.post("/teacher/exams/<int:exam_id>/toggle_review")
@teacher_required
def toggle_exam_review(exam_id):
    if not check_csrf(): abort(400, "Invalid form token")
    conn = db_conn()
    exam = conn.execute("SELECT id, title, allow_review FROM exams WHERE id=?", (exam_id,)).fetchone()
    if not exam: conn.close(); abort(404)
    new_state = 0 if exam["allow_review"] == 1 else 1
    conn.execute("UPDATE exams SET allow_review=? WHERE id=?", (new_state, exam_id))
    conn.commit(); conn.close()
    msg = f"🔓 Answer Review Unlocked for students taking '{exam['title']}'." if new_state == 1 else f"🔒 Answer Review Locked for students taking '{exam['title']}'."
    flash(msg, "success")
    return redirect(url_for("teacher_dashboard", exam_id=exam_id))


@app.get("/api/exam_status/<int:exam_id>")
def api_exam_status(exam_id):
    conn = db_conn()
    exam = conn.execute("SELECT started, active, allow_review FROM exams WHERE id=?", (exam_id,)).fetchone()
    conn.close()
    if not exam:
        return jsonify({"status": "error", "message": "Exam not found"}), 404
    return jsonify({"status": "success", "started": bool(exam["started"]), "active": bool(exam["active"]), "allow_review": bool(exam["allow_review"])})


def process_submissions_analytics(submissions_rows):
    """
    Process raw submissions rows for an assessment:
    - Sorts by score percentage (DESC) and time taken (ASC)
    - Computes 1-based ranks
    - Assigns performance tiers: 1st Topper, 2nd Topper, 3rd Topper, Above Average, Average, Needs Support
    - Calculates overall exam average score percentage
    - Returns (ranked_submissions, first_topper, second_topper, third_topper, exam_avg_pct, tier_counts)
    """
    if not submissions_rows:
        empty_counts = {"toppers": 0, "above_avg": 0, "average": 0, "below_avg": 0}
        return [], None, None, None, 0.0, empty_counts, empty_counts

    items = []
    total_pct_sum = 0.0
    for r in submissions_rows:
        d = dict(r)
        tot = d.get("total_questions") or 0
        score = d.get("score") or 0
        pct = round((score * 100.0 / tot), 1) if tot > 0 else 0.0
        d["pct"] = pct
        total_pct_sum += pct
        items.append(d)

    exam_avg_pct = round(total_pct_sum / len(items), 1)

    # Sort by score percentage DESC, then time_taken_seconds ASC (faster completion breaks ties)
    items.sort(key=lambda x: (-x["pct"], x["time_taken_seconds"], x["id"]))

    tier_counts = {"toppers": 0, "above_avg": 0, "average": 0, "below_avg": 0}

    for idx, item in enumerate(items, 1):
        item["rank"] = idx
        pct = item["pct"]
        if idx == 1:
            item["tier"] = "1st Topper"
            item["tier_code"] = "topper_1"
            item["badge_class"] = "badge-topper-gold"
            item["tier_icon"] = "🥇"
            tier_counts["toppers"] += 1
        elif idx == 2:
            item["tier"] = "2nd Topper"
            item["tier_code"] = "topper_2"
            item["badge_class"] = "badge-topper-silver"
            item["tier_icon"] = "🥈"
            tier_counts["toppers"] += 1
        elif idx == 3:
            item["tier"] = "3rd Topper"
            item["tier_code"] = "topper_3"
            item["badge_class"] = "badge-topper-bronze"
            item["tier_icon"] = "🥉"
            tier_counts["above_avg"] += 1
        elif pct > exam_avg_pct:
            item["tier"] = "Above Average"
            item["tier_code"] = "above_avg"
            item["badge_class"] = "badge-above-avg"
            item["tier_icon"] = "📈"
            tier_counts["above_avg"] += 1
        elif pct >= max(0.0, exam_avg_pct - 10.0):
            item["tier"] = "Average"
            item["tier_code"] = "average"
            item["badge_class"] = "badge-avg"
            item["tier_icon"] = "📊"
            tier_counts["average"] += 1
        else:
            item["tier"] = "Needs Support"
            item["tier_code"] = "below_avg"
            item["badge_class"] = "badge-below-avg"
            item["tier_icon"] = "💡"
            tier_counts["below_avg"] += 1

    first_topper = items[0] if len(items) >= 1 else None
    second_topper = items[1] if len(items) >= 2 else None
    third_topper = items[2] if len(items) >= 3 else None

    total_subs = len(items)
    tier_pcts = {
        "toppers": round(tier_counts["toppers"] / total_subs * 100, 1) if total_subs else 0,
        "above_avg": round(tier_counts["above_avg"] / total_subs * 100, 1) if total_subs else 0,
        "average": round(tier_counts["average"] / total_subs * 100, 1) if total_subs else 0,
        "below_avg": round(tier_counts["below_avg"] / total_subs * 100, 1) if total_subs else 0,
    }

    return items, first_topper, second_topper, third_topper, exam_avg_pct, tier_counts, tier_pcts


@app.get("/teacher")
@teacher_required
def teacher_dashboard():
    conn = db_conn()
    exams = conn.execute("SELECT e.*, COUNT(q.id) AS question_count FROM exams e LEFT JOIN questions q ON q.exam_id=e.id GROUP BY e.id ORDER BY e.id DESC").fetchall()
    selected_id = request.args.get("exam_id", type=int) or (exams[0]["id"] if exams else None)
    selected = conn.execute("SELECT * FROM exams WHERE id=?", (selected_id,)).fetchone() if selected_id else None
    questions = conn.execute("SELECT * FROM questions WHERE exam_id=? ORDER BY id", (selected_id,)).fetchall() if selected else []
    raw_submissions = conn.execute("SELECT * FROM submissions WHERE exam_id=? ORDER BY id DESC", (selected_id,)).fetchall() if selected else []
    submissions, first_topper, second_topper, third_topper, exam_avg_pct, tier_counts, tier_pcts = process_submissions_analytics(raw_submissions)
    total_students = conn.execute("SELECT COUNT(DISTINCT student_pin) FROM submissions").fetchone()[0]
    total_attempts = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    overall_avg = conn.execute("SELECT AVG(score * 100.0 / NULLIF(total_questions,0)) FROM submissions").fetchone()[0] or 0
    conn.close()
    return render_template("teacher_dashboard.html", exams=exams, selected_exam=selected, questions=questions,
                           submissions=submissions, first_topper=first_topper, second_topper=second_topper,
                           third_topper=third_topper, exam_avg_pct=exam_avg_pct, tier_counts=tier_counts,
                           tier_pcts=tier_pcts, total_students=total_students, total_attempts=total_attempts,
                           avg_score=round(overall_avg, 1))


@app.post("/teacher/exams/new")
@teacher_required
def create_exam():
    if not check_csrf(): abort(400, "Invalid form token")
    title = request.form.get("title", "").strip(); desc = request.form.get("description", "").strip()
    duration = request.form.get("duration_minutes", type=int) or 45
    if not title or len(title) > 160 or not (1 <= duration <= 240):
        flash("Enter a valid title and duration (1–240 minutes).", "error"); return redirect(url_for("teacher_dashboard"))
    conn = db_conn()
    try:
        conn.execute("INSERT INTO exams(title,description,duration_minutes,active,created_at) VALUES(?,?,?,?,?)", (title, desc, duration, 1, now_iso()))
        conn.commit(); flash("Exam created successfully.", "success")
    except sqlite3.IntegrityError:
        flash("An exam with that title already exists.", "error")
    finally: conn.close()
    return redirect(url_for("teacher_dashboard"))


@app.post("/teacher/exams/<int:exam_id>/toggle")
@teacher_required
def toggle_exam(exam_id):
    if not check_csrf(): abort(400, "Invalid form token")
    conn = db_conn(); exam = conn.execute("SELECT active FROM exams WHERE id=?", (exam_id,)).fetchone()
    if not exam: conn.close(); abort(404)
    new_value = 0 if exam[0] else 1
    conn.execute("UPDATE exams SET active=? WHERE id=?", (new_value, exam_id)); conn.commit(); conn.close()
    flash("Exam published." if new_value else "Exam unpublished.", "success")
    return redirect(url_for("teacher_dashboard", exam_id=exam_id))


@app.post("/teacher/exams/<int:exam_id>/delete")
@teacher_required
def delete_exam(exam_id):
    if not check_csrf(): abort(400, "Invalid form token")
    conn = db_conn()
    exam = conn.execute("SELECT title FROM exams WHERE id=?", (exam_id,)).fetchone()
    if not exam:
        conn.close()
        abort(404)
    conn.execute("DELETE FROM exams WHERE id=?", (exam_id,))
    conn.commit()
    conn.close()
    flash(f"🗑️ Assessment '{exam['title']}' permanently deleted.", "success")
    return redirect(url_for("teacher_dashboard"))


@app.post("/teacher/exams/<int:exam_id>/update_timer")
@teacher_required
def update_exam_timer(exam_id):
    if not check_csrf(): abort(400, "Invalid form token")
    duration = request.form.get("duration_minutes", type=int)
    if not duration or not (1 <= duration <= 300):
        flash("Enter a valid duration between 1 and 300 minutes.", "error")
        return redirect(url_for("teacher_dashboard", exam_id=exam_id))
    conn = db_conn()
    exam = conn.execute("SELECT id, title FROM exams WHERE id=?", (exam_id,)).fetchone()
    if not exam:
        conn.close()
        abort(404)
    conn.execute("UPDATE exams SET duration_minutes=? WHERE id=?", (duration, exam_id))
    conn.commit()
    conn.close()
    flash(f"⏱️ Timer for '{exam['title']}' updated to {duration} minutes!", "success")
    return redirect(url_for("teacher_dashboard", exam_id=exam_id))



@app.post("/teacher/generate_from_pdf")
@teacher_required
def generate_from_pdf():
    """Import existing MCQs or generate source-grounded MCQs completely offline.

    The parser first detects an existing MCQ structure. If none is found, it uses
    conservative definition/fact extraction. It never claims to be an LLM and
    does not send document contents to the internet.
    """
    if not check_csrf(): abort(400, "Invalid form token")
    exam_id = request.form.get("exam_id", type=int)
    unit = request.form.get("unit", "General").strip() or "General"
    count = request.form.get("count", type=int) or 10
    mode = request.form.get("mode", "auto")
    uploaded = request.files.get("pdf")
    if not exam_id or not uploaded:
        flash("Choose a document and an exam first.", "error")
        return redirect(url_for("teacher_dashboard", exam_id=exam_id))
    if count < 1 or count > 50:
        flash("Choose between 1 and 50 questions.", "error")
        return redirect(url_for("teacher_dashboard", exam_id=exam_id))

    filename = (uploaded.filename or "").lower()
    try:
        if filename.endswith(".pdf"):
            if PdfReader is None:
                flash("PDF support is not installed. Run: pip install -r requirements.txt", "error")
                return redirect(url_for("teacher_dashboard", exam_id=exam_id))
            reader = PdfReader(uploaded.stream)
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
        elif filename.endswith(".docx"):
            if Document is None:
                flash("DOCX support is not installed. Run: pip install -r requirements.txt", "error")
                return redirect(url_for("teacher_dashboard", exam_id=exam_id))
            doc = Document(uploaded.stream)
            text = "\n".join(p.text for p in doc.paragraphs)
            for table in doc.tables:
                for row in table.rows:
                    text += "\n" + " | ".join(cell.text for cell in row.cells)
        elif filename.endswith(".txt"):
            text = uploaded.read().decode("utf-8", errors="ignore")
        else:
            flash("Use a PDF, DOCX, or TXT document.", "error")
            return redirect(url_for("teacher_dashboard", exam_id=exam_id))
    except Exception as exc:
        app.logger.exception("Document extraction failed: %s", exc)
        flash("Could not read that document. If it is scanned, OCR is required.", "error")
        return redirect(url_for("teacher_dashboard", exam_id=exam_id))

    imported = parse_existing_mcqs(text, count)
    answer_key = parse_answer_key(text)
    if answer_key and imported:
        for idx, q in enumerate(imported, 1):
            if idx in answer_key:
                q["correct"] = answer_key[idx]
    if mode == "import" or (mode == "auto" and imported):
        questions = imported
        if not questions:
            flash("No complete A-D MCQ pattern was detected in this document.", "error")
            return redirect(url_for("teacher_dashboard", exam_id=exam_id))
        message = f"Imported {len(questions)} existing MCQs from {uploaded.filename}."
    else:
        questions = generate_offline_questions(text, unit, count)
        if not questions:
            flash("No reliable definition/fact material was found. Use a selectable-text document or import an existing MCQ file.", "error")
            return redirect(url_for("teacher_dashboard", exam_id=exam_id))
        message = f"Generated {len(questions)} quality-checked offline MCQs from {uploaded.filename}. Questions are only created when the source contains enough compatible facts."

    conn = db_conn()
    exam = conn.execute("SELECT id FROM exams WHERE id=?", (exam_id,)).fetchone()
    if not exam:
        conn.close(); abort(404)
    for q in questions:
        conn.execute("""INSERT INTO questions(exam_id,subject,question_text,option_a,option_b,option_c,option_d,correct_option,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                     (exam_id, unit, q["question"], q["A"], q["B"], q["C"], q["D"], q["correct"], now_iso()))
    conn.commit(); conn.close()
    flash(message, "success")
    return redirect(url_for("teacher_dashboard", exam_id=exam_id))


def _clean_pdf_text(text):
    if not text:
        return ""
    text = text.replace("\u00a0", " ").replace("\r", "\n")
    # Repair hyphenated word breaks at end of PDF lines (e.g. "comput-\ner" -> "computer")
    text = re.sub(r"([a-zA-Z]{2,})\s*-\s*\n\s*([a-zA-Z]{2,})", r"\1\2", text)
    # Replace non-standard bullets
    text = re.sub(r"[•▪‣⁃❖➢]", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def infer_correct_option(question, opts):
    """Best-effort offline answer inference for common diploma facts."""
    q = question.lower()
    joined = {k: v.lower() for k, v in opts.items()}
    rules = [
        (r"data link layer.*purpose", ["frame - to - frame communication", "frame-to-frame communication"]),
        (r"part of a frame.*actual information", ["data/payload"]),
        (r"stop.*wait.*sender waits", ["ack"]),
        (r"ieee standard.*ethernet", ["802.3"]),
        (r"bluetooth network.*one master.*active slaves", ["piconet"]),
        (r"bluetooth protocol.*discover.*services", ["sdp"]),
        (r"address.*network interface.*data link", ["mac address"]),
        (r"address.*network layer", ["ip address"]),
        (r"protocol.*(?:mac address.*ip address|mac address.*from an ip address|finds the mac address)", ["arp"]),
        (r"routing method.*all possible paths", ["flooding"]),
        (r"algorithm.*shortest path", ["dijkstra"]),
        (r"size.*ipv4", ["32 bits"]),
        (r"size.*ipv6", ["128 bits"]),
        (r"purpose.*subnetting", ["divide a large network into smaller networks"]),
        (r"ipv6.*ipv4.*tunnelling", ["ipv6 packet is encapsulated inside an ipv4 packet"]),
    ]
    for pattern, answers in rules:
        if re.search(pattern, q):
            for k, v in joined.items():
                if any(a in v for a in answers):
                    return k
    return "A"


def parse_answer_key(text):
    """Read common answer-key forms such as 1-B, 2: B, 3)C, 1.(A), 2.(C), Ans: 1-A."""
    result = {}
    for m in re.finditer(r"(?:Q(?:uestion)?\s*)?(\d{1,3})\s*[-:.)]\s*\(?\s*([ABCDa-d])\s*\)?\b", text or "", re.I):
        result[int(m.group(1))] = m.group(2).upper()
    return result


def parse_existing_mcqs(text, count=50):
    """Parse numbered & formatted MCQs from PDF, DOCX, or TXT documents."""
    text = _clean_pdf_text(text)
    lines = [re.sub(r"\s+", " ", x).strip() for x in text.splitlines()]
    lines = [x for x in lines if x]
    
    blocks = []
    current = []
    # Match numbered questions "1.", "1)", "[1]", "Q1.", "Q.1:", or lines ending in "?"
    qstart = re.compile(
        r"^(?:(?:Q(?:uestion)?\s*[-:.]?\s*)?\[?\d{1,3}\]?\s*[-:.)]?\s+|"
        r"(?:What|Which|Define|State|Explain|Calculate|How|Why|In|The|A|An)\b.*[\?:.]?$)",
        re.I
    )

    for line in lines:
        if qstart.match(line) and not re.match(r"^(?:Option|Ans|Answer|Correct|Key)\b|^(?:Option\s*)?[A-Da-d]\s*[).:\-]", line, re.I):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(current)

    out = []
    # Match options A-D, a-d, 1-4 with A., A), (A), [A], Option A:
    opt_re = re.compile(r"^(?:Option\s*)?\(?\s*([A-Da-d1-4])\s*[\).:\-]\s*(.+)$", re.I)
    opt_map = {"1": "A", "2": "B", "3": "C", "4": "D", "a": "A", "b": "B", "c": "C", "d": "D", "A": "A", "B": "B", "C": "C", "D": "D"}
    ans_line_re = re.compile(r"^(?:Ans(?:wer)?|Correct(?:\s*Option|\s*Answer)?|Key)\s*[-:.)]?\s*\(?\s*([ABCDa-d1-4])\s*\)?$", re.I)

    # Check for standalone Answer Key block at top/bottom of text
    global_answer_key = parse_answer_key(text)

    for q_idx, block in enumerate(blocks, 1):
        qtext = re.sub(r"^(?:Q(?:uestion)?\s*[-:.]?\s*)?\[?\d{1,3}\]?\s*[-:.)]?\s*", "", block[0], flags=re.I).strip()
        opts = {}
        active = None
        question_parts = [qtext]
        explicit_correct = None

        for line in block[1:]:
            ans_match = ans_line_re.match(line.strip())
            if ans_match:
                raw_ans = ans_match.group(1)
                explicit_correct = opt_map.get(raw_ans, raw_ans.upper())
                continue

            om = opt_re.match(line)
            if om:
                raw_key = om.group(1).lower() if om.group(1) in "abcd1234" else om.group(1).upper()
                mapped_key = opt_map.get(raw_key, om.group(1).upper())
                active = mapped_key
                opts[active] = om.group(2).strip()
            elif active:
                opts[active] += " " + line.strip()
            else:
                question_parts.append(line)

        qtext = " ".join(question_parts)
        qtext = re.sub(r"\s*\[\s*\]\s*", " ", qtext)
        qtext = re.sub(r"\s+", " ", qtext).strip(" -")

        if set(opts) >= {"A", "B", "C", "D"} and qtext:
            vals = {k: re.sub(r"\s+", " ", opts[k]).strip(" .") for k in "ABCD"}
            if all(vals.values()) and len(set(v.lower() for v in vals.values())) == 4:
                # Determine correct answer: 1) explicit line, 2) answer key map, 3) inference fallback
                final_correct = explicit_correct or global_answer_key.get(q_idx) or infer_correct_option(qtext, vals)
                if final_correct not in ("A", "B", "C", "D"):
                    final_correct = "A"
                out.append({"question": qtext, **vals, "correct": final_correct})
                if len(out) >= count:
                    break

    # Inline pattern fallback for single-line MCQ layouts
    if not out:
        flat = " ".join(lines)
        pattern = re.compile(
            r"(?:Q(?:uestion)?\s*[-:.]?\s*)?(\d{1,3})[.)]\s*(.*?)\s+"
            r"\(?[A]\)?\s*[).:]\s*(.*?)\s+"
            r"\(?[B]\)?\s*[).:]\s*(.*?)\s+"
            r"\(?[C]\)?\s*[).:]\s*(.*?)\s+"
            r"\(?[D]\)?\s*[).:]\s*(.*?)"
            r"(?=(?:\s+(?:Q(?:uestion)?\s*[-:.]?\s*)?\d{1,3}[.)]\s)|$)",
            re.I
        )
        for m in pattern.finditer(flat):
            q, a, b, c, d = m.group(2).strip(), m.group(3).strip(), m.group(4).strip(), m.group(5).strip(), m.group(6).strip()
            if all([q, a, b, c, d]):
                out.append({"question": q, "A": a, "B": b, "C": c, "D": d, "correct": "A"})
                if len(out) >= count:
                    break
    return out


def _sentences(text):
    """Split source text into usable sentences while preserving short note lines."""
    text = _clean_pdf_text(text)
    text = re.sub(r"[ \t]+", " ", text or "")
    return [s.strip(" -•\t") for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def _clean_fragment(value):
    value = re.sub(r"\s+", " ", value or "").strip()
    value = re.sub(r"^[\s\-–—:;,.]+|[\s\-–—:;,.]+$", "", value)
    value = re.sub(r"\(\s*([^)]+?)\s*\?", r"(\1)", value)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = re.sub(r"([(\[])\s+", r"\1", value)
    value = re.sub(r"\s+([)\]])", r"\1", value)
    return value.strip()


def _candidate_ok(subject, answer):
    subject = _clean_fragment(subject)
    answer = _clean_fragment(answer)
    if not (1 <= len(subject.split()) <= 15): return False
    if not (1 <= len(answer.split()) <= 40): return False
    if len(subject) > 120 or len(answer) > 300: return False
    if re.search(r"^(?:what|which|when|where|why|how)\b", subject, re.I): return False
    if re.search(r"\b(?:student name|pin|section|college|approved by|affiliated to|page \d+)\b", subject, re.I): return False
    if re.search(r"^[A-D]\s*[).:]", answer, re.I): return False
    if answer.lower() == subject.lower(): return False
    return True


def _make_candidates(text):
    """Extract fact/definition pairs from notes."""
    raw_lines = [re.sub(r"\s+", " ", x).strip() for x in _clean_pdf_text(text).splitlines()]
    sources = [x for x in raw_lines if x]
    for sentence in _sentences(text):
        if sentence not in sources:
            sources.append(sentence)

    candidates, seen = [], set()

    def add(subject, answer, kind):
        subject, answer = _clean_fragment(subject), _clean_fragment(answer)
        if not _candidate_ok(subject, answer):
            return
        key = (subject.lower(), answer.lower())
        if key in seen:
            return
        seen.add(key)
        candidates.append({"subject": subject, "answer": answer, "kind": kind})

    for s in sources:
        if re.search(r"\b(?:student name|pin|section|college|approved by|affiliated to|page \d+)\b", s, re.I):
            continue

        m = re.match(r"^(?:\d{1,3}[.)]\s*)?(.{2,90}?)\s+is used (?:for|to)\s+(.{3,240})$", s, re.I)
        if m:
            add(m.group(1), m.group(2), "purpose")
            continue

        m = re.match(
            r"^(?:\d{1,3}[.)]\s*)?(.{2,100}?)\s+"
            r"(is|are|refers to|means|is defined as|are defined as|is called|are called)"
            r"\s+(.{3,260})$",
            s, re.I
        )
        if m:
            subject, answer = m.group(1), m.group(3)
            if ". " not in answer:
                add(subject, answer, "definition")
                continue

        m = re.match(r"^(?:\d{1,3}[.)]\s*)?([A-Za-z][A-Za-z0-9 ()/&+\-]{1,80})\s*[:–—]\s*(.{4,260})$", s)
        if m:
            subject, answer = m.group(1), m.group(2)
            if len(answer.split()) >= 1 and ". " not in answer:
                add(subject, answer, "definition")
                continue

    return candidates


def _generate_fallback_distractors(candidate, unit_name):
    """Generate realistic technical distractors when document has limited facts."""
    ans = candidate["answer"]
    kind = candidate["kind"]
    subject = candidate["subject"]

    if kind == "year":
        return ["1992", "2001", "1985"]
    
    # Generic plausible diploma distractors based on subject/unit
    if re.search(r"network|protocol|layer|ip|mac|ethernet|tcp", (unit_name + " " + subject).lower()):
        defaults = [
            "Encapsulation of network packets",
            "Error checking and frame synchronization",
            "Routing packets to destination host",
            "Session initialization and control",
            "Port address translation"
        ]
    elif re.search(r"electronic|circuit|gate|flip|multiprocess", (unit_name + " " + subject).lower()):
        defaults = [
            "Combinational logic output processing",
            "Sequential state transition and clocking",
            "High impedance bus switching",
            "Voltage level amplification",
            "Multiplexing input signals"
        ]
    elif re.search(r"structure|data|array|tree|stack|queue|sort", (unit_name + " " + subject).lower()):
        defaults = [
            "O(n log n) average time complexity",
            "Linear traversal and memory allocation",
            "First In First Out (FIFO) processing",
            "Pointer modification in heap space",
            "Binary tree height balancing"
        ]
    else:
        defaults = [
            "Primary operational function of the component",
            "Secondary control mechanism in system architecture",
            "Hardware protocol handling interface",
            "Software buffer management layer",
            "Execution pipeline optimization"
        ]

    filtered = [d for d in defaults if d.lower() != ans.lower()][:3]
    while len(filtered) < 3:
        filtered.append(f"Alternative state of {subject}")
    return filtered


def generate_offline_questions(text, unit, count):
    """Quality-first offline MCQ generation from unit notes/texts."""
    candidates = _make_candidates(text)

    unique = []
    seen_answers = set()
    for c in candidates:
        ak = re.sub(r"[^a-z0-9]+", " ", c["answer"].lower()).strip()
        if ak in seen_answers:
            continue
        seen_answers.add(ak)
        unique.append(c)
    candidates = unique

    out = []
    used_questions = set()
    for c in candidates:
        if len(out) >= count:
            break

        pool = [x for x in candidates if x is not c and x["answer"].lower() != c["answer"].lower()]
        if len(pool) >= 3:
            distractors = [x["answer"] for x in pool[:3]]
        else:
            distractors = _generate_fallback_distractors(c, unit)

        opts = [c["answer"]] + distractors[:3]
        if len({o.lower() for o in opts}) != 4:
            continue

        local = random.Random(1009 + sum(map(ord, c["subject"])))
        local.shuffle(opts)
        correct = "ABCD"[opts.index(c["answer"])]
        
        qtext = f"What is the main function of {c['subject']}?" if c["kind"] == "purpose" else f"What is {c['subject']}?"
        if qtext.lower() in used_questions:
            continue
        used_questions.add(qtext.lower())

        out.append({
            "question": qtext,
            "A": opts[0], "B": opts[1], "C": opts[2], "D": opts[3],
            "correct": correct,
        })
    return out

@app.post("/teacher/add_question")
@teacher_required
def add_question():
    if not check_csrf(): abort(400, "Invalid form token")
    exam_id = request.form.get("exam_id", type=int)
    fields = ["subject", "question_text", "option_a", "option_b", "option_c", "option_d", "correct_option"]
    values = [request.form.get(x, "").strip() for x in fields]
    if not exam_id or not all(values) or values[-1] not in "ABCD":
        flash("Fill every question field correctly.", "error"); return redirect(url_for("teacher_dashboard", exam_id=exam_id))
    conn = db_conn(); conn.execute("INSERT INTO questions(exam_id,subject,question_text,option_a,option_b,option_c,option_d,correct_option,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (exam_id,*values,now_iso())); conn.commit(); conn.close()
    flash("Question added successfully.", "success")
    return redirect(url_for("teacher_dashboard", exam_id=exam_id))


@app.post("/teacher/import_pasted_text")
@teacher_required
def import_pasted_text():
    if not check_csrf(): abort(400, "Invalid form token")
    exam_id = request.form.get("exam_id", type=int)
    subject_tag = request.form.get("subject", "").strip() or "General"
    raw_text = request.form.get("raw_text", "").strip()
    if not exam_id or not raw_text:
        flash("Please paste the question text.", "error")
        return redirect(url_for("teacher_dashboard", exam_id=exam_id))

    parsed = parse_existing_mcqs(raw_text, count=100)
    if not parsed:
        flash("Could not detect valid MCQs in the pasted text. Ensure questions have options A-D.", "error")
        return redirect(url_for("teacher_dashboard", exam_id=exam_id))

    conn = db_conn()
    added_count = 0
    for q in parsed:
        conn.execute(
            "INSERT INTO questions(exam_id,subject,question_text,option_a,option_b,option_c,option_d,correct_option,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (exam_id, subject_tag, q["question"], q["A"], q["B"], q["C"], q["D"], q["correct"], now_iso())
        )
        added_count += 1
    conn.commit()
    conn.close()

    flash(f"⚡ Successfully parsed and added {added_count} MCQs directly to the question bank!", "success")
    return redirect(url_for("teacher_dashboard", exam_id=exam_id))


def parse_mcq_text_advanced(text):
    text = _clean_pdf_text(text)
    if not text:
        return []

    lines = [re.sub(r"\s+", " ", x).strip() for x in text.splitlines()]
    lines = [x for x in lines if x]

    global_answers = parse_answer_key(text)

    blocks = []
    current = []
    qstart = re.compile(
        r"^(?:(?:Q(?:uestion)?\s*[-:.]?\s*)?\[?\d{1,3}\]?\s*[-:.)]?\s+|"
        r"(?:What|Which|Define|State|Explain|Calculate|How|Why|In|The|A|An|Consider)\b.*[\?:.]?$)",
        re.I
    )

    for line in lines:
        if qstart.match(line) and not re.match(r"^(?:Option|Ans|Answer|Correct|Key)\b|^(?:Option\s*)?[A-Da-d]\s*[).:\-]", line, re.I):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(current)

    out = []
    opt_re = re.compile(r"^(?:Option\s*)?\(?\s*([A-Da-d1-4])\s*[\).:\-]\s*(.+)$", re.I)
    opt_map = {"1": "A", "2": "B", "3": "C", "4": "D", "a": "A", "b": "B", "c": "C", "d": "D", "A": "A", "B": "B", "C": "C", "D": "D"}
    ans_line_re = re.compile(r"^(?:Ans(?:wer)?|Correct(?:\s*Option|\s*Answer)?|Key)\s*[-:.)]?\s*\(?\s*([ABCDa-d1-4])\s*\)?$", re.I)

    for q_idx, block in enumerate(blocks, 1):
        qtext = re.sub(r"^(?:Q(?:uestion)?\s*[-:.]?\s*)?\[?\d{1,3}\]?\s*[-:.)]?\s*", "", block[0], flags=re.I).strip()
        opts = {}
        active = None
        question_parts = [qtext]
        explicit_correct = None
        warnings = []

        for line in block[1:]:
            ans_match = ans_line_re.match(line.strip())
            if ans_match:
                raw_ans = ans_match.group(1)
                explicit_correct = opt_map.get(raw_ans, raw_ans.upper())
                continue

            om = opt_re.match(line)
            if om:
                raw_key = om.group(1).lower() if om.group(1) in "abcd1234" else om.group(1).upper()
                mapped_key = opt_map.get(raw_key, om.group(1).upper())
                active = mapped_key
                opt_val = om.group(2).strip()

                tail_ans = re.search(r"\s+(?:Ans(?:wer)?|Correct)\s*[:.-]?\s*([ABCDa-d])$", opt_val, re.I)
                if tail_ans:
                    explicit_correct = tail_ans.group(1).upper()
                    opt_val = opt_val[:tail_ans.start()].strip()

                opts[active] = opt_val
            elif active:
                opt_val = line.strip()
                tail_ans = re.search(r"\s+(?:Ans(?:wer)?|Correct)\s*[:.-]?\s*([ABCDa-d])$", opt_val, re.I)
                if tail_ans:
                    explicit_correct = tail_ans.group(1).upper()
                    opt_val = opt_val[:tail_ans.start()].strip()
                opts[active] += " " + opt_val
            else:
                tail_ans = re.search(r"(?:Ans(?:wer)?|Correct)\s*[:.-]?\s*([ABCDa-d])", line, re.I)
                if tail_ans:
                    explicit_correct = tail_ans.group(1).upper()
                else:
                    question_parts.append(line)

        qtext = " ".join(question_parts)
        qtext = re.sub(r"\s+", " ", qtext).strip(" -")

        for key in ["A", "B", "C", "D"]:
            if key not in opts or not opts[key]:
                opts[key] = f"Option {key}"
                warnings.append(f"Option {key} was missing and auto-filled.")

        vals = [opts[k].lower().strip() for k in "ABCD"]
        if len(set(vals)) < 4:
            warnings.append("Duplicate option values detected.")

        final_correct = explicit_correct or global_answers.get(q_idx) or infer_correct_option(qtext, opts)
        if final_correct not in ("A", "B", "C", "D"):
            final_correct = "A"
            warnings.append("Could not confidently identify correct answer; defaulted to Option A.")

        low_q = qtext.lower()
        if any(w in low_q for w in ["calculate", "explain in detail", "derive", "architecture", "algorithm", "complexity", "worst case"]):
            difficulty = "Hard"
        elif any(w in low_q for w in ["what is", "which language", "define", "stand for", "full form"]):
            difficulty = "Easy"
        else:
            difficulty = "Medium"

        out.append({
            "id": q_idx,
            "question": qtext,
            "A": opts["A"],
            "B": opts["B"],
            "C": opts["C"],
            "D": opts["D"],
            "correct": final_correct,
            "difficulty": difficulty,
            "warnings": warnings
        })

    return out


@app.get("/mcq_converter")
@teacher_required
def mcq_converter_page():
    conn = db_conn()
    exams = conn.execute("SELECT id, title FROM exams WHERE active=1 ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("mcq_converter.html", exams=exams)


@app.post("/api/parse_mcq_text")
@teacher_required
def api_parse_mcq_text():
    data = request.get_json(silent=True) or {}
    raw_text = data.get("raw_text") or request.form.get("raw_text") or ""
    if not raw_text.strip():
        return jsonify({"status": "error", "message": "No text provided"}), 400

    parsed = parse_mcq_text_advanced(raw_text)
    return jsonify({"status": "success", "count": len(parsed), "questions": parsed})


@app.post("/api/export_mcq_docx")
@teacher_required
def api_export_mcq_docx():
    if Document is None:
        return jsonify({"status": "error", "message": "python-docx library not installed"}), 500
    data = request.get_json(silent=True) or {}
    questions = data.get("questions", [])
    title = data.get("title", "MCQ Assessment Document").strip() or "MCQ Assessment Document"

    doc = Document()
    doc.add_heading(title, level=0)
    p_meta = doc.add_paragraph(f"Generated via Diploma Quiz Portal — Text-to-MCQ Studio\nTotal Questions: {len(questions)}")
    if p_meta.runs:
        p_meta.runs[0].font.italic = True

    for idx, q in enumerate(questions, 1):
        doc.add_heading(f"Q{idx}. {q.get('question', '')}", level=2)
        p_info = doc.add_paragraph(f"Difficulty: {q.get('difficulty', 'Medium')} | Correct Option: {q.get('correct', 'A')}")

        for key in ["A", "B", "C", "D"]:
            opt_val = q.get(key, "")
            is_cor = (q.get("correct") == key)
            mark = " ✓ (Correct Answer)" if is_cor else ""
            doc.add_paragraph(f"   [{key}] {opt_val}{mark}")

    doc.add_heading("ANSWER KEY SUMMARY", level=1)
    key_items = [f"Q{i+1}: {q.get('correct', 'A')}" for i, q in enumerate(questions)]
    doc.add_paragraph("  |  ".join(key_items))

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)

    clean_filename = re.sub(r"[^a-zA-Z0-9_-]", "_", title).lower()
    return Response(
        bio.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{clean_filename}.docx"'}
    )


@app.post("/api/import_converted_mcqs")
@teacher_required
def api_import_converted_mcqs():
    data = request.get_json(silent=True) or {}
    exam_id = data.get("exam_id")
    subject = data.get("subject", "General").strip() or "General"
    questions = data.get("questions", [])

    if not exam_id or not questions:
        return jsonify({"status": "error", "message": "Missing exam_id or questions payload"}), 400

    conn = db_conn()
    exam = conn.execute("SELECT id, title FROM exams WHERE id=?", (exam_id,)).fetchone()
    if not exam:
        conn.close()
        return jsonify({"status": "error", "message": "Target exam not found"}), 404

    added_count = 0
    for q in questions:
        qtext = q.get("question", "").strip()
        a = q.get("A", "").strip()
        b = q.get("B", "").strip()
        c = q.get("C", "").strip()
        d = q.get("D", "").strip()
        cor = q.get("correct", "A").upper()
        if cor not in "ABCD":
            cor = "A"

        if qtext and a and b and c and d:
            conn.execute(
                "INSERT INTO questions(exam_id,subject,question_text,option_a,option_b,option_c,option_d,correct_option,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (exam_id, subject, qtext, a, b, c, d, cor, now_iso())
            )
            added_count += 1

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "added": added_count,
        "message": f"Successfully imported {added_count} questions into '{exam['title']}'!"
    })



@app.post("/teacher/questions/<int:question_id>/delete")
@teacher_required
def delete_question(question_id):
    if not check_csrf(): abort(400, "Invalid form token")
    conn = db_conn(); q = conn.execute("SELECT exam_id FROM questions WHERE id=?", (question_id,)).fetchone()
    if not q: conn.close(); abort(404)
    conn.execute("DELETE FROM questions WHERE id=?", (question_id,)); conn.commit(); conn.close()
    flash("Question deleted.", "success")
    return redirect(url_for("teacher_dashboard", exam_id=q[0]))


@app.get("/teacher/results.csv")
@teacher_required
def export_results():
    exam_id = request.args.get("exam_id", type=int)
    conn = db_conn()
    if exam_id:
        exams = conn.execute("SELECT id, title FROM exams WHERE id=?", (exam_id,)).fetchall()
    else:
        exams = conn.execute("SELECT id, title FROM exams ORDER BY id DESC").fetchall()

    out = io.StringIO()
    out.write("\ufeff")
    writer = csv.writer(out)
    writer.writerow(["Rank", "Performance Tier", "Exam Title", "Student PIN", "Student Name", "Score", "Total Questions", "Percentage (%)", "Time Taken", "Submitted At"])

    for e in exams:
        raw_subs = conn.execute("SELECT * FROM submissions WHERE exam_id=? ORDER BY id DESC", (e["id"],)).fetchall()
        subs, *rest = process_submissions_analytics(raw_subs)
        for s in subs:
            mins = s["time_taken_seconds"] // 60
            secs = s["time_taken_seconds"] % 60
            time_str = f"{mins}m {secs}s"
            sub_time = (s["submitted_at"] or "").replace("T", " ")[:19]
            writer.writerow([s["rank"], s["tier"], e["title"], s["student_pin"], s["student_name"], s["score"], s["total_questions"], f"{s['pct']}%", time_str, sub_time])

    conn.close()
    csv_data = out.getvalue().encode("utf-8-sig")
    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f'attachment; filename="quiz-results-{exam_id or "all"}.csv"',
            "Content-Type": "text/csv; charset=utf-8-sig"
        }
    )



@app.get("/quiz")
@student_required
def student_quiz():
    conn = db_conn()
    exam_id = session.get("exam_id")
    if not exam_id:
        conn.close()
        session.clear()
        flash("Session expired. Please select your exam and PIN to start.", "error")
        return redirect(url_for("home"))

    exam = conn.execute("SELECT * FROM exams WHERE id=?", (exam_id,)).fetchone()
    if not exam:
        conn.close()
        session.clear()
        flash("Exam not found or inactive.", "error")
        return redirect(url_for("home"))

    ids = session.get("question_ids", [])
    if not ids:
        conn.close()
        session.clear()
        flash("No questions found for this exam session.", "error")
        return redirect(url_for("home"))

    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(f"SELECT * FROM questions WHERE id IN ({placeholders})", ids).fetchall()
    conn.close()

    by_id = {r["id"]: r for r in rows}
    questions = [by_id[i] for i in ids if i in by_id and by_id[i]["exam_id"] == exam["id"]]

    started = datetime.fromisoformat(session["exam_started_at"])
    deadline = started + timedelta(minutes=exam["duration_minutes"])
    remaining = max(0, int((deadline - datetime.now(timezone.utc)).total_seconds()))

    return render_template("student_quiz.html", exam=exam, questions=questions, remaining=remaining,
                           student_pin=session["student_pin"], student_name=session["student_name"])


@app.route("/submit_quiz", methods=["POST", "GET"])
@student_required
def submit_quiz():
    if request.method == "POST" and not check_csrf():
        abort(400, "Invalid form token")
    
    exam_id = session.get("exam_id")
    pin = session.get("student_pin")
    name = session.get("student_name")

    if not exam_id or not pin:
        session.clear()
        flash("Session expired before submission. Please log in with your PIN again.", "error")
        return redirect(url_for("home"))

    conn = db_conn()
    exam = conn.execute("SELECT * FROM exams WHERE id=?", (exam_id,)).fetchone()
    if not exam:
        conn.close()
        session.clear()
        flash("Exam not found.", "error")
        return redirect(url_for("home"))

    existing = conn.execute("SELECT id FROM submissions WHERE exam_id=? AND student_pin=?", (exam_id, pin)).fetchone()
    if existing:
        conn.close()
        session.clear()
        flash("This exam has already been submitted. Only one attempt is allowed per PIN.", "error")
        return redirect(url_for("home"))

    ids = session.get("question_ids", [])
    questions = []
    if ids:
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(f"SELECT * FROM questions WHERE id IN ({placeholders})", ids).fetchall()
        by_id = {r["id"]: r for r in rows}
        questions = [by_id[i] for i in ids if i in by_id]

    user_answers = {}
    review_data = []
    for q in questions:
        ans = request.form.get(f"question_{q['id']}")
        if ans: user_answers[str(q["id"])] = ans
        is_cor = (ans == q["correct_option"])
        review_data.append({
            "id": q["id"],
            "question": q["question_text"],
            "subject": q["subject"],
            "A": q["option_a"],
            "B": q["option_b"],
            "C": q["option_c"],
            "D": q["option_d"],
            "selected": ans,
            "correct": q["correct_option"],
            "is_correct": is_cor
        })

    score = sum(1 for item in review_data if item["is_correct"])
    started_raw = session.get("exam_started_at")
    if started_raw:
        try:
            started = datetime.fromisoformat(started_raw)
        except Exception:
            started = datetime.now(timezone.utc)
    else:
        started = datetime.now(timezone.utc)
    elapsed = max(0, int((datetime.now(timezone.utc) - started).total_seconds()))
    elapsed = min(elapsed, exam["duration_minutes"] * 60)

    try:
        conn.execute(
            "INSERT INTO submissions(exam_id,student_pin,student_name,score,total_questions,time_taken_seconds,submitted_at,answers_json) VALUES(?,?,?,?,?,?,?,?)",
            (exam_id, pin, name, score, len(questions), elapsed, now_iso(), json.dumps(user_answers))
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        session.clear()
        flash("This exam has already been submitted.", "error")
        return redirect(url_for("home"))

    # Compute ranking & performance analytics for the student's result view
    raw_subs = conn.execute("SELECT * FROM submissions WHERE exam_id=?", (exam_id,)).fetchall()
    subs, first_topper, second_topper, third_topper, exam_avg_pct, tier_counts, tier_pcts = process_submissions_analytics(raw_subs)
    student_sub = next((s for s in subs if s["student_pin"] == pin), None)

    conn.close()
    session.clear()
    return render_template("result.html", score=score, total=len(questions), name=name, exam=exam, review_data=review_data,
                           student_sub=student_sub, first_topper=first_topper, second_topper=second_topper,
                           exam_avg_pct=exam_avg_pct, total_submissions=len(subs), allow_review=bool(exam["allow_review"]))


@app.get("/teacher/submissions/<int:sub_id>/review")
@teacher_required
def teacher_submission_review(sub_id):
    conn = db_conn()
    sub = conn.execute("SELECT s.*, e.title as exam_title FROM submissions s JOIN exams e ON e.id=s.exam_id WHERE s.id=?", (sub_id,)).fetchone()
    if not sub:
        conn.close()
        return jsonify({"status": "error", "message": "Submission not found"}), 404

    questions = conn.execute("SELECT * FROM questions WHERE exam_id=? ORDER BY id ASC", (sub["exam_id"],)).fetchall()
    conn.close()

    user_answers = {}
    if sub["answers_json"]:
        try: user_answers = json.loads(sub["answers_json"])
        except Exception: pass

    review_data = []
    for q in questions:
        ans = user_answers.get(str(q["id"]))
        is_cor = (ans == q["correct_option"])
        review_data.append({
            "id": q["id"],
            "question": q["question_text"],
            "subject": q["subject"],
            "A": q["option_a"],
            "B": q["option_b"],
            "C": q["option_c"],
            "D": q["option_d"],
            "selected": ans,
            "correct": q["correct_option"],
            "is_correct": is_cor
        })

    return jsonify({
        "status": "success",
        "student_name": sub["student_name"],
        "student_pin": sub["student_pin"],
        "exam_title": sub["exam_title"],
        "score": sub["score"],
        "total_questions": sub["total_questions"],
        "time_taken_seconds": sub["time_taken_seconds"],
        "submitted_at": sub["submitted_at"],
        "review_data": review_data
    })


@app.post("/teacher/exams/<int:exam_id>/clear_questions")
@teacher_required
def clear_exam_questions(exam_id):
    if not check_csrf(): abort(400, "Invalid form token")
    conn = db_conn()
    exam = conn.execute("SELECT title FROM exams WHERE id=?", (exam_id,)).fetchone()
    if exam:
        conn.execute("DELETE FROM questions WHERE exam_id=?", (exam_id,))
        conn.commit()
        flash(f"All questions have been cleared from '{exam['title']}'.", "success")
    conn.close()
    return redirect(url_for("teacher_dashboard", exam_id=exam_id))


@app.post("/teacher/exams/<int:exam_id>/clear_submissions")
@teacher_required
def clear_exam_submissions(exam_id):
    if not check_csrf(): abort(400, "Invalid form token")
    conn = db_conn()
    exam = conn.execute("SELECT title FROM exams WHERE id=?", (exam_id,)).fetchone()
    if exam:
        conn.execute("DELETE FROM submissions WHERE exam_id=?", (exam_id,))
        conn.commit()
        flash(f"All student submissions have been cleared for '{exam['title']}'.", "success")
    conn.close()
    return redirect(url_for("teacher_dashboard", exam_id=exam_id))


@app.get("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))


@app.get("/health")
def health():
    try:
        conn=db_conn(); conn.execute("SELECT 1"); conn.close(); return {"status":"ok"},200
    except Exception:
        return {"status":"error"},500


init_db()

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "5000")), debug=False)
