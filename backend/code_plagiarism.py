import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Folders
UPLOAD_FOLDER = 'uploads'
LOCAL_FOLDER = 'local_files'
RESULT_FOLDER = 'results'
os.makedirs(RESULT_FOLDER, exist_ok=True)

def read_code(file_path):
    """Read code from a file"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

def highlight_matches(text1, text2):
    """Highlight matching code tokens"""
    words2 = set(text2.split())
    return ' '.join([f'<mark>{w}</mark>' if w in words2 and len(w)>1 else w for w in text1.split()])

def save_html(result, filename="code_result.html"):
    """Generate HTML report for code plagiarism"""
    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>Code Plagiarism Report</title>
<style>
body {{ font-family:'Consolas, monospace'; background:#f0f4f8; color:#1f2937; }}
.container {{ max-width:900px; margin:40px auto; padding:30px; background:#fff; border:2px solid #00897b; border-radius:12px; }}
.files-container {{ display:flex; gap:20px; margin-top:30px; }}
.file-card {{ flex:1; background:#f9f9f9; padding:20px; border-radius:10px; border:1px solid #ccc; overflow-x:auto; }}
mark {{ background-color:#ffff00; }}
</style>
</head>
<body>
<div class="container">
<h2>Code Plagiarism Report</h2>
<h3>{result['score']}% Plagiarised | {result['unique']}% Unique</h3>
<p><b>Files Compared:</b> {result['file1']} and {result['file2']}</p>
<div class="files-container">
<div class="file-card"><h4>File 1</h4><pre>{result['file1_content']}</pre></div>
<div class="file-card"><h4>File 2</h4><pre>{result['file2_content']}</pre></div>
</div>
<div style="margin-top:30px;padding:20px;background:#ffe0b2;border-radius:10px;border:1px solid #ff9800;">
<h4>Matched Snippets</h4>
<pre>{result['common_content']}</pre>
</div>
</div>
</body>
</html>
"""
    with open(os.path.join(RESULT_FOLDER, filename), 'w', encoding='utf-8') as f:
        f.write(html)

def compare_code_files(uploaded):
    """Compare two code files"""
    file1 = uploaded[0]
    file2 = uploaded[1] if len(uploaded) > 1 else os.path.join(LOCAL_FOLDER, os.listdir(LOCAL_FOLDER)[0])
    
    code1 = read_code(file1)
    code2 = read_code(file2)
    
    # Compute TF-IDF similarity
    vectorizer = TfidfVectorizer().fit([code1, code2])
    tfidf = vectorizer.transform([code1, code2])
    score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100
    unique = 100 - score
    
    highlighted1 = highlight_matches(code1, code2)
    highlighted2 = highlight_matches(code2, code1)
    common = ' '.join([w for w in code1.split() if w in code2.split() and len(w)>1])
    
    result = {
        'file1': os.path.basename(file1),
        'file2': os.path.basename(file2),
        'score': round(score,2),
        'unique': round(unique,2),
        'file1_content': highlighted1,
        'file2_content': highlighted2,
        'common_content': common
    }
    
    save_html(result)
    print(f"Code plagiarism report saved to {RESULT_FOLDER}/code_result.html")

if __name__=="__main__":
    uploaded = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.endswith(('.py','.java','.c','.cpp','.js'))]
    if not uploaded:
        print("Upload at least 1 code file in uploads folder")
    else:
        compare_code_files(uploaded)