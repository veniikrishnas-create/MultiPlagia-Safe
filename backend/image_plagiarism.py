import os
from PIL import Image
import imagehash

UPLOAD_FOLDER = 'uploads'
LOCAL_FOLDER = 'local_files'
RESULT_FOLDER = 'results'
os.makedirs(RESULT_FOLDER, exist_ok=True)

def compare_images(file1, file2):
    hash1 = imagehash.average_hash(Image.open(file1))
    hash2 = imagehash.average_hash(Image.open(file2))
    distance = hash1 - hash2
    similarity = max(0, 100 - distance*10)  # rough % similarity
    return similarity

def save_html(file1, file2, score, filename="image_result.html"):
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset='utf-8'><title>Image Plagiarism</title>
<style>
body{{font-family:'Segoe UI',sans-serif;background:#f0f4f8;color:#1f2937;}}
.container{{max-width:800px;margin:40px auto;padding:30px;background:#fff;border:2px solid #00897b;border-radius:12px;}}
h2,h3{{text-align:center;}}
img{{max-width:100%;margin-top:20px;border:1px solid #ccc;border-radius:10px;}}
</style>
</head>
<body>
<div class="container">
<h2>Image Plagiarism Report</h2>
<h3>Similarity: {score}%</h3>
<p><b>File 1:</b> {os.path.basename(file1)}</p>
<p><b>File 2:</b> {os.path.basename(file2)}</p>
<img src="{file1}" alt="Image 1"/>
<img src="{file2}" alt="Image 2"/>
</div></body></html>"""
    with open(os.path.join(RESULT_FOLDER, filename), 'w') as f:
        f.write(html)

if __name__=="__main__":
    uploaded = [os.path.join(UPLOAD_FOLDER,f) for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(('.png','.jpg','.jpeg'))]
    if not uploaded:
        print("Upload at least 1 image in uploads folder")
    else:
        file1 = uploaded[0]
        file2 = uploaded[1] if len(uploaded)>1 else os.path.join(LOCAL_FOLDER, os.listdir(LOCAL_FOLDER)[0])
        score = compare_images(file1, file2)
        save_html(file1, file2, score)
        print(f"Result saved to {RESULT_FOLDER}/image_result.html")