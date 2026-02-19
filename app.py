from flask import Flask, request, render_template
import re
import pdfplumber
import os

app = Flask(__name__)

theme_keywords = {
    "education": ["education", "learning", "school", "teacher", "classroom", "knowledge", "study", "exam"],
    "betrayal": ["betrayal", "deception", "cheating", "mistrust", "treachery"],
    "courage": ["courage", "bravery", "heroism", "sacrifice", "fearless"]
}

def highlight_keywords(paragraph, keywords):
    for kw in keywords:
        paragraph = re.sub(rf"\b({kw})\b", r"<b>\1</b>", paragraph, flags=re.IGNORECASE)
    return paragraph

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

        if not file:
            results = ["Please upload a file."]
        else:
            filename = file.filename.lower()
            text = ""

            # ===== HANDLE PDF =====
            if filename.endswith(".pdf"):
                import pdfplumber
                with pdfplumber.open(file) as pdf:
                    if page_number and page_number.isdigit():
                        page_idx = int(page_number) - 1
                        if 0 <= page_idx < len(pdf.pages):
                            text = pdf.pages[page_idx].extract_text() or ""
                        else:
                            results = ["Page number out of range."]
                    else:
                        for page in pdf.pages:
                            text += (page.extract_text() or "") + "\n"

            # ===== HANDLE TXT =====
            elif filename.endswith(".txt"):
                text = file.read().decode("utf-8")
            else:
                results = ["Unsupported file type."]

            # ===== MODE 1: THEME SEARCH =====
            if theme and theme in theme_keywords:
                paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 20]
                keywords = theme_keywords[theme]
                scored = sorted(
                    [(p, sum(1 for kw in keywords if kw.lower() in p.lower())) for p in paragraphs],
                    key=lambda x: x[1],
                    reverse=True
                )
                results = [highlight_keywords(p, keywords) for p, s in scored if s > 0][:5]

            # ===== MODE 2: PAGE THEME DETECTION =====
            elif page_number:
                detected = []
                for t_name, kws in theme_keywords.items():
                    score = sum(1 for kw in kws if kw.lower() in text.lower())
                    if score > 0:
                        detected.append((t_name, score))
                results = [f"Detected Theme: <b>{t}</b> (Score: {s})" for t, s in sorted(detected, key=lambda x: x[1], reverse=True)]

            # ===== DEFAULT IF NOTHING FOUND =====
            if not results:
                results = ["No results found."]

    # Always return the template
    return render_template("index.html", results=results)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Use Render's PORT or default to 5000 locally
    app.run(host="0.0.0.0", port=port, debug=True)




