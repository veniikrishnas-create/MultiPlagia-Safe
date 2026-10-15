import os
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ----------------- Folders -----------------
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# ----------------- Read Text -----------------
def read_text(filepath):
    """Read text file safely."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

# ----------------- Highlight Common Words -----------------
def highlight_text(text1, text2):
    """Highlights common words between text1 and text2."""
    words2 = set(re.findall(r'\w+', text2.lower()))
    highlighted = []
    for word in text1.split():
        clean_word = re.sub(r'\W+', '', word).lower()
        if clean_word in words2 and len(clean_word) > 3:
            highlighted.append(f"<mark>{word}</mark>")
        else:
            highlighted.append(word)
    return " ".join(highlighted)

# ----------------- Compute Paraphrase Similarity -----------------
def paraphrase_similarity(text1, text2):
    """Compute TF-IDF cosine similarity between two text strings."""
    vectorizer = TfidfVectorizer().fit_transform([text1, text2])
    vectors = vectorizer.toarray()
    score = cosine_similarity([vectors[0]], [vectors[1]])[0][0]
    return score

# ----------------- Compare Files -----------------
def compare_paraphrase(file_paths):
    """Compare two files and return a result dictionary."""
    if len(file_paths) != 2:
        raise ValueError("Two files must be provided.")

    file1_path, file2_path = file_paths
    text1 = read_text(file1_path)
    text2 = read_text(file2_path)

    score = paraphrase_similarity(text1, text2) * 100
    unique = 100 - score

    result = {
        "file1": os.path.basename(file1_path),
        "file2": os.path.basename(file2_path),
        "score": round(score, 2),
        "unique": round(unique, 2),
        "file1_content": highlight_text(text1, text2),
        "file2_content": highlight_text(text2, text1)
    }

    return result

# ----------------- Save HTML Result -----------------
def save_html(result, filename="paraphrase_result.html"):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Paraphrase Result</title>
<style>
body {{font-family:'Segoe UI',sans-serif;background:#f0f4f8;color:#1f2937;}}
.container {{max-width:900px;margin:40px auto;padding:30px;background:#fff;border:2px solid #00897b;border-radius:12px;}}
.files-container {{display:flex;gap:20px;margin-top:30px;}}
.file-card {{flex:1;background:#f9f9f9;padding:20px;border-radius:10px;border:1px solid #ccc;overflow-x:auto;}}
mark {{background-color:#ffff00;}}
</style>
</head>
<body>
<div class="container">
<h2>Paraphrase Report</h2>
<h3>{result['score']}% Plagiarised | {result['unique']}% Unique</h3>
<p><b>Files:</b> {result['file1']} and {result['file2']}</p>
<div class="files-container">
<div class="file-card"><h4>File 1</h4><pre>{result['file1_content']}</pre></div>
<div class="file-card"><h4>File 2</h4><pre>{result['file2_content']}</pre></div>
</div>
</div>
</body>
</html>
"""
    path = os.path.join(RESULT_FOLDER, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Result saved to {path}")

# ----------------- Main Execution -----------------
if __name__ == "__main__":
    uploaded = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.txt')]
    if len(uploaded) < 2:
        print("Please upload at least 2 text files in the 'uploads' folder.")
    else:
        file1 = uploaded[0]
        file2 = uploaded[1]
        result = compare_paraphrase([file1, file2])
        save_html(result)