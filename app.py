# app.py  — ISEMini (complete, matches your templates)
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, abort
import os, time, json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "isehub_secret_key_v3"

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
UPLOAD_DIR = os.path.join(BASE, "uploads")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "admin_assignments"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "notes"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "student_submissions"), exist_ok=True)

ALLOWED = {"pdf","docx","pptx","ppt","png","jpg","jpeg"}
ADMIN_PASSWORD = "123"

FILES = {
    "assignments": os.path.join(DATA_DIR, "assignments.json"),
    "notes": os.path.join(DATA_DIR, "notes.json"),
    "notifications": os.path.join(DATA_DIR, "notifications.json"),
    "students_A": os.path.join(DATA_DIR, "students_A.json"),
    "students_B": os.path.join(DATA_DIR, "students_B.json"),
    "students_C": os.path.join(DATA_DIR, "students_C.json"),
    "faculty":os.path.join(DATA_DIR,"faculty.json")
}

# Ensure JSON files exist (empty list default)
for p in FILES.values():
    if not os.path.exists(p):
        with open(p, "w") as f:
            json.dump([], f)

# ------------------ helpers ------------------

def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED

def normalize(s):
    return "" if not s else s.strip().lower()

def load_students(section):
    key = f"students_{section}"
    path = FILES.get(key)
    return load_json(path) if path else []

def save_students(section, arr):
    path = FILES.get(f"students_{section}")
    if path:
        save_json(path, arr)

def find_student(identifier):
    """
    find by usn or email (case-insensitive).
    returns (student_dict, section) or (None,None)
    """
    if not identifier:
        return None, None
    idn = normalize(identifier)
    for sec in ("A","B","C"):
        students = load_students(sec)
        for s in students:
            if normalize(s.get("usn")) == idn or normalize(s.get("email")) == idn:
                return s, sec
    return None, None

# ---------- faculty helpers ----------
def load_faculty():
    return load_json(FILES.get("faculty"))

def find_faculty(username):
    if not username:
        return None
    username = username.strip().lower()
    for f in load_faculty():
        if f.get("username","").strip().lower() == username:
            return f
    return None

def faculty_can_edit(faculty_obj, subject, section):
    if not faculty_obj:
        return False
    subs = faculty_obj.get("subjects", [])
    secs = faculty_obj.get("sections", [])
    return (subject in subs) and (section in secs)

# Subject metadata (used in student pages)
subject_data = {
    "sepm": {"title":"Software Engineering & Project Management"},
    "cn": {"title":"Computer Networks"},
    "toc": {"title":"Theory of Computation"},
    "rmipr": {"title":"Research Methodology & IPR"},
    "ai": {"title":"Artificial Intelligence"},
    "evs": {"title":"Environmental Studies & E-Waste"}
}

# ------------------ AUTH / HOME ------------------


