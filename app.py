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
            if re.search(rf"\b{kw}\b", temp_sentence, flags=re.IGNORECASE):
                found_in_sentence = True
                temp_sentence = re.sub(rf"\b({kw})\b", r"<b>\1</b>", temp_sentence, flags=re.IGNORECASE)
        
        if found_in_sentence:
            # Wrap matching sentence in 'mark' tag
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

        # Persistence Logic
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
        else:
            files = os.listdir(app.config['UPLOAD_FOLDER'])
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], files[0]) if files else None

        if not filepath:
            results = ["Please upload a file."]
        else:
            with pdfplumber.open(filepath) as pdf:
                
                # MODE A: Theme Search (Whole Book)
                if theme and theme in theme_keywords and not page_number:
                    keywords = theme_keywords[theme]
                    for i, page in enumerate(pdf.pages):
                        page_text = page.extract_text()
                        if page_text and any(re.search(rf"\b{kw}\b", page_text, re.I) for kw in keywords):
                            highlighted = highlight_content(page_text, keywords)
                            results.append(f"<div class='page-address'>Page {i+1}</div>{highlighted}")
                
                # MODE B: Specific Page Number Analysis (FIXED WITH HIGHLIGHTING)
                elif page_number and page_number.isdigit():
                    page_idx = int(page_number) - 1
                    if 0 <= page_idx < len(pdf.pages):
                        text = pdf.pages[page_idx].extract_text() or ""
                        
                        all_relevant_kws = []
                        detected_labels = []
                        
                        # Identify every theme present on this specific page
                        for t_name, kws in theme_keywords.items():
                            theme_found = False
                            for kw in kws:
                                if re.search(rf"\b{kw}\b", text, re.I):
                                    all_relevant_kws.append(kw)
                                    theme_found = True
                            
                            if theme_found:
                                score = sum(1 for kw in kws if re.search(rf"\b{kw}\b", text, re.I))
                                detected_labels.append(f"<b>{t_name.upper()}</b> ({score})")
                        
                        # Apply highlighting using keywords from ALL detected themes
                        if all_relevant_kws:
                            display_text = highlight_content(text, list(set(all_relevant_kws)))
                            summary = " | ".join(detected_labels)
                        else:
                            display_text = text.replace('\n', '<br>')
                            summary = "No specific themes detected"
                            
                        results = [f"<div class='page-address'>Page {page_number} Analysis</div><p style='color: #666; font-size: 0.9rem;'>Themes: {summary}</p><hr>{display_text}"]
                    else:
                        results = ["Page number out of range."]

            if not results:
                results = ["No themes found matching your search."]

    return render_template("index.html", results=results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)




