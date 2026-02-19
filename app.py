from flask import Flask, request, render_template
import re
import pdfplumber
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Step 2 setup: Create a folder to keep the file "remembered" during the session
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

theme_keywords = {
    "education": ["education", "learning", "school", "teacher", "classroom", "knowledge", "study", "exam"],
    "courage": ["courage", "bravery", "heroism", "sacrifice", "fearless"],
    "corruption": ["corruption", "bribery", "impunity", "misuse of power", "grabbing", "embezzlement", "nepotism", "tender", "municipality"],
    "betrayal": ["betrayal", "disloyalty", "treachery", "double-cross", "unfaithful", "abandon", "sell-out"],
    "leadership": ["leadership", "governance", "dictatorship", "regime", "authority", "power struggle", "politics", "heads of state"],
    "change": ["change", "transformation", "reform", "activism", "revolution", "innovation", "protest", "the Samaritan app"],
    "poverty": ["poverty", "struggle", "inequality", "deprivation", "destitution", "suffering", "slums", "underprivileged"],
    "technology": ["technology", "digital", "app", "innovation", "social media", "internet", "online", "software"]

}

# Step 1: Improved Highlighter (Deterministic Logic)
def highlight_content(text, keywords):
    # 1. Clean up newlines so sentences don't break mid-way
    text = text.replace('\n', ' ')
    
    # 2. Split into sentences using regex (looks for . ! or ?)
    sentences = re.split(r'(?<=[.!?]) +', text)
    highlighted_page = []

    for sentence in sentences:
        found_in_sentence = False
        temp_sentence = sentence
        
        for kw in keywords:
            # Check if keyword exists in this sentence
            if re.search(rf"\b{kw}\b", temp_sentence, flags=re.IGNORECASE):
                found_in_sentence = True
                # Bold the keyword
                temp_sentence = re.sub(rf"\b({kw})\b", r"<b>\1</b>", temp_sentence, flags=re.IGNORECASE)
        
        if found_in_sentence:
            # Wrap the matching sentence in a 'mark' tag for the user
            highlighted_page.append(f"<mark style='background-color: #fff3cd;'>{temp_sentence}</mark>")
        else:
            highlighted_page.append(temp_sentence)

    return " ".join(highlighted_page)

@app.route("/ping")
def ping():
    return "OK", 200

@app.route("/", methods=["GET", "POST"])
def index():
    results = []

    if request.method == "POST":
        file = request.files.get("file")
        theme = request.form.get("theme", "").lower().strip()
        page_number = request.form.get("page_number", "").strip()

        # Step 2: Persistence Logic - Save file so it stays available
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
        else:
            # If no new file uploaded, check if one was already there (for re-analysis)
            files = os.listdir(app.config['UPLOAD_FOLDER'])
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], files[0]) if files else None

        if not filepath:
            results = ["Please upload a file."]
        else:
            text = ""
            # Extract Text Logic
            if filepath.endswith(".pdf"):
                with pdfplumber.open(filepath) as pdf:
                    if page_number and page_number.isdigit():
                        page_idx = int(page_number) - 1
                        if 0 <= page_idx < len(pdf.pages):
                            text = pdf.pages[page_idx].extract_text() or ""
                        else:
                            results = ["Page number out of range."]
                    else:
                        for page in pdf.pages:
                            text += (page.extract_text() or "") + "\n"
            elif filepath.endswith(".txt"):
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()

            # ANALYSIS LOGIC (The Deterministic AI Part)
            if text:
                if theme and theme in theme_keywords:
                    keywords = theme_keywords[theme]
                    # We now return the FULL text with highlights instead of just snippets
                    highlighted_result = highlight_content(text, keywords)
                    results = [highlighted_result]
                
                elif page_number:
                    detected = []
                    for t_name, kws in theme_keywords.items():
                        score = sum(1 for kw in kws if re.search(rf"\b{kw}\b", text, re.I))
                        if score > 0:
                            detected.append((t_name, score))
                    
                    if detected:
                        results = [f"Detected Theme: <b>{t}</b> (Score: {s})" for t, s in sorted(detected, key=lambda x: x[1], reverse=True)]

            if not results:
                results = ["No themes found on this page."]

    return render_template("index.html", results=results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)



