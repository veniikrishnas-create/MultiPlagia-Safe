import os
import difflib
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from werkzeug.utils import secure_filename
import json
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




from werkzeug.security import generate_password_hash
import json

users = {"admin": generate_password_hash("admin123")}
with open("users.json", "w") as f:
    json.dump(users, f) 



app.secret_key = "secret123"
UPLOAD_FOLDER = "uploads"
REPORT_FOLDER = "reports"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        default = {"admin": generate_password_hash("admin123")}
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f)
        return default
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f)


# ---------------- Serve uploaded/report files ---------------- #
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/welcome')
def welcome():
    return render_template('welcome.html') 

@app.route('/reports/<filename>')
def get_report(filename):
    return send_from_directory(REPORT_FOLDER, filename)

# ---------------- Helper Functions ---------------- #
def safe_tfidf_similarity(text1, text2):
    """Compute TF-IDF cosine similarity safely."""
    text1 = text1.strip()
    text2 = text2.strip()
    if not text1 or not text2:
        return None  # empty file
    try:
        vectorizer = TfidfVectorizer().fit([text1, text2])
        tfidf = vectorizer.transform([text1, text2])
        if tfidf.shape[1] == 0:
            return None
        score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100
        return round(score, 2)
    except Exception as e:
        print("TF-IDF error:", e)
        return None

def create_report_html(category, similarity, f1, f2, content_a="", content_b=""):
    """Generate HTML report file."""
    filename = f"report_{category.lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}.html"
    path = os.path.join(REPORT_FOLDER, filename)
    generated_date = datetime.now().strftime("%Y-%m-%d")
    generated_time = datetime.now().strftime("%H:%M:%S")
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
        generated_date=generated_date,
        generated_time=generated_time
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return filename

# ---------------- Home/Login ---------------- #
@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    users = load_users()
    if username in users and check_password_hash(users[username], password):
        session["user"] = username
        return redirect(url_for("welcome"))
    else:
        flash("Invalid username or password")
        return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))
 

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
    return render_template("dashboard.html")


from flask import Flask, render_template, request, redirect, url_for


# Use a list of dicts for reviews, each with a unique ID
submitted_reviews = []
next_id = 1  # Global ID counter

@app.route("/review", methods=["GET", "POST"])
def review():
    global next_id
    if request.method == "POST":
        name = request.form.get("name")
        message = request.form.get("message")
        stars = int(request.form.get("stars"))

        submitted_reviews.append({
            "id": next_id,
            "name": name,
            "message": message,
            "stars": stars
        })
        next_id += 1

        return render_template("review.html", success=True, reviews=submitted_reviews)

    return render_template("review.html", reviews=submitted_reviews)

@app.route("/review/delete/<int:review_id>", methods=["POST"])
def delete_review(review_id):
    global submitted_reviews
    # Remove the review with matching id
    submitted_reviews = [r for r in submitted_reviews if r["id"] != review_id]
    return redirect(url_for("review"))





@app.route("/history")
def history():
    reports = []
    for f in os.listdir(REPORT_FOLDER):
        path = os.path.join(REPORT_FOLDER, f)
        if os.path.isfile(path):
            reports.append({
                "name": f,
                "time": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S"),
                "path": url_for("get_report", filename=f)
            })
    reports = sorted(reports, key=lambda x: x["time"], reverse=True)
    return render_template("history.html", reports=reports)

