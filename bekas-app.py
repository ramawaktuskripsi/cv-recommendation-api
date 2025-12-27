# app.py - Railway-Ready CV Parser API

import os
import re
import json
import requests
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Flask
from flask import Flask, request, jsonify
from flask_cors import CORS

# NLP & NER
import spacy
import nltk
from nltk.tokenize import sent_tokenize

# Fuzzy Matching
from rapidfuzz import fuzz

# Document Processing
import pdfplumber
from docx import Document

# ============================================
# CONFIGURATION
# ============================================

app = Flask(__name__)
CORS(app)

# Environment
PORT = int(os.environ.get('PORT', 5000))
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')

# Folders
TEMP_FOLDER = 'temp'
UPLOAD_FOLDER = 'uploads'
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load NLP Model
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    print("⚠️  spaCy model not found. Downloading...")
    os.system('python -m spacy download en_core_web_sm')
    nlp = spacy.load('en_core_web_sm')

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

# ============================================
# COMMON SYNONYMS (Minimal - for variations)
# ============================================

# Hanya common variations yang sering muncul
# Tidak perlu maintain semua skills - skills diambil dari required_skills di request
COMMON_SYNONYMS = {
    # Office Tools
    "excel": ["microsoft excel", "ms excel", "spreadsheet", "excel spreadsheet"],
    "word": ["microsoft word", "ms word", "word processing"],
    "powerpoint": ["microsoft powerpoint", "ms powerpoint", "ppt", "presentation"],
    "office": ["microsoft office", "ms office"],
    
    # Quality & Manufacturing
    "quality control": ["qc", "quality assurance", "qa", "quality inspector", "quality checker", "inspeksi kualitas"],
    "lean manufacturing": ["lean", "lean production", "5s", "kaizen"],
    "six sigma": ["6 sigma", "six-sigma", "6-sigma"],
    
    # Leadership & Soft Skills
    "leadership": ["team leadership", "people management", "team lead", "team leader", "supervisi", "kepemimpinan"],
    "communication": ["komunikasi", "interpersonal skills"],
    "problem solving": ["problem-solving", "analytical thinking", "critical thinking"],
    
    # Technical
    "autocad": ["auto cad", "auto-cad", "cad"],
    "sap": ["sap erp", "sap system"],
    "erp": ["erp system", "enterprise resource planning"],
    
    # Industry Specific - Textile & Footwear
    "ppic": ["ppic", "production planning", "inventory control", "planning control", "production control"],
    "painting": ["painting", "cat", "pengecatan", "finishing", "spray painting", "pewarnaan"],
    "sablon": ["sablon", "screen printing", "printing", "cetak sablon", "sablon manual", "sablon otomatis"],
    
    # Bahasa Indonesia variations
    "kepemimpinan": ["leadership", "team leadership"],
    "kualitas": ["quality", "quality control", "qc"],
}

# ============================================
# SKILL INFERENCE PATTERNS
# ============================================

SKILL_PATTERNS = {
    r'(inspeksi|pemeriksaan|quality check)\s+(kualitas|produk)': 'Quality Control',
    r'(memimpin|supervisi|mengawasi)\s+tim': 'Leadership',
    r'(excel|spreadsheet)': 'Microsoft Excel',
    r'(lean|5s|kaizen)': 'Lean Manufacturing',
    r'(maintenance|perawatan)\s+mesin': 'Maintenance Management',
}

# ============================================
# KEYWORD EXTRACTION FROM JOB TITLE
# ============================================

def extract_keywords_from_job_title(job_title: str) -> List[str]:
    """
    Extract keywords from job title by removing stopwords and common terms.
    
    Args:
        job_title: Job title string (e.g., "OPERATOR SABLON")
    
    Returns:
        List of keywords (e.g., ["operator", "sablon"])
    """
    # Indonesian + English stopwords
    STOPWORDS = {
        'dan', 'atau', 'untuk', 'di', 'ke', 'dari', 'yang', 'dengan',
        'and', 'or', 'for', 'in', 'to', 'from', 'with', 'the', 'a', 'an',
        'staff', 'karyawan', 'pegawai', 'pekerja', 'worker', 'employee'
    }
    
    # Common acronyms (exception untuk short words)
    ACRONYMS = {'qc', 'qa', 'hr', 'it', 'ga', 'ppic', 'hrd', 'erp', 'sap'}
    
    # Clean and tokenize
    title_lower = job_title.lower()
    # Remove special characters, keep only alphanumeric and spaces
    title_clean = re.sub(r'[^a-z0-9\s]', ' ', title_lower)
    words = title_clean.split()
    
    # Filter stopwords and short words (except acronyms)
    keywords = [
        w for w in words 
        if w not in STOPWORDS and (len(w) > 2 or w in ACRONYMS)
    ]
    
    return keywords

