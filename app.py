from flask import Flask, request, jsonify
from flask_cors import CORS
from sklearn.feature_extraction.text import TfidfVectorizer
import re

app = Flask(__name__)
CORS(app)

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    try:
        data = request.get_json()
        
        if not data or 'resume_text' not in data or 'job_description_text' not in data:
            return jsonify({'error': 'Missing required fields: resume_text and job_description_text'}), 400
        
        resume_text = data['resume_text'].strip()
        job_description_text = data['job_description_text'].strip()
        
        if not resume_text or not job_description_text:
            return jsonify({'error': 'Resume and job description text cannot be empty'}), 400
        
        # Clean and preprocess text
        def clean_text(text):
            # Remove special characters and convert to lowercase
            text = re.sub(r'[^\w\s]', ' ', text.lower())
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        
        clean_resume = clean_text(resume_text)
        clean_job_desc = clean_text(job_description_text)
        
        # Create TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2),  # Include both single words and bigrams
            min_df=1
        )
        
        # Fit and transform the documents
        documents = [clean_resume, clean_job_desc]
        tfidf_matrix = vectorizer.fit_transform(documents)
        
        # Get feature names (keywords)
        feature_names = vectorizer.get_feature_names_out()
        
        # Get TF-IDF scores for job description (second document)
        job_desc_scores = tfidf_matrix[1].toarray()[0]
        
        # Find important keywords from job description (top 20 by TF-IDF score)
        keyword_scores = list(zip(feature_names, job_desc_scores))
        keyword_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Get top keywords (excluding very low scores)
        top_keywords = [keyword for keyword, score in keyword_scores[:20] if score > 0.01]
        
        # Find which keywords are present in resume
        resume_words = set(clean_resume.split())
        matched_keywords = []
        
        for keyword in top_keywords:
            # Check if keyword (or its parts) is in resume
            if ' ' in keyword:  # Bigram
                if keyword in clean_resume:
                    matched_keywords.append(keyword)
            else:  # Single word
                if keyword in resume_words:
                    matched_keywords.append(keyword)
        
        # Calculate match score
        if top_keywords:
            match_score = round((len(matched_keywords) / len(top_keywords)) * 100, 1)
        else:
            match_score = 0.0
        
        return jsonify({
            'match_score': match_score,
            'matched_keywords': matched_keywords,
            'total_keywords_analyzed': len(top_keywords)
        })
        
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'ResuMatch API is running'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
