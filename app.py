import os
import difflib
import json
import secrets
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_from_directory, send_file
)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from backend.text_plagiarism import read_text, highlight_matches as text_highlight
from backend.slide_plagiarism import extract_text, highlight_matches as slide_highlight
from backend.resume_plagiarism import read_text as resume_read, highlight_text as resume_highlight
from backend.code_plagiarism import read_code, highlight_matches as code_highlight
from backend.paraphrase_plagiarism import paraphrase_similarity, highlight_text as para_highlight
from backend.image_plagiarism import compare_images
from backend.settings_manager import load_settings, save_settings


# ---------------- Flask Setup ---------------- #

app = Flask(__name__)

# Set FLASK_SECRET_KEY in Render Environment Variables.
# The fallback is only for local development.
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
REPORT_FOLDER = os.environ.get("REPORT_FOLDER", "reports")
USERS_FILE = os.environ.get("USERS_FILE", "users.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)


# ---------------- User Management ---------------- #

def load_users():
    """Load existing user hashes without resetting the admin password."""

    if not os.path.exists(USERS_FILE):
        admin_username = os.environ.get("ADMIN_USERNAME")
        admin_password = os.environ.get("ADMIN_PASSWORD")

        if not admin_username or not admin_password:
            return {}

        users = {
            admin_username: generate_password_hash(admin_password)
        }
        save_users(users)
        return users

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as file:
            users = json.load(file)

        return users if isinstance(users, dict) else {}

    except (OSError, json.JSONDecodeError) as error:
        app.logger.error("Could not load user data: %s", error)
        return {}


def save_users(users):
    """Save user password hashes."""

    folder = os.path.dirname(USERS_FILE)

    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(USERS_FILE, "w", encoding="utf-8") as file:
        json.dump(users, file)


# ---------------- File Serving ---------------- #

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/welcome")
def welcome():
    if "user" not in session:
        return redirect(url_for("home"))

    return render_template("welcome.html")


@app.route("/reports/<path:filename>")
def get_report(filename):
    return send_from_directory(REPORT_FOLDER, filename)


# ---------------- Similarity Helper ---------------- #

def safe_tfidf_similarity(text1, text2):
    """Compute TF-IDF cosine similarity safely."""

    text1 = text1.strip()
    text2 = text2.strip()

    if not text1 or not text2:
        return None

    try:
        vectorizer = TfidfVectorizer().fit([text1, text2])
        tfidf = vectorizer.transform([text1, text2])

        if tfidf.shape[1] == 0:
            return None

        score = cosine_similarity(
            tfidf[0:1], tfidf[1:2]
        )[0][0] * 100

        return round(score, 2)

    except ValueError:
        return 0.0


# ---------------- Report Creation ---------------- #

def create_report_html(
    category, similarity, f1, f2,
    content_a="", content_b=""
):
    """Generate an HTML report."""

    filename = (
        f"report_{category.lower()}_"
        f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}.html"
    )

    path = os.path.join(REPORT_FOLDER, filename)

    html = render_template(
        "pdf_result.html",
        category=category,
        result={
            "similarity": similarity,
            "file_a": f1,
            "file_b": f2,
            "content_a": content_a,
            "content_b": content_b,
        },
        generated_date=datetime.now().strftime("%Y-%m-%d"),
        generated_time=datetime.now().strftime("%H:%M:%S")
    )

    with open(path, "w", encoding="utf-8") as file:
        file.write(html)

    return filename


# ---------------- Home and Login ---------------- #

@app.route("/")
def home():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    users = load_users()

    if username in users and check_password_hash(users[username], password):
        session.clear()
        session["user"] = username
        return redirect(url_for("welcome"))

    flash("Invalid username or password")
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------------- Informational Pages ---------------- #

@app.route("/sample")
def sample_page():
    return render_template("sample_page.html")


@app.route("/tips")
def tips_page():
    return render_template("tips_page.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/help")
def help_page():
    return render_template("help_page.html")


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("home"))

    return render_template("dashboard.html")


# ---------------- Reviews ---------------- #