# ============================================
# CV PARSER CLASS
# ============================================

class CVParser:
    def __init__(self):
        self.nlp = nlp
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"Error extracting PDF: {e}")
        
        # Preprocess text after extraction
        text = self._preprocess_text(text)
        
        return text
    
    def _preprocess_text(self, text: str) -> str:
        """
        Basic text preprocessing to clean CV text.
        
        Steps:
        1. Remove extra whitespaces (multiple spaces/tabs -> single space)
        2. Remove bullets and decorative symbols
        3. Normalize line breaks (max 2 consecutive)
        4. Remove leading/trailing whitespace per line
        
        Preserves:
        - Case (for name extraction with NER)
        - Punctuation (for email/phone extraction)
        - Numbers
        """
        # Remove extra spaces and tabs (but preserve single spaces)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Remove bullets and decorative symbols
        text = re.sub(r'[•●○■□▪▫◆◇★☆→←↑↓]', '', text)
        
        # Normalize line breaks (max 2 consecutive = paragraph separator)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove leading/trailing whitespace per line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def extract_text_from_docx(self, file_path: str) -> str:
        text = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            print(f"Error extracting DOCX: {e}")
        return text
    
    def extract_contact_info(self, text: str) -> Dict:
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        phone_patterns = [
            r'\+?62\s?\d{2,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
            r'0\d{2,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
        ]
        phone = None
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                phone = phones[0]
                break
        
        return {
            'email': emails[0] if emails else None,
            'phone': phone
        }
    
    def extract_name(self, text: str) -> Optional[str]:
        lines = text.split('\n')[:10]
        for line in lines:
            line = line.strip()
            if len(line.split()) >= 2 and len(line.split()) <= 4:
                if line.isupper() or line.istitle():
                    return line
        
        doc = self.nlp(text[:500])
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                return ent.text
        
        return None
    
    def extract_skills(self, text: str, required_skills: List[str]) -> List[str]:
        """
        Extract skills dari CV berdasarkan required_skills yang diberikan.
        Dynamic approach - hanya scan skills yang relevan.
        
        Args:
            text: CV text (already preprocessed)
            required_skills: List of skills yang dicari (dari job requirements)
        
        Returns:
            List of skills yang ditemukan di CV
        """
        # Additional preprocessing for skill matching
        text_lower = self._preprocess_for_matching(text)
        found_skills = set()
        
        for required_skill in required_skills:
            # Get variations dari skill ini
            variations = self._get_skill_variations(required_skill)
            
            # Check setiap variation
            for variation in variations:
                if variation.lower() in text_lower:
                    # Simpan dengan format original required_skill
                    found_skills.add(required_skill)
                    break  # Sudah ketemu, skip variations lainnya
        
        # Pattern matching untuk Bahasa Indonesia
        for pattern, skill in SKILL_PATTERNS.items():
            if skill in required_skills:  # Hanya jika skill ini di-require
                if re.search(pattern, text_lower):
                    found_skills.add(skill)
        
        return list(found_skills)
    
    def _get_skill_variations(self, skill: str) -> List[str]:
        """
        Get variations dari skill (synonyms, common typos, etc)
        
        Args:
            skill: Skill name
        
        Returns:
            List of variations
        """
        skill_lower = skill.lower()
        variations = [skill_lower]
        
        # Check di COMMON_SYNONYMS
        for key, synonyms in COMMON_SYNONYMS.items():
            if skill_lower == key or skill_lower in synonyms:
                variations.extend(synonyms)
                variations.append(key)
        
        # Remove duplicates
        return list(set(variations))
    
    def _preprocess_for_matching(self, text: str) -> str:
        """
        Aggressive preprocessing khusus untuk skill matching.
        
        Steps:
        1. Lowercase (case-insensitive matching)
        2. Remove punctuation (except hyphen for multi-word skills)
        3. Normalize spaces
        
        Args:
            text: Text to preprocess
        
        Returns:
            Preprocessed text for matching
        """
        # Lowercase
        text = text.lower()
        
        # Remove punctuation (keep hyphen and alphanumeric)
        text = re.sub(r'[^\w\s-]', '', text)
        
        # Normalize spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def parse(self, file_path: str, required_skills: List[str]) -> Dict:
        """
        Parse CV dan extract information.
        
        Args:
            file_path: Path to PDF file
            required_skills: List of skills yang dicari
        
        Returns:
            Dict with parsed information
        """
        # Extract text from PDF only
        if not file_path.endswith('.pdf'):
            raise ValueError("Only PDF files are supported")
        
        text = self.extract_text_from_pdf(file_path)
        
        if not text or len(text.strip()) < 50:
            raise ValueError("Unable to extract text from PDF or file is too short")
        
        # Extract information
        name = self.extract_name(text)
        contact = self.extract_contact_info(text)
        skills = self.extract_skills(text, required_skills)  # Pass required_skills
        
        return {
            'name': name,
            'email': contact['email'],
            'phone': contact['phone'],
            'skills': skills,
            'raw_text': text[:1000] if len(text) > 1000 else text
        }

