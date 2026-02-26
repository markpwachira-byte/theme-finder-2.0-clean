from flask import Flask, request, render_template
import re
import pdfplumber
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ==============================
# AI KNOWLEDGE BASE (The Brain)
# ==============================
ai_knowledge = {
    "education": {
        "anchors": {"education": 1.0, "learning": 0.7, "school": 0.5, "teacher": 0.7, "classroom": 0.8, "knowledge": 0.5, "study": 0.4, "exam": 0.9},
        "vetoes": ["fish", "shiver", "swimming", "ocean", "fry"]
    },
    "courage": {
        "anchors": {"courage": 1.0, "bravery": 1.0, "heroism": 1.0, "sacrifice": 0.8, "fearless": 0.9},
        "vetoes": []
    },
    "corruption": {
        "anchors": {"corruption": 1.0, "bribery": 1.0, "impunity": 0.9, "misuse of power": 1.0, "grabbing": 0.7, "embezzlement": 1.0, "nepotism": 0.9, "tender": 0.8, "municipality": 0.4},
        "vetoes": ["tender heart", "tender meat"]
    },
    "betrayal": {
        "anchors": {"betrayal": 1.0, "disloyalty": 1.0, "treachery": 1.0, "double-cross": 1.0, "unfaithful": 0.8, "abandon": 0.5, "sell-out": 0.8},
        "vetoes": []
    },
    "leadership": {
        "anchors": {"leadership": 1.0, "governance": 0.9, "dictatorship": 1.0, "regime": 1.0, "authority": 0.7, "power struggle": 1.0, "politics": 0.6, "heads of state": 1.0},
        "vetoes": ["biological father", "priest", "mountain peak"]
    },
    "change": {
        "anchors": {"change": 0.4, "transformation": 0.8, "reform": 0.9, "activism": 0.9, "revolution": 1.0, "innovation": 0.8, "protest": 0.9, "the Samaritan app": 1.0},
        "vetoes": ["small change", "loose change", "change clothes"]
    },
    "poverty": {
        "anchors": {"poverty": 1.0, "struggle": 0.5, "inequality": 0.8, "deprivation": 0.9, "destitution": 1.0, "suffering": 0.5, "slums": 0.9, "underprivileged": 0.9},
        "vetoes": []
    },
    "technology": {
        "anchors": {"technology": 1.0, "digital": 0.9, "app": 0.8, "innovation": 0.7, "social media": 1.0, "internet": 1.0, "online": 0.8, "software": 0.9},
        "vetoes": []
    }
}

# Use /tmp for Render deployment as it's a writable directory
UPLOAD_FOLDER = '/tmp'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ==============================
# AI HIGHLIGHTER (Context-Aware)
# ==============================
def highlight_content(text, theme_name):
    knowledge = ai_knowledge.get(theme_name)
    if not knowledge:
        return text.replace('\n', ' '), "General content analysis performed."

    anchors = knowledge["anchors"]
    vetoes = knowledge["vetoes"]

    text = text.replace('\n', ' ')
    sentences = re.split(r'(?<=[.!?]) +', text)
    highlighted_page = []
    found_keywords = []

    for sentence in sentences:
        if any(re.search(rf"\b{v}\b", sentence, re.I) for v in vetoes):
            highlighted_page.append(sentence)
            continue

        score = 0
        temp_sentence = sentence
        found_any = False
        
        for kw, weight in anchors.items():
            if re.search(rf"\b{kw}\b", sentence, flags=re.IGNORECASE):
                score += weight
                found_any = True
                found_keywords.append(kw.lower())
                temp_sentence = re.sub(rf"\b({kw})\b", r"<b>\1</b>", temp_sentence, flags=re.IGNORECASE)

        if found_any and score > 0.4:
            highlighted_page.append(f"<mark style='background-color: #fff3cd;'>{temp_sentence}</mark>")
        else:
            highlighted_page.append(sentence)

    unique_kw = sorted(list(set(found_keywords)))
    assessment = f"AI identified '{theme_name}' theme via: {', '.join(unique_kw[:3])}." if unique_kw else "No strong evidence."

    return " ".join(highlighted_page), assessment

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    
    if request.method == "POST":
        file = request.files.get("file")
        theme = request.form.get("theme", "").lower().strip()
        page_num = request.form.get("page_number", "").strip()

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                with pdfplumber.open(filepath) as pdf:
                    # Mode A: Theme Search
                    if theme and not page_num:
                        for i, page in enumerate(pdf.pages):
                            page_text = page.extract_text()
                            if page_text:
                                highlighted, assessment = highlight_content(page_text, theme)
                                if "<mark" in highlighted:
                                    results.append({"page": i + 1, "content": highlighted, "assessment": assessment})
                    
                    # Mode B: Page Analysis
                    elif page_num.isdigit():
                        idx = int(page_num) - 1
                        if 0 <= idx < len(pdf.pages):
                            page_text = pdf.pages[idx].extract_text() or ""
                            display, assessment = highlight_content(page_text, theme) if theme else (page_text, "Direct view.")
                            results.append({"page": page_num, "content": display, "assessment": assessment})
                
                # Cleanup: Delete file after processing to prevent storage errors
                if os.path.exists(filepath):
                    os.remove(filepath)
                    
            except Exception as e:
                results.append({"page": "Error", "content": f"PDF Error: {str(e)}", "assessment": "Failed to read file."})

    return render_template("index.html", results=results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)



