from flask import Flask, request, render_template
import re
import pdfplumber
import os
import sqlite3
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

def get_db():
    conn = sqlite3.connect("library.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            filepath TEXT,
            text TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
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

    # Generate the "Why" logic
    unique_kw = sorted(list(set(found_keywords)))
    if unique_kw:
        assessment = f"The AI identified the '{theme_name}' theme based on the presence of: {', '.join(unique_kw[:3])}."
    else:
        assessment = "No strong thematic evidence found on this page."

    return " ".join(highlighted_page), assessment

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    conn = get_db()
    library_books = conn.execute("SELECT id, title, filepath FROM books ORDER BY date_added DESC").fetchall()
    conn.close()

    if request.method == "POST":
        file = request.files.get("file")
        theme = request.form.get("theme", "").lower().strip()
        page_number = request.form.get("page_number", "").strip()
        selected_book_id = request.form.get("selected_book_id")

        filepath = None

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            conn = get_db()
            existing = conn.execute("SELECT id FROM books WHERE title = ?", (filename,)).fetchone()
            if not existing:
                full_text = ""
                with pdfplumber.open(filepath) as pdf:
                    for page in pdf.pages:
                        full_text += (page.extract_text() or "") + "\n"
                conn.execute("INSERT INTO books (title, filepath, text) VALUES (?, ?, ?)", (filename, filepath, full_text))
                conn.commit()
            conn.close()
            conn = get_db()
            library_books = conn.execute("SELECT id, title, filepath FROM books ORDER BY date_added DESC").fetchall()
            conn.close()

        elif selected_book_id:
            conn = get_db()
            book = conn.execute("SELECT filepath FROM books WHERE id = ?", (selected_book_id,)).fetchone()
            conn.close()
            if book:
                filepath = book['filepath']

        if filepath:
            with pdfplumber.open(filepath) as pdf:
                # MODE A: Theme Search
                if theme and theme in ai_knowledge and not page_number:
                    for i, page in enumerate(pdf.pages):
                        page_text = page.extract_text()
                        if page_text:
                            highlighted, assessment = highlight_content(page_text, theme)
                            if "<mark" in highlighted:
                                # NECESSARY CHANGE: Dictionary keys must match HTML r.page, r.content, r.assessment
                                results.append({
                                    "page": i + 1,
                                    "content": highlighted,
                                    "assessment": assessment
                                })
                
                # MODE B: Specific Page Analysis
                elif page_number.isdigit():
                    idx = int(page_number) - 1
                    if 0 <= idx < len(pdf.pages):
                        page_text = pdf.pages[idx].extract_text() or ""
                        display, assessment = highlight_content(page_text, theme) if theme else (page_text, "Direct view of page text.")
                        results.append({
                            "page": page_number,
                            "content": display,
                            "assessment": assessment
                        })

    return render_template("index.html", results=results, library_books=library_books)

if __name__ == "__main__":
    app.run(debug=True)