# ============================================
# SKILL MATCHER CLASS
# ============================================

class SkillMatcher:
    def __init__(self, threshold: int = 75):
        self.threshold = threshold
    
    def get_synonyms(self, skill: str) -> List[str]:
        """
        Get synonyms untuk skill dari COMMON_SYNONYMS
        """
        skill_lower = skill.lower()
        expanded = [skill_lower]
        
        for key, synonyms in COMMON_SYNONYMS.items():
            if skill_lower in synonyms or skill_lower == key:
                expanded.extend(synonyms)
                expanded.append(key)
        
        return list(set(expanded))
    
    def match_single_skill(self, required: str, candidate_skills: List[str]) -> Dict:
        required_synonyms = self.get_synonyms(required)
        
        best_match = None
        best_score = 0
        match_type = None
        
        for cand_skill in candidate_skills:
            cand_synonyms = self.get_synonyms(cand_skill)
            
            for req_syn in required_synonyms:
                for cand_syn in cand_synonyms:
                    score = fuzz.token_set_ratio(req_syn, cand_syn)
                    
                    if score > best_score:
                        best_score = score
                        best_match = cand_skill
                        
                        if score == 100:
                            match_type = "Exact"
                        elif req_syn != required or cand_syn != cand_skill:
                            match_type = "Synonym"
                        else:
                            match_type = "Fuzzy"
        
        is_match = best_score >= self.threshold
        
        return {
            'required': required,
            'matched': best_match if is_match else None,
            'score': best_score,
            'is_match': is_match,
            'match_type': match_type if is_match else None
        }
    
    def match_all(self, required_skills: List[str], candidate_skills: List[str]) -> Dict:
        matches = []
        
        for req_skill in required_skills:
            match_result = self.match_single_skill(req_skill, candidate_skills)
            matches.append(match_result)
        
        matched_skills = [m for m in matches if m['is_match']]
        match_percentage = (len(matched_skills) / len(required_skills) * 100) if required_skills else 0
        
        return {
            'matches': matches,
            'statistics': {
                'total_required': len(required_skills),
                'matched_count': len(matched_skills),
                'match_percentage': round(match_percentage, 2)
            }
        }

# ============================================
# INITIALIZE
# ============================================