# ------------------ LOGIN (ADMIN + STUDENT + FACULTY) ------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # ADMIN LOGIN
        if username.lower() == "admin" and password == ADMIN_PASSWORD:
            session.clear()
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))

        # STUDENT LOGIN
        stu, sec = find_student(username)
        if stu and stu.get("password") == password:
            session.clear()
            session["student_usn"] = stu.get("usn")
            session["student_section"] = sec
            return redirect(url_for("student_dashboard"))

        # FACULTY LOGIN
        fac = find_faculty(username)
        if fac and fac.get("password") == password:
            session.clear()
            session["faculty_user"] = username
            return redirect(url_for("faculty_dashboard"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


# ------------------ FACULTY LOGIN PAGE ------------------
@app.route("/faculty/login", methods=["GET", "POST"])
def faculty_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()

        fac = find_faculty(username)
        if fac and fac.get("password") == password:
            session.clear()
            session["faculty_user"] = username
            flash("Login successful", "success")
            return redirect(url_for("faculty_dashboard"))
        else:
            flash("Invalid faculty credentials", "danger")

    return render_template("faculty_login.html")

    
    # ---------- FACULTY DASHBOARD ----------
@app.route("/faculty/dashboard")
def faculty_dashboard():
    if not session.get("faculty_user"):
        return redirect(url_for("faculty_login"))
    f = find_faculty(session["faculty_user"])
    # gather subjects & sections
    subs = f.get("subjects", [])
    secs = f.get("sections", [])
    # show latest assignments and notes (faculty can view)
    assignments = load_json(FILES["assignments"])
    notes = load_json(FILES["notes"])
    return render_template("faculty_dashboard.html", faculty=f, assignments=assignments, notes=notes)

# View students assigned to this faculty (filter by sections)
@app.route("/faculty/students")
def faculty_students():
    if not session.get("faculty_user"):
        return redirect(url_for("faculty_login"))
    f = find_faculty(session["faculty_user"])
    # collect students across faculty sections
    students = []
    for sec in f.get("sections", []):
        students += load_students(sec)
    return render_template("faculty_students.html", faculty=f, students=students)

# ------------------ FACULTY: EDIT OVERALL ATTENDANCE ------------------
@app.route("/faculty/attendance/<usn>", methods=["GET", "POST"])
def faculty_attendance(usn):
    if not session.get("faculty_user"):
        return redirect(url_for("faculty_login"))

    faculty_obj = find_faculty(session["faculty_user"])
    student, section = find_student(usn)

    if not student:
        return "Student not found", 404

    # load section students
    students = load_students(section)

    # find student index
    idx = next((i for i, s in enumerate(students)
                if normalize(s.get("usn")) == normalize(usn)), None)

    if idx is None:
        return "Student not found in section file", 404

    # ensure attendance is integer
    if "attendance" not in students[idx] or not isinstance(students[idx]["attendance"], int):
        students[idx]["attendance"] = int(students[idx].get("attendance", 0))

    if request.method == "POST":
        val = request.form.get("attendance", "").strip()
        if val.isdigit():
            students[idx]["attendance"] = int(val)
            save_students(section, students)
            flash("Attendance updated successfully", "success")
            return redirect(url_for("faculty_students"))
        else:
            flash("Invalid attendance value", "danger")

    return render_template("faculty_attendance.html",
                           faculty=faculty_obj,
                           student=students[idx])

# Edit internal marks for a student (faculty permission checked per subject)
@app.route("/faculty/marks/<usn>/<subject>", methods=["GET","POST"])
def faculty_marks(usn, subject):
    if not session.get("faculty_user"):
        return redirect(url_for("faculty_login"))
    faculty_obj = find_faculty(session["faculty_user"])
    student, section = find_student(usn)
    if not student:
        return "Student not found", 404
    if not faculty_can_edit(faculty_obj, subject, section):
        flash("You are not authorized to edit this student's marks for that subject", "danger")
        return redirect(url_for("faculty_students"))
    students = load_students(section)
    idx = next((i for i,s in enumerate(students) if normalize(s.get("usn")) == normalize(usn)), None)
    students[idx].setdefault("internal_marks", {})
    if request.method == "POST":
        val = request.form.get("marks","").strip()
        try:
            v = int(val)
            students[idx]["internal_marks"][subject] = v
            save_students(section, students)
            flash("Marks updated", "success")
            return redirect(url_for("faculty_students"))
        except:
            flash("Invalid marks value", "danger")
    return render_template("faculty_marks.html", faculty=faculty_obj, student=students[idx], subject=subject)

# Upload study materials (faculty can upload, marked by uploader)
@app.route("/faculty/notes", methods=["GET","POST"])
def faculty_notes():
    if not session.get("faculty_user"):
        return redirect(url_for("faculty_login"))
    f = find_faculty(session["faculty_user"])
    notes = load_json(FILES["notes"])
    if request.method == "POST":
        title = request.form.get("title","").strip()
        subject = request.form.get("subject","").strip()
        file = request.files.get("file")
        if file and allowed_file(file.filename) and subject:
            fname = f"{int(time.time())}_{secure_filename(file.filename)}"
            file.save(os.path.join(UPLOAD_DIR, "notes", fname))
            notes.insert(0, {
                "id": str(int(time.time()*1000)),
                "title": title,
                "subject": subject,
                "file": fname,
                "uploader": f.get("username"),
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            save_json(FILES["notes"], notes)
            flash("Note uploaded", "success")
        else:
            flash("Invalid file/subject", "danger")
        return redirect(url_for("faculty_notes"))
    return render_template("faculty_notes.html", faculty=f, notes=notes, subjects=subject_data)
    
# ------------------ ADMIN DASHBOARD & STUDENTS ------------------

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html")

@app.route("/admin/students/<section>")
def admin_students(section):
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    sec = section.upper()
    if sec not in ("A","B","C"):
        abort(404)
    students = load_students(sec)
    return render_template("admin_students.html", section=sec, students=students)

# ------------------ ADMIN: ASSIGNMENTS ------------------

@app.route("/admin/assignments", methods=["GET","POST"])
def admin_assignments():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    assignments = load_json(FILES["assignments"])
    if request.method == "POST":
        title = request.form.get("title","").strip()
        desc = request.form.get("description","").strip()
        deadline = request.form.get("deadline","").strip()
        file = request.files.get("assignment_file")
        if file and allowed_file(file.filename):
            fname = f"{int(time.time())}_{secure_filename(file.filename)}"
            file.save(os.path.join(UPLOAD_DIR, "admin_assignments", fname))
            new = {
                "id": str(int(time.time()*1000)),
                "title": title,
                "description": desc,
                "deadline": deadline,
                "file": fname,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "submissions": []
            }
            assignments.insert(0, new)
            save_json(FILES["assignments"], assignments)
            flash("Assignment uploaded", "success")
        else:
            flash("Invalid file or missing fields", "danger")
        return redirect(url_for("admin_assignments"))
    return render_template("admin_assignments.html", assignments=assignments)

@app.route("/admin/assignments/<aid>/submissions")
def admin_view_submissions(aid):
    if not session.get("is_admin"):
        return redirect(url_for("login"))

    assignments = load_json(FILES["assignments"])

    # find correct assignment by id
    assignment = next((a for a in assignments if str(a.get("id")) == str(aid)), None)

    if not assignment:
        return "Assignment not found", 404

    # extract submissions list
    submissions = assignment.get("submissions", [])

    return render_template(
        "admin_view_submissions.html",
        assignment=assignment,
        submissions=submissions
    )

@app.route("/admin/assignments/<aid>/delete", methods=["POST"])
def admin_delete_assignment(aid):
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    assignments = load_json(FILES["assignments"])
    assignments = [a for a in assignments if str(a.get("id")) != str(aid)]
    save_json(FILES["assignments"], assignments)
    flash("Assignment deleted", "success")
    return redirect(url_for("admin_assignments"))

# ------------------ ADMIN: NOTES ------------------

@app.route("/admin/notes", methods=["GET","POST"])
def admin_notes():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    notes = load_json(FILES["notes"])
    if request.method == "POST":
        subject = request.form.get("subject","").strip()
        title = request.form.get("title","").strip()
        desc = request.form.get("description","").strip()
        file = request.files.get("note_file")
        if file and allowed_file(file.filename) and subject:
            fname = f"{int(time.time())}_{secure_filename(file.filename)}"
            file.save(os.path.join(UPLOAD_DIR, "notes", fname))
            notes.insert(0, {
                "id": str(int(time.time()*1000)),
                "subject": subject,
                "title": title,
                "description": desc,
                "filename": fname,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            save_json(FILES["notes"], notes)
            flash("Note uploaded", "success")
        else:
            flash("Invalid or missing file/subject", "danger")
        return redirect(url_for("admin_notes"))
    return render_template("admin_notes.html", notes=notes, subject_data=subject_data)

@app.route("/admin/notes/<nid>/delete", methods=["POST"])
def admin_delete_note(nid):
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    notes = load_json(FILES["notes"])
    notes = [n for n in notes if str(n.get("id")) != str(nid)]
    save_json(FILES["notes"], notes)
    flash("Note deleted", "success")
    return redirect(url_for("admin_notes"))

# ------------------ ADMIN: NOTIFICATIONS ------------------

@app.route("/admin/notifications", methods=["GET","POST"])
def admin_notifications():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    notifs = load_json(FILES["notifications"])
    if request.method == "POST":
        msg = request.form.get("message","").strip()
        if msg:
            notifs.insert(0, {"id": str(int(time.time()*1000)), "message": msg, "time": time.strftime("%d %b %Y")})
            save_json(FILES["notifications"], notifs)
            flash("Notification posted", "success")
        else:
            flash("Enter a message", "danger")
        return redirect(url_for("admin_notifications"))
    return render_template("admin_notifications.html", notifications=notifs)

@app.route("/admin/notifications/<nid>/delete", methods=["POST"])
def admin_delete_notification(nid):
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    notifs = load_json(FILES["notifications"])
    notifs = [n for n in notifs if str(n.get("id")) != str(nid)]
    save_json(FILES["notifications"], notifs)
    flash("Notification removed", "success")
    return redirect(url_for("admin_notifications"))

# ------------------ ADMIN: INTERNAL MARKS ------------------

@app.route("/admin/internal_marks/<usn>", methods=["GET", "POST"])
def admin_internal_marks(usn):
    if not session.get("is_admin"):
        return redirect(url_for("login"))

    student, section = find_student(usn)
    if not student:
        return "Student not found", 404

    students = load_students(section)
    idx = next((i for i, s in enumerate(students) 
                if normalize(s.get("usn")) == normalize(usn)), None)

    if idx is None:
        return "Student not found in section file", 404

    # ensure internal marks is always a dict
    students[idx].setdefault("internal_marks", {})

    if request.method == "POST":
        for key, val in request.form.items():
            val = val.strip()
            if val.isdigit():
                students[idx]["internal_marks"][key] = int(val)

        save_students(section, students)
        flash("Marks updated", "success")
        return redirect(url_for("admin_students", section=section))

    return render_template(
        "admin_internal_marks.html",
        student=students[idx],
        section=section
    )
# ------------------ ADMIN: ATTENDANCE ------------------
@app.route("/admin/attendance/<usn>", methods=["GET", "POST"])
def admin_attendance(usn):
    if not session.get("is_admin"):
        return redirect(url_for("login"))

    # find student
    student, section = find_student(usn)
    if not student:
        return "Student not found", 404

    students = load_students(section)

    idx = next((i for i, s in enumerate(students)
                if normalize(s.get("usn")) == normalize(usn)), None)

    if idx is None:
        return "Student not found in section file", 404

    # ensure attendance exists & is integer
    if "attendance" not in students[idx] or not isinstance(students[idx]["attendance"], int):
        students[idx]["attendance"] = int(students[idx].get("attendance", 0))

    if request.method == "POST":
        new_value = request.form.get("attendance", "").strip()

        if new_value.isdigit():
            students[idx]["attendance"] = int(new_value)
            save_students(section, students)
            flash("Attendance updated successfully", "success")
            return redirect(url_for("admin_students", section=section))
        else:
            flash("Invalid attendance value", "danger")

    return render_template(
        "admin_edit_attendance.html",
        student=students[idx],
        section=section
    )
# ------------------ ADMIN: ATTENDANCE HOME (SECTION SELECT) ------------------

@app.route("/admin/attendance_home")
def admin_attendance_index():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    return render_template("admin_attendance.html")


# ------------------ ADMIN: ATTENDANCE SECTION VIEW ------------------

@app.route("/admin/attendance_home/<section>")
def admin_attendance_section(section):
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    sec = section.upper()
    if sec not in ("A", "B", "C"):
        abort(404)
    students = load_students(sec)
    return render_template("admin_attendance_section.html", section=sec, students=students)

# ------------------ STUDENT: DASHBOARD & FLOWS ------------------

@app.route("/student/dashboard")
def student_dashboard():
    usn = session.get("student_usn")
    if not usn:
        return redirect(url_for("login"))
    stu, sec = find_student(usn)
    if not stu:
        flash("Student record missing", "danger")
        return redirect(url_for("logout"))
    # pass recent assignments & notifications
    assignments = load_json(FILES["assignments"])
    notifs = load_json(FILES["notifications"])
    return render_template("student_dashboard.html", student=stu, section=sec, assignments=assignments, notifications=notifs)

@app.route("/student/assignments")
def student_assignments_list():
    usn = session.get("student_usn")
    if not usn:
        return redirect(url_for("login"))

    assignments = load_json(FILES["assignments"])
    return render_template("student_assignments_list.html", assignments=assignments)

@app.route("/student/assignments/<aid>", methods=["GET","POST"])
def student_submit_assignment(aid):
    # submit assignment upload
    # allow both logged students and manual name if needed
    assignments = load_json(FILES["assignments"])
    item = next((a for a in assignments if str(a.get("id"))==str(aid)), None)
    if not item:
        return "Assignment not found", 404
    if request.method == "POST":
        usn = session.get("student_usn") or request.form.get("student_name")
        file = request.files.get("submission")
        if file and allowed_file(file.filename) and usn:
            folder = os.path.join(UPLOAD_DIR, "student_submissions", str(aid))
            os.makedirs(folder, exist_ok=True)
            fname = f"{int(time.time())}_{secure_filename(file.filename)}"
            file.save(os.path.join(folder, fname))
            item.setdefault("submissions", []).append({
                "student_usn": usn,
                "file": fname,
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            save_json(FILES["assignments"], assignments)
            flash("Submission uploaded", "success")
            return redirect(url_for("student_dashboard"))
        flash("Upload failed", "danger")
    return render_template("student_assignments.html", assignment=item)

@app.route("/study_material")
def study_material():
    notes = load_json(FILES["notes"])
    return render_template("study_material.html", notes=notes, subjects=subject_data)

@app.route("/notifications")
def notifications_page():
    notif = load_json(FILES["notifications"])
    return render_template("notifications.html", notifications=notif)

@app.route("/internal_marks")
def internal_marks():
    usn = session.get("student_usn")
    if not usn:
        return redirect(url_for("login"))
    stu, sec = find_student(usn)
    return render_template("internal_marks.html", student=stu, internal_marks=stu.get("internal_marks", {}))

@app.route("/attendance")
def attendance_page():
    usn = session.get("student_usn")
    if not usn:
        return redirect(url_for("login"))
    stu, sec = find_student(usn)
    # If attendance stored as number or dict, handle both
    return render_template("attendance.html", student=stu, attendance=stu.get("attendance", {}))

@app.route("/profile")
def profile_page():
    usn = session.get("student_usn")
    if not usn:
        return redirect(url_for("login"))
    stu, sec = find_student(usn)
    return render_template("profile.html", student=stu, section=sec)

# ------------------ FILE SERVING ------------------

@app.route("/files/notes/<filename>")
def download_note(filename):
    return send_from_directory(os.path.join(UPLOAD_DIR,"notes"), filename, as_attachment=False)

@app.route("/files/admin/<filename>")
def download_admin_assignment(filename):
    return send_from_directory(os.path.join(UPLOAD_DIR,"admin_assignments"), filename, as_attachment=False)

@app.route("/files/student/<aid>/<filename>")
def download_student_submission(aid, filename):
    folder = os.path.join(UPLOAD_DIR, "student_submissions", str(aid))
    return send_from_directory(folder, filename, as_attachment=False)

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))

@app.route("/faculty")
def timetable_page():
    return render_template("faculty.html")


# ------------------ RUN ------------------

if __name__ == "__main__":
    app.run(debug=True)