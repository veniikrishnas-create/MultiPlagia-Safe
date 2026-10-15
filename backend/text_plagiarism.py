import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

UPLOAD_FOLDER='uploads'
LOCAL_FOLDER='local_files'
RESULT_FOLDER='results'
os.makedirs(RESULT_FOLDER, exist_ok=True)

def read_text(path):
    with open(path,'r',encoding='utf-8',errors='ignore') as f:
        return f.read()

def highlight_matches(text1,text2):
    words2 = set(text2.split())
    return ' '.join([f'<mark>{w}</mark>' if w in words2 and len(w)>3 else w for w in text1.split()])

def save_html(result, filename="text_result.html"):
    html=f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>Text Plagiarism</title>
<style>
body{{font-family:'Segoe UI',sans-serif;background:#f0f4f8;color:#1f2937;}}
.container{{max-width:900px;margin:40px auto;padding:30px;background:#fff;border:2px solid #00897b;border-radius:12px;}}
.files-container{{display:flex;gap:20px;margin-top:30px;}}
.file-card{{flex:1;background:#f9f9f9;padding:20px;border-radius:10px;border:1px solid #ccc;overflow-x:auto;}}
mark{{background-color:#ffff00;}}
</style></head><body>
<div class="container">
<h2>Text Plagiarism Report</h2>
<h3>{result['score']}% Plagiarised | {result['unique']}% Unique</h3>
<p><b>Files:</b> {result['file1']} and {result['file2']}</p>
<div class="files-container">
<div class="file-card"><h4>File 1</h4><pre>{result['file1_content']}</pre></div>
<div class="file-card"><h4>File 2</h4><pre>{result['file2_content']}</pre></div>
</div>
</div></body></html>"""
    with open(os.path.join(RESULT_FOLDER, filename),'w',encoding='utf-8') as f:
        f.write(html)

if __name__=="main_":
    uploaded = [os.path.join(UPLOAD_FOLDER,f) for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.txt')]
    if not uploaded:
        print("Upload .txt files")
    else:
        file1 = uploaded[0]
        file2 = uploaded[1] if len(uploaded)>1 else os.path.join(LOCAL_FOLDER, os.listdir(LOCAL_FOLDER)[0])
        text1 = read_text(file1)
        text2 = read_text(file2)
        vectorizer = TfidfVectorizer().fit([text1,text2])
        tfidf = vectorizer.transform([text1,text2])
        score = cosine_similarity(tfidf[0:1],tfidf[1:2])[0][0]*100
        unique = 100 - score
        highlighted1 = highlight_matches(text1,text2)
        highlighted2 = highlight_matches(text2,text1)
        result={'file1':os.path.basename(file1),'file2':os.path.basename(file2),
                'score':round(score,2),'unique':round(unique,2),
                'file1_content':highlighted1,'file2_content':highlighted2}
        save_html(result)
        print(f"Result saved to {RESULT_FOLDER}/text_result.html")