cv_parser = CVParser()
skill_matcher = SkillMatcher(threshold=75)

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'CV Parser & Skill Matcher API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'health': '/api/health',
            'parse': '/api/parse-cv',
            'match': '/api/match-skills',
            'process': '/api/process-complete'
        }
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/process-complete', methods=['POST'])
def process_complete():
    """
    Process CV from URL (Supabase Storage)
    
    Request Body (JSON):
    {
        "cv_url": "https://...",
        "job_id": "...",
        "application_id": "...",
        "job_title": "...",
        "required_skills": [...]
    }
    """
    try:
        data = request.get_json()
        
        cv_url = data.get('cv_url')
        job_id = data.get('job_id')
        application_id = data.get('application_id')
        job_title = data.get('job_title', 'Unknown Position')
        required_skills = data.get('required_skills', [])
        
        if not cv_url:
            return jsonify({
                'success': False,
                'error': 'cv_url is required'
            }), 400
        
        # FALLBACK: If no required_skills, extract from job_title
        if not required_skills:
            if job_title and job_title != 'Unknown Position':
                print(f"⚠️  No required_skills provided. Extracting keywords from job title: {job_title}")
                required_skills = extract_keywords_from_job_title(job_title)
                print(f"📝 Extracted keywords: {required_skills}")
            else:
                return jsonify({
                    'success': False,
                    'error': 'Either required_skills or job_title must be provided'
                }), 400
        
        if not required_skills:
            return jsonify({
                'success': False,
                'error': 'Unable to determine skills to match (empty job_title or required_skills)'
            }), 400
        
        # Download CV from URL
        print(f"📥 Downloading CV from: {cv_url}")
        cv_response = requests.get(cv_url, timeout=30)
        
        if cv_response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Failed to download CV: HTTP {cv_response.status_code}'
            }), 400
        
        # Validate PDF only
        content_type = cv_response.headers.get('Content-Type', '')
        is_pdf = 'pdf' in content_type or cv_url.lower().endswith('.pdf')
        
        if not is_pdf:
            return jsonify({
                'success': False,
                'error': 'Only PDF files are supported',
                'message': 'Please upload CV in PDF format only'
            }), 400
        
        # Save temporarily
        temp_filename = f"temp_{os.urandom(8).hex()}.pdf"
        temp_path = os.path.join(TEMP_FOLDER, temp_filename)
        
        with open(temp_path, 'wb') as f:
            f.write(cv_response.content)
        
        print(f"✅ CV saved to: {temp_path}")
        
        # Parse CV
        print("🔍 Parsing CV...")
        parsed_cv = cv_parser.parse(temp_path, required_skills)
        
        # Match skills
        print("🎯 Matching skills...")
        match_result = skill_matcher.match_all(required_skills, parsed_cv['skills'])
        
        # Clean up
        os.remove(temp_path)
        print("🗑️  Temp file removed")
        
        # Generate recommendation
        match_pct = match_result['statistics']['match_percentage']
        matched_count = match_result['statistics']['matched_count']
        
        # Simple logic: if any skill matches, then RECOMMENDED
        if matched_count > 0:
            recommendation = "RECOMMENDED"
            
            print(f"✅ Processing complete: {matched_count}/{match_result['statistics']['total_required']} skills matched ({match_pct}%) - RECOMMENDED")
            
            # Only send data if RECOMMENDED
            return jsonify({
                'success': True,
                'data': {
                    'application_id': application_id,
                    'job_id': job_id,
                    'job_title': job_title,
                    'candidate': {
                        'name': parsed_cv['name'],
                        'email': parsed_cv['email'],
                        'phone': parsed_cv['phone'],
                        'skills': parsed_cv['skills']
                    },
                    'matching': match_result,
                    'recommendation': {
                        'status': recommendation,
                        'score': match_pct
                    }
                }
            })
        else:
            # NOT RECOMMENDED - don't send candidate data
            print(f"❌ Processing complete: 0/{match_result['statistics']['total_required']} skills matched - NOT RECOMMENDED")
            
            return jsonify({
                'success': False,
                'reason': 'NOT_RECOMMENDED',
                'message': 'No matching skills found',
                'application_id': application_id,
                'job_id': job_id
            }), 200  # Still 200 OK, but success=false
        
    except requests.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'Download error: {str(e)}'
        }), 500
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("="*60)
    print("🚀 CV PARSER & SKILL MATCHER API")
    print("="*60)
    print(f"\n🌐 Environment: {FLASK_ENV}")
    print(f"📍 Port: {PORT}")
    print(f"🔧 Common synonyms: {len(COMMON_SYNONYMS)} groups")
    print(f"⚡ Dynamic skill matching enabled")
    print("\n✅ Server starting...\n")
    
    app.run(host='0.0.0.0', port=PORT, debug=(FLASK_ENV == 'development'))