@app.route("/delete_report/<filename>")
def delete_report(filename):
    file_path = os.path.join(REPORT_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect(url_for("history"))


# ---------------- Settings/Profile ---------------- #
@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    settings = load_settings()
    if request.method == "POST":
        save_settings(request.form)
        flash("Settings updated successfully!")
        return redirect(url_for("settings_page"))
    return render_template("settings_page.html", settings=settings)

@app.route("/profile", methods=["GET", "POST"])
def profile_page():
    if "user" not in session:
        return redirect(url_for("home"))

    users = load_users()
    current = session["user"]

    if request.method == "POST":
        new_username = request.form["username"].strip()
        new_password = request.form["password"]

        if new_username != current and new_username in users:
            flash("Username already exists!")
            return redirect(url_for("profile_page"))

        # remove old username if changed
        if new_username != current:
            users[new_username] = users.pop(current)

        # update password
        users[new_username] = generate_password_hash(new_password)
        save_users(users)

        session["user"] = new_username
        flash("Profile updated successfully!")
        return redirect(url_for("profile_page"))

    return render_template("profile_page.html", profile={"username": current})
#_TEXT_#
@app.route("/check_text", methods=["GET", "POST"])
def check_text():
    if request.method == "POST":
        file1, file2 = request.files["file1"], request.files["file2"]
        path1, path2 = os.path.join(UPLOAD_FOLDER, file1.filename), os.path.join(UPLOAD_FOLDER, file2.filename)
        file1.save(path1); file2.save(path2)

        text1, text2 = read_text(path1), read_text(path2)
        vectorizer = TfidfVectorizer().fit([text1, text2])
        tfidf = vectorizer.transform([text1, text2])
        score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100
        unique = 100 - score

        highlighted1, highlighted2 = text_highlight(text1, text2), text_highlight(text2, text1)

        matcher = difflib.SequenceMatcher(None, text1, text2)
        matches = [text1[block.a:block.a+block.size].strip() for block in matcher.get_matching_blocks() if block.size > 8]
        common_content = "\n".join(set(matches)) if matches else "No significant plagiarised content found."

        report_file = create_report_html("Text", round(score,2), file1.filename, file2.filename,
                                         content_a=highlighted1, content_b=highlighted2)

        result = {"file1": file1.filename, "file2": file2.filename,
                  "score": round(score, 2), "unique": round(unique, 2),
                  "file1_content": highlighted1, "file2_content": highlighted2,
                  "common_content": common_content, "report_file": report_file}
        return render_template("result_common.html", result=result, category="Text")
    return render_template("check_text.html")

# ---------------- Slides Check ---------------- #
@app.route("/check_slides", methods=["GET", "POST"])
def check_slides():
    if request.method == "POST":
        file1, file2 = request.files["file1"], request.files["file2"]
        path1, path2 = os.path.join(UPLOAD_FOLDER, file1.filename), os.path.join(UPLOAD_FOLDER, file2.filename)
        file1.save(path1); file2.save(path2)

        text1, text2 = extract_text(path1), extract_text(path2)
        vectorizer = TfidfVectorizer().fit([text1, text2])
        tfidf = vectorizer.transform([text1, text2])
        score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100
        unique = 100 - score

        report_file = create_report_html("Slides", round(score,2), file1.filename, file2.filename,
                                         content_a=text1, content_b=text2)

        result = {"file1": file1.filename, "file2": file2.filename,
                  "score": round(score, 2), "unique": round(unique, 2),
                  "file1_content": slide_highlight(text1, text2),
                  "file2_content": slide_highlight(text2, text1),
                  "report_file": report_file}
        return render_template("result_common.html", result=result, category="Slides")
    return render_template("check_slides.html")

# ---------------- PARAPHRASE CHECK ---------------- #
# ---------------- Paraphrase Check ---------------- #
@app.route("/check_paraphrase", methods=["GET", "POST"])
def check_paraphrase():
    if request.method == "POST":
        file1, file2 = request.files["file1"], request.files["file2"]
        path1, path2 = os.path.join(UPLOAD_FOLDER, file1.filename), os.path.join(UPLOAD_FOLDER, file2.filename)
        file1.save(path1); file2.save(path2)

        # Read text
        text1, text2 = read_text(path1), read_text(path2)

        # Compute similarity
        score = paraphrase_similarity(text1, text2) * 100
        unique = 100 - score
         # Create report file
        report_file = create_report_html("paraphrase", round(score,2), file1.filename, file2.filename,
                                         content_a=text1, content_b=text2)
        
        
        # Pack result dict
        result = {
            "file1": file1.filename,
            "file2": file2.filename,
            "score": round(score, 2),
            "unique": round(unique, 2),
            "file1_content": para_highlight(text1, text2),
            "file2_content": para_highlight(text2, text1),
            "report_file": report_file}

        return render_template("result_common.html", result=result, category="Paraphrase")

    return render_template("check_paraphrase.html")


# ---------------- CODE CHECK ---------------- #
@app.route("/check_code", methods=["GET", "POST"])
def check_code():
    if request.method == "POST":
        file1 = request.files["file1"]
        file2 = request.files["file2"]
        path1 = os.path.join(UPLOAD_FOLDER, file1.filename)
        path2 = os.path.join(UPLOAD_FOLDER, file2.filename)
        file1.save(path1)
        file2.save(path2)

        text1 = read_code(path1)
        text2 = read_code(path2)

        vectorizer = TfidfVectorizer().fit([text1, text2])
        tfidf = vectorizer.transform([text1, text2])
        score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100
        unique = 100 - score
        
        report_file = create_report_html("code", round(score,2), file1.filename, file2.filename,
                                         content_a=text1, content_b=text2)

        result = {
            "file1": file1.filename,
            "file2": file2.filename,
            "score": round(score, 2),
            "unique": round(unique, 2),
            "file1_content": code_highlight(text1, text2),
            "file2_content": code_highlight(text2, text1),
            "report_file": report_file
        }
        return render_template("result_common.html", result=result, category="Code")
    return render_template("check_code.html")

# ---------------- RESUME CHECK ---------------- #
# ---------------- Resume Check ---------------- #
# ---------------- Resume Check ---------------- #
@app.route("/check_resume", methods=["GET", "POST"])
def check_resume():
    if request.method == "POST":
        # Upload files
        file1, file2 = request.files["resume1"], request.files["resume2"]
        path1 = os.path.join(UPLOAD_FOLDER, file1.filename)
        path2 = os.path.join(UPLOAD_FOLDER, file2.filename)
        file1.save(path1)
        file2.save(path2)

        # Read text from resumes
        text1 = read_text(path1)
        text2 = read_text(path2)

        # Calculate TF-IDF similarity
        vectorizer = TfidfVectorizer(stop_words='english').fit([text1, text2])
        tfidf = vectorizer.transform([text1, text2])
        score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100
        unique = 100 - score

        # Highlight common words
        file1_content = text_highlight(text1, text2)
        file2_content = text_highlight(text2, text1)

        # Save HTML report
        report_file = create_report_html("resume", round(score,2), file1.filename, file2.filename,
                                         content_a=text1, content_b=text2)
        # Prepare result dict for template
        result = {
            "file1": file1.filename,
            "file2": file2.filename,
            "score": round(score,2),
            "unique": round(unique,2),
            "file1_content": text_highlight(text1, text2),
            "file2_content": text_highlight(text2, text1),

            "report_file": report_file
        }

        return render_template("result_common.html", result=result, category="Resume")

    return render_template("check_resume.html")

@app.route("/check_image", methods=["GET", "POST"])
def check_image():
    if request.method == "POST":
        file1, file2 = request.files["file1"], request.files["file2"]
        path1, path2 = os.path.join(UPLOAD_FOLDER, file1.filename), os.path.join(UPLOAD_FOLDER, file2.filename)
        file1.save(path1); file2.save(path2)

        score = compare_images(path1, path2)
        unique = 100 - score

        report_file = create_report_html("Image", round(score,2), file1.filename, file2.filename)

        result = {"file1": file1.filename, "file2": file2.filename,
                  "score": round(score, 2), "unique": round(unique, 2),
                  "file1_path": url_for("uploaded_file", filename=file1.filename),
                  "file2_path": url_for("uploaded_file", filename=file2.filename),
                  "report_file": report_file}
        return render_template("result_image.html", result=result, category="Image")
    return render_template("check_image.html")

# ---------------- PDF Result ---------------- #
from flask import send_file
@app.route("/pdf_result/<filename>")
def pdf_result(filename):
    file_path=os.path.join(REPORT_FOLDER,filename)
    return send_file(file_path,as_attachment=True)

from werkzeug.utils import secure_filename

@app.route('/pdf_result_image/<file_a>/<file_b>/<int:similarity>')
def pdf_result_image(file_a, file_b, similarity):
    file_a = secure_filename(file_a)
    file_b = secure_filename(file_b)
    generated_at = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    result = {
        "file_a": file_a,
        "file_b": file_b,
        "content_a": url_for('uploaded_file', filename=file_a),
        "content_b": url_for('uploaded_file', filename=file_b),
        "similarity": similarity
    }
    return render_template("pdf_result_image.html", category="Image", result=result, generated_at=generated_at)


# ---------------- Analytics ---------------- #
@app.route("/analytics")
def analytics():
    reports = os.listdir(REPORT_FOLDER)
    total_reports = len(reports)
    categories = {"Text":0,"Code":0,"Resume":0,"Image":0,"Paraphrase":0,"Slides":0}
    for r in reports:
        for c in categories.keys():
            if c.lower() in r.lower():
                categories[c] += 1
    import json
    return render_template("analytics.html", total_reports=total_reports, categories_json=json.dumps(categories))

# ---------------- Run App ---------------- #
if __name__ == "__main__":
    app.run(debug=True)