submitted_reviews = []
next_id = 1


@app.route("/review", methods=["GET", "POST"])
def review():
    global next_id

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        message = request.form.get("message", "").strip()

        try:
            stars = int(request.form.get("stars", "0"))
        except ValueError:
            stars = 0

        if not name or not message or stars < 1 or stars > 5:
            flash("Please enter valid review details.")
            return redirect(url_for("review"))

        submitted_reviews.append({
            "id": next_id,
            "name": name,
            "message": message,
            "stars": stars
        })

        next_id += 1

        return render_template(
            "review.html",
            success=True,
            reviews=submitted_reviews
        )

    return render_template(
        "review.html",
        reviews=submitted_reviews
    )


@app.route("/review/delete/<int:review_id>", methods=["POST"])
def delete_review(review_id):
    global submitted_reviews

    submitted_reviews = [
        review_item
        for review_item in submitted_reviews
        if review_item["id"] != review_id
    ]

    return redirect(url_for("review"))


# ---------------- Report History ---------------- #

@app.route("/history")
def history():
    if "user" not in session:
        return redirect(url_for("home"))

    reports = []

    for filename in os.listdir(REPORT_FOLDER):
        path = os.path.join(REPORT_FOLDER, filename)

        if os.path.isfile(path):
            reports.append({
                "name": filename,
                "time": datetime.fromtimestamp(
                    os.path.getmtime(path)
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "path": url_for("get_report", filename=filename)
            })

    reports.sort(key=lambda item: item["time"], reverse=True)

    return render_template("history.html", reports=reports)


@app.route("/delete_report/<path:filename>", methods=["POST"])
def delete_report(filename):
    if "user" not in session:
        return redirect(url_for("home"))

    safe_name = os.path.basename(filename)
    file_path = os.path.join(REPORT_FOLDER, safe_name)

    if os.path.isfile(file_path):
        os.remove(file_path)

    return redirect(url_for("history"))


# ---------------- Settings ---------------- #

@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    if "user" not in session:
        return redirect(url_for("home"))

    settings = load_settings()

    if request.method == "POST":
        save_settings(request.form)
        flash("Settings updated successfully!")
        return redirect(url_for("settings_page"))

    return render_template(
        "settings_page.html",
        settings=settings
    )


# ---------------- Profile ---------------- #

@app.route("/profile", methods=["GET", "POST"])
def profile_page():
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    current = session["user"]

    if current not in users:
        session.clear()
        return redirect(url_for("home"))

    if request.method == "POST":
        new_username = request.form.get("username", "").strip()
        new_password = request.form.get("password", "")

        if not new_username:
            flash("Username cannot be empty.")
            return redirect(url_for("profile_page"))

        if new_username != current and new_username in users:
            flash("Username already exists!")
            return redirect(url_for("profile_page"))

        if new_username != current:
            users[new_username] = users.pop(current)

        # Keep the current password if the password field is empty.
        if new_password:
            users[new_username] = generate_password_hash(new_password)

        save_users(users)

        session["user"] = new_username
        flash("Profile updated successfully!")

        return redirect(url_for("profile_page"))

    return render_template(
        "profile_page.html",
        profile={"username": current}
    )


# ---------------- Upload Helper ---------------- #

def save_uploaded_file(file_storage):
    """Validate a filename and save the uploaded file."""

    if not file_storage or not file_storage.filename:
        raise ValueError("Please select a file.")

    filename = secure_filename(file_storage.filename)

    if not filename:
        raise ValueError("Invalid filename.")

    path = os.path.join(UPLOAD_FOLDER, filename)
    file_storage.save(path)

    return filename, path


def get_two_files(field1="file1", field2="file2"):
    file1 = request.files.get(field1)
    file2 = request.files.get(field2)

    name1, path1 = save_uploaded_file(file1)
    name2, path2 = save_uploaded_file(file2)

    return name1, path1, name2, path2


def calculate_similarity(text1, text2, stop_words=None):
    """Return similarity and uniqueness percentages."""

    try:
        vectorizer = TfidfVectorizer(stop_words=stop_words)
        tfidf = vectorizer.fit_transform([text1, text2])

        score = cosine_similarity(
            tfidf[0:1], tfidf[1:2]
        )[0][0] * 100

    except ValueError:
        score = 0.0

    score = round(float(score), 2)
    unique = round(100 - score, 2)

    return score, unique


# ---------------- Text Plagiarism ---------------- #

@app.route("/check_text", methods=["GET", "POST"])
def check_text():
    if "user" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        try:
            name1, path1, name2, path2 = get_two_files()

            text1 = read_text(path1)
            text2 = read_text(path2)

            score, unique = calculate_similarity(text1, text2)

            highlighted1 = text_highlight(text1, text2)
            highlighted2 = text_highlight(text2, text1)

            matcher = difflib.SequenceMatcher(None, text1, text2)

            matches = [
                text1[block.a:block.a + block.size].strip()
                for block in matcher.get_matching_blocks()
                if block.size > 8
            ]

            common_content = (
                "\n".join(set(matches))
                if matches
                else "No significant plagiarised content found."
            )

            report_file = create_report_html(
                "Text", score, name1, name2,
                content_a=highlighted1,
                content_b=highlighted2
            )

            result = {
                "file1": name1,
                "file2": name2,
                "score": score,
                "unique": unique,
                "file1_content": highlighted1,
                "file2_content": highlighted2,
                "common_content": common_content,
                "report_file": report_file
            }

            return render_template(
                "result_common.html",
                result=result,
                category="Text"
            )

        except (ValueError, OSError) as error:
            flash(str(error))
            return redirect(url_for("check_text"))

    return render_template("check_text.html")


# ---------------- Slides Plagiarism ---------------- #

@app.route("/check_slides", methods=["GET", "POST"])
def check_slides():
    if "user" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        try:
            name1, path1, name2, path2 = get_two_files()

            text1 = extract_text(path1)
            text2 = extract_text(path2)

            score, unique = calculate_similarity(text1, text2)

            report_file = create_report_html(
                "Slides", score, name1, name2,
                content_a=text1,
                content_b=text2
            )

            result = {
                "file1": name1,
                "file2": name2,
                "score": score,
                "unique": unique,
                "file1_content": slide_highlight(text1, text2),
                "file2_content": slide_highlight(text2, text1),
                "report_file": report_file
            }

            return render_template(
                "result_common.html",
                result=result,
                category="Slides"
            )

        except (ValueError, OSError) as error:
            flash(str(error))
            return redirect(url_for("check_slides"))

    return render_template("check_slides.html")


# ---------------- Paraphrase Plagiarism ---------------- #

@app.route("/check_paraphrase", methods=["GET", "POST"])
def check_paraphrase():
    if "user" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        try:
            name1, path1, name2, path2 = get_two_files()

            text1 = read_text(path1)
            text2 = read_text(path2)

            score = round(
                float(paraphrase_similarity(text1, text2)) * 100,
                2
            )
            unique = round(100 - score, 2)

            report_file = create_report_html(
                "paraphrase", score, name1, name2,
                content_a=text1,
                content_b=text2
            )

            result = {
                "file1": name1,
                "file2": name2,
                "score": score,
                "unique": unique,
                "file1_content": para_highlight(text1, text2),
                "file2_content": para_highlight(text2, text1),
                "report_file": report_file
            }

            return render_template(
                "result_common.html",
                result=result,
                category="Paraphrase"
            )

        except (ValueError, OSError) as error:
            flash(str(error))
            return redirect(url_for("check_paraphrase"))

    return render_template("check_paraphrase.html")


# ---------------- Code Plagiarism ---------------- #

@app.route("/check_code", methods=["GET", "POST"])
def check_code():
    if "user" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        try:
            name1, path1, name2, path2 = get_two_files()

            text1 = read_code(path1)
            text2 = read_code(path2)

            score, unique = calculate_similarity(text1, text2)

            report_file = create_report_html(
                "code", score, name1, name2,
                content_a=text1,
                content_b=text2
            )

            result = {
                "file1": name1,
                "file2": name2,
                "score": score,
                "unique": unique,
                "file1_content": code_highlight(text1, text2),
                "file2_content": code_highlight(text2, text1),
                "report_file": report_file
            }

            return render_template(
                "result_common.html",
                result=result,
                category="Code"
            )

        except (ValueError, OSError) as error:
            flash(str(error))
            return redirect(url_for("check_code"))

    return render_template("check_code.html")


# ---------------- Resume Plagiarism ---------------- #

@app.route("/check_resume", methods=["GET", "POST"])
def check_resume():
    if "user" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        try:
            name1, path1, name2, path2 = get_two_files(
                "resume1", "resume2"
            )

            text1 = read_text(path1)
            text2 = read_text(path2)

            score, unique = calculate_similarity(
                text1, text2, stop_words="english"
            )

            report_file = create_report_html(
                "resume", score, name1, name2,
                content_a=text1,
                content_b=text2
            )

            result = {
                "file1": name1,
                "file2": name2,
                "score": score,
                "unique": unique,
                "file1_content": text_highlight(text1, text2),
                "file2_content": text_highlight(text2, text1),
                "report_file": report_file
            }

            return render_template(
                "result_common.html",
                result=result,
                category="Resume"
            )

        except (ValueError, OSError) as error:
            flash(str(error))
            return redirect(url_for("check_resume"))

    return render_template("check_resume.html")


# ---------------- Image Plagiarism ---------------- #

@app.route("/check_image", methods=["GET", "POST"])
def check_image():
    if "user" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        try:
            name1, path1, name2, path2 = get_two_files()

            score = float(compare_images(path1, path2))
            score = round(max(0, min(100, score)), 2)
            unique = round(100 - score, 2)

            report_file = create_report_html(
                "Image", score, name1, name2
            )

            result = {
                "file1": name1,
                "file2": name2,
                "score": score,
                "unique": unique,
                "file1_path": url_for(
                    "uploaded_file", filename=name1
                ),
                "file2_path": url_for(
                    "uploaded_file", filename=name2
                ),
                "report_file": report_file
            }

            return render_template(
                "result_image.html",
                result=result,
                category="Image"
            )

        except (ValueError, OSError) as error:
            flash(str(error))
            return redirect(url_for("check_image"))

    return render_template("check_image.html")


# ---------------- Report Download ---------------- #

@app.route("/pdf_result/<path:filename>")
def pdf_result(filename):
    if "user" not in session:
        return redirect(url_for("home"))

    safe_name = os.path.basename(filename)
    file_path = os.path.join(REPORT_FOLDER, safe_name)

    if not os.path.isfile(file_path):
        return "Report not found", 404

    return send_file(file_path, as_attachment=True)


@app.route("/pdf_result_image/<file_a>/<file_b>/<int:similarity>")
def pdf_result_image(file_a, file_b, similarity):
    if "user" not in session:
        return redirect(url_for("home"))

    file_a = secure_filename(file_a)
    file_b = secure_filename(file_b)

    generated_at = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    result = {
        "file_a": file_a,
        "file_b": file_b,
        "content_a": url_for("uploaded_file", filename=file_a),
        "content_b": url_for("uploaded_file", filename=file_b),
        "similarity": similarity
    }

    return render_template(
        "pdf_result_image.html",
        category="Image",
        result=result,
        generated_at=generated_at
    )


# ---------------- Analytics ---------------- #

@app.route("/analytics")
def analytics():
    if "user" not in session:
        return redirect(url_for("home"))

    reports = os.listdir(REPORT_FOLDER)
    total_reports = len(reports)

    categories = {
        "Text": 0,
        "Code": 0,
        "Resume": 0,
        "Image": 0,
        "Paraphrase": 0,
        "Slides": 0
    }

    for report_name in reports:
        for category in categories:
            if category.lower() in report_name.lower():
                categories[category] += 1

    return render_template(
        "analytics.html",
        total_reports=total_reports,
        categories_json=json.dumps(categories)
    )


# ---------------- Run Application ---------------- #

if __name__ == "__main__":
    app.run(debug=True)