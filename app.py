from flask import Flask, request, jsonify, send_from_directory
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_cors import CORS
from sklearn.feature_extraction.text import TfidfVectorizer
import os
import io
import re

app = Flask(__name__)
CORS(app)
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
try:

    import docx
except ImportError:
    docx = None

# Weighted keywords (higher weight => more impact)
HIGH_VALUE_WEIGHTS = {
    'python': 2.0,
    'flask': 2.0,
    'django': 1.8,
    'fastapi': 1.8,
    'aws': 2.2,
    'docker': 1.6,
    'kubernetes': 1.8,
    'sql': 1.5,
    'postgresql': 1.7,
    'rest api': 1.6,
    'pandas': 1.7,
}

DB_PATH = 'analysis_history.db'

def extract_sentence_for_keyword(text: str, keyword: str) -> str:
    """Return a sentence from text that contains the keyword (case-insensitive)."""
    try:
        # Simple sentence split on ., !, ?
        import re as _re
        parts = [_s.strip() for _s in _re.split(r'(?<=[.!?])\s+', text) if _s.strip()]
        if ' ' in keyword:
            pat = _re.compile(_re.escape(keyword), _re.IGNORECASE)
        else:
            pat = _re.compile(r'\b' + _re.escape(keyword) + r'\b', _re.IGNORECASE)
        for s in parts:
            if pat.search(s):
                return s
    except Exception:
        pass
    return ''

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    role_template = None
    resume_text = None
    job_description_text = None
    try:
        # Parse input (multipart for files, JSON otherwise)
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            file = request.files.get('resume_file')
            if file:
                filename = secure_filename(file.filename)
                ext = os.path.splitext(filename)[1].lower()
                if ext == '.pdf' and PyPDF2:
                    reader = PyPDF2.PdfReader(file)
                    resume_text = ' '.join(page.extract_text() or '' for page in reader.pages)
                elif ext in ['.docx'] and docx:
                    _doc = docx.Document(file)
                    resume_text = ' '.join(para.text for para in _doc.paragraphs)
                else:
                    # Treat unknown as plain text
                    resume_text = file.read().decode(errors='ignore')
            job_description_text = request.form.get('job_description_text', '').strip()
            role_template = request.form.get('role_template')
        else:
            data = request.get_json() or {}
            resume_text = data.get('resume_text', '').strip()
            job_description_text = data.get('job_description_text', '').strip()
            role_template = data.get('role_template')

    # Role template override removed for simplicity in new logic
        if not resume_text or not job_description_text:
            return jsonify({'error': 'Resume and job description text cannot be empty'}), 400

        # Clean text for vectorization; keep originals for context
        def clean_text(text: str) -> str:
            text = re.sub(r'[^\w\s]', ' ', text.lower())
            return re.sub(r'\s+', ' ', text).strip()

        clean_resume = clean_text(resume_text)
        clean_job = clean_text(job_description_text)

        # TF-IDF
        vectorizer = TfidfVectorizer(max_features=100, stop_words='english', ngram_range=(1, 2), min_df=1)
        tfidf = vectorizer.fit_transform([clean_resume, clean_job])
        feature_names = vectorizer.get_feature_names_out()
        job_scores = tfidf[1].toarray()[0]
        kw_scores = sorted(zip(feature_names, job_scores), key=lambda x: x[1], reverse=True)
        top_kws = [k for k, s in kw_scores[:20] if s > 0.01]

        # Matched / Missing
        resume_words = set(clean_resume.split())
        matched, missing = [], []
        for kw in top_kws:
            if ' ' in kw:
                (matched if kw in clean_resume else missing).append(kw)
            else:
                (matched if kw in resume_words else missing).append(kw)

        # Cosine similarity score
    # (Removed cosine_similarity and SUGGESTIONS_MAP logic for new analysis)

        # Save history
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO history (timestamp, role_template, job_description, match_score) VALUES (?, ?, ?, ?)',
            (datetime.utcnow().isoformat(), role_template, job_description_text, match_score)
        )
        conn.commit()
        conn.close()

        return jsonify({
            'match_score': match_score,
            'matched_keywords': matched,
            'missing_keywords': missing,
            'total_keywords_analyzed': len(jd_keywords)
        })
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/history', methods=['GET'])
def get_history():
    """Return saved analysis history."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT id, timestamp, role_template, job_description, match_score FROM history ORDER BY id DESC')
    rows = cur.fetchall()
    conn.close()
    history = []
    for row in rows:
        history.append({
            'id': row[0],
            'timestamp': row[1],
            'role_template': row[2],
            'job_description': row[3],
            'match_score': row[4]
        })
    return jsonify(history)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'ResuMatch API is running'})

@app.route('/')
def serve_frontend